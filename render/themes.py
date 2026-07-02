# render/themes.py
"""
Bülten tema sistemi.

Tek bir render edilmiş HTML'i 3 görsel temaya "yeniden giydirir":
  - premium   : rafine koyu terminal (varsayılan, e-posta uyumlu)
  - editorial : açık krem gazete tasarımı (e-posta uyumlu)
  - glass     : koyu + gradyan + cam paneller (web/PDF için ideal;
                e-postada blur düşer, kartlar yine de durur)

Kullanım:
    from render.themes import apply_theme
    html = apply_theme(html, theme="premium")

Tema, html_wrapper içinden uygulanır; render fonksiyonları sadece
`theme` parametresini iletir. Renkler/fontlar büyük oranda CSS
değişkenlerinden geldiği için palet değişimi tüm bölümlere yayılır;
SVG grafiklerdeki sabit-kodlu hex'ler ise color-map ile eşlenir.
"""
import os
import re

_FONT_RE = re.compile(r'<link href="https://fonts\.googleapis[^>]*>')

# ─────────────────────────────────────────── PREMIUM (koyu, rafine, Brand Gold)
# Palet 2026-07-03'te siteyle hizalandı: nocashflow.net'in altını (#d4a853) tek
# vurucu renk; maviler sakin çeliğe, zemin site siyahına (#0b0d10) çekildi.
_PREMIUM = dict(
    font='<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">',
    cmap={
        "#ef4444": "#f0556b", "#10b981": "#22c79a", "#f59e0b": "#d4a853", "#3b82f6": "#9aabc9",
        "#94a3b8": "#9aa0a6", "#fbbf24": "#d4a853", "#fb923c": "#c89448", "#f87171": "#f0728a",
        "#f0f4f9": "#f2f6fb",
        "#4ade80": "#4be3b0", "#26344d": "#2a2d36", "#22c55e": "#22c79a",
        "#1c2436": "#1d2027", "#121824": "#14161b", "#0b0f17": "#0b0d10",
    },
    css="""
:root{--bg:#0b0d10;--bg2:#14161b;--bg3:#1d2027;--border:#2a2d36;--text:#f2f6fb;--dim:#9aa0a6;--gold:#d4a853;--gold2:#c89448;--green:#22c79a;--red:#f0556b;--accent:#9aabc9;}
body{background-color:#0b0d10;background:radial-gradient(1100px 560px at 50% -240px,#1a1c22 0%,#0b0d10 55%) !important;}
.container{max-width:700px;padding:36px 22px;}
.container > table:first-of-type{border-bottom:1px solid var(--border);}
h1{font-size:34px !important;letter-spacing:-1px !important;}
.kpi-card,[style*="border-radius:6px"]{border-radius:14px !important;}
.kpi-card{overflow:hidden;}
.kpi-card::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--gold),transparent);}
.section-title{letter-spacing:2.5px;}
.section-line{background:linear-gradient(90deg,var(--border),transparent);}
.summary-card{border-radius:0 14px 14px 0 !important;}
.ti{border-radius:10px;}
""")

# ──────────────────────────────────────────────── EDITORIAL (açık, gazete)
_EDITORIAL = dict(
    font='<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;0,800;0,900;1,600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">',
    cmap={
        "#ffffff": "#1a1714",
        "#ef4444": "#c0392b", "#10b981": "#1f6b4a", "#f59e0b": "#b5311b", "#3b82f6": "#b5311b",
        "#94a3b8": "#6f6557", "#fbbf24": "#b5311b", "#fb923c": "#b5311b", "#f87171": "#c0392b",
        "#f0f4f9": "#1a1714", "#4ade80": "#1f6b4a", "#26344d": "#d8cdb8", "#22c55e": "#1f6b4a",
        "#1c2436": "#efe7d6", "#121824": "#fbf7ee", "#0b0f17": "#f7f1e6",
        "rgba(255,255,255,": "rgba(0,0,0,",
    },
    css="""
:root{--bg:#f7f1e6;--bg2:#fbf7ee;--bg3:#efe7d6;--border:#d8cdb8;--text:#1a1714;--dim:#6f6557;--gold:#b5311b;--gold2:#b5311b;--green:#1f6b4a;--red:#c0392b;--accent:#b5311b;--sans:"Source Serif 4",Georgia,serif;--serif:"Playfair Display",Georgia,serif;--mono:"IBM Plex Mono",ui-monospace,monospace;}
body{background:#f7f1e6 !important;color:#1a1714;}
.container{max-width:720px;padding:42px 32px;}
.container > table:first-of-type{border-bottom:3px double var(--text) !important;padding-bottom:20px !important;}
.container > table:first-of-type td[align="right"]{white-space:nowrap;}
h1{font-family:var(--serif) !important;font-size:42px !important;font-weight:900 !important;border-left:none !important;padding-left:0 !important;letter-spacing:-1px !important;}
.section-divider{border-bottom:2px solid var(--text);padding-bottom:7px;margin:36px 0 16px;}
.section-line{display:none !important;}
.section-title{font-family:var(--mono);font-size:11px;letter-spacing:2.5px;}
.kpi-card,[style*="border-radius:6px"]{border-radius:3px !important;box-shadow:none !important;}
.kpi-value,.ti-val{font-family:var(--mono);}
table.data-table td{border-bottom:1px solid var(--border) !important;}
.summary-card{border-radius:0 3px 3px 0 !important;}
.ti{border-radius:0;}
""")

# ──────────────────────────────────────────────── GLASS (koyu, gradyan + blur)
_GLASS = dict(
    font='<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">',
    cmap={
        "#ef4444": "#ff5d7a", "#10b981": "#3ee5a7", "#f59e0b": "#5b8cff", "#3b82f6": "#5b8cff",
        "#94a3b8": "#8b93b5", "#fbbf24": "#b06bff", "#fb923c": "#b06bff", "#f87171": "#ff5d7a",
        "#f0f4f9": "#eef1fa", "#4ade80": "#3ee5a7", "#26344d": "#2a3550", "#22c55e": "#3ee5a7",
        "#1c2436": "#141b2e", "#121824": "#0d1322", "#0b0f17": "#070912",
    },
    css="""
:root{--bg:#070912;--bg2:rgba(255,255,255,0.05);--bg3:rgba(255,255,255,0.09);--border:rgba(255,255,255,0.12);--text:#eef1fa;--dim:#8b93b5;--gold:#5b8cff;--gold2:#b06bff;--green:#3ee5a7;--red:#ff5d7a;--accent:#5b8cff;}
body{background:#070912 !important;}
body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(620px 440px at 10% 4%,rgba(91,140,255,.30),transparent 60%),radial-gradient(640px 440px at 90% 18%,rgba(176,107,255,.26),transparent 60%),radial-gradient(760px 560px at 50% 114%,rgba(62,229,167,.13),transparent 60%);}
.container{position:relative;z-index:1;max-width:700px;padding:34px 22px;}
h1{font-family:"Space Grotesk",sans-serif !important;font-weight:700 !important;border-left:none !important;padding-left:0 !important;letter-spacing:-.5px !important;}
.section-title{font-family:"Space Grotesk",sans-serif;letter-spacing:1.5px;}
.section-line{background:linear-gradient(90deg,var(--accent),transparent);}
.kpi-card,.ti,.sparkline-wrap,.summary-card,[style*="border-radius:6px"]{border-radius:18px !important;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);box-shadow:0 8px 40px rgba(0,0,0,.40);}
[style*="background:var(--bg2)"]{-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-radius:18px;}
.summary-card{border-radius:0 18px 18px 0 !important;}
""")

THEMES = {
    "premium": _PREMIUM,
    "editorial": _EDITORIAL,
    "glass": _GLASS,
}

DEFAULT_THEME = "premium"


def resolve_theme(theme=None):
    """Geçerli tema adını döndürür; geçersiz/boşsa env veya varsayılana düşer."""
    name = (theme or os.environ.get("BULLETIN_THEME") or DEFAULT_THEME).lower().strip()
    return name if name in THEMES else DEFAULT_THEME


def apply_theme(html, theme=None):
    """Render edilmiş tam HTML'i seçili temaya göre yeniden giydirir."""
    name = resolve_theme(theme)
    t = THEMES[name]
    html = _FONT_RE.sub(t["font"], html, count=1)
    for old, new in t["cmap"].items():
        html = html.replace(old, new)
    html = html.replace("</style>", "\n/* ===== THEME: %s ===== */\n%s\n</style>" % (name, t["css"]), 1)
    return html
