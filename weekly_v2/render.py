"""Weekly bulletin v2 — renderer (TR + EN).

Layout and styling come from the approved demo (Nov 2026): Nasdaq, gold and
silver first, crypto one line at the end, USD only, sectors as ETF + three
names from the owner's watchlist. Every sentence that depends on the week is
built from the numbers by a rule below; nothing is written ahead of time. A
block whose data is missing is left out instead of showing a guess.
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

# ── strings ─────────────────────────────────────────────────────────────────
S = {
    "tr": {
        "title": "Haftalık Bülten", "eyebrow": "Haftalık bülten",
        "hero_k": "Haftanın tek cümlesi",
        "s01": ("Üç varlık, ", "tek bakış"), "s01m": "trend = fiyat vs MA50 / MA200",
        "s02": ("Piyasa ", "panosu"), "s02m": "son kapanış",
        "s03": ("Fiyatı ne ", "hareket ettiriyor"), "s03m": "FRED · ICE · Cboe",
        "s04": ("Nasdaq ", "sektörleri"), "s04m": "her sektör: ETF + 3 hisse · haftanın lideri",
        "s05": ("AI değer ", "zinciri"), "s05m": "para zincirin neresine akıyor · eşit ağırlıklı sepetler",
        "s06": ("Asya çip ", "ekseni"), "s06m": "bellek döngüsünü Nasdaq'tan önce fiyatlar",
        "s07": ("Devler ve ", "genişlik"), "s07m": "Muhteşem 7, eşit ağırlık, hacim",
        "s08": ("Metallerin ", "içi"), "s08m": "oranlar ve madenciler · hepsi USD",
        "s09": ("Önümüzdeki ", "hafta"), "s09m": "CET · ABD verisi + izleme listenden bilançolar",
        "s10": ("İzleme ", "seviyeleri"), "s10m": "yatırım tavsiyesi değildir",
        "s11": ("Geçen haftanın ", "karnesi"), "s11m": "trend bir haftada değişti mi · aynı kural: fiyat vs MA50 / MA200",
        "s12": ("Kripto ", "köşesi"), "s12m": "kısaca",
        "trend_up": "Yükseliş trendi", "trend_dn": "Düşüş trendi", "trend_mix": "Kararsız",
        "last5": "Son 5 seans", "since": "'den",
        "th": ["", "Son", "1W", "1M", "YTD", "vs MA200", "52W aralık", "1 yıl"],
        "g_eq": "Hisseler", "g_met": "Metaller", "g_en": "Enerji & dolar", "g_vol": "Oynaklık & kripto",
        "g_rates": "Faiz", "g_rates_note": "değişimler baz puan",
        "corr_k": "Korelasyon · son 63 seans, günlük değişim", "corr_scale": "−1 ters · 0 ilişkisiz · +1 birlikte",
        "per_hour": " / saat", "index": " endeks",
        "m7_k": "Muhteşem 7 · haftalık", "sorted": "sıralı",
        "breadth_k": "Genişlik · eşit ağırlık / piyasa değeri", "one_month": "1 ay",
        "soxndx_k": "SOX / Nasdaq", "qqqvol_k": "QQQ hacmi", "vs60": "60 günlük ortalamaya göre",
        "week_rel": "1 hafta, göreli", "earn_k": "İzleme listenden bilançolar · 14 gün", "earn_src": "beklenti: analist ortalaması",
        "rev": "gelir", "prev": "önceki", "est": "beklenti",
        "no_earn": "Önümüzdeki 14 günde izleme listenden bilanço yok.",
        "no_cal": "Takvimde bu hafta yüksek etkili ABD verisi yok.",
        "fg": "Korku & Açgözlülük",
        "foot": "Bu bülten bilgi amaçlıdır; yatırım tavsiyesi değildir. Veriler: Yahoo Finance, FRED, OKX, Bitget, Polymarket, Forex Factory. Her rakam yayın anındaki son kapanıştır.",
        "web": "nocashflow.net'te oku",
        "days": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
        "months": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
        "bn": " mr", "mn": " mn",
    },
    "en": {
        "title": "Weekly Bulletin", "eyebrow": "Weekly bulletin",
        "hero_k": "The week in one line",
        "s01": ("Three assets, ", "one look"), "s01m": "trend = price vs MA50 / MA200",
        "s02": ("Market ", "board"), "s02m": "last close",
        "s03": ("What is ", "moving prices"), "s03m": "FRED · ICE · Cboe",
        "s04": ("Nasdaq ", "sectors"), "s04m": "each sector: ETF + 3 names · leader this week",
        "s05": ("AI value ", "chain"), "s05m": "where the money is flowing · equal-weight baskets",
        "s06": ("Asia chip ", "axis"), "s06m": "prices the memory cycle before Nasdaq does",
        "s07": ("Giants and ", "breadth"), "s07m": "Magnificent 7, equal weight, volume",
        "s08": ("Inside ", "metals"), "s08m": "ratios and miners · all USD",
        "s09": ("The week ", "ahead"), "s09m": "CET · US data + earnings from the watchlist",
        "s10": ("Levels to ", "watch"), "s10m": "not investment advice",
        "s11": ("Last week's ", "scorecard"), "s11m": "did the trend change in a week · same rule: price vs MA50 / MA200",
        "s12": ("Crypto ", "corner"), "s12m": "briefly",
        "trend_up": "Uptrend", "trend_dn": "Downtrend", "trend_mix": "Mixed",
        "last5": "Last 5 sessions", "since": "since ",
        "th": ["", "Last", "1W", "1M", "YTD", "vs MA200", "52W range", "1 year"],
        "g_eq": "Equities", "g_met": "Metals", "g_en": "Energy & dollar", "g_vol": "Volatility & crypto",
        "g_rates": "Rates", "g_rates_note": "changes in basis points",
        "corr_k": "Correlation · last 63 sessions, daily changes", "corr_scale": "−1 opposite · 0 unrelated · +1 together",
        "per_hour": " / hour", "index": " index",
        "m7_k": "Magnificent 7 · weekly", "sorted": "sorted",
        "breadth_k": "Breadth · equal weight / cap weight", "one_month": "1 month",
        "soxndx_k": "SOX / Nasdaq", "qqqvol_k": "QQQ volume", "vs60": "vs 60-day average",
        "week_rel": "1 week, relative", "earn_k": "Earnings from the watchlist · 14 days", "earn_src": "estimate: analyst mean",
        "rev": "revenue", "prev": "prior", "est": "est.",
        "no_earn": "No watchlist earnings in the next 14 days.",
        "no_cal": "No high-impact US data on the calendar this week.",
        "fg": "Fear & Greed",
        "foot": "This bulletin is for information only; it is not investment advice. Data: Yahoo Finance, FRED, OKX, Bitget, Polymarket, Forex Factory. Every figure is the last close at publication.",
        "web": "Read on nocashflow.net",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "bn": "bn", "mn": "m",
    },
}

NAME = {
    "ndx": ("Nasdaq 100", "Nasdaq 100"), "spx": ("S&P 500", "S&P 500"), "rut": ("Russell 2000", "Russell 2000"),
    "sox": ("Yarı iletken (SOX)", "Semiconductors (SOX)"), "gold": ("Altın", "Gold"), "silver": ("Gümüş", "Silver"),
    "plat": ("Platin", "Platinum"), "copper": ("Bakır", "Copper"), "brent": ("Brent petrol", "Brent crude"),
    "dxy": ("Dolar endeksi", "Dollar index"), "vix": ("VIX", "VIX"), "vxn": ("VXN", "VXN"), "btc": ("Bitcoin", "Bitcoin"),
    "us2y": ("ABD 2Y", "US 2Y"), "us10y": ("ABD 10Y", "US 10Y"), "real10": ("10Y reel faiz", "10Y real yield"),
    "be10": ("10Y başabaş enflasyon", "10Y breakeven inflation"), "s2s10": ("2s10s eğim", "2s10s slope"),
    "kospi": ("KOSPI", "KOSPI"), "twii": ("TAIEX", "TAIEX"), "n225": ("Nikkei 225", "Nikkei 225"), "usdjpy": ("USD/JPY", "USD/JPY"),
    "nvda": ("Nvidia", "Nvidia"), "aapl": ("Apple", "Apple"), "msft": ("Microsoft", "Microsoft"), "googl": ("Alphabet", "Alphabet"),
    "amzn": ("Amazon", "Amazon"), "meta": ("Meta", "Meta"), "tsla": ("Tesla", "Tesla"),
}

# US calendar events: TR names and why each matters (EN keeps the source name)
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
CAL_WHY = {
    "Retail Sales m/m": ("Güçlü tüketim → faiz indirimi daha uzak", "Strong spending → rate cuts further away"),
    "Core Retail Sales m/m": ("Güçlü tüketim → faiz indirimi daha uzak", "Strong spending → rate cuts further away"),
    "FOMC Meeting Minutes": ("Komitede indirim isteyen var mı?", "Is anyone on the committee asking for a cut?"),
    "Unemployment Claims": ("İşgücü yumuşarsa reel faiz geri çekilir", "A softer labour market pulls real yields down"),
    "CPI m/m": ("Reel faizin yönünü en çok bu belirler", "The single biggest input for real yields"),
    "Core CPI m/m": ("Reel faizin yönünü en çok bu belirler", "The single biggest input for real yields"),
    "Non-Farm Employment Change": ("Zayıf istihdam → indirim beklentisi, metallere destek", "Weak jobs → cut hopes, support for metals"),
    "Core PCE Price Index m/m": ("Fed'in hedeflediği enflasyon ölçüsü", "The inflation gauge the Fed targets"),
    "Federal Funds Rate": ("Haftanın ana olayı", "The main event of the week"),
}

# ── formatting ──────────────────────────────────────────────────────────────
class F:
    def __init__(self, lang):
        self.l = lang
        self.s = S[lang]

    def num(self, v, dec=2):
        s = f"{abs(v):,.{dec}f}"
        if self.l == "tr":
            s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return ("−" if v < 0 and round(abs(v), dec) != 0 else "") + s

    def pct(self, v, dec=2, sign=True):
        sg = ("+" if v > 0 else "−" if v < 0 else "") if sign else ("−" if v < 0 else "")
        if round(abs(v), dec) == 0:
            sg = ""
        body = self.num(abs(v), dec)
        return f"{sg}%{body}" if self.l == "tr" else f"{sg}{body}%"

    def lvl(self, v, dec=2):
        """A level that is itself a percentage (yields)."""
        return f"%{self.num(v, dec)}" if self.l == "tr" else f"{self.num(v, dec)}%"

    def bp(self, v):
        r = round(v)
        return ("+" if r > 0 else "−" if r < 0 else "") + f"{abs(r)}bp"

    def day(self, iso):
        d = date.fromisoformat(iso)
        return f"{self.s['days'][d.weekday()]} {d.day:02d}.{d.month:02d}"

    def long_date(self, iso):
        d = date.fromisoformat(iso)
        m = self.s["months"][d.month - 1]
        return f"{d.day} {m} {d.year}" if self.l == "tr" else f"{m} {d.day}, {d.year}"

    def money(self, v):
        return f"${self.num(v / 1e9, 1)}{self.s['bn']}" if v >= 1e9 else f"${self.num(v / 1e6, 0)}{self.s['mn']}"

    def ylab(self, a):
        if a.get("since"):
            d = date.fromisoformat(a["since"])
            return (f"{d.day:02d}.{d.month:02d}'den" if self.l == "tr"
                    else f"since {self.s['months'][d.month - 1]} {d.day}")
        return "YTD"


def dc(v):
    return "up" if v and v > 0 else "dn" if v and v < 0 else ""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def trend(a, f):
    p, m50, m200 = a["last"], a["ma50"], a.get("ma200")
    if m200 is None:
        return f.s["trend_mix"], ""
    if p > m50 and p > m200:
        return f.s["trend_up"], "up"
    if p < m50 and p < m200:
        return f.s["trend_dn"], "dn"
    return f.s["trend_mix"], ""


def regime(last, ma50, ma200):
    if ma200 is None:
        return "mix"
    if last > ma50 and last > ma200:
        return "up"
    if last < ma50 and last < ma200:
        return "dn"
    return "mix"


def wbp(A, k):
    a = A[k]
    if "w_bp" in a:
        return a["w_bp"]
    s = a["series"]
    return (s[-1] - s[-2]) * (1 if k == "s2s10" else 100)


def zmove(a, rate=False):
    """This week's move in units of its own typical weekly move (1y of weekly closes)."""
    s = a["series"]
    if len(s) < 12:
        return 0.0
    if rate:
        ch = [(s[i] - s[i - 1]) * 100 for i in range(1, len(s))]
        now = a.get("w_bp", ch[-1])
    else:
        ch = [(s[i] / s[i - 1] - 1) * 100 for i in range(1, len(s)) if s[i - 1]]
        now = a["w"]
    m = sum(ch) / len(ch)
    sd = math.sqrt(sum((c - m) ** 2 for c in ch) / (len(ch) - 1))
    # floor: a near-flat year would otherwise turn any small move into a headline
    return now / max(sd, 3.0 if rate else 0.5)


def sh(num, title, meta):
    return (f'<div class="sh"><span class="mono">§ {num:02d}</span><h2>{title[0]}<i>{title[1]}</i></h2>'
            f'<span class="meta mono mute">{meta}</span></div>')


# ── the bulletin ────────────────────────────────────────────────────────────
class Bulletin:
    def __init__(self, data, lang):
        self.d = data
        self.A = data["a"]
        self.l = lang
        self.f = F(lang)
        self.s = S[lang]
        self.skipped = []
        self.num = 0

    def has(self, *keys):
        return all(k in self.A for k in keys)

    def n(self, key):
        return NAME[key][0 if self.l == "tr" else 1]

    def T(self, tr, en):
        return tr if self.l == "tr" else en

    def section(self, title, meta, body, extra=""):
        self.num += 1
        return f'<section class="sec">{sh(self.num, title, meta)}{body}{extra}</section>'

    # headline: the week's most unusual move among the things the bulletin is about
    def headline(self):
        A, f, T = self.A, self.f, self.T
        cands = []
        for k in ("ndx", "gold", "silver", "dxy"):
            if k in A:
                cands.append((abs(zmove(A[k])), k, False))
        for k in ("us2y", "real10"):
            if k in A:
                cands.append((abs(zmove(A[k], rate=True)), k, True))
        if not cands:
            return None
        _, k, rate = max(cands)
        a = A[k]
        name = self.n(k)
        if rate:
            mv = wbp(A, k)
            if k == "real10":
                h1 = T(f"Reel faiz {f.lvl(a['last'])}", f"Real yields at {f.lvl(a['last'])}")
                h2 = (T("metaller bunu affetmiyor.", "metals do not forgive that.") if mv > 0
                      else T("metallere nefes alanı.", "room for metals to breathe."))
            else:
                h1 = T(f"2Y faiz {f.lvl(a['last'])}", f"The 2-year at {f.lvl(a['last'])}")
                h2 = (T("piyasa indirimi erteliyor.", "the market is pushing cuts out.") if mv > 0
                      else T("piyasa indirime yaklaşıyor.", "the market is pulling cuts in."))
            sub = T(f"bir haftada {f.bp(mv)}", f"{f.bp(mv)} in a week")
            return {"k": k, "h1": h1, "h2": h2, "sub": sub, "series": a["series"],
                    "lab": f"{name} · {T('1 yıl', '1 year')}", "val": f.lvl(a["last"])}
        p = pos52(a)
        h1 = T(f"{name} haftada {f.pct(a['w'], 1)}", f"{name} {f.pct(a['w'], 1)} on the week")
        if p >= .95:
            h2 = T("52 haftanın zirvesinde.", "at a 52-week high.")
        elif p <= .05:
            h2 = T("52 haftanın dibinde.", "at a 52-week low.")
        elif a.get("ma200") and (a["last"] - a["ma200"]) * a["w"] < 0 and abs(a["last"] / a["ma200"] - 1) < .03:
            h2 = T("MA200 sınırda.", "testing its MA200.")
        elif a["w"] > 0:
            h2 = T("alıcılar geri döndü.", "buyers are back.")
        else:
            h2 = T("satıcılar baskın.", "sellers are in charge.")
        dec = 0 if k in ("ndx", "gold") else 2
        cur = "$" if k in ("gold", "silver") else ""
        return {"k": k, "h1": h1, "h2": h2, "sub": "", "series": a["series"],
                "lab": f"{name} · {T('1 yıl', '1 year')}", "val": cur + f.num(a["last"], dec)}

    def lede(self):
        A, f, T = self.A, self.f, self.T
        out = []
        if self.has("ndx", "gold", "silver"):
            out.append(T(f"Nasdaq 100 haftayı {f.pct(A['ndx']['w'])}, altın {f.pct(A['gold']['w'])}, gümüş {f.pct(A['silver']['w'])} ile kapattı.",
                         f"Nasdaq 100 ended the week {f.pct(A['ndx']['w'])}, gold {f.pct(A['gold']['w'])}, silver {f.pct(A['silver']['w'])}."))
        if self.has("dxy"):
            p = pos52(A["dxy"])
            where = (T("52 haftanın zirvesine yakın", "near its 52-week high") if p >= .85 else
                     T("52 haftanın dibine yakın", "near its 52-week low") if p <= .15 else
                     T("52 haftalık aralığının ortasında", "mid-way through its 52-week range"))
            out.append(T(f"Dolar endeksi {f.num(A['dxy']['last'])}, {where}.", f"The dollar index is at {f.num(A['dxy']['last'])}, {where}."))
        if self.has("sox", "ndx", "nvda"):
            lead = A["sox"]["w"] > A["ndx"]["w"]
            out.append(T(f"Yarı iletkenler {f.pct(A['sox']['w'], 1)} ile Nasdaq'ın {'önünde' if lead else 'gerisinde'} kaldı; Nvidia {f.pct(A['nvda']['w'], 1)}.",
                         f"Semiconductors {'led' if lead else 'lagged'} Nasdaq at {f.pct(A['sox']['w'], 1)}; Nvidia {f.pct(A['nvda']['w'], 1)}."))
        if self.has("real10"):
            mv = wbp(A, "real10")
            amt = f"{abs(round(mv))}bp"
            if round(mv) == 0:
                out.append(T(f"10 yıllık reel faiz hafta boyunca yatay kaldı; şu an {f.lvl(A['real10']['last'])}.",
                             f"The 10-year real yield was flat on the week at {f.lvl(A['real10']['last'])}."))
            else:
                out.append(T(f"10 yıllık reel faiz bir haftada {amt} {'yükseldi' if mv > 0 else 'geriledi'}; şu an {f.lvl(A['real10']['last'])}.",
                             f"The 10-year real yield {'rose' if mv > 0 else 'fell'} {amt} on the week to {f.lvl(A['real10']['last'])}."))
        return " ".join(out)

    def key5(self):
        A, f, T = self.A, self.f, self.T
        items = []
        if "silver" in A:
            items.append((self.n("silver"), f.pct(A["silver"]["w"], 1), "1W", dc(A["silver"]["w"])))
        if "sox" in A:
            items.append((T("Yarı iletken", "Semis"), f.pct(A["sox"]["w"], 1), "1W", dc(A["sox"]["w"])))
        if "nvda" in A:
            items.append(("Nvidia", f.pct(A["nvda"]["w"], 1), "1W", dc(A["nvda"]["w"])))
        if "real10" in A:
            items.append((T("Reel faiz", "Real yield"), f.bp(wbp(A, "real10")), "1W", dc(wbp(A, "real10"))))
        if "h100" in A:
            items.append((T("H100 kirası", "H100 rent"), "$" + f.num(A["h100"]["last"]), T("saat başı", "per hour"), ""))
        return items

    # §01
    def assets(self):
        A, f = self.A, self.f
        cards = []
        for key, sub, dec, cur in (("ndx", "NDX", 0, ""), ("gold", "XAU · oz" if self.l == "en" else "XAU · ons", 0, "$"),
                                   ("silver", "XAG · oz" if self.l == "en" else "XAG · ons", 2, "$")):
            if key not in A:
                continue
            a = A[key]
            t, tc = trend(a, f)
            ma200 = f'<div><dt>MA200</dt><dd>{cur}{f.num(a["ma200"], dec)}</dd></div>' if a.get("ma200") else ""
            cards.append(f'''
    <article class="asset">
      <header><div><h3>{self.n(key)}</h3><span class="mono mute">{sub}</span></div><span class="pill {tc}">{t}</span></header>
      <div class="px">{cur}{f.num(a["last"], dec)}</div>
      <div class="chg mono"><span class="{dc(a["w"])}">{f.pct(a["w"])} 1W</span><span class="{dc(a["m"])}">{f.pct(a["m"], 1)} 1M</span><span class="{dc(a["ytd"])}">{f.pct(a["ytd"], 1)} {f.ylab(a)}</span></div>
      {spark(a["series"], layers=4)}
      <div class="k" style="margin-top:2px">{self.s["last5"]}</div>{bars5(a, f)}
      <dl class="lv"><div><dt>MA50</dt><dd>{cur}{f.num(a["ma50"], dec)}</dd></div>{ma200}</dl>
      <div class="r52"><span class="mono mute">52W</span>{rng(a)}<span class="mono">{cur}{f.num(a["lo52"], dec)} — {cur}{f.num(a["hi52"], dec)}</span></div>
    </article>''')
        if not cards:
            return ""
        return self.section(self.s["s01"], self.s["s01m"], f'<div class="assets">{"".join(cards)}</div>')

    # §02
    def board(self):
        A, f, s = self.A, self.f, self.s
        groups = [(s["g_eq"], [("ndx", 0, ""), ("spx", 0, ""), ("rut", 0, ""), ("sox", 0, "")]),
                  (s["g_met"], [("gold", 0, "$"), ("silver", 2, "$"), ("plat", 0, "$"), ("copper", 2, "$")]),
                  (s["g_en"], [("brent", 2, "$"), ("dxy", 2, "")]),
                  (s["g_vol"], [("vix", 2, ""), ("vxn", 2, ""), ("btc", 0, "$")])]
        rows = []
        for grp, items in groups:
            items = [i for i in items if i[0] in A]
            if not items:
                continue
            rows.append(f'<tr class="g"><td colspan="8">{grp}</td></tr>')
            for k, dec, cur in items:
                a = A[k]
                d200 = (a["last"] / a["ma200"] - 1) * 100 if a.get("ma200") else None
                d200c = f'<td class="n {dc(d200)}">{f.pct(d200, 1)}</td>' if d200 is not None else '<td class="n">—</td>'
                rows.append(f'''<tr><th>{self.n(k)}</th><td class="n">{cur}{f.num(a["last"], dec)}</td>
          <td class="n {dc(a["w"])}">{f.pct(a["w"], 1)}</td><td class="n {dc(a["m"])}">{f.pct(a["m"], 1)}</td><td class="n {dc(a["ytd"])}">{f.pct(a["ytd"], 1)}</td>
          {d200c}<td class="rc">{rng(a)}</td><td class="sc">{spark(a["series"], w=120, h=28, fill=False, dot=False, sw=1.5)}</td></tr>''')
        rates = [k for k in ("us2y", "us10y", "real10", "be10", "s2s10") if k in A]
        if rates:
            rows.append(f'<tr class="g"><td colspan="8">{s["g_rates"]} <span class="mute">· {s["g_rates_note"]}</span></td></tr>')
            for k in rates:
                a = A[k]
                last = f"{round(a['last'])}bp" if k == "s2s10" else f.lvl(a["last"])
                m_bp = a.get("m_bp")
                rows.append(f'''<tr><th>{self.n(k)}</th><td class="n">{last}</td><td class="n {dc(wbp(A, k))}">{f.bp(wbp(A, k))}</td>
      <td class="n {dc(m_bp or 0)}">{f.bp(m_bp) if m_bp is not None else "—"}</td><td class="n">—</td><td class="n">—</td>
      <td class="rc">{rng(a)}</td><td class="sc">{spark(a["series"], w=120, h=28, fill=False, dot=False, sw=1.5)}</td></tr>''')
        if not rows:
            return ""
        th = "".join(f"<th>{h}</th>" for h in s["th"])
        body = f'<div class="tblw"><table class="board"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        return self.section(s["s02"], f'{s["s02m"]} · {self.d["asof"]}', body)

    # §03
    def drivers(self):
        A, f, T = self.A, self.f, self.T
        drv = []
        if self.has("us2y"):
            mv = wbp(A, "us2y")
            drv.append((self.n("us2y"), f.lvl(A["us2y"]["last"]), f.bp(mv) + " 1W", dc(mv),
                        T("Fed beklentisinin en saf ölçüsü. " + ("Yükselmesi “indirim yok” demek." if mv > 0 else "Düşmesi indirim beklentisinin güçlendiği anlamına gelir."),
                          "The purest read on Fed expectations. " + ("Rising means “no cuts”." if mv > 0 else "Falling means cut hopes are building."))))
        if self.has("us10y"):
            mv = wbp(A, "us10y")
            split = ""
            if self.has("real10", "be10"):
                r, b = wbp(A, "real10"), wbp(A, "be10")
                part = T("reel faizden", "real yield") if abs(r) >= abs(b) else T("enflasyon beklentisinden", "inflation expectations")
                split = T(f"Haftalık hareketin {f.bp(r)} kısmı reel faiz (şu an {f.lvl(A['real10']['last'])}), {f.bp(b)} kısmı başabaş enflasyon; ağırlık {part} geliyor. Reel faiz, getirisi olmayan altını tutmanın fırsat maliyeti.",
                          f"Of the weekly move, {f.bp(r)} is real yield (now {f.lvl(A['real10']['last'])}) and {f.bp(b)} breakeven inflation; most of it is {part}. The real yield is the opportunity cost of holding gold, which pays nothing.")
            drv.append((self.n("us10y"), f.lvl(A["us10y"]["last"]), f.bp(mv) + " 1W", dc(mv), split or T("Uzun vadeli borçlanma maliyeti.", "The long-term cost of borrowing.")))
        if self.has("dxy"):
            p = pos52(A["dxy"])
            where = (T("52 haftanın zirvesine yakın.", "Near its 52-week high.") if p >= .85 else
                     T("52 haftanın dibine yakın.", "Near its 52-week low.") if p <= .15 else "")
            drv.append((self.n("dxy"), f.num(A["dxy"]["last"]), f.pct(A["dxy"]["w"]) + " 1W", dc(A["dxy"]["w"]),
                        (where + " " if where else "") + T("Dolar güçlenince dolar cinsinden emtialar ucuzlamak zorunda kalır.",
                                                            "A stronger dollar forces dollar-priced commodities lower.")))
        if self.has("vxn"):
            v = A["vxn"]
            above = v["last"] > v["ma50"]
            drv.append(("VXN", f.num(v["last"]), f.pct(v["w"], 1) + " 1W", dc(v["w"]),
                        T(f"Nasdaq'ın korku endeksi. 50 günlük ortalaması {f.num(v['ma50'])}; {'hâlâ üstünde' if above else 'altına indi'}.",
                          f"Nasdaq's fear gauge. Its 50-day average is {f.num(v['ma50'])}; it is {'still above it' if above else 'now below it'}.")))
        body = "".join(f'<div class="drv"><span class="k">{k}</span><b>{v}</b><span class="mono {c}">{ch}</span><p>{why}</p></div>'
                       for k, v, ch, c, why in drv)
        C = self.d.get("corr") or {}
        pairs = [("gold_real", T("Altın × reel faiz", "Gold × real yield"), T("faiz yükselince altın düşmeli", "gold should fall when yields rise"), -1),
                 ("gold_dxy", T("Altın × dolar", "Gold × dollar"), T("dolar güçlenince altın düşmeli", "gold should fall when the dollar rises"), -1),
                 ("ndx_10y", T("Nasdaq × 10Y faiz", "Nasdaq × 10Y yield"), T("faiz yükselince teknoloji düşmeli", "tech should fall when yields rise"), -1),
                 ("ndx_gold", T("Nasdaq × altın", "Nasdaq × gold"), T("biri diğerini hedge ediyor mu", "does one hedge the other"), 0),
                 ("silver_copper", T("Gümüş × bakır", "Silver × copper"), T("gümüş sanayi metali gibi mi davranıyor", "is silver trading like an industrial metal"), 1)]
        items = []
        for k, name, test, expect in pairs:
            if k not in C:
                continue
            r = C[k]
            st = abs(r)
            word = (T("ilişki yok", "no relationship") if st < .2 else T("zayıf", "weak") if st < .4 else
                    T("orta", "moderate") if st < .7 else T("güçlü", "strong"))
            if st < .2:
                read = T(f"Bu dönemde {word}.", f"Right now there is {word}.")
            else:
                dirw = T("ters", "inverse") if r < 0 else T("aynı yönde", "positive")
                ok = (expect < 0 and r < 0) or (expect > 0 and r > 0)
                if expect == 0:
                    tail = (T(" İkisi birlikte likiditeyle hareket ediyor, birbirini hedge etmiyor.", " They move together with liquidity; neither hedges the other.") if r > 0
                            else T(" Biri düşerken diğeri tutuyor: hedge işlevi çalışıyor.", " One holds when the other falls: the hedge works."))
                else:
                    tail = (T(" Ders kitabındaki ilişki çalışıyor.", " The textbook relationship is working.") if ok
                            else T(" Ders kitabındaki ilişki bu dönemde çalışmıyor.", " The textbook relationship is not working right now."))
                read = T(f"{word.capitalize()}, {dirw}.", f"{word.capitalize()}, {dirw}.") + tail
            sign = "+" if r >= 0 else "−"
            w = abs(r) * 50
            left = 50 if r >= 0 else 50 - w
            bar = f'<div class="cb"><span class="z"></span><i class="{"up" if r >= 0 else "dn"}" style="left:{left:.1f}%;width:{w:.1f}%"></i></div>'
            items.append(f'<li><div class="ch"><b>{name}</b><span class="mono">{sign}{f.num(abs(r))}</span></div>{bar}'
                         f'<p><span class="mute">{test.capitalize()}.</span> {read}</p></li>')
        corr = ""
        if items:
            corr = (f'<div class="panel corr"><div class="ph"><span class="k">{self.s["corr_k"]}</span>'
                    f'<span class="mono mute">{self.s["corr_scale"]}</span></div><ul>{"".join(items)}</ul></div>')
        if not body and not corr:
            return ""
        return self.section(self.s["s03"], self.s["s03m"], f'<div class="drivers">{body}</div>{corr}')

    # §04
    def hrow(self, sym, mx):
        a, f = self.A[sym.lower()], self.f
        side = "left:50%" if a["w"] >= 0 else "right:50%"
        return (f'<li><div class="hn"><b>{NAMES.get(sym, sym)}</b><span class="mono mute">{sym}</span></div>'
                f'<span class="mono">${f.num(a["last"])}</span>'
                f'<div class="hb"><span class="z"></span><i class="{dc(a["w"])}" style="{side};width:{min(abs(a["w"]) / mx * 50, 50):.1f}%"></i></div>'
                f'<span class="mono {dc(a["w"])} r">{f.pct(a["w"], 1)}</span>'
                f'<span class="mono {dc(a["ytd"])} r">{f.pct(a["ytd"], 0)} <small>{f.ylab(a)}</small></span></li>')

    def sectors(self):
        A, f, T = self.A, self.f, self.T
        pick = T("İzleme listenden 3 hisse", "3 names from the watchlist")
        secs = [(T("Yarı iletken", "Semiconductors"), "SMH", "smh", ["NVDA", "AMD", "AVGO"], pick),
                (T("Yazılım", "Software"), "IGV", "igv", ["NOW", "CRWD", "PANW"], pick),
                (T("Optik & fotonik", "Optics & photonics"), T("Sepet · 4 hisse", "Basket · 4 names"), "optics", ["CRDO", "ALAB", "LITE"],
                 T("Saf ETF yok: CRDO, ALAB, LITE, AAOI eşit ağırlıklı sepet", "No pure ETF: equal-weight basket of CRDO, ALAB, LITE, AAOI")),
                (T("Uzay", "Space"), "NASA", "nasa", ["SPCX", "RKLB", "ASTS"],
                 T("Tema Space Innovators ETF · izleme listenden 3 hisse", "Tema Space Innovators ETF · 3 names from the watchlist"))]
        cards, live = [], []
        for name, etf, key, holds, note in secs:
            if key not in A:
                continue
            holds = [t for t in holds if t.lower() in A]
            e = A[key]
            live.append((name, e["w"]))
            mx = max([abs(A[t.lower()]["w"]) for t in holds] + [1])
            level = (f'<div class="px">{f.num(e["last"], 1)}<small class="mono mute">{self.s["index"]}</small></div>' if key == "optics"
                     else f'<div class="px">${f.num(e["last"])}</div>')
            d200 = (e["last"] / e["ma200"] - 1) * 100 if e.get("ma200") else None
            cards.append(
                f'<article class="sector"><header><div><span class="k">{name}</span><h3>{etf}</h3></div>'
                f'{spark(e["series"], w=180, h=46, layers=3)}</header>{level}'
                f'<div class="chg mono"><span class="{dc(e["w"])}">{f.pct(e["w"], 1)} 1W</span>'
                f'<span class="{dc(e["m"])}">{f.pct(e["m"], 1)} 1M</span><span class="{dc(e["ytd"])}">{f.pct(e["ytd"], 1)} {f.ylab(e)}</span>'
                + (f'<span class="{dc(d200)}">{f.pct(d200, 1)} vs MA200</span>' if d200 is not None else '') + '</div>'
                f'<ul class="holds">{"".join(self.hrow(t, mx) for t in holds)}</ul><p class="mono mute sn">{note}</p></article>')
        if not cards:
            return ""
        lead = max(live, key=lambda x: x[1])[0]
        return self.section(self.s["s04"], f'{self.s["s04m"]} {lead.lower() if self.l == "tr" else lead.lower()}',
                            f'<div class="sectors">{"".join(cards)}</div>')

    # §05
    def chain(self):
        A, f, T = self.A, self.f, self.T
        links = [("neocloud", "Neocloud", T("GPU'yu kiraya veren bulutlar", "clouds that rent out GPUs")),
                 ("memory", T("Bellek", "Memory"), T("HBM ve NAND", "HBM and NAND")),
                 ("optics", T("Optik", "Optics"), T("veri merkezi bağlantısı", "data-centre interconnect")),
                 ("power", T("Enerji", "Power"), T("şebeke, yakıt hücresi, nükleer", "grid, fuel cells, nuclear"))]
        links = [l for l in links if l[0] in A]
        if not links:
            return ""
        out = []
        n = 1
        H1, B2 = A.get("h100"), A.get("b200")
        if H1:
            b2 = (T(f" B200 ${f.num(B2['last'])} / saat (Bitget, ince hacim).", f" B200 ${f.num(B2['last'])} / hour (Bitget, thin volume).") if B2 else "")
            since = ""
            if H1.get("since"):
                d = date.fromisoformat(H1["since"])
                since = T(f" · {d.month:02d}.{d.year}'den beri işlem görüyor", f" · trading since {self.s['months'][d.month - 1]} {d.year}")
            out.append(f'''<article class="link gpu"><span class="n mono">0{n}</span><span class="k">{T("GPU kirası", "GPU rent")}</span><h3>H100</h3>
  <div class="px">${f.num(H1["last"])}<small class="mono">{self.s["per_hour"]}</small></div>
  <div class="chg mono"><span class="{dc(H1["w"])}">{f.pct(H1["w"], 1)} 1W</span><span class="{dc(H1["m"])}">{f.pct(H1["m"], 1)} 1M</span></div>
  {spark(H1["series"], w=240, h=46, layers=3)}
  <p>{T("Zincirin en erken sinyali: kira düşerse talep zayıflıyor demektir.", "The chain's earliest signal: falling rent means demand is weakening.")}{b2}</p>
  <span class="mono mute src">{T("OKX vadeli", "OKX perpetual")}{since}</span></article>''')
            n += 1
        baskets = self.d.get("baskets", {})
        for k, name, sub in links:
            b = A[k]
            chips = "".join(f'<li><span>{NAMES.get(t, t)}</span><b class="mono {dc(A[t.lower()]["w"])}">{f.pct(A[t.lower()]["w"], 1)}</b></li>'
                            for t in baskets.get(k, []) if t.lower() in A)
            out.append(f'''<article class="link"><span class="n mono">0{n}</span><span class="k">{name}</span><h3>{sub}</h3>
  <div class="px {dc(b["w"])}">{f.pct(b["w"], 1)}<small class="mono mute"> 1W</small></div>
  <div class="chg mono"><span class="{dc(b["m"])}">{f.pct(b["m"], 1)} 1M</span><span class="{dc(b["ytd"])}">{f.pct(b["ytd"], 0)} {f.ylab(b)}</span></div>
  <ul class="chips">{chips}</ul></article>''')
            n += 1
        ranked = sorted(links, key=lambda x: A[x[0]]["w"], reverse=True)
        best, worst = ranked[0], ranked[-1]
        read = T(f"Bu hafta para zincirin <b>{best[1].lower()}</b> halkasına aktı ({f.pct(A[best[0]]['w'], 1)}); en zayıf halka <b>{worst[1].lower()}</b> ({f.pct(A[worst[0]]['w'], 1)}).",
                 f"This week money flowed to the <b>{best[1].lower()}</b> link ({f.pct(A[best[0]]['w'], 1)}); the weakest link was <b>{worst[1].lower()}</b> ({f.pct(A[worst[0]]['w'], 1)}).")
        if H1:
            w, m = H1["w"], H1["m"]
            if w <= -3 and m < 0:
                read += T(f" H100 kirası haftada {f.pct(w, 1)}, ayda {f.pct(m, 1)}: talep tarafında bozulma işareti var.",
                          f" H100 rent {f.pct(w, 1)} on the week and {f.pct(m, 1)} on the month: demand is showing cracks.")
            elif w <= -3:
                read += T(f" H100 kirası haftada {f.pct(w, 1)} geriledi ama ayda hâlâ {f.pct(m, 1)}: henüz bozulma değil.",
                          f" H100 rent fell {f.pct(w, 1)} on the week but is still {f.pct(m, 1)} on the month: not a crack yet.")
            else:
                read += T(f" H100 kirası haftada {f.pct(w, 1)}: talep tarafında bozulma yok.",
                          f" H100 rent {f.pct(w, 1)} on the week: no sign of demand cracking.")
        return self.section(self.s["s05"], self.s["s05m"], f'<div class="chain">{"".join(out)}</div><p class="read">{read}</p>')

    # §06
    def asia(self):
        A, f, T = self.A, self.f, self.T
        rows = [("kospi", T("Kore · Samsung, SK hynix", "Korea · Samsung, SK hynix"), 0), ("twii", T("Tayvan · TSMC", "Taiwan · TSMC"), 0),
                ("n225", T("Japonya · çip ekipmanı", "Japan · chip equipment"), 0), ("usdjpy", T("yen taşıma işlemi", "the yen carry trade"), 2)]
        rows = [r for r in rows if r[0] in A]
        if not rows:
            return ""
        cards = "".join(f'''<div class="panel{' dark' if k == 'usdjpy' else ''}"><span class="k">{sub}</span><h3>{self.n(k)}</h3>
  <div class="big">{f.num(A[k]["last"], d)}</div>
  <div class="chg mono"><span class="{dc(A[k]["w"])}">{f.pct(A[k]["w"], 1)} 1W</span><span class="{dc(A[k]["m"])}">{f.pct(A[k]["m"], 1)} 1M</span><span class="{dc(A[k]["ytd"])}">{f.pct(A[k]["ytd"], 0)} YTD</span></div>
  {spark(A[k]["series"], w=300, h=56, fill=k != "usdjpy", layers=0 if k == "usdjpy" else 3)}</div>''' for k, sub, d in rows)
        read = ""
        if self.has("kospi", "sox"):
            read = T(f"KOSPI 1M {f.pct(A['kospi']['m'], 1)}, SOX {f.pct(A['sox']['m'], 1)}.", f"KOSPI 1M {f.pct(A['kospi']['m'], 1)}, SOX {f.pct(A['sox']['m'], 1)}.")
        if "usdjpy" in A:
            read += T(f" USD/JPY {f.num(A['usdjpy']['last'])}: yen hızlı güçlenirse kaldıraçlı pozisyonlar kapanır, Nasdaq bunu ilk hisseden yerdir.",
                      f" USD/JPY {f.num(A['usdjpy']['last'])}: if the yen strengthens fast, leveraged positions unwind, and Nasdaq feels it first.")
        return self.section(self.s["s06"], self.s["s06m"], f'<div class="asia">{cards}</div>' + (f'<p class="read">{read.strip()}</p>' if read else ""))

    # §07
    def giants(self):
        A, f, T = self.A, self.f, self.T
        m7 = [k for k in ("nvda", "aapl", "msft", "googl", "amzn", "meta", "tsla") if k in A]
        if not m7:
            return ""
        m7.sort(key=lambda k: A[k]["w"])
        mx = max(abs(A[k]["w"]) for k in m7) or 1
        lis = "".join(f'''<li><span class="nm">{self.n(k)}</span><span class="mono px2">${f.num(A[k]["last"])}</span>
  <div class="hb"><span class="z"></span><i class="{dc(A[k]["w"])}" style="{"left:50%" if A[k]["w"] >= 0 else "right:50%"};width:{abs(A[k]["w"]) / mx * 50:.1f}%"></i></div>
  <span class="mono {dc(A[k]["w"])}">{f.pct(A[k]["w"], 1)}</span><span class="mono mute ytd">{f.pct(A[k]["ytd"], 0)} YTD</span></li>''' for k in m7)
        right = ""
        if "ew_cw" in A:
            ew = A["ew_cw"]
            better = ew["m"] > 0
            txt = (T(f"Eşit ağırlıklı Nasdaq (QQQE), devlerin ağırlıklı olduğu QQQ'dan son bir ayda <b>{f.pct(abs(ew['m']), 1, sign=False)}</b> daha iyi. Ortalama hisse devlerden sağlam.",
                     f"Equal-weight Nasdaq (QQQE) beat cap-weighted QQQ by <b>{f.pct(abs(ew['m']), 1, sign=False)}</b> over the past month. The average stock is holding up better than the giants.") if better else
                   T(f"Devlerin ağırlıklı olduğu QQQ, eşit ağırlıklı Nasdaq'tan (QQQE) son bir ayda <b>{f.pct(abs(ew['m']), 1, sign=False)}</b> daha iyi. Yükselişi birkaç dev taşıyor.",
                     f"Cap-weighted QQQ beat equal-weight Nasdaq (QQQE) by <b>{f.pct(abs(ew['m']), 1, sign=False)}</b> over the past month. A handful of giants are carrying the index."))
            right += (f'<div class="panel dark"><span class="k">{self.s["breadth_k"]}</span>'
                      f'<div class="big2"><span class="{dc(ew["m"])}">{f.pct(ew["m"], 1)}</span><small class="mono">{self.s["one_month"]}</small></div>'
                      f'<p>{txt}</p>{spark(ew["series"], w=500, h=70, layers=4)}</div>')
        pair = ""
        if "sox_ndx" in A:
            sx = A["sox_ndx"]
            pair += (f'<div class="panel"><span class="k">{self.s["soxndx_k"]}</span><b class="{dc(sx["w"])}">{f.pct(sx["w"], 1)}</b>'
                     f'<span class="mono mute">{T("1 hafta · yarı iletken " + ("önde" if sx["w"] > 0 else "geride"), "1 week · semis " + ("ahead" if sx["w"] > 0 else "behind"))}</span></div>')
        vol = (self.d.get("vol") or {}).get("qqq")
        if vol:
            pair += f'<div class="panel"><span class="k">{self.s["qqqvol_k"]}</span><b>{f.num(vol)}×</b><span class="mono mute">{self.s["vs60"]}</span></div>'
        if pair:
            right += f'<div class="pair">{pair}</div>'
        body = (f'<div class="split"><div class="panel"><div class="ph"><span class="k">{self.s["m7_k"]}</span><span class="mono mute">{self.s["sorted"]}</span></div>'
                f'<ul class="m7">{lis}</ul></div><div class="stack">{right}</div></div>')
        return self.section(self.s["s07"], self.s["s07m"], body)

    # §08
    def metals(self):
        A, f, T = self.A, self.f, self.T
        panels = []
        if "gsr" in A:
            G = A["gsr"]
            panels.append(f'''<div class="panel dark"><span class="k">{T("Altın / gümüş oranı", "Gold / silver ratio")}</span><div class="big">{f.num(G["last"], 1)}</div>
      <div class="chg mono"><span class="{dc(G["w"])}">{f.pct(G["w"], 1)} 1W</span><span class="{dc(G["ytd"])}">{f.pct(G["ytd"], 0)} YTD</span></div>
      <p>{T("Oran yükseliyorsa gümüş altından kötü gidiyor. Dönüşü izlerken önce bu oranın dönmesine bak.", "A rising ratio means silver is doing worse than gold. When looking for a turn, watch this ratio turn first.")}</p>{spark(G["series"], w=400, h=70, layers=4)}</div>''')
        if "cu_au" in A:
            CA = A["cu_au"]
            panels.append(f'''<div class="panel"><span class="k">{T("Bakır / altın oranı", "Copper / gold ratio")}</span><div class="big">{f.num(CA["last"], 2)}</div>
      <div class="chg mono"><span class="{dc(CA["w"])}">{f.pct(CA["w"], 1)} 1W</span><span class="{dc(CA["ytd"])}">{f.pct(CA["ytd"], 1)} YTD</span></div>
      <p>{T("Büyüme beklentisinin metal karşılığı: bakır altından iyi gidiyorsa piyasa resesyon değil büyüme fiyatlıyor.", "Growth expectations in metal form: copper beating gold means the market is pricing growth, not recession.")}</p>{spark(CA["series"], w=400, h=70, fill=False)}</div>''')
        for key, lab, metal_tr, metal_en in (("sil_silver", T("Gümüş madencileri / gümüş (SIL)", "Silver miners / silver (SIL)"), "gümüşün", "silver"),
                                            ("gdx_gold", T("Madenciler / altın (GDX)", "Miners / gold (GDX)"), "altının", "gold")):
            if key not in A:
                continue
            M = A[key]
            if M["w"] > 0:
                p = T(f"Madenciler metalden iyi: piyasa {metal_tr} dibe yakın olduğunu düşünüyor.", f"Miners are beating the metal: the market thinks {metal_en} is near a bottom.")
            else:
                p = T("Madenciler metalden de kötü: piyasa düşük fiyatın kalıcı olabileceğini fiyatlıyor.", "Miners are doing worse than the metal: the market is pricing low prices as lasting.")
            extra = ""
            vol = self.d.get("vol") or {}
            if key == "gdx_gold" and ("gld" in vol or "slv" in vol):
                parts = []
                if "gld" in vol:
                    parts.append(f'<span>{T("GLD hacmi", "GLD volume")} <b>{f.num(vol["gld"])}×</b></span>')
                if "slv" in vol:
                    parts.append(f'<span>{T("SLV hacmi", "SLV volume")} <b>{f.num(vol["slv"])}×</b></span>')
                extra = f'<div class="vols mono">{"".join(parts)}</div>'
            panels.append(f'''<div class="panel"><span class="k">{lab}</span><div class="big {dc(M["w"])}">{f.pct(M["w"], 1)}</div>
      <div class="chg mono"><span class="mute">{self.s["week_rel"]}</span><span class="{dc(M["ytd"])}">{f.pct(M["ytd"], 1)} YTD</span></div>
      <p>{p}</p>{spark(M["series"], w=400, h=70, fill=False) if key == "sil_silver" else ""}{extra}</div>''')
        if not panels:
            return ""
        return self.section(self.s["s08"], self.s["s08m"], f'<div class="metals">{"".join(panels)}</div>')

    # §09
    def week_ahead(self):
        f, T = self.f, self.T
        cal = []
        for e in self.d.get("calendar", []):
            if e.get("impact") != "high" and e.get("event") not in CAL_WHY:
                continue
            ev = e["event"]
            name = CAL_TR.get(ev, ev) if self.l == "tr" else ev
            if self.l == "tr" and ev not in CAL_TR and "Speaks" in ev:
                name = ev.replace("Fed Chairman", "Fed Başkanı").replace("FOMC Member", "FOMC üyesi").replace(" Speaks", " konuşuyor")
            pe = ""
            if e.get("prev") not in (None, "—") or e.get("est") not in (None, "—"):
                pv = e.get("prev", "—")
                es = e.get("est", "—")
                if self.l == "tr":
                    pv, es = pv.replace(".", ","), es.replace(".", ",")
                pe = f'<span class="mono mute">{self.s["prev"]} {esc(pv)} · {self.s["est"]} {esc(es)}</span>'
            why = CAL_WHY.get(ev)
            if why is None and "Speaks" in ev and ("Chair" in ev or "Fed" in ev):
                why = ("Reel faizin yönü için dinlenecek ses", "A voice that matters for real yields")
            whyh = f'<p>{why[0] if self.l == "tr" else why[1]}</p>' if why else ""
            wd = e.get("wd", date.fromisoformat(e["cet_date"]).weekday())
            cal.append(f'<li><span class="mono when">{self.s["days"][wd]} {esc(e.get("time", ""))}</span><div><b>{esc(name)}</b>{pe}{whyh}</div>'
                       f'<span class="imp {e.get("impact", "")}"></span></li>')
        cal_html = f'<ul class="cal">{"".join(cal[:8])}</ul>' if cal else f'<p class="note">{self.s["no_cal"]}</p>'
        fed = self.d.get("fed")
        fed_html = ""
        if fed:
            p = fed["p"]
            when = f.long_date(fed["date"])
            if p < 20:
                txt = T(f"Piyasa {when} toplantısında indirim beklemiyor.", f"The market does not expect a cut at the {when} meeting.")
            elif p < 60:
                txt = T(f"Piyasa {when} toplantısı için kararsız.", f"The market is split on the {when} meeting.")
            else:
                txt = T(f"Piyasa {when} toplantısında indirim bekliyor.", f"The market expects a cut at the {when} meeting.")
            if "us2y" in self.A:
                txt += T(f" 2Y faiz {f.lvl(self.A['us2y']['last'])}.", f" The 2-year is at {f.lvl(self.A['us2y']['last'])}.")
            fed_html = (f'<div class="panel dark"><span class="k">Fed · {when}</span>'
                        f'<div class="big" style="margin-top:12px">{f.lvl(p, 1)}</div><span class="mono" style="color:rgba(236,234,227,.6)">'
                        f'{T("faiz indirimi olasılığı · Polymarket", "probability of a cut · Polymarket")}</span><p>{txt}</p></div>')
        earn = self.d.get("earn") or []
        if earn:
            lis = "".join(f'''<li><span class="mono when">{f.day(e["d"])}</span>
  <div><b>{NAMES.get(e["t"], e["t"])}</b> <span class="mono mute">{e["t"]}</span></div>
  <span class="mono r">{("EPS " + ("−" if e["eps"] < 0 else "") + "$" + f.num(abs(e["eps"]))) if e.get("eps") is not None else "—"}</span>
  <span class="mono mute r">{(self.s["rev"] + " " + f.money(e["rev"])) if e.get("rev") else ""}</span></li>''' for e in earn)
            earn_html = (f'<div class="panel earn"><div class="ph"><span class="k">{self.s["earn_k"]}</span><span class="mono mute">{self.s["earn_src"]}</span></div>'
                         f'<ul>{lis}</ul></div>')
        else:
            earn_html = f'<p class="note">{self.s["no_earn"]}</p>'
        return self.section(self.s["s09"], self.s["s09m"], f'<div class="split">{cal_html}{fed_html}</div>{earn_html}')

    # §10 levels, §11 scorecard share one rule: regime = price vs MA50 and MA200
    LEVEL_ASSETS = (("ndx", 0, ""), ("gold", 0, "$"), ("silver", 2, "$"))

    def levels(self):
        A, f, T = self.A, self.f, self.T
        cards = []
        for k, dec, cur in self.LEVEL_ASSETS:
            if k not in A or not A[k].get("ma200"):
                continue
            a = A[k]
            m50, m200, p = a["ma50"], a["ma200"], a["last"]
            rg = regime(p, m50, m200)
            if rg == "up":
                title = T("Trend yukarı", "Trend up")
                lines = [T(f"Fiyat <b>{cur}{f.num(p, dec)}</b>; iki ortalamanın da üstünde.", f"Price <b>{cur}{f.num(p, dec)}</b>; above both averages."),
                         T(f"<b>{cur}{f.num(m50, dec)}</b> (MA50) ilk destek; altında kapanış trendi kararsıza çevirir.", f"<b>{cur}{f.num(m50, dec)}</b> (MA50) is first support; a close below turns the trend mixed."),
                         T(f"<b>{cur}{f.num(m200, dec)}</b> (MA200) kırılırsa trend aşağı döner.", f"A break of <b>{cur}{f.num(m200, dec)}</b> (MA200) turns the trend down.")]
            elif rg == "dn":
                title = T("Trend aşağı", "Trend down")
                lines = [T(f"Fiyat <b>{cur}{f.num(p, dec)}</b>; iki ortalamanın da altında.", f"Price <b>{cur}{f.num(p, dec)}</b>; below both averages."),
                         T(f"<b>{cur}{f.num(m50, dec)}</b> (MA50) ilk direnç; üstünde kapanış ilk toparlanma işareti.", f"<b>{cur}{f.num(m50, dec)}</b> (MA50) is first resistance; a close above is the first sign of repair."),
                         T(f"<b>{cur}{f.num(m200, dec)}</b> (MA200) geri alınmadan trend aşağı.", f"Until <b>{cur}{f.num(m200, dec)}</b> (MA200) is reclaimed, the trend is down.")]
            else:
                title = T("İki ortalamanın arasında", "Between the averages")
                hi, lo = max(m50, m200), min(m50, m200)
                lines = [T(f"Fiyat <b>{cur}{f.num(p, dec)}</b>; MA50 ile MA200 arasında.", f"Price <b>{cur}{f.num(p, dec)}</b>; between MA50 and MA200."),
                         T(f"<b>{cur}{f.num(hi, dec)}</b> üstünde kapanış trendi yukarı çevirir.", f"A close above <b>{cur}{f.num(hi, dec)}</b> turns the trend up."),
                         T(f"<b>{cur}{f.num(lo, dec)}</b> altında kapanış trendi aşağı çevirir.", f"A close below <b>{cur}{f.num(lo, dec)}</b> turns the trend down.")]
            p52 = pos52(a)
            if p52 <= .05 or p52 >= .95:
                lines.append(T("52 haftalık aralığın " + ("dibinde." if p52 <= .05 else "zirvesinde."),
                               "At the " + ("bottom" if p52 <= .05 else "top") + " of its 52-week range."))
            cards.append(f'<div class="panel"><span class="k">{self.n(k)}</span><h3>{title}</h3><ul>{"".join(f"<li>{x}</li>" for x in lines)}</ul></div>')
        if not cards:
            return ""
        return self.section(self.s["s10"], self.s["s10m"], f'<div class="scen">{"".join(cards)}</div>')

    def scorecard(self):
        A, f, T = self.A, self.f, self.T
        word = {"up": T("yukarı", "up"), "dn": T("aşağı", "down"), "mix": T("kararsız", "mixed")}
        was = {"up": "yukarıydı", "dn": "aşağıydı", "mix": "kararsızdı"}   # TR past tense, suffix follows the last sound
        rows = []
        for k, dec, cur in self.LEVEL_ASSETS:
            if k not in A or not A[k].get("ma200") or not (A[k].get("prev") or {}).get("ma200"):
                continue
            a, pv = A[k], A[k]["prev"]
            then = regime(pv["last"], pv["ma50"], pv["ma200"])
            now = regime(a["last"], a["ma50"], a["ma200"])
            held = then == now
            mark = '<b class="up">✓</b>' if held else '<b class="dn">✗</b>'
            # Factual either way: it compares last week's close with this week's,
            # and does not claim a previous issue said anything.
            why = (T(f"Geçen haftanın kapanışında trend {was[then]}; bu hafta da {word[now]}.",
                     f"At last week's close the trend was {word[then]}; it still is.") if held
                   else T(f"Geçen haftanın kapanışında trend {was[then]}; bu hafta {word[now]}.",
                          f"At last week's close the trend was {word[then]}; this week it is {word[now]}."))
            rows.append(f'<li>{mark}<div><b>{self.n(k)}</b><p>{why} <span class="mono mute">{cur}{f.num(pv["last"], dec)} → {cur}{f.num(a["last"], dec)}</span></p></div></li>')
        if not rows:
            return ""
        return self.section(self.s["s11"], self.s["s11m"], f'<ul class="karne">{"".join(rows)}</ul>')

    # §12
    def crypto(self):
        A, f, T = self.A, self.f, self.T
        parts = []
        if "btc" in A:
            b = A["btc"]
            parts.append(f'<span><b>Bitcoin</b><span class="mono">${f.num(b["last"], 0)} <span class="{dc(b["w"])}">{f.pct(b["w"], 1)} 1W</span> · '
                         f'<span class="{dc(b["ytd"])}">{f.pct(b["ytd"], 1)} YTD</span></span></span>')
        fg = self.d.get("fg")
        if fg and fg.get("px"):
            lab = fg.get("chg", "")
            if self.l == "tr":
                lab = {"Extreme Fear": "Aşırı korku", "Fear": "Korku", "Neutral": "Nötr", "Greed": "Açgözlülük",
                       "Extreme Greed": "Aşırı açgözlülük"}.get(lab, lab)
            parts.append(f'<span><b>{self.s["fg"]}</b><span class="mono">{esc(fg["px"])} · {esc(lab)}</span></span>')
        if not parts:
            return ""
        return self.section(self.s["s12"], self.s["s12m"], f'<div class="strip">{"".join(parts)}</div>')

    def render(self, web_url=None):
        s, f = self.s, self.f
        hd = self.headline()
        css = open(os.path.join(HERE, "style.css")).read()
        hero = ""
        if hd:
            sub = f'<span class="mono" style="color:rgba(236,234,227,.6)">{hd["sub"]}</span>' if hd["sub"] else ""
            hero = f'''<section class="hero">
  <span class="k">{s["hero_k"]}</span>
  <h1>{hd["h1"]} — <i>{hd["h2"]}</i></h1>
  <p class="lede">{self.lede()}</p>
  <div class="chart"><div class="lab"><span class="k">{hd["lab"]}</span><b>{hd["val"]}</b>{sub}</div>{spark(hd["series"], w=1000, h=150, layers=9)}</div>
</section>'''
        k5 = "".join(f'<div><span class="k">{a}</span><b class="{c}">{b}</b><span class="mono mute">{x}</span></div>' for a, b, x, c in self.key5())
        body = "".join([self.assets(), self.board(), self.drivers(), self.sectors(), self.chain(), self.asia(),
                        self.giants(), self.metals(), self.week_ahead(), self.levels(), self.scorecard(), self.crypto()])
        web = f'<a class="weblink mono" href="{web_url}">{s["web"]} →</a>' if web_url else ""
        alt = "en" if self.l == "tr" else "tr"
        return f'''<!doctype html>
<html lang="{self.l}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NO/CASHFLOW · {s["title"]} · {f.long_date(self.d["today"])}</title>
<meta name="description" content="{esc(self.lede())}">
<link rel="alternate" hreflang="{alt}" href="https://nocashflow.net/bulletins/weekly/latest.{alt}.html">
<link rel="icon" href="https://nocashflow.net/favicon.svg?v=4" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500&display=swap">
<style>{css}</style></head><body><div class="wrap">
<div class="top"><a class="wm" href="https://nocashflow.net/{'tr/' if self.l == 'tr' else ''}">NO<b>/</b>CASHFLOW</a><span class="eyebrow"><em>{s["eyebrow"]}</em> · {f.long_date(self.d["today"])}</span></div>
{hero}
<div class="key5">{k5}</div>
{body}
<footer><span class="wm">NO<b>/</b>CASHFLOW</span><p>{s["foot"]}</p>{web}</footer>
</div></body></html>'''

    def teaser(self):
        """What the email shows: the headline, the lede and the five key numbers."""
        hd = self.headline()
        return {"h1": hd["h1"] if hd else "", "h2": hd["h2"] if hd else "", "lede": self.lede(), "key5": self.key5()}


def render(data, lang, web_url=None):
    return Bulletin(data, lang).render(web_url)


def teaser(data, lang):
    return Bulletin(data, lang).teaser()
