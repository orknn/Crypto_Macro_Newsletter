"""Offline tests for the weekly v2 personal edition.

    python -m unittest weekly_v2.test_weekly_v2
"""
import glob
import html as H
import json
import os
import re
import tempfile
import unittest
from datetime import date

import numpy as np
import pandas as pd

from weekly_v2 import data as D, personal as P, render as R

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CUT = "2026-11-13"


# ── fixtures ────────────────────────────────────────────────────────────────
def daily(seed, start=100.0, n=520, end="2026-11-16", drift=0.0, vol=0.02, bdays=True):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=end, periods=n) if bdays else pd.date_range(end=end, periods=n)
    r = rng.normal(drift, vol, n)
    return pd.Series(start * np.cumprod(1 + r), index=idx)


def asset(last, w=1.0, m=2.0, q=3.0, ytd=5.0, ma50=None, ma200=None, lo=None, hi=None, week=None, prev=None):
    s = [last * (.8 + .2 * i / 52) for i in range(53)]
    return {"since": None, "last": last, "date": CUT, "w": w, "m": m, "q": q, "ytd": ytd,
            "ma50": ma50 if ma50 is not None else last * .97, "ma200": ma200 if ma200 is not None else last * .9,
            "hi52": hi if hi is not None else last * 1.02, "lo52": lo if lo is not None else last * .7, "series": s,
            "d5": [.1, -.2, .3, -.1, .2], "d5dates": ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", CUT],
            "week": week or [["2026-11-09", last], [CUT, last]],
            "prev": prev or {"last": last * .99, "ma50": last * .97, "ma200": last * .9}}


def rate(last, w_bp, m_bp=10.0):
    a = asset(last)
    a.update({"w_bp": w_bp, "m_bp": m_bp, "q_bp": 20.0, "ytd_bp": 30.0, "d200_bp": 15.0, "w": None, "m": None})
    return a


def basket(w, m, q=-10.0, members=("AAA", "BBB")):
    a = asset(100.0, w=w, m=m, q=q)
    a.update({"members": list(members), "missing_members": []})
    return a


RULES = {
    "watchlist": [{"ticker": "AAA", "buy_at": 96.0, "basket": "swing"}, {"ticker": "BBB", "basket": "spekulatif"}],
    "swing": {"down_volume_mult": 1.5, "down_volume_lookback": 5, "max_net_debt_ebitda": 3.0,
              "analyst_lookback_days": 30, "target_cut_pct": 20},
    "this_week": {"stop_within_pct": 10, "buy_within_pct": 5, "stop_highlight_pct": 5},
    "regime": {"states": [
        {"when": {"ndx_above_ma200": True, "vxn_above_ma50": False}, "label": "Risk açık", "max_equity_pct": 90},
        {"when": {"ndx_above_ma200": True, "vxn_above_ma50": True}, "label": "Temkinli", "max_equity_pct": 70},
        {"when": {"ndx_above_ma200": False, "vxn_above_ma50": False}, "label": "Savunma", "max_equity_pct": 50},
        {"when": {"ndx_above_ma200": False, "vxn_above_ma50": True}, "label": "Risk kapalı", "max_equity_pct": 30}]},
    "show_metals": "compact",
}
PORTFOLIO = {"cash": 1000, "positions": [{"ticker": "AAA", "shares": 10, "cost": 90.0, "stop": 97.0, "basket": "core"}]}


def base():
    A = {k: asset(100.0) for k in ("ndx", "spx", "gold", "silver", "dxy", "sox", "nvda", "btc", "aaa", "bbb", "copper")}
    A["vxn"] = asset(20.0, ma50=22.0)
    A["gsr"] = asset(80.0, m=3.0)
    A["h100"] = asset(3.3)
    A.update({"us2y": rate(4.0, 5), "us10y": rate(4.5, 10), "real10": rate(2.0, 7), "be10": rate(2.5, 3), "hy": rate(3.2, -4)})
    A["neocloud"] = basket(-2.0, -5.0)
    A["memory"] = basket(4.0, -20.0)
    co = {"AAA": {"t": "AAA", "nd_ebitda": 1.0, "profit": True, "fcf": True, "analyst_bad": [], "dist_days": [], "short": 3.4,
                  "next": {"d": "2026-11-18", "sess": "amc", "eps": 1.23, "rev30": "up", "im": 7.5}},
          "BBB": {"t": "BBB", "nd_ebitda": None, "ebitda_neg": True, "profit": False, "fcf": False, "analyst_bad": ["X: hedef $100 → $50"],
                  "dist_days": ["2026-11-12"], "reported": {"d": "2026-11-11", "sess": "bmo", "surprise": 12.0, "react": -4.0}}}
    return {"asof": CUT, "cut": CUT, "today": "2026-11-16", "a": A,
            "corr": {"gold_real": -.23, "gold_dxy": -.5, "ndx_10y": .1}, "vol": {"qqq": 1.1},
            "calendar": [], "fed": {"date": "2026-12-09", "p": 2.0}, "fg": None,
            "personal": {"co": co, "pc": {"date": CUT, "total": .85, "equity": .63, "total10": .9, "equity10": .65, "n": 10}, "missing": []},
            "rules": RULES, "portfolio": PORTFOLIO, "news": [], "example_files": [], "prev_issue": None}


def page(d):
    return R.render(d)[0]


def visible_text(html):
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<svg.*?</svg>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    txt = H.unescape(html)
    # day labels like "Çar 18.11" are dates, not decimals
    return re.sub(r"(Pzt|Sal|Çar|Per|Cum|Cmt|Paz) \d{2}\.\d{2}", "DATE", txt)


def assert_clean(tc, html):
    txt = visible_text(html)
    for bad in (r"\bN/?A\b", r"\bnan\b", r"\bNone\b", r"\binf\b", r"\bnull\b"):
        tc.assertIsNone(re.search(bad, txt, re.I), f"found {bad}")
    # raw floats: a dot-decimal (TR uses comma; a dot only groups thousands in 3s)
    m = re.search(r"\d\.\d{1,2}(?!\d)|\d\.\d{4,}|,\d{3,}(?![\d.])", txt)
    tc.assertIsNone(m, f"raw float: {m and txt[max(0, m.start() - 30):m.end() + 30]}")
    # zero is never signed or coloured
    tc.assertIsNone(re.search(r"[+−]%0(,0+)?(?!\d|,\d*[1-9])", txt), "signed zero")
    for cls, inner in re.findall(r'<span class="(up|dn)">([^<]*)</span>', html):
        tc.assertFalse(re.fullmatch(r"\s*%0(,0+)?\s*\w*\s*|\s*0bp\s*\w*\s*", inner), f"coloured zero: {inner}")


# ── 1. baskets ──────────────────────────────────────────────────────────────
class Baskets(unittest.TestCase):
    def test_basket_windows_are_member_averages(self):
        C = pd.DataFrame({"A": daily(1, drift=.004), "B": daily(2, drift=-.002), "C": daily(3, vol=.05),
                          "D": daily(4).where(lambda s: s.index > "2025-07-01")})
        b = D.basket_stats(C, ["A", "B", "C", "D"], date(2026, 11, 13))
        mem = {t: D.stats(C[t], date(2026, 11, 13)) for t in "ABCD"}
        for k in ("w", "m", "q"):
            self.assertAlmostEqual(b[k], sum(mem[t][k] for t in "ABCD") / 4, places=9)
        self.assertEqual(b["members"], ["A", "B", "C", "D"])

    def test_old_drifted_index_would_not_add_up(self):
        # the bug: rebase to 100 two years ago and never rebalance → weights drift
        C = pd.DataFrame({"A": daily(1, drift=.006), "B": daily(2, drift=-.003)})
        drift = (C / C.iloc[0]).mean(axis=1)
        drift = drift[drift.index <= "2026-11-13"]
        old_w = (drift.iloc[-1] / drift[drift.index <= "2026-11-06"].iloc[-1] - 1) * 100
        new_w = D.basket_stats(C, ["A", "B"], date(2026, 11, 13))["w"]
        self.assertGreater(abs(old_w - new_w), 0.01)

    def test_card_lists_exactly_the_members_in_the_average(self):
        d = base()
        html = page(d)
        chain = html[html.index("AI değer"):html.index("Finansman")]
        for t in d["a"]["neocloud"]["members"]:
            self.assertIn(R.NAMES.get(t, t), chain)

    def test_member_without_data_is_left_out_and_named(self):
        C = pd.DataFrame({"A": daily(1), "B": daily(2), "Z": pd.Series(np.nan, index=daily(3).index)})
        b = D.basket_stats(C, ["A", "B", "Z"], date(2026, 11, 13))
        self.assertEqual(b["members"], ["A", "B"])
        self.assertEqual(b["missing_members"], ["Z"])


# ── 2. single cut ───────────────────────────────────────────────────────────
class SingleCut(unittest.TestCase):
    def test_latest_completed_close(self):
        self.assertEqual(D.last_close(date(2026, 11, 17), 15), date(2026, 11, 16))   # Tuesday, market open
        self.assertEqual(D.last_close(date(2026, 11, 17), 22), date(2026, 11, 17))   # Tuesday, after close
        self.assertEqual(D.last_close(date(2026, 11, 16), 10), date(2026, 11, 13))   # Monday morning → Friday
        self.assertEqual(D.last_close(date(2026, 11, 15), 22), date(2026, 11, 13))   # Sunday

    def test_last_completed_friday(self):
        self.assertEqual(D.last_friday(date(2026, 11, 16)), date(2026, 11, 13))      # Monday
        self.assertEqual(D.last_friday(date(2026, 11, 15)), date(2026, 11, 13))      # Sunday
        self.assertEqual(D.last_friday(date(2026, 11, 13), 15), date(2026, 11, 6))   # Friday, market open
        self.assertEqual(D.last_friday(date(2026, 11, 13), 22), date(2026, 11, 13))  # Friday, after close

    def test_every_series_stops_at_the_cut(self):
        cut = date(2026, 11, 13)
        nasdaq = daily(1)                                  # weekdays to Monday 16th
        gold = daily(2)                                    # futures: also trades Monday
        btc = daily(3, bdays=False)                        # 7 days a week
        for s in (nasdaq, gold, btc):
            st = D.stats(s, cut)
            self.assertEqual(st["date"], "2026-11-13")
            self.assertEqual(st["d5dates"][-1], "2026-11-13")
            self.assertTrue(all(dd <= "2026-11-13" for dd, _ in st["week"]))
            prev = s[s.index <= "2026-11-06"].iloc[-1]
            self.assertAlmostEqual(st["w"], (s[s.index <= "2026-11-13"].iloc[-1] / prev - 1) * 100)

    def test_ytd_is_against_prior_year_close(self):
        s = daily(5)
        st = D.stats(s, date(2026, 11, 13))
        y0 = s[s.index <= "2025-12-31"].iloc[-1]
        self.assertAlmostEqual(st["ytd"], (s[s.index <= "2026-11-13"].iloc[-1] / y0 - 1) * 100)

    def test_cut_date_is_printed_on_top(self):
        self.assertIn("kesim: 13 Kas 2026 Cuma kapanışı", page(base()))

    def test_saved_fetch_has_one_cut(self):
        files = sorted(glob.glob(os.path.join(ROOT, "personal_out", "data_*.json")))
        if not files:
            self.skipTest("no saved fetch")
        d = json.load(open(files[-1]))
        for k, a in d["a"].items():
            self.assertLessEqual(a["date"], d["cut"], k)


# ── 3–7. wording rules ──────────────────────────────────────────────────────
class Wording(unittest.TestCase):
    def test_no_causal_line_when_correlation_does_not_back_it(self):
        d = base()
        d["a"]["real10"].update({"w_bp": 22, "m_bp": -2})
        d["a"]["gold"]["w"] = -4.0
        d["a"]["silver"]["w"] = -5.0
        html = page(d)
        self.assertNotIn("affetmiyor", html)
        self.assertNotIn("ilişki bu hafta çalıştı", html)   # corr −0.23 < 0.3

    def test_causal_line_when_change_and_correlation_agree(self):
        d = base()
        d["a"]["real10"]["w_bp"] = 22
        d["a"]["gold"]["w"] = -4.0
        d["corr"]["gold_real"] = -.55
        self.assertIn("ilişki bu hafta çalıştı", page(d))

    def test_no_flow_language_and_rebound_label(self):
        d = base()
        html = page(d)
        self.assertNotIn("aktı", html)
        self.assertIn("tepki", html[html.index("AI değer"):html.index("Finansman")])   # memory: +4 1W, −20 1M

    def test_h100_out_of_top_five_and_no_demand_verdict(self):
        b = R.Bulletin(base())
        self.assertFalse(any("H100" in x[0] for x in b.key5()))
        html = page(base())
        self.assertIn("Düşük güvenilirlik", html)
        self.assertNotIn("talep", html.lower().replace("talepte", "talep"))

    def test_metals_contradiction_is_named_in_full_mode(self):
        d = base()
        d["rules"] = {**RULES, "show_metals": "full"}
        d["a"]["cu_au"] = asset(1.5, m=4.0)
        d["a"]["gsr"]["m"] = 3.0
        html = page(d)
        self.assertIn("Çelişki", html)
        self.assertNotIn("büyüme fiyatlıyor", html)

    def test_compact_metals_is_one_card(self):
        html = page(base())
        self.assertIn("Metaller · tek kart", html)
        self.assertNotIn("Metallerin", html)

    def test_zero_is_bare(self):
        f = R.F("tr")
        self.assertEqual(f.pct(0.04), "%0,0")
        self.assertEqual(f.pct(-0.3, 0), "%0")
        self.assertEqual(R.dc(0.04), "")
        self.assertEqual(f.bp(0.4), "0bp")

    def test_thresholds_are_never_the_current_price(self):
        d = base()
        b = R.Bulletin(d)
        b.render()
        for r in b.week_rows:
            self.assertNotAlmostEqual(r["level"], d["a"][r["key"]]["last"])


# ── §01 decision page ───────────────────────────────────────────────────────
class Decision(unittest.TestCase):
    def test_regime_and_ratio_side_by_side(self):
        html = page(base())                         # ndx above MA200, vxn below MA50 → Risk açık 90
        self.assertIn("Risk açık", html)
        self.assertIn("%90", html)
        self.assertIn("Mevcut hisse oranı", html)

    def test_stop_close_is_highlighted_and_listed(self):
        html = page(base())                         # AAA 100 vs stop 97 → 3%
        self.assertIn('class="warn"', html)
        self.assertIn("<b>$97,00</b> altında kapanırsa stop çalışır", html)

    def test_buy_level_row(self):
        self.assertIn("alım seviyesine (<b>$96,00</b>) %4,2 mesafede", page(base()))

    def test_setup_rows_sorted_by_passes(self):
        html = page(base())
        sec = html[html.index("Kurulum"):html.index("AI değer")]
        self.assertLess(sec.index("AAA"), sec.index("BBB"))
        self.assertIn("nakit yakıyor", page(dict(base(), rules={**RULES, "watchlist": [{"ticker": "BBB", "basket": "swing"}]})))


# ── missing data ────────────────────────────────────────────────────────────
class MissingData(unittest.TestCase):
    def test_full_page_is_clean(self):
        assert_clean(self, page(base()))

    def test_missing_series_are_left_out_and_listed(self):
        d = base()
        for k in ("hy", "h100", "memory", "vxn"):
            del d["a"][k]
        d["personal"]["pc"] = None
        d["personal"]["co"]["AAA"].pop("next")
        html = page(d)
        assert_clean(self, html)
        self.assertNotIn("H100", html)
        self.assertIn("Eksik veri", html)
        self.assertIn("HY kredi makası", html[html.index("Eksik veri"):])
        self.assertIn("AAA: sıradaki bilanço tarihi", html)

    def test_empty_inputs_still_render(self):
        d = base()
        d["a"], d["corr"], d["personal"] = {}, {}, {}
        d["portfolio"], d["rules"] = {}, {}
        html = page(d)
        self.assertIn("NO<b>/</b>CASHFLOW", html)
        assert_clean(self, html)

    def test_real_saved_fetch_renders_clean(self):
        files = sorted(glob.glob(os.path.join(ROOT, "personal_out", "data_*.json")))
        if not files:
            self.skipTest("no saved fetch")
        d = json.load(open(files[-1]))
        pf, rl, news, ex = P.load_inputs(ROOT)
        d.update({"portfolio": pf, "rules": rl, "news": news, "example_files": ex, "prev_issue": None})
        assert_clean(self, page(d))


# ── English edition ─────────────────────────────────────────────────────────
class English(unittest.TestCase):
    def en(self, d):
        return visible_text(R.render(d, lang="en")[0])

    def test_no_turkish_left_and_no_raw_values(self):
        d = base()
        d["prev_issue"] = {"cut": "2026-11-06", "rows": [{"kind": "stop", "key": "aaa", "level": 97.0, "dir": "below", "text": "AAA $97,00 altında kapanırsa stop çalışır", "text_en": "AAA closes below $97.00: stop triggers"}]}
        d["personal"]["missing"] = ["AAA: EPS revizyonu", "Put/call oranı (CBOE)"]
        txt = re.sub(r"\s+", " ", self.en(d))
        self.assertIsNone(re.search(r"[çğışöüÇĞİŞÖÜ]", txt), re.findall(r"\S*[çğışöüÇĞİŞÖÜ]\S*", txt))
        for bad in (r"\bN/?A\b", r"\bnan\b", r"\bNone\b", r"\binf\b", r"\bnull\b", r"\bpuan\b", r"%\d"):
            self.assertIsNone(re.search(bad, txt), bad)
        self.assertIn("If AAA closes below $97.00, the stop triggers", txt.replace(" ,", ",").replace("  ", " "))
        self.assertIn("AAA closes below $97.00: stop triggers", txt)       # scorecard row in English

    def test_same_rules_both_languages(self):
        tr_rows = R.render(base(), lang="tr")[1]
        en_rows = R.render(base(), lang="en")[1]
        self.assertEqual(tr_rows, en_rows)       # history stays in one language

    def test_rebound_label(self):
        self.assertIn("rebound", self.en(base()))


# ── editor's read (no network: the model call is stubbed) ───────────────────
class Editor(unittest.TestCase):
    def setUp(self):
        from weekly_v2 import editor as E
        self.E = E
        self.tr, self.en = R.render(base(), lang="tr")[0], R.render(base(), lang="en")[0]
        self.ttr, self.ten = E.page_text(self.tr), E.page_text(self.en)

    def test_page_numbers_pass_invented_numbers_fail(self):
        ok = "AAA stop seviyesine %3,1 uzakta; rejim sınırı %90, mevcut hisse oranı %50,0. Bellek sepeti 1M −%20,0 sonrası tepki."
        self.assertEqual(self.E.check(ok, self.ttr, "tr"), [])
        bad = "AAA stop seviyesine %3,7 uzakta ve rejim sınırı %90 seviyesinde, haftanın en önemli koşulu bu."
        self.assertTrue(any("3,7" in p for p in self.E.check(bad, self.ttr, "tr")))

    def test_number_format_is_per_language(self):
        self.assertEqual(self.E.check("AAA is 3.1% from its stop; the regime limit is 90% and equity share 50.0% for now.", self.ten, "en"), [])
        self.assertTrue(self.E.check("AAA stop seviyesine %3.1 uzakta; rejim sınırı %90 ve hisse oranı %50,0 düzeyinde.", self.ttr, "tr"))

    def test_flow_and_advice_wording_rejected(self):
        self.assertTrue(self.E.check("Bellek sepetine para aktı; rejim sınırı %90 olduğu için AAA alınmalı ve tutulmalı.", self.ttr, "tr"))
        self.assertTrue(self.E.check("Investors should buy AAA here because the regime limit is 90% and equity share 50.0%.", self.ten, "en"))

    def test_cash_and_total_never_sent(self):
        self.assertNotIn("$1.000", self.ttr)
        self.assertNotIn("$2,000", self.ten)

    def test_retry_then_print(self):
        drafts = iter([({"tr": "Bellek sepetine para aktı, rejim sınırı %90 ve hisse oranı %50,0.", "en": "Money flowed into memory, limit 90% and share 50.0%."},
                        {"model": "m", "usd": 0.01}),
                       ({"tr": "AAA stop seviyesine %3,1 uzakta; rejim sınırı %90, mevcut hisse oranı %50,0.",
                         "en": "AAA is 3.1% from its stop; the regime limit is 90% against an equity share of 50.0%."}, {"model": "m", "usd": 0.01})])
        ed = self.E.write(self.tr, self.en, call=lambda p: next(drafts))
        self.assertIsNotNone(ed["tr"])
        self.assertEqual(len(ed["usage"]), 2)
        d = base()
        d["editor"] = ed
        self.assertIn("Editörün okuması", page(d))
        self.assertIn("Editor’s read", R.render(d, lang="en")[0])
        assert_clean(self, page(d))

    def test_two_failures_print_nothing(self):
        bad = ({"tr": "Para aktı, %99 ile.", "en": "Money flowed, 99%."}, {"model": "m", "usd": 0.0})
        ed = self.E.write(self.tr, self.en, call=lambda p: bad)
        self.assertIsNone(ed["tr"])
        d = base()
        d["editor"] = ed
        html = page(d)
        self.assertNotIn("Editörün okuması ·", html.split("Eksik veri")[0])
        self.assertIn("denetimden geçmedi", html)


# ── §11 scorecard ───────────────────────────────────────────────────────────
class Scorecard(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            P.save_issue("2026-11-06", [{"kind": "stop", "key": "aaa", "level": 97.0, "dir": "below", "text": "AAA $97 stop"},
                                        {"kind": "level", "key": "ndx", "level": 90.0, "dir": "below", "text": "NDX MA200"}], tmp)
            prev = P.previous_issue(CUT, tmp)
            self.assertEqual(prev["cut"], "2026-11-06")
            d = base()
            d["a"]["aaa"]["week"] = [["2026-11-09", 99.0], ["2026-11-11", 96.5], [CUT, 100.0]]
            d["prev_issue"] = prev
            html = page(d)
            sec = html[html.index("karnesi"):]
            self.assertIn("tutmadı", sec)          # AAA closed 96.50 < 97
            self.assertIn("tuttu", sec)            # NDX never below 90
            self.assertIn("Çar 11.11", sec)

    def test_first_issue_has_no_scorecard(self):
        html = page(base())
        self.assertNotIn("karnesi", html.split("Eksik veri")[0])
        self.assertIn("Karne: önceki sayı yok", html)


class Inputs(unittest.TestCase):
    def test_example_files_load_and_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in ("portfolio", "rules"):
                with open(os.path.join(ROOT, f"{n}.example.yaml")) as src, open(os.path.join(tmp, f"{n}.example.yaml"), "w") as dst:
                    dst.write(src.read())
            pf, rl, news, ex = P.load_inputs(tmp)
            self.assertEqual(ex, ["portfolio.yaml", "rules.yaml"])
            self.assertTrue(pf["positions"])
            self.assertEqual(rl["show_metals"], "compact")
            self.assertEqual(len(rl["regime"]["states"]), 4)
            d = base()
            d["example_files"] = ex
            self.assertIn("Örnek veriyle üretildi", page(d))

    def test_personal_files_are_git_ignored(self):
        gi = open(os.path.join(ROOT, ".gitignore")).read().split()
        for f in ("portfolio.yaml", "rules.yaml", "news.yaml", "history/", "personal_out/"):
            self.assertIn(f, gi)


if __name__ == "__main__":
    unittest.main()
