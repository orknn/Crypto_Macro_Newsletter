"""
AI Report Generator — Creates a separate private HTML report
with numbered proposals from the AI agents.
"""
import os
from datetime import datetime


def generate_ai_report(data, output_filename="ai_reports.html"):
    """
    Generate a separate HTML file with AI agent reports.
    This file is for the newsletter owner only, not sent to subscribers.
    """
    ai_summary = data.get('ai_summary')
    news_commentaries = data.get('news_commentaries')
    content_suggestions = data.get('content_suggestions')

    if not ai_summary:
        print("  ℹ️  AI raporu yok, ai_reports.html atlanıyor.")
        return None

    now = datetime.now()

    # Build editor section from AI summary and commentaries
    content_section = ''
    if ai_summary:
        content_html = f'<h3 style="color:#e8c547; margin:20px 0 10px; font-size:16px;">📝 Genel Değerlendirme (AI)</h3>'
        content_html += f'<p style="margin:6px 0; font-size:14px; color:#a8bcd4; line-height:1.7;">{ai_summary}</p>'
        if news_commentaries:
            content_html += f'<h3 style="color:#e8c547; margin:20px 0 10px; font-size:16px;">📰 Haber Yorumları (AI)</h3>'
            for nc in news_commentaries:
                content_html += f'<p style="margin:6px 0; font-size:13px; line-height:1.7;"><strong style="color:#f0ead8;">{nc.get("headline", "")}</strong><br><span style="color:#a8bcd4; font-style:italic;">→ {nc.get("commentary", "")}</span></p>'
        if content_suggestions:
            content_html += f'<h3 style="color:#e8c547; margin:20px 0 10px; font-size:16px;">💡 İçerik Önerileri</h3>'
            for i, cs in enumerate(content_suggestions, 1):
                cs_type = cs.get('type', 'ekle')
                badge_color = '#10B981' if cs_type == 'ekle' else '#EF4444'
                badge_text = '➕ EKLE' if cs_type == 'ekle' else '➖ ÇIKAR'
                content_html += f'<div style="margin:10px 0; padding:10px 14px; background:rgba(255,255,255,0.03); border-left:3px solid {badge_color}; border-radius:0 6px 6px 0;">'
                content_html += f'<span style="background:{badge_color}; color:white; font-size:9px; padding:2px 8px; border-radius:8px; font-weight:700; letter-spacing:0.5px;">{badge_text}</span> '
                content_html += f'<strong style="color:#f0ead8; font-size:13px;">{cs.get("title", "")}</strong>'
                content_html += f'<p style="margin:6px 0 0; font-size:12px; color:#a8bcd4; line-height:1.5;">{cs.get("reason", "")}</p></div>'
        content_section = f'''
    <div style="background:#1f3350; border-radius:10px; padding:24px; margin-bottom:24px; border:1px solid #2a4a6e;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
        <span style="font-size:24px;">🤖</span>
        <h2 style="margin:0; color:#f0ead8; font-size:18px;">İçerik Editörü Çıktısı</h2>
        <span style="background:#10B981; color:white; font-size:10px; padding:2px 8px; border-radius:10px; font-weight:600;">AI ACTIVE</span>
      </div>
      <div style="border-left:3px solid #e8c547; padding-left:16px;">
        {content_html}
      </div>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>AI Agent Raporları — {now.strftime('%d %B %Y')}</title>
</head>
<body style="margin:0; padding:20px; background:#0f1b2d; font-family:'Inter',sans-serif;">
  <div style="max-width:700px; margin:0 auto;">

    <div style="text-align:center; padding:24px; margin-bottom:24px;">
      <h1 style="color:#e8c547; font-size:22px; margin:0;">🤖 AI Agent Raporları</h1>
      <p style="color:#5e7a9a; font-size:13px; margin:8px 0 0;">{now.strftime('%d %B %Y, %H:%M')} — Sadece senin için</p>
    </div>

    <div style="background:#162338; border:1px solid #e8c547; border-radius:8px; padding:16px 20px; margin-bottom:24px;">
      <p style="color:#a8bcd4; font-size:13px; margin:0; line-height:1.6;">
        💡 <strong style="color:#f0ead8;">Kullanım:</strong> Bu sayfa, aboneye giden bültenden önce
        AI'ın ürettiği metinleri tek yerde gözden geçirmen içindir.
      </p>
    </div>

    {content_section}

    <div style="text-align:center; padding:16px; color:#5e7a9a; font-size:11px;">
      Bu rapor sadece bülten editörüne özeldir. Okuyuculara gönderilmez.
    </div>
  </div>
</body>
</html>'''

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  📋 AI raporu oluşturuldu: {os.path.abspath(output_filename)}")
    return output_filename
