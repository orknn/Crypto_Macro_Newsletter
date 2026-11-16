"""Weekly bulletin v2 — the email: headline, lede, five numbers, a button.

Inline styles and tables only (email clients ignore <style> and CSS vars).
Colours follow nocashflow.net's Liquid theme. {{UNSUB_URL}} is filled per
recipient by email_sender.send_to_subscribers.
"""
from datetime import date

from weekly_v2.render import F

BONE, BONE2, INK, DIM, MUTE, HOT = "#ECEAE3", "#E1DED5", "#0B0C0F", "#45423D", "#5F5D58", "#FF4B26"
UP, DN = "#14713F", "#AD2B11"
SANS = "Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
MONO = "'Courier New',monospace"

STR = {
    "tr": {"k": "Haftalık bülten", "btn": "Bülteni oku →", "pdf": "Tüm grafikler ve tablolar ekteki PDF'te.",
           "unsub": "Bu maili almak istemiyor musun? Abonelikten çık", "foot": "Bilgi amaçlıdır; yatırım tavsiyesi değildir.",
           "subject": "Haftalık bülten · {h1}"},
    "en": {"k": "Weekly bulletin", "btn": "Read the bulletin →", "pdf": "Every chart and table is in the attached PDF.",
           "unsub": "Don't want these emails? Unsubscribe", "foot": "For information only; not investment advice.",
           "subject": "Weekly bulletin · {h1}"},
}


def subject(teaser, lang):
    return STR[lang]["subject"].format(h1=teaser["h1"])


def build(teaser, lang, web_url, when):
    s = STR[lang]
    cells = []
    for label, value, sub, cls in teaser["key5"]:
        col = UP if cls == "up" else DN if cls == "dn" else INK
        cells.append(
            f'<td align="left" valign="top" style="padding:12px 10px;background:{BONE2};border-radius:12px;">'
            f'<div style="font-family:{MONO};font-size:9px;letter-spacing:1.4px;text-transform:uppercase;color:{MUTE};">{label}</div>'
            f'<div style="font-family:{SANS};font-size:17px;font-weight:700;color:{col};margin-top:6px;">{value}</div>'
            f'<div style="font-family:{MONO};font-size:10px;color:{MUTE};margin-top:2px;">{sub}</div></td>')
    # two rows so it still fits a phone: 3 + 2
    gap = '<td style="width:6px;"></td>'
    row1 = gap.join(cells[:3])
    row2 = gap.join(cells[3:])
    strip = (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;margin:22px 0 6px;"><tr>{row1}</tr></table>'
             + (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;margin:6px 0 0;"><tr>{row2}</tr></table>' if row2 else ""))
    d = date.fromisoformat(when)
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:28px 14px;background:{BONE2};font-family:{SANS};">
<div style="max-width:620px;margin:0 auto;background:{BONE};border-radius:22px;padding:30px 28px;">
  <div style="font-family:{SANS};font-weight:800;font-size:18px;letter-spacing:-0.5px;color:{INK};">NO<span style="color:{HOT};">/</span>CASHFLOW</div>
  <div style="font-family:{MONO};font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:{HOT};margin:22px 0 10px;">{s["k"]} · {F(lang).long_date(when)}</div>
  <h1 style="font-family:{SANS};font-weight:600;font-size:28px;line-height:1.12;letter-spacing:-0.6px;color:{INK};margin:0 0 4px;">{teaser["h1"]}</h1>
  <div style="font-family:{SERIF};font-style:italic;font-size:26px;line-height:1.15;color:{INK};margin:0 0 16px;">{teaser["h2"]}</div>
  <p style="font-size:15px;line-height:1.6;color:{DIM};margin:0;">{teaser["lede"]}</p>
  {strip}
  <table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0 8px;"><tr><td align="center">
    <a href="{web_url}" target="_blank" style="display:inline-block;background:{INK};color:{BONE};font-family:{MONO};font-size:12px;letter-spacing:1px;text-transform:uppercase;font-weight:700;text-decoration:none;padding:14px 30px;border-radius:999px;">{s["btn"]}</a>
  </td></tr><tr><td align="center" style="padding-top:12px;font-size:12px;color:{MUTE};">{s["pdf"]}</td></tr></table>
  <div style="margin-top:30px;padding-top:16px;border-top:1px solid rgba(11,12,15,.12);font-family:{MONO};font-size:11px;color:{MUTE};text-align:center;line-height:1.7;">
    {s["foot"]}<br>© {d.year} nocashflow.net<br>
    <a href="{{{{UNSUB_URL}}}}" style="color:{MUTE};text-decoration:underline;">{s["unsub"]}</a>
  </div>
</div></body></html>'''
