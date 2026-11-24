"""Alert rules: parsing user input, checking triggers, formatting."""

from __future__ import annotations

from dataclasses import dataclass

KINDS = {
    "above": "above",
    ">": "above",
    ">=": "above",
    "below": "below",
    "<": "below",
    "<=": "below",
    "change": "change",
    "move": "change",
    "%": "change",
}

SUFFIXES = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


@dataclass
class Alert:
    id: int
    chat_id: int
    coin_id: str
    symbol: str
    kind: str  # "above" | "below" | "change"
    value: float  # target price in USD, or percent for "change"
    base_price: float  # price when the alert was created


def parse_number(text: str) -> float:
    """Parse '100000', '100,000', '$65k', '1.5m', '5%' into a float."""
    t = text.strip().lower().replace(",", "").replace("$", "").replace("%", "")
    mult = 1
    if t and t[-1] in SUFFIXES:
        mult = SUFFIXES[t[-1]]
        t = t[:-1]
    try:
        n = float(t) * mult
    except ValueError:
        raise ValueError(f"'{text}' is not a number") from None
    if n <= 0:
        raise ValueError("The number must be greater than zero")
    return n


def parse_alert_args(args: list[str]) -> tuple[str, str, float]:
    """['BTC', 'above', '100k'] -> ('BTC', 'above', 100000.0)"""
    if len(args) != 3:
        raise ValueError(
            "Use: /alert BTC above 100000, /alert ETH below 2500 or /alert SOL change 5"
        )
    symbol, kind_raw, value_raw = args
    kind = KINDS.get(kind_raw.lower())
    if kind is None:
        raise ValueError("The condition must be above, below or change")
    value = parse_number(value_raw)
    if kind == "change" and value >= 1000:
        raise ValueError("For change, give a percent, for example 5")
    return symbol.upper(), kind, value


def is_triggered(alert: Alert, price: float) -> bool:
    if alert.kind == "above":
        return price >= alert.value
    if alert.kind == "below":
        return price <= alert.value
    if alert.kind == "change":
        if alert.base_price <= 0:
            return False
        return abs(price - alert.base_price) / alert.base_price * 100 >= alert.value
    return False


def fmt_price(p: float) -> str:
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    if p >= 0.0001:
        return f"${p:.6f}"
    return f"${p:.10f}".rstrip("0")


def fmt_change(pct: float | None) -> str:
    if pct is None:
        return "n/a"
    return f"{pct:+.2f}%"


def describe(alert: Alert) -> str:
    if alert.kind == "change":
        return (
            f"{alert.symbol} moves {alert.value:g}% from {fmt_price(alert.base_price)}"
        )
    return f"{alert.symbol} {alert.kind} {fmt_price(alert.value)}"
