"""Weekly bulletin v2 — data layer.

Every number in the bulletin comes from here. Nothing is estimated or filled
in: a series that fails to load is simply absent, and the renderer shows "—"
or hides the block. Sources: Yahoo Finance (yfinance), FRED CSV, OKX and Bitget
public market APIs (GPU rental perpetuals), Finnhub (earnings cross-check, if
a key is set) and nocashflow.net's own data files (calendar, Fed odds, F&G).
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

# earnings watch: every single name in the owner's watchlist (prices or not)
_EARN_ONLY = ["INTC", "WDAY", "CRM", "SNOW", "ORCL", "MRVL", "NFLX", "PLTR", "COIN", "HOOD", "MSTR", "UBER", "FSLR",
              "FLNC", "CLSK", "SMR", "ISRG", "MRNA", "BNTX", "KLAC", "AMAT", "ASML", "ARM", "VRT", "MP", "SN", "TEM", "RDDT", "AXON"]
_NOT_COMPANIES = {"QQQ", "QQQE", "GDX", "SIL", "GLD", "SLV", "IGV", "SMH", "NASA"}
EARNINGS_WATCH = _EARN_ONLY + [t for t in TICKERS.values() if t.isalpha() and t.isupper() and t not in _NOT_COMPANIES]


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


def stats(s):
    """Summary of one daily series. `since` is set when the history is shorter
    than ~11 months: YTD then measures from the first point, and the renderer
    labels it with that date instead of 'YTD'."""
    s = s.dropna()
    if len(s) < 25:
        raise ValueError("series too short")
    last = float(s.iloc[-1])
    end = s.index[-1]
    y = s[s.index >= end - pd.Timedelta(days=365)]
    ytd0 = float(s[s.index.year == end.year].iloc[0])
    wk = y.resample("W-FRI").last().dropna()
    young = s.index[0] > end - pd.Timedelta(days=330)
    rets = s.pct_change().dropna()
    return {
        "since": str(s.index[0].date()) if young else None,
        "last": last, "date": str(end.date()),
        "w": (last / float(s.iloc[-6]) - 1) * 100,
        "m": (last / float(s.iloc[-22]) - 1) * 100,
        "ytd": (last / ytd0 - 1) * 100,
        "ma50": float(s.tail(50).mean()),
        "ma200": float(s.tail(200).mean()) if len(s) >= 200 else None,
        "hi52": float(y.max()), "lo52": float(y.min()),
        "series": [float(v) for v in wk],
        "d5": [float(v) for v in (rets * 100).tail(5)],
        "d5dates": [str(i.date()) for i in s.tail(5).index],
        # the same levels one week (5 sessions) earlier, for the scorecard
        "prev": {
            "last": float(s.iloc[-6]),
            "ma50": float(s.iloc[:-5].tail(50).mean()),
            "ma200": float(s.iloc[:-5].tail(200).mean()) if len(s) >= 205 else None,
        },
    }


def rate_stats(s):
    out = stats(s)
    out["w_bp"] = (float(s.iloc[-1]) - float(s.iloc[-6])) * 100
    out["m_bp"] = (float(s.iloc[-1]) - float(s.iloc[-22])) * 100
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


def _corr(a, b, diff_b=True, n=63):
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


def _earnings(today, report):
    """Next 14 days of earnings for the watchlist (yfinance calendar). If a
    Finnhub key is set, a date Finnhub disagrees with is dropped rather than
    guessed at."""
    import yfinance as yf
    out = []
    horizon = today + timedelta(days=14)
    for t in EARNINGS_WATCH:
        try:
            cal = yf.Ticker(t).calendar or {}
            for d in cal.get("Earnings Date") or []:
                d = d if isinstance(d, date) else pd.Timestamp(d).date()
                if today <= d <= horizon:
                    out.append({"t": t, "d": str(d), "eps": cal.get("Earnings Average"),
                                "rev": cal.get("Revenue Average")})
                    break
        except Exception as e:
            report["warnings"].append(f"earnings {t}: {e}")
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if key and out:
        try:
            fh = _json(f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={horizon}&token={key}")
            fh_dates = {}
            for e in fh.get("earningsCalendar", []):
                fh_dates.setdefault(e.get("symbol"), set()).add(e.get("date"))
            kept = []
            for e in out:
                if e["t"] in fh_dates and e["d"] not in fh_dates[e["t"]]:
                    report["warnings"].append(f"earnings {e['t']}: yfinance {e['d']} vs Finnhub {sorted(fh_dates[e['t']])} — dropped")
                    continue
                kept.append(e)
            out = kept
        except Exception as e:
            report["warnings"].append(f"finnhub cross-check: {e}")
    out.sort(key=lambda x: (x["d"], x["t"]))
    return out


def fetch(today=None):
    """Returns (data, report). `data` is JSON-serialisable."""
    import yfinance as yf
    today = today or date.today()
    report = {"missing": [], "warnings": []}
    raw = yf.download(list(TICKERS.values()), period="2y", interval="1d", progress=False, auto_adjust=True)
    C, V = raw["Close"], raw["Volume"]
    A = {}
    for k, t in TICKERS.items():
        try:
            A[k] = stats(C[t])
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"{k} ({t}): {e}")

    def ratio(key, num, den, mult=1.0):
        try:
            A[key] = stats((C[num] / C[den]).dropna() * mult)
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
            b = C[names].dropna()
            A[k] = stats((b / b.iloc[0]).mean(axis=1) * 100)
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"basket {k}: {e}")

    # rates (FRED)
    series = {}
    for k, sid in (("us2y", "DGS2"), ("us10y", "DGS10"), ("real10", "DFII10")):
        try:
            series[k] = fred(sid)
            A[k] = rate_stats(series[k])
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"FRED {sid}: {e}")
    # Breakeven = nominal − real on the same dates (that is how FRED defines
    # T10YIE). Deriving it keeps the split exact: 10Y move = real + breakeven.
    if "us10y" in series and "real10" in series:
        try:
            series["be10"] = (series["us10y"] - series["real10"]).dropna()
            A["be10"] = rate_stats(series["be10"])
        except Exception as e:
            report["missing"].append("be10")
            report["warnings"].append(f"be10: {e}")
    if "us2y" in series and "us10y" in series:
        try:
            A["s2s10"] = stats((series["us10y"] - series["us2y"]).dropna() * 100)
            A["s2s10"]["w_bp"] = A["s2s10"]["last"] - (float(series["us10y"].iloc[-6]) - float(series["us2y"].iloc[-6])) * 100
        except Exception as e:
            report["warnings"].append(f"s2s10: {e}")

    # GPU rental perpetuals
    for k, f in (("h100", lambda: _okx("H100-USDT-SWAP")), ("b200", lambda: _bitget("B200USDT"))):
        try:
            A[k] = stats(f())
        except Exception as e:
            report["missing"].append(k)
            report["warnings"].append(f"{k}: {e}")

    corr = {}
    for key, fn in (
        ("gold_real", lambda: _corr(C["GC=F"].dropna(), series["real10"])),
        ("gold_dxy", lambda: _corr(C["GC=F"].dropna(), C["DX-Y.NYB"].dropna(), False)),
        ("ndx_10y", lambda: _corr(C["^NDX"].dropna(), series["us10y"])),
        ("ndx_gold", lambda: _corr(C["^NDX"].dropna(), C["GC=F"].dropna(), False)),
        ("silver_copper", lambda: _corr(C["SI=F"].dropna(), C["HG=F"].dropna(), False)),
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
        "asof": max(v["date"] for v in A.values()) if A else str(today),
        "today": str(today),
        "a": A, "corr": corr, "vol": vol, "baskets": BASKETS,
        "calendar": cal, "fed": fed, "fg": fg,
        "earn": _earnings(today, report),
    }
    return data, report
