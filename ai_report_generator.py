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
    content_report = data.get('content_strategy_report', {})
    design_report = data.get('design_improvement_report', {})

    if not content_report and not design_report:
        print("  ℹ️  AI raporu yok, ai_reports.html atlanıyor.")
        return None

    now = datetime.now()

    def _md_to_html(md_text):
        """Convert markdown to styled HTML."""
        import re
        lines = md_text.split('\n')
        html_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    html_lines.append('</ol>')
                    in_list = False
                html_lines.append('<br>')
                continue

            if stripped.startswith('## '):
                if in_list:
                    html_lines.append('</ol>')
                    in_list = False
                heading = stripped[3:]
                heading = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', heading)
                html_lines.append(f'<h3 style="color:#e8c547; margin:20px 0 10px; font-size:16px;">{heading}</h3>')
                continue

            # Numbered list items (1. 2. 3. etc.)
            num_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
            if num_match:
                if not in_list:
                    html_lines.append('<ol style="margin:8px 0; padding-left:24px;">')
                    in_list = True
                item = num_match.group(2)
                item = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#f0ead8;">\1</strong>', item)
                item = re.sub(r'`(.*?)`', r'<code style="background:rgba(232,197,71,0.15); padding:2px 6px; border-radius:3px; color:#e8c547;">\1</code>', item)
                html_lines.append(f'<li style="margin-bottom:10px; font-size:14px; color:#a8bcd4; line-height:1.7;" value="{num_match.group(1)}">{item}</li>')
                continue

            # Bullet list items
            if stripped.startswith('- ') or stripped.startswith('* '):
                if in_list:
                    html_lines.append('</ol>')
                    in_list = False
                item = stripped[2:]
                item = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#f0ead8;">\1</strong>', item)
                html_lines.append(f'<p style="margin:4px 0 4px 16px; font-size:14px; color:#a8bcd4; line-height:1.7;">• {item}</p>')
                continue

            # Regular paragraph
            if in_list:
                html_lines.append('</ol>')
                in_list = False
            p = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#f0ead8;">\1</strong>', stripped)
            html_lines.append(f'<p style="margin:6px 0; font-size:14px; color:#a8bcd4; line-height:1.7;">{p}</p>')

        if in_list:
            html_lines.append('</ol>')

        return '\n'.join(html_lines)

    def _render_section(title, icon, report_data):
        status = report_data.get('success', False)
        badge_color = '#10B981' if status else '#EF4444'
        badge_text = 'AI ACTIVE' if status else 'OFFLINE'
        report_html = _md_to_html(report_data.get('report', ''))

        return f'''
    <div style="background:#1f3350; border-radius:10px; padding:24px; margin-bottom:24px; border:1px solid #2a4a6e;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
        <span style="font-size:24px;">{icon}</span>
        <h2 style="margin:0; color:#f0ead8; font-size:18px;">{title}</h2>
        <span style="background:{badge_color}; color:white; font-size:10px; padding:2px 8px; border-radius:10px; font-weight:600;">{badge_text}</span>
      </div>
      <div style="border-left:3px solid #e8c547; padding-left:16px;">
        {report_html}
      </div>
    </div>'''

    content_section = _render_section(
        'İçerik Strateji Raporu', '🤖', content_report
    ) if content_report else ''

    design_section = _render_section(
        'Tasarım Geliştirme Önerisi', '🎨', design_report
    ) if design_report else ''

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
        💡 <strong style="color:#f0ead8;">Kullanım:</strong> Numaralı önerileri inceleyip Antigravity'de
        <em>"İçerik raporundan 1 ve 3'ü uygula"</em> veya
        <em>"Tasarım raporundan 2. öneriyi uygula"</em> şeklinde talimat verebilirsiniz.
      </p>
    </div>

    {content_section}
    {design_section}

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
