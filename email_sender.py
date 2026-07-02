"""
Email Sender — Send the daily/weekly bulletin via Resend API.

Recipients come ONLY from the site's confirmed-subscriber API (Cloudflare
Worker + D1). Subscriber emails are never stored in this repo (EU/GDPR).

Required env vars:
  RESEND_API_KEY   — Resend transactional key (sends the bulletin)
  NCF_ADMIN_TOKEN  — Bearer for GET /api/subscribers
Optional:
  WORKER_BASE         — Worker origin, defaults to the workers.dev host
  SUBSCRIBERS_API_URL — overrides the full subscribers endpoint URL
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
import base64
import re
from render.i18n import STR, format_bulletin_date

# nocashflow.net is DNS-only (unproxied) on Cloudflare, so /api/* does not route
# to the Worker — it must be reached on the workers.dev host instead.
WORKER_BASE = os.environ.get(
    "WORKER_BASE", "https://ncf-subscribe.bicenorkun.workers.dev"
)
SUBSCRIBERS_API_URL = os.environ.get(
    "SUBSCRIBERS_API_URL", f"{WORKER_BASE}/api/subscribers"
)
UNSUBSCRIBE_URL = f"{WORKER_BASE}/api/unsubscribe"

EMAIL_STR = {
    "market_overview": {
        "tr": "Piyasa Değerlendirmesi",
        "en": "Market Overview"
    },
    "pdf_notice": {
        "tr": "Ayrıntılı analizler ve tüm grafikler ekteki PDF bülteninde.",
        "en": "Detailed analysis and all charts are in the attached PDF bulletin."
    },
    "fallback_overview": {
        "tr": "Piyasa değerlendirmesi ve tüm veriler için lütfen ekteki PDF dosyasını inceleyin.",
        "en": "Please refer to the attached PDF for today's market overview and full data."
    },
    "unsubscribe": {
        "tr": "Bu bülteni almak istemiyor musun? Abonelikten çık",
        "en": "Don't want these emails? Unsubscribe"
    },
    "read_on_web": {
        "tr": "Bülteni Web'de Oku →",
        "en": "Read the Bulletin on the Web →"
    },
    "metric_btc": {"tr": "BTC", "en": "BTC"},
    "metric_etf": {"tr": "ETF NET AKIŞ", "en": "ETF NET FLOW"},
    "metric_etf_weekly": {"tr": "ETF HAFTALIK", "en": "ETF WEEKLY"},
    "metric_fng": {"tr": "KORKU & AÇG.", "en": "FEAR & GREED"},
    "metric_vix": {"tr": "VIX", "en": "VIX"},
    "metric_dxy": {"tr": "DXY", "en": "DXY"},
}

FNG_LABELS_TR = {
    'Neutral': 'Nötr',
    'Fear': 'Korku',
    'Extreme Fear': 'Aşırı Korku',
    'Greed': 'Açgözlülük',
    'Extreme Greed': 'Aşırı Açgözlülük',
}

GREEN = "#10b981"
RED = "#ef4444"
GOLD = "#d4a853"
DIM = "#9aa0a6"


def _build_archive_url(edition, lang):
    """Public web copy of this bulletin (same scheme as the PDF footer)."""
    now = datetime.now()
    if edition == 'weekly':
        iso_year, iso_week, _ = now.isocalendar()
        return f"https://nocashflow.net/bulletins/weekly/{iso_year}-W{iso_week:02d}.{lang}.html"
    return f"https://nocashflow.net/bulletins/daily/{now.strftime('%Y-%m-%d')}.{lang}.html"


def _metric_cell(label, value, sub, sub_color, value_color="#e8e4df"):
    """One inline-styled metric tile (email-client safe: tables only, no CSS vars)."""
    sub_html = ""
    if sub:
        sub_html = f'<div style="font-size: 10px; color: {sub_color}; margin-top: 3px; font-family: \'Courier New\', monospace;">{sub}</div>'
    return f'''
    <td align="center" style="padding: 10px 4px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px;">
        <div style="font-size: 9px; letter-spacing: 1px; color: {DIM}; text-transform: uppercase; margin-bottom: 4px;">{label}</div>
        <div style="font-size: 14px; font-weight: 700; color: {value_color}; font-family: 'Courier New', monospace;">{value}</div>
        {sub_html}
    </td>'''


def _build_metrics_strip(data, lang, edition):
    """Compact key-metrics row for the email body. Skips metrics that are missing."""
    if not data:
        return ""

    cells = []

    # BTC price + 24h change
    try:
        btc = next((c for c in data.get('crypto_prices', []) if c.get('Symbol') == 'BTC'), None)
        if btc and btc.get('Current Price USD'):
            chg = btc.get('24h %')
            sub, color = "", DIM
            if chg is not None:
                arrow = "▲" if chg >= 0 else "▼"
                color = GREEN if chg >= 0 else RED
                sub = f"{arrow} {chg:+.2f}%"
            cells.append(_metric_cell(EMAIL_STR["metric_btc"][lang], f"${btc['Current Price USD']:,.0f}", sub, color))
    except Exception:
        pass

    # ETF flow — weekly total for the weekly edition, latest daily otherwise
    try:
        if edition == 'weekly':
            hist = data.get('etf_weekly_history_data') or []
            total = hist[-1].get('Total_flow_m') if hist else None
            label = EMAIL_STR["metric_etf_weekly"][lang]
        else:
            total = (data.get('etf_flows') or {}).get('Total_flow_m')
            label = EMAIL_STR["metric_etf"][lang]
        if total is not None:
            color = GREEN if total >= 0 else RED
            cells.append(_metric_cell(label, f"{total:+,.0f}M$", "", color, value_color=color))
    except Exception:
        pass

    # Fear & Greed
    try:
        fng = data.get('fear_and_greed') or {}
        if fng.get('value') is not None:
            lbl = fng.get('classification', '')
            if lang == 'tr':
                lbl = FNG_LABELS_TR.get(lbl, lbl)
            val = fng['value']
            color = RED if val <= 25 else (GREEN if val >= 75 else GOLD)
            cells.append(_metric_cell(EMAIL_STR["metric_fng"][lang], str(val), lbl, color))
    except Exception:
        pass

    # VIX and DXY
    try:
        macro = data.get('macro_indicators') or {}
        for key, str_key in (('VIX', 'metric_vix'), ('DXY', 'metric_dxy')):
            val = macro.get(key)
            if val:
                chg = macro.get(f'{key}_chg')
                sub, color = "", DIM
                if chg is not None:
                    arrow = "▲" if chg >= 0 else "▼"
                    color = GREEN if chg >= 0 else RED
                    sub = f"{arrow} {chg:+.2f}%"
                fmt = f"{val:.1f}" if key == 'VIX' else f"{val:.2f}"
                cells.append(_metric_cell(EMAIL_STR[str_key][lang], fmt, sub, color))
    except Exception:
        pass

    if not cells:
        return ""

    spacer = '<td style="width: 6px;"></td>'
    return f'''
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px; border-collapse: separate;">
        <tr>
            {spacer.join(cells)}
        </tr>
    </table>
    '''


def fetch_confirmed_subscribers(lang, admin_token):
    """
    Fetch confirmed subscribers for `lang` from the site API.
    Returns list of dicts: [{'email': '...', 'token': '...'}, ...]
    Raises on auth/transport failure so the caller can refuse to send blind.
    """
    url = f"{SUBSCRIBERS_API_URL}?lang={lang}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {admin_token}",
            "User-Agent": "NoCashFlow-Bulletin/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    return res.get("subscribers", [])


def build_email_html(full_html, lang='tr', edition='daily', data=None):
    """
    Build the email body: metrics strip + market overview + web/PDF CTAs.
    {{UNSUB_URL}} is replaced per-recipient by the caller — every send carries
    a working, token-scoped unsubscribe link (mandatory).
    """
    # Extract Market Overview (summary-text)
    match = re.search(r'<p class="summary-text">(.*?)</p>', full_html, re.DOTALL)
    market_overview = match.group(1).strip() if match else EMAIL_STR["fallback_overview"][lang]

    metrics_strip = _build_metrics_strip(data, lang, edition)
    archive_url = _build_archive_url(edition, lang)

    return f"""
    <html>
    <body style="background-color: #0b0d10; color: #e8e4df; font-family: 'Inter', Helvetica, sans-serif; padding: 40px 20px; line-height: 1.6; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: #121418; padding: 30px; border-top: 3px solid #d4a853; border-radius: 6px;">

            {metrics_strip}

            <h2 style="color: #d4a853; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;">
                {EMAIL_STR["market_overview"][lang]}
            </h2>

            <p style="font-size: 14px; color: #9aa0a6; line-height: 1.8; margin-bottom: 30px;">
                {market_overview}
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px;">
                <tr>
                    <td align="center">
                        <a href="{archive_url}" target="_blank"
                           style="display: inline-block; background: #d4a853; color: #121418; font-size: 14px; font-weight: 700; text-decoration: none; padding: 12px 32px; border-radius: 4px;">
                            {EMAIL_STR["read_on_web"][lang]}
                        </a>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-top: 14px;">
                        <p style="font-size: 12px; color: #6b7280; margin: 0;">
                            📄 {EMAIL_STR["pdf_notice"][lang]}
                        </p>
                    </td>
                </tr>
            </table>

            <div style="margin-top: 40px; font-size: 11px; color: #6b7280; text-align: center;">
                <p>© {datetime.now().year} nocashflow.net · Orkun Biçen</p>
                <p style="margin-top: 8px;">
                    <a href="{{{{UNSUB_URL}}}}" style="color: #6b7280; text-decoration: underline;">{EMAIL_STR["unsubscribe"][lang]}</a>
                </p>
            </div>

        </div>
    </body>
    </html>
    """


def send_newsletter_email(html_path="daily_bulletin.html", pdf_path="daily_bulletin.pdf", lang='tr', edition='daily', data=None):
    """
    Send the bulletin HTML to confirmed subscribers via Resend API.
    Required env: RESEND_API_KEY, NCF_ADMIN_TOKEN
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("❌ RESEND_API_KEY env variable not set. Skipping email.")
        return False

    admin_token = os.environ.get("NCF_ADMIN_TOKEN")
    if not admin_token:
        print("❌ NCF_ADMIN_TOKEN not set — cannot fetch subscriber list. Skipping email.")
        return False

    if not os.path.isfile(html_path):
        print(f"❌ HTML file not found: {html_path}")
        return False

    with open(html_path, "r", encoding="utf-8") as f:
        full_html = f.read()

    html_content = build_email_html(full_html, lang=lang, edition=edition, data=data)

    formatted_date = format_bulletin_date(datetime.now(), lang)
    subject_tmpl = STR[f"email_subject_{edition}"][lang]
    subject = subject_tmpl.format(date=formatted_date)

    # Recipients: confirmed subscribers for this language, from the site API only.
    print(f"  → Fetching confirmed {lang.upper()} subscribers from {SUBSCRIBERS_API_URL}...")
    try:
        recipients = fetch_confirmed_subscribers(lang, admin_token)
    except urllib.error.HTTPError as e:
        print(f"  ❌ Subscriber API error: {e.code} {e.read().decode('utf-8', 'replace')}")
        return False
    except Exception as e:
        print(f"  ❌ Could not reach subscriber API: {e}")
        return False

    print(f"  → Found {len(recipients)} confirmed subscriber(s).")
    if not recipients:
        print("  ⚠️ No confirmed recipients to send to.")
        return True

    print(f"\n📧 Sending {edition.upper()} ({lang.upper()}) bulletin to {len(recipients)} subscribers via Resend...")

    # PDF attachment (same for everyone) — read once.
    attachments = None
    if os.path.isfile(pdf_path):
        with open(pdf_path, "rb") as pdf_file:
            pdf_b64 = base64.b64encode(pdf_file.read()).decode("utf-8")
        attachments = [{"filename": os.path.basename(pdf_path), "content": pdf_b64}]

    from_addr = (
        "NoCashFlow Daily Bulletin <dailyfinancialbulletin@nocashflow.net>"
        if edition == 'daily'
        else "NoCashFlow Weekly Deep Dive <dailyfinancialbulletin@nocashflow.net>"
    )

    success_count = 0
    fail_count = 0

    for sub in recipients:
        recipient = sub.get("email")
        token = sub.get("token", "")
        if not recipient:
            continue

        # Mandatory per-recipient unsubscribe link (token-scoped).
        unsub_url = f"{UNSUBSCRIBE_URL}?token={token}"
        personalized_html = html_content.replace("{{UNSUB_URL}}", unsub_url)

        try:
            email_payload = {
                "from": from_addr,
                "to": [recipient],
                "subject": subject,
                "html": personalized_html,
                "reply_to": "orkun@nocashflow.net",
                "headers": {"List-Unsubscribe": f"<{unsub_url}>"},
            }
            if attachments:
                email_payload["attachments"] = attachments

            payload = json.dumps(email_payload).encode("utf-8")

            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "NoCashFlow-Bulletin/1.0",
                },
                method="POST"
            )

            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                print(f"  ✅ Sent → {recipient} (id: {result.get('id', '?')})")
                success_count += 1

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"  ❌ Failed → {recipient}: {e.code} {body}")
            fail_count += 1
        except Exception as e:
            print(f"  ❌ Error → {recipient}: {e}")
            fail_count += 1

    print(f"📊 Email summary ({lang.upper()}): {success_count} sent, {fail_count} failed")
    return fail_count == 0
