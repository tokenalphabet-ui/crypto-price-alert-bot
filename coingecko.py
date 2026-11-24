"""Minimal async client for the free CoinGecko API."""

from __future__ import annotations

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)

PUBLIC_URL = "https://api.coingecko.com/api/v3"


class CoinGecko:
    def __init__(self, api_key: str | None = None):
        headers = {"accept": "application/json"}
        if api_key:
            headers["x-cg-demo-api-key"] = api_key
        self.client = httpx.AsyncClient(base_url=PUBLIC_URL, headers=headers, timeout=20)
        self.by_symbol: dict[str, str] = {}  # "btc" -> "bitcoin" (largest market cap wins)
        self.coins: dict[str, tuple[str, str]] = {}  # "bitcoin" -> ("BTC", "Bitcoin")

    async def _get(self, path: str, params: dict | None = None, retries: int = 3):
        """GET with a pause and retry when the free API says 429 Too Many Requests."""
        for attempt in range(retries + 1):
            r = await self.client.get(path, params=params)
            if r.status_code != 429 or attempt == retries:
                r.raise_for_status()
                return r.json()
            retry_after = r.headers.get("retry-after", "")
            delay = min(int(retry_after), 60) if retry_after.isdigit() else 5 * (attempt + 1)
            log.info("CoinGecko rate limit, retrying in %ss", delay)
            await asyncio.sleep(delay)

    def _remember(self, coin_id: str, symbol: str, name: str) -> None:
        symbol = symbol.upper()
        self.coins[coin_id] = (symbol, name)
        self.by_symbol.setdefault(symbol.lower(), coin_id)

    async def refresh_symbols(self, pages: int = 4) -> None:
        """Load the top coins by market cap so tickers resolve without extra calls."""
        by_symbol: dict[str, str] = {}
        loaded = 0
        for page in range(1, pages + 1):
            try:
                data = await self._get("/coins/markets", {
                    "vs_currency": "usd", "order": "market_cap_desc",
                    "per_page": 250, "page": page,
                })
            except httpx.HTTPError as e:
                log.warning("Could not load coin list page %s: %s", page, e)
                break
            for c in data:
                by_symbol.setdefault(c["symbol"].lower(), c["id"])
                self.coins[c["id"]] = (c["symbol"].upper(), c["name"])
            loaded += len(data)
        if by_symbol:
            self.by_symbol = by_symbol
        log.info("Loaded %s coins, %s tickers", loaded, len(self.by_symbol))

    async def resolve(self, query: str) -> tuple[str, str, str] | None:
        """Ticker or CoinGecko id -> (coin_id, SYMBOL, Name)."""
        q = query.strip().lower()
        if q in self.by_symbol:
            coin_id = self.by_symbol[q]
            return (coin_id, *self.coins[coin_id])
        if q in self.coins:
            return (q, *self.coins[q])
        data = await self._get("/search", {"query": q})
        for c in data.get("coins", []):
            if c["symbol"].lower() == q or c["id"] == q:
                self._remember(c["id"], c["symbol"], c["name"])
                return (c["id"], c["symbol"].upper(), c["name"])
        return None

    async def prices(self, coin_ids: list[str]) -> dict[str, dict]:
        """{coin_id: {"usd": 65000.0, "usd_24h_change": 1.2}}"""
        result: dict[str, dict] = {}
        ids = sorted(set(coin_ids))
        for i in range(0, len(ids), 200):
            chunk = ids[i:i + 200]
            data = await self._get("/simple/price", {
                "ids": ",".join(chunk), "vs_currencies": "usd",
                "include_24hr_change": "true",
            })
            result.update(data)
        return result

    async def close(self) -> None:
        await self.client.aclose()
