"""Links to coin charts on TokenAlphabet.

tokenalphabet_slugs.json maps CoinGecko coin ids to TokenAlphabet page slugs
for the top 1000 coins. Coins outside the map link to the full coin list.

The site moved to token-alphabet.com. Coin pages that already exist there are
listed in NEW_SITE_SLUGS; the rest still live on the old domain until the new
site gets them. Add a slug to NEW_SITE_SLUGS once its page opens on the new site.
"""

from __future__ import annotations

import json
from pathlib import Path

SITE = "https://token-alphabet.com"
OLD_SITE = "https://tokenalphabet.com"
UTM = "utm_source=github&utm_medium=telegram_bot&utm_campaign=crypto_price_alert_bot"

NEW_SITE_SLUGS = {
    "bitcoin-btc-price",
    "ethereum-eth-price",
    "tether-usdt-price",
    "xrp-price",
    "bnb-price",
    "solana-sol-price",
}

_SLUGS_FILE = Path(__file__).with_name("tokenalphabet_slugs.json")
SLUGS: dict[str, str] = json.loads(_SLUGS_FILE.read_text(encoding="utf-8"))


def chart_url(coin_id: str) -> str:
    slug = SLUGS.get(coin_id)
    if not slug:
        return f"{SITE}/cryptocurrencies?{UTM}"
    site = SITE if slug in NEW_SITE_SLUGS else OLD_SITE
    return f"{site}/cryptocurrencies/{slug}?{UTM}"
