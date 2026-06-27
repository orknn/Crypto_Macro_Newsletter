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
        "tr": "📄 Ayrıntılı analizler, grafikler ve tüm finansal veriler için lütfen ekteki PDF bültenini inceleyin.",
        "en": "📄 For comprehensive insights, detailed charts, and full financial market data, please review the attached PDF Bulletin."
    },
    "fallback_overview": {
        "tr": "Piyasa değerlendirmesi ve tüm veriler için lütfen ekteki PDF dosyasını inceleyin.",
        "en": "Please refer to the attached PDF for today's market overview and full data."
    },
    "unsubscribe": {
        "tr": "Bu bülteni almak istemiyor musun? Abonelikten çık",
        "en": "Don't want these emails? Unsubscribe"
    },
}


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

    # Extract Market Overview (summary-text)
    match = re.search(r'<p class="summary-text">(.*?)</p>', full_html, re.DOTALL)
    market_overview = match.group(1).strip() if match else EMAIL_STR["fallback_overview"][lang]

    # Build minimalist Email UI. {{UNSUB_URL}} is replaced per-recipient below —
    # every send carries a working, token-scoped unsubscribe link (mandatory).
    html_content = f"""
    <html>
    <body style="background-color: #0b0d10; color: #e8e4df; font-family: 'Inter', Helvetica, sans-serif; padding: 40px 20px; line-height: 1.6; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: #121418; padding: 30px; border-top: 3px solid #d4a853; border-radius: 6px;">

            <h2 style="color: #d4a853; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;">
                {EMAIL_STR["market_overview"][lang]}
            </h2>

            <p style="font-size: 14px; color: #9aa0a6; line-height: 1.8; margin-bottom: 30px;">
                {market_overview}
            </p>

            <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; text-align: center;">
                <p style="font-size: 16px; font-weight: 600; color: #e8e4df; margin: 0; line-height: 1.5;">
                    {EMAIL_STR["pdf_notice"][lang]}
                </p>
            </div>

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
