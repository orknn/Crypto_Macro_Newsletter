"""
Email Sender — Send the daily newsletter via SMTP (Gmail).
Reads credentials from environment variables.
"""
import os
import re
import sys
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime


def _inline_images(html_content, base_dir="."):
    """
    Convert local <img src="file.png"> references to inline base64 data URIs
    so that images render inside the email without external links.
    """
    def replace_img(match):
        src = match.group(1)
        img_path = os.path.join(base_dir, src)
        if os.path.isfile(img_path):
            try:
                with open(img_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                ext = os.path.splitext(src)[1].lstrip(".").lower()
                mime = {"png": "image/png", "jpg": "image/jpeg",
                        "jpeg": "image/jpeg", "gif": "image/gif",
                        "svg": "image/svg+xml", "webp": "image/webp"}
                content_type = mime.get(ext, "image/png")
                return f'src="data:{content_type};base64,{data}"'
            except Exception:
                pass
        return match.group(0)

    return re.sub(r'src="([^"]+\.(png|jpg|jpeg|gif|svg|webp))"',
                  replace_img, html_content, flags=re.IGNORECASE)


def send_newsletter_email(html_path="daily_bulletin.html",
                          pdf_path="daily_bulletin.pdf"):
    """
    Send the newsletter HTML as an email.

    Required environment variables:
      EMAIL_FROM     — sender Gmail address
      EMAIL_PASSWORD — Gmail App Password (NOT your regular password)
      EMAIL_TO       — recipient email(s), comma-separated for multiple
    """
    email_from = os.environ.get("EMAIL_FROM")
    email_password = os.environ.get("EMAIL_PASSWORD")
    email_to = os.environ.get("EMAIL_TO")

    if not all([email_from, email_password, email_to]):
        print("❌ E-posta gönderimi için gerekli ortam değişkenleri eksik:")
        if not email_from:
            print("   - EMAIL_FROM ayarlanmamış")
        if not email_password:
            print("   - EMAIL_PASSWORD ayarlanmamış")
        if not email_to:
            print("   - EMAIL_TO ayarlanmamış")
        return False

    # ── Read HTML content ──
    if not os.path.isfile(html_path):
        print(f"❌ HTML dosyası bulunamadı: {html_path}")
        return False

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inline images for email compatibility
    base_dir = os.path.dirname(os.path.abspath(html_path))
    html_content = _inline_images(html_content, base_dir)

    # ── Build email ──
    today_str = datetime.now().strftime("%d %B %Y")
    subject = f"📊 Daily Financial Bulletin — {today_str}"

    recipients = [addr.strip() for addr in email_to.split(",")]

    msg = MIMEMultipart("mixed")
    msg["From"] = email_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # HTML body
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(html_part)

    # Attach PDF if available
    if pdf_path and os.path.isfile(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition", "attachment",
            filename=f"daily_bulletin_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        msg.attach(pdf_attachment)
        print(f"  📎 PDF ek olarak eklendi: {pdf_path}")

    # ── Send via Gmail SMTP ──
    try:
        print(f"\n📧 E-posta gönderiliyor → {', '.join(recipients)}")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, email_password)
            server.sendmail(email_from, recipients, msg.as_string())
        print("  ✅ E-posta başarıyla gönderildi!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  ❌ Gmail kimlik doğrulama hatası!")
        print("     → Gmail App Password kullandığından emin ol.")
        print("     → https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        print(f"  ❌ E-posta gönderme hatası: {e}")
        return False


if __name__ == "__main__":
    # Standalone test — requires env vars to be set
    success = send_newsletter_email()
    sys.exit(0 if success else 1)
