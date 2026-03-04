"""
Design Preview Generator — Visual preview of Designer Agent suggestions.
Generates design_preview.html showing before/after for each suggestion.
"""
import os
import json
from datetime import datetime


def generate_design_preview(design_report_raw, output_filename="design_preview.html"):
    """
    Generate an HTML preview showing designer suggestions with before/after cards.
    design_report_raw: the raw report string from ExperienceDesignerAgent
    """
    if not design_report_raw:
        return None

    now = datetime.now()

    # Parse suggestions from the report
    suggestions = _extract_suggestions(design_report_raw)
    if not suggestions:
        return None

    # Build suggestion cards
    cards = []
    for i, s in enumerate(suggestions, 1):
        priority = s.get('priority', 'medium')
        priority_color = {'high': '#EF4444', 'medium': '#F59E0B', 'low': '#10B981'}.get(priority, '#F59E0B')
        priority_label = {'high': 'YÜKSEK', 'medium': 'ORTA', 'low': 'DÜŞÜK'}.get(priority, 'ORTA')

        cards.append(f'''
    <div style="background:#1f3350; border-radius:12px; padding:24px; margin-bottom:20px; border:1px solid #2a4a6e;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
        <span style="background:{priority_color}; color:white; font-size:10px; padding:3px 10px; border-radius:10px; font-weight:700; letter-spacing:1px;">{priority_label}</span>
        <h3 style="margin:0; color:#f0ead8; font-size:16px;">Öneri {i}: {s.get('area', 'Tasarım')}</h3>
      </div>

      <div style="display:flex; gap:16px; margin-bottom:16px;">
        <div style="flex:1; background:#162338; border-radius:8px; padding:16px; border:1px solid #2a4a6e;">
          <div style="font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:#EF4444; font-weight:600; margin-bottom:8px;">📌 Mevcut</div>
          <code style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#a8bcd4; line-height:1.6; display:block; word-break:break-all;">
            {s.get('selector', '')} {{ {s.get('current', '')} }}
          </code>
        </div>
        <div style="flex:1; background:#162338; border-radius:8px; padding:16px; border:1px solid #10B981;">
          <div style="font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:#10B981; font-weight:600; margin-bottom:8px;">✅ Önerilen</div>
          <code style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#f0ead8; line-height:1.6; display:block; word-break:break-all;">
            {s.get('selector', '')} {{ {s.get('proposed', '')} }}
          </code>
        </div>
      </div>

      <div style="font-size:13px; color:#a8bcd4; line-height:1.6; padding:12px 16px; background:rgba(232,197,71,0.06); border-left:3px solid #e8c547; border-radius:0 6px 6px 0;">
        💡 {s.get('reason', '')}
      </div>
    </div>''')

    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Tasarım Önerileri — {now.strftime('%d %B %Y')}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body style="margin:0; padding:20px; background:#0f1b2d; font-family:'Inter',sans-serif;">
  <div style="max-width:700px; margin:0 auto;">

    <div style="text-align:center; padding:24px; margin-bottom:24px;">
      <h1 style="color:#e8c547; font-size:22px; margin:0;">🎨 Tasarım Önerileri</h1>
      <p style="color:#5e7a9a; font-size:13px; margin:8px 0 0;">{now.strftime('%d %B %Y, %H:%M')} — Onayın bekleniyor</p>
    </div>

    <div style="background:#162338; border:1px solid #e8c547; border-radius:8px; padding:16px 20px; margin-bottom:24px;">
      <p style="color:#a8bcd4; font-size:13px; margin:0; line-height:1.6;">
        💡 <strong style="color:#f0ead8;">Kullanım:</strong> Aşağıdaki önerileri incele.
        Beğendiklerini Antigravity'de <em>"Tasarım önerisi 1 ve 3'ü uygula"</em> şeklinde söylemen yeterli.
      </p>
    </div>

    {''.join(cards)}

    <div style="text-align:center; padding:16px; color:#5e7a9a; font-size:11px;">
      Bu önizleme sadece sana özeldir. Onaylamadığın öneriler uygulanmaz.
    </div>
  </div>
</body>
</html>'''

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  🎨 Tasarım önizlemesi oluşturuldu: {os.path.abspath(output_filename)}")
    return output_filename


def _extract_suggestions(report_text):
    """Extract structured suggestions from the report text."""
    suggestions = []
    # The report is formatted as markdown with **1. [PRIORITY] Area** blocks
    import re
    # Find all suggestion blocks
    blocks = re.split(r'\*\*\d+\.', report_text)
    for block in blocks[1:]:  # Skip the header
        s = {}
        # Extract priority
        priority_match = re.search(r'\[(HIGH|MEDIUM|LOW)\]', block, re.IGNORECASE)
        if priority_match:
            s['priority'] = priority_match.group(1).lower()
        # Extract area
        area_match = re.search(r'\]\s*(.*?)\*\*', block)
        if area_match:
            s['area'] = area_match.group(1).strip()
        # Extract selector
        sel_match = re.search(r'Selector:\s*`(.*?)`', block)
        if sel_match:
            s['selector'] = sel_match.group(1)
        # Extract current
        cur_match = re.search(r'Mevcut:\s*`(.*?)`', block)
        if cur_match:
            s['current'] = cur_match.group(1)
        # Extract proposed
        prop_match = re.search(r'Önerilen:\s*`(.*?)`', block)
        if prop_match:
            s['proposed'] = prop_match.group(1)
        # Extract reason
        reason_match = re.search(r'Neden:\s*(.*?)(?:\n|$)', block)
        if reason_match:
            s['reason'] = reason_match.group(1).strip()

        if s.get('selector') or s.get('area'):
            suggestions.append(s)

    return suggestions
