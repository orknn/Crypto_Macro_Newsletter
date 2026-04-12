"""
Email Sender — Send the daily bulletin via Resend API.
Reads credentials from environment variables / GitHub Secrets.
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime


SUBSCRIBERS = [
    # "arzucesur00@gmail.com",
    # "bicenhalil17@gmail.com",
    # "mbalbay23@gmail.com",
    # "Cuneyt_y@yahoo.com",
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
        html_content = f.read()

    today_str = datetime.now().strftime("%B %d, %Y")
    subject = f"Daily Financial Bulletin - {today_str}"

    print(f"\n📧 Sending bulletin to {len(SUBSCRIBERS)} subscribers via Resend...")

    success_count = 0
    fail_count = 0

    for recipient in SUBSCRIBERS:
        try:
            payload = json.dumps({
                "from": "NoCashFlow Daily Bulletin <dailyfinancialbulletin@nocashflow.net>",
                "to": [recipient],
                "subject": subject,
                "html": html_content,
                "reply_to": "orkun@nocashflow.net",
            }).encode("utf-8")

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
