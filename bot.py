"""Crypto price alert bot for Telegram.

Set alerts like "/alert BTC above 100000" and get a message when the price
gets there. Prices come from the free CoinGecko API; every alert links to the
coin's live chart on TokenAlphabet (https://token-alphabet.com).
"""

from __future__ import annotations

import html
import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import BotCommand, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes

from alerts import Alert, describe, fmt_change, fmt_price, is_triggered, parse_alert_args
from coingecko import CoinGecko
from links import SITE, UTM, chart_url
from storage import Storage

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))
MAX_ALERTS_PER_CHAT = int(os.environ.get("MAX_ALERTS_PER_CHAT", "20"))
DB_PATH = os.environ.get("DB_PATH", "alerts.db")
COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY") or None

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

HELP = """<b>Crypto price alerts</b>

/price BTC ETH: current price and 24h change
/alert BTC above 100000: tell me when BTC is at or above $100,000
/alert ETH below 2500: tell me when ETH is at or below $2,500
/alert SOL change 5: tell me when SOL moves 5% up or down from now
/list: your alerts
/delete 3: delete alert #3
/clear: delete all your alerts

Numbers can be written as 100000, 100k or 1.5m. Each alert fires once.
Live charts and price history: <a href="{site}">token-alphabet.com</a>
Not financial advice."""

COMMANDS = [
    BotCommand("price", "Current price: /price BTC"),
    BotCommand("alert", "New alert: /alert BTC above 100000"),
    BotCommand("list", "Your alerts"),
    BotCommand("delete", "Delete an alert: /delete 3"),
    BotCommand("clear", "Delete all alerts"),
    BotCommand("help", "How to use the bot"),
]


def cg(context: ContextTypes.DEFAULT_TYPE) -> CoinGecko:
    return context.bot_data["cg"]


def db(context: ContextTypes.DEFAULT_TYPE) -> Storage:
    return context.bot_data["db"]


async def reply(update: Update, text: str) -> None:
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW
    )


def coin_link(coin_id: str, symbol: str) -> str:
    return f'<a href="{html.escape(chart_url(coin_id))}">{html.escape(symbol)} chart</a>'


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, HELP.format(site=html.escape(f"{SITE}/?{UTM}")))


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await reply(update, "Use: /price BTC or /price BTC ETH SOL")
        return
    found, missing = [], []
    for q in context.args[:5]:
        coin = await cg(context).resolve(q)
        if coin:
            found.append(coin)
        else:
            missing.append(q)
    lines = []
    if found:
        prices = await cg(context).prices([c[0] for c in found])
        for coin_id, symbol, name in found:
            p = prices.get(coin_id, {})
            if "usd" not in p:
                lines.append(f"{html.escape(symbol)}: no price right now")
                continue
            lines.append(
                f"<b>{html.escape(symbol)}</b> ({html.escape(name)}): {fmt_price(p['usd'])}, "
                f"{fmt_change(p.get('usd_24h_change'))} 24h · {coin_link(coin_id, symbol)}"
            )
    if missing:
        lines.append("Not found: " + html.escape(", ".join(missing)))
    await reply(update, "\n".join(lines))


async def alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query, kind, value = parse_alert_args(context.args or [])
    except ValueError as e:
        await reply(update, html.escape(str(e)))
        return
    chat_id = update.effective_chat.id
    if db(context).count_for_chat(chat_id) >= MAX_ALERTS_PER_CHAT:
        await reply(update, f"You already have {MAX_ALERTS_PER_CHAT} alerts. Delete some with /delete.")
        return
    coin = await cg(context).resolve(query)
    if not coin:
        await reply(update, f"Coin {html.escape(query)} not found. Try the ticker (BTC) or CoinGecko id (bitcoin).")
        return
    coin_id, symbol, name = coin
    price = (await cg(context).prices([coin_id])).get(coin_id, {}).get("usd")
    if price is None:
        await reply(update, f"No price for {html.escape(symbol)} right now, try again later.")
        return
    alert_id = db(context).add(chat_id, coin_id, symbol, kind, value, price)
    alert = Alert(alert_id, chat_id, coin_id, symbol, kind, value, price)
    note = ""
    if kind != "change" and is_triggered(alert, price):
        note = "\nThe condition is already true, so it will fire on the next check."
    await reply(
        update,
        f"Alert #{alert_id} set: {html.escape(describe(alert))}\n"
        f"Now: {fmt_price(price)} · {coin_link(coin_id, symbol)}{note}",
    )


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alerts = db(context).for_chat(update.effective_chat.id)
    if not alerts:
        await reply(update, "No alerts yet. Example: /alert BTC above 100000")
        return
    lines = [f"#{a.id} {html.escape(describe(a))}" for a in alerts]
    await reply(update, "<b>Your alerts</b>\n" + "\n".join(lines))


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].lstrip("#").isdigit():
        await reply(update, "Use: /delete 3 (the number from /list)")
        return
    alert_id = int(context.args[0].lstrip("#"))
    ok = db(context).delete(update.effective_chat.id, alert_id)
    await reply(update, f"Alert #{alert_id} deleted." if ok else f"Alert #{alert_id} not found.")


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    n = db(context).clear(update.effective_chat.id)
    await reply(update, f"Deleted {n} alert(s).")


async def check_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    alerts = db(context).all()
    if not alerts:
        return
    try:
        prices = await cg(context).prices([a.coin_id for a in alerts])
    except httpx.HTTPError as e:
        log.warning("Price check failed: %s", e)
        return
    for a in alerts:
        p = prices.get(a.coin_id, {})
        price = p.get("usd")
        if price is None or not is_triggered(a, price):
            continue
        text = (
            f"🔔 <b>{html.escape(describe(a))}</b>\n"
            f"Now: {fmt_price(price)} ({fmt_change(p.get('usd_24h_change'))} 24h)\n"
            f"{coin_link(a.coin_id, a.symbol)} on TokenAlphabet"
        )
        try:
            await context.bot.send_message(
                a.chat_id, text, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW
            )
        except Forbidden:
            log.info("Chat %s blocked the bot, removing its alerts", a.chat_id)
            db(context).clear(a.chat_id)
            continue
        db(context).remove(a.id)


async def refresh_coins(context: ContextTypes.DEFAULT_TYPE) -> None:
    await cg(context).refresh_symbols()


async def post_init(app: Application) -> None:
    app.bot_data["cg"] = CoinGecko(COINGECKO_API_KEY)
    app.bot_data["db"] = Storage(DB_PATH)
    await app.bot_data["cg"].refresh_symbols()
    await app.bot.set_my_commands(COMMANDS)
    app.job_queue.run_repeating(check_alerts, interval=CHECK_INTERVAL, first=10)
    app.job_queue.run_repeating(refresh_coins, interval=6 * 3600, first=6 * 3600)
    log.info("Bot started, checking prices every %ss", CHECK_INTERVAL)


async def post_shutdown(app: Application) -> None:
    await app.bot_data["cg"].close()
    app.bot_data["db"].close()


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Error while handling an update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Something went wrong, please try again in a minute.")


def main() -> None:
    if not TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (get it from @BotFather)")
    app = (
        Application.builder().token(TOKEN)
        .post_init(post_init).post_shutdown(post_shutdown).build()
    )
    app.add_handler(CommandHandler(["start", "help"], help_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("alert", alert_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_error_handler(on_error)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
