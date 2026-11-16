"""Weekly bulletin v2 — data layer.

Every number in the bulletin comes from here. Nothing is estimated or filled
in: a series that fails to load is simply absent, and the renderer shows "—"
or hides the block. Sources: Yahoo Finance (yfinance), FRED CSV, OKX and Bitget
public market APIs (GPU rental perpetuals) and nocashflow.net's own data
files (calendar, Fed odds, F&G). Every series is cut at the same point: the
last completed Friday close. Company-level data (fundamentals, earnings,
options, analyst actions) lives in personal.py.
"""
import io
import json
import os
import urllib.request
import warnings
from datetime import date, datetime, timedelta

import pandas as pd

warnings.filterwarnings("ignore")

SITE_DATA = os.environ.get("NCF_SITE_DATA", "https://nocashflow.net/data")
UA = {"User-Agent": "Mozilla/5.0 (NoCashFlow-Bulletin)"}

# key -> Yahoo ticker
TICKERS = {
    # board
    "ndx": "^NDX", "spx": "^GSPC", "rut": "^RUT", "sox": "^SOX",
    "gold": "GC=F", "silver": "SI=F", "plat": "PL=F", "copper": "HG=F", "brent": "BZ=F",
    "dxy": "DX-Y.NYB", "vix": "^VIX", "vxn": "^VXN", "btc": "BTC-USD",
    # breadth + giants
    "qqq": "QQQ", "qqqe": "QQQE",
    "aapl": "AAPL", "msft": "MSFT", "nvda": "NVDA", "googl": "GOOGL", "amzn": "AMZN", "meta": "META", "tsla": "TSLA",
    # metals inside
    "gdx": "GDX", "sil": "SIL", "gld": "GLD", "slv": "SLV",
    # sector ETFs + the owner's watchlist names
    "smh": "SMH", "igv": "IGV", "nasa": "NASA",
    "amd": "AMD", "avgo": "AVGO", "now": "NOW", "crwd": "CRWD", "panw": "PANW",
    "spcx": "SPCX", "rklb": "RKLB", "asts": "ASTS", "fly": "FLY",
    "crdo": "CRDO", "alab": "ALAB", "lite": "LITE", "aaoi": "AAOI",
    # Asia chip axis
    "kospi": "^KS11", "n225": "^N225", "twii": "^TWII", "usdjpy": "JPY=X",
    # AI value chain
    "crwv": "CRWV", "nbis": "NBIS", "iren": "IREN", "apld": "APLD",
    "mu": "MU", "sndk": "SNDK", "skhy": "SKHY",
    "gev": "GEV", "be": "BE", "ceg": "CEG", "oklo": "OKLO",
}

# equal-weight baskets, rebased to 100
BASKETS = {
    "optics": ["CRDO", "ALAB", "LITE", "AAOI"],
    "neocloud": ["CRWV", "NBIS", "IREN", "APLD"],
    "memory": ["MU", "SNDK", "SKHY"],
    "power": ["GEV", "BE", "CEG", "OKLO"],
}

def _get(url, timeout=25, headers=None, retries=1):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA if headers is None else headers)
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            last = e
            if i < retries - 1:
                import time
                time.sleep(3 * (i + 1))
    raise last


def _json(url):
    return json.loads(_get(url))


def fred(series_id):
    """FRED CSV as a float Series. Empty days arrive as '.', so coerce + dropna."""
    start = (date.today() - timedelta(days=800)).isoformat()
    # urllib's TLS handshake stalls against FRED here; requests (as data_fetcher.py uses) does not.
    import requests
    last = None
    for i in range(3):
        try:
            r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}",
                             headers={"User-Agent": "nocashflow-bulletin/2.0"}, timeout=25)
            r.raise_for_status()
            raw = r.text
            break
        except Exception as e:
            last = e
            import time
            time.sleep(2 * (i + 1))
    else:
        raise last
    f = pd.read_csv(io.StringIO(raw))
    f.columns = ["d", "v"]
    f["v"] = pd.to_numeric(f["v"], errors="coerce")
    f = f.dropna()
    return pd.Series(f["v"].values, index=pd.to_datetime(f["d"]))


def last_friday(today, utc_hour=None):
    """The last *completed* Friday close. On a Friday the close only counts
    once the US session is over (21:00 UTC); before that it is last week's."""
    off = (today.weekday() - 4) % 7
    if off == 0 and (utc_hour is None or utc_hour < 21):
        off = 7
    return today - timedelta(days=off)


def _at(s, when):
    """Last value on or before `when` (None if the series starts later)."""
    x = s[s.index <= pd.Timestamp(when)]
    return float(x.iloc[-1]) if len(x) else None


def _chg(last, base):
    return (last / base - 1) * 100 if base else None


def stats(s, cut):
    """Summary of one daily series, everything measured at the same cut (the
    last completed Friday close). 1W = vs the close a week before the cut,
    1M / 3M = vs one / three calendar months before, YTD = vs the prior
    year's last close. `since` is set when the series has no prior-year
    close: YTD then measures from its first point and is labelled so."""
    s = s.dropna()
    s = s[s.index <= pd.Timestamp(cut)]
    if len(s) < 25:
        raise ValueError("series too short")
    end = s.index[-1]
    if (pd.Timestamp(cut) - end).days > 4:
        raise ValueError(f"stale: last point {end.date()}")
    c = pd.Timestamp(cut)
    last = float(s.iloc[-1])
    w0 = _at(s, c - pd.Timedelta(days=7))
    m0 = _at(s, c - pd.DateOffset(months=1))
    q0 = _at(s, c - pd.DateOffset(months=3))
    y0 = _at(s, pd.Timestamp(c.year - 1, 12, 31))
    since = None
    if y0 is None:
        since = str(s.index[0].date())
        y0 = float(s.iloc[0])
    y = s[s.index >= c - pd.Timedelta(days=365)]
    wk = y.resample("W-FRI").last().dropna()
    rets = s.pct_change().dropna()
    p = s[s.index <= c - pd.Timedelta(days=7)]
    week = s[s.index > c - pd.Timedelta(days=7)]
    return {
        "since": since, "last": last, "date": str(end.date()),
        "w": _chg(last, w0), "m": _chg(last, m0), "q": _chg(last, q0), "ytd": _chg(last, y0),
        "ma50": float(s.tail(50).mean()),
        "ma200": float(s.tail(200).mean()) if len(s) >= 200 else None,
        "hi52": float(y.max()), "lo52": float(y.min()),
        "series": [float(v) for v in wk],
        "d5": [float(v) for v in (rets * 100).tail(5)],
        "d5dates": [str(i.date()) for i in s.tail(5).index],
        # this week's daily closes (for the scorecard) and the levels a week ago
        "week": [[str(i.date()), float(v)] for i, v in week.items()],
        "prev": {
            "last": w0,
            "ma50": float(p.tail(50).mean()) if len(p) >= 50 else None,
            "ma200": float(p.tail(200).mean()) if len(p) >= 200 else None,
        },
    }


def rate_stats(s, cut):
    out = stats(s, cut)
    s = s.dropna()
    s = s[s.index <= pd.Timestamp(cut)]
    c = pd.Timestamp(cut)
    last = float(s.iloc[-1])

    def bp(base):
        return (last - base) * 100 if base is not None else None
    out["w_bp"] = bp(_at(s, c - pd.Timedelta(days=7)))
    out["m_bp"] = bp(_at(s, c - pd.DateOffset(months=1)))
    out["q_bp"] = bp(_at(s, c - pd.DateOffset(months=3)))
    out["ytd_bp"] = None if out["since"] else bp(_at(s, pd.Timestamp(c.year - 1, 12, 31)))
    out["d200_bp"] = (last - out["ma200"]) * 100 if out["ma200"] is not None else None
    return out


WINDOWS = ("w", "m", "q", "ytd")


def basket_stats(C, names, cut):
    """Equal-weight basket. Each window's return is the plain average of the
    members' returns over that same window (equal weight at the start of
    every window), so the card always adds up to the names it lists. A
    window is left out when any member lacks it. The level, MAs and chart
    come from a daily-rebalanced equal-weight index of the same members."""
    members = {}
    for t in names:
        try:
            members[t] = stats(C[t], cut)
        except Exception:
            pass
    if len(members) < 2:
        raise ValueError("fewer than two members with data")
    cols = [t for t in names if t in members]
    daily = C[cols][C.index <= pd.Timestamp(cut)].pct_change().mean(axis=1, skipna=True).fillna(0)
    idx = (1 + daily).cumprod() * 100
    first = max(C[t].first_valid_index() for t in cols)
    out = stats(idx[idx.index >= first], cut)
    for k in WINDOWS:
        vals = [members[t][k] for t in cols]
        young = k == "ytd" and any(members[t]["since"] for t in cols)
        out[k] = None if young or any(v is None for v in vals) else sum(vals) / len(vals)
    out["since"] = None
    out["members"] = cols
    out["missing_members"] = [t for t in names if t not in members]
    return out


def _okx(inst):
    rows, after = [], ""
    for _ in range(5):
        d = _json(f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1D&limit=100{after}")["data"]
        if not d:
            break
        rows += d
        after = f"&after={d[-1][0]}"
    return pd.Series([float(r[4]) for r in rows],
                     index=pd.to_datetime([int(r[0]) for r in rows], unit="ms")).sort_index()


def _bitget(sym):
    d = _json(f"https://api.bitget.com/api/v2/mix/market/candles?symbol={sym}"
              "&productType=USDT-FUTURES&granularity=1D&limit=1000")["data"]
    return pd.Series([float(r[4]) for r in d],
                     index=pd.to_datetime([int(r[0]) for r in d], unit="ms")).sort_index()


def _corr(a, b, diff_b=True, n=63, cut=None):
    if cut is not None:
        a, b = a[a.index <= pd.Timestamp(cut)], b[b.index <= pd.Timestamp(cut)]
    x = a.pct_change()
    y = b.diff() if diff_b else b.pct_change()
    z = pd.concat([x, y], axis=1).dropna().tail(n)
    return float(z.corr().iloc[0, 1])


def _next_fed(cut_odds, today):
    """First meeting on or after today, from the site's 'Mon D' labels."""
    best = None
    for o in cut_odds:
        try:
            d = datetime.strptime(f"{o['m']} {today.year}", "%b %d %Y").date()
        except (ValueError, KeyError):
            continue
        if d < today - timedelta(days=200):
            d = d.replace(year=today.year + 1)
        if d >= today and (best is None or d < best[0]):
            best = (d, float(o["p"]))
    return {"date": str(best[0]), "p": best[1]} if best else None


def fetch(today=None, extra=(), cut=None):
    """Returns (data, report, C, V). `data` is JSON-serialisable; C and V are
    the raw daily closes and volumes, for the personal layer. `extra` adds
    tickers (portfolio + watchlist) to the same download."""
    import yfinance as yf
    today = today or date.today()
    cut = cut or last_friday(today, datetime.utcnow().hour)
    report = {"missing": [], "warnings": []}
    tick = list(dict.fromkeys(list(TICKERS.values()) + [t for b in BASKETS.values() for t in b] + list(extra)))
    raw = yf.download(tick, period="2y", interval="1d", progress=False, auto_adjust=True)
    C, V = raw["Close"], raw["Volume"]
    A = {}
    for t in extra:
        k = t.lower()
        if k in A or k in TICKERS:
            continue
        try:
            A[k] = stats(C[t], cut)
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"{t}: {e}")
    for k, t in TICKERS.items():
        try:
            A[k] = stats(C[t], cut)
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"{k} ({t}): {e}")

    def ratio(key, num, den, mult=1.0):
        try:
            A[key] = stats((C[num] / C[den]).dropna() * mult, cut)
        except Exception as e:
            report["missing"].append(key)
            report["warnings"].append(f"{key}: {e}")

    ratio("gsr", "GC=F", "SI=F")
    ratio("gdx_gold", "GDX", "GC=F")
    ratio("sil_silver", "SIL", "SI=F")
    ratio("cu_au", "HG=F", "GC=F", 1000)
    ratio("ew_cw", "QQQE", "QQQ")
    ratio("sox_ndx", "^SOX", "^NDX")

    for k, names in BASKETS.items():
        try:
            A[k] = basket_stats(C, names, cut)
            for t in A[k]["missing_members"]:
                report["warnings"].append(f"basket {k}: {t} has no data, left out of the card and the average")
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"basket {k}: {e}")

    # rates (FRED)
    series = {}
    for k, sid in (("us2y", "DGS2"), ("us10y", "DGS10"), ("real10", "DFII10"), ("hy", "BAMLH0A0HYM2")):
        try:
            series[k] = fred(sid)
            A[k] = rate_stats(series[k], cut)
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"FRED {sid}: {e}")
    # Breakeven = nominal − real on the same dates (that is how FRED defines
    # T10YIE). Deriving it keeps the split exact: 10Y move = real + breakeven.
    if "us10y" in series and "real10" in series:
        try:
            series["be10"] = (series["us10y"] - series["real10"]).dropna()
            A["be10"] = rate_stats(series["be10"], cut)
        except Exception as e:
            report["missing"].append("be10")
            report["warnings"].append(f"be10: {e}")
    if "us2y" in series and "us10y" in series:
        try:
            A["s2s10"] = rate_stats((series["us10y"] - series["us2y"]).dropna(), cut)
        except Exception as e:
            report["warnings"].append(f"s2s10: {e}")

    # GPU rental perpetuals
    for k, f in (("h100", lambda: _okx("H100-USDT-SWAP")), ("b200", lambda: _bitget("B200USDT"))):
        try:
            A[k] = stats(f(), cut)
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"{k}: {e}")

    corr = {}
    for key, fn in (
        ("gold_real", lambda: _corr(C["GC=F"].dropna(), series["real10"], cut=cut)),
        ("gold_dxy", lambda: _corr(C["GC=F"].dropna(), C["DX-Y.NYB"].dropna(), False, cut=cut)),
        ("ndx_10y", lambda: _corr(C["^NDX"].dropna(), series["us10y"], cut=cut)),
        ("ndx_gold", lambda: _corr(C["^NDX"].dropna(), C["GC=F"].dropna(), False, cut=cut)),
        ("silver_copper", lambda: _corr(C["SI=F"].dropna(), C["HG=F"].dropna(), False, cut=cut)),
    ):
        try:
            v = fn()
            if v == v:   # not NaN
                corr[key] = v
        except Exception as e:
            report["warnings"].append(f"corr {key}: {e}")

    vol = {}
    for k in ("qqq", "gld", "slv"):
        try:
            v = V[TICKERS[k]].dropna()
            v = v[v.index <= pd.Timestamp(cut)]
            vol[k] = float(v.tail(5).mean() / v.tail(65).head(60).mean())
        except Exception as e:
            report["warnings"].append(f"vol {k}: {e}")

    site = {}
    for name in ("calendar", "macro2", "market"):
        try:
            site[name] = _json(f"{SITE_DATA}/{name}.json")
        except Exception as e:
            report["warnings"].append(f"site {name}: {e}")
    cal = [e for e in (site.get("calendar") or {}).get("events", [])
           if e.get("country") == "US" and e.get("impact") in ("high", "medium")]
    fed = _next_fed(((site.get("macro2") or {}).get("fed") or {}).get("cut_odds", []), today)
    fg = ((site.get("market") or {}).get("instruments") or {}).get("fg")

    data = {
        "asof": str(cut), "cut": str(cut),
        "today": str(today),
        "a": A, "corr": corr, "vol": vol, "baskets": BASKETS,
        "calendar": cal, "fed": fed, "fg": fg,
    }
    return data, report, C, V
