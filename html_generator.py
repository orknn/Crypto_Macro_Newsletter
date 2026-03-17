"""
HTML Newsletter Generator — Premium Design
Generates a Daily Financial Bulletin matching the example template.
"""
import os
from datetime import datetime


def _fmt_price(price, fmt="price2"):
    """Format price based on type."""
    if price is None or price == 0:
        return "—"
    if fmt == "index":
        return f"{price:,.0f}" if price >= 1000 else f"{price:.2f}"
    if fmt == "fx4":
        return f"{price:.4f}"
    if fmt == "price2":
        return f"${price:,.2f}"
    if fmt == "price0":
        return f"${price:,.0f}"
    if fmt == "price4":
        return f"${price:.4f}"
    if fmt == "crypto":
        if price >= 100:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        else:
            return f"${price:.6f}"
    if fmt == "pct":
        return f"{price:.2f}%"
    return f"{price:.2f}"


def _fmt_change(val):
    """Format percentage change with sign."""
    if val is None:
        return "—", ""
    sign = "+" if val >= 0 else ""
    cls = "up" if val >= 0 else "down"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {sign}{val:.2f}%", cls


def _momentum_score(chg):
    """Map change to 0-100 momentum score."""
    if chg is None:
        return 50
    return max(0, min(100, 50 + chg * 5))


def _generate_ticker_bar(data):
    """Generate the top ticker bar HTML."""
    macro = data.get('macro_indicators', {})
    crypto_prices = data.get('crypto_prices', [])
    commodities = data.get('commodities', [])

    # Find BTC and Gold prices
    btc_price = 0
    btc_chg = 0
    for c in crypto_prices:
        if c['Symbol'] == 'BTC':
            btc_price = c.get('Current Price USD', 0)
            btc_chg = c.get('24h %', 0)
            break

    gold_price = 0
    gold_chg = 0
    for c in commodities:
        if c['Name'] == 'Gold':
            gold_price = c.get('Price', 0)
            gold_chg = c.get('Change %', 0)
            break

    tickers = [
        {'name': 'NASDAQ 100', 'price': _fmt_price(macro.get('NASDAQ 100 Futures', 0), 'index'),
         'chg': macro.get('NASDAQ 100 Futures_chg', 0), 'chg_val': macro.get('NASDAQ 100 Futures_chg', 0)},
        {'name': 'DXY', 'price': _fmt_price(macro.get('DXY', 0), 'fx4'),
         'chg': macro.get('DXY_chg', 0), 'chg_val': macro.get('DXY_chg', 0)},
        {'name': 'BTC', 'price': _fmt_price(btc_price, 'crypto'),
         'chg': btc_chg, 'chg_val': btc_chg},
        {'name': 'Gold', 'price': _fmt_price(gold_price, 'price2'),
         'chg': gold_chg, 'chg_val': gold_chg},
        {'name': '10Y UST', 'price': _fmt_price(macro.get('US 10-Year Treasury Yield', 0), 'pct'),
         'chg': macro.get('US 10-Year Treasury Yield_chg', 0), 'chg_val': macro.get('US 10-Year Treasury Yield_chg', 0)},
        {'name': 'VIX', 'price': _fmt_price(macro.get('VIX', 0), 'price2'),
         'chg': macro.get('VIX_chg', 0), 'chg_val': macro.get('VIX_chg', 0)},
    ]

    items = []
    for t in tickers:
        chg_text, chg_cls = _fmt_change(t['chg_val']) if t['chg_val'] != 0 else ("—", "")
        items.append(f'''
    <div class="ticker-item">
      <div class="ticker-name">{t['name']}</div>
      <div class="ticker-price">{t['price']}</div>
      <div class="ticker-change {chg_cls}">{chg_text}</div>
    </div>''')

    return '\n'.join(items)


def _generate_economic_calendar(events):
    """Generate the weekly economic calendar table."""
    rows = []
    for ev in events:
        actual = ev.get('actual', '—')
        rows.append(f'''
        <tr>
          <td style="color:var(--mid); white-space:nowrap;">{ev.get('date', '')}</td>
          <td class="mono">{ev.get('time', '')}</td>
          <td><div class="asset-name"><div class="asset-dot"></div>{ev.get('event', '')}</div></td>
          <td style="color:var(--mid);">{ev.get('country', '')}</td>
          <td class="mono" style="color:var(--mid);">{ev.get('previous', '—')}</td>
          <td class="mono" style="color:var(--gold);">{ev.get('forecast', '—')}</td>
          <td class="mono" style="font-weight:600; color:var(--ink);">{actual}</td>
        </tr>''')
    return '\n'.join(rows)


def _generate_kpi_cards(data):
    """Generate the KPI cards section."""
    macro = data.get('macro_indicators', {})
    fng = data.get('fear_and_greed', {})
    crypto_ov = data.get('crypto_market_overview', {})

    cards = [
        {'label': 'VIX Endeksi', 'value': f"{macro.get('VIX', 0):.1f}",
         'change': '', 'cls': ''},
        {'label': 'Dolar Endeksi (DXY)', 'value': f"{macro.get('DXY', 0):.2f}",
         'change': '', 'cls': ''},
        {'label': '10Y Treasury Yield', 'value': f"%{macro.get('US 10-Year Treasury Yield', 0):.2f}",
         'change': '', 'cls': ''},
        {'label': 'Fear & Greed', 'value': f"{fng.get('value', 0)}",
         'change': fng.get('classification', ''), 'cls': 'up' if fng.get('value', 50) >= 50 else 'down'},
        {'label': 'BTC Dominance', 'value': f"%{crypto_ov.get('btc_dominance', 0):.1f}",
         'change': '', 'cls': ''},
        {'label': 'Total Market Cap', 'value': f"${crypto_ov.get('total_market_cap', 0)/1e12:.2f}T",
         'change': '', 'cls': ''},
    ]

    items = []
    for c in cards:
        items.append(f'''
      <div class="kpi-card">
        <div class="kpi-label">{c['label']}</div>
        <div class="kpi-value">{c['value']}</div>
        <div class="kpi-change {c['cls']}">{c['change']}</div>
      </div>''')
    return '\n'.join(items)


def _generate_coinbase_premium(data):
    """Generate the Coinbase Premium SVG bar chart."""
    cp = data.get('coinbase_premium', {})
    trend = cp.get('trend_data', [])
    current = cp.get('current_value', 0)

    if not trend:
        return '<div style="color:var(--mid); text-align:center;">Veri bulunamadı</div>'

    min_val = min(d['value'] for d in trend)
    max_val = max(d['value'] for d in trend)
    abs_max = max(abs(min_val), abs(max_val), 0.001)

    width = 600
    height = 140
    padding_top = 10
    padding_bottom = 20
    chart_height = height - padding_top - padding_bottom
    zero_y = padding_top + chart_height / 2

    # Adjust zero line based on data range
    if abs_max > 0:
        scale = (chart_height / 2) / abs_max
    else:
        scale = 1

    n = len(trend)
    bar_gap = 1
    bar_width = max(1, (width - (n - 1) * bar_gap) / n)

    bars_svg = []
    for i, d in enumerate(trend):
        val = d['value']
        x = i * (bar_width + bar_gap)
        bar_h = abs(val) * scale
        bar_h = max(0.5, min(bar_h, chart_height / 2))

        if val >= 0:
            bar_y = zero_y - bar_h
            color = '#10B981'
        else:
            bar_y = zero_y
            color = '#EF4444'

        bars_svg.append(
            f'<rect x="{x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_h:.1f}" fill="{color}" rx="0.5"/>'
        )

    # X-axis time labels (show ~6 labels)
    time_labels_svg = []
    label_count = min(6, n)
    for j in range(label_count):
        idx = int(j * (n - 1) / max(label_count - 1, 1))
        t = trend[idx]['time']
        time_str = t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)
        lx = idx * (bar_width + bar_gap) + bar_width / 2
        time_labels_svg.append(
            f'<text x="{lx:.0f}" y="{height - 2}" font-size="8" '
            f'fill="rgba(255,255,255,0.3)" font-family="monospace" text-anchor="middle">{time_str}</text>'
        )

    # Y-axis labels
    y_labels_svg = [
        f'<text x="{width - 4}" y="{padding_top + 8}" font-size="7" fill="rgba(255,255,255,0.25)" font-family="monospace" text-anchor="end">{abs_max:+.3f}%</text>',
        f'<text x="{width - 4}" y="{zero_y - 3}" font-size="7" fill="rgba(255,255,255,0.35)" font-family="monospace" text-anchor="end">0</text>',
        f'<text x="{width - 4}" y="{height - padding_bottom - 2}" font-size="7" fill="rgba(255,255,255,0.25)" font-family="monospace" text-anchor="end">{-abs_max:+.3f}%</text>',
    ]

    # Determine signal
    if current > 0:
        signal_text = '▲ US buying pressure active'
        signal_cls = '#10B981'
    else:
        signal_text = '▼ US selling pressure'
        signal_cls = '#EF4444'

    return f'''
    <div class="sparkline-wrap" style="padding:20px 24px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
        <div>
          <div style="font-size:12px; color:var(--mid); margin-bottom:4px;">BTC/USD · Coinbase vs Global Spread</div>
          <div style="font-family:var(--mono); font-size:26px; color:var(--ink);">{current:+.4f}%</div>
          <div style="font-size:11px; color:{signal_cls}; margin-top:2px;">{signal_text}</div>
        </div>
        <div style="display:flex; gap:16px; font-size:11px; color:var(--mid);">
          <div style="text-align:center;"><div style="font-family:var(--mono); color:var(--ink); font-size:13px;">{max_val:+.3f}%</div><div>24h High</div></div>
          <div style="text-align:center;"><div style="font-family:var(--mono); color:var(--ink); font-size:13px;">{min_val:+.3f}%</div><div>24h Low</div></div>
        </div>
      </div>
      <div style="position:relative;">
        <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; height:160px;">
          <line x1="0" y1="{zero_y:.0f}" x2="{width}" y2="{zero_y:.0f}" stroke="rgba(255,255,255,0.12)" stroke-width="0.5"/>
          {''.join(bars_svg)}
          {''.join(time_labels_svg)}
          {''.join(y_labels_svg)}
        </svg>
      </div>
      <div style="margin-top:10px; padding:8px 12px; background:var(--cream2); border:1px solid rgba(232,197,71,0.15); border-radius:6px; font-size:11px; color:var(--mid); line-height:1.6;">
        💡 <strong style="color:var(--mid);">Reading guide:</strong> Positive values indicate US institutional buying pressure. Sustained positive premium is a bullish signal for BTC.
      </div>
    </div>'''


def _generate_asset_table(assets, columns, id_prefix="row"):
    """Generate a heatmap-style asset table."""
    rows = []
    for asset in assets:
        name = asset.get('Name', asset.get('Symbol', ''))
        symbol = asset.get('Symbol', asset.get('Ticker', ''))
        # Combine name and symbol on the same line if they're different
        if name != symbol:
            display = f"{name} <span style='color:var(--mid); font-size:11px; margin-left:6px;'>{symbol}</span>"
        else:
            display = name
            
        price = asset.get('Price', asset.get('Current Price USD', 0))
        chg_1d = asset.get('Change %', asset.get('24h %', 0)) or 0
        chg_1w = asset.get('7d %', asset.get('Change %', 0)) or 0
        chg_30d = asset.get('30d %', 0) or 0

        # Format price
        if price >= 1000:
            price_str = f"${price:,.0f}"
        elif price >= 1:
            price_str = f"${price:,.2f}"
        else:
            price_str = f"${price:.6f}"

        chg_1d_text, chg_1d_cls = _fmt_change(chg_1d)
        chg_1w_text, chg_1w_cls = _fmt_change(chg_1w)
        chg_30d_text, chg_30d_cls = _fmt_change(chg_30d)
        momentum = _momentum_score(chg_1d)
        neg_cls = " neg" if chg_1d < 0 else ""

        row_id = f"{id_prefix}-{symbol.lower()}" if symbol else ""
        rows.append(f'''
        <tr id="{row_id}">
          <td><div class="asset-name"><div class="asset-dot"></div>{display}</div></td>
          <td class="mono">{price_str}</td>
          <td class="mono {chg_1d_cls}">{chg_1d_text.replace("▲ ", "").replace("▼ ", "")}</td>
          <td class="mono {chg_1w_cls}">{chg_1w_text.replace("▲ ", "").replace("▼ ", "")}</td>
          <td class="mono {chg_30d_cls}">{chg_30d_text.replace("▲ ", "").replace("▼ ", "")}</td>
          <td><div class="cell-bar"><div class="cell-mini-bar"><div class="cell-mini-fill{neg_cls}" style="width:{momentum:.0f}%"></div></div><span class="mono" style="font-size:10px;color:var(--mid)">{momentum:.0f}</span></div></td>
        </tr>''')
    return '\n'.join(rows)








def _generate_news_stories(news_data, ai_commentaries=None):
    """Generate the news stories section with AI insights."""
    news = news_data.get('news', [])

    # Build a lookup from AI commentaries if available
    ai_lookup = {}
    if ai_commentaries:
        for item in ai_commentaries:
            ai_lookup[item.get('headline', '')] = item.get('commentary', '')

    # Keyword-based fallback commentary
    def _fallback_commentary(headline):
        h = headline.lower()
        if 'fed' in h or 'merkez bankası' in h:
            if 'temkinli' in h or 'şahin' in h or 'sıkılaştır' in h:
                return 'Risk iştahını azaltabilecek bir gelişme — risk assets üzerinde baskı oluşturabilir.'
            else:
                return 'Para politikası beklentilerini etkileyebilecek bir gelişme — market volatility artabilir.'
        if 'ecb' in h or 'avrupa' in h:
            if 'indirim' in h or 'gevşe' in h:
                return 'Likidite artışı beklentisi — riskli varlıklar için pozitif bir gelişme.'
            return 'Avrupa para politikası gelişmesi — DXY ve EUR paritesini etkileyebilir.'
        if 'çin' in h or 'teşvik' in h:
            return 'Riskli varlıklar için pozitif bir gelişme — emtia ve kripto piyasalarında yukarı yönlü hareket desteklenebilir.'
        if 'enflasyon' in h or 'tüfe' in h or 'cpi' in h:
            return 'Enflasyon verileri para politikası beklentilerini şekillendirecek — market volatility artabilir.'
        if 'istihdam' in h or 'işsizlik' in h:
            return 'İstihdam verileri ekonomik sağlık göstergesi — tahvil getirileri ve DXY üzerinde etkili olabilir.'
        if 'iran' in h or 'savaş' in h or 'gerilim' in h or 'jeopolitik' in h:
            return 'Jeopolitik risk — petrol, altın ve güvenli liman varlıklarında yükselişe neden olabilir.'
        return 'Makroekonomik gelişme — piyasa katılımcıları tarafından yakından takip edilmeli.'

    items = []
    for i, news_item in enumerate(news):
        # Handle backward compatibility: if it's a string, convert to dict
        if isinstance(news_item, str):
            headline = news_item
            img_url = ""
        else:
            headline = news_item.get('title', '')
            img_url = news_item.get('image_url', '')

        # Use AI commentary if available, otherwise fallback
        commentary = ai_lookup.get(headline) or _fallback_commentary(headline)
        ai_label = 'AI Insight' if ai_lookup.get(headline) else 'Analiz'
        
        # Build image HTML if present
        img_html = ""
        if img_url:
            img_html = f'''<div style="flex-shrink:0; margin-right:16px;">
              <img src="{img_url}" alt="News Thumbnail" style="width:72px; height:72px; object-fit:cover; border-radius:8px; border:1px solid var(--border);">
            </div>'''
            
        items.append(f'''
      <div class="story-item">
        <div class="story-num">{i+1:02d}</div>
        <div class="story-content" style="display:flex; align-items:flex-start;">
          {img_html}
          <div style="flex:1;">
            <div class="story-tag">Makro</div>
            <div class="story-headline">{headline}</div>
            <div style="margin-top:4px; font-size:11px; font-style:italic; color:var(--mid); line-height:1.5;">🤖 <strong style="color:var(--gold); font-style:normal;">{ai_label}:</strong> {commentary}</div>
          </div>
        </div>
      </div>''')
    return '\n'.join(items)

def _generate_options_market(options_data, options_note=None):
    """Generate the Options Market (Deribit) section."""
    if not options_data:
        return ""
    
    dvol = options_data.get('dvol_index', 0)
    dvol_chg = options_data.get('dvol_change_24h', 0)
    pcr = options_data.get('put_call_ratio', 0)
    oi = options_data.get('open_interest_btc', 0)
    
    dvol_chg_text, dvol_chg_cls = _fmt_change(dvol_chg)
    
    return f'''
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">BTC DVOL (Zımni Volatilite)</div>
        <div class="kpi-value">{dvol:.1f}</div>
        <div class="kpi-change {dvol_chg_cls}">{dvol_chg_text}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Put/Call Ratio (Hacim)</div>
        <div class="kpi-value">{pcr:.2f}</div>
        <div class="kpi-change">{"Ayı Eğilimli" if pcr > 1.0 else "Boğa Eğilimli"}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Açık Pozisyon (OI)</div>
        <div class="kpi-value">{oi/1000:.1f}K BTC</div>
      </div>
    </div>
    <div style="margin-top:12px; font-size:11.5px; color:var(--mid); line-height:1.5;">
      💡 <strong style="color:var(--mid);">Opsiyon Piyasası Notu:</strong> 
      {options_note or "DVOL endeksi piyasaların öngördüğü volatiliteti gösterir. Put/Call oranının 1'in altında olması call (alım) yönlü beklentinin ağırlıkta olduğuna işaret edebilir."}
    </div>'''


def _md_to_html(md_text):
    """Convert simple markdown to HTML for agent reports."""
    import re
    lines = md_text.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br>')
            continue

        # Headers
        if stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            heading = stripped[3:]
            # Bold within heading
            heading = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', heading)
            html_lines.append(f'<h4 style="color:var(--gold); font-size:13px; font-weight:600; margin:16px 0 8px; letter-spacing:0.5px;">{heading}</h4>')
            continue

        if stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            heading = stripped[4:]
            heading = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', heading)
            html_lines.append(f'<h5 style="color:var(--mid); font-size:12px; font-weight:600; margin:12px 0 6px;">{heading}</h5>')
            continue

        # List items
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul style="margin:4px 0; padding-left:20px;">')
                in_list = True
            item = stripped[2:]
            item = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:var(--ink);">\1</strong>', item)
            item = re.sub(r'`(.*?)`', r'<code style="background:rgba(232,197,71,0.1); padding:1px 5px; border-radius:3px; font-size:11px; color:var(--gold);">\1</code>', item)
            html_lines.append(f'<li style="margin-bottom:6px; font-size:12px; color:var(--mid); line-height:1.6;">{item}</li>')
            continue

        # Regular paragraph - close list if open
        if in_list:
            html_lines.append('</ul>')
            in_list = False

        # Bold + code + inline formatting
        p = stripped
        p = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:var(--ink);">\1</strong>', p)
        p = re.sub(r'`(.*?)`', r'<code style="background:rgba(232,197,71,0.1); padding:1px 5px; border-radius:3px; font-size:11px; color:var(--gold);">\1</code>', p)
        html_lines.append(f'<p style="margin:4px 0; font-size:12px; color:var(--mid); line-height:1.65;">{p}</p>')

    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


def _generate_agent_section(title, icon, report_data):
    """Generate an agent report section for the newsletter."""
    if not report_data:
        return ''

    report = report_data.get('report', '')
    success = report_data.get('success', False)

    status_badge = (
        '<span style="background:#10B981; color:#fff; padding:2px 8px; border-radius:10px; '
        'font-size:9px; font-weight:600; letter-spacing:0.5px;">AI ACTIVE</span>'
        if success else
        '<span style="background:var(--mid); color:var(--navy); padding:2px 8px; border-radius:10px; '
        'font-size:9px; font-weight:600; letter-spacing:0.5px;">OFFLINE</span>'
    )

    report_html = _md_to_html(report)

    return f'''
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
      <span style="font-size:18px;">{icon}</span>
      <span style="font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:var(--mid);">{title}</span>
      {status_badge}
    </div>
    <div style="background:var(--cream2); border:1px solid var(--border); border-radius:10px; padding:20px 24px; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(to right, var(--gold), transparent); opacity:0.5;"></div>
      {report_html}
    </div>'''


def _generate_fear_greed_gauge(data):
    """Generate an SVG speedometer gauge for the Crypto Fear & Greed Index."""
    import math

    fng = data.get('fear_and_greed', {})
    value = fng.get('value', 50)
    label = fng.get('classification', 'Neutral')

    # Gauge parameters
    cx, cy = 200, 180  # center of the arc
    radius = 140
    inner_radius = 120
    tick_outer = radius + 8
    tick_inner = radius - 4
    label_radius = radius + 28

    # Arc goes from 180° (left) to 0° (right) — semi-circle
    start_angle = 180
    end_angle = 0

    # Value mapped to angle (0=180°, 100=0°)
    needle_angle = 180 - (value / 100) * 180

    # Helper to get point on circle
    def polar(angle_deg, r):
        rad = math.radians(angle_deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    # Create gradient arc segments
    segments = [
        (0, 25, '#22c55e', '#4ade80'),     # Extreme Fear (green)
        (25, 45, '#4ade80', '#facc15'),     # Fear (green→yellow)
        (45, 55, '#facc15', '#fbbf24'),     # Neutral (yellow)
        (55, 75, '#fbbf24', '#f87171'),     # Greed (yellow→red)
        (75, 100, '#f87171', '#ef4444'),    # Extreme Greed (red)
    ]

    arc_paths = []
    for seg_start, seg_end, color1, color2 in segments:
        a1 = 180 - (seg_start / 100) * 180
        a2 = 180 - (seg_end / 100) * 180
        x1, y1 = polar(a1, radius)
        x2, y2 = polar(a2, radius)
        x1i, y1i = polar(a1, inner_radius)
        x2i, y2i = polar(a2, inner_radius)
        large = 1 if abs(a1 - a2) > 180 else 0
        arc_paths.append(
            f'<path d="M {x1:.1f},{y1:.1f} A {radius},{radius} 0 {large},1 {x2:.1f},{y2:.1f} '
            f'L {x2i:.1f},{y2i:.1f} A {inner_radius},{inner_radius} 0 {large},0 {x1i:.1f},{y1i:.1f} Z" '
            f'fill="{color1}" opacity="0.85"/>'
        )

    # Tick marks
    ticks_svg = []
    for i in range(0, 101, 4):
        angle = 180 - (i / 100) * 180
        x1t, y1t = polar(angle, tick_inner)
        x2t, y2t = polar(angle, tick_outer)
        width = "2.5" if i % 25 == 0 else "1.2"
        opacity = "0.9" if i % 25 == 0 else "0.4"
        ticks_svg.append(
            f'<line x1="{x1t:.1f}" y1="{y1t:.1f}" x2="{x2t:.1f}" y2="{y2t:.1f}" '
            f'stroke="var(--mid)" stroke-width="{width}" opacity="{opacity}"/>'
        )

    # Zone labels
    zone_labels = [
        (12.5, 'Extreme', 'Fear'),
        (35, 'Fear', ''),
        (50, 'Neutral', ''),
        (65, 'Greed', ''),
        (87.5, 'Extreme', 'Greed'),
    ]
    labels_svg = []
    for pos, line1, line2 in zone_labels:
        angle = 180 - (pos / 100) * 180
        lx, ly = polar(angle, label_radius)
        # Rotate text to follow the arc
        text_angle = -angle + 90
        labels_svg.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
            f'transform="rotate({text_angle:.1f},{lx:.1f},{ly:.1f})" '
            f'fill="var(--mid)" font-size="10" font-weight="500" letter-spacing="0.5">'
            f'{line1}</text>'
        )
        if line2:
            ly2 = ly + 12
            labels_svg.append(
                f'<text x="{lx:.1f}" y="{ly2:.1f}" text-anchor="middle" '
                f'transform="rotate({text_angle:.1f},{lx:.1f},{ly2:.1f})" '
                f'fill="var(--mid)" font-size="10" font-weight="500" letter-spacing="0.5">'
                f'{line2}</text>'
            )

    # Needle (triangle)
    needle_rad = math.radians(needle_angle)
    tip_x = cx + (inner_radius - 10) * math.cos(needle_rad)
    tip_y = cy - (inner_radius - 10) * math.sin(needle_rad)
    # Base of needle (perpendicular to needle direction)
    base_offset = 8
    perp_rad = needle_rad + math.pi / 2
    b1x = cx + base_offset * math.cos(perp_rad)
    b1y = cy - base_offset * math.sin(perp_rad)
    b2x = cx - base_offset * math.cos(perp_rad)
    b2y = cy + base_offset * math.sin(perp_rad)

    # Needle color based on value
    if value <= 25:
        needle_color = '#22c55e'
    elif value <= 45:
        needle_color = '#4ade80'
    elif value <= 55:
        needle_color = '#facc15'
    elif value <= 75:
        needle_color = '#f87171'
    else:
        needle_color = '#ef4444'

    needle_svg = (
        f'<polygon points="{tip_x:.1f},{tip_y:.1f} {b1x:.1f},{b1y:.1f} {b2x:.1f},{b2y:.1f}" '
        f'fill="{needle_color}" opacity="0.95"/>'
        f'<circle cx="{cx}" cy="{cy}" r="6" fill="{needle_color}" opacity="0.9"/>'
    )

    svg = f'''
    <div style="text-align:center;">
      <svg viewBox="0 0 400 240" width="200" height="130" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;">
        <!-- Arc segments -->
        {''.join(arc_paths)}
        <!-- Tick marks -->
        {''.join(ticks_svg)}
        <!-- Zone labels -->
        {''.join(labels_svg)}
        <!-- Needle -->
        {needle_svg}
        <!-- Center value -->
        <text x="{cx}" y="{cy - 20}" text-anchor="middle" fill="var(--ink)"
              font-family="'JetBrains Mono', monospace" font-size="42" font-weight="700">{value}</text>
        <text x="{cx}" y="{cy + 8}" text-anchor="middle" fill="var(--mid)"
              font-size="14" font-weight="500" letter-spacing="1">{label}</text>
      </svg>
    </div>'''

    return svg


def _generate_etf_flows(data):
    """Generate the Spot Bitcoin ETF Flow section."""
    etf = data.get('etf_flows')
    if not etf:
        return ""
        
    ibit = etf.get('IBIT_flow_m', 0)
    fbtc = etf.get('FBTC_flow_m', 0)
    total = etf.get('Total_flow_m', 0)
    sentiment = etf.get('sentiment', 'Neutral')
    note = data.get('etf_note', '')
    
    ibit_cls = "up" if ibit >= 0 else "down"
    fbtc_cls = "up" if fbtc >= 0 else "down"
    total_cls = "up" if total >= 0 else "down"
    
    ibit_sign = "+" if ibit > 0 else ""
    fbtc_sign = "+" if fbtc > 0 else ""
    total_sign = "+" if total > 0 else ""
    
    badge_style = 'background:rgba(232,197,71,0.1); color:var(--gold); border:1px solid rgba(232,197,71,0.3);'
    if 'Inflow' in sentiment:
        badge_style = 'background:rgba(16,185,129,0.15); color:#10B981; border:1px solid rgba(16,185,129,0.4);'
    elif 'Outflow' in sentiment:
        badge_style = 'background:rgba(239,68,68,0.15); color:#EF4444; border:1px solid rgba(239,68,68,0.4);'

    return f'''
    <div style="background:var(--cream2); border:1px solid var(--border); border-radius:8px; padding:16px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div style="font-size:12px; color:var(--ink); font-weight:500;">Spot Bitcoin ETF Flows</div>
        <div style="font-size:10px; padding:2px 8px; border-radius:12px; font-weight:600; text-transform:uppercase; {badge_style}">{sentiment}</div>
      </div>
      <div style="display:flex; gap:24px; margin-bottom:12px;">
        <div>
          <div style="font-size:9.5px; text-transform:uppercase; color:var(--mid); letter-spacing:1px; margin-bottom:4px;">Total Flow</div>
          <div class="{total_cls}" style="font-family:var(--mono); font-size:16px; font-weight:600;">{total_sign}${total:.1f}m</div>
        </div>
        <div>
          <div style="font-size:9.5px; text-transform:uppercase; color:var(--mid); letter-spacing:1px; margin-bottom:4px;">IBIT (BlackRock)</div>
          <div class="{ibit_cls}" style="font-family:var(--mono); font-size:16px; font-weight:600;">{ibit_sign}${ibit:.1f}m</div>
        </div>
        <div>
          <div style="font-size:9.5px; text-transform:uppercase; color:var(--mid); letter-spacing:1px; margin-bottom:4px;">FBTC (Fidelity)</div>
          <div class="{fbtc_cls}" style="font-family:var(--mono); font-size:16px; font-weight:600;">{fbtc_sign}${fbtc:.1f}m</div>
        </div>
      </div>
      <div style="font-size:11.5px; color:var(--mid); line-height:1.5;">
        🎯 {note}
      </div>
    </div>
    '''


def generate_newsletter_html(data, output_filename='daily_bulletin.html'):
    """
    Generate the complete newsletter HTML.
    data: dict with all data sections from data_fetcher.py
    """
    now = datetime.now()
    days_tr = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
    months_tr = ['OCA', 'ŞUB', 'MAR', 'NİS', 'MAY', 'HAZ', 'TEM', 'AĞU', 'EYL', 'EKİ', 'KAS', 'ARA']
    day_name = days_tr[now.weekday()]
    date_str = f"{day_name} · {now.day:02d} {months_tr[now.month-1]} {now.year}"

    # Prepare general assessment narrative
    macro = data.get('macro_indicators', {})
    crypto_ov = data.get('crypto_market_overview', {})
    fng = data.get('fear_and_greed', {})

    # Fear & Greed badge for header (Design Proposal #1)
    fng_value = fng.get('value', 0)
    fng_label = fng.get('classification', 'N/A')
    if fng_value <= 25:
        fng_color = '#ff4757'  # Extreme Fear
    elif fng_value <= 45:
        fng_color = '#ff6348'  # Fear
    elif fng_value <= 55:
        fng_color = '#ffa502'  # Neutral
    elif fng_value <= 75:
        fng_color = '#2ed573'  # Greed
    else:
        fng_color = '#00d084'  # Extreme Greed

    # Use AI-generated summary if available, otherwise build template
    ai_summary = data.get('ai_summary')
    if ai_summary:
        summary_text = ai_summary
    else:
        summary_text = (
            f"<strong>Makroekonomik göstergeler</strong>e bakıldığında, <strong>VIX</strong> endeksi "
            f"<span class='highlight'>{macro.get('VIX', 0):.1f}</span> seviyesinde, "
            f"<strong>DXY</strong> (Dolar Endeksi) {macro.get('DXY', 0):.2f} noktasında işlem görmektedir. "
            f"<strong>ABD 10 Yıllık Tahvil Getirisi</strong> %{macro.get('US 10-Year Treasury Yield', 0):.2f} seviyesindedir. "
            f"Kripto piyasalarında <strong>Crypto Fear &amp; Greed Index</strong> "
            f"<span class='highlight'>{fng.get('value', 0)}</span> ({fng.get('classification', 'N/A')}) olarak kaydedildi. "
            f"Toplam kripto <strong>market cap</strong> ${crypto_ov.get('total_market_cap', 0)/1e12:.2f} Trilyon, "
            f"<strong>BTC Dominance</strong> %{crypto_ov.get('btc_dominance', 0):.1f} seviyesindedir."
        )
        # Inject actuals from economic calendar if available
        for ev in data.get('economic_calendar', []):
            actual = ev.get('actual', '—')
            if actual != '—':
                if 'CPI' in ev.get('event', '') or 'TÜFE' in ev.get('event', '') or 'PCE' in ev.get('event', ''):
                    summary_text += f" Öte yandan, piyasaların merakla beklediği <strong>{ev.get('event', '')}</strong> verisi <strong>{actual}</strong> seviyesinde gerçekleşti."
                elif 'Non-Farm' in ev.get('event', '') or 'Tarım Dışı' in ev.get('event', ''):
                    summary_text += f" Ayrıca <strong>ABD Tarım Dışı İstihdam</strong> verisi son olarak <strong>{actual}</strong> olarak açıklandı."

    korelasyon_notu = data.get('korelasyon_notu')
    if korelasyon_notu:
        summary_text += f"<br><br>💡 <strong style='font-weight:600;'>Gözlem:</strong> <span style='font-style:italic;'>{korelasyon_notu}</span>"

    # ── Makro Scoreboard (Inline Bar) ──
    ms = data.get('macro_scoreboard', {})
    dxy = ms.get('DXY', 0)
    dxy_chg = ms.get('DXY_chg', 0)
    m2 = ms.get('M2', 0)
    m2_chg = ms.get('M2_chg', 0)
    pmi = ms.get('PMI', 0)
    pmi_chg = ms.get('PMI_chg', 0)

    dxy_chg_text, dxy_chg_cls = _fmt_change(dxy_chg)
    m2_chg_text, m2_chg_cls = _fmt_change(m2_chg)
    pmi_chg_text, pmi_chg_cls = _fmt_change(pmi_chg)

    macro_scoreboard_html = f'''
    <div style="display:flex; justify-content:space-between; align-items:center; background:var(--cream2); border:1px solid var(--border); border-radius:8px; padding:10px 16px; margin-top:16px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:10px; color:var(--mid); text-transform:uppercase; font-weight:600; letter-spacing:1px;">DXY</span>
        <span style="font-family:var(--mono); font-size:13px; color:var(--ink); font-weight:500;">{dxy:.2f}</span>
        <span class="{dxy_chg_cls}" style="font-size:11px;">{dxy_chg_text}</span>
      </div>
      <div style="width:1px; height:16px; background:var(--navy-border);"></div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:10px; color:var(--mid); text-transform:uppercase; font-weight:600; letter-spacing:1px;">M2 Supply</span>
        <span style="font-family:var(--mono); font-size:13px; color:var(--ink); font-weight:500;">${m2:.1f}T</span>
        <span class="{m2_chg_cls}" style="font-size:11px;">{m2_chg_text}</span>
      </div>
      <div style="width:1px; height:16px; background:var(--navy-border);"></div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:10px; color:var(--mid); text-transform:uppercase; font-weight:600; letter-spacing:1px;">US PMI</span>
        <span style="font-family:var(--mono); font-size:13px; color:var(--ink); font-weight:500;">{pmi:.1f}</span>
        <span class="{pmi_chg_cls}" style="font-size:11px;">{pmi_chg_text}</span>
      </div>
    </div>
    '''

    # Build all sections
    ticker_bar = _generate_ticker_bar(data)
    econ_calendar = _generate_economic_calendar(data.get('economic_calendar', []))
    kpi_cards = _generate_kpi_cards(data)
    coinbase_premium = _generate_coinbase_premium(data)
    commodity_rows = _generate_asset_table(data.get('commodities', []), 'commodities', 'row')
    mag7_rows = _generate_asset_table(
        [{'Name': s['Name'], 'Symbol': s['Symbol'], 'Price': s['Price'],
          'Change %': s['Change %'], '7d %': s.get('7d %', 0), '30d %': s.get('30d %', 0)} for s in data.get('magnificent_7', [])],
        'mag7', 'row'
    )
    crypto_rows = _generate_asset_table(data.get('crypto_prices', []), 'crypto', 'row')
    
    sp500_sectors = data.get('sp500_sectors', [])
    sp500_rows = ""
    if sp500_sectors:
        sp500_rows_list = []
        for s in sp500_sectors:
            sym = s.get('Symbol', '')
            name = s.get('Name', '')
            chg = s.get('Change %', 0)
            chg_text, chg_cls = _fmt_change(chg)
            # Create a simple colored tile for the heatmap
            bg_color = 'rgba(16, 185, 129, 0.15)' if chg > 0 else ('rgba(239, 68, 68, 0.15)' if chg < 0 else 'rgba(255, 255, 255, 0.05)')
            border_color = 'rgba(16, 185, 129, 0.4)' if chg > 0 else ('rgba(239, 68, 68, 0.4)' if chg < 0 else 'rgba(255, 255, 255, 0.1)')
            sp500_rows_list.append(f'''
            <div style="background:{bg_color}; border:1px solid {border_color}; border-radius:6px; padding:6px; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <div style="font-size:9.5px; color:var(--mid); letter-spacing:0.5px; margin-bottom:2px; text-transform:uppercase;">{name}</div>
                <div style="font-family:var(--mono); font-size:12px; font-weight:600; color:var(--ink);">{sym}</div>
                <div class="{chg_cls}" style="font-family:var(--mono); font-size:10.5px; margin-top:2px;">{chg:.2f}%</div>
            </div>''')
        sp500_rows = f'''
        <div style="margin-bottom:6px; display:flex; align-items:center; gap:8px;">
          <span style="font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:var(--mid); font-weight:600;">📊 S&P 500 Sectors</span>
          <div style="flex:1; height:1px; background:var(--navy-border);"></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(105px, 1fr)); gap:8px; margin-bottom:16px;">
          {''.join(sp500_rows_list)}
        </div>
        '''

    news_stories = _generate_news_stories(data.get('macro_news', {}), data.get('news_commentaries'))
    options_market = _generate_options_market(data.get('options_data', {}))
    fear_greed_gauge = _generate_fear_greed_gauge(data)

    # Extra indicators (Content Proposals #6, #7, #8)
    macro = data.get('macro_indicators', {})
    crypto_ov = data.get('crypto_market_overview', {})
    yield_10y = macro.get('US 10-Year Treasury Yield', 0)
    yield_2y = macro.get('US 2-Year Treasury Yield', 0)
    yield_spread = yield_10y - yield_2y if yield_10y and yield_2y else 0
    spread_status = 'Normal' if yield_spread > 0 else 'Inverted ⚠️'
    spread_cls = 'up' if yield_spread > 0 else 'down'

    smh_price = macro.get('SMH (Semiconductor ETF)', 0)
    smh_chg = macro.get('SMH (Semiconductor ETF)_chg', 0)
    smh_chg_text, smh_chg_cls = _fmt_change(smh_chg)

    stablecoin_mcap = crypto_ov.get('total_market_cap', 0) * (crypto_ov.get('stablecoin_dominance', 0) / 100) if crypto_ov.get('stablecoin_dominance') else 0
    stablecoin_dom = crypto_ov.get('stablecoin_dominance', 0)

    # Global Liquidity
    gl = data.get('global_liquidity', {})
    gl_value = gl.get('value_formatted', 'N/A')
    gl_weekly = gl.get('weekly_change', 0)
    gl_weekly_text, gl_weekly_cls = _fmt_change(gl_weekly)

    extra_indicators = f'''
    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:1px; background:var(--border); border:1px solid var(--border);">
      <div style="background:var(--cream); padding:14px 16px;">
        <div style="font-family:var(--mono); font-size:8px; letter-spacing:1px; text-transform:uppercase; color:var(--mid); margin-bottom:6px;">2Y-10Y Spread</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:500; color:var(--ink);">{yield_spread:.2f}%</div>
        <div class="{spread_cls}" style="font-family:var(--mono); font-size:10px; margin-top:4px;">{spread_status}</div>
      </div>
      <div style="background:var(--cream); padding:14px 16px;">
        <div style="font-family:var(--mono); font-size:8px; letter-spacing:1px; text-transform:uppercase; color:var(--mid); margin-bottom:6px;">Fed Balance Sheet</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:500; color:var(--ink);">{gl_value}</div>
        <div class="{gl_weekly_cls}" style="font-family:var(--mono); font-size:10px; margin-top:4px;">W: {gl_weekly_text}</div>
      </div>
      <div style="background:var(--cream); padding:14px 16px;">
        <div style="font-family:var(--mono); font-size:8px; letter-spacing:1px; text-transform:uppercase; color:var(--mid); margin-bottom:6px;">Stablecoin Mcap</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:500; color:var(--ink);">${stablecoin_mcap/1e9:.1f}B</div>
        <div style="font-family:var(--mono); font-size:10px; margin-top:4px; color:var(--mid);">Dom: %{stablecoin_dom:.1f}</div>
      </div>
      <div style="background:var(--cream); padding:14px 16px;">
        <div style="font-family:var(--mono); font-size:8px; letter-spacing:1px; text-transform:uppercase; color:var(--mid); margin-bottom:6px;">SMH (Semi ETF)</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:500; color:var(--ink);">${smh_price:,.2f}</div>
        <div class="{smh_chg_cls}" style="font-family:var(--mono); font-size:10px; margin-top:4px;">{smh_chg_text}</div>
      </div>
    </div>
    <div style="margin-top:10px; font-size:11px; color:var(--mid); line-height:1.4;">
      💡 <strong style="color:var(--mid);">Gösterge Notu:</strong>
      {data.get('indicators_note', "2Y-10Y spread negatifken resesyon sinyali verir. Fed Balance Sheet artışı global likiditeyi gösterir. SMH, AI ve semiconductor sektörünün barometresidir.")}
    </div>'''

    # BTC 4-Hour Status with support/resistance
    cp = data.get('coinbase_premium', {})
    btc_support = cp.get('btc_support_level', 0)
    btc_resistance = cp.get('btc_resistance_level', 0)
    btc_price = 0
    btc_chg_24h = 0
    for c in data.get('crypto_prices', []):
        if c['Symbol'] == 'BTC':
            btc_price = c.get('Current Price USD', 0)
            btc_chg_24h = c.get('24h %', 0)
            break

    # Determine BTC position relative to support/resistance
    if btc_price > 0 and btc_support > 0 and btc_resistance > 0:
        if btc_price > btc_resistance:
            btc_analysis = f"Fiyat <strong>${btc_price:,.0f}</strong> ile <strong>resistance level</strong> (${btc_resistance:,.0f}) üzerinde işlem görüyor — yukarı yönlü momentum devam edebilir."
            btc_status_color = '#10B981'
        elif btc_price < btc_support:
            btc_analysis = f"Fiyat <strong>${btc_price:,.0f}</strong> ile <strong>support level</strong> (${btc_support:,.0f}) altına geriledi — kısa vadeli selling pressure devam edebilir."
            btc_status_color = '#EF4444'
        else:
            btc_analysis = f"Fiyat <strong>${btc_price:,.0f}</strong> şu an <strong>support level</strong> (${btc_support:,.0f}) üzerinde tutunuyor, <strong>resistance level</strong> ${btc_resistance:,.0f} seviyesinde."
            btc_status_color = 'var(--gold)'
    else:
        btc_analysis = 'BTC fiyat verisi alınamadı.'
        btc_status_color = 'var(--mid)'

    btc_chg_text, btc_chg_cls = _fmt_change(btc_chg_24h)
    btc_status_html = f'''
    <div class="sparkline-wrap" style="padding:18px 24px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;">
        <div style="display:flex; align-items:center; gap:12px;">
          <div style="font-family:var(--mono); font-size:22px; font-weight:500; color:var(--ink);">${btc_price:,.0f}</div>
          <div class="{btc_chg_cls}" style="font-family:var(--mono); font-size:13px;">{btc_chg_text}</div>
        </div>
        <div style="display:flex; gap:20px; font-size:11px;">
          <div style="text-align:center;"><div style="color:var(--mid); margin-bottom:2px;">Support Level</div><div style="font-family:var(--mono); color:#10B981; font-size:13px;">${btc_support:,.0f}</div></div>
          <div style="text-align:center;"><div style="color:var(--mid); margin-bottom:2px;">Resistance Level</div><div style="font-family:var(--mono); color:#EF4444; font-size:13px;">${btc_resistance:,.0f}</div></div>
        </div>
      </div>
      <div style="padding:10px 14px; background:var(--cream2); border-left:3px solid {btc_status_color}; border-radius:0 6px 6px 0; font-size:12.5px; color:var(--mid); line-height:1.65;">
        📈 {btc_analysis}
      </div>
    </div>
    '''

    # Futures Basis Analysis
    fb = data.get('crypto_futures_basis', {})
    fb_btc = fb.get('btc_basis', 0)
    fb_eth = fb.get('eth_basis', 0)
    fb_sen = fb.get('sentiment', 'Neutral')
    fb_desc = fb.get('description', '')
    
    # Sentiment Badge Color Map
    fb_badges = {
        'Strong Bullish': 'background:rgba(16,185,129,0.15); color:#10B981; border:1px solid rgba(16,185,129,0.4);',
        'Bullish': 'background:rgba(16,185,129,0.1); color:#34d399; border:1px solid rgba(16,185,129,0.3);',
        'Neutral': 'background:rgba(232,197,71,0.1); color:var(--gold); border:1px solid rgba(232,197,71,0.3);',
        'Bearish': 'background:rgba(239,68,68,0.1); color:#fca5a5; border:1px solid rgba(239,68,68,0.3);',
        'Strong Bearish': 'background:rgba(239,68,68,0.15); color:#EF4444; border:1px solid rgba(239,68,68,0.4);',
    }
    fb_badge_style = fb_badges.get(fb_sen, fb_badges['Neutral'])
    
    basis_html = f'''
    <div style="background:var(--cream2); border:1px solid var(--border); border-radius:8px; padding:16px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div style="font-size:12px; color:var(--ink); font-weight:500;">Annualized Futures Premium</div>
        <div style="font-size:10px; padding:2px 8px; border-radius:12px; font-weight:600; text-transform:uppercase; {fb_badge_style}">{fb_sen}</div>
      </div>
      <div style="display:flex; gap:24px; margin-bottom:12px;">
        <div>
          <div style="font-size:9.5px; text-transform:uppercase; color:var(--mid); letter-spacing:1px; margin-bottom:4px;">BTC Basis</div>
          <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--ink);">{fb_btc:.1f}%</div>
        </div>
        <div>
          <div style="font-size:9.5px; text-transform:uppercase; color:var(--mid); letter-spacing:1px; margin-bottom:4px;">ETH Basis</div>
          <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--ink);">{fb_eth:.1f}%</div>
        </div>
      </div>
      <div style="font-size:11.5px; color:var(--mid); line-height:1.5;">
        🎯 {data.get('futures_note') or fb_desc}
      </div>
    </div>
    '''

    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="x-apple-disable-message-reformatting">
<title>Daily Financial Bulletin — nocashflow.net</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;1,700&family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  /* ── RESET & BASE ── */
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: #f0ebe0;
    color: #1a1410;
    font-family: 'Source Serif 4', Georgia, serif;
    -webkit-font-smoothing: antialiased;
    font-size: 15px;
    line-height: 1.6;
  }}

  /* ── COLOUR SYSTEM ── */
  :root {{
    --cream:   #f0ebe0;
    --cream2:  #e8e2d6;
    --cream3:  #ddd7ca;
    --ink:     #1a1410;
    --ink2:    #2d2620;
    --ink3:    #3d352a;
    --mid:     #7a6e62;
    --dim:     #a89e92;
    --border:  rgba(26,20,16,.12);
    --border2: rgba(26,20,16,.06);
    --accent:  #b5292a;
    --gold:    #8b6914;
    --green:   #1a6b3a;
    --red:     #b5292a;
    --serif:   'Playfair Display', Georgia, serif;
    --body:    'Source Serif 4', Georgia, serif;
    --mono:    'DM Mono', monospace;
  }}

  /* ── WRAPPER ── */
  .bulletin {{
    max-width: 680px;
    margin: 0 auto;
    background: var(--cream);
    border: 1px solid var(--border);
  }}

  /* ── HEADER ── */
  .header {{
    padding: 32px 40px 24px;
    border-bottom: 3px solid var(--ink);
    background: var(--cream);
  }}
  .header-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }}
  .logo-mark {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .logo-icon {{
    width: 32px; height: 32px;
    background: var(--ink);
    border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
  }}
  .logo-text {{
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--mid);
  }}
  .date-badge {{
    font-family: var(--mono);
    font-size: 10px;
    color: var(--mid);
    letter-spacing: 0.5px;
    border-left: 2px solid var(--border);
    padding-left: 12px;
  }}
  .header-title {{
    font-family: var(--serif);
    font-size: clamp(28px, 5vw, 40px);
    font-weight: 800;
    line-height: 1.05;
    color: var(--ink);
    letter-spacing: -1px;
    margin-bottom: 6px;
  }}
  .header-title span {{ color: var(--accent); font-style: italic; }}
  .header-sub {{
    font-family: var(--mono);
    font-size: 10px;
    color: var(--mid);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 4px;
  }}

  /* ── TICKER BAR ── */
  .ticker-bar {{
    background: var(--ink);
    padding: 0 40px;
    display: flex;
    gap: 0;
    overflow-x: auto;
    border-bottom: 1px solid var(--ink);
  }}
  .ticker-bar::-webkit-scrollbar {{ display: none; }}
  .ticker-item {{
    padding: 10px 20px 10px 0;
    margin-right: 20px;
    border-right: 1px solid rgba(255,255,255,0.1);
    display: flex;
    flex-direction: column;
    gap: 2px;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .ticker-item:last-child {{ border-right: none; }}
  .ticker-name {{
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: 1.5px;
    color: rgba(255,255,255,0.4);
    text-transform: uppercase;
  }}
  .ticker-price {{
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 500;
    color: rgba(255,255,255,0.9);
  }}
  .ticker-change {{ font-family: var(--mono); font-size: 10px; }}
  .up   {{ color: #2d9e5f; }}
  .down {{ color: var(--accent); }}

  /* ── SECTION ── */
  .section {{
    padding: 32px 40px;
    border-bottom: 1px solid var(--border);
  }}
  .section-label {{
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--mid);
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .section-label::before {{
    content: '';
    width: 16px;
    height: 2px;
    background: var(--accent);
    flex-shrink: 0;
  }}
  .section-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }}

  /* ── SUMMARY CARD ── */
  .summary-card {{
    border-left: 3px solid var(--accent);
    padding: 16px 20px;
    background: var(--cream2);
  }}
  .summary-text {{
    font-size: 14px;
    line-height: 1.75;
    color: var(--ink3);
    font-weight: 300;
  }}
  .summary-text strong {{ color: var(--ink); font-weight: 600; }}
  .summary-text .highlight {{
    color: var(--accent);
    font-weight: 600;
  }}

  /* ── KPI GRID ── */
  .kpi-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    background: transparent;
    border: 1px solid var(--border);
  }}
  .kpi-card {{
    background: var(--cream);
    padding: 14px 16px;
    flex: 1 1 28%;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .kpi-label {{
    font-family: var(--mono);
    font-size: 8px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--mid);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .kpi-value {{
    font-family: var(--mono);
    font-size: 20px;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.5px;
  }}
  .kpi-change {{
    font-family: var(--mono);
    font-size: 10px;
    color: var(--mid);
  }}

  /* ── HEATMAP TABLE ── */
  .heatmap-table {{ width: 100%; border-collapse: collapse; }}
  .heatmap-table th {{
    font-family: var(--mono);
    font-size: 8.5px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--mid);
    padding: 8px 10px;
    text-align: right;
    border-bottom: 2px solid var(--ink);
    font-weight: 500;
    background: var(--cream2);
  }}
  .heatmap-table th:first-child {{ text-align: left; }}
  .heatmap-table td {{
    padding: 8px 10px;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
    text-align: right;
    color: var(--ink3);
  }}
  .heatmap-table td:first-child {{ text-align: left; }}
  .heatmap-table tr:last-child td {{ border-bottom: none; }}
  .heatmap-table tbody tr:nth-child(even) {{ background: var(--cream2); }}
  .heatmap-table tbody tr:hover {{ background: var(--cream3); }}
  .asset-name {{
    font-weight: 500;
    color: var(--ink);
    display: flex; align-items: center; gap: 6px;
    font-size: 13px;
  }}
  .asset-dot {{
    width: 4px; height: 4px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
  }}
  .mono {{ font-family: var(--mono); font-size: 12.5px; }}
  .cell-bar {{
    display: flex;
    align-items: center;
    gap: 6px;
    justify-content: flex-end;
  }}
  .cell-mini-bar {{
    flex: 1;
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
    max-width: 60px;
  }}
  .cell-mini-fill {{ height: 100%; border-radius: 2px; background: var(--gold); }}
  .cell-mini-fill.neg {{ background: var(--accent); }}

  /* ── ECON CALENDAR ── */
  .econ-calendar {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
  .econ-calendar th {{
    font-family: var(--mono);
    font-size: 8.5px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--mid);
    padding: 8px 8px;
    text-align: left;
    border-bottom: 2px solid var(--ink);
    font-weight: 500;
    background: var(--cream2);
  }}
  .econ-calendar th:nth-child(n+5) {{ text-align: right; }}
  .econ-calendar td {{
    padding: 8px 8px;
    font-size: 11.5px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
    color: var(--ink3);
  }}
  .econ-calendar td:nth-child(n+5) {{ text-align: right; font-family: var(--mono); font-size: 11px; }}
  .econ-calendar tr:last-child td {{ border-bottom: none; }}
  .econ-calendar tbody tr:nth-child(even) {{ background: var(--cream2); }}

  /* ── SPARKLINE WRAP ── */
  .sparkline-wrap {{
    background: var(--cream2);
    border: 1px solid var(--border);
    padding: 16px 20px;
  }}

  /* ── STORIES ── */
  .story-list {{ display: flex; flex-direction: column; gap: 0; }}
  .story-item {{
    display: flex;
    gap: 16px;
    padding: 16px 0;
    border-bottom: 1px solid var(--border);
  }}
  .story-item:last-child {{ border-bottom: none; padding-bottom: 0; }}
  .story-num {{
    font-family: var(--mono);
    font-size: 11px;
    color: var(--dim);
    width: 20px;
    flex-shrink: 0;
    padding-top: 3px;
  }}
  .story-tag {{
    font-family: var(--mono);
    font-size: 8px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 5px;
  }}
  .story-headline {{
    font-family: var(--serif);
    font-size: 16px;
    font-weight: 700;
    color: var(--ink);
    margin-bottom: 6px;
    line-height: 1.3;
  }}
  .story-body {{ font-size: 13px; color: var(--ink3); line-height: 1.65; }}

  /* ── INSIGHT BOX ── */
  .insight-box {{
    background: var(--cream2);
    border-left: 2px solid var(--gold);
    padding: 10px 14px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--ink3);
    line-height: 1.6;
    font-style: italic;
  }}
  .insight-label {{
    font-family: var(--mono);
    font-size: 8px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--gold);
    font-style: normal;
    font-weight: 500;
    margin-right: 6px;
  }}

  /* ── SCOREBOARD ── */
  .scoreboard {{
    display: flex;
    border: 1px solid var(--border);
    background: var(--cream2);
    margin-top: 16px;
    overflow: hidden;
  }}
  .scoreboard-item {{
    flex: 1;
    padding: 12px 16px;
    border-right: 1px solid var(--border);
    text-align: center;
  }}
  .scoreboard-item:last-child {{ border-right: none; }}
  .scoreboard-lbl {{
    font-family: var(--mono);
    font-size: 8px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--mid);
    margin-bottom: 4px;
  }}
  .scoreboard-val {{
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 500;
    color: var(--ink);
  }}
  .scoreboard-chg {{
    font-family: var(--mono);
    font-size: 10px;
    margin-top: 2px;
  }}

  /* ── FOOTER ── */
  .footer {{
    padding: 20px 40px;
    background: var(--ink);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .footer-brand {{
    font-family: var(--mono);
    font-size: 11px;
    color: rgba(255,255,255,0.6);
    letter-spacing: 1px;
  }}
  .footer-link {{
    font-family: var(--mono);
    font-size: 10px;
    color: rgba(255,255,255,0.4);
    text-decoration: none;
    letter-spacing: 0.5px;
  }}
  .footer-disc {{
    font-size: 10px;
    color: rgba(255,255,255,0.3);
    line-height: 1.5;
    padding: 16px 40px;
    background: var(--ink);
    text-align: center;
    border-top: 1px solid rgba(255,255,255,0.08);
    font-family: var(--mono);
    letter-spacing: 0.3px;
  }}

  @media (max-width: 540px) {{
    .header, .section, .footer {{ padding-left: 20px; padding-right: 20px; }}
    .kpi-grid {{ flex-wrap: wrap; }}
    .header-title {{ font-size: 26px; }}
    .scoreboard {{ flex-wrap: wrap; }}
    .scoreboard-item {{ flex: 1 1 45%; }}
  }}
</style>
</head>
<body>
<div class="bulletin">

  <!-- HEADER -->
  <div class="header">
    <div class="header-top">
      <div class="logo-mark">
        <div class="logo-icon">
          <svg width="18" height="18" viewBox="0 0 22 22" fill="none">
            <path d="M9 4C6.239 4 4 6.239 4 9C4 11.761 6.239 14 9 14C10.2 14 11.3 13.56 12.15 12.83" stroke="#f0ebe0" stroke-width="2.2" stroke-linecap="round"/>
            <path d="M12.15 5.17C11.3 4.44 10.2 4 9 4" stroke="#f0ebe0" stroke-width="2.2" stroke-linecap="round"/>
            <line x1="14" y1="4" x2="14" y2="18" stroke="#f0ebe0" stroke-width="2.2" stroke-linecap="round"/>
            <path d="M14 4C14 4 18 4 18 7C18 10 14 10 14 10" stroke="#f0ebe0" stroke-width="2.2" stroke-linecap="round"/>
            <path d="M14 10C14 10 18.5 10 18.5 13.5C18.5 17 14 18 14 18" stroke="#f0ebe0" stroke-width="2.2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="logo-text">nocashflow.net</div>
      </div>
      <div class="date-badge">{date_str}</div>
    </div>
    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap;">
      <div>
        <div class="header-title">Daily <span>Financial</span><br>Bulletin</div>
        <div class="header-sub">Markets · Macro · Crypto · Key Stories</div>
      </div>
      <div style="flex-shrink:0; margin-top:4px;">
        {fear_greed_gauge}
      </div>
    </div>
  </div>

  <!-- TICKER BAR -->
  <div class="ticker-bar">
    {ticker_bar}
  </div>

  <!-- GENEL DEĞERLENDİRME -->
  <div class="section">
    <div class="section-label">Genel Değerlendirme</div>
    <div class="summary-card">
      <p class="summary-text">{summary_text}</p>
    </div>
    <div class="scoreboard">
      <div class="scoreboard-item">
        <div class="scoreboard-lbl">DXY</div>
        <div class="scoreboard-val">{dxy:.2f}</div>
        <div class="scoreboard-chg {dxy_chg_cls}">{dxy_chg_text}</div>
      </div>
      <div class="scoreboard-item">
        <div class="scoreboard-lbl">M2 Supply</div>
        <div class="scoreboard-val">${m2:.1f}T</div>
        <div class="scoreboard-chg {m2_chg_cls}">{m2_chg_text}</div>
      </div>
      <div class="scoreboard-item">
        <div class="scoreboard-lbl">US PMI</div>
        <div class="scoreboard-val">{pmi:.1f}</div>
        <div class="scoreboard-chg {pmi_chg_cls}">{pmi_chg_text}</div>
      </div>
      <div class="scoreboard-item">
        <div class="scoreboard-lbl">2Y-10Y Spread</div>
        <div class="scoreboard-val">{yield_spread:.2f}%</div>
        <div class="scoreboard-chg {spread_cls}">{spread_status}</div>
      </div>
    </div>
  </div>

  <!-- EKONOMİK TAKVİM -->
  <div class="section">
    <div class="section-label">Haftalık Ekonomik Takvim</div>
    <div style="margin-bottom:10px; font-size:11px; color:var(--mid); display:flex; align-items:center; gap:6px; font-family:var(--mono);">
      <span style="background:var(--accent); color:var(--ink); padding:2px 8px; font-size:9px; letter-spacing:1px;">★★★ YÜKSEK ETKİLİ</span>
    </div>
    <table class="econ-calendar">
      <colgroup>
        <col style="width:13%"><col style="width:10%"><col style="width:32%">
        <col style="width:10%"><col style="width:11%"><col style="width:11%"><col style="width:13%">
      </colgroup>
      <thead>
        <tr>
          <th>Gün</th><th>Saat</th><th>Veri</th><th>Ülke</th>
          <th>Önceki</th><th>Beklenti</th><th>Gerçekleşen</th>
        </tr>
      </thead>
      <tbody>{econ_calendar}</tbody>
    </table>
  </div>

  <!-- GÜNÜN ÖNE ÇIKAN VERİLERİ -->
  <div class="section">
    <div class="section-label">Günün Öne Çıkan Verileri</div>
    <div class="kpi-grid">{kpi_cards}</div>
  </div>

  <!-- EK GÖSTERGELER -->
  <div class="section">
    <div class="section-label">Ek Piyasa Göstergeleri</div>
    {extra_indicators}
  </div>

  <!-- COİNBASE PREMİUM -->
  <div class="section">
    <div class="section-label">Coinbase Premium Index — 24 Saatlik</div>
    {coinbase_premium}
  </div>

  <!-- BTC & ETF -->
  <div class="section">
    <div class="section-label">BTC Analizi & ETF Akışları</div>
    {btc_status_html}
    <div style="margin-top:20px;">{_generate_etf_flows(data)}</div>
  </div>

  <!-- FUTURES BASIS -->
  <div class="section">
    <div class="section-label">Crypto Futures Basis Analizi</div>
    {basis_html}
  </div>

  <!-- OPSİYON PİYASALARI -->
  <div class="section">
    <div class="section-label">Deribit Opsiyon Piyasaları</div>
    {options_market}
  </div>

  <!-- ASSET SUMMARY -->
  <div class="section">
    <div class="section-label">Asset Summary</div>

    <div style="margin-bottom:6px; display:flex; align-items:center; gap:8px;">
      <span style="font-family:var(--mono); font-size:9px; letter-spacing:1.5px; text-transform:uppercase; color:var(--mid);">🪙 Commodities</span>
      <div style="flex:1; height:1px; background:var(--border);"></div>
    </div>
    <table class="heatmap-table" style="margin-bottom:24px;">
      <thead><tr><th>Asset</th><th>Price</th><th>1D</th><th>1W</th><th>30D</th><th style="width:90px">Momentum</th></tr></thead>
      <tbody>{commodity_rows}</tbody>
    </table>

    <div style="margin-bottom:6px; display:flex; align-items:center; gap:8px;">
      <span style="font-family:var(--mono); font-size:9px; letter-spacing:1.5px; text-transform:uppercase; color:var(--mid);">📊 Magnificent 7</span>
      <div style="flex:1; height:1px; background:var(--border);"></div>
    </div>
    <table class="heatmap-table" style="margin-bottom:24px;">
      <thead><tr><th>Asset</th><th>Price</th><th>1D</th><th>1W</th><th>30D</th><th style="width:90px">Momentum</th></tr></thead>
      <tbody>{mag7_rows}</tbody>
    </table>

    <div style="margin-bottom:6px; display:flex; align-items:center; gap:8px;">
      <span style="font-family:var(--mono); font-size:9px; letter-spacing:1.5px; text-transform:uppercase; color:var(--mid);">₿ Crypto Watchlist</span>
      <div style="flex:1; height:1px; background:var(--border);"></div>
    </div>
    <table class="heatmap-table" style="margin-bottom:24px;">
      <thead><tr><th>Asset</th><th>Price</th><th>24h</th><th>7d</th><th>30D</th><th style="width:90px">Momentum</th></tr></thead>
      <tbody>{crypto_rows}</tbody>
    </table>

    {sp500_rows}

    <div style="margin-top:8px; font-family:var(--mono); font-size:9.5px; font-style:italic; color:var(--dim); line-height:1.5;">
      Momentum &gt; 70: aşırı alım · Momentum &lt; 30: aşırı satım
    </div>
  </div>

  <!-- HABERLER -->
  <div class="section">
    <div class="section-label">Öne Çıkan Haberler</div>
    <div class="story-list">{news_stories}</div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-brand">nocashflow.net · Orkun Biçen</div>
    <a href="https://nocashflow.net" class="footer-link">nocashflow.net</a>
  </div>
  <div class="footer-disc">
    Bu bülten yalnızca bilgilendirme amaçlıdır ve yatırım tavsiyesi niteliği taşımaz. Geçmiş performans gelecekteki sonuçların göstergesi değildir. © {now.year} Orkun Biçen. Tüm hakları saklıdır.
  </div>

</div>
</body>
</html>'''


    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  ✅ HTML oluşturuldu: {os.path.abspath(output_filename)}")
    return output_filename
