"""Weekly bulletin v2 — personal layer: portfolio, rules, setups, earnings,
positioning, news, scorecard history.

Inputs live in the repo root but are git-ignored (the repo is public):
    portfolio.yaml   positions + cash        (falls back to portfolio.example.yaml)
    rules.yaml       watchlist + rules       (falls back to rules.example.yaml)
    news.yaml        up to five news items   (optional; the section hides without it)
    history/         one JSON per issue, read back by next week's scorecard

Nothing is estimated. A value that cannot be fetched is left out and named in
the page's "missing data" note.
"""
import json
import os
from datetime import date, datetime, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CBOE = "https://cdn.cboe.com/data/us/options/market_statistics/daily/{d}_daily_options"


# ── inputs ──────────────────────────────────────────────────────────────────
def _yaml(path):
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_inputs(root=ROOT):
    """Returns (portfolio, rules, news, example_files)."""
    example = []

    def pick(name):
        real = os.path.join(root, f"{name}.yaml")
        if os.path.exists(real):
            return _yaml(real)
        example.append(f"{name}.yaml")
        return _yaml(os.path.join(root, f"{name}.example.yaml"))

    portfolio, rules = pick("portfolio"), pick("rules")
    news_path = os.path.join(root, "news.yaml")
    news = (_yaml(news_path).get("items") or []) if os.path.exists(news_path) else []
    return portfolio, rules, news[:5], example


def tickers(portfolio, rules):
    pos = [p["ticker"].upper() for p in portfolio.get("positions") or []]
    wl = [w["ticker"].upper() for w in rules.get("watchlist") or []]
    return list(dict.fromkeys(pos + wl))


# ── regime ──────────────────────────────────────────────────────────────────
def regime_state(rules, ndx_above, vxn_above):
    for st in (rules.get("regime") or {}).get("states") or []:
        w = st.get("when") or {}
        if w.get("ndx_above_ma200") == ndx_above and w.get("vxn_above_ma50") == vxn_above:
            return st
    return None


# ── per-company data (yfinance; each piece optional) ────────────────────────
def _session(ts):
    """Yahoo stamps earnings with the US/Eastern time of the release."""
    h = ts.hour + ts.minute / 60
    if h == 0:
        return None
    return "bmo" if h < 9.5 else "amc" if h >= 16 else None


def _mid(row):
    b, a = float(row.get("bid") or 0), float(row.get("ask") or 0)
    return (a + b) / 2 if a > 0 and b > 0 else None


def implied_move(tk, on, spot):
    """ATM straddle on the first expiry on/after the report date, as % of spot."""
    exps = [e for e in (tk.options or []) if date.fromisoformat(e) >= on]
    if not exps:
        return None
    ch = tk.option_chain(exps[0])
    calls, puts = ch.calls, ch.puts
    if calls.empty or puts.empty:
        return None
    k = min(set(calls["strike"]) & set(puts["strike"]), key=lambda x: abs(x - spot), default=None)
    if k is None:
        return None
    c = _mid(calls[calls["strike"] == k].iloc[0])
    p = _mid(puts[puts["strike"] == k].iloc[0])
    if c is None or p is None:
        return None
    return {"pct": (c + p) / spot * 100, "exp": exps[0]}


def company(t, close, cut, today, rules, missing):
    """Everything §01, §02, §05 and §07 need for one ticker."""
    import yfinance as yf
    tk = yf.Ticker(t)
    out = {"t": t}
    sw = rules.get("swing") or {}

    # fundamentals + short interest
    try:
        i = tk.info or {}
        debt, cash, ebitda = i.get("totalDebt"), i.get("totalCash"), i.get("ebitda")
        if debt is not None and cash is not None and ebitda is not None:
            out["nd_ebitda"] = (debt - cash) / ebitda if ebitda > 0 else None
            out["ebitda_neg"] = ebitda <= 0
        else:
            missing.append(f"{t}: net borç / FAVÖK")
        ni, fcf = i.get("netIncomeToCommon"), i.get("freeCashflow")
        if ni is not None and fcf is not None:
            out["profit"], out["fcf"] = ni > 0, fcf > 0
        else:
            missing.append(f"{t}: kâr / serbest nakit akışı")
        if i.get("shortPercentOfFloat") is not None:
            out["short"] = float(i["shortPercentOfFloat"]) * 100
            if i.get("dateShortInterest"):
                out["short_date"] = str(datetime.utcfromtimestamp(i["dateShortInterest"]).date())
        out["name"] = i.get("shortName")
    except Exception:
        missing.append(f"{t}: şirket verisi")

    # analyst actions in the window before the cut
    try:
        ud = tk.upgrades_downgrades
        if ud is not None and not ud.empty:
            days = int(sw.get("analyst_lookback_days", 30))
            idx = pd.to_datetime(ud.index)
            if getattr(idx, "tz", None) is not None:
                idx = idx.tz_localize(None)
            ud = ud.assign(_d=idx)
            ud = ud[(ud["_d"] > pd.Timestamp(cut) - pd.Timedelta(days=days)) & (ud["_d"] <= pd.Timestamp(cut) + pd.Timedelta(days=1))]
            cut_pct = float(sw.get("target_cut_pct", 20))
            bad = []
            for _, r in ud.iterrows():
                if str(r.get("Action", "")).lower() == "down":
                    bad.append(f"{r.get('Firm')}: not indirimi ({r.get('FromGrade')} → {r.get('ToGrade')})")
                pr, cu = r.get("priorPriceTarget") or 0, r.get("currentPriceTarget") or 0
                if pr and cu and (pr - cu) / pr * 100 >= cut_pct:
                    bad.append(f"{r.get('Firm')}: hedef ${pr:.0f} → ${cu:.0f}")
            out["analyst_bad"] = bad
        else:
            out["analyst_bad"] = []
    except Exception:
        missing.append(f"{t}: analist aksiyonları")

    # volume on down days, from the price download
    vol = close.get("vol")
    px = close.get("px")
    if vol is not None and px is not None and len(px) > 30:
        mult = float(sw.get("down_volume_mult", 1.5))
        n = int(sw.get("down_volume_lookback", 5))
        avg20 = vol.shift(1).rolling(20).mean()
        down = px.diff() < 0
        hit = (down & (vol > mult * avg20)).tail(n)
        out["dist_days"] = [str(d.date()) for d, v in hit.items() if v]

    # earnings: next date (any horizon), last week's report
    try:
        ed = tk.earnings_dates
        if ed is not None and not ed.empty:
            rows = []
            for ts, r in ed.iterrows():
                ts = pd.Timestamp(ts)
                if ts.tzinfo is not None:
                    ts = ts.tz_convert("America/New_York")
                rows.append((ts, r))
            nxt = sorted([x for x in rows if x[0].date() >= today], key=lambda x: x[0])
            if nxt:
                ts, r = nxt[0]
                e = {"d": str(ts.date()), "sess": _session(ts)}
                if pd.notna(r.get("EPS Estimate")):
                    e["eps"] = float(r["EPS Estimate"])
                out["next"] = e
            past = [x for x in rows if pd.Timestamp(cut).date() - timedelta(days=7) < x[0].date() <= pd.Timestamp(cut).date()]
            if past:
                ts, r = past[0]
                rep = {"d": str(ts.date()), "sess": _session(ts)}
                if pd.notna(r.get("Surprise(%)")):
                    rep["surprise"] = float(r["Surprise(%)"])
                if px is not None:
                    s = px.dropna()
                    s = s[s.index <= pd.Timestamp(cut)]
                    d = pd.Timestamp(ts.date())
                    before = s[s.index < d]
                    on = s[s.index >= d]
                    if rep["sess"] == "bmo" and len(before) and len(on):
                        rep["react"] = (float(on.iloc[0]) / float(before.iloc[-1]) - 1) * 100
                    elif rep["sess"] == "amc" and len(on) >= 2:
                        rep["react"] = (float(on.iloc[1]) / float(on.iloc[0]) - 1) * 100
                out["reported"] = rep
    except Exception:
        missing.append(f"{t}: bilanço tarihleri")

    # the next 14 days only: estimate revisions and the options' implied move
    nx = out.get("next")
    if nx and date.fromisoformat(nx["d"]) <= today + timedelta(days=14):
        try:
            tr = tk.eps_trend
            if tr is not None and "0q" in tr.index:
                cur, ago = tr.loc["0q"].get("current"), tr.loc["0q"].get("30daysAgo")
                if pd.notna(cur) and pd.notna(ago):
                    nx["rev30"] = "up" if cur > ago else "dn" if cur < ago else "flat"
        except Exception:
            missing.append(f"{t}: EPS revizyonu")
        try:
            spot = float(px.dropna().iloc[-1]) if px is not None else None
            if spot:
                im = implied_move(tk, date.fromisoformat(nx["d"]), spot)
                if im:
                    nx["im"] = im["pct"]
                else:
                    missing.append(f"{t}: opsiyon ima hareketi")
        except Exception:
            missing.append(f"{t}: opsiyon ima hareketi")
    return out


def finnhub_sessions(today, report):
    """Finnhub gives the release session (bmo/amc) when Yahoo has no time."""
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not key:
        return {}
    from weekly_v2.data import _json
    try:
        fh = _json(f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={today + timedelta(days=14)}&token={key}")
        return {(e["symbol"], e["date"]): e.get("hour") for e in fh.get("earningsCalendar", []) if e.get("hour") in ("bmo", "amc")}
    except Exception as e:
        report["warnings"].append(f"finnhub: {e}")
        return {}


def put_call(cut, missing):
    """CBOE daily market statistics: total and equity put/call, the cut day
    and the average of the last 10 sessions that published."""
    from weekly_v2.data import _json
    got, d = [], pd.Timestamp(cut).date()
    tries = 0
    while len(got) < 10 and tries < 20:
        if d.weekday() < 5:
            try:
                j = _json(CBOE.format(d=d))
                r = {x["name"]: float(x["value"]) for x in j.get("ratios", [])}
                if "TOTAL PUT/CALL RATIO" in r and "EQUITY PUT/CALL RATIO" in r:
                    got.append((str(d), r["TOTAL PUT/CALL RATIO"], r["EQUITY PUT/CALL RATIO"]))
            except Exception:
                pass
        d -= timedelta(days=1)
        tries += 1
    if not got:
        missing.append("Put/call oranı (CBOE)")
        return None
    return {"date": got[0][0], "total": got[0][1], "equity": got[0][2],
            "total10": sum(g[1] for g in got) / len(got), "equity10": sum(g[2] for g in got) / len(got), "n": len(got)}


def fetch_personal(portfolio, rules, C, V, cut, today, report):
    missing = []
    names = tickers(portfolio, rules)
    sess = finnhub_sessions(today, report)
    co = {}
    for t in names:
        px = C[t] if t in C.columns else None
        vol = V[t] if t in V.columns else None
        if px is not None:
            px = px[px.index <= pd.Timestamp(cut)]
        if vol is not None:
            vol = vol[vol.index <= pd.Timestamp(cut)]
        co[t] = company(t, {"px": px, "vol": vol}, cut, today, rules, missing)
        nx = co[t].get("next")
        if nx and not nx.get("sess") and (t, nx["d"]) in sess:
            nx["sess"] = sess[(t, nx["d"])]
    return {"co": co, "pc": put_call(cut, missing), "missing": missing}


# ── scorecard history ───────────────────────────────────────────────────────
def history_dir(root=ROOT):
    return os.path.join(root, "history")


def save_issue(cut, rows, root=ROOT):
    os.makedirs(history_dir(root), exist_ok=True)
    with open(os.path.join(history_dir(root), f"{cut}.json"), "w", encoding="utf-8") as fh:
        json.dump({"cut": cut, "rows": rows}, fh, ensure_ascii=False, indent=2)


def previous_issue(cut, root=ROOT):
    d = history_dir(root)
    if not os.path.isdir(d):
        return None
    files = sorted(f for f in os.listdir(d) if f.endswith(".json") and f[:-5] < cut)
    if not files:
        return None
    with open(os.path.join(d, files[-1]), encoding="utf-8") as fh:
        return json.load(fh)
