"""Offline tests for weekly v2: rules, formatting, missing data, email safety.

    python -m unittest weekly_v2.test_weekly_v2
"""
import os
import re
import unittest
from unittest.mock import patch

from weekly_v2 import mail as M, render as R


def series(start, step, n=53):
    # a trend with some wiggle, so weekly moves have a realistic spread
    return [start + step * i + (step * 3 if i % 2 else -step * 3) for i in range(n)]


def asset(last, w=1.0, m=2.0, ytd=5.0, ma50=None, ma200=None, lo=None, hi=None, s=None, prev=None):
    s = s or series(last * .8, last * .2 / 52)
    return {"since": None, "last": last, "date": "2026-11-13", "w": w, "m": m, "ytd": ytd,
            "ma50": ma50 if ma50 is not None else last * .97, "ma200": ma200 if ma200 is not None else last * .9,
            "hi52": hi if hi is not None else last * 1.02, "lo52": lo if lo is not None else last * .7, "series": s,
            "d5": [.1, -.2, .3, -.1, .2], "d5dates": ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"],
            "prev": prev or {"last": last * .99, "ma50": last * .97, "ma200": last * .9}}


def rate(last, w_bp, m_bp=10.0):
    a = asset(last, s=series(last - .5, .01))
    a.update({"w_bp": w_bp, "m_bp": m_bp})
    return a


def base():
    A = {k: asset(100.0) for k in ("ndx", "spx", "gold", "silver", "dxy", "sox", "nvda", "vxn", "btc")}
    A.update({"us2y": rate(4.0, 5), "us10y": rate(4.5, 10), "real10": rate(2.0, 7), "be10": rate(2.5, 3)})
    return {"asof": "2026-11-13", "today": "2026-11-15", "a": A, "corr": {"gold_dxy": -.5}, "vol": {},
            "baskets": {}, "calendar": [], "fed": None, "fg": None, "earn": []}


class Formatting(unittest.TestCase):
    def test_tr_and_en_numbers(self):
        tr, en = R.F("tr"), R.F("en")
        self.assertEqual(tr.num(1234.5), "1.234,50")
        self.assertEqual(en.num(1234.5), "1,234.50")
        self.assertEqual(tr.pct(-3.456), "−%3,46")
        self.assertEqual(en.pct(3.456), "+3.46%")
        self.assertEqual(tr.pct(0.001), "%0,00")       # no sign on a rounded zero
        self.assertEqual(en.bp(-21.6), "−22bp")

    def test_long_dates(self):
        self.assertEqual(R.F("tr").long_date("2026-12-09"), "9 Ara 2026")
        self.assertEqual(R.F("en").long_date("2026-12-09"), "Dec 9, 2026")


class Rules(unittest.TestCase):
    def test_regime(self):
        self.assertEqual(R.regime(10, 9, 8), "up")
        self.assertEqual(R.regime(7, 9, 8), "dn")
        self.assertEqual(R.regime(8.5, 9, 8), "mix")
        self.assertEqual(R.regime(8.5, 9, None), "mix")

    def test_headline_picks_the_unusual_move(self):
        d = base()
        d["a"]["silver"]["w"] = -15.0          # far beyond its usual weekly move
        self.assertEqual(R.Bulletin(d, "en").headline()["k"], "silver")

    def test_breakeven_split_adds_up(self):
        d = base()
        html = R.render(d, "en")
        self.assertIn("+7bp is real yield", html)
        self.assertIn("+3bp breakeven", html)

    def test_scorecard_never_claims_a_prior_call(self):
        d = base()
        d["a"]["ndx"]["prev"] = {"last": 80.0, "ma50": 97.0, "ma200": 90.0}   # was down, now up
        b = R.Bulletin(d, "tr")
        html = b.scorecard()
        self.assertNotIn("dedik", html)
        self.assertIn("aşağıydı; bu hafta yukarı", html)

    def test_tr_past_tense_suffix(self):
        d = base()
        d["a"]["gold"].update({"last": 95.0, "ma50": 97.0, "ma200": 90.0})
        d["a"]["gold"]["prev"] = {"last": 95.0, "ma50": 97.0, "ma200": 90.0}
        self.assertIn("kararsızdı", R.Bulletin(d, "tr").scorecard())


class MissingData(unittest.TestCase):
    def test_missing_blocks_are_left_out_not_guessed(self):
        d = base()
        html = R.render(d, "tr")
        for absent in ("H100", "KOSPI", "Optik", "Bakır / altın"):
            self.assertNotIn(absent, html)
        self.assertIsNone(re.search(r"\bnan\b", html, re.I))
        self.assertNotIn("None", html)

    def test_empty_inputs_still_render(self):
        d = base()
        d["a"] = {}
        d["corr"] = {}
        html = R.render(d, "en")
        self.assertIn("NO<b>/</b>CASHFLOW", html)

    def test_gate(self):
        from datetime import date
        from weekly_v2 import run
        d = base()
        self.assertEqual(run.gate(d, {}, date(2026, 11, 15)), [])
        self.assertTrue(run.gate(d, {}, date(2026, 11, 25)))          # stale
        del d["a"]["gold"]
        self.assertTrue(run.gate(d, {}, date(2026, 11, 15)))          # core missing


class EmailSafety(unittest.TestCase):
    def test_email_has_unsubscribe_placeholder(self):
        t = R.teaser(base(), "tr")
        body = M.build(t, "tr", "https://nocashflow.net/x", "2026-11-15")
        self.assertIn("{{UNSUB_URL}}", body)
        self.assertIn("15 Kas 2026", body)

    def test_refuses_body_without_unsubscribe(self):
        import email_sender
        with patch.dict(os.environ, {"RESEND_API_KEY": "x", "TEST_TO": ""}):
            self.assertFalse(email_sender.send_to_subscribers("<p>no link</p>", "s", "tr"))

    def test_test_mode_skips_subscriber_api_and_hides_address(self):
        import email_sender
        sent = []

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"id": "1"}'

        def fake_open(req, *a, **k):
            sent.append(req)
            return Resp()

        with patch.dict(os.environ, {"RESEND_API_KEY": "x", "TEST_TO": "someone@example.com"}), \
                patch.object(email_sender, "fetch_confirmed_subscribers", side_effect=AssertionError("must not call")), \
                patch("urllib.request.urlopen", fake_open), \
                patch("builtins.print") as pr:
            ok = email_sender.send_to_subscribers("<a href='{{UNSUB_URL}}'>u</a>", "Subj", "en")
        self.assertTrue(ok)
        self.assertEqual(len(sent), 1)
        logged = " ".join(str(c) for c in pr.call_args_list)
        self.assertNotIn("someone@example.com", logged)


if __name__ == "__main__":
    unittest.main()
