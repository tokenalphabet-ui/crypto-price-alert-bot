"""Links to coin charts on TokenAlphabet.

tokenalphabet_slugs.json maps CoinGecko coin ids to TokenAlphabet page slugs
for the top 1000 coins. Coins outside the map link to the full coin list.
"""

from __future__ import annotations

import json
from pathlib import Path

SITE = "https://tokenalphabet.com"
UTM = "utm_source=github&utm_medium=telegram_bot&utm_campaign=crypto_price_alert_bot"

_SLUGS_FILE = Path(__file__).with_name("tokenalphabet_slugs.json")
SLUGS: dict[str, str] = json.loads(_SLUGS_FILE.read_text(encoding="utf-8"))


def chart_url(coin_id: str) -> str:
    slug = SLUGS.get(coin_id)
    path = f"/cryptocurrencies/{slug}" if slug else "/cryptocurrencies"
    return f"{SITE}{path}?{UTM}"
