"""Weekly bulletin v2 — personal decision edition (TR, EN).

One reader. The page answers "what am I doing this week", not "what did the
market do". Layout and styling are the approved Liquid demo; only content
changed. Rules every sentence follows:

  * it rests on a number printed on the page;
  * a cause is named only when the driver's change over the same period AND
    its correlation with the target both point that way (`supports`);
  * one week of price is never called a flow; a positive week after a 1M
    loss worse than −15% is labelled "tepki" / "rebound";
  * conditions, not advice: "X closes below Y → the stop triggers";
  * a threshold is never the current value itself;
  * a value that cannot be fetched is not printed: the row/box is left out
    and named in the missing-data note at the bottom.

Every visible string goes through `Bulletin.t(tr, en)`; the logic is shared.
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
           "bn": " mr", "mn": " mn",
           "dayfull": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]},
    "en": {"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
           "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
           "bn": "bn", "mn": "m",
           "dayfull": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]},
}

_COMMON = {"ndx": "Nasdaq 100", "spx": "S&P 500", "vix": "VIX", "vxn": "VXN", "btc": "Bitcoin",
           "kospi": "KOSPI", "twii": "TAIEX", "n225": "Nikkei 225", "usdjpy": "USD/JPY",
           "nvda": "Nvidia", "aapl": "Apple", "msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "tsla": "Tesla",
           "qqq": "QQQ", "qqqe": "QQQE", "smh": "SMH", "igv": "IGV", "nasa": "NASA", "ew_cw": "QQQE/QQQ", "sox_ndx": "SOX/Nasdaq"}
NAME = {
    "tr": {**_COMMON, "sox": "Yarı iletken (SOX)", "gold": "Altın", "silver": "Gümüş", "copper": "Bakır", "dxy": "Dolar endeksi",
           "us2y": "ABD 2Y", "us10y": "ABD 10Y", "real10": "10Y reel faiz", "be10": "10Y başabaş enflasyon",
           "s2s10": "2s10s eğim", "hy": "HY kredi makası"},
    "en": {**_COMMON, "sox": "Semiconductors (SOX)", "gold": "Gold", "silver": "Silver", "copper": "Copper", "dxy": "Dollar index",
           "us2y": "US 2Y", "us10y": "US 10Y", "real10": "10Y real yield", "be10": "10Y breakeven inflation",
           "s2s10": "2s10s slope", "hy": "HY credit spread"},
}
MISSING_NAME = {
    "tr": {**NAME["tr"], "optics": "Optik sepeti", "neocloud": "Neocloud sepeti", "memory": "Bellek sepeti",
           "power": "Enerji sepeti", "h100": "H100 kirası", "b200": "B200 kirası", "gsr": "Altın/gümüş oranı",
           "gdx_gold": "GDX/altın", "sil_silver": "SIL/gümüş", "cu_au": "Bakır/altın"},
    "en": {**NAME["en"], "optics": "Optics basket", "neocloud": "Neocloud basket", "memory": "Memory basket",
           "power": "Power basket", "h100": "H100 rental", "b200": "B200 rental", "gsr": "Gold/silver ratio",
           "gdx_gold": "GDX/gold", "sil_silver": "SIL/silver", "cu_au": "Copper/gold"},
}

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

BASKET_NAME = {
    "tr": {"neocloud": ("Neocloud", "GPU kiralayan şirketler · hisse fiyatı"), "memory": ("Bellek", "HBM ve NAND"),
           "optics": ("Optik", "veri merkezi bağlantısı"), "power": ("Enerji", "şebeke, yakıt hücresi, nükleer")},
    "en": {"neocloud": ("Neocloud", "GPU-renting clouds · share price"), "memory": ("Memory", "HBM and NAND"),
           "optics": ("Optics", "data-centre connectivity"), "power": ("Power", "grid, fuel cells, nuclear")},
}
# regime labels in the example rules.yaml; a real file may set label_en per state
REGIME_EN = {"Risk açık": "Risk on", "Temkinli": "Cautious", "Savunma": "Defensive", "Risk kapalı": "Risk off"}
# fragments of personal.py's Turkish missing-data notes / analyst notes
MISS_EN = [("net borç / FAVÖK", "net debt / EBITDA"), ("kâr / serbest nakit akışı", "profit / free cash flow"),
           ("şirket verisi", "company data"), ("analist aksiyonları", "analyst actions"),
           ("bilanço tarihleri", "earnings dates"), ("EPS revizyonu", "EPS revision"),
           ("opsiyon ima hareketi", "options-implied move"), ("Put/call oranı (CBOE)", "Put/call ratio (Cboe)"),
           ("not indirimi", "downgrade"), ("hedef ", "target ")]
REBOUND_1M = -15.0          # a positive week after a 1M worse than this is a "tepki" / "rebound"
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
        """Signed percent; a value that rounds to zero is printed bare: %0,0 / 0.0%."""
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
        unit = " puan" if self.l == "tr" else " pts"
        if round(abs(v), dec) == 0:
            return f"{self.num(0, dec)}{unit}"
        return ("+" if v > 0 else "−") + f"{self.num(abs(v), dec)}{unit}"

    def usd(self, v, dec=2):
        return ("−" if v < 0 else "") + "$" + self.num(abs(v), dec)

    def day(self, iso):
        d = date.fromisoformat(iso)
        if self.l == "en":
            return f"{self.s['days'][d.weekday()]} {self.s['months'][d.month - 1]} {d.day}"
        return f"{self.s['days'][d.weekday()]} {d.day:02d}.{d.month:02d}"

    def long_date(self, iso):
        d = date.fromisoformat(iso)
        m = self.s["months"][d.month - 1]
        return f"{d.day} {m} {d.year}" if self.l == "tr" else f"{m} {d.day}, {d.year}"

    def ylab(self, a):
        if a.get("since"):
            d = date.fromisoformat(a["since"])
            if self.l == "en":
                return f"since {self.s['months'][d.month - 1]} {d.day}"
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
        self.l = lang if lang in S else "tr"
        self.f = F(self.l)
        self.num = 0
        self.missing = []
        self.week_rows = []          # §01 "this week" rows, stored for next week's scorecard (always TR text)

    # helpers
    def t(self, tr, en):
        return en if self.l == "en" else tr

    def tx(self, s):
        """Translate a Turkish note produced outside the renderer (personal.py)."""
        if self.l != "en":
            return s
        for a, b in MISS_EN:
            s = s.replace(a, b)
        return s

    def has(self, *keys):
        return all(k in self.A for k in keys)

    def n(self, key):
        return NAME[self.l].get(key, key.upper())

    def bn(self, k):
        return BASKET_NAME[self.l][k]

    def rlabel(self, st):
        lab = st.get("label", "")
        if self.l == "en":
            return st.get("label_en") or REGIME_EN.get(lab, lab)
        return lab

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

    def above(self, up):
        return self.t("üstünde", "above") if up else self.t("altında", "below")

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
        A, f, t = self.A, self.f, self.t
        cands = [(abs(zmove(A[k])), k) for k in ("ndx", "gold", "silver", "dxy", "us2y", "real10", "hy") if k in A]
        if not cands:
            return None
        _, k = max(cands)
        a = A[k]
        name = self.n(k)
        lab = f"{name} · " + t("1 yıl", "1 year")
        if is_rate(a):
            mv, mm = a.get("w_bp") or 0, a.get("m_bp")
            h1 = f"{name} {f.lvl(a['last'])}"
            if k == "real10" and self.supports("gold", "real10"):
                g, r = f.pct(A['gold']['w']), f.num(self.d['corr']['gold_real'])
                h2 = t(f"altın aynı hafta {g}; korelasyon {r}.", f"gold {g} the same week; correlation {r}.")
            else:
                h2 = (t(f"haftada {f.bp(mv)}", f"{f.bp(mv)} on the week")
                      + ((t(f", ayda {f.bp(mm)}.", f", {f.bp(mm)} on the month.")) if mm is not None else "."))
            return {"k": k, "h1": h1, "h2": h2, "series": a["series"], "lab": lab, "val": f.lvl(a["last"])}
        p = pos52(a)
        h1 = t(f"{name} haftada {f.pct(a['w'])}", f"{name} {f.pct(a['w'])} on the week")
        if p >= .95:
            h2 = t("52 haftanın zirvesinde.", "at its 52-week high.")
        elif p <= .05:
            h2 = t("52 haftanın dibinde.", "at its 52-week low.")
        elif a.get("ma200"):
            d = (a["last"] / a["ma200"] - 1) * 100
            dd = f.pct(abs(d), 1, sign=False)
            h2 = t(f"MA200'ün {dd} {self.above(d > 0)}.", f"{dd} {self.above(d > 0)} its MA200.")
        else:
            h2 = t(f"ayda {f.pct(a['m'])}.", f"{f.pct(a['m'])} on the month.")
        dec = 0 if k in ("ndx", "gold") else 2
        cur = "$" if k in ("gold", "silver") else ""
        return {"k": k, "h1": h1, "h2": h2, "series": a["series"], "lab": lab, "val": cur + f.num(a["last"], dec)}

    def lede(self):
        A, f, t = self.A, self.f, self.t
        out = []
        if self.has("ndx", "gold", "silver"):
            n, g, s = f.pct(A['ndx']['w']), f.pct(A['gold']['w']), f.pct(A['silver']['w'])
            out.append(t(f"Nasdaq 100 haftayı {n}, altın {g}, gümüş {s} ile kapattı.",
                         f"Nasdaq 100 ended the week {n}, gold {g}, silver {s}."))
        if self.has("sox", "ndx"):
            lead = f.pts(A["sox"]["w"] - A["ndx"]["w"])
            sx = f.pct(A['sox']['w'])
            out.append(t(f"Yarı iletkenler {sx}; Nasdaq'a göre {lead}.", f"Semiconductors {sx}; {lead} versus the Nasdaq."))
        if self.has("real10"):
            b, lv = f.bp(A['real10']['w_bp']), f.lvl(A['real10']['last'])
            out.append(t(f"10 yıllık reel faiz haftada {b}, şu an {lv}.", f"The 10-year real yield moved {b} on the week, now {lv}."))
        if self.has("hy"):
            lv, b = f.lvl(A['hy']['last']), f.bp(A['hy']['w_bp'])
            out.append(t(f"HY kredi makası {lv}, haftada {b}.", f"The HY credit spread is {lv}, {b} on the week."))
        return " ".join(out)

    def key5(self):
        A, f, t = self.A, self.f, self.t
        items = []
        for k in ("ndx", "gold", "silver"):
            if k in A:
                items.append((self.n(k), f.pct(A[k]["w"]), "1W", dc(A[k]["w"])))
        for k, lab in (("real10", t("Reel faiz", "Real yield")), ("hy", t("HY makası", "HY spread"))):
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
            tk = p["ticker"].upper()
            a = self.tick(tk)
            if not a:
                self.miss(self.t(f"{tk}: kesim fiyatı yok — portföy satırı ve hisse oranı hesaplanmadı",
                                 f"{tk}: no price at the cut — portfolio row and equity share not computed"))
                return None, None
            v = a["last"] * float(p["shares"])
            rows.append({**p, "t": tk, "a": a, "value": v})
            total += v
        cash = float(self.PF.get("cash") or 0)
        return rows, total + cash

    def decision(self):
        A, f, t = self.A, self.f, self.t
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
            mx = f.lvl(float(st["max_equity_pct"]), 0)
            d_ndx = (A["ndx"]["last"] / A["ndx"]["ma200"] - 1) * 100
            d_vxn = (A["vxn"]["last"] / A["vxn"]["ma50"] - 1) * 100
            cash, tot = f.usd(float(self.PF.get("cash") or 0), 0), f.usd(nav, 0) if nav else ""
            cur = (f'<div class="big">{f.lvl(eq_pct, 1)}</div><span class="mono mute priv">{t("nakit", "cash")} {cash} · {t("toplam", "total")} {tot}</span>'
                   if eq_pct is not None else f'<p>{t("Hisse oranı hesaplanamadı (eksik fiyat).", "Equity share could not be computed (missing price).")}</p>')
            gap = ""
            if eq_pct is not None:
                diff = eq_pct - float(st["max_equity_pct"])
                side = (t("sınırın üstünde", "above the limit") if diff > 0 else t("sınırın altında", "below the limit") if diff < 0 else "")
                gap = f'<p>{t("Fark", "Gap")}: <b>{f.pts(diff)}</b> {side}.</p>'
            pn, pv = f.pct(abs(d_ndx), 1, sign=False), f.pct(abs(d_vxn), 1, sign=False)
            why = t(f"Nasdaq 100 MA200'ün {pn} {self.above(d_ndx > 0)}; VXN MA50'sinin {pv} {self.above(d_vxn > 0)}.",
                    f"Nasdaq 100 is {pn} {self.above(d_ndx > 0)} its MA200; VXN is {pv} {self.above(d_vxn > 0)} its MA50.")
            parts.append(f'''<div class="regime">
  <div class="panel dark"><span class="k">{t("Rejim · bu hafta", "Regime · this week")}</span><div class="big" style="margin-top:12px">{esc(self.rlabel(st))}</div>
    <p>{why}</p></div>
  <div class="panel"><span class="k">{t("İzin verilen azami hisse oranı", "Maximum equity share allowed")}</span><div class="big">{mx}</div><span class="mono mute">rules.yaml · {t("rejim tablosu", "regime table")}</span></div>
  <div class="panel"><span class="k">{t("Mevcut hisse oranı", "Current equity share")}</span>{cur}{gap}</div>
</div>''')
            # regime boundary conditions (thresholds are MAs, never the price itself)
            for key, ma_key, up, flip, label in (("ndx", "ma200", rg["ndx_up"], rg["flip_ndx"], "MA200"),
                                                 ("vxn", "ma50", rg["vxn_up"], rg["flip_vxn"], "MA50")):
                if not flip:
                    continue
                lvl = A[key][ma_key]
                dirw = self.above(not up)
                fl, fmx = esc(self.rlabel(flip)), f.lvl(float(flip["max_equity_pct"]), 0)
                lines.append(t(f"<b>{self.n(key)}</b>, {label} (<b>{f.num(lvl)}</b>) {dirw} kapanırsa rejim “{fl}” olur; "
                               f"azami hisse oranı {mx} → {fmx}.",
                               f"If <b>{self.n(key)}</b> closes {dirw} its {label} (<b>{f.num(lvl)}</b>), the regime becomes “{fl}”; "
                               f"maximum equity share {mx} → {fmx}."))
                trdir = "altında" if up else "üstünde"
                self.week_rows.append({"kind": "level", "key": key, "level": lvl, "dir": "below" if up else "above",
                                       "text": f"{NAME['tr'].get(key, key)} {label} ({F('tr').num(lvl)}) {trdir} kapanırsa rejim değişir",
                                       "text_en": f"{NAME['en'].get(key, key)} closes {'below' if up else 'above'} its {label} ({F('en').num(lvl)}): regime changes"})
            if eq_pct is not None and eq_pct > float(st["max_equity_pct"]):
                e, g = f.lvl(eq_pct, 1), f.pts(eq_pct - float(st['max_equity_pct']))
                lines.append(t(f"Hisse oranı {e}; rejim sınırı {mx}, aradaki fark {g}.",
                               f"Equity share {e}; regime limit {mx}, a gap of {g}."))
        else:
            self.miss(t("Rejim: Nasdaq 100 MA200 / VXN MA50 ya da rules.yaml rejim tablosu eksik",
                        "Regime: Nasdaq 100 MA200 / VXN MA50 or the rules.yaml regime table is missing"))

        # portfolio table
        if rows:
            trs = []
            for r in sorted(rows, key=lambda x: -x["value"]):
                a, tk = r["a"], r["t"]
                w = r["value"] / nav * 100
                vs_cost = (a["last"] / float(r["cost"]) - 1) * 100
                stop = r.get("stop")
                sd = (a["last"] / float(stop) - 1) * 100 if stop else None
                warn = sd is not None and sd < hl
                nxt = (self.CO.get(tk) or {}).get("next")
                earn = f.day(nxt["d"]) if nxt else ""
                if not nxt:
                    self.miss(t(f"{tk}: sıradaki bilanço tarihi", f"{tk}: next earnings date"))
                if sd is not None:
                    below = t("stop altında ", "below stop ") + f.pct(sd, 1)
                    sd_cell = f'<td class="n {"dn" if warn else ""}">{f.pct(sd, 1, sign=False) if sd >= 0 else below}</td>'
                else:
                    sd_cell = '<td class="n"></td>'
                trs.append(f'<tr class="{"warn" if warn else ""}"><th>{NAMES.get(tk, tk)}<small>{tk} · {esc(r.get("basket", ""))}</small></th>'
                           f'<td class="n">{f.usd(a["last"])}</td><td class="n">{f.lvl(w, 1)}</td>'
                           f'<td class="n">{self.ch(vs_cost)}</td><td class="n">{f.usd(float(stop)) if stop else ""}</td>{sd_cell}'
                           f'<td class="n">{self.ch(a["w"])}</td><td class="n">{earn}</td></tr>')
                if sd is not None and 0 <= sd < stop_within:
                    s, dd = f.usd(float(stop)), f.pct(sd, 1, sign=False)
                    lines.insert(0, t(f"<b>{tk}</b>, <b>{s}</b> altında kapanırsa stop çalışır (şu an {dd} uzakta).",
                                      f"If <b>{tk}</b> closes below <b>{s}</b>, the stop triggers (now {dd} away)."))
                    self.week_rows.append({"kind": "stop", "key": tk.lower(), "level": float(stop), "dir": "below",
                                           "text": f"{tk} {F('tr').usd(float(stop))} altında kapanırsa stop çalışır",
                                           "text_en": f"{tk} closes below {F('en').usd(float(stop))}: stop triggers"})
                elif sd is not None and sd < 0:
                    s, dd = f.usd(float(stop)), f.pct(abs(sd), 1, sign=False)
                    lines.insert(0, t(f"<b>{tk}</b> stop seviyesinin ({s}) {dd} altında kapandı.",
                                      f"<b>{tk}</b> closed {dd} below its stop ({s})."))
            heads = t(("Pozisyon", "Son", "Ağırlık", "Maliyete göre", "Stop", "Stop'a mesafe", "1W", "Bilanço"),
                      ("Position", "Last", "Weight", "vs cost", "Stop", "Distance to stop", "1W", "Earnings"))
            th = "".join(f"<th>{h}</th>" for h in heads)
            parts.append(f'<div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')

        # earnings of held names in the next 7 days
        today = date.fromisoformat(self.d["today"])
        for tk in sorted(self.held()):
            nx = (self.CO.get(tk) or {}).get("next")
            if nx and (date.fromisoformat(nx["d"]) - today).days <= 7:
                sess = {"bmo": t(" açılış öncesi", " before the open"), "amc": t(" kapanış sonrası", " after the close")}.get(nx.get("sess"), "")
                im = ""
                if nx.get("im") is not None:
                    m = f.pct(nx['im'], 1, sign=False)
                    im = t(f"; opsiyonlar ±{m} hareket ima ediyor", f"; options imply a ±{m} move")
                lines.append(t(f"<b>{tk}</b> bilançosu {f.day(nx['d'])}{sess}{im}.",
                               f"<b>{tk}</b> reports {f.day(nx['d'])}{sess}{im}."))

        # watchlist names near their buy level
        for w in self.R.get("watchlist") or []:
            tk, b = w["ticker"].upper(), w.get("buy_at")
            a = self.tick(tk)
            if not b or not a:
                continue
            dist = (a["last"] / float(b) - 1) * 100
            bb = f.usd(float(b))
            if 0 <= dist <= buy_within:
                dd = f.pct(dist, 1, sign=False)
                lines.append(t(f"<b>{tk}</b> alım seviyesine (<b>{bb}</b>) {dd} mesafede.",
                               f"<b>{tk}</b> is {dd} from its buy level (<b>{bb}</b>)."))
                self.week_rows.append({"kind": "buy", "key": tk.lower(), "level": float(b), "dir": "below",
                                       "text": f"{tk} alım seviyesi {F('tr').usd(float(b))}",
                                       "text_en": f"{tk} buy level {F('en').usd(float(b))}"})
            elif dist < 0:
                dd = f.pct(abs(dist), 1, sign=False)
                lines.append(t(f"<b>{tk}</b> alım seviyesinin (<b>{bb}</b>) {dd} altında kapandı.",
                               f"<b>{tk}</b> closed {dd} below its buy level (<b>{bb}</b>)."))

        if lines:
            parts.append(f'<div class="panel"><span class="k">{t("Bu hafta · yalnızca kurallardan", "This week · from the rules only")}</span>'
                         f'<ul class="tw">{"".join(f"<li>{x}</li>" for x in lines)}</ul></div>')
        if not parts:
            return ""
        return self.section(t(("Karar ", "sayfası"), ("Decision ", "page")),
                            t("rejim · portföy · bu hafta", "regime · portfolio · this week"), "".join(parts))

    # ── §02 setups ──────────────────────────────────────────────────────────
    def setups(self):
        f, t = self.f, self.t
        sw = self.R.get("swing") or {}
        rows = []
        for w in self.R.get("watchlist") or []:
            tk = w["ticker"].upper()
            a, c = self.tick(tk), self.CO.get(tk) or {}
            if not a:
                self.miss(t(f"{tk}: fiyat verisi — kurulum satırı yok", f"{tk}: price data — no setup row"))
                continue
            cells = []
            # 1 volume on down days
            cells.append(None if "dist_days" not in c else not c["dist_days"])
            # 2 moving averages
            if a.get("ma200") is None:
                cells.append(None)
                self.miss(t(f"{tk}: MA200 için yeterli geçmiş yok", f"{tk}: not enough history for MA200"))
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
            rows.append((passed, tk, w, a, c, cells, known))
        if not rows:
            return ""
        rows.sort(key=lambda r: (-r[0], r[1]))
        trs, notes = [], []
        for passed, tk, w, a, c, cells, known in rows:
            tds = "".join('<td class="c"></td>' if x is None else ('<td class="c up">✓</td>' if x else '<td class="c dn">✗</td>') for x in cells)
            b = w.get("buy_at")
            dist = f.pct((a["last"] / float(b) - 1) * 100, 1) if b else ""
            dd = (a["last"] / a["hi52"] - 1) * 100
            nx = c.get("next")
            spec = ""
            if "profit" in c and not (c["profit"] and c["fcf"]) and w.get("basket") != "spekulatif":
                spec = t(" · nakit yakıyor → spekülatif", " · burning cash → speculative")
            trs.append(f'<tr><th>{NAMES.get(tk, tk)}<small>{tk} · {esc(w.get("basket", ""))}{spec}</small></th>{tds}'
                       f'<td class="n">{passed}/{known}</td><td class="n">{dist}</td><td class="n">{self.ch(dd)}</td>'
                       f'<td class="n">{f.day(nx["d"]) if nx else ""}</td></tr>')
            if c.get("dist_days"):
                ds = ", ".join(f.day(d) for d in c["dist_days"])
                notes.append(t(f"{tk}: yüksek hacimli düşüş günü {ds}", f"{tk}: high-volume down day {ds}"))
            if c.get("nd_ebitda") is None and c.get("ebitda_neg"):
                notes.append(t(f"{tk}: FAVÖK negatif", f"{tk}: EBITDA negative"))
            elif c.get("nd_ebitda") is not None and c["nd_ebitda"] >= float(sw.get("max_net_debt_ebitda", 3)):
                notes.append(t(f"{tk}: net borç / FAVÖK {f.num(c['nd_ebitda'], 1)}", f"{tk}: net debt / EBITDA {f.num(c['nd_ebitda'], 1)}"))
            bad = c.get("analyst_bad") or []
            for x in bad[:2]:
                notes.append(f"{tk}: {esc(self.tx(x))}")
            if len(bad) > 2:
                notes.append(t(f"{tk}: +{len(bad) - 2} analist aksiyonu daha (30 gün)", f"{tk}: +{len(bad) - 2} more analyst actions (30 days)"))
        mult = f.num(float(sw.get("down_volume_mult", 1.5)), 1)
        heads = t(["", "Hacim", "MA", "Borç", "Kâr+FCF", "Analist", "Geçen", "Alım seviyesine", "52W zirveden", "Bilanço"],
                  ["", "Volume", "MA", "Debt", "Profit+FCF", "Analysts", "Passed", "To buy level", "From 52W high", "Earnings"])
        th = "".join(f"<th>{h}</th>" for h in heads)
        lb, nd = sw.get('down_volume_lookback', 5), f.num(float(sw.get('max_net_debt_ebitda', 3)), 1)
        ad, tc = sw.get('analyst_lookback_days', 30), sw.get('target_cut_pct', 20)
        ma50 = sw.get('require_above_ma50')
        legend = t(f"Hacim: son {lb} seansta hacmi 20G ortalamanın {mult} katını aşan düşüş günü yok · "
                   f"MA: fiyat MA200 üstünde{' ve MA50 üstünde' if ma50 else ''} · "
                   f"Borç: net borç / FAVÖK &lt; {nd} · Kâr+FCF: net kâr ve serbest nakit akışı pozitif · "
                   f"Analist: son {ad} günde not indirimi ya da %{tc}+ hedef kesintisi yok",
                   f"Volume: no down day in the last {lb} sessions with volume above {mult}× the 20D average · "
                   f"MA: price above MA200{' and above MA50' if ma50 else ''} · "
                   f"Debt: net debt / EBITDA &lt; {nd} · Profit+FCF: net income and free cash flow positive · "
                   f"Analysts: no downgrade or {tc}%+ target cut in the last {ad} days")
        body = (f'<div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
                f'<p class="mono mute" style="font-size:11px;margin-top:10px;line-height:1.6">{legend}</p>')
        if notes:
            body += (f'<div class="panel" style="margin-top:12px"><span class="k">{t("Kalan kuralların dayanağı", "Why rules failed")}</span>'
                     f'<ul class="tw">{"".join(f"<li>{x}</li>" for x in notes)}</ul></div>')
        return self.section(t(("Kurulum ", "tablosu"), ("Setup ", "table")),
                            t("izleme listesi × swing kuralları · geçen kurala göre sıralı",
                              "watchlist × swing rules · sorted by rules passed"), body)

    # ── §03 AI value chain ──────────────────────────────────────────────────
    def chain(self):
        A, f, t = self.A, self.f, self.t
        keys = [k for k in ("neocloud", "memory", "optics", "power") if k in A]
        if not keys:
            return ""
        sox = A.get("sox")
        out, n = [], 1
        for k in keys:
            b = A[k]
            name, sub = self.bn(k)
            chips = "".join(f'<li><span>{NAMES.get(tk, tk)}</span><b class="mono {dc(self.tick(tk)["w"])}">{f.pct(self.tick(tk)["w"])}</b></li>'
                            for tk in b["members"] if self.tick(tk))
            for tk in b.get("missing_members") or []:
                self.miss(t(f"{name} sepeti: {tk} verisi yok — sepetten çıkarıldı", f"{name} basket: no data for {tk} — left out of the basket"))
            rebound = b["w"] is not None and b["m"] is not None and b["w"] > 0 and b["m"] < REBOUND_1M
            tag = f'<span class="pill" style="margin-left:8px">{t("tepki", "rebound")}</span>' if rebound else ""
            wins = []
            for lab, key in (("1W", "w"), ("1M", "m"), ("3M", "q")):
                if b.get(key) is None:
                    self.miss(t(f"{name} sepeti {lab}: bir üyenin o pencerede verisi yok", f"{name} basket {lab}: a member has no data for that window"))
                    continue
                rel = (f'<span class="{dc(b[key] - sox[key])}">{f.pts(b[key] - sox[key])}</span>'
                       if sox and sox.get(key) is not None else "")
                wins.append(f'<tr><td>{lab}</td><td>{self.ch(b[key])}</td><td>{rel}</td></tr>')
            out.append(f'''<article class="link"><span class="n mono">0{n}</span><span class="k">{name}{tag}</span><h3>{sub}</h3>
  <div class="px {dc(b["w"])}">{f.pct(b["w"])}<small class="mono mute"> 1W</small></div>
  <table class="rel"><tr><th></th><th>{t("getiri", "return")}</th><th>{t("SOX’a göre", "vs SOX")}</th></tr>{"".join(wins)}</table>
  <ul class="chips">{chips}</ul></article>''')
            n += 1
        H1 = A.get("h100")
        if H1:
            since = ""
            if H1.get("since"):
                since = t(", " + f.long_date(H1["since"]) + "'den beri", ", since " + f.long_date(H1["since"]))
            src = t(f"Düşük güvenilirlik: OKX'te tek, ince hacimli vadeli{since}. Sonuç çıkarılmaz.",
                    f"Low reliability: a single thinly traded future on OKX{since}. No conclusion is drawn.")
            out.append(f'''<article class="link gpu"><span class="n mono">0{n}</span><span class="k" style="display:block;padding-right:34px">{t("GPU kirası · gösterge", "GPU rent · indicator")}</span><h3>H100</h3>
  <div class="px">${f.num(H1["last"])}<small class="mono"> / {t("saat", "hour")}</small></div>
  <div class="chg mono">{self.ch(H1["w"], suffix=" 1W")}{self.ch(H1["m"], suffix=" 1M") if H1.get("m") is not None else ""}</div>
  {spark(H1["series"], w=240, h=46, layers=3)}
  <span class="mono mute src">{src}</span></article>''')
        ranked = sorted(keys, key=lambda k: A[k]["w"], reverse=True)
        best, worst = ranked[0], ranked[-1]
        bn_, wn_ = self.bn(best)[0].lower(), self.bn(worst)[0].lower()
        bp_, wp_ = f.pct(A[best]['w']), f.pct(A[worst]['w'])
        read = t(f"1W en güçlü halka <b>{bn_}</b> ({bp_}), en zayıf <b>{wn_}</b> ({wp_}).",
                 f"Strongest link over 1W: <b>{bn_}</b> ({bp_}); weakest: <b>{wn_}</b> ({wp_}).")
        reb = [self.bn(k)[0] for k in keys if A[k]["w"] > 0 and A[k]["m"] is not None and A[k]["m"] < REBOUND_1M]
        if reb:
            th_ = f.pct(REBOUND_1M, 0)
            read += t(f" {', '.join(reb)}: pozitif hafta, ama 1M {th_}'ten kötü — tepki olarak etiketlendi.",
                      f" {', '.join(reb)}: a positive week, but 1M worse than {th_} — labelled a rebound.")
        legend = t("Sepet kartları hisse fiyatını gösterir, kira ücretini değil · getiri = sepetin eşit ağırlıklı hisse getirisi · "
                   "SOX'a göre = yarı iletken endeksine (SOX) göre fark, yüzde puan · alttaki isimler = her hissenin 1W getirisi",
                   "Basket cards show share prices, not rental rates · return = the basket's equal-weight share return · "
                   "vs SOX = difference from the semiconductor index (SOX), percentage points · names below = each stock's 1W return")
        if H1:
            legend += t(" · GPU kirası yalnızca H100 kartında", " · GPU rent appears only on the H100 card")
        meta = t("eşit ağırlıklı sepetler · her pencere = üyelerin o penceredeki getirilerinin ortalaması",
                 "equal-weight baskets · each window = mean of the members' returns over that window")
        return self.section(t(("AI değer ", "zinciri"), ("AI value ", "chain")), meta,
                            f'<div class="chain">{"".join(out)}</div>'
                            f'<p class="mono mute" style="font-size:11px;margin-top:10px;line-height:1.6">{legend}</p><p class="read">{read}</p>')

    # ── §04 financing stress + macro (+ compact metals) ─────────────────────
    def macro(self):
        A, f, t = self.A, self.f, self.t
        drv = []
        if self.has("hy"):
            h = A["hy"]
            q = (", 3M " + f.bp(h['q_bp'])) if h.get("q_bp") is not None else ""
            lo, hi = f.lvl(h['lo52']), f.lvl(h['hi52'])
            drv.append((self.n("hy"), f.lvl(h["last"]), self.chbp(h["w_bp"], " 1W"),
                        t(f"ICE BofA ABD yüksek getirili endeks, Hazine'ye göre makas. 1M {f.bp(h['m_bp'])}{q}; 52 haftalık aralık {lo} – {hi}.",
                          f"ICE BofA US High Yield index, spread over Treasuries. 1M {f.bp(h['m_bp'])}{q}; 52-week range {lo} – {hi}.")))
        else:
            self.miss(t("HY kredi makası (FRED BAMLH0A0HYM2)", "HY credit spread (FRED BAMLH0A0HYM2)"))
        if self.has("us2y"):
            a = A["us2y"]
            fed = self.d.get("fed")
            tail = ""
            if fed:
                fd, fp = f.long_date(fed['date']), f.lvl(fed['p'], 0)
                tail = t(f" Fed {fd} toplantısı için indirim olasılığı {fp} (Polymarket).",
                         f" Probability of a cut at the {fd} Fed meeting: {fp} (Polymarket).")
            drv.append((self.n("us2y"), f.lvl(a["last"]), self.chbp(a["w_bp"], " 1W"), f"1M {f.bp(a['m_bp'])}.{tail}"))
        if self.has("us10y"):
            a = A["us10y"]
            txt = f"1M {f.bp(a['m_bp'])}."
            if self.has("real10", "be10"):
                r, b = A["real10"]["w_bp"], A["be10"]["w_bp"]
                rl = f.lvl(A['real10']['last'])
                if abs(r) >= abs(b):
                    part = t("reel faizden", "real yields")
                else:
                    part = t("enflasyon beklentisinden", "inflation expectations")
                txt = t(f"Haftalık hareketin {f.bp(r)} kısmı reel faiz (şu an {rl}), {f.bp(b)} kısmı başabaş enflasyon; ağırlık {part} geliyor.",
                        f"Of the weekly move, {f.bp(r)} came from real yields (now {rl}) and {f.bp(b)} from breakeven inflation; most of it from {part}.")
                if self.supports("gold", "real10"):
                    g, cr = f.pct(A['gold']['w']), f.num(self.d['corr']['gold_real'])
                    txt += t(f" Altın aynı hafta {g}, korelasyon {cr}: ilişki bu hafta çalıştı.",
                             f" Gold {g} the same week, correlation {cr}: the link held this week.")
            drv.append((self.n("us10y"), f.lvl(a["last"]), self.chbp(a["w_bp"], " 1W"), txt))
        if self.has("dxy"):
            a = A["dxy"]
            p52 = pos52(a)
            if p52 >= .95:
                where = t("52 haftanın zirvesinde", "at its 52-week high")
            elif p52 <= .05:
                where = t("52 haftanın dibinde", "at its 52-week low")
            else:
                pp = f.num(p52 * 100, 0)
                where = t(f"52 haftalık aralığın %{pp} noktasında", f"at {pp}% of its 52-week range")
            txt = f"1M {f.pct(a['m'])}; {where}."
            if self.supports("gold", "dxy"):
                g, cr = f.pct(A['gold']['w']), f.num(self.d['corr']['gold_dxy'])
                txt += t(f" Altın aynı hafta {g}, korelasyon {cr}.", f" Gold {g} the same week, correlation {cr}.")
            drv.append((self.n("dxy"), f.num(a["last"]), self.ch(a["w"], suffix=" 1W"), txt))
        if self.has("vxn"):
            v = A["vxn"]
            ab = self.above(v["last"] > v["ma50"])
            drv.append(("VXN", f.num(v["last"]), self.ch(v["w"], suffix=" 1W"),
                        t(f"50 günlük ortalaması {f.num(v['ma50'])}; {ab}.", f"50-day average {f.num(v['ma50'])}; {ab} it.")))
        body = "".join(f'<div class="drv"><span class="k">{k}</span><b>{v}</b><span class="mono">{ch}</span><p>{why}</p></div>'
                       for k, v, ch, why in drv)
        corr = self.corr_panel()
        metals = self.metals_compact() if (self.R.get("show_metals") or "compact") == "compact" else ""
        if not body and not corr and not metals:
            return ""
        return self.section(t(("Finansman stresi ", "ve makro"), ("Financing stress ", "and macro")),
                            t("FRED · ICE · Cboe · korelasyon 63 seans", "FRED · ICE · Cboe · correlation 63 sessions"),
                            f'<div class="drivers">{body}</div>{corr}{metals}')

    def corr_panel(self):
        f, t = self.f, self.t
        C = self.d.get("corr") or {}
        pairs = [("gold_real", t("Altın × reel faiz", "Gold × real yield"), t("faiz yükselince altın düşmeli", "gold should fall when yields rise"), -1),
                 ("gold_dxy", t("Altın × dolar", "Gold × dollar"), t("dolar güçlenince altın düşmeli", "gold should fall when the dollar strengthens"), -1),
                 ("ndx_10y", t("Nasdaq × 10Y faiz", "Nasdaq × 10Y yield"), t("faiz yükselince teknoloji düşmeli", "tech should fall when yields rise"), -1),
                 ("ndx_gold", t("Nasdaq × altın", "Nasdaq × gold"), t("biri diğerini hedge ediyor mu", "test: does one hedge the other"), 0),
                 ("silver_copper", t("Gümüş × bakır", "Silver × copper"), t("gümüş sanayi metali gibi mi davranıyor", "test: is silver trading like an industrial metal"), 1)]
        items = []
        for k, name, test, expect in pairs:
            if k not in C:
                continue
            r = C[k]
            st = abs(r)
            word = (t("ilişki yok", "no relationship") if st < .2 else t("zayıf", "weak") if st < .4
                    else t("orta", "moderate") if st < .7 else t("güçlü", "strong"))
            if st < .2:
                read = t(f"Bu dönemde {word}.", f"Over this period: {word}.")
            else:
                dirw = t("ters", "inverse") if r < 0 else t("aynı yönde", "same direction")
                if expect == 0:
                    tail = (t(" Aynı yönde hareket ediyorlar; biri diğerini hedge etmiyor.", " They move together; neither hedges the other.") if r > 0
                            else t(" Ters yönde: hedge işlevi çalışıyor.", " Inverse: the hedge is working."))
                else:
                    ok = sgn(r) == expect and st >= CORR_MIN
                    tail = (t(" Ders kitabındaki ilişki çalışıyor.", " The textbook relationship holds.") if ok
                            else t(" Ders kitabındaki ilişki bu dönemde çalışmıyor.", " The textbook relationship does not hold over this period."))
                read = f"{word.capitalize()}, {dirw}." + tail
            sign = "+" if r >= 0 else "−"
            w = abs(r) * 50
            left = 50 if r >= 0 else 50 - w
            bar = f'<div class="cb"><span class="z"></span><i class="{"up" if r >= 0 else "dn"}" style="left:{left:.1f}%;width:{w:.1f}%"></i></div>'
            items.append(f'<li><div class="ch"><b>{name}</b><span class="mono">{sign}{f.num(abs(r))}</span></div>{bar}'
                         f'<p><span class="mute">{test[0].upper() + test[1:]}.</span> {read}</p></li>')
        if not items:
            return ""
        return (f'<div class="panel corr"><div class="ph"><span class="k">{t("Korelasyon · son 63 seans, günlük değişim", "Correlation · last 63 sessions, daily changes")}</span>'
                f'<span class="mono mute">{t("−1 ters · 0 ilişkisiz · +1 birlikte", "−1 inverse · 0 unrelated · +1 together")}</span></div><ul>{"".join(items)}</ul></div>')

    def gsr_line(self, m):
        rel = self.t("kötü", "worse") if m > 0 else self.t("iyi", "better")
        p = self.f.pct(m)
        return self.t(f"Oran 1M {p}: gümüş son bir ayda altından {rel}.", f"Ratio 1M {p}: silver did {rel} than gold over the past month.")

    def metals_compact(self):
        A, f, t = self.A, self.f, self.t
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
            cells.append(f'<div class="panel dark"><span class="k">{t("Altın / gümüş oranı", "Gold / silver ratio")}</span><div class="big">{f.num(G["last"], 1)}</div>'
                         f'<div class="chg mono">{self.ch(G["w"], suffix=" 1W")}{self.ch(G["m"], suffix=" 1M")}</div>'
                         f'<p>{self.gsr_line(G["m"])}</p></div>')
        r = (self.d.get("corr") or {}).get("gold_dxy")
        if r is not None:
            msg = (t("Ters yönlü ilişki çalışıyor.", "The inverse relationship holds.") if r <= -CORR_MIN
                   else t("Ters yönlü ilişki bu dönemde zayıf ya da yok.", "The inverse relationship is weak or absent over this period."))
            cells.append(f'<div class="panel"><span class="k">{t("Altın × dolar · 63 seans", "Gold × dollar · 63 sessions")}</span><div class="big">{"+" if r >= 0 else "−"}{f.num(abs(r))}</div>'
                         f'<p>{msg}</p></div>')
        return f'<div class="k subk">{t("Metaller · tek kart", "Metals · one card")}</div><div class="metals">{"".join(cells)}</div>'

    # full metals mode keeps the two old sections
    def assets_full(self):
        A, f, t = self.A, self.f, self.t
        cards = []
        for key, sub, dec, cur in (("ndx", "NDX", 0, ""), ("gold", t("XAU · ons", "XAU · oz"), 0, "$"), ("silver", t("XAG · ons", "XAG · oz"), 2, "$")):
            if key not in A:
                continue
            a = A[key]
            rg = regime(a["last"], a["ma50"], a.get("ma200"))
            lab = {"up": t("Yükseliş trendi", "Uptrend"), "dn": t("Düşüş trendi", "Downtrend"), "mix": t("Kararsız", "Mixed")}[rg]
            ma200 = f'<div><dt>MA200</dt><dd>{cur}{f.num(a["ma200"], dec)}</dd></div>' if a.get("ma200") else ""
            cards.append(f'''<article class="asset"><header><div><h3>{self.n(key)}</h3><span class="mono mute">{sub}</span></div><span class="pill {rg if rg != 'mix' else ''}">{lab}</span></header>
      <div class="px">{cur}{f.num(a["last"], dec)}</div>
      <div class="chg mono">{self.ch(a["w"], suffix=" 1W")}{self.ch(a["m"], suffix=" 1M")}{self.ch(a["ytd"], suffix=" " + f.ylab(a))}</div>
      {spark(a["series"], layers=4)}<div class="k" style="margin-top:2px">{t("Son 5 seans", "Last 5 sessions")}</div>{bars5(a, f)}
      <dl class="lv"><div><dt>MA50</dt><dd>{cur}{f.num(a["ma50"], dec)}</dd></div>{ma200}</dl>
      <div class="r52"><span class="mono mute">52W</span>{rng(a)}<span class="mono">{cur}{f.num(a["lo52"], dec)} — {cur}{f.num(a["hi52"], dec)}</span></div></article>''')
        if not cards:
            return ""
        return self.section(t(("Üç varlık, ", "tek bakış"), ("Three assets, ", "one look")),
                            t("trend = fiyat vs MA50 / MA200", "trend = price vs MA50 / MA200"), f'<div class="assets">{"".join(cards)}</div>')

    def metals_full(self):
        A, f, t = self.A, self.f, self.t
        panels = []
        if "gsr" in A:
            G = A["gsr"]
            panels.append(f'''<div class="panel dark"><span class="k">{t("Altın / gümüş oranı", "Gold / silver ratio")}</span><div class="big">{f.num(G["last"], 1)}</div>
      <div class="chg mono">{self.ch(G["w"], suffix=" 1W")}{self.ch(G["m"], suffix=" 1M")}</div>
      <p>{self.gsr_line(G["m"])}</p>{spark(G["series"], w=400, h=70, layers=4)}</div>''')
        if "cu_au" in A:
            CA = A["cu_au"]
            rel = t("iyi", "better") if CA["m"] > 0 else t("kötü", "worse")
            p = f.pct(CA["m"])
            line = t(f"Oran 1M {p}: bakır son bir ayda altından {rel}.", f"Ratio 1M {p}: copper did {rel} than gold over the past month.")
            panels.append(f'''<div class="panel"><span class="k">{t("Bakır / altın oranı", "Copper / gold ratio")}</span><div class="big">{f.num(CA["last"], 2)}</div>
      <div class="chg mono">{self.ch(CA["w"], suffix=" 1W")}{self.ch(CA["m"], suffix=" 1M")}</div>
      <p>{line}</p>{spark(CA["series"], w=400, h=70, fill=False)}</div>''')
        for key, lab in (("sil_silver", t("Gümüş madencileri / gümüş (SIL)", "Silver miners / silver (SIL)")),
                         ("gdx_gold", t("Madenciler / altın (GDX)", "Miners / gold (GDX)"))):
            if key in A:
                M = A[key]
                rel = t("iyi", "better") if M["w"] > 0 else t("kötü", "worse")
                line = t(f"Madenciler bu hafta metalden {rel}; ayda {f.pct(M['m'])}.", f"Miners did {rel} than the metal this week; {f.pct(M['m'])} on the month.")
                panels.append(f'''<div class="panel"><span class="k">{lab}</span><div class="big {dc(M["w"])}">{f.pct(M["w"])}</div>
      <div class="chg mono"><span class="mute">{t("1 hafta, göreli", "1 week, relative")}</span>{self.ch(M["m"], suffix=" 1M")}</div>
      <p>{line}</p></div>''')
        read = ""
        if self.has("cu_au", "gsr"):
            cu, gs = A["cu_au"]["m"], A["gsr"]["m"]
            pc, pg = f.pct(cu), f.pct(gs)
            if cu > 0 and gs > 0:
                read = t(f"Çelişki: bakır altından iyi gidiyor (bakır/altın 1M {pc}) ama gümüş altından kötü (altın/gümüş 1M {pg}). "
                         "İki oran aynı yönü göstermiyor; ikisinden de tek başına büyüme sonucu çıkarılmaz.",
                         f"Contradiction: copper is beating gold (copper/gold 1M {pc}) but silver is lagging gold (gold/silver 1M {pg}). "
                         "The two ratios point different ways; neither alone supports a growth conclusion.")
            elif cu < 0 and gs < 0:
                read = t(f"Çelişki: gümüş altından iyi gidiyor (altın/gümüş 1M {pg}) ama bakır altından kötü (bakır/altın 1M {pc}). "
                         "İki oran aynı yönü göstermiyor.",
                         f"Contradiction: silver is beating gold (gold/silver 1M {pg}) but copper is lagging gold (copper/gold 1M {pc}). "
                         "The two ratios point different ways.")
        if not panels:
            return ""
        return self.section(t(("Metallerin ", "içi"), ("Inside ", "the metals")),
                            t("oranlar ve madenciler · hepsi USD", "ratios and miners · all USD"),
                            f'<div class="metals">{"".join(panels)}</div>' + (f'<p class="read">{read}</p>' if read else ""))

    # ── §05 earnings ────────────────────────────────────────────────────────
    def earnings(self):
        f, t = self.f, self.t
        today = date.fromisoformat(self.d["today"])
        names = sorted(self.held() | self.wl())
        up, past = [], []
        for tk in names:
            c = self.CO.get(tk) or {}
            nx = c.get("next")
            if nx and (date.fromisoformat(nx["d"]) - today).days <= 14:
                up.append((nx["d"], tk, nx))
            if c.get("reported"):
                past.append((c["reported"]["d"], tk, c["reported"]))
        parts = []
        if up:
            trs = []
            for d, tk, nx in sorted(up):
                sess = {"bmo": t("açılış öncesi", "before open"), "amc": t("kapanış sonrası", "after close")}.get(nx.get("sess"), "")
                if not sess:
                    self.miss(t(f"{tk}: bilanço saati", f"{tk}: earnings time"))
                eps = f.usd(nx["eps"]) if nx.get("eps") is not None else ""
                im = f"±{f.pct(nx['im'], 1, sign=False)}" if nx.get("im") is not None else ""
                rv = {"up": f'<span class="up">{t("yukarı", "up")}</span>', "dn": f'<span class="dn">{t("aşağı", "down")}</span>',
                      "flat": t("yatay", "flat")}.get(nx.get("rev30"), "")
                if not rv:
                    self.miss(t(f"{tk}: 30 günlük EPS revizyonu", f"{tk}: 30-day EPS revision"))
                own = t(" · portföy", " · held") if tk in self.held() else ""
                trs.append(f'<tr><th>{NAMES.get(tk, tk)}<small>{tk}{own}</small></th><td class="n">{f.day(d)}</td><td class="n">{sess}</td>'
                           f'<td class="n">{eps}</td><td class="n">{im}</td><td class="n">{rv}</td></tr>')
            heads = t(("", "Tarih", "Saat", "Çeyreklik EPS beklentisi", "Opsiyon ima hareketi", "EPS revizyonu · 30G"),
                      ("", "Date", "Time", "Quarterly EPS estimate", "Options-implied move", "EPS revision · 30D"))
            th = "".join(f"<th>{h}</th>" for h in heads)
            parts.append(f'<div class="k subk">{t("Önümüzdeki 14 gün", "Next 14 days")}</div><div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
        else:
            parts.append(f'<p class="note">{t("Önümüzdeki 14 günde portföyde ya da izleme listesinde bilanço yok.", "No earnings from holdings or the watchlist in the next 14 days.")}</p>')
        if past:
            trs = []
            for d, tk, r in sorted(past):
                sur = self.ch(r["surprise"]) if r.get("surprise") is not None else ""
                rea = self.ch(r["react"]) if r.get("react") is not None else ""
                if r.get("react") is None:
                    self.miss(t(f"{tk}: bilanço sonrası fiyat tepkisi (açıklama saati bilinmiyor)", f"{tk}: post-earnings price reaction (release time unknown)"))
                trs.append(f'<tr><th>{NAMES.get(tk, tk)}<small>{tk}</small></th><td class="n">{f.day(d)}</td><td class="n">{sur}</td><td class="n">{rea}</td></tr>')
            heads = t(("", "Tarih", "EPS sürprizi", "Ertesi seans tepkisi"), ("", "Date", "EPS surprise", "Next-session reaction"))
            th = "".join(f"<th>{h}</th>" for h in heads)
            parts.append(f'<div class="k subk">{t("Geçen hafta açıklayanlar", "Reported last week")}</div><div class="tblw"><table class="board p"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
        return self.section(t(("Bilan", "çolar"), ("Earn", "ings")),
                            t("yalnızca portföy ve izleme listesi · ima hareketi = bilanço sonrası ilk vadede ATM straddle",
                              "holdings and watchlist only · implied move = ATM straddle on the first expiry after earnings"), "".join(parts))

    # ── §06 news ────────────────────────────────────────────────────────────
    def news(self):
        t = self.t
        items = self.d.get("news") or []
        if not items:
            self.miss(t("Haberler: news.yaml boş ya da yok (Grokbot bildirimleri elle eklenir)",
                        "News: news.yaml is empty or missing (Grokbot notifications are added by hand)"))
            return ""
        lis = []
        for it in items[:5]:
            tag = (it.get("tag") or "").lower()
            tag_l = t("tez", "thesis") if tag == "tez" else t("gürültü", "noise")
            cls = "up" if tag == "tez" else ""
            url = it.get("url") or ""
            title = esc(it.get("title", ""))
            link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
            tk = f' <span class="mono mute">{esc(it["ticker"])}</span>' if it.get("ticker") else ""
            lis.append(f'<li><span class="pill {cls}">{tag_l}</span><div><b>{link}</b>{tk}</div></li>')
        return self.section(t(("Tezi değiştiren ", "haberler"), ("News that changes ", "the thesis")),
                            t("en fazla beş · kaynak: news.yaml", "at most five · source: news.yaml"), f'<ul class="news">{"".join(lis)}</ul>')

    # ── §07 positioning ─────────────────────────────────────────────────────
    def positioning(self):
        f, t = self.f, self.t
        parts = []
        pc = self.P.get("pc")
        if pc:
            avg = t(f'{pc["n"]} seans ort.', f'{pc["n"]}-session avg')
            parts.append(f'''<div class="pair">
  <div class="panel"><span class="k">{t("Toplam put/call · Cboe", "Total put/call · Cboe")}</span><b>{f.num(pc["total"])}</b><span class="mono mute">{avg} {f.num(pc["total10"])} · {f.day(pc["date"])}</span></div>
  <div class="panel"><span class="k">{t("Hisse put/call · Cboe", "Equity put/call · Cboe")}</span><b>{f.num(pc["equity"])}</b><span class="mono mute">{avg} {f.num(pc["equity10"])}</span></div>
</div>''')
        rows = []
        for tk in sorted(self.held() | self.wl()):
            c = self.CO.get(tk) or {}
            if c.get("short") is None:
                self.miss(t(f"{tk}: açığa satış oranı", f"{tk}: short interest"))
                continue
            rows.append((c["short"], tk, c.get("short_date")))
        if rows:
            rows.sort(reverse=True)
            own = t(" · portföy", " · held")
            trs = "".join(f'<tr><th>{NAMES.get(tk, tk)}<small>{tk}{own if tk in self.held() else ""}</small></th>'
                          f'<td class="n">{f.lvl(s, 1)}</td><td class="n">{f.day(d) if d else ""}</td></tr>' for s, tk, d in rows)
            parts.append(f'<div class="k subk">{t("Açığa satış · halka açık payın yüzdesi", "Short interest · % of float")}</div><div class="tblw"><table class="board p" style="min-width:420px">'
                         f'<thead><tr><th></th><th>{t("Açığa satış", "Short interest")}</th><th>{t("Rapor tarihi", "Report date")}</th></tr></thead><tbody>{trs}</tbody></table></div>')
        if not parts:
            return ""
        return self.section(t(("Konum", "lanma"), ("Position", "ing")),
                            t("Cboe günlük istatistik · açığa satış: borsa raporu (ayda iki kez)",
                              "Cboe daily statistics · short interest: exchange report (twice a month)"), "".join(parts))

    # ── §08 Asia ────────────────────────────────────────────────────────────
    def asia(self):
        A, f, t = self.A, self.f, self.t
        rows = [("kospi", t("Kore · Samsung, SK hynix", "Korea · Samsung, SK hynix"), 0), ("twii", t("Tayvan · TSMC", "Taiwan · TSMC"), 0),
                ("n225", t("Japonya · çip ekipmanı", "Japan · chip equipment"), 0), ("usdjpy", "yen", 2)]
        rows = [r for r in rows if r[0] in A]
        if not rows:
            return ""
        cards = "".join(f'''<div class="panel{' dark' if k == 'usdjpy' else ''}"><span class="k">{sub}</span><h3>{self.n(k)}</h3>
  <div class="big">{f.num(A[k]["last"], d)}</div>
  <div class="chg mono">{self.ch(A[k]["w"], suffix=" 1W")}{self.ch(A[k]["m"], suffix=" 1M")}{self.ch(A[k]["ytd"], suffix=" YTD")}</div>
  {spark(A[k]["series"], w=300, h=56, fill=k != "usdjpy", layers=0 if k == "usdjpy" else 3)}</div>''' for k, sub, d in rows)
        read = ""
        if self.has("kospi", "sox"):
            kp, sp, gp = f.pct(A['kospi']['m']), f.pct(A['sox']['m']), f.pts(A['kospi']['m'] - A['sox']['m'])
            read = t(f"1M: KOSPI {kp}, SOX {sp}; fark {gp}.", f"1M: KOSPI {kp}, SOX {sp}; gap {gp}.")
        return self.section(t(("Asya çip ", "ekseni"), ("Asia chip ", "axis")), "KOSPI · TAIEX · Nikkei · USD/JPY",
                            f'<div class="asia">{cards}</div>' + (f'<p class="read">{read}</p>' if read else ""))

    # ── §09 breadth ─────────────────────────────────────────────────────────
    def breadth(self):
        A, f, t = self.A, self.f, self.t
        mine = self.held() | self.wl()
        m7 = [k for k in ("nvda", "aapl", "msft", "googl", "amzn", "meta", "tsla") if k in A and k.upper() in mine]
        left = ""
        if m7:
            m7.sort(key=lambda k: A[k]["w"])
            mx = max(abs(A[k]["w"]) for k in m7) or 1
            lis = "".join(f'''<li><span class="nm">{self.n(k)}</span><span class="mono px2">${f.num(A[k]["last"])}</span>
  <div class="hb"><span class="z"></span><i class="{dc(A[k]["w"])}" style="{"left:50%" if A[k]["w"] >= 0 else "right:50%"};width:{abs(A[k]["w"]) / mx * 50:.1f}%"></i></div>
  <span class="mono {dc(A[k]["w"])}">{f.pct(A[k]["w"])}</span><span class="mono mute ytd">{f.pct(A[k]["ytd"], 0)} YTD</span></li>''' for k in m7)
            left = (f'<div class="panel"><div class="ph"><span class="k">{t("Muhteşem 7 · portföy ve izleme listesindekiler", "Magnificent 7 · those in holdings or the watchlist")}</span>'
                    f'<span class="mono mute">{t("1W sıralı", "sorted by 1W")}</span></div><ul class="m7">{lis}</ul></div>')
        right = ""
        if "ew_cw" in A:
            ew = A["ew_cw"]
            p = f.pct(abs(ew['m']), 1, sign=False)
            if ew["m"] > 0:
                txt = t(f"Eşit ağırlıklı Nasdaq (QQQE), QQQ'dan son bir ayda <b>{p}</b> iyi.",
                        f"The equal-weight Nasdaq (QQQE) beat QQQ by <b>{p}</b> over the past month.")
            else:
                txt = t(f"QQQ, eşit ağırlıklı Nasdaq'tan (QQQE) son bir ayda <b>{p}</b> iyi: endeksi büyükler taşıyor.",
                        f"QQQ beat the equal-weight Nasdaq (QQQE) by <b>{p}</b> over the past month: the large caps are carrying the index.")
            right += (f'<div class="panel dark"><span class="k">{t("Genişlik · eşit ağırlık / piyasa değeri", "Breadth · equal weight / cap weight")}</span>'
                      f'<div class="big2">{self.ch(ew["m"])}<small class="mono">{t("1 ay", "1 month")}</small></div><p>{txt}</p>{spark(ew["series"], w=500, h=70, layers=4)}</div>')
        pair = ""
        if "sox_ndx" in A:
            sx = A["sox_ndx"]
            pair += (f'<div class="panel"><span class="k">SOX / Nasdaq</span><b class="{dc(sx["w"])}">{f.pct(sx["w"])}</b>'
                     f'<span class="mono mute">{t("1 hafta", "1 week")}</span></div>')
        vol = (self.d.get("vol") or {}).get("qqq")
        if vol:
            pair += (f'<div class="panel"><span class="k">{t("QQQ hacmi", "QQQ volume")}</span><b>{f.num(vol)}×</b>'
                     f'<span class="mono mute">{t("60 günlük ortalamaya göre", "vs 60-day average")}</span></div>')
        if pair:
            right += f'<div class="pair">{pair}</div>'
        if not left and not right:
            return ""
        body = f'<div class="split">{left}<div class="stack">{right}</div></div>' if left else f'<div class="stack">{right}</div>'
        return self.section(t(("Genişlik", ""), ("Breadth", "")), t("eşit ağırlık · SOX/Nasdaq · hacim", "equal weight · SOX/Nasdaq · volume"), body)

    # ── §10 calendar ────────────────────────────────────────────────────────
    def calendar(self):
        f, t = self.f, self.t
        cal = []
        for e in self.d.get("calendar", []):
            if e.get("impact") != "high":
                continue
            ev = e["event"]
            name = ev
            if self.l == "tr":
                name = CAL_TR.get(ev, ev)
                if ev not in CAL_TR and "Speaks" in ev:
                    name = ev.replace("Fed Chairman", "Fed Başkanı").replace("FOMC Member", "FOMC üyesi").replace(" Speaks", " konuşuyor")
            pe = ""
            pv, es = e.get("prev"), e.get("est")
            bits = []
            fix = (lambda x: str(x).replace('.', ',')) if self.l == "tr" else str
            if pv not in (None, "—", ""):
                bits.append(f"{t('önceki', 'prior')} {esc(fix(pv))}")
            if es not in (None, "—", ""):
                bits.append(f"{t('beklenti', 'forecast')} {esc(fix(es))}")
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
                        f'{t("faiz indirimi olasılığı · Polymarket", "probability of a rate cut · Polymarket")}</span></div>')
        if not cal and not fed_html:
            self.miss(t("Takvim: nocashflow.net calendar.json / Fed olasılığı", "Calendar: nocashflow.net calendar.json / Fed probability"))
            return ""
        cal_html = (f'<ul class="cal">{"".join(cal[:8])}</ul>' if cal else
                    f'<p class="note">{t("Takvimde bu hafta yüksek etkili ABD verisi yok.", "No high-impact US data on the calendar this week.")}</p>')
        return self.section(t(("Tak", "vim"), ("Calen", "dar")), t("CET · yüksek etkili ABD verisi · Fed", "CET · high-impact US data · Fed"),
                            f'<div class="split">{cal_html}{fed_html}</div>')

    # ── §11 scorecard ───────────────────────────────────────────────────────
    def scorecard(self):
        f, t = self.f, self.t
        prev = self.d.get("prev_issue")
        if not prev or not prev.get("rows"):
            self.miss(t("Karne: önceki sayı yok (history/ boş) — ilk sayıdan sonra dolacak",
                        "Scorecard: no previous issue (history/ is empty) — fills after the first issue"))
            return ""
        lis = []
        for r in prev["rows"]:
            a = self.A.get(r["key"])
            text = (r.get("text_en") or r["text"]) if self.l == "en" else r["text"]
            closes = [(d, v) for d, v in (a or {}).get("week", []) if d > prev["cut"]]
            if not closes:
                self.miss(t(f"Karne: {text} — bu haftanın kapanışları yok", f"Scorecard: {text} — no closes this week"))
                continue
            lvl = r["level"]
            if r["dir"] == "below":
                d, v = min(closes, key=lambda x: x[1])
                broke = v < lvl
                why = t(f"Haftanın en düşük kapanışı {f.num(v)} ({f.day(d)}); seviye {f.num(lvl)}.",
                        f"Lowest close of the week {f.num(v)} ({f.day(d)}); level {f.num(lvl)}.")
            else:
                d, v = max(closes, key=lambda x: x[1])
                broke = v > lvl
                why = t(f"Haftanın en yüksek kapanışı {f.num(v)} ({f.day(d)}); seviye {f.num(lvl)}.",
                        f"Highest close of the week {f.num(v)} ({f.day(d)}); level {f.num(lvl)}.")
            mark = '<b class="dn">✗</b>' if broke else '<b class="up">✓</b>'
            verdict = (t("tutmadı — seviye kapanışta geçildi", "broken — the level was crossed on a close") if broke
                       else t("tuttu — seviye kapanışta geçilmedi", "held — the level was not crossed on a close"))
            lis.append(f'<li>{mark}<div><b>{esc(text)}</b><p>{verdict}. {why}</p></div></li>')
        if not lis:
            return ""
        pc = f.long_date(prev['cut'])
        return self.section(t(("Geçen sayının ", "karnesi"), ("Last issue's ", "scorecard")),
                            t(f"{pc} sayısının “bu hafta” satırları", f"the “this week” rows of the {pc} issue"),
                            f'<ul class="karne">{"".join(lis)}</ul>')

    # ── §12 board ───────────────────────────────────────────────────────────
    def board(self):
        A, f, t = self.A, self.f, self.t
        groups = [(t("Hisseler", "Equities"), [("ndx", 0, ""), ("spx", 0, ""), ("sox", 0, "")]),
                  (t("Metaller", "Metals"), [("gold", 0, "$"), ("silver", 2, "$"), ("copper", 2, "$")]),
                  (t("Dolar", "Dollar"), [("dxy", 2, "")]),
                  (t("Oynaklık & kripto", "Volatility & crypto"), [("vix", 2, ""), ("vxn", 2, ""), ("btc", 0, "$")])]
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
            rows.append(f'<tr class="g"><td colspan="8">{t("Faiz ve makas", "Rates and spreads")} <span class="mute">· {t("değişimler baz puan", "changes in basis points")}</span></td></tr>')
            for k in rates:
                a = A[k]
                last = f"{f.num(a['last'] * 100, 0)}bp" if k == "s2s10" else f.lvl(a["last"])
                rows.append(f'''<tr><th>{self.n(k)}</th><td class="n">{last}</td><td class="n">{self.chbp(a["w_bp"])}</td>
      <td class="n">{self.chbp(a.get("m_bp"))}</td><td class="n">{self.chbp(a.get("ytd_bp"))}</td><td class="n">{self.chbp(a.get("d200_bp"))}</td>
      <td class="rc">{rng(a)}</td><td class="sc">{spark(a["series"], w=120, h=28, fill=False, dot=False, sw=1.5)}</td></tr>''')
        if not rows:
            return ""
        heads = t(("", "Son", "1W", "1M", "YTD", "vs MA200", "52W aralık", "1 yıl"), ("", "Last", "1W", "1M", "YTD", "vs MA200", "52W range", "1 year"))
        th = "".join(f"<th>{h}</th>" for h in heads)
        body = f'<div class="tblw"><table class="board"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        return self.section(t(("Ek: piyasa ", "panosu"), ("Appendix: market ", "board")),
                            t("kesim ", "cut ") + f.long_date(self.d['cut']), body)

    # ── §13 crypto ──────────────────────────────────────────────────────────
    def crypto(self):
        A, f, t = self.A, self.f, self.t
        parts = []
        if "btc" in A:
            b = A["btc"]
            parts.append(f'<span><b>Bitcoin</b><span class="mono">${f.num(b["last"], 0)} {self.ch(b["w"], suffix=" 1W")} · {self.ch(b["ytd"], suffix=" YTD")}</span></span>')
        fg = self.d.get("fg")
        if fg and fg.get("px"):
            lab = fg.get("chg", "")
            if self.l == "tr":
                lab = {"Extreme Fear": "Aşırı korku", "Fear": "Korku", "Neutral": "Nötr", "Greed": "Açgözlülük",
                       "Extreme Greed": "Aşırı açgözlülük"}.get(lab, lab)
            parts.append(f'<span><b>{t("Korku &amp; Açgözlülük", "Fear &amp; Greed")}</b><span class="mono">{esc(fg["px"])} · {esc(lab)}</span></span>')
        if not parts:
            return ""
        return self.section(t(("Kripto ", "köşesi"), ("Crypto ", "corner")), t("kısaca", "in brief"), f'<div class="strip">{"".join(parts)}</div>')

    # ── page ────────────────────────────────────────────────────────────────
    def render(self):
        f, t = self.f, self.t
        hd = self.headline()
        css = open(os.path.join(HERE, "style.css")).read()
        hero = ""
        if hd:
            hero = f'''<section class="hero">
  <span class="k">{t("Haftanın tek cümlesi", "The week in one line")}</span>
  <h1>{hd["h1"]} — <i>{hd["h2"]}</i></h1>
  <p class="lede">{self.lede()}</p>
  <div class="chart"><div class="lab"><span class="k">{hd["lab"]}</span><b>{hd["val"]}</b></div>{spark(hd["series"], w=1000, h=150, layers=9)}</div>
</section>'''
        ed = self.d.get("editor") or {}
        editor = ""
        if ed.get(self.l):
            editor = (f'<div class="panel dark" style="margin:0 0 22px"><span class="k">{t("Editörün okuması", "Editor’s read")} · '
                      f'{esc(ed.get("model", ""))} · {t("sayılar sayfayla doğrulandı", "numbers checked against the page")}</span>'
                      f'<p style="margin-top:10px;font-size:17px;line-height:1.55">{esc(ed[self.l])}</p></div>')
        elif ed.get("rejected"):
            self.miss(t("Editörün okuması: model taslağı denetimden geçmedi, basılmadı",
                        "Editor’s read: the model draft failed the check and was not printed"))
        k5 = "".join(f'<div><span class="k">{a}</span><b class="{c}">{b}</b><span class="mono mute">{x}</span></div>' for a, b, x, c in self.key5())
        full = (self.R.get("show_metals") or "compact") == "full"
        sections = [self.decision(), self.setups(), self.chain(), self.macro()]
        if full:
            sections += [self.assets_full(), self.metals_full()]
        sections += [self.earnings(), self.news(), self.positioning(), self.asia(), self.breadth(),
                     self.calendar(), self.scorecard(), self.board(), self.crypto()]
        body = "".join(sections)
        MN = MISSING_NAME[self.l]
        lag = [f"{MN.get(k, k.upper())} ({f.day(a['date'])})" for k, a in self.A.items() if a.get("date") and a["date"] < self.d["cut"]]
        if lag:
            self.miss(t("Kesimden önce biten seriler — son yayımlanan değer kullanıldı: ",
                        "Series ending before the cut — last published value used: ") + ", ".join(lag))
        for k in self.d.get("report_missing") or []:
            self.miss(MN.get(k, k.upper()))
        for m in self.P.get("missing") or []:
            self.miss(self.tx(m))
        example = self.d.get("example_files") or []
        banner = ""
        if example:
            ex, used = ", ".join(example), ", ".join(x.replace(".yaml", ".example.yaml") for x in example)
            banner = (f'<p class="note" style="margin-bottom:18px">'
                      + t(f"<b>Örnek veriyle üretildi:</b> {ex} bulunamadı; {used} kullanıldı. Pozisyonlar ve seviyeler gerçek değil.",
                          f"<b>Built with example data:</b> {ex} not found; {used} used instead. Positions and levels are not real.")
                      + '</p>')
        miss = (f'<div class="note missing"><b>{t("Eksik veri", "Missing data")}</b> · {t("bu sayıda gösterilmeyenler", "not shown in this issue")}'
                f'<ul>{"".join(f"<li>{esc(m)}</li>" for m in self.missing)}</ul></div>' if self.missing else "")
        cut = f.long_date(self.d["cut"])
        wd = f.s["dayfull"][date.fromisoformat(self.d["cut"]).weekday()]
        foot = t(f"Kişisel karar bülteni; yatırım tavsiyesi değildir. Koşullar rules.yaml'dan, pozisyonlar portfolio.yaml'dan okunur. "
                 f"Tüm getiriler {cut} {wd} kapanışına göre.",
                 f"Personal decision bulletin; not investment advice. Conditions are read from rules.yaml, positions from portfolio.yaml. "
                 f"All returns are measured to the {wd} close of {cut}.")
        src = t("Veriler", "Data")
        return f'''<!doctype html>
<html lang="{self.l}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NO/CASHFLOW · {t("Haftalık karar bülteni", "Weekly decision bulletin")} · {cut}</title>
<meta name="robots" content="noindex,nofollow">
<link rel="icon" href="https://nocashflow.net/favicon.svg?v=4" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500&display=swap">
<style>{css}</style></head><body><div class="wrap">
<div class="top"><span class="wm">NO<b>/</b>CASHFLOW</span><span class="eyebrow"><em>{t("Haftalık karar bülteni", "Weekly decision bulletin")}</em> · {t(f"kesim: {cut} {wd} kapanışı", f"cut: {wd} close, {cut}")}</span></div>
{banner}{hero}
<div class="key5">{k5}</div>
{editor}
{body}
{miss}
<footer><span class="wm">NO<b>/</b>CASHFLOW</span><p>{foot} {src}: Yahoo Finance, FRED, ICE BofA, Cboe, OKX, Polymarket, Forex Factory.</p></footer>
</div></body></html>'''


def render(data, lang="tr", web_url=None):
    b = Bulletin(data, lang)
    html = b.render()
    return html, b.week_rows
