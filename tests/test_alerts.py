import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alerts import Alert, describe, fmt_price, is_triggered, parse_alert_args, parse_number  # noqa: E402
from links import chart_url  # noqa: E402
from storage import Storage  # noqa: E402


def alert(kind, value, base=100.0):
    return Alert(1, 42, "bitcoin", "BTC", kind, value, base)


class ParseTest(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(parse_number("100000"), 100000)
        self.assertEqual(parse_number("100,000"), 100000)
        self.assertEqual(parse_number("$65k"), 65000)
        self.assertEqual(parse_number("1.5m"), 1_500_000)
        self.assertEqual(parse_number("5%"), 5)
        for bad in ("abc", "0", "-5", ""):
            with self.assertRaises(ValueError):
                parse_number(bad)

    def test_alert_args(self):
        self.assertEqual(parse_alert_args(["btc", "above", "100k"]), ("BTC", "above", 100000))
        self.assertEqual(parse_alert_args(["eth", "<", "2500"]), ("ETH", "below", 2500))
        self.assertEqual(parse_alert_args(["sol", "change", "5%"]), ("SOL", "change", 5))
        with self.assertRaises(ValueError):
            parse_alert_args(["btc", "sideways", "1"])
        with self.assertRaises(ValueError):
            parse_alert_args(["btc", "above"])
        with self.assertRaises(ValueError):
            parse_alert_args(["btc", "change", "5000"])


class TriggerTest(unittest.TestCase):
    def test_above_below(self):
        self.assertTrue(is_triggered(alert("above", 100), 100))
        self.assertFalse(is_triggered(alert("above", 100), 99.9))
        self.assertTrue(is_triggered(alert("below", 100), 99))
        self.assertFalse(is_triggered(alert("below", 100), 101))

    def test_change_both_directions(self):
        self.assertTrue(is_triggered(alert("change", 5, base=100), 105))
        self.assertTrue(is_triggered(alert("change", 5, base=100), 95))
        self.assertFalse(is_triggered(alert("change", 5, base=100), 104))


class FormatTest(unittest.TestCase):
    def test_prices(self):
        self.assertEqual(fmt_price(65432.1), "$65,432.10")
        self.assertEqual(fmt_price(0.5), "$0.5000")
        self.assertEqual(fmt_price(0.00123), "$0.001230")
        self.assertEqual(fmt_price(0.0000123), "$0.0000123")

    def test_describe(self):
        self.assertEqual(describe(alert("above", 100000)), "BTC above $100,000.00")
        self.assertEqual(describe(alert("change", 5, base=100)), "BTC moves 5% from $100.00")


class LinksTest(unittest.TestCase):
    def test_known_and_unknown(self):
        self.assertTrue(chart_url("bitcoin").startswith(
            "https://token-alphabet.com/cryptocurrencies/bitcoin-btc-price?"))
        self.assertTrue(chart_url("no-such-coin").startswith(
            "https://token-alphabet.com/cryptocurrencies?"))
        self.assertTrue(chart_url("dogecoin").startswith(
            "https://tokenalphabet.com/cryptocurrencies/dogecoin-doge-price?"))


class StorageTest(unittest.TestCase):
    def test_crud(self):
        s = Storage(":memory:")
        a = s.add(1, "bitcoin", "BTC", "above", 100000, 90000)
        s.add(1, "ethereum", "ETH", "below", 2000, 3000)
        s.add(2, "solana", "SOL", "change", 5, 150)
        self.assertEqual(s.count_for_chat(1), 2)
        self.assertEqual(s.for_chat(1)[0].coin_id, "bitcoin")
        self.assertFalse(s.delete(2, a))  # other chat cannot delete it
        self.assertTrue(s.delete(1, a))
        self.assertEqual(s.clear(1), 1)
        self.assertEqual(len(s.all()), 1)


if __name__ == "__main__":
    unittest.main()
