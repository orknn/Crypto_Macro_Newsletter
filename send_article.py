#!/usr/bin/env python3
"""
send_article.py — one-off "Special Edition" article blast to confirmed
subscribers, in the language each one chose for the bulletin.

Generic & reusable: point it at ANY published nocashflow.net article URL.
The script fetches the live page, discovers its EN/TR siblings via hreflang,
extracts the article prose, and re-renders it as an email that matches the
site's light "broadsheet" design (crimson accent, serif headlines, the same
table / data-point / blockquote styling). One input (a URL) → both languages.

Reuses the bulletin plumbing: subscriber fetch per language, Resend send loop,
mandatory token-scoped unsubscribe.

Usage:
  python3 send_article.py --url URL --preview                 # write out/*.html, no secrets, no send
  python3 send_article.py --url URL --count                   # subscriber counts (NCF_ADMIN_TOKEN)
  python3 send_article.py --url URL --test you@x.com --lang tr # one test email (RESEND_API_KEY)
  python3 send_article.py --url URL --send                    # real send (RESEND_API_KEY + NCF_ADMIN_TOKEN)
Options: --lang en|tr (default both) · --topic "CPI Flash" (flash label)

Required env for --send: RESEND_API_KEY, NCF_ADMIN_TOKEN
"""
import os
import re
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

from email_sender import fetch_confirmed_subscribers, UNSUBSCRIBE_URL, SUBSCRIBERS_API_URL

FROM_ADDR = "NoCashFlow <dailyfinancialbulletin@nocashflow.net>"
REPLY_TO = "orkun@nocashflow.net"
SITE = "https://nocashflow.net"

# ── light broadsheet palette (mirrors body.bs tokens in the site CSS) ──────────
PAPER = "#F8F8F4"
PAPER2 = "#F1F1EA"
INK = "#16181C"
INK2 = "#3C3F45"
MUTE = "#8A8577"
CRIMSON = "#B3122B"
BORDER = "#D8D7CE"
HAIR = "#E5E3DA"
SERIF = "Georgia,'Times New Roman',serif"

LABELS = {"en": "Special Edition", "tr": "Özel Sayı"}
SUBJ_PREFIX = {"en": "Flash", "tr": "Flaş"}
CTA = {"en": "Read the full analysis →", "tr": "Tam analizi oku →"}
UNSUB = {"en": "Unsubscribe", "tr": "Abonelikten çık"}

# ── inline styles for prose elements ──────────────────────────────────────────
P = f"font-size:16px; line-height:1.8; color:{INK}; margin:0 0 22px;"
H2 = f"font-family:{SERIF}; font-style:italic; font-weight:400; font-size:25px; color:{INK}; letter-spacing:-0.01em; margin:36px 0 14px;"
BQ = f"margin:26px 0; padding:6px 0 6px 20px; border-left:2px solid {CRIMSON}; font-family:{SERIF}; font-style:italic; font-size:19px; line-height:1.5; color:{INK};"
DP = f"border:1px solid {BORDER}; background:{PAPER2}; padding:16px 18px; margin:24px 0; font-family:monospace; font-size:14px; color:{INK};"
DPK = f"font-size:9px; letter-spacing:1.6px; text-transform:uppercase; color:{MUTE}; margin-bottom:6px;"
SB = f"border-left:2px solid {BORDER}; padding:12px 18px; margin:24px 0; font-size:13px; color:{MUTE};"
SBK = f"font-family:monospace; font-size:9px; letter-spacing:1.6px; text-transform:uppercase; display:block; margin-bottom:6px; color:{INK2};"
TBL = "width:100%; border-collapse:collapse; margin:26px 0;"
TH = f"font-family:monospace; font-size:10px; letter-spacing:1px; text-transform:uppercase; color:{MUTE}; font-weight:600; padding:0 12px 8px 0; border-bottom:1px solid {INK}; text-align:left;"
TD = f"font-family:monospace; font-size:13px; color:{INK2}; padding:10px 12px 10px 0; border-bottom:1px solid {HAIR};"
TDHIT = f"font-family:monospace; font-size:13px; color:{CRIMSON}; font-weight:700; padding:10px 12px 10px 0; border-bottom:1px solid {HAIR};"
FC = f"font-family:monospace; font-size:11px; color:{MUTE}; margin-top:8px; line-height:1.5;"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "NoCashFlow-Article-Mailer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def discover_urls(any_url):
    html = _get(any_url)
    en = re.search(r'hreflang="en" href="([^"]+)"', html)
    tr = re.search(r'hreflang="tr" href="([^"]+)"', html)
    if not (en and tr):
        raise SystemExit("❌ Could not find EN/TR hreflang links on the page — is this a nocashflow.net article URL?")
    return en.group(1), tr.group(1)


def _meta(html, prop):
    m = re.search(r'<meta property="%s" content="([^"]*)"' % re.escape(prop), html)
    return m.group(1) if m else ""


def extract_prose(html):
    # prose lives in <div class="prose article-prose" ...> ... </div> before the share row
    part = html.split('class="prose article-prose"', 1)[1]
    part = part.split(">", 1)[1]                       # skip rest of opening tag
    prose = part.split('<div class="share-row">', 1)[0]
    prose = prose.rstrip()
    if prose.endswith("</div>"):
        prose = prose[: prose.rfind("</div>")]
    return prose.strip()


def transform(prose):
    s = prose
    s = re.sub(r'<span class="gloss"[^>]*>(.*?)</span>', r"\1", s, flags=re.S)  # unwrap glossary tooltips
    for cls in ("em", "red", "accent"):
        s = s.replace(f'<span class="{cls}">', f'<span style="color:{CRIMSON};">')
    s = s.replace('<div class="data-point">', f'<div style="{DP}">')
    s = s.replace('<div class="k">', f'<div style="{DPK}">')
    s = s.replace('<div class="source-box">', f'<div style="{SB}">')
    s = s.replace('<span class="k">', f'<span style="{SBK}">')
    s = s.replace('<table class="a-table">', f'<table cellpadding="0" cellspacing="0" style="{TBL}">')
    s = s.replace('<td class="hit">', f'<td style="{TDHIT}">')
    s = s.replace("<td>", f'<td style="{TD}">')
    s = s.replace("<th>", f'<th style="{TH}">')
    s = s.replace("<h2>", f'<h2 style="{H2}">')
    s = s.replace("<blockquote>", f'<blockquote style="{BQ}">')
    s = s.replace("<p>", f'<p style="{P}">')
    s = s.replace('<figure class="article-figure">', '<figure style="margin:28px 0;">')
    s = re.sub(r"<img ", '<img style="max-width:100%;height:auto;display:block;margin:0 auto;" ', s)
    s = re.sub(r'(<img[^>]*\ssrc=")/', r"\1" + SITE + "/", s)
    s = s.replace("<figcaption>", f'<figcaption style="{FC}">')
    s = s.replace('<a href="/', f'<a style="color:{CRIMSON};text-decoration:underline;" href="{SITE}/')
    # drop cap on the first paragraph
    m = re.search(r'(<p style="[^"]*">)(\w)', s)
    if m:
        cap = (f'<span style="float:left;font-family:{SERIF};font-size:52px;line-height:0.82;'
               f'color:{CRIMSON};padding:4px 8px 0 0;">{m.group(2)}</span>')
        s = s[: m.start()] + m.group(1) + cap + s[m.end():]
    return s


def extract_article(url):
    html = _get(url)
    title = _meta(html, "og:title")
    dek = _meta(html, "og:description")
    dm = re.search(r'class="muted">([^<·]+)', html)
    date = dm.group(1).strip() if dm else datetime.now().strftime("%b %d, %Y")
    prose = transform(extract_prose(html))
    return {"url": url, "title": title, "dek": dek, "date": date, "prose": prose}


def build_email(lang, art, topic):
    label = LABELS[lang] + (f" · {topic}" if topic else "") + f" · {art['date']}"
    header = (
        f'<div style="font-family:monospace; font-size:11px; letter-spacing:2px; text-transform:uppercase; color:{CRIMSON}; margin-bottom:10px;">{label}</div>'
        f'<h1 style="font-family:{SERIF}; font-weight:400; font-size:30px; line-height:1.15; color:{INK}; margin:0 0 14px;">{art["title"]}</h1>'
        f'<p style="font-family:{SERIF}; font-style:italic; font-size:18px; line-height:1.5; color:{INK2}; margin:0 0 26px;">{art["dek"]}</p>'
        f'<hr style="border:none; border-top:1px solid {BORDER}; margin:0 0 30px;">'
    )
    cta = (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:34px 0 6px;"><tr><td align="center">'
        f'<a href="{art["url"]}" target="_blank" style="display:inline-block; background:{CRIMSON}; color:{PAPER}; '
        f'font-family:monospace; font-size:12px; letter-spacing:1px; text-transform:uppercase; font-weight:700; '
        f'text-decoration:none; padding:13px 30px;">{CTA[lang]}</a></td></tr></table>'
    )
    footer = (
        f'<div style="margin-top:36px; padding-top:18px; border-top:1px solid {HAIR}; font-family:monospace; font-size:11px; color:{MUTE}; text-align:center;">'
        f'<p style="margin:0;">© {datetime.now().year} nocashflow.net · Orkun Biçen</p>'
        f'<p style="margin:8px 0 0;"><a href="{{{{UNSUB_URL}}}}" style="color:{MUTE}; text-decoration:underline;">{UNSUB[lang]}</a></p></div>'
    )
    inner = header + art["prose"] + cta + footer
    return (
        f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>'
        f'<body style="background-color:{PAPER2}; margin:0; padding:32px 16px; '
        f'font-family:Helvetica,Arial,sans-serif;">'
        f'<div style="max-width:640px; margin:0 auto; background:{PAPER}; padding:36px 34px; '
        f'border-top:3px solid {CRIMSON};">' + inner + "</div></body></html>"
    )


def _subject(lang, art):
    return f"{SUBJ_PREFIX[lang]}: {art['title'].rstrip('.')}"


def _resend_send(api_key, from_addr, to, subject, html):
    payload = json.dumps({"from": from_addr, "to": [to], "subject": subject,
                          "html": html, "reply_to": REPLY_TO}).encode("utf-8")
    req = urllib.request.Request("https://api.resend.com/emails", data=payload,
                                 headers={"Authorization": f"Bearer {api_key}",
                                          "Content-Type": "application/json",
                                          "User-Agent": "NoCashFlow-Bulletin/1.0"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── modes ─────────────────────────────────────────────────────────────────────
def preview(arts, topic):
    os.makedirs("out", exist_ok=True)
    for lang, art in arts.items():
        html = build_email(lang, art, topic).replace("{{UNSUB_URL}}", f"{UNSUBSCRIBE_URL}?token=PREVIEW")
        path = f"out/article_email_{lang}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ {path}  ·  subject: {_subject(lang, art)}")
    print("\nNo email sent. Open the files above to review.")


def count(langs):
    tok = os.environ.get("NCF_ADMIN_TOKEN")
    if not tok:
        sys.exit("❌ NCF_ADMIN_TOKEN not set.")
    total = 0
    for lang in langs:
        try:
            n = len(fetch_confirmed_subscribers(lang, tok))
            print(f"  {lang.upper()}: {n} confirmed subscriber(s)")
            total += n
        except Exception as e:
            print(f"  ❌ {lang}: {e}")
    print(f"  TOTAL: {total}")


def test(arts, langs, to, topic):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        sys.exit("❌ RESEND_API_KEY not set.")
    lang = langs[0]
    art = arts[lang]
    html = build_email(lang, art, topic).replace("{{UNSUB_URL}}", f"{UNSUBSCRIBE_URL}?token=TEST")
    try:
        r = _resend_send(api_key, FROM_ADDR, to, "[TEST] " + _subject(lang, art), html)
        print(f"  ✅ Test ({lang.upper()}) sent → {to} (id: {r.get('id','?')})")
    except urllib.error.HTTPError as e:
        print(f"  ❌ {e.code} {e.read().decode('utf-8','replace')}")


def send(arts, langs, topic):
    api_key = os.environ.get("RESEND_API_KEY")
    tok = os.environ.get("NCF_ADMIN_TOKEN")
    if not api_key:
        sys.exit("❌ RESEND_API_KEY not set — refusing to send.")
    if not tok:
        sys.exit("❌ NCF_ADMIN_TOKEN not set — refusing to send.")
    g_ok = g_fail = 0
    for lang in langs:
        art = arts[lang]
        html_tmpl = build_email(lang, art, topic)
        subject = _subject(lang, art)
        print(f"\n  → Fetching confirmed {lang.upper()} subscribers...")
        try:
            recipients = fetch_confirmed_subscribers(lang, tok)
        except Exception as e:
            print(f"  ❌ Subscriber API error ({lang}): {e}")
            continue
        print(f"  → {len(recipients)} confirmed {lang.upper()} subscriber(s).")
        if not recipients:
            continue
        print(f"📧 Sending SPECIAL EDITION ({lang.upper()}) to {len(recipients)}...")
        ok = fail = 0
        for sub in recipients:
            rec = sub.get("email")
            token = sub.get("token", "")
            if not rec:
                continue
            html = html_tmpl.replace("{{UNSUB_URL}}", f"{UNSUBSCRIBE_URL}?token={token}")
            try:
                r = _resend_send(api_key, FROM_ADDR, rec, subject, html)
                print(f"  ✅ {rec} (id: {r.get('id','?')})")
                ok += 1
            except urllib.error.HTTPError as e:
                print(f"  ❌ {rec}: {e.code} {e.read().decode('utf-8','replace')}")
                fail += 1
            except Exception as e:
                print(f"  ❌ {rec}: {e}")
                fail += 1
        print(f"📊 {lang.upper()}: {ok} sent, {fail} failed")
        g_ok += ok
        g_fail += fail
    print(f"\n══ TOTAL: {g_ok} sent, {g_fail} failed ══")


if __name__ == "__main__":
    args = sys.argv[1:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default

    url = opt("--url")
    if not url:
        sys.exit("❌ --url is required (a published nocashflow.net article URL).")
    TOPIC = opt("--topic", "")
    lang_arg = opt("--lang")
    langs = [lang_arg] if lang_arg in ("en", "tr") else ["en", "tr"]

    en_url, tr_url = discover_urls(url)
    url_by_lang = {"en": en_url, "tr": tr_url}
    print(f"  discovered · EN {en_url}\n             · TR {tr_url}")
    arts = {lang: extract_article(url_by_lang[lang]) for lang in langs}

    if "--test" in args:
        print("=== TEST MODE ===")
        test(arts, langs, opt("--test"), TOPIC)
    elif "--count" in args:
        print("=== COUNT MODE (no send) ===")
        count(langs)
    elif "--send" in args:
        print("=== SEND MODE — emails real subscribers ===")
        send(arts, langs, TOPIC)
    else:
        print("=== PREVIEW MODE (no send) ===")
        preview(arts, TOPIC)
