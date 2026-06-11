"""
HTML Newsletter Generator — Premium Design
Generates a Daily Financial Bulletin matching the example template.
"""
import os
from datetime import datetime


def _na(v):
    """True for missing values, including float NaN (which `is None` misses)."""
    return v is None or (isinstance(v, float) and v != v)


def _fmt_price(price, fmt="price2"):
    """Format price based on type."""
    if _na(price) or price == 0:
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
    if _na(val):
        return "—", ""
    sign = "+" if val >= 0 else ""
    cls = "up" if val >= 0 else "down"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {sign}{val:.2f}%", cls


def _momentum_score(chg):
    """Map change to 0-100 momentum score."""
    if _na(chg):
        return 50
    return max(0, min(100, 50 + chg * 5))


def _generate_ticker_bar(data):
    """Generate the top ticker bar HTML."""
    macro = data.get('macro_indicators', {})
    crypto_prices = data.get('crypto_prices', [])
    commodities = data.get('commodities', [])
    fng = data.get('fear_and_greed', {})
    crypto_ov = data.get('crypto_market_overview', {})

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
        {'name': 'GOLD', 'price': _fmt_price(gold_price, 'price0'),
         'chg': gold_chg, 'chg_val': gold_chg},
        {'name': '10Y UST', 'price': _fmt_price(macro.get('US 10-Year Treasury Yield', 0), 'pct'),
         'chg': macro.get('US 10-Year Treasury Yield_chg', 0), 'chg_val': macro.get('US 10-Year Treasury Yield_chg', 0)},
        {'name': 'VIX', 'price': _fmt_price(macro.get('VIX', 0), 'price2'),
         'chg': macro.get('VIX_chg', 0), 'chg_val': macro.get('VIX_chg', 0)},
        {'name': 'BTC', 'price': _fmt_price(btc_price, 'price0'),
         'chg': btc_chg, 'chg_val': btc_chg},
        {'name': 'BTC.D', 'price': f"{crypto_ov.get('btc_dominance', 0):.1f}%",
         'custom_chg_text': '—', 'custom_chg_cls': ''},
        {'name': 'F&G INDEX', 'price': str(fng.get('value', 0)),
         'custom_chg_text': fng.get('classification', ''), 'custom_chg_cls': 'up' if fng.get('value', 50) >= 50 else 'down'},
    ]

    html = '<table class="ticker" cellpadding="0" cellspacing="0"><tr>\n'
    for t in tickers:
        if 'custom_chg_text' in t:
            chg_text = t['custom_chg_text']
            chg_cls = t.get('custom_chg_cls', '')
        else:
            chg_text, chg_cls = _fmt_change(t.get('chg_val', 0)) if t.get('chg_val', 0) != 0 else ("—", "")
            
        html += f'''
    <td class="ti">
      <div class="ti-name">{t['name']}</div>
      <div class="ti-val">{t['price']}</div>
      <div class="ti-chg {chg_cls}">{chg_text}</div>
    </td>'''
    html += '\n</tr></table>'
    return html


def _generate_economic_calendar(events):
    """Generate the weekly economic calendar table."""
    rows = []
    for ev in events:
        actual = ev.get('actual', '—')
        forecast = ev.get('forecast', '—')
        
        # Color-code actual: green if released, bold; dim if pending
        if actual and actual != '—':
            actual_style = 'font-weight:700; color:var(--text);'
            # Try to compare actual vs forecast for beat/miss coloring
            try:
                act_num = float(actual.replace('%', '').replace('K', '').replace('M', '').replace('B', '').strip())
                fct_num = float(forecast.replace('%', '').replace('K', '').replace('M', '').replace('B', '').strip())
                
                # Determine if higher or lower is "better" (green)
                higher_is_better = True
                event_lower = ev.get('event', '').lower()
                if any(kw in event_lower for kw in ['cpi', 'pce', 'inflation', 'unemployment', 'claims']):
                    higher_is_better = False
                
                if act_num > fct_num:
                    actual_style = f"font-weight:700; color:var(--{'green' if higher_is_better else 'red'});"
                elif act_num < fct_num:
                    actual_style = f"font-weight:700; color:var(--{'red' if higher_is_better else 'green'});"
            except (ValueError, AttributeError):
                pass
        else:
            actual = '—'
            actual_style = 'color:var(--dim);'
        
        rows.append(f'''
        <tr>
          <td style="color:var(--dim); white-space:nowrap;">{ev.get('date', '')}</td>
          <td class="mono">{ev.get('time', '')}</td>
          <td><div class="asset-name"><div class="asset-dot"></div>{ev.get('event', '')}</div></td>
          <td style="color:var(--dim);">{ev.get('country', '')}</td>
          <td class="mono" style="color:var(--dim);">{ev.get('previous', '—')}</td>
          <td class="mono" style="color:var(--gold);">{forecast}</td>
          <td class="mono" style="{actual_style}">{actual}</td>
        </tr>''')
    return '\n'.join(rows)


def _generate_kpi_cards(data):
    """Generate the KPI cards section."""
    macro = data.get('macro_indicators', {})
    fng = data.get('fear_and_greed', {})
    crypto_ov = data.get('crypto_market_overview', {})

    cards = [
        {'label': 'VIX Index', 'value': f"{macro.get('VIX', 0):.1f}",
         'change': '', 'cls': ''},
        {'label': 'Dollar Index (DXY)', 'value': f"{macro.get('DXY', 0):.2f}",
         'change': '', 'cls': ''},
        {'label': '10Y Treasury Yield', 'value': f"{macro.get('US 10-Year Treasury Yield', 0):.2f}%",
         'change': '', 'cls': ''},
        {'label': 'Fear & Greed', 'value': f"{fng.get('value', 0)}",
         'change': fng.get('classification', ''), 'cls': 'up' if fng.get('value', 50) >= 50 else 'down'},
        {'label': 'BTC Dominance', 'value': f"{crypto_ov.get('btc_dominance', 0):.1f}%",
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
        return '<div style="color:#a1a1aa; text-align:center;">No data available</div>'

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
            color = '#4aba7a'
        else:
            bar_y = zero_y
            color = '#cd5c5c'

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
        signal_cls = '#4aba7a'
    else:
        signal_text = '▼ US selling pressure'
        signal_cls = '#cd5c5c'

    return f'''
    <div class="sparkline-wrap" style="padding:20px 24px; page-break-inside: avoid; break-inside: avoid;">
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
        <tr>
          <td style="vertical-align:top;">
            <div style="font-size:12px; color:#a1a1aa; margin-bottom:4px;">BTC/USD · Coinbase vs Global Spread</div>
            <div style="font-family:var(--mono); font-size:26px; color:#e6edf3;">{current:+.4f}%</div>
            <div style="font-size:11px; color:{signal_cls}; margin-top:2px;">{signal_text}</div>
          </td>
          <td style="vertical-align:top; text-align:right;">
            <table style="display:inline-block; font-size:11px; color:#a1a1aa;">
              <tr>
                <td style="padding-right:16px; text-align:center;"><div style="font-family:var(--mono); color:#e6edf3; font-size:13px;">{max_val:+.3f}%</div><div>24h High</div></td>
                <td style="text-align:center;"><div style="font-family:var(--mono); color:#e6edf3; font-size:13px;">{min_val:+.3f}%</div><div>24h Low</div></td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
      <div style="position:relative; overflow:hidden;">
        <!--[if !mso]><!-->
        <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; height:160px; min-width:100%;">
          <line x1="0" y1="{zero_y:.0f}" x2="{width}" y2="{zero_y:.0f}" stroke="rgba(255,255,255,0.12)" stroke-width="0.5"/>
          {''.join(bars_svg)}
        </svg>
        <!--<![endif]-->
      </div>
      <div style="margin-top:12px; padding:10px 14px; background:var(--bg3); border:1px solid var(--border); border-radius:4px; font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.6;">
        <strong style="color:var(--gold2);">Reading guide:</strong> Positive values indicate US institutional buying pressure. Sustained positive premium is a bullish signal for BTC.
      </div>
    </div>'''


def _generate_m2_money_supply(data):
    """Generate the M2 Money Supply section with a 5-year SVG line chart."""
    m2 = data.get('m2_money_supply')
    if not m2:
        return ""

    val_fmt = m2.get('value_formatted', '')
    chg = m2.get('monthly_change', 0)
    chg_text, chg_cls = _fmt_change(chg)
    trend = m2.get('trend', [])

    chart_html = ""
    if trend:
        width = 700
        height = 120
        pad_l, pad_r, pad_t, pad_b = 0, 0, 8, 8

        vals = [p['value'] for p in trend]
        min_v = min(vals)
        max_v = max(vals)
        rng = max_v - min_v or 0.001
        n = len(vals)

        def px(i, v):
            x = pad_l + (i / max(n - 1, 1)) * (width - pad_l - pad_r)
            y = height - pad_b - ((v - min_v) / rng) * (height - pad_t - pad_b)
            return x, y

        # Build polyline points
        points = " ".join(f"{px(i,v)[0]:.1f},{px(i,v)[1]:.1f}" for i, v in enumerate(vals))

        # Build gradient area (closed path)
        path_d = f"M {px(0, vals[0])[0]:.1f},{px(0, vals[0])[1]:.1f} "
        path_d += " ".join(f"L {px(i,v)[0]:.1f},{px(i,v)[1]:.1f}" for i, v in enumerate(vals))
        last_x = px(n - 1, vals[-1])[0]
        path_d += f" L {last_x:.1f},{height - pad_b} L {pad_l},{height - pad_b} Z"

        # Year labels: show one label per year
        year_labels = []
        seen_years = set()
        for i, p in enumerate(trend):
            yr = p['date'][:4]
            if yr not in seen_years:
                seen_years.add(yr)
                x, _ = px(i, vals[i])
                year_labels.append(
                    f'<text x="{x:.0f}" y="{height}" font-size="8" '
                    f'fill="rgba(255,255,255,0.25)" font-family="monospace" text-anchor="middle">{yr}</text>'
                )

        # Current value marker
        last_x2, last_y2 = px(n - 1, vals[-1])

        chart_html = f'''
        <div style="position:relative; margin-top:16px; overflow:hidden;">
          <svg width="100%" viewBox="0 0 {width} {height + 12}" preserveAspectRatio="none"
               style="display:block; height:110px;">
            <defs>
              <linearGradient id="m2grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#4aba7a" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="#4aba7a" stop-opacity="0.01"/>
              </linearGradient>
            </defs>
            <!-- Area fill -->
            <path d="{path_d}" fill="url(#m2grad)"/>
            <!-- Line -->
            <polyline points="{points}" fill="none" stroke="#4aba7a" stroke-width="1.5"
                      stroke-linejoin="round" stroke-linecap="round"/>
            <!-- Endpoint dot -->
            <circle cx="{last_x2:.1f}" cy="{last_y2:.1f}" r="3" fill="#4aba7a"/>
            <!-- Year labels -->
            {''.join(year_labels)}
          </svg>
        </div>'''

    return f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; page-break-inside:avoid;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">Global Liquidity Proxy</div>
          <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">US M2 Money Supply — 5Y Weekly · FRED (M2SL)</div>
        </div>
        <div style="text-align:right;">
          <div style="font-family:var(--mono); font-size:20px; font-weight:700; color:var(--text);">{val_fmt}</div>
          <div class="{chg_cls}" style="font-family:var(--mono); font-size:12px; margin-top:2px;">{chg_text} <span style="color:var(--dim); font-size:10px;">MoM</span></div>
        </div>
      </div>
      {chart_html}
      <div style="font-family:var(--sans); font-size:10px; color:var(--dim); font-style:italic; line-height:1.5; margin-top:10px;">
        A rising M2 supply indicates expanding liquidity, which generally provides tailwinds for risk assets.
      </div>
    </div>
    '''



def _generate_asset_table(assets, columns, id_prefix="row"):
    """Generate a heatmap-style asset table."""
    rows = []
    for asset in assets:
        name = asset.get('Name', asset.get('Symbol', ''))
        symbol = asset.get('Symbol', asset.get('Ticker', ''))
        # Combine name and symbol on the same line if they're different
        if name != symbol:
            display = f"{name} <span style='color:var(--dim); font-size:11px; margin-left:6px;'>{symbol}</span>"
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
            key_headline = item.get('original_headline') or item.get('headline', '')
            ai_lookup[key_headline] = {
                'commentary': item.get('commentary', '')
            }

    # Keyword-based fallback commentary
    def _fallback_commentary(headline):
        h = headline.lower()
        if 'fed' in h or 'central bank' in h:
            if 'hawkish' in h or 'tighten' in h or 'cautious' in h:
                return 'A development that could weigh on risk appetite — potential downward pressure on risk assets.'
            else:
                return 'A development that could shift monetary policy expectations — market volatility may increase.'
        if 'ecb' in h or 'europe' in h:
            if 'cut' in h or 'ease' in h or 'dovish' in h:
                return 'Expectations of increased liquidity — a positive development for risk assets.'
            return 'European monetary policy development — could impact DXY and EUR parity.'
        if 'china' in h or 'stimulus' in h:
            return 'A positive development for risk assets — could support upward movement in commodity and crypto markets.'
        if 'inflation' in h or 'cpi' in h or 'pce' in h:
            return 'Inflation data will shape monetary policy expectations — market volatility may increase.'
        if 'employment' in h or 'jobs' in h or 'payroll' in h or 'unemployment' in h:
            return 'Employment data is a key economic health indicator — could impact bond yields and DXY.'
        if 'iran' in h or 'war' in h or 'tension' in h or 'geopolitical' in h:
            return 'Geopolitical risk — could drive oil, gold, and safe-haven assets higher.'
        return 'Macroeconomic development — should be closely monitored by market participants.'

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
        ai_data = ai_lookup.get(headline, {})
        display_headline = headline
        
        commentary = ai_data.get('commentary') or _fallback_commentary(headline)
        ai_label = 'AI Insight' if ai_data else 'Analysis'
        
        # Build image HTML if present
        img_html = ""
        if img_url:
            img_html = f'''<div style="flex-shrink:0; margin-right:16px;">
              <img src="{img_url}" alt="News Thumbnail" style="width:72px; height:72px; object-fit:cover; border-radius:4px; border:1px solid var(--border);">
            </div>'''
            
        items.append(f'''
      <div class="story-item">
        <div class="story-num">{i+1:02d}</div>
        <div class="story-content" style="display:flex; align-items:flex-start;">
          {img_html}
          <div style="flex:1;">
            <div class="story-tag">Macro</div>
            <div class="story-headline">{display_headline}</div>
            <div style="margin-top:6px; font-family:var(--sans); font-size:11px; font-style:italic; color:var(--dim); line-height:1.6;"><strong style="color:var(--gold); font-style:normal; font-size:10px; letter-spacing:.5px;">{ai_label}:</strong> {commentary}</div>
          </div>
        </div>
      </div>''')
    return '\n'.join(items)




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
            html_lines.append(f'<h5 style="color:#a1a1aa; font-size:12px; font-weight:600; margin:12px 0 6px;">{heading}</h5>')
            continue

        # List items
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul style="margin:4px 0; padding-left:20px;">')
                in_list = True
            item = stripped[2:]
            item = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#e6edf3;">\1</strong>', item)
            item = re.sub(r'`(.*?)`', r'<code style="background:rgba(232,197,71,0.1); padding:1px 5px; border-radius:3px; font-size:11px; color:var(--gold);">\1</code>', item)
            html_lines.append(f'<li style="margin-bottom:6px; font-size:12px; color:#a1a1aa; line-height:1.6;">{item}</li>')
            continue

        # Regular paragraph - close list if open
        if in_list:
            html_lines.append('</ul>')
            in_list = False

        # Bold + code + inline formatting
        p = stripped
        p = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#e6edf3;">\1</strong>', p)
        p = re.sub(r'`(.*?)`', r'<code style="background:rgba(232,197,71,0.1); padding:1px 5px; border-radius:3px; font-size:11px; color:var(--gold);">\1</code>', p)
        html_lines.append(f'<p style="margin:4px 0; font-size:12px; color:#a1a1aa; line-height:1.65;">{p}</p>')

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
      <span style="font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#a1a1aa;">{title}</span>
      {status_badge}
    </div>
    <div style="background:#161b22; border:1px solid rgba(255,255,255,.06); border-radius:10px; padding:20px 24px; position:relative; overflow:hidden;">
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
        
    ibit = etf.get('IBIT_flow_m')
    fbtc = etf.get('FBTC_flow_m')
    total = etf.get('Total_flow_m')
    if _na(ibit) or _na(fbtc) or _na(total):
        return ""  # incomplete real data → omit the section rather than invent values
    sentiment = etf.get('sentiment', 'Neutral')
    note = data.get('etf_note', '')
    
    ibit_cls = "up" if ibit >= 0 else "down"
    fbtc_cls = "up" if fbtc >= 0 else "down"
    total_cls = "up" if total >= 0 else "down"
    
    ibit_sign = "+" if ibit > 0 else ""
    fbtc_sign = "+" if fbtc > 0 else ""
    total_sign = "+" if total > 0 else ""
    
    badge_style = 'background:rgba(212,168,83,0.1); color:var(--amber); border:1px solid rgba(212,168,83,0.3);'
    if 'Inflow' in sentiment:
        badge_style = 'background:rgba(74,186,122,0.12); color:var(--green); border:1px solid rgba(74,186,122,0.3);'
    elif 'Outflow' in sentiment:
        badge_style = 'background:rgba(205,92,92,0.12); color:var(--red); border:1px solid rgba(205,92,92,0.3);'
    etf_date = etf.get('date', '')

    return f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div>
          <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">Spot Bitcoin ETF Flows</div>
          <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">{etf_date}</div>
        </div>
        <div style="font-family:var(--mono); font-size:9px; padding:3px 10px; border-radius:3px; font-weight:600; text-transform:uppercase; {badge_style}">{sentiment}</div>
      </div>
      <div style="display:flex; gap:28px; margin-bottom:12px;">
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">Total Flow</div>
          <div class="{total_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{total_sign}${total:.1f}m</div>
        </div>
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">IBIT (BlackRock)</div>
          <div class="{ibit_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{ibit_sign}${ibit:.1f}m</div>
        </div>
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">FBTC (Fidelity)</div>
          <div class="{fbtc_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{fbtc_sign}${fbtc:.1f}m</div>
        </div>
      </div>
      <div style="font-family:var(--sans); font-size:10px; color:var(--dim); font-style:italic; line-height:1.5;">
        {note}
      </div>
    </div>
    '''


def generate_newsletter_html(data, output_filename='daily_bulletin.html'):
    """
    Generate the complete newsletter HTML.
    data: dict with all data sections from data_fetcher.py
    """
    now = datetime.now()
    days_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months_en = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    day_name = days_en[now.weekday()]
    date_str = f"{day_name} · {now.day:02d} {months_en[now.month-1]} {now.year}"

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
            f"Looking at <strong>macro indicators</strong>, the <strong>VIX</strong> index is at "
            f"<span class='highlight'>{macro.get('VIX', 0):.1f}</span>, "
            f"<strong>DXY</strong> (Dollar Index) is trading at {macro.get('DXY', 0):.2f}. "
            f"The <strong>US 10-Year Treasury Yield</strong> stands at {macro.get('US 10-Year Treasury Yield', 0):.2f}%. "
            f"Crypto <strong>Fear &amp; Greed Index</strong> reads "
            f"<span class='highlight'>{fng.get('value', 0)}</span> ({fng.get('classification', 'N/A')}). "
            f"Total crypto <strong>market cap</strong> is ${crypto_ov.get('total_market_cap', 0)/1e12:.2f} Trillion, "
            f"<strong>BTC Dominance</strong> at {crypto_ov.get('btc_dominance', 0):.1f}%."
        )
        # Inject actuals from economic calendar if available
        for ev in data.get('economic_calendar', []):
            actual = ev.get('actual', '—')
            event_name = ev.get('event', '')
            forecast = ev.get('forecast', '—')
            previous = ev.get('previous', '—')
            if actual != '—':
                if 'CPI' in event_name or 'PCE' in event_name or 'PPI' in event_name:
                    summary_text += f" <strong>{event_name}</strong> came in at <strong>{actual}</strong> (vs est. {forecast}, prev. {previous})."
                elif 'Non-Farm' in event_name or 'Payroll' in event_name:
                    summary_text += f" <strong>US Non-Farm Payrolls</strong> came in at <strong>{actual}</strong> (vs est. {forecast}, prev. {previous})."
                elif 'Fed' in event_name or 'Interest Rate' in event_name or 'Funds Rate' in event_name:
                    summary_text += f" <strong>{event_name}</strong> decision was announced at <strong>{actual}</strong> (vs est. {forecast}, prev. {previous})."
            else:
                if 'CPI' in event_name or 'PPI' in event_name or 'PCE' in event_name or 'Fed' in event_name or 'Funds Rate' in event_name or 'Non-Farm' in event_name:
                    summary_text += f" <strong>{event_name}</strong> is expected at <strong>{forecast}</strong> (prev. {previous}) — to be released this week."

    korelasyon_notu = data.get('korelasyon_notu')
    if korelasyon_notu:
        summary_text += f"<br><br><strong style='color:var(--gold2);font-weight:600;'>Observation:</strong> <span style='font-style:italic;'>{korelasyon_notu}</span>"

    # ── Makro Scoreboard (Inline Bar) ──
    ms = data.get('macro_scoreboard', {})
    dxy = ms.get('DXY')
    dxy_chg = ms.get('DXY_chg')
    m2 = ms.get('M2')
    m2_chg = ms.get('M2_chg')
    pmi = ms.get('PMI')
    pmi_chg = ms.get('PMI_chg')

    dxy_chg_text, dxy_chg_cls = _fmt_change(dxy_chg)
    m2_chg_text, m2_chg_cls = _fmt_change(m2_chg)
    pmi_chg_text, pmi_chg_cls = _fmt_change(pmi_chg)
    # None-safe display (missing series render "—", never a fabricated 0)
    dxy_str = "—" if _na(dxy) else f"{dxy:.2f}"
    m2_str = "—" if _na(m2) else f"${m2:.1f}T"
    pmi_str = "—" if _na(pmi) else f"{pmi:.1f}"

    macro_scoreboard_html = f'''
    <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:11px 18px; margin-top:16px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-family:var(--sans); font-size:9px; color:var(--dim); text-transform:uppercase; font-weight:600; letter-spacing:1px;">DXY</span>
        <span style="font-family:var(--mono); font-size:13px; color:var(--text); font-weight:500;">{dxy_str}</span>
        <span class="{dxy_chg_cls}" style="font-size:11px;">{dxy_chg_text}</span>
      </div>
      <div style="width:1px; height:16px; background:var(--border);"></div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-family:var(--sans); font-size:9px; color:var(--dim); text-transform:uppercase; font-weight:600; letter-spacing:1px;">M2 Supply</span>
        <span style="font-family:var(--mono); font-size:13px; color:var(--text); font-weight:500;">{m2_str}</span>
        <span class="{m2_chg_cls}" style="font-size:11px;">{m2_chg_text}</span>
      </div>
      <div style="width:1px; height:16px; background:var(--border);"></div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-family:var(--sans); font-size:9px; color:var(--dim); text-transform:uppercase; font-weight:600; letter-spacing:1px;">US PMI</span>
        <span style="font-family:var(--mono); font-size:13px; color:var(--text); font-weight:500;">{pmi_str}</span>
        <span class="{pmi_chg_cls}" style="font-size:11px;">{pmi_chg_text}</span>
      </div>
    </div>
    '''

    # Build all sections
    ticker_bar = _generate_ticker_bar(data)
    econ_calendar = _generate_economic_calendar(data.get('economic_calendar', []))
    kpi_cards = _generate_kpi_cards(data)
    coinbase_premium = _generate_coinbase_premium(data)
    m2_supply_html = _generate_m2_money_supply(data)
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
            bg_color = 'rgba(74,186,122,.04)' if chg > 0 else ('rgba(205,92,92,.04)' if chg < 0 else 'rgba(255,255,255,.02)')
            border_color = 'rgba(74,186,122,.18)' if chg > 0 else ('rgba(205,92,92,.18)' if chg < 0 else 'var(--border)')
            sp500_rows_list.append(f'''
            <div style="background:{bg_color}; border:1px solid {border_color}; padding:7px 6px; text-align:center;">
                <div style="font-size:7.5px; color:#a1a1aa; letter-spacing:0.5px; margin-bottom:2px; text-transform:uppercase;">{name}</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:500; color:#c9d1d9; margin-bottom:2px;">{sym}</div>
                <div class="{chg_cls}" style="font-family:'JetBrains Mono',monospace; font-size:10px;">{chg:.2f}%</div>
            </div>''')
        sp500_rows = f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:8px;letter-spacing:1.5px;text-transform:uppercase;color:#a1a1aa">📊 S&P 500 Sectors</span>
          <div style="flex:1;height:0.5px;background:rgba(255,255,255,.06)"></div>
        </div>
        <div class="sp500-grid" style="margin-bottom:16px">
          {''.join(sp500_rows_list)}
        </div>
        '''

    news_stories = _generate_news_stories(data.get('macro_news', {}), data.get('news_commentaries'))

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

    stablecoin_data = data.get('stablecoin_data', {})
    stablecoin_dom = crypto_ov.get('stablecoin_dominance', 0)
    if stablecoin_data and stablecoin_data.get('success'):
        stablecoin_mcap = stablecoin_data.get('combined_mcap', 0.0)
        stablecoin_chg = stablecoin_data.get('change_24h_pct', 0.0)
        stablecoin_sub = f"Dom: %{stablecoin_dom:.1f} ({stablecoin_chg:+.2f}%)"
    else:
        stablecoin_mcap = crypto_ov.get('total_market_cap', 0) * (stablecoin_dom / 100) if stablecoin_dom else 0
        stablecoin_sub = f"Dom: %{stablecoin_dom:.1f}"

    # Global Liquidity
    gl = data.get('global_liquidity', {})
    gl_value = gl.get('value_formatted', 'N/A')
    gl_weekly = gl.get('weekly_change', 0)
    gl_weekly_text, gl_weekly_cls = _fmt_change(gl_weekly)

    extra_indicators = f'''
    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden;">
      <div style="background:var(--bg2); padding:14px 16px;">
        <div style="font-family:var(--sans); font-size:8px; font-weight:500; letter-spacing:1px; text-transform:uppercase; color:var(--dim); margin-bottom:6px;">2Y-10Y Spread</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--text);">{yield_spread:.2f}%</div>
        <div class="{spread_cls}" style="font-family:var(--mono); font-size:10px; margin-top:4px;">{spread_status}</div>
      </div>
      <div style="background:var(--bg2); padding:14px 16px;">
        <div style="font-family:var(--sans); font-size:8px; font-weight:500; letter-spacing:1px; text-transform:uppercase; color:var(--dim); margin-bottom:6px;">Fed Balance Sheet</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--text);">{gl_value}</div>
        <div class="{gl_weekly_cls}" style="font-family:var(--mono); font-size:10px; margin-top:4px;">W: {gl_weekly_text}</div>
      </div>
      <div style="background:var(--bg2); padding:14px 16px;">
        <div style="font-family:var(--sans); font-size:8px; font-weight:500; letter-spacing:1px; text-transform:uppercase; color:var(--dim); margin-bottom:6px;">Stablecoin Mcap</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--text);">${stablecoin_mcap/1e9:.1f}B</div>
        <div style="font-family:var(--mono); font-size:10px; margin-top:4px; color:var(--dim);">{stablecoin_sub}</div>
      </div>
      <div style="background:var(--bg2); padding:14px 16px;">
        <div style="font-family:var(--sans); font-size:8px; font-weight:500; letter-spacing:1px; text-transform:uppercase; color:var(--dim); margin-bottom:6px;">SMH (Semi ETF)</div>
        <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--text);">${smh_price:,.2f}</div>
        <div class="{smh_chg_cls}" style="font-family:var(--mono); font-size:10px; margin-top:4px;">{smh_chg_text}</div>
      </div>
    </div>
    '''
    indicators_fallback = "A negative 2Y-10Y spread signals recession risk. Rising Fed Balance Sheet indicates expanding global liquidity. SMH serves as a barometer for AI and the semiconductor sector."
    indicators_note = data.get('indicators_note') or indicators_fallback
    extra_indicators += f'''
    <div style="margin-top:12px; font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.5;">
      <strong style="color:var(--gold2);">Note:</strong>
      {indicators_note}
    </div>'''

    # ── BIST 100 & TRY/USD ──
    bist_data = data.get('bist_try', {})
    bist_val = f"{bist_data.get('bist100', 0):,.0f}" if bist_data.get('bist100', 0) else '—'
    bist_chg = bist_data.get('bist100_chg', 0)
    bist_chg_text, bist_cls = _fmt_change(bist_chg)
    usd_try = bist_data.get('usd_try', 0)
    usd_try_val = f"{usd_try:.2f}" if usd_try else '—'
    try_chg = bist_data.get('try_chg', 0)
    try_chg_text, try_cls = _fmt_change(try_chg)

    # ── FUNDING RATES ──
    fr = data.get('funding_rates', {})
    def fmt_fr(val):
        if val is None: return '—', 'neu'
        s = f"{val:+.4f}%"
        cls = 'up' if val > 0 else ('down' if val < 0 else 'neu')
        return s, cls
    btc_fr_str, btc_fr_cls = fmt_fr(fr.get('BTC'))
    eth_fr_str, eth_fr_cls = fmt_fr(fr.get('ETH'))
    sol_fr_str, sol_fr_cls = fmt_fr(fr.get('SOL'))

    # ── OPEN INTEREST ──
    oi = data.get('open_interest', {})
    def fmt_oi(val, chg):
        if not val: return '—', '—', 'neu'
        v_str = f"{val/1000:.1f}K" if val < 1e6 else f"{val/1e6:.2f}M"
        chg_str, cls = _fmt_change(chg)
        return v_str, chg_str, cls
    btc_oi_str, btc_oi_chg_str, btc_oi_chg_cls = fmt_oi(oi.get('BTC', {}).get('oi'), oi.get('BTC', {}).get('oi_chg_24h'))
    eth_oi_str, eth_oi_chg_str, eth_oi_chg_cls = fmt_oi(oi.get('ETH', {}).get('oi'), oi.get('ETH', {}).get('oi_chg_24h'))
    sol_oi_str, sol_oi_chg_str, sol_oi_chg_cls = fmt_oi(oi.get('SOL', {}).get('oi'), oi.get('SOL', {}).get('oi_chg_24h'))

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
            btc_analysis = f"Price at <strong>${btc_price:,.0f}</strong> is trading above <strong>resistance</strong> (${btc_resistance:,.0f}) — upward momentum may continue."
            btc_status_color = '#4aba7a'
        elif btc_price < btc_support:
            btc_analysis = f"Price at <strong>${btc_price:,.0f}</strong> has broken below <strong>support</strong> (${btc_support:,.0f}) — short-term selling pressure may persist."
            btc_status_color = '#cd5c5c'
        else:
            btc_analysis = f"Price at <strong>${btc_price:,.0f}</strong> is holding above <strong>support</strong> (${btc_support:,.0f}), with <strong>resistance</strong> at ${btc_resistance:,.0f}."
            btc_status_color = 'var(--gold)'
    else:
        btc_analysis = 'BTC price data unavailable.'
        btc_status_color = 'var(--mid)'

    btc_chg_text, btc_chg_cls = _fmt_change(btc_chg_24h)
    btc_status_html = f'''
    <div class="sparkline-wrap" style="padding:20px 24px; page-break-inside: avoid; break-inside: avoid;">
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px;">
        <tr>
          <td valign="middle" style="vertical-align:middle;">
            <table cellpadding="0" cellspacing="0"><tr>
              <td style="font-family:var(--mono); font-size:22px; font-weight:600; color:var(--text); padding-right:12px;">${btc_price:,.0f}</td>
              <td class="{btc_chg_cls}" style="font-family:var(--mono); font-size:13px;">{btc_chg_text}</td>
            </tr></table>
          </td>
          <td valign="middle" style="vertical-align:middle; text-align:right;">
            <table cellpadding="0" cellspacing="0" style="display:inline-block; font-family:var(--sans); font-size:11px;">
              <tr>
                <td style="padding-right:24px; text-align:center;"><div style="color:var(--dim); margin-bottom:3px;">Support Level</div><div style="font-family:var(--mono); color:var(--green); font-size:13px;">${btc_support:,.0f}</div></td>
                <td style="text-align:center;"><div style="color:var(--dim); margin-bottom:3px;">Resistance Level</div><div style="font-family:var(--mono); color:var(--red); font-size:13px;">${btc_resistance:,.0f}</div></td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
      <div style="padding:10px 14px; background:var(--bg3); border-left:3px solid {btc_status_color}; border-radius:0 4px 4px 0; font-family:var(--sans); font-size:12px; color:var(--dim); line-height:1.65;">
        {btc_analysis}
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
        'Strong Bullish': 'background:rgba(74,186,122,0.12); color:var(--green); border:1px solid rgba(74,186,122,0.3);',
        'Bullish': 'background:rgba(74,186,122,0.08); color:var(--green); border:1px solid rgba(74,186,122,0.2);',
        'Neutral': 'background:rgba(212,168,83,0.1); color:var(--amber); border:1px solid rgba(212,168,83,0.25);',
        'Bearish': 'background:rgba(205,92,92,0.08); color:var(--red); border:1px solid rgba(205,92,92,0.2);',
        'Strong Bearish': 'background:rgba(205,92,92,0.12); color:var(--red); border:1px solid rgba(205,92,92,0.3);',
    }
    fb_badge_style = fb_badges.get(fb_sen, fb_badges['Neutral'])
    
    basis_html = f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">Annualized Futures Premium</div>
        <div style="font-family:var(--mono); font-size:9px; padding:3px 10px; border-radius:3px; font-weight:600; text-transform:uppercase; {fb_badge_style}">{fb_sen}</div>
      </div>
      <div style="display:flex; gap:28px; margin-bottom:12px;">
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">BTC Basis</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:600; color:var(--text);">{fb_btc:.1f}%</div>
        </div>
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">ETH Basis</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:600; color:var(--text);">{fb_eth:.1f}%</div>
        </div>
      </div>
      <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.6;">
        {data.get('futures_note') or fb_desc}
      </div>
    </div>
    '''

    # ================= CSS STYLES =================
    # CSS Variables are replaced manually at the end for email client compatibility
    css_styles = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1c2026;color:var(--text);font-family:var(--sans);-webkit-font-smoothing:antialiased;font-size:13px;line-height:1.6}
.bul{max-width:720px;margin:0 auto;background:var(--bg);border-left:1px solid rgba(0,0,0,0.3);border-right:1px solid rgba(0,0,0,0.3);box-shadow:0 0 30px rgba(0,0,0,0.6)}

/* ── HEADER ── */
.hdr{background:var(--bg3);border-bottom:1px solid var(--border2);padding:20px 28px;display:flex;justify-content:space-between;align-items:center}
.hdr-logo{font-family:var(--serif);font-size:22px;font-weight:400;color:var(--text);letter-spacing:.3px}
.hdr-logo span{color:var(--gold)}
.hdr-date{font-family:var(--mono);font-size:10px;color:var(--dim);letter-spacing:.5px;text-align:right}
.hdr-ed{font-family:var(--sans);font-size:9px;color:var(--gold2);letter-spacing:1.5px;text-transform:uppercase;margin-top:4px;font-weight:500}

/* ── TICKER ── */
.ticker{background:var(--bg2);border-bottom:1px solid var(--border);width:100%;border-collapse:collapse;table-layout:fixed}
.ti{padding:10px 4px;border-right:1px solid var(--border);text-align:center;}
.ti:last-child{border-right:none}
.ti-name{font-family:var(--mono);font-size:8px;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-bottom:2px;}
.ti-val{font-family:var(--mono);font-size:12px;color:var(--text);font-weight:500}
.ti-chg{font-family:var(--mono);font-size:9px}
.up,.heatmap-table td.up{color:var(--green);font-weight:500}
.down,.heatmap-table td.down{color:var(--red);font-weight:500}
.neu,.heatmap-table td.neu{color:var(--dim)}

/* ── SECTION ── */
.section{padding:32px 28px;border-bottom:1px solid var(--border); page-break-inside: avoid; break-inside: avoid;}
.section-label{font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:1.8px;color:var(--gold);text-transform:uppercase;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid rgba(201,169,110,.15);display:block}

/* ── SUMMARY ── */
.summary-card{background:var(--bg2);border-left:3px solid var(--gold);padding:16px 20px;border-radius:0 4px 4px 0}
.summary-text{font-family:var(--sans);font-size:13px;line-height:1.85;color:var(--dim)}
.summary-text strong{color:var(--text);font-weight:600}
.summary-text .highlight{color:var(--gold);font-weight:600}
.obs{background:var(--bg2);border-left:2px solid var(--amber);padding:10px 14px;margin-top:10px;font-family:var(--sans);font-size:11px;color:var(--dim);line-height:1.7}
.obs-lbl{color:var(--amber);font-family:var(--mono);font-size:8px;letter-spacing:1px;font-weight:700;margin-right:6px}

/* ── SCOREBOARD ── */
.scores{display:flex;background:var(--bg2);border:1px solid var(--border);border-radius:4px;overflow:hidden;margin-top:14px}
.score{flex:1;padding:11px 14px;border-right:1px solid var(--border);text-align:center}
.score:last-child{border-right:none}
.score-lbl{font-family:var(--mono);font-size:8px;letter-spacing:1px;color:var(--dim);text-transform:uppercase;margin-bottom:4px}
.score-val{font-family:var(--mono);font-size:15px;color:var(--text);font-weight:600}
.score-chg{font-family:var(--mono);font-size:9px;margin-top:3px}

/* ── KPI GRID ── */
.kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;background:transparent;border-radius:4px;overflow:hidden}
.kpi-card{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:16px 18px;transition:background .2s ease}
.kpi-card:hover{background:var(--bg3)}
.kpi-label{font-family:var(--sans);font-size:9px;font-weight:500;letter-spacing:1px;color:var(--dim);text-transform:uppercase;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi-value{font-family:var(--mono);font-size:24px;font-weight:600;color:var(--text);letter-spacing:-.5px;line-height:1.1}
.kpi-change{font-family:var(--mono);font-size:9px;margin-top:5px}

/* ── IND GRID ── */
.ind-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--border);border-radius:4px;overflow:hidden}
.ind{background:var(--bg2);padding:14px 16px}
.ind-lbl{font-family:var(--sans);font-size:8px;font-weight:500;letter-spacing:1px;color:var(--dim);text-transform:uppercase;margin-bottom:5px}
.ind-val{font-family:var(--mono);font-size:16px;color:var(--text);font-weight:600}
.ind-chg{font-family:var(--mono);font-size:9px;margin-top:4px}

/* ── BIST/TRY PANEL ── */
.bist-panel{display:flex;background:var(--bg2);border:1px solid var(--border);border-radius:4px;overflow:hidden;margin-top:12px}
.bist-item{flex:1;padding:14px 18px;border-right:1px solid var(--border);text-align:center}
.bist-item:last-child{border-right:none}
.bist-lbl{font-family:var(--sans);font-size:8px;font-weight:500;letter-spacing:1px;color:var(--dim);text-transform:uppercase;margin-bottom:6px}
.bist-val{font-family:var(--mono);font-size:20px;color:var(--text);font-weight:600}
.bist-flag{font-family:var(--mono);font-size:9px;color:var(--dim);margin-top:4px;letter-spacing:.5px}

/* ── FUNDING RATES ── */
.funding-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--border);border-radius:4px;overflow:hidden;margin-top:10px}
.funding-item{background:var(--bg2);padding:14px 16px;text-align:center}
.funding-sym{font-family:var(--mono);font-size:9px;letter-spacing:1px;color:var(--dim);text-transform:uppercase;margin-bottom:6px}
.funding-val{font-family:var(--mono);font-size:18px;font-weight:600}
.funding-lbl{font-family:var(--sans);font-size:9px;color:var(--dim);margin-top:4px}

/* ── OI TABLE ── */
.oi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--border);border-radius:4px;overflow:hidden;margin-top:10px}
.oi-item{background:var(--bg2);padding:14px 16px;text-align:center}
.oi-sym{font-family:var(--mono);font-size:9px;letter-spacing:1px;color:var(--dim);text-transform:uppercase;margin-bottom:6px}
.oi-val{font-family:var(--mono);font-size:16px;color:var(--text);font-weight:600}
.oi-chg{font-family:var(--mono);font-size:9px;margin-top:4px}

/* ── CALENDAR ── */
.econ-calendar{width:100%;border-collapse:collapse;table-layout:fixed}
.econ-calendar th{font-family:var(--sans);font-size:9px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;color:var(--gold2);padding:12px 14px;text-align:left;border-bottom:1px solid var(--border2);background:var(--bg2)}
.econ-calendar th:nth-child(n+5){text-align:right}
.econ-calendar td{padding:12px 14px;font-family:var(--mono);font-size:10px;border-bottom:1px solid var(--border);color:var(--dim);vertical-align:middle}
.econ-calendar td:nth-child(n+5){text-align:right;font-size:10px}
.econ-calendar tr:last-child td{border-bottom:none}
.econ-calendar tbody tr:nth-child(even){background:rgba(255,255,255,.015)}
.econ-calendar tbody tr:hover{background:rgba(201,169,110,.04)}

/* ── HEATMAP TABLE ── */
.heatmap-table{width:100%;border-collapse:collapse;table-layout:fixed;font-variant-numeric:tabular-nums}
.heatmap-table th{font-family:var(--sans);font-size:9px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;color:var(--gold2);padding:16px 20px;text-align:right;border-bottom:1px solid var(--border2);background:var(--bg2);white-space:nowrap}
.heatmap-table th:first-child{text-align:left}
.heatmap-table td{padding:16px 20px;font-family:var(--mono);font-size:11px;border-bottom:1px solid var(--border);vertical-align:middle;text-align:right;color:var(--dim);white-space:nowrap}
.heatmap-table td:first-child{text-align:left;color:var(--text);font-weight:600;font-family:var(--sans);font-size:13px}
.heatmap-table td:nth-child(2){color:var(--text);font-weight:500}
.heatmap-table tr:last-child td{border-bottom:none}
.heatmap-table tbody tr:nth-child(even){background:rgba(255,255,255,.015)}
.heatmap-table tbody tr:hover{background:rgba(201,169,110,.04)}
.asset-name{display:flex;align-items:center;gap:7px}
.asset-dot{width:4px;height:4px;border-radius:0;background:var(--gold);flex-shrink:0}
.mono{font-family:var(--mono);font-size:11px;font-variant-numeric:tabular-nums}
.cell-bar{display:flex;align-items:center;gap:5px;justify-content:flex-end}
.cell-mini-bar{width:48px;height:3px;background:rgba(255,255,255,.06);overflow:hidden;border-radius:1px}
.cell-mini-fill{height:100%;border-radius:1px}
.cell-mini-fill.pos{background:var(--green)}
.cell-mini-fill.neg{background:var(--red)}
.cell-mini-fill.overbought{background:var(--amber)}

/* ── SP500 GRID ── */
.sp500-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:2px}
.sp500-tile{background:var(--bg2);border:1px solid var(--border);padding:8px 6px;text-align:center;border-radius:2px;transition:background .15s}
.sp500-tile.pos{border-color:rgba(74,186,122,.18);background:rgba(74,186,122,.04)}
.sp500-tile.neg{border-color:rgba(205,92,92,.18);background:rgba(205,92,92,.04)}
.sp500-name{font-family:var(--mono);font-size:8px;color:var(--dim);letter-spacing:.5px;margin-bottom:2px}
.sp500-sym{font-family:var(--mono);font-size:10px;font-weight:600;color:var(--text);margin-bottom:2px}

/* ── COINBASE PREMIUM / DATA BOX ── */
.sparkline-wrap{background:var(--bg2);border:1px solid var(--border);padding:18px 22px;border-radius:4px}
.data-box{background:var(--bg2);border:1px solid var(--border);padding:18px 20px;border-radius:4px}
.data-box-hd{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.data-box-title{font-family:var(--sans);font-size:13px;color:var(--text);font-weight:600}
.badge{font-family:var(--mono);font-size:9px;padding:3px 10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;border-radius:3px}
.badge-green{background:rgba(74,186,122,.1);color:var(--green);border:1px solid rgba(74,186,122,.25)}
.badge-red{background:rgba(205,92,92,.1);color:var(--red);border:1px solid rgba(205,92,92,.25)}
.badge-amber{background:rgba(212,168,83,.1);color:var(--amber);border:1px solid rgba(212,168,83,.25)}
.data-metrics{display:flex;gap:28px;margin-bottom:12px}
.data-metric-lbl{font-family:var(--sans);font-size:9px;font-weight:500;text-transform:uppercase;color:var(--dim);letter-spacing:1px;margin-bottom:4px}
.data-metric-val{font-family:var(--mono);font-size:17px;font-weight:600;color:var(--text)}
.data-note{font-family:var(--sans);font-size:11px;color:var(--dim);line-height:1.65}

/* ── NEWS STORIES ── */
.story-list{display:flex;flex-direction:column;gap:0}
.story-item{padding:16px 0;border-bottom:1px solid var(--border)}
.story-item:last-child{border-bottom:none;padding-bottom:0}
.story-inner{display:flex;gap:14px}
.story-num{font-family:var(--mono);font-size:10px;color:var(--gold2);width:20px;flex-shrink:0;padding-top:2px}
.story-tag{font-family:var(--sans);font-size:8px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--gold);margin-bottom:5px}
.story-headline{font-family:var(--serif);font-size:16px;font-weight:700;color:var(--text);line-height:1.4;margin-bottom:8px}
.story-insight{background:var(--bg3);border-left:2px solid var(--gold);padding:8px 14px;margin-top:8px;font-family:var(--sans);font-size:11px;color:var(--dim);line-height:1.65;border-radius:0 3px 3px 0}
.ins-lbl{color:var(--gold);font-family:var(--mono);font-size:8px;letter-spacing:1px;font-weight:600;margin-right:5px}

/* ── FOOTER ── */
.footer{background:var(--bg3);border-top:1px solid var(--border2);padding:16px 28px;display:flex;justify-content:space-between;align-items:center}
.footer-brand{font-family:var(--serif);font-size:13px;color:var(--dim);letter-spacing:.3px}
.footer-brand span{color:var(--gold)}
.footer-disc{background:var(--bg);border-top:1px solid var(--border);padding:14px 28px 18px;font-family:var(--sans);font-size:9px;color:var(--faint);text-align:center;line-height:1.7;letter-spacing:.2px}

/* ── SUB HEADER ── */
.sub-hd{display:flex;align-items:center;gap:8px;margin:16px 0 10px}
.sub-hd-txt{font-family:var(--sans);font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--gold2)}
.sub-hd-line{flex:1;height:1px;background:var(--border)}

@media(max-width:540px){
  .hdr,.section,.footer{padding-left:14px;padding-right:14px}
  .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .ind-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .scores{flex-wrap:wrap}
  .score{flex:1 1 45%}
}

    """

    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Financial Bulletin — nocashflow.net</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{css_styles}
</style>
</head>
<body>
<div class="bul">

  <!-- HEADER -->
  <div class="hdr">
    <div>
      <div class="hdr-logo">nocashflow<span>.net</span></div>
    </div>
    <div>
      <div class="hdr-date">{date_str} · {now.strftime('%H:%M')} CET</div>
      <div class="hdr-ed">Daily Financial Bulletin</div>
    </div>
  </div>

  <!-- TICKER BAR -->
  {ticker_bar}

  <!-- GENEL DEĞERLENDİRME -->
  <div class="section">
    <div class="section-label">Market Overview</div>
    <div class="summary-card">
      <p class="summary-text">{summary_text}</p>
    </div>
    {macro_scoreboard_html}
  </div>

  <!-- WEEKLY ECONOMIC CALENDAR -->
  <div class="section">
    <div class="section-label">Weekly Economic Calendar</div>
    <div style="margin-bottom:10px"><span style="background:var(--red);color:#fff;font-size:8px;padding:3px 10px;letter-spacing:1px;border-radius:2px;font-family:var(--sans);font-weight:600">★★★ HIGH IMPACT</span></div>
    <table class="econ-calendar">
      <colgroup>
        <col style="width:13%"><col style="width:10%"><col style="width:32%">
        <col style="width:10%"><col style="width:11%"><col style="width:11%"><col style="width:13%">
      </colgroup>
      <thead>
        <tr><th>Day</th><th>Time</th><th>Event</th><th>CCY</th><th>Prev.</th><th>Est.</th><th>Actual</th></tr>
      </thead>
      <tbody>{econ_calendar}</tbody>
    </table>
  </div>

  <!-- TODAY'S KEY DATA (includes Turkey Markets) -->
  <div class="section">
    <div class="section-label">Today's Key Data</div>
    <div class="kpi-grid">{kpi_cards}
      <div class="kpi-card">
        <div class="kpi-label">BIST 100</div>
        <div class="kpi-value">{bist_val}</div>
        <div class="kpi-change {bist_cls}">{bist_chg_text}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">USD/TRY</div>
        <div class="kpi-value">{usd_try_val}</div>
        <div class="kpi-change {try_cls}">{try_chg_text}</div>
      </div>
    </div>
  </div>

  <!-- ADDITIONAL INDICATORS -->
  <div class="section">
    <div class="section-label">Additional Indicators</div>
    {extra_indicators}
    <div style="margin-top:18px">{sp500_rows}</div>
  </div>

  <!-- FUNDING RATES & OPEN INTEREST -->
  <div class="section">
    <div class="section-label">Funding Rates & Open Interest</div>
    <div style="font-family:var(--sans);font-size:9px;color:var(--dim);margin-bottom:8px;letter-spacing:.5px">Binance Perpetual · Live</div>
    <div class="funding-grid">
      <div class="funding-item">
        <div class="funding-sym">BTC</div>
        <div class="funding-val {btc_fr_cls}">{btc_fr_str}</div>
        <div class="funding-lbl">8h Funding</div>
      </div>
      <div class="funding-item">
        <div class="funding-sym">ETH</div>
        <div class="funding-val {eth_fr_cls}">{eth_fr_str}</div>
        <div class="funding-lbl">8h Funding</div>
      </div>
      <div class="funding-item">
        <div class="funding-sym">SOL</div>
        <div class="funding-val {sol_fr_cls}">{sol_fr_str}</div>
        <div class="funding-lbl">8h Funding</div>
      </div>
    </div>
    <div class="oi-grid">
      <div class="oi-item">
        <div class="oi-sym">BTC OI</div>
        <div class="oi-val">{btc_oi_str}</div>
        <div class="oi-chg {btc_oi_chg_cls}">{btc_oi_chg_str}</div>
      </div>
      <div class="oi-item">
        <div class="oi-sym">ETH OI</div>
        <div class="oi-val">{eth_oi_str}</div>
        <div class="oi-chg {eth_oi_chg_cls}">{eth_oi_chg_str}</div>
      </div>
      <div class="oi-item">
        <div class="oi-sym">SOL OI</div>
        <div class="oi-val">{sol_oi_str}</div>
        <div class="oi-chg {sol_oi_chg_cls}">{sol_oi_chg_str}</div>
      </div>
    </div>
    <div style="margin-top:12px; padding:10px 14px; background:var(--bg3); border:1px solid var(--border); border-radius:4px; font-family:var(--sans); font-size:10px; color:var(--dim); line-height:1.7;">
      <strong style="color:var(--gold2);">How to read:</strong> Funding rates are periodic payments between long and short traders in perpetual futures. <strong style="color:var(--text);">Positive rates</strong> mean longs pay shorts (bullish crowding — market is overleveraged long). <strong style="color:var(--text);">Negative rates</strong> mean shorts pay longs (bearish pressure — market is overleveraged short). Rates above ±0.03% are considered elevated. <strong style="color:var(--text);">Open Interest (OI)</strong> shows total outstanding contracts — rising OI with rising price confirms trend strength, while rising OI with falling price signals growing short pressure.
    </div>
  </div>

  <!-- COINBASE PREMIUM -->
  <div class="section">
    <div class="section-label" style="text-transform: none;">COINBASE PREMIUM INDEX — 7D</div>
    {coinbase_premium}
  </div>

  <div class="section">
    <div class="section-label">Macro Liquidity</div>
    {m2_supply_html}
  </div>

  <!-- BTC ANALYSIS & ETF FLOWS -->
  <div class="section">
    <div class="section-label">BTC Analysis & ETF Flows</div>
    {btc_status_html}
    <div style="margin-top:16px">{_generate_etf_flows(data)}</div>
    <div style="margin-top:6px; font-family:var(--sans); font-size:9px; color:var(--dim); font-style:italic;">Daily net flows · ETF markets operate Mon–Fri; no weekend trading.</div>
  </div>

  <!-- CRYPTO FUTURES BASIS -->
  <div class="section">
    <div class="section-label">Crypto Futures Basis</div>
    {basis_html}
  </div>

  <!-- ASSET SUMMARY -->
  <div class="section">
    <div class="section-label">Asset Summary</div>

    <div class="sub-hd"><div class="sub-hd-txt">🪙 Commodities</div><div class="sub-hd-line"></div></div>
    <table class="heatmap-table" style="margin-bottom:16px">
      <thead><tr><th>Asset</th><th>Price</th><th>1D</th><th>1W</th><th>30D</th><th style="width:80px">Momentum</th></tr></thead>
      <tbody>{commodity_rows}</tbody>
    </table>

    <div class="sub-hd"><div class="sub-hd-txt">📊 Magnificent 7</div><div class="sub-hd-line"></div></div>
    <table class="heatmap-table" style="margin-bottom:16px">
      <thead><tr><th>Asset</th><th>Price</th><th>1D</th><th>1W</th><th>30D</th><th style="width:80px">Momentum</th></tr></thead>
      <tbody>{mag7_rows}</tbody>
    </table>

    <div class="sub-hd"><div class="sub-hd-txt">₿ Crypto Watchlist</div><div class="sub-hd-line"></div></div>
    <table class="heatmap-table" style="margin-bottom:16px">
      <thead><tr><th>Asset</th><th>Price</th><th>24h</th><th>7D</th><th>30D</th><th style="width:80px">Momentum</th></tr></thead>
      <tbody>{crypto_rows}</tbody>
    </table>

    <div style="margin-top:8px;font-family:var(--sans);font-size:9px;color:var(--dim);font-style:italic">Momentum &gt; 70: overbought · Momentum &lt; 30: oversold</div>
  </div>



  <!-- TOP STORIES -->
  <div class="section">
    <div class="section-label">Top Stories</div>
    <div class="story-list">{news_stories}</div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-brand">nocashflow<span>.net</span> · orkun biçen</div>
    <div style="font-family:var(--mono);font-size:9px;color:var(--dim)">{date_str}</div>
  </div>
  <div class="footer-disc">
    This bulletin is for informational purposes only and does not constitute investment advice. Past performance is not indicative of future results. © {now.year} Orkun Biçen. All rights reserved.
  </div>

</div>
</body>
</html>'''

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html)
        
    html_color_map = {
        'var(--bg)': '#0f1114',
        'var(--bg2)': '#161a1e',
        'var(--bg3)': '#1c2127',
        'var(--bg4)': '#22272e',
        'var(--border)': 'rgba(255,255,255,.07)',
        'var(--border2)': 'rgba(255,255,255,.12)',
        'var(--gold)': '#c9a96e',
        'var(--gold2)': '#a08550',
        'var(--green)': '#4aba7a',
        'var(--red)': '#cd5c5c',
        'var(--amber)': '#d4a853',
        'var(--cyan)': '#7aafcf',
        'var(--text)': '#e8e4df',
        'var(--dim)': '#9a9590',
        'var(--mid)': '#6a6f7a',
        'var(--faint)': '#2a2d31', 
        'var(--ink)': '#111317',
        'var(--mono)': "'JetBrains Mono', monospace",
        'var(--serif)': "'DM Serif Display', Georgia, serif",
        'var(--sans)': "'Inter', system-ui, sans-serif",
    }
    for old, new in html_color_map.items():
        html = html.replace(old, new)
        
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  ✅ HTML generated: {os.path.abspath(output_filename)}")
    return output_filename


if __name__ == "__main__":
    # Test için mock data
    mock_data = {
        'crypto_prices': [
            {'Name': 'Bitcoin', 'Symbol': 'BTC', 'Current Price USD': 68500.20, '24h %': 2.5, '7d %': 5.1, '30d %': 12.4},
            {'Name': 'Ethereum', 'Symbol': 'ETH', 'Current Price USD': 3450.15, '24h %': -1.2, '7d %': 3.2, '30d %': 8.5},
            {'Name': 'Solana', 'Symbol': 'SOL', 'Current Price USD': 145.50, '24h %': 4.3, '7d %': 15.2, '30d %': 25.1},
        ],
        'crypto_market_overview': {
            'total_market_cap': 2.65e12,
            'btc_dominance': 53.2,
            'stablecoin_dominance': 6.5
        },
        'macro_indicators': {
            'VIX': 14.2,
            'VIX_chg': -2.1,
            'DXY': 103.45,
            'DXY_chg': 0.15,
            'US 10-Year Treasury Yield': 4.12,
            'US 10-Year Treasury Yield_chg': 0.02,
            'US 2-Year Treasury Yield': 4.45,
            'NASDAQ 100 Futures': 18245.50,
            'NASDAQ 100 Futures_chg': 0.85,
            'SMH (Semiconductor ETF)': 225.40,
            'SMH (Semiconductor ETF)_chg': 1.25
        },
        'macro_scoreboard': {
            'DXY': 103.45, 'DXY_chg': 0.15,
            'M2': 21.0, 'M2_chg': 0.05,
            'PMI': 50.2, 'PMI_chg': -0.3
        },
        'magnificent_7': [
            {'Name': 'NVIDIA', 'Symbol': 'NVDA', 'Price': 875.20, 'Change %': 3.5},
            {'Name': 'Apple', 'Symbol': 'AAPL', 'Price': 175.10, 'Change %': -0.5},
        ],
        'commodities': [
            {'Name': 'Gold', 'Price': 2165.40, 'Change %': 0.45},
            {'Name': 'Silver', 'Price': 24.50, 'Change %': 1.1},
        ],
        'fear_and_greed': {'value': 72, 'classification': 'Greed'},
        'economic_calendar': [
            {'date': '18 Mar', 'time': '15:30', 'event': 'US Core CPI', 'country': 'USA', 'previous': '3.1%', 'forecast': '3.0%', 'actual': '3.0%'},
        ],
        'macro_news': {
            'news': [
                {'title': 'Fed signals caution on interest rate cuts', 'image_url': ''},
                {'title': 'Bitcoin reaches new heights amid ETF inflows', 'image_url': ''},
            ]
        },
        'options_data': {
            'dvol_index': 58.2, 'dvol_change_24h': 2.1,
            'put_call_ratio': 0.85, 'open_interest_btc': 450000
        },
        'sp500_sectors': [
            {'Name': 'Technology', 'Symbol': 'XLK', 'Change %': 1.2},
            {'Name': 'Energy', 'Symbol': 'XLE', 'Change %': -0.8},
        ]
    }
    
    print("Standalone test mode: Generating 'design_preview_yeni.html'...")
    generate_newsletter_html(mock_data, output_filename='/tmp/design_preview_yeni.html')
