# Crypto Price Alert Bot for Telegram

A small, self-hosted Telegram bot that messages you when a coin hits your price. Written in Python, free to run, no exchange account or API key needed.

- `/alert BTC above 100000`: ping me when Bitcoin is at or above $100,000
- `/alert ETH below 2500`: ping me when Ethereum drops to $2,500
- `/alert SOL change 5`: ping me when Solana moves 5% up or down from now
- `/price BTC ETH SOL`: current price and 24h change

Works with thousands of coins. Prices come from the free [CoinGecko API](https://www.coingecko.com/en/api). Every alert includes a link to the coin's live chart and full price history on [TokenAlphabet](https://tokenalphabet.com/).

## What it looks like

```
You:  /alert BTC above 100k
Bot:  Alert #1 set: BTC above $100,000.00
      Now: $97,412.55 · BTC chart

Bot:  🔔 BTC above $100,000.00
      Now: $100,184.20 (+3.12% 24h)
      BTC chart on TokenAlphabet
```

## Quick start

1. Create a bot: open [@BotFather](https://t.me/BotFather) in Telegram, send `/newbot` and copy the token.
2. Get the code and install dependencies (Python 3.10+):

   ```bash
   git clone https://github.com/tokenalphabet-ui/crypto-price-alert-bot.git
   cd crypto-price-alert-bot
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and paste your token:

   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   ```

4. Run it:

   ```bash
   python bot.py
   ```

5. Open your bot in Telegram and send `/start`.

### Run with Docker

```bash
docker build -t crypto-price-alert-bot .
docker run -d --name price-alerts --env-file .env -v alerts-data:/data crypto-price-alert-bot
```

## Commands

| Command | What it does |
|---|---|
| `/price BTC ETH` | Price and 24h change, up to 5 coins at once |
| `/alert BTC above 100000` | Fires when the price is at or above the target |
| `/alert ETH below 2500` | Fires when the price is at or below the target |
| `/alert SOL change 5` | Fires when the price moves 5% either way from the moment you set it |
| `/list` | Your active alerts |
| `/delete 3` | Delete alert #3 |
| `/clear` | Delete all your alerts |

Numbers can be written as `100000`, `100,000`, `100k` or `1.5m`. Coins can be given by ticker (`BTC`) or by CoinGecko id (`bitcoin`). When several coins share a ticker, the one with the largest market cap wins. Each alert fires once and is then removed.

## Settings

All settings go in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | (required) | Token from @BotFather |
| `CHECK_INTERVAL` | `60` | Seconds between price checks |
| `MAX_ALERTS_PER_CHAT` | `20` | Alert limit per user or group |
| `DB_PATH` | `alerts.db` | SQLite file for alerts |
| `COINGECKO_API_KEY` | (empty) | Optional free [CoinGecko Demo key](https://www.coingecko.com/en/api/pricing) for higher rate limits |

The public CoinGecko API allows only a few requests per minute. The bot batches all alerts into one request per check and waits and retries when it gets rate limited. If you run it for many users, add a free Demo key.

## How it works

```
bot.py         Telegram commands and the price check job
alerts.py      Parsing "/alert BTC above 100k", trigger rules, formatting
coingecko.py   Async CoinGecko client: ticker lookup and batched prices
storage.py     SQLite storage for alerts
links.py       Links to coin charts on tokenalphabet.com
tests/         Unit tests: python -m unittest discover -s tests
```

Every `CHECK_INTERVAL` seconds the bot loads prices for all coins that have alerts in a single request, sends a message for each alert whose condition is met and deletes it. If a user blocks the bot, their alerts are removed.

## Ideas for your own version

- Alerts on 24h volume or market cap
- Repeating alerts instead of one-shot
- Daily morning summary of your watchlist
- Inline buttons to snooze or re-arm an alert

Pull requests are welcome.

## About

Made by [TokenAlphabet](https://tokenalphabet.com/): live crypto prices, charts, market cap rankings and free historical data for Bitcoin and thousands of altcoins. See also our [crypto wallet guides](https://github.com/tokenalphabet-ui/awesome-crypto-wallets).

Not financial advice. Prices can be delayed; do not rely on this bot for trading decisions that need exact timing.

## License

[MIT](LICENSE)
