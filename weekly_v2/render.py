"""Weekly bulletin v2 — personal decision edition (TR).

One reader. The page answers "what am I doing this week", not "what did the
market do". Layout and styling are the approved Liquid demo; only content
changed. Rules every sentence follows:

  * it rests on a number printed on the page;
  * a cause is named only when the driver's change over the same period AND
    its correlation with the target both point that way (`supports`);
  * one week of price is never called a flow; a positive week after a 1M
    loss worse than −15% is labelled "tepki" (rebound);
  * conditions, not advice: "X closes below Y → the stop triggers";
  * a threshold is never the current value itself;
  * a value that cannot be fetched is not printed: the row/box is left out
    and named in the missing-data note at the bottom.
"""
import math
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

NAMES = {"NVDA": "Nvidia", "AMD": "AMD", "AVGO": "Broadcom", "NOW": "ServiceNow", "CRWD": "CrowdStrike",
         "PANW": "Palo Alto", "CRDO": "Credo", "ALAB": "Astera Labs", "LITE": "Lumentum", "AAOI": "Applied Opto",
         "SPCX": "SpaceX", "RKLB": "Rocket Lab", "ASTS": "AST Space", "FLY": "Firefly",
         "CRWV": "CoreWeave", "NBIS": "Nebius", "IREN": "IREN", "APLD": "Applied Digital",
         "MU": "Micron", "SNDK": "Sandisk", "SKHY": "SK hynix", "GEV": "GE Vernova", "BE": "Bloom", "CEG": "Constellation",
         "OKLO": "Oklo", "WDAY": "Workday", "FLNC": "Fluence", "CLSK": "CleanSpark", "MRVL": "Marvell",
         "INTC": "Intel", "CRM": "Salesforce", "SNOW": "Snowflake", "ORCL": "Oracle", "NFLX": "Netflix",
         "PLTR": "Palantir", "COIN": "Coinbase", "HOOD": "Robinhood", "MSTR": "Strategy", "UBER": "Uber",
         "FSLR": "First Solar", "SMR": "NuScale", "ISRG": "Intuitive Surgical", "MRNA": "Moderna", "BNTX": "BioNTech",
         "KLAC": "KLA", "AMAT": "Applied Materials", "ASML": "ASML", "ARM": "Arm", "VRT": "Vertiv", "MP": "MP Materials",
         "SN": "SharkNinja", "TEM": "Tempus AI", "RDDT": "Reddit", "AXON": "Axon",
         "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla"}

S = {
    "tr": {"days": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
           "months": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
           "bn": " mr", "mn": " mn"},
    "en": {"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
           "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
           "bn": "bn", "mn": "m"},
}

NAME = {
    "ndx": "Nasdaq 100", "spx": "S&P 500", "sox": "Yarı iletken (SOX)", "gold": "Altın", "silver": "Gümüş",
    "copper": "Bakır", "dxy": "Dolar endeksi", "vix": "VIX", "vxn": "VXN", "btc": "Bitcoin",
    "us2y": "ABD 2Y", "us10y": "ABD 10Y", "real10": "10Y reel faiz", "be10": "10Y başabaş enflasyon",
    "s2s10": "2s10s eğim", "hy": "HY kredi makası",
    "kospi": "KOSPI", "twii": "TAIEX", "n225": "Nikkei 225", "usdjpy": "USD/JPY",
    "nvda": "Nvidia", "aapl": "Apple", "msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "tsla": "Tesla",
}
MISSING_NAME = {**NAME, "optics": "Optik sepeti", "neocloud": "Neocloud sepeti", "memory": "Bellek sepeti",
                "power": "Enerji sepeti", "h100": "H100 kirası", "b200": "B200 kirası", "gsr": "Altın/gümüş oranı",
                "gdx_gold": "GDX/altın", "sil_silver": "SIL/gümüş", "cu_au": "Bakır/altın", "ew_cw": "QQQE/QQQ",
                "sox_ndx": "SOX/Nasdaq", "qqq": "QQQ", "qqqe": "QQQE", "smh": "SMH", "igv": "IGV", "nasa": "NASA"}

CAL_TR = {
    "Fed Chairman Warsh Speaks": "Fed Başkanı Warsh konuşuyor", "Core Retail Sales m/m": "Çekirdek perakende satışlar (MoM)",
    "Retail Sales m/m": "Perakende satışlar (MoM)", "FOMC Meeting Minutes": "FOMC tutanakları",
    "Philly Fed Manufacturing Index": "Philly Fed imalat endeksi", "Unemployment Claims": "İşsizlik başvuruları",
    "Revised UoM Consumer Sentiment": "Michigan tüketici güveni (revize)", "Prelim UoM Consumer Sentiment": "Michigan tüketici güveni (öncü)",
    "CPI m/m": "TÜFE (MoM)", "CPI y/y": "TÜFE (YoY)", "Core CPI m/m": "Çekirdek TÜFE (MoM)",
    "PPI m/m": "ÜFE (MoM)", "Core PPI m/m": "Çekirdek ÜFE (MoM)", "Non-Farm Employment Change": "Tarım dışı istihdam",
    "Unemployment Rate": "İşsizlik oranı", "Average Hourly Earnings m/m": "Ortalama saatlik kazanç (MoM)",
    "Advance GDP q/q": "GSYİH öncü (QoQ)", "Prelim GDP q/q": "GSYİH ikinci tahmin (QoQ)", "Final GDP q/q": "GSYİH nihai (QoQ)",
    "Core PCE Price Index m/m": "Çekirdek PCE fiyat endeksi (MoM)", "ISM Manufacturing PMI": "ISM imalat PMI",
    "ISM Services PMI": "ISM hizmet PMI", "JOLTS Job Openings": "JOLTS açık pozisyonlar", "ADP Non-Farm Employment Change": "ADP özel sektör istihdamı",
    "Federal Funds Rate": "Fed faiz kararı", "FOMC Statement": "FOMC metni", "FOMC Press Conference": "FOMC basın toplantısı",
    "CB Consumer Confidence": "Conference Board tüketici güveni", "Empire State Manufacturing Index": "Empire State imalat endeksi",
    "Flash Manufacturing PMI": "İmalat PMI (öncü)", "Flash Services PMI": "Hizmet PMI (öncü)",
    "Durable Goods Orders m/m": "Dayanıklı mal siparişleri (MoM)", "Core Durable Goods Orders m/m": "Çekirdek dayanıklı mal siparişleri (MoM)",
    "Pending Home Sales m/m": "Bekleyen konut satışları (MoM)", "Existing Home Sales": "Mevcut konut satışları",
    "New Home Sales": "Yeni konut satışları", "Building Permits": "İnşaat izinleri", "Housing Starts": "Konut başlangıçları",
}

BASKET_NAME = {"neocloud": ("Neocloud", "GPU'yu kiraya veren bulutlar"), "memory": ("Bellek", "HBM ve NAND"),
               "optics": ("Optik", "veri merkezi bağlantısı"), "power": ("Enerji", "şebeke, yakıt hücresi, nükleer")}
REBOUND_1M = -15.0          # a positive week after a 1M worse than this is a "tepki"
CORR_MIN = 0.3              # a correlation weaker than this cannot carry a causal sentence


# ── formatting ──────────────────────────────────────────────────────────────
class F:
    def __init__(self, lang="tr"):
        self.l = lang
        self.s = S[lang]

    def num(self, v, dec=2):
        s = f"{abs(v):,.{dec}f}"
        if self.l == "tr":
            s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return ("−" if v < 0 and round(abs(v), dec) != 0 else "") + s

    def pct(self, v, dec=1, sign=True):
        """Signed percent; a value that rounds to zero is printed bare: %0,0."""
        if round(abs(v), dec) == 0:
            return f"%{self.num(0, dec)}" if self.l == "tr" else f"{self.num(0, dec)}%"
        sg = ("+" if v > 0 else "−") if sign else ("−" if v < 0 else "")
        body = self.num(abs(v), dec)
        return f"{sg}%{body}" if self.l == "tr" else f"{sg}{body}%"

    def lvl(self, v, dec=2):
        """A level that is itself a percentage (yields, ratios of a whole)."""
        return f"%{self.num(v, dec)}" if self.l == "tr" else f"{self.num(v, dec)}%"

    def bp(self, v):
        r = round(v)
        return ("+" if r > 0 else "−" if r < 0 else "") + f"{abs(r)}bp"

    def pts(self, v, dec=1):
        if round(abs(v), dec) == 0:
            return f"{self.num(0, dec)} puan"
        return ("+" if v > 0 else "−") + f"{self.num(abs(v), dec)} puan"

    def usd(self, v, dec=2):
        return ("−" if v < 0 else "") + "$" + self.num(abs(v), dec)

    def day(self, iso):
        d = date.fromisoformat(iso)
        return f"{self.s['days'][d.weekday()]} {d.day:02d}.{d.month:02d}"

    def long_date(self, iso):
        d = date.fromisoformat(iso)
        m = self.s["months"][d.month - 1]
        return f"{d.day} {m} {d.year}" if self.l == "tr" else f"{m} {d.day}, {d.year}"

    def ylab(self, a):
        if a.get("since"):
            d = date.fromisoformat(a["since"])
            return f"{d.day:02d}.{d.month:02d}'den"
        return "YTD"


def dc(v, dec=1):
    """Colour class only for a value that does not round to zero."""
    return "" if v is None or round(v, dec) == 0 else ("up" if v > 0 else "dn")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def sgn(v):
    return 0 if not v else (1 if v > 0 else -1)


# ── charts ──────────────────────────────────────────────────────────────────
def spark(vals, w=260, h=64, stroke="#FF4B26", fill=True, layers=0, dot=True, sw=2):
    vals = [v for v in vals if v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    sp = (hi - lo) or 1
    n = len(vals) - 1
    pts = [(i * w / n, h - 4 - (v - lo) / sp * (h - 10)) for i, v in enumerate(vals)]
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    out = []
    for k in range(layers, 0, -1):
        out.append(f'<path d="{d}" transform="translate({k * 5} {-k * 5})" fill="none" stroke="#6FB2FF" '
                   f'stroke-opacity="{0.55 * (1 - k / (layers + 1)) ** 1.5 + 0.05:.2f}" stroke-width="1"/>')
    if fill:
        out.append(f'<path d="{d} L{w} {h} L0 {h} Z" fill="{stroke}" fill-opacity=".08"/>')
    out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>')
    if dot:
        x, y = pts[-1]
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{stroke}"/>')
    return (f'<svg viewBox="-2 -{layers * 5 + 2} {w + layers * 5 + 6} {h + layers * 5 + 4}" '
            f'preserveAspectRatio="none" class="sp" aria-hidden="true">{"".join(out)}</svg>')


def rng(a):
    pos = (a["last"] - a["lo52"]) / ((a["hi52"] - a["lo52"]) or 1) * 100
    return f'<div class="rng"><i style="left:{max(0, min(100, pos)):.1f}%"></i></div>'


def pos52(a):
    return (a["last"] - a["lo52"]) / ((a["hi52"] - a["lo52"]) or 1)


def bars5(a, f):
    if len(a.get("d5", [])) < 5:
        return ""
    m = max(abs(x) for x in a["d5"]) or 1
    w, mid, half = 300, 38, 24
    out = [f'<line x1="0" x2="{w}" y1="{mid}" y2="{mid}" stroke="rgba(11,12,15,.25)" stroke-width="1"/>']
    for i, (v, ds) in enumerate(zip(a["d5"], a["d5dates"])):
        x = i * 60 + 8
        h = max(abs(v) / m * half, 1.5)
        y = mid - h if v > 0 else mid
        col = "#14713F" if v > 0 else "#AD2B11"
        ty = mid - h - 5 if v > 0 else mid + h + 12
        out.append(f'<rect x="{x}" y="{y:.1f}" width="44" height="{h:.1f}" rx="3" fill="{col}"/>')
        out.append(f'<text x="{x + 22}" y="{ty:.1f}" text-anchor="middle" class="bv">{f.pct(v, 1)}</text>')
        out.append(f'<text x="{x + 22}" y="88" text-anchor="middle" class="bd">{f.s["days"][date.fromisoformat(ds).weekday()]}</text>')
    return f'<svg viewBox="0 0 {w} 92" class="d5" aria-hidden="true">{"".join(out)}</svg>'


def regime(last, ma50, ma200):
    if ma200 is None or ma50 is None:
        return "mix"
    if last > ma50 and last > ma200:
        return "up"
    if last < ma50 and last < ma200:
        return "dn"
    return "mix"


def is_rate(a):
    return "w_bp" in a


def zmove(a):
    """This week's move in units of its own typical weekly move (1y of weekly closes)."""
    s = a["series"]
    if len(s) < 12:
        return 0.0
    if is_rate(a):
        ch = [(s[i] - s[i - 1]) * 100 for i in range(1, len(s))]
        now = a.get("w_bp") or 0
    else:
        ch = [(s[i] / s[i - 1] - 1) * 100 for i in range(1, len(s)) if s[i - 1]]
        now = a.get("w") or 0
    m = sum(ch) / len(ch)
    sd = math.sqrt(sum((c - m) ** 2 for c in ch) / (len(ch) - 1))
    # floor: a near-flat year would otherwise turn any small move into a headline
    return now / max(sd, 3.0 if is_rate(a) else 0.5)


def sh(num, title, meta):
    return (f'<div class="sh"><span class="mono">§ {num:02d}</span><h2>{title[0]}<i>{title[1]}</i></h2>'
            f'<span class="meta mono mute">{meta}</span></div>')


# ── the bulletin ────────────────────────────────────────────────────────────
class Bulletin:
    def __init__(self, data, lang="tr"):
        self.d = data
        self.A = data["a"]
        self.P = data.get("personal") or {}
        self.CO = self.P.get("co") or {}
        self.R = data.get("rules") or {}
        self.PF = data.get("portfolio") or {}
        self.l = "tr"
        self.f = F("tr")
        self.num = 0
        self.missing = []
        self.week_rows = []          # §01 "Bu hafta" rows, stored for next week's scorecard

    # helpers
    def has(self, *keys):
        return all(k in self.A for k in keys)

    def n(self, key):
        return NAME.get(key, key.upper())

    def miss(self, what):
        if what not in self.missing:
            self.missing.append(what)

    def ch(self, v, dec=1, suffix=""):
        """A signed percent change as a coloured span; None → nothing."""
        if v is None:
            return ""
        return f'<span class="{dc(v, dec)}">{self.f.pct(v, dec)}{suffix}</span>'

    def chbp(self, v, suffix=""):
        if v is None:
            return ""
        return f'<span class="{dc(round(v), 0)}">{self.f.bp(v)}{suffix}</span>'

    def section(self, title, meta, body):
        self.num += 1
        return f'<section class="sec">{sh(self.num, title, meta)}{body}</section>'

    def tick(self, t):
        return self.A.get(t.lower())

    def wl(self):
        return set(w["ticker"].upper() for w in self.R.get("watchlist") or [])

    def held(self):
        return set(p["ticker"].upper() for p in self.PF.get("positions") or [])

    # ── causality gate ──────────────────────────────────────────────────────
    CORR_FOR = {("gold", "real10"): ("gold_real", -1), ("gold", "dxy"): ("gold_dxy", -1),
                ("ndx", "us10y"): ("ndx_10y", -1)}

    def supports(self, target, driver, period="w"):
        """True only if the driver moved materially over `period`, the target
        moved the way the textbook link says, and the 63-session correlation
        has that sign and at least CORR_MIN strength."""
        key = self.CORR_FOR.get((target, driver))
        if not key or target not in self.A or driver not in self.A:
            return False
        r = (self.d.get("corr") or {}).get(key[0])
        expect = key[1]
        if r is None or abs(r) < CORR_MIN or sgn(r) != expect:
            return False
        da = self.A[driver]
        dv = da.get(period + "_bp") if is_rate(da) else da.get(period)
        tv = self.A[target].get(period)
        if dv is None or tv is None:
            return False
        if abs(dv) < (3 if is_rate(da) else 0.3) or round(tv, 1) == 0:
            return False
        return sgn(tv) == expect * sgn(dv)

    # ── hero ────────────────────────────────────────────────────────────────
    def headline(self):
        A, f = self.A, self.f
        cands = [(abs(zmove(A[k])), k) for k in ("ndx", "gold", "silver", "dxy", "us2y", "real10", "hy") if k in A]
        if not cands:
            return None
        _, k = max(cands)
        a = A[k]
        name = self.n(k)
        if is_rate(a):
            mv, mm = a.get("w_bp") or 0, a.get("m_bp")
            h1 = f"{name} {f.lvl(a['last'])}"
            if k == "real10" and self.supports("gold", "real10"):
                h2 = f"altın aynı hafta {f.pct(A['gold']['w'])}; korelasyon {f.num(self.d['corr']['gold_real'])}."
            else:
                h2 = f"haftada {f.bp(mv)}" + (f", ayda {f.bp(mm)}." if mm is not None else ".")
            return {"k": k, "h1": h1, "h2": h2, "series": a["series"], "lab": f"{name} · 1 yıl", "val": f.lvl(a["last"])}
        p = pos52(a)
        h1 = f"{name} haftada {f.pct(a['w'])}"
        if p >= .95:
            h2 = "52 haftanın zirvesinde."
        elif p <= .05:
            h2 = "52 haftanın dibinde."
        elif a.get("ma200"):
            d = (a["last"] / a["ma200"] - 1) * 100
            h2 = f"MA200'ün {f.pct(abs(d), 1, sign=False)} {'üstünde' if d > 0 else 'altında'}."
        else:
            h2 = f"ayda {f.pct(a['m'])}."
        dec = 0 if k in ("ndx", "gold") else 2
        cur = "$" if k in ("gold", "silver") else ""
        return {"k": k, "h1": h1, "h2": h2, "series": a["series"], "lab": f"{name} · 1 yıl", "val": cur + f.num(a["last"], dec)}

    def lede(self):
        A, f = self.A, self.f
        out = []
        if self.has("ndx", "gold", "silver"):
            out.append(f"Nasdaq 100 haftayı {f.pct(A['ndx']['w'])}, altın {f.pct(A['gold']['w'])}, gümüş {f.pct(A['silver']['w'])} ile kapattı.")
        if self.has("sox", "ndx"):
            lead = A["sox"]["w"] - A["ndx"]["w"]
            out.append(f"Yarı iletkenler {f.pct(A['sox']['w'])}; Nasdaq'a göre {f.pts(lead)}.")
        if self.has("real10"):
            out.append(f"10 yıllık reel faiz haftada {f.bp(A['real10']['w_bp'])}, şu an {f.lvl(A['real10']['last'])}.")
        if self.has("hy"):
            out.append(f"HY kredi makası {f.lvl(A['hy']['last'])}, haftada {f.bp(A['hy']['w_bp'])}.")
        return " ".join(out)

    def key5(self):
        A, f = self.A, self.f
        items = []
        for k, lab in (("ndx", "Nasdaq 100"), ("gold", "Altın"), ("silver", "Gümüş")):
            if k in A:
                items.append((lab, f.pct(A[k]["w"]), "1W", dc(A[k]["w"])))
        for k, lab in (("real10", "Reel faiz"), ("hy", "HY makası")):
            if k in A:
                items.append((lab, f.bp(A[k]["w_bp"]), "1W", dc(round(A[k]["w_bp"]), 0)))
        return items

    # ── §01 decision page ───────────────────────────────────────────────────
    def regime_now(self):
        from weekly_v2.personal import regime_state
        A = self.A
        if not self.has("ndx", "vxn") or not A["ndx"].get("ma200"):
            return None
        ndx_up = A["ndx"]["last"] > A["ndx"]["ma200"]
        vxn_up = A["vxn"]["last"] > A["vxn"]["ma50"]
        st = regime_state(self.R, ndx_up, vxn_up)
        if not st:
            return None
        return {"st": st, "ndx_up": ndx_up, "vxn_up": vxn_up,
                "flip_ndx": regime_state(self.R, not ndx_up, vxn_up), "flip_vxn": regime_state(self.R, ndx_up, not vxn_up)}

    def book(self):
        """Positions with a price at the cut; None if any position lacks one."""
        rows, total = [], 0.0
        for p in self.PF.get("positions") or []:
            t = p["ticker"].upper()
            a = self.tick(t)
            if not a:
                self.miss(f"{t}: kesim fiyatı yok — portföy satırı ve hisse oranı hesaplanmadı")
                return None, None
            v = a["last"] * float(p["shares"])
            rows.append({**p, "t": t, "a": a, "value": v})
            total += v
        cash = float(self.PF.get("cash") or 0)
        return rows, total + cash

    def decision(self):
        A, f = self.A, self.f
        tw = self.R.get("this_week") or {}
        stop_within = float(tw.get("stop_within_pct", 10))
        buy_within = float(tw.get("buy_within_pct", 5))
        hl = float(tw.get("stop_highlight_pct", 5))
        rg = self.regime_now()
        rows, nav = self.book()
        eq_pct = (sum(r["value"] for r in rows) / nav * 100) if rows and nav else None
        parts, lines = [], []

        # regime vs current equity share
        if rg:
            st = rg["st"]
            d_ndx = (A["ndx"]["last"] / A["ndx"]["ma200"] - 1) * 100
            d_vxn = (A["vxn"]["last"] / A["vxn"]["ma50"] - 1) * 100
            cur = (f'<div class="big">{f.lvl(eq_pct, 1)}</div><span class="mono mute">nakit {f.usd(float(self.PF.get("cash") or 0), 0)} · toplam {f.usd(nav, 0)}</span>'
                   if eq_pct is not None else '<p>Hisse oranı hesaplanamadı (eksik fiyat).</p>')
            gap = ""
            if eq_pct is not None:
                diff = eq_pct - float(st["max_equity_pct"])
                gap = f'<p>Fark: <b>{f.pts(diff)}</b> {"sınırın üstünde" if diff > 0 else "sınırın altında" if diff < 0 else ""}.</p>'
            parts.append(f'''<div class="regime">
  <div class="panel dark"><span class="k">Rejim · bu hafta</span><div class="big" style="margin-top:12px">{esc(st.get("label", ""))}</div>
    <p>Nasdaq 100 MA200'ün {f.pct(abs(d_ndx), 1, sign=False)} {"üstünde" if d_ndx > 0 else "altında"}; VXN MA50'sinin {f.pct(abs(d_vxn), 1, sign=False)} {"üstünde" if d_vxn > 0 else "altında"}.</p></div>
  <div class="panel"><span class="k">İzin verilen azami hisse oranı</span><div class="big">{f.lvl(float(st["max_equity_pct"]), 0)}</div><span class="mono mute">rules.yaml · rejim tablosu</span></div>
  <div class="panel"><span class="k">Mevcut hisse oranı</span>{cur}{gap}</div>
</div>''')
            # regime boundary conditions (thresholds are MAs, never the price itself)
            for key, ma_key, up, flip, label in (("ndx", "ma200", rg["ndx_up"], rg["flip_ndx"], "MA200"),
                                                 ("vxn", "ma50", rg["vxn_up"], rg["flip_vxn"], "MA50")):
                if not flip:
                    continue
                lvl = A[key][ma_key]
                dirw = "altında" if up else "üstünde"
                txt = (f"<b>{self.n(key)}</b>, {label} (<b>{f.num(lvl)}</b>) {dirw} kapanırsa rejim “{esc(flip.get('label', ''))}” olur; "
                       f"azami hisse oranı {f.lvl(float(st['max_equity_pct']), 0)} → {f.lvl(float(flip['max_equity_pct']), 0)}.")
                lines.append(txt)
                self.week_rows.append({"kind": "level", "key": key, "level": lvl, "dir": "below" if up else "above",
                                       "text": f"{self.n(key)} {label} ({f.num(lvl)}) {dirw} kapanırsa rejim değişir"})
            if eq_pct is not None and eq_pct > float(st["max_equity_pct"]):
                lines.append(f"Hisse oranı {f.lvl(eq_pct, 1)}; rejim sınırı {f.lvl(float(st['max_equity_pct']), 0)}, "
                             f"aradaki fark {f.pts(eq_pct - float(st['max_equity_pct']))}.")
        else:
            self.miss("Rejim: Nasdaq 100 MA200 / VXN MA50 ya da rules.yaml rejim tablosu eksik")

        # portfolio table
        if rows:
            trs = []
            for r in sorted(rows, key=lambda x: -x["value"]):
                a, t = r["a"], r["t"]
                w = r["value"] / nav * 100
                vs_cost = (a["last"] / float(r["cost"]) - 1) * 100
                stop = r.get("stop")
                sd = (a["last"] / float(stop) - 1) * 100 if stop else None
                warn = sd is not None and sd < hl
                nxt = (self.CO.get(t) or {}).get("next")
                earn = f.day(nxt["d"]) if nxt else ""
                if not nxt:
                    self.miss(f"{t}: sıradaki bilanço tarihi")
                sd_cell = (f'<td class="n {"dn" if warn else ""}">{f.pct(sd, 1, sign=False) if sd >= 0 else "stop altında " + f.pct(sd, 1)}</td>'
                           if sd is not None else '<td class="n"></td>')
                trs.append(f'<tr class="{"warn" if warn else ""}"><th>{NAMES.get(t, t)}<small>{t} · {esc(r.get("basket", ""))}</small></th>'
                           f'<td class="n">{f.usd(a["last"])}</td><td class="n">{f.lvl(w, 1)}</td>'
                           f'<td class="n">{self.ch(vs_cost)}</td><td class="n">{f.usd(float(stop)) if stop else ""}</td>{sd_cell}'
                           f'<td class="n">{self.ch(a["w"])}</td><td class="n">{earn}</td></tr>')
                if sd is not None and 0 <= sd < stop_within:
                    lines.insert(0, f"<b>{t}</b>, <b>{f.usd(float(stop))}</b> altında kapanırsa stop çalışır (şu an {f.pct(sd, 1, sign=False)} uzakta).")
                    self.week_rows.append({"kind": "stop", "key": t.lower(), "level": float(stop), "dir": "below",
                                           "text": f"{t} {f.usd(float(stop))} altında kapanırsa stop çalışır"})
                elif sd is not None and sd < 0:
                    lines.insert(0, f"<b>{t}</b> stop seviyesinin ({f.usd(float(stop))}) {f.pct(abs(sd), 1, sign=False)} altında kapandı.")
            th = "".join(f"<th>{h}</th>" for h in ("Pozisyon", "Son", "Ağırlık", "Maliyete göre", "Stop", "Stop'a mesafe", "1W", "Bilanço"))
            parts.append(f'<div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')

        # earnings of held names in the next 7 days
        today = date.fromisoformat(self.d["today"])
        for t in sorted(self.held()):
            nx = (self.CO.get(t) or {}).get("next")
            if nx and (date.fromisoformat(nx["d"]) - today).days <= 7:
                sess = {"bmo": " açılış öncesi", "amc": " kapanış sonrası"}.get(nx.get("sess"), "")
                im = f"; opsiyonlar ±{f.pct(nx['im'], 1, sign=False)} hareket ima ediyor" if nx.get("im") is not None else ""
                lines.append(f"<b>{t}</b> bilançosu {f.day(nx['d'])}{sess}{im}.")

        # watchlist names near their buy level
        for w in self.R.get("watchlist") or []:
            t, b = w["ticker"].upper(), w.get("buy_at")
            a = self.tick(t)
            if not b or not a:
                continue
            dist = (a["last"] / float(b) - 1) * 100
            if 0 <= dist <= buy_within:
                lines.append(f"<b>{t}</b> alım seviyesine (<b>{f.usd(float(b))}</b>) {f.pct(dist, 1, sign=False)} mesafede.")
                self.week_rows.append({"kind": "buy", "key": t.lower(), "level": float(b), "dir": "below",
                                       "text": f"{t} alım seviyesi {f.usd(float(b))}"})
            elif dist < 0:
                lines.append(f"<b>{t}</b> alım seviyesinin (<b>{f.usd(float(b))}</b>) {f.pct(abs(dist), 1, sign=False)} altında kapandı.")

        if lines:
            parts.append(f'<div class="panel"><span class="k">Bu hafta · yalnızca kurallardan</span><ul class="tw">{"".join(f"<li>{x}</li>" for x in lines)}</ul></div>')
        if not parts:
            return ""
        return self.section(("Karar ", "sayfası"), "rejim · portföy · bu hafta", "".join(parts))

    # ── §02 setups ──────────────────────────────────────────────────────────
    def setups(self):
        f = self.f
        sw = self.R.get("swing") or {}
        rows = []
        for w in self.R.get("watchlist") or []:
            t = w["ticker"].upper()
            a, c = self.tick(t), self.CO.get(t) or {}
            if not a:
                self.miss(f"{t}: fiyat verisi — kurulum satırı yok")
                continue
            cells = []
            # 1 volume on down days
            cells.append(None if "dist_days" not in c else not c["dist_days"])
            # 2 moving averages
            if a.get("ma200") is None:
                cells.append(None)
                self.miss(f"{t}: MA200 için yeterli geçmiş yok")
            else:
                ok = a["last"] > a["ma200"]
                if sw.get("require_above_ma50"):
                    ok = ok and a["last"] > a["ma50"]
                cells.append(ok)
            # 3 net debt / EBITDA
            if "nd_ebitda" in c:
                v = c["nd_ebitda"]
                cells.append(v is not None and v < float(sw.get("max_net_debt_ebitda", 3)))
            else:
                cells.append(None)
            # 4 profit + FCF
            cells.append((c["profit"] and c["fcf"]) if "profit" in c else None)
            # 5 analyst actions
            cells.append(None if "analyst_bad" not in c else not c["analyst_bad"])
            passed = sum(1 for x in cells if x)
            known = sum(1 for x in cells if x is not None)
            rows.append((passed, t, w, a, c, cells, known))
        if not rows:
            return ""
        rows.sort(key=lambda r: (-r[0], r[1]))
        trs, notes = [], []
        for passed, t, w, a, c, cells, known in rows:
            tds = "".join('<td class="c"></td>' if x is None else (f'<td class="c up">✓</td>' if x else f'<td class="c dn">✗</td>') for x in cells)
            b = w.get("buy_at")
            dist = f.pct((a["last"] / float(b) - 1) * 100, 1) if b else ""
            dd = (a["last"] / a["hi52"] - 1) * 100
            nx = c.get("next")
            spec = ""
            if "profit" in c and not (c["profit"] and c["fcf"]) and w.get("basket") != "spekulatif":
                spec = " · nakit yakıyor → spekülatif"
            trs.append(f'<tr><th>{NAMES.get(t, t)}<small>{t} · {esc(w.get("basket", ""))}{spec}</small></th>{tds}'
                       f'<td class="n">{passed}/{known}</td><td class="n">{dist}</td><td class="n">{self.ch(dd)}</td>'
                       f'<td class="n">{f.day(nx["d"]) if nx else ""}</td></tr>')
            if c.get("dist_days"):
                notes.append(f"{t}: yüksek hacimli düşüş günü {', '.join(f.day(d) for d in c['dist_days'])}")
            if c.get("nd_ebitda") is None and c.get("ebitda_neg"):
                notes.append(f"{t}: FAVÖK negatif")
            elif c.get("nd_ebitda") is not None and c["nd_ebitda"] >= float(sw.get("max_net_debt_ebitda", 3)):
                notes.append(f"{t}: net borç / FAVÖK {f.num(c['nd_ebitda'], 1)}")
            bad = c.get("analyst_bad") or []
            for x in bad[:2]:
                notes.append(f"{t}: {esc(x)}")
            if len(bad) > 2:
                notes.append(f"{t}: +{len(bad) - 2} analist aksiyonu daha (30 gün)")
        mult = f.num(float(sw.get("down_volume_mult", 1.5)), 1)
        heads = ["", "Hacim", "MA", "Borç", "Kâr+FCF", "Analist", "Geçen", "Alım seviyesine", "52W zirveden", "Bilanço"]
        th = "".join(f"<th>{h}</th>" for h in heads)
        legend = (f"Hacim: son {sw.get('down_volume_lookback', 5)} seansta hacmi 20G ortalamanın {mult} katını aşan düşüş günü yok · "
                  f"MA: fiyat MA200 üstünde{' ve MA50 üstünde' if sw.get('require_above_ma50') else ''} · "
                  f"Borç: net borç / FAVÖK &lt; {f.num(float(sw.get('max_net_debt_ebitda', 3)), 1)} · Kâr+FCF: net kâr ve serbest nakit akışı pozitif · "
                  f"Analist: son {sw.get('analyst_lookback_days', 30)} günde not indirimi ya da %{sw.get('target_cut_pct', 20)}+ hedef kesintisi yok")
        body = (f'<div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
                f'<p class="mono mute" style="font-size:11px;margin-top:10px;line-height:1.6">{legend}</p>')
        if notes:
            body += f'<div class="panel" style="margin-top:12px"><span class="k">Kalan kuralların dayanağı</span><ul class="tw">{"".join(f"<li>{x}</li>" for x in notes)}</ul></div>'
        return self.section(("Kurulum ", "tablosu"), "izleme listesi × swing kuralları · geçen kurala göre sıralı", body)

    # ── §03 AI value chain ──────────────────────────────────────────────────
    def chain(self):
        A, f = self.A, self.f
        keys = [k for k in ("neocloud", "memory", "optics", "power") if k in A]
        if not keys:
            return ""
        sox = A.get("sox")
        out, n = [], 1
        for k in keys:
            b = A[k]
            name, sub = BASKET_NAME[k]
            chips = "".join(f'<li><span>{NAMES.get(t, t)}</span><b class="mono {dc(self.tick(t)["w"])}">{f.pct(self.tick(t)["w"])}</b></li>'
                            for t in b["members"] if self.tick(t))
            for t in b.get("missing_members") or []:
                self.miss(f"{name} sepeti: {t} verisi yok — sepetten çıkarıldı")
            rebound = b["w"] is not None and b["m"] is not None and b["w"] > 0 and b["m"] < REBOUND_1M
            tag = '<span class="pill" style="margin-left:8px">tepki</span>' if rebound else ""
            wins = []
            for lab, key in (("1W", "w"), ("1M", "m"), ("3M", "q")):
                if b.get(key) is None:
                    self.miss(f"{name} sepeti {lab}: bir üyenin o pencerede verisi yok")
                    continue
                rel = (f'<span class="{dc(b[key] - sox[key])}">{f.pts(b[key] - sox[key])}</span>'
                       if sox and sox.get(key) is not None else "")
                wins.append(f'<tr><td>{lab}</td><td>{self.ch(b[key])}</td><td>{rel}</td></tr>')
            out.append(f'''<article class="link"><span class="n mono">0{n}</span><span class="k">{name}{tag}</span><h3>{sub}</h3>
  <div class="px {dc(b["w"])}">{f.pct(b["w"])}<small class="mono mute"> 1W</small></div>
  <table class="rel"><tr><th></th><th>getiri</th><th>SOX’a göre</th></tr>{"".join(wins)}</table>
  <ul class="chips">{chips}</ul></article>''')
            n += 1
        H1 = A.get("h100")
        if H1:
            out.append(f'''<article class="link gpu"><span class="n mono">0{n}</span><span class="k">GPU kirası · gösterge</span><h3>H100</h3>
  <div class="px">${f.num(H1["last"])}<small class="mono"> / saat</small></div>
  <div class="chg mono">{self.ch(H1["w"], suffix=" 1W")}{self.ch(H1["m"], suffix=" 1M") if H1.get("m") is not None else ""}</div>
  {spark(H1["series"], w=240, h=46, layers=3)}
  <span class="mono mute src">Düşük güvenilirlik: OKX'te tek, ince hacimli vadeli{(", " + f.long_date(H1["since"]) + "'den beri") if H1.get("since") else ""}. Sonuç çıkarılmaz.</span></article>''')
        ranked = sorted(keys, key=lambda k: A[k]["w"], reverse=True)
        best, worst = ranked[0], ranked[-1]
        read = (f"1W en güçlü halka <b>{BASKET_NAME[best][0].lower()}</b> ({f.pct(A[best]['w'])}), "
                f"en zayıf <b>{BASKET_NAME[worst][0].lower()}</b> ({f.pct(A[worst]['w'])}).")
        reb = [BASKET_NAME[k][0] for k in keys if A[k]["w"] > 0 and A[k]["m"] is not None and A[k]["m"] < REBOUND_1M]
        if reb:
            read += f" {', '.join(reb)}: pozitif hafta, ama 1M {f.pct(REBOUND_1M, 0)}'ten kötü — tepki olarak etiketlendi."
        meta = "eşit ağırlıklı sepetler · her pencere = üyelerin o penceredeki getirilerinin ortalaması"
        return self.section(("AI değer ", "zinciri"), meta, f'<div class="chain">{"".join(out)}</div><p class="read">{read}</p>')

    # ── §04 financing stress + macro (+ compact metals) ─────────────────────
    def macro(self):
        A, f = self.A, self.f
        drv = []
        if self.has("hy"):
            h = A["hy"]
            drv.append(("HY kredi makası", f.lvl(h["last"]), self.chbp(h["w_bp"], " 1W"),
                        f"ICE BofA ABD yüksek getirili endeks, Hazine'ye göre makas. 1M {f.bp(h['m_bp'])}"
                        + (f", 3M {f.bp(h['q_bp'])}" if h.get("q_bp") is not None else "")
                        + f"; 52 haftalık aralık {f.lvl(h['lo52'])} – {f.lvl(h['hi52'])}."))
        else:
            self.miss("HY kredi makası (FRED BAMLH0A0HYM2)")
        if self.has("us2y"):
            a = A["us2y"]
            fed = self.d.get("fed")
            tail = f" Fed {f.long_date(fed['date'])} toplantısı için indirim olasılığı {f.lvl(fed['p'], 0)} (Polymarket)." if fed else ""
            drv.append((self.n("us2y"), f.lvl(a["last"]), self.chbp(a["w_bp"], " 1W"), f"1M {f.bp(a['m_bp'])}.{tail}"))
        if self.has("us10y"):
            a = A["us10y"]
            txt = f"1M {f.bp(a['m_bp'])}."
            if self.has("real10", "be10"):
                r, b = A["real10"]["w_bp"], A["be10"]["w_bp"]
                part = "reel faizden" if abs(r) >= abs(b) else "enflasyon beklentisinden"
                txt = (f"Haftalık hareketin {f.bp(r)} kısmı reel faiz (şu an {f.lvl(A['real10']['last'])}), "
                       f"{f.bp(b)} kısmı başabaş enflasyon; ağırlık {part} geliyor.")
                if self.supports("gold", "real10"):
                    txt += f" Altın aynı hafta {f.pct(A['gold']['w'])}, korelasyon {f.num(self.d['corr']['gold_real'])}: ilişki bu hafta çalıştı."
            drv.append((self.n("us10y"), f.lvl(a["last"]), self.chbp(a["w_bp"], " 1W"), txt))
        if self.has("dxy"):
            a = A["dxy"]
            p52 = pos52(a)
            where = ("52 haftanın zirvesinde" if p52 >= .95 else "52 haftanın dibinde" if p52 <= .05
                     else f"52 haftalık aralığın %{f.num(p52 * 100, 0)} noktasında")
            txt = f"1M {f.pct(a['m'])}; {where}."
            if self.supports("gold", "dxy"):
                txt += f" Altın aynı hafta {f.pct(A['gold']['w'])}, korelasyon {f.num(self.d['corr']['gold_dxy'])}."
            drv.append((self.n("dxy"), f.num(a["last"]), self.ch(a["w"], suffix=" 1W"), txt))
        if self.has("vxn"):
            v = A["vxn"]
            above = v["last"] > v["ma50"]
            drv.append(("VXN", f.num(v["last"]), self.ch(v["w"], suffix=" 1W"),
                        f"50 günlük ortalaması {f.num(v['ma50'])}; {'üstünde' if above else 'altında'}."))
        body = "".join(f'<div class="drv"><span class="k">{k}</span><b>{v}</b><span class="mono">{ch}</span><p>{why}</p></div>'
                       for k, v, ch, why in drv)
        corr = self.corr_panel()
        metals = self.metals_compact() if (self.R.get("show_metals") or "compact") == "compact" else ""
        if not body and not corr and not metals:
            return ""
        return self.section(("Finansman stresi ", "ve makro"), "FRED · ICE · Cboe · korelasyon 63 seans",
                            f'<div class="drivers">{body}</div>{corr}{metals}')

    def corr_panel(self):
        f = self.f
        C = self.d.get("corr") or {}
        pairs = [("gold_real", "Altın × reel faiz", "faiz yükselince altın düşmeli", -1),
                 ("gold_dxy", "Altın × dolar", "dolar güçlenince altın düşmeli", -1),
                 ("ndx_10y", "Nasdaq × 10Y faiz", "faiz yükselince teknoloji düşmeli", -1),
                 ("ndx_gold", "Nasdaq × altın", "biri diğerini hedge ediyor mu", 0),
                 ("silver_copper", "Gümüş × bakır", "gümüş sanayi metali gibi mi davranıyor", 1)]
        items = []
        for k, name, test, expect in pairs:
            if k not in C:
                continue
            r = C[k]
            st = abs(r)
            word = "ilişki yok" if st < .2 else "zayıf" if st < .4 else "orta" if st < .7 else "güçlü"
            if st < .2:
                read = f"Bu dönemde {word}."
            else:
                dirw = "ters" if r < 0 else "aynı yönde"
                if expect == 0:
                    tail = " Aynı yönde hareket ediyorlar; biri diğerini hedge etmiyor." if r > 0 else " Ters yönde: hedge işlevi çalışıyor."
                else:
                    ok = sgn(r) == expect and st >= CORR_MIN
                    tail = " Ders kitabındaki ilişki çalışıyor." if ok else " Ders kitabındaki ilişki bu dönemde çalışmıyor."
                read = f"{word.capitalize()}, {dirw}." + tail
            sign = "+" if r >= 0 else "−"
            w = abs(r) * 50
            left = 50 if r >= 0 else 50 - w
            bar = f'<div class="cb"><span class="z"></span><i class="{"up" if r >= 0 else "dn"}" style="left:{left:.1f}%;width:{w:.1f}%"></i></div>'
            items.append(f'<li><div class="ch"><b>{name}</b><span class="mono">{sign}{f.num(abs(r))}</span></div>{bar}'
                         f'<p><span class="mute">{test.capitalize()}.</span> {read}</p></li>')
        if not items:
            return ""
        return (f'<div class="panel corr"><div class="ph"><span class="k">Korelasyon · son 63 seans, günlük değişim</span>'
                f'<span class="mono mute">−1 ters · 0 ilişkisiz · +1 birlikte</span></div><ul>{"".join(items)}</ul></div>')

    def metals_compact(self):
        A, f = self.A, self.f
        if not self.has("gold", "silver"):
            return ""
        cells = []
        for k, dec in (("gold", 0), ("silver", 2)):
            a = A[k]
            cells.append(f'<div class="panel"><span class="k">{self.n(k)}</span><div class="big">${f.num(a["last"], dec)}</div>'
                         f'<div class="chg mono">{self.ch(a["w"], suffix=" 1W")}{self.ch(a["m"], suffix=" 1M")}{self.ch(a["ytd"], suffix=" " + f.ylab(a))}</div>'
                         f'{spark(a["series"], w=400, h=60, layers=3)}</div>')
        if "gsr" in A:
            G = A["gsr"]
            rel = "kötü" if G["m"] > 0 else "iyi"
            cells.append(f'<div class="panel dark"><span class="k">Altın / gümüş oranı</span><div class="big">{f.num(G["last"], 1)}</div>'
                         f'<div class="chg mono">{self.ch(G["w"], suffix=" 1W")}{self.ch(G["m"], suffix=" 1M")}</div>'
                         f'<p>Oran 1M {f.pct(G["m"])}: gümüş son bir ayda altından {rel}.</p></div>')
        r = (self.d.get("corr") or {}).get("gold_dxy")
        if r is not None:
            cells.append(f'<div class="panel"><span class="k">Altın × dolar · 63 seans</span><div class="big">{"+" if r >= 0 else "−"}{f.num(abs(r))}</div>'
                         f'<p>{"Ters yönlü ilişki çalışıyor." if r <= -CORR_MIN else "Ters yönlü ilişki bu dönemde zayıf ya da yok."}</p></div>')
        return f'<div class="k subk">Metaller · tek kart</div><div class="metals">{"".join(cells)}</div>'

    # full metals mode keeps the two old sections
    def assets_full(self):
        A, f = self.A, self.f
        cards = []
        for key, sub, dec, cur in (("ndx", "NDX", 0, ""), ("gold", "XAU · ons", 0, "$"), ("silver", "XAG · ons", 2, "$")):
            if key not in A:
                continue
            a = A[key]
            rg = regime(a["last"], a["ma50"], a.get("ma200"))
            t = {"up": "Yükseliş trendi", "dn": "Düşüş trendi", "mix": "Kararsız"}[rg]
            ma200 = f'<div><dt>MA200</dt><dd>{cur}{f.num(a["ma200"], dec)}</dd></div>' if a.get("ma200") else ""
            cards.append(f'''<article class="asset"><header><div><h3>{self.n(key)}</h3><span class="mono mute">{sub}</span></div><span class="pill {rg if rg != 'mix' else ''}">{t}</span></header>
      <div class="px">{cur}{f.num(a["last"], dec)}</div>
      <div class="chg mono">{self.ch(a["w"], suffix=" 1W")}{self.ch(a["m"], suffix=" 1M")}{self.ch(a["ytd"], suffix=" " + f.ylab(a))}</div>
      {spark(a["series"], layers=4)}<div class="k" style="margin-top:2px">Son 5 seans</div>{bars5(a, f)}
      <dl class="lv"><div><dt>MA50</dt><dd>{cur}{f.num(a["ma50"], dec)}</dd></div>{ma200}</dl>
      <div class="r52"><span class="mono mute">52W</span>{rng(a)}<span class="mono">{cur}{f.num(a["lo52"], dec)} — {cur}{f.num(a["hi52"], dec)}</span></div></article>''')
        if not cards:
            return ""
        return self.section(("Üç varlık, ", "tek bakış"), "trend = fiyat vs MA50 / MA200", f'<div class="assets">{"".join(cards)}</div>')

    def metals_full(self):
        A, f = self.A, self.f
        panels = []
        if "gsr" in A:
            G = A["gsr"]
            panels.append(f'''<div class="panel dark"><span class="k">Altın / gümüş oranı</span><div class="big">{f.num(G["last"], 1)}</div>
      <div class="chg mono">{self.ch(G["w"], suffix=" 1W")}{self.ch(G["m"], suffix=" 1M")}</div>
      <p>Oran 1M {f.pct(G["m"])}: gümüş son bir ayda altından {"kötü" if G["m"] > 0 else "iyi"}.</p>{spark(G["series"], w=400, h=70, layers=4)}</div>''')
        if "cu_au" in A:
            CA = A["cu_au"]
            panels.append(f'''<div class="panel"><span class="k">Bakır / altın oranı</span><div class="big">{f.num(CA["last"], 2)}</div>
      <div class="chg mono">{self.ch(CA["w"], suffix=" 1W")}{self.ch(CA["m"], suffix=" 1M")}</div>
      <p>Oran 1M {f.pct(CA["m"])}: bakır son bir ayda altından {"iyi" if CA["m"] > 0 else "kötü"}.</p>{spark(CA["series"], w=400, h=70, fill=False)}</div>''')
        for key, lab in (("sil_silver", "Gümüş madencileri / gümüş (SIL)"), ("gdx_gold", "Madenciler / altın (GDX)")):
            if key in A:
                M = A[key]
                panels.append(f'''<div class="panel"><span class="k">{lab}</span><div class="big {dc(M["w"])}">{f.pct(M["w"])}</div>
      <div class="chg mono"><span class="mute">1 hafta, göreli</span>{self.ch(M["m"], suffix=" 1M")}</div>
      <p>Madenciler bu hafta metalden {"iyi" if M["w"] > 0 else "kötü"}; ayda {f.pct(M["m"])}.</p></div>''')
        read = ""
        if self.has("cu_au", "gsr"):
            cu, gs = A["cu_au"]["m"], A["gsr"]["m"]
            if cu > 0 and gs > 0:
                read = (f"Çelişki: bakır altından iyi gidiyor (bakır/altın 1M {f.pct(cu)}) ama gümüş altından kötü (altın/gümüş 1M {f.pct(gs)}). "
                        "İki oran aynı yönü göstermiyor; ikisinden de tek başına büyüme sonucu çıkarılmaz.")
            elif cu < 0 and gs < 0:
                read = (f"Çelişki: gümüş altından iyi gidiyor (altın/gümüş 1M {f.pct(gs)}) ama bakır altından kötü (bakır/altın 1M {f.pct(cu)}). "
                        "İki oran aynı yönü göstermiyor.")
        if not panels:
            return ""
        return self.section(("Metallerin ", "içi"), "oranlar ve madenciler · hepsi USD",
                            f'<div class="metals">{"".join(panels)}</div>' + (f'<p class="read">{read}</p>' if read else ""))

    # ── §05 earnings ────────────────────────────────────────────────────────
    def earnings(self):
        f = self.f
        today = date.fromisoformat(self.d["today"])
        names = sorted(self.held() | self.wl())
        up, past = [], []
        for t in names:
            c = self.CO.get(t) or {}
            nx = c.get("next")
            if nx and (date.fromisoformat(nx["d"]) - today).days <= 14:
                up.append((nx["d"], t, nx))
            if c.get("reported"):
                past.append((c["reported"]["d"], t, c["reported"]))
        parts = []
        if up:
            trs = []
            for d, t, nx in sorted(up):
                sess = {"bmo": "açılış öncesi", "amc": "kapanış sonrası"}.get(nx.get("sess"), "")
                if not sess:
                    self.miss(f"{t}: bilanço saati")
                eps = f.usd(nx["eps"]) if nx.get("eps") is not None else ""
                im = f"±{f.pct(nx['im'], 1, sign=False)}" if nx.get("im") is not None else ""
                rv = {"up": '<span class="up">yukarı</span>', "dn": '<span class="dn">aşağı</span>', "flat": "yatay"}.get(nx.get("rev30"), "")
                if not rv:
                    self.miss(f"{t}: 30 günlük EPS revizyonu")
                own = " · portföy" if t in self.held() else ""
                trs.append(f'<tr><th>{NAMES.get(t, t)}<small>{t}{own}</small></th><td class="n">{f.day(d)}</td><td class="n">{sess}</td>'
                           f'<td class="n">{eps}</td><td class="n">{im}</td><td class="n">{rv}</td></tr>')
            th = "".join(f"<th>{h}</th>" for h in ("", "Tarih", "Saat", "EPS beklentisi", "Opsiyon ima hareketi", "EPS revizyonu · 30G"))
            parts.append(f'<div class="k subk">Önümüzdeki 14 gün</div><div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
        else:
            parts.append('<p class="note">Önümüzdeki 14 günde portföyde ya da izleme listesinde bilanço yok.</p>')
        if past:
            trs = []
            for d, t, r in sorted(past):
                sur = self.ch(r["surprise"]) if r.get("surprise") is not None else ""
                rea = self.ch(r["react"]) if r.get("react") is not None else ""
                if r.get("react") is None:
                    self.miss(f"{t}: bilanço sonrası fiyat tepkisi (açıklama saati bilinmiyor)")
                trs.append(f'<tr><th>{NAMES.get(t, t)}<small>{t}</small></th><td class="n">{f.day(d)}</td><td class="n">{sur}</td><td class="n">{rea}</td></tr>')
            th = "".join(f"<th>{h}</th>" for h in ("", "Tarih", "EPS sürprizi", "Ertesi seans tepkisi"))
            parts.append(f'<div class="k subk">Geçen hafta açıklayanlar</div><div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
        return self.section(("Bilan", "çolar"), "yalnızca portföy ve izleme listesi · ima hareketi = bilanço sonrası ilk vadede ATM straddle", "".join(parts))

    # ── §06 news ────────────────────────────────────────────────────────────
    def news(self):
        items = self.d.get("news") or []
        if not items:
            self.miss("Haberler: news.yaml boş ya da yok (Grokbot bildirimleri elle eklenir)")
            return ""
        lis = []
        for it in items[:5]:
            tag = (it.get("tag") or "").lower()
            tag_l = "tez" if tag == "tez" else "gürültü"
            cls = "up" if tag == "tez" else ""
            url = it.get("url") or ""
            title = esc(it.get("title", ""))
            link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
            tk = f' <span class="mono mute">{esc(it["ticker"])}</span>' if it.get("ticker") else ""
            lis.append(f'<li><span class="pill {cls}">{tag_l}</span><div><b>{link}</b>{tk}</div></li>')
        return self.section(("Tezi değiştiren ", "haberler"), "en fazla beş · kaynak: news.yaml", f'<ul class="news">{"".join(lis)}</ul>')

    # ── §07 positioning ─────────────────────────────────────────────────────
    def positioning(self):
        f = self.f
        parts = []
        pc = self.P.get("pc")
        if pc:
            parts.append(f'''<div class="pair">
  <div class="panel"><span class="k">Toplam put/call · Cboe</span><b>{f.num(pc["total"])}</b><span class="mono mute">{pc["n"]} seans ort. {f.num(pc["total10"])} · {f.day(pc["date"])}</span></div>
  <div class="panel"><span class="k">Hisse put/call · Cboe</span><b>{f.num(pc["equity"])}</b><span class="mono mute">{pc["n"]} seans ort. {f.num(pc["equity10"])}</span></div>
</div>''')
        rows = []
        for t in sorted(self.held() | self.wl()):
            c = self.CO.get(t) or {}
            if c.get("short") is None:
                self.miss(f"{t}: açığa satış oranı")
                continue
            rows.append((c["short"], t, c.get("short_date")))
        if rows:
            rows.sort(reverse=True)
            trs = "".join(f'<tr><th>{NAMES.get(t, t)}<small>{t}{" · portföy" if t in self.held() else ""}</small></th>'
                          f'<td class="n">{f.lvl(s, 1)}</td><td class="n">{f.day(d) if d else ""}</td></tr>' for s, t, d in rows)
            parts.append(f'<div class="k subk">Açığa satış · halka açık payın yüzdesi</div><div class="tblw"><table class="board p" style="min-width:420px">'
                         f'<thead><tr><th></th><th>Açığa satış</th><th>Rapor tarihi</th></tr></thead><tbody>{trs}</tbody></table></div>')
        if not parts:
            return ""
        return self.section(("Konum", "lanma"), "Cboe günlük istatistik · açığa satış: borsa raporu (ayda iki kez)", "".join(parts))

    # ── §08 Asia ────────────────────────────────────────────────────────────
    def asia(self):
        A, f = self.A, self.f
        rows = [("kospi", "Kore · Samsung, SK hynix", 0), ("twii", "Tayvan · TSMC", 0), ("n225", "Japonya · çip ekipmanı", 0), ("usdjpy", "yen", 2)]
        rows = [r for r in rows if r[0] in A]
        if not rows:
            return ""
        cards = "".join(f'''<div class="panel{' dark' if k == 'usdjpy' else ''}"><span class="k">{sub}</span><h3>{self.n(k)}</h3>
  <div class="big">{f.num(A[k]["last"], d)}</div>
  <div class="chg mono">{self.ch(A[k]["w"], suffix=" 1W")}{self.ch(A[k]["m"], suffix=" 1M")}{self.ch(A[k]["ytd"], suffix=" YTD")}</div>
  {spark(A[k]["series"], w=300, h=56, fill=k != "usdjpy", layers=0 if k == "usdjpy" else 3)}</div>''' for k, sub, d in rows)
        read = ""
        if self.has("kospi", "sox"):
            read = f"1M: KOSPI {f.pct(A['kospi']['m'])}, SOX {f.pct(A['sox']['m'])}; fark {f.pts(A['kospi']['m'] - A['sox']['m'])}."
        return self.section(("Asya çip ", "ekseni"), "KOSPI · TAIEX · Nikkei · USD/JPY", f'<div class="asia">{cards}</div>' + (f'<p class="read">{read}</p>' if read else ""))

    # ── §09 breadth ─────────────────────────────────────────────────────────
    def breadth(self):
        A, f = self.A, self.f
        mine = self.held() | self.wl()
        m7 = [k for k in ("nvda", "aapl", "msft", "googl", "amzn", "meta", "tsla") if k in A and k.upper() in mine]
        left = ""
        if m7:
            m7.sort(key=lambda k: A[k]["w"])
            mx = max(abs(A[k]["w"]) for k in m7) or 1
            lis = "".join(f'''<li><span class="nm">{self.n(k)}</span><span class="mono px2">${f.num(A[k]["last"])}</span>
  <div class="hb"><span class="z"></span><i class="{dc(A[k]["w"])}" style="{"left:50%" if A[k]["w"] >= 0 else "right:50%"};width:{abs(A[k]["w"]) / mx * 50:.1f}%"></i></div>
  <span class="mono {dc(A[k]["w"])}">{f.pct(A[k]["w"])}</span><span class="mono mute ytd">{f.pct(A[k]["ytd"], 0)} YTD</span></li>''' for k in m7)
            left = f'<div class="panel"><div class="ph"><span class="k">Muhteşem 7 · portföy ve izleme listesindekiler</span><span class="mono mute">1W sıralı</span></div><ul class="m7">{lis}</ul></div>'
        right = ""
        if "ew_cw" in A:
            ew = A["ew_cw"]
            better = ew["m"] > 0
            txt = (f"Eşit ağırlıklı Nasdaq (QQQE), QQQ'dan son bir ayda <b>{f.pct(abs(ew['m']), 1, sign=False)}</b> iyi." if better else
                   f"QQQ, eşit ağırlıklı Nasdaq'tan (QQQE) son bir ayda <b>{f.pct(abs(ew['m']), 1, sign=False)}</b> iyi: endeksi büyükler taşıyor.")
            right += (f'<div class="panel dark"><span class="k">Genişlik · eşit ağırlık / piyasa değeri</span>'
                      f'<div class="big2">{self.ch(ew["m"])}<small class="mono">1 ay</small></div><p>{txt}</p>{spark(ew["series"], w=500, h=70, layers=4)}</div>')
        pair = ""
        if "sox_ndx" in A:
            sx = A["sox_ndx"]
            pair += (f'<div class="panel"><span class="k">SOX / Nasdaq</span><b class="{dc(sx["w"])}">{f.pct(sx["w"])}</b>'
                     f'<span class="mono mute">1 hafta</span></div>')
        vol = (self.d.get("vol") or {}).get("qqq")
        if vol:
            pair += f'<div class="panel"><span class="k">QQQ hacmi</span><b>{f.num(vol)}×</b><span class="mono mute">60 günlük ortalamaya göre</span></div>'
        if pair:
            right += f'<div class="pair">{pair}</div>'
        if not left and not right:
            return ""
        body = f'<div class="split">{left}<div class="stack">{right}</div></div>' if left else f'<div class="stack">{right}</div>'
        return self.section(("Genişlik", ""), "eşit ağırlık · SOX/Nasdaq · hacim", body)

    # ── §10 calendar ────────────────────────────────────────────────────────
    def calendar(self):
        f = self.f
        cal = []
        for e in self.d.get("calendar", []):
            if e.get("impact") != "high":
                continue
            ev = e["event"]
            name = CAL_TR.get(ev, ev)
            if ev not in CAL_TR and "Speaks" in ev:
                name = ev.replace("Fed Chairman", "Fed Başkanı").replace("FOMC Member", "FOMC üyesi").replace(" Speaks", " konuşuyor")
            pe = ""
            pv, es = e.get("prev"), e.get("est")
            bits = []
            if pv not in (None, "—", ""):
                bits.append(f"önceki {esc(str(pv).replace('.', ','))}")
            if es not in (None, "—", ""):
                bits.append(f"beklenti {esc(str(es).replace('.', ','))}")
            if bits:
                pe = f'<span class="mono mute">{" · ".join(bits)}</span>'
            wd = e.get("wd")
            if wd is None and e.get("cet_date"):
                wd = date.fromisoformat(e["cet_date"]).weekday()
            when = f'{f.s["days"][wd]} {esc(e.get("time", ""))}' if wd is not None else esc(e.get("time", ""))
            cal.append(f'<li><span class="mono when">{when}</span><div><b>{esc(name)}</b>{pe}</div><span class="imp high"></span></li>')
        fed = self.d.get("fed")
        fed_html = ""
        if fed:
            when = f.long_date(fed["date"])
            fed_html = (f'<div class="panel dark"><span class="k">Fed · {when}</span>'
                        f'<div class="big" style="margin-top:12px">{f.lvl(fed["p"], 0)}</div><span class="mono" style="color:rgba(236,234,227,.6)">'
                        f'faiz indirimi olasılığı · Polymarket</span></div>')
        if not cal and not fed_html:
            self.miss("Takvim: nocashflow.net calendar.json / Fed olasılığı")
            return ""
        cal_html = f'<ul class="cal">{"".join(cal[:8])}</ul>' if cal else '<p class="note">Takvimde bu hafta yüksek etkili ABD verisi yok.</p>'
        return self.section(("Tak", "vim"), "CET · yüksek etkili ABD verisi · Fed", f'<div class="split">{cal_html}{fed_html}</div>')

    # ── §11 scorecard ───────────────────────────────────────────────────────
    def scorecard(self):
        f = self.f
        prev = self.d.get("prev_issue")
        if not prev or not prev.get("rows"):
            self.miss("Karne: önceki sayı yok (history/ boş) — ilk sayıdan sonra dolacak")
            return ""
        lis = []
        for r in prev["rows"]:
            a = self.A.get(r["key"])
            closes = [(d, v) for d, v in (a or {}).get("week", []) if d > prev["cut"]]
            if not closes:
                self.miss(f"Karne: {r['text']} — bu haftanın kapanışları yok")
                continue
            lvl = r["level"]
            if r["dir"] == "below":
                d, v = min(closes, key=lambda x: x[1])
                broke = v < lvl
                why = f"Haftanın en düşük kapanışı {f.num(v)} ({f.day(d)}); seviye {f.num(lvl)}."
            else:
                d, v = max(closes, key=lambda x: x[1])
                broke = v > lvl
                why = f"Haftanın en yüksek kapanışı {f.num(v)} ({f.day(d)}); seviye {f.num(lvl)}."
            mark = '<b class="dn">✗</b>' if broke else '<b class="up">✓</b>'
            verdict = "tutmadı — seviye kapanışta geçildi" if broke else "tuttu — seviye kapanışta geçilmedi"
            lis.append(f'<li>{mark}<div><b>{esc(r["text"])}</b><p>{verdict}. {why}</p></div></li>')
        if not lis:
            return ""
        return self.section(("Geçen sayının ", "karnesi"), f"{f.long_date(prev['cut'])} sayısının “bu hafta” satırları",
                            f'<ul class="karne">{"".join(lis)}</ul>')

    # ── §12 board ───────────────────────────────────────────────────────────
    def board(self):
        A, f = self.A, self.f
        groups = [("Hisseler", [("ndx", 0, ""), ("spx", 0, ""), ("sox", 0, "")]),
                  ("Metaller", [("gold", 0, "$"), ("silver", 2, "$"), ("copper", 2, "$")]),
                  ("Dolar", [("dxy", 2, "")]),
                  ("Oynaklık & kripto", [("vix", 2, ""), ("vxn", 2, ""), ("btc", 0, "$")])]
        rows = []
        for grp, items in groups:
            items = [i for i in items if i[0] in A]
            if not items:
                continue
            rows.append(f'<tr class="g"><td colspan="8">{grp}</td></tr>')
            for k, dec, cur in items:
                a = A[k]
                d200 = (a["last"] / a["ma200"] - 1) * 100 if a.get("ma200") else None
                rows.append(f'''<tr><th>{self.n(k)}</th><td class="n">{cur}{f.num(a["last"], dec)}</td>
          <td class="n">{self.ch(a["w"])}</td><td class="n">{self.ch(a["m"])}</td><td class="n">{self.ch(a["ytd"])}</td>
          <td class="n">{self.ch(d200)}</td><td class="rc">{rng(a)}</td><td class="sc">{spark(a["series"], w=120, h=28, fill=False, dot=False, sw=1.5)}</td></tr>''')
        rates = [k for k in ("us2y", "us10y", "real10", "be10", "s2s10", "hy") if k in A]
        if rates:
            rows.append('<tr class="g"><td colspan="8">Faiz ve makas <span class="mute">· değişimler baz puan</span></td></tr>')
            for k in rates:
                a = A[k]
                last = f"{f.num(a['last'] * 100, 0)}bp" if k == "s2s10" else f.lvl(a["last"])
                rows.append(f'''<tr><th>{self.n(k)}</th><td class="n">{last}</td><td class="n">{self.chbp(a["w_bp"])}</td>
      <td class="n">{self.chbp(a.get("m_bp"))}</td><td class="n">{self.chbp(a.get("ytd_bp"))}</td><td class="n">{self.chbp(a.get("d200_bp"))}</td>
      <td class="rc">{rng(a)}</td><td class="sc">{spark(a["series"], w=120, h=28, fill=False, dot=False, sw=1.5)}</td></tr>''')
        if not rows:
            return ""
        th = "".join(f"<th>{h}</th>" for h in ("", "Son", "1W", "1M", "YTD", "vs MA200", "52W aralık", "1 yıl"))
        body = f'<div class="tblw"><table class="board"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        return self.section(("Ek: piyasa ", "panosu"), f"kesim {f.long_date(self.d['cut'])}", body)

    # ── §13 crypto ──────────────────────────────────────────────────────────
    def crypto(self):
        A, f = self.A, self.f
        parts = []
        if "btc" in A:
            b = A["btc"]
            parts.append(f'<span><b>Bitcoin</b><span class="mono">${f.num(b["last"], 0)} {self.ch(b["w"], suffix=" 1W")} · {self.ch(b["ytd"], suffix=" YTD")}</span></span>')
        fg = self.d.get("fg")
        if fg and fg.get("px"):
            lab = {"Extreme Fear": "Aşırı korku", "Fear": "Korku", "Neutral": "Nötr", "Greed": "Açgözlülük",
                   "Extreme Greed": "Aşırı açgözlülük"}.get(fg.get("chg", ""), fg.get("chg", ""))
            parts.append(f'<span><b>Korku &amp; Açgözlülük</b><span class="mono">{esc(fg["px"])} · {esc(lab)}</span></span>')
        if not parts:
            return ""
        return self.section(("Kripto ", "köşesi"), "kısaca", f'<div class="strip">{"".join(parts)}</div>')

    # ── page ────────────────────────────────────────────────────────────────
    def render(self):
        f = self.f
        hd = self.headline()
        css = open(os.path.join(HERE, "style.css")).read()
        hero = ""
        if hd:
            hero = f'''<section class="hero">
  <span class="k">Haftanın tek cümlesi</span>
  <h1>{hd["h1"]} — <i>{hd["h2"]}</i></h1>
  <p class="lede">{self.lede()}</p>
  <div class="chart"><div class="lab"><span class="k">{hd["lab"]}</span><b>{hd["val"]}</b></div>{spark(hd["series"], w=1000, h=150, layers=9)}</div>
</section>'''
        k5 = "".join(f'<div><span class="k">{a}</span><b class="{c}">{b}</b><span class="mono mute">{x}</span></div>' for a, b, x, c in self.key5())
        full = (self.R.get("show_metals") or "compact") == "full"
        sections = [self.decision(), self.setups(), self.chain(), self.macro()]
        if full:
            sections += [self.assets_full(), self.metals_full()]
        sections += [self.earnings(), self.news(), self.positioning(), self.asia(), self.breadth(),
                     self.calendar(), self.scorecard(), self.board(), self.crypto()]
        body = "".join(sections)
        lag = [f"{MISSING_NAME.get(k, k.upper())} ({f.day(a['date'])})" for k, a in self.A.items() if a.get("date") and a["date"] < self.d["cut"]]
        if lag:
            self.miss("Kesimden önce biten seriler — son yayımlanan değer kullanıldı: " + ", ".join(lag))
        for k in self.d.get("report_missing") or []:
            self.miss(MISSING_NAME.get(k, k.upper()))
        for m in self.P.get("missing") or []:
            self.miss(m)
        example = self.d.get("example_files") or []
        banner = (f'<p class="note" style="margin-bottom:18px"><b>Örnek veriyle üretildi:</b> {", ".join(example)} bulunamadı; '
                  f'{", ".join(x.replace(".yaml", ".example.yaml") for x in example)} kullanıldı. Pozisyonlar ve seviyeler gerçek değil.</p>') if example else ""
        miss = (f'<div class="note missing"><b>Eksik veri</b> · bu sayıda gösterilmeyenler<ul>{"".join(f"<li>{esc(m)}</li>" for m in self.missing)}</ul></div>'
                if self.missing else "")
        cut = f.long_date(self.d["cut"])
        return f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NO/CASHFLOW · Haftalık karar bülteni · {cut}</title>
<meta name="robots" content="noindex,nofollow">
<link rel="icon" href="https://nocashflow.net/favicon.svg?v=4" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500&display=swap">
<style>{css}</style></head><body><div class="wrap">
<div class="top"><span class="wm">NO<b>/</b>CASHFLOW</span><span class="eyebrow"><em>Haftalık karar bülteni</em> · kesim: {cut} Cuma kapanışı</span></div>
{banner}{hero}
<div class="key5">{k5}</div>
{body}
{miss}
<footer><span class="wm">NO<b>/</b>CASHFLOW</span><p>Kişisel karar bülteni; yatırım tavsiyesi değildir. Koşullar rules.yaml'dan, pozisyonlar portfolio.yaml'dan okunur. Tüm getiriler {cut} Cuma kapanışına göre. Veriler: Yahoo Finance, FRED, ICE BofA, Cboe, OKX, Polymarket, Forex Factory.</p></footer>
</div></body></html>'''


def render(data, lang="tr", web_url=None):
    b = Bulletin(data, lang)
    html = b.render()
    return html, b.week_rows
