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
                          pdf_path="daily_bulletin.pdf",
                          data=None):
    """
    Send the newsletter HTML as an email.

    Required environment variables:
      EMAIL_FROM     — sender Gmail address
      EMAIL_PASSWORD — Gmail App Password (NOT your regular password)
      EMAIL_TO       — recipient email(s), comma-separated for multiple
    """

    # ── Read or Build HTML content ──
    # ── Read or Build HTML content ──
    if data:
        # Build minimal HTML containing only Summary and News
        macro = data.get('macro_indicators', {})
        crypto_ov = data.get('crypto_market_overview', {})
        fng = data.get('fear_and_greed', {})
        
        summary_text = (
            f"<strong>Makroekonomik göstergeler</strong>e bakıldığında, <strong>VIX</strong> endeksi "
            f"<strong>{macro.get('VIX', 0):.1f}</strong> seviyesinde, "
            f"<strong>DXY</strong> (Dolar Endeksi) {macro.get('DXY', 0):.2f} noktasında işlem görmektedir. "
            f"<strong>ABD 10 Yıllık Tahvil Getirisi</strong> %{macro.get('US 10-Year Treasury Yield', 0):.2f} seviyesindedir. "
            f"Kripto piyasalarında <strong>Crypto Fear &amp; Greed Index</strong> "
            f"<strong>{fng.get('value', 0)}</strong> ({fng.get('classification', 'N/A')}) olarak kaydedildi. "
            f"Toplam kripto <strong>market cap</strong> ${crypto_ov.get('total_market_cap', 0)/1e12:.2f} Trilyon, "
            f"<strong>BTC Dominance</strong> %{crypto_ov.get('btc_dominance', 0):.1f} seviyesindedir."
        )

        for ev in data.get('economic_calendar', []):
            actual = ev.get('actual', '—')
            if actual != '—':
                if 'CPI' in ev.get('event', '') or 'TÜFE' in ev.get('event', '') or 'PCE' in ev.get('event', ''):
                    summary_text += f" Öte yandan, piyasaların merakla beklediği <strong>{ev.get('event', '')}</strong> verisi <strong>{actual}</strong> seviyesinde gerçekleşti."
                elif 'Non-Farm' in ev.get('event', '') or 'Tarım Dışı' in ev.get('event', ''):
                    summary_text += f" Ayrıca <strong>ABD Tarım Dışı İstihdam</strong> verisi son olarak <strong>{actual}</strong> olarak açıklandı."

        news_list = data.get('macro_news', {}).get('news', [])
        news_html = "".join([f"<li style='margin-bottom:12px; font-size:14px; color:#334155;'>{item.get('title') if isinstance(item, dict) else item}</li>" for item in news_list])

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
    <div style="background-color: #1e293b; padding: 24px; text-align: center;">
      <h2 style="color: #ffffff; margin: 0; font-size: 22px;">📊 Daily Financial Bulletin</h2>
      <p style="color: #94a3b8; margin: 8px 0 0; font-size: 14px;">{datetime.now().strftime('%d %B %Y')}</p>
    </div>
    
    <div style="padding: 32px 24px;">
      <h3 style="color: #0f172a; font-size: 18px; margin-top: 0; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">Genel Değerlendirme</h3>
      <div style="background-color: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 20px; margin-bottom: 32px;">
        <p style="margin: 0; color: #422006; font-size: 15px; line-height: 1.6;">{summary_text}</p>
      </div>
      
      <h3 style="color: #0f172a; font-size: 18px; margin-top: 0; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">🌍 Öne Çıkan Haberler</h3>
      <ul style="padding-left: 20px; margin-bottom: 32px; line-height: 1.5;">
        {news_html}
      </ul>
      
      <div style="text-align: center; margin-top: 40px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
        <p style="font-size: 14px; color: #64748b; font-style: italic; margin: 0;">
          📌 Detaylı grafikler, takvim ve tüm veriler için e-postanın ekindeki <strong>PDF dosyasını</strong> inceleyebilirsiniz.
        </p>
      </div>
    </div>
  </div>
</body>
</html>
"""
    else:
        if not os.path.isfile(html_path):
            print(f"❌ HTML dosyası bulunamadı: {html_path}")
            return False

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Inline images for email compatibility
        base_dir = os.path.dirname(os.path.abspath(html_path))
        html_content = _inline_images(html_content, base_dir)

    # ── Preview feature ──
    if os.environ.get("SAVE_EMAIL_PREVIEW") == "true":
        with open("email_preview.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  📝 Email önizlemesi kaydedildi: {os.path.abspath('email_preview.html')}")

    # ── Email Credentials Check ──
    email_from = os.environ.get("EMAIL_FROM")
    email_password = os.environ.get("EMAIL_PASSWORD")
    email_to = os.environ.get("EMAIL_TO")

    if not all([email_from, email_password, email_to]):
        print("❌ E-posta gönderimi için gerekli ortam değişkenleri eksik. (Gönderim atlandı)")
        return False

    # ── Build email ──
    today_str = datetime.now().strftime("%d %B %Y")
    subject = f"📊 Daily Financial Bulletin — {today_str}"

    recipients = [addr.strip() for addr in email_to.split(",")]

    msg = MIMEMultipart("mixed")
    msg["From"] = email_from
    msg["To"] = email_from  # Gönderici kendi adresini görür
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
