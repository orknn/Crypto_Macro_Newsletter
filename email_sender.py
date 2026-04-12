"""
Email Sender — Send the daily bulletin via Resend API.
Reads credentials from environment variables / GitHub Secrets.
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
import base64
import re


SUBSCRIBERS = [
    "arzucesur00@gmail.com",
    "bicenhalil17@gmail.com",
    "mbalbay23@gmail.com",
    "Cuneyt_y@yahoo.com",
    "bicenorkun@gmail.com",
]


def send_newsletter_email(html_path="daily_bulletin.html", data=None):
    """
    Send the bulletin HTML to all subscribers via Resend API.
    Required env var: RESEND_API_KEY
    """

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("❌ RESEND_API_KEY env variable not set. Skipping email.")
        return False

    if not os.path.isfile(html_path):
        print(f"❌ HTML file not found: {html_path}")
        return False

    with open(html_path, "r", encoding="utf-8") as f:
        full_html = f.read()

    # Extract Market Overview
    match = re.search(r'<p class="summary-text">(.*?)</p>', full_html, re.DOTALL)
    market_overview = match.group(1) if match else "Please refer to the attached PDF for today's market overview and full data."

    # Build minimalist Email UI
    html_content = f"""
    <html>
    <body style="background-color: #0b0d10; color: #e8e4df; font-family: 'Inter', Helvetica, sans-serif; padding: 40px 20px; line-height: 1.6; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: #121418; padding: 30px; border-top: 3px solid #d4a853; border-radius: 6px;">
            
            <h2 style="color: #d4a853; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;">Market Overview</h2>
            
            <p style="font-size: 14px; color: #9aa0a6; line-height: 1.8; margin-bottom: 30px;">
                {market_overview}
            </p>
            
            <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; text-align: center;">
                <p style="font-size: 16px; font-weight: 600; color: #e8e4df; margin: 0; line-height: 1.5;">
                    📄 For comprehensive insights, detailed charts, and full financial market data, please review the attached PDF Bulletin.
                </p>
            </div>
            
            <div style="margin-top: 40px; font-size: 11px; color: #6b7280; text-align: center;">
                <p>© {datetime.now().year} nocashflow.net · Orkun Biçen</p>
            </div>
            
        </div>
    </body>
    </html>
    """

    today_str = datetime.now().strftime("%B %d, %Y")
    subject = f"Daily Financial Bulletin - {today_str}"

    print(f"\n📧 Sending bulletin to {len(SUBSCRIBERS)} subscribers via Resend...")

    success_count = 0
    fail_count = 0

    for recipient in SUBSCRIBERS:
        try:
            email_payload = {
                "from": "NoCashFlow Daily Bulletin <dailyfinancialbulletin@nocashflow.net>",
                "to": [recipient],
                "subject": subject,
                "html": html_content,
                "reply_to": "orkun@nocashflow.net",
            }
            
            # PDF ekle
            pdf_path = "daily_bulletin.pdf"
            if os.path.isfile(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    pdf_b64 = base64.b64encode(pdf_file.read()).decode("utf-8")
                email_payload["attachments"] = [
                    {
                        "filename": "daily_bulletin.pdf",
                        "content": pdf_b64
                    }
                ]

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

    print(f"\n📊 Email summary: {success_count} sent, {fail_count} failed")
    return fail_count == 0
