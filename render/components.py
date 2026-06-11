# render/components.py
from datetime import datetime
from render.tokens import STYLE_TOKENS, CSS_VARIABLES
from render.svg import (
    generate_sparkline, generate_fear_greed_gauge_svg,
    generate_coinbase_premium_chart, generate_etf_flow_chart,
    generate_winners_losers_chart, generate_correlation_matrix_svg,
    generate_cycle_heatmap_svg, generate_net_liquidity_chart,
    generate_inflation_chart
)

def _na(v):
    return v is None or (isinstance(v, float) and v != v)

def _fmt_price(price, fmt="price2"):
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
    if _na(val):
        return "—", ""
    sign = "+" if val >= 0 else ""
    cls = "up" if val >= 0 else "down"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {sign}{val:.2f}%", cls

def html_wrapper(title, content, accent_color="#3b82f6"):
    """Wrap content in base HTML template with CSS styling."""
    return f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
  <style>
    {CSS_VARIABLES}
    
    body {{
        background-color: var(--bg);
        color: var(--text);
        font-family: var(--sans);
        margin: 0;
        padding: 0;
        -webkit-font-smoothing: antialiased;
    }}
    
    .container {{
        max-width: 680px;
        margin: 0 auto;
        padding: 24px 16px;
    }}
    
    /* Layout components */
    .card-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }}
    @media (max-width: 500px) {{
        .card-grid {{
            grid-template-columns: repeat(2, 1fr);
        }}
    }}
    
    .kpi-card {{
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 14px 16px;
        position: relative;
    }}
    
    .kpi-label {{
        font-size: 10px;
        font-weight: 500;
        text-transform: uppercase;
        color: var(--dim);
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }}
    
    .kpi-value {{
        font-family: var(--mono);
        font-size: 18px;
        font-weight: 700;
        color: var(--text);
    }}
    
    .kpi-change {{
        font-family: var(--mono);
        font-size: 11px;
        margin-top: 4px;
    }}
    
    .up {{ color: var(--green); }}
    .down {{ color: var(--red); }}
    
    /* Tables */
    table.data-table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }}
    
    table.data-table th {{
        text-align: left;
        padding: 8px 12px;
        font-size: 10px;
        text-transform: uppercase;
        color: var(--dim);
        border-bottom: 1px solid var(--border);
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
    
    table.data-table td {{
        padding: 10px 12px;
        font-size: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        vertical-align: middle;
    }}
    
    .mono {{
        font-family: var(--mono);
    }}
    
    /* Section dividers */
    .section-divider {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 32px 0 16px 0;
    }}
    
    .section-title {{
        font-family: var(--serif);
        font-size: 18px;
        font-weight: 600;
        color: var(--text);
    }}
    
    .section-line {{
        flex: 1;
        height: 1px;
        background: var(--border);
    }}
    
    /* Ticker bar */
    table.ticker {{
        width: 100%;
        margin-bottom: 24px;
        border-collapse: collapse;
    }}
    
    .ti {{
        background: var(--bg2);
        border: 1px solid var(--border);
        padding: 8px 10px;
        text-align: center;
        width: 12.5%;
    }}
    
    .ti-name {{
        font-size: 8.5px;
        color: var(--dim);
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 3px;
        letter-spacing: 0.5px;
    }}
    
    .ti-val {{
        font-family: var(--mono);
        font-size: 12px;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 2px;
    }}
    
    .ti-chg {{
        font-family: var(--mono);
        font-size: 9px;
    }}
    
    /* S&P Grid */
    .sp500-grid {{
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 6px;
    }}
    @media (max-width: 600px) {{
        .sp500-grid {{
            grid-template-columns: repeat(3, 1fr);
        }}
    }}
    
    /* Sparkline wrapper */
    .sparkline-wrap {{
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 20px;
    }}
    
    .asset-dot {{
        width: 6px;
        height: 6px;
        background: {accent_color};
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }}
    
    .asset-name {{
        display: flex;
        align-items: center;
        font-weight: 500;
    }}
  </style>
</head>
<body>
  <div class="container">
    {content}
  </div>
</body>
</html>
'''

def render_header(title, sub_title, accent_color, fng_data=None):
    """Render the premium header section with optional Fear & Greed index indicator."""
    now = datetime.now()
    days_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months_en = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    date_str = f"{days_en[now.weekday()]} · {now.day:02d} {months_en[now.month-1]} {now.year}"
    
    fng_html = ""
    if fng_data:
        val = fng_data.get('value', 50)
        lbl = fng_data.get('classification', 'Neutral')
        color = STYLE_TOKENS['colors']['gold']
        if val <= 25: color = STYLE_TOKENS['colors']['red']
        elif val >= 75: color = STYLE_TOKENS['colors']['green']
        fng_html = f'''
        <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:15px; padding:4px 12px; display:inline-flex; align-items:center; gap:8px;">
          <span style="font-size:9.5px; color:var(--dim); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Fear & Greed:</span>
          <span style="font-family:var(--mono); font-size:11px; font-weight:700; color:{color};">{val}</span>
          <span style="font-size:10px; color:var(--dim); font-weight:500;">({lbl})</span>
        </div>
        '''
        
    return f'''
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px; border-bottom:1px solid var(--border); padding-bottom:16px;">
      <tr>
        <td>
          <div style="font-family:var(--sans); font-size:10px; font-weight:700; color:var(--dim); letter-spacing:2px; text-transform:uppercase; margin-bottom:4px;">NOCASHFLOW</div>
          <h1 style="font-family:var(--serif); font-size:26px; font-weight:700; color:var(--text); margin:0 0 4px 0; letter-spacing:-0.5px; border-left:3px solid {accent_color}; padding-left:12px;">{title}</h1>
          <div style="font-family:var(--sans); font-size:11px; color:var(--dim); font-style:italic;">{sub_title}</div>
        </td>
        <td align="right" style="vertical-align:bottom; text-align:right;">
          <div style="font-family:var(--mono); font-size:11px; font-weight:600; color:var(--text); margin-bottom:8px;">{date_str}</div>
          {fng_html}
        </td>
      </tr>
    </table>
    '''

def render_ticker(data):
    """Render the top ticker bar with 7-day sparklines."""
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
         'chg': macro.get('NASDAQ 100 Futures_chg', 0)},
        {'name': 'DXY', 'price': _fmt_price(macro.get('DXY', 0), 'fx4'),
         'chg': macro.get('DXY_chg', 0)},
        {'name': 'GOLD', 'price': _fmt_price(gold_price, 'price0'),
         'chg': gold_chg},
        {'name': '10Y UST', 'price': _fmt_price(macro.get('US 10-Year Treasury Yield', 0), 'pct'),
         'chg': macro.get('US 10-Year Treasury Yield_chg', 0)},
        {'name': 'VIX', 'price': _fmt_price(macro.get('VIX', 0), 'price2'),
         'chg': macro.get('VIX_chg', 0)},
        {'name': 'BTC', 'price': _fmt_price(btc_price, 'price0'),
         'chg': btc_chg},
        {'name': 'BTC.D', 'price': f"{crypto_ov.get('btc_dominance', 0):.1f}%", 'chg': None},
        {'name': 'F&G INDEX', 'price': str(fng.get('value', 0)), 'chg': None, 'custom': fng.get('classification', '')},
    ]

    html = '<table class="ticker" cellpadding="0" cellspacing="0"><tr>\n'
    for t in tickers:
        if t.get('chg') is not None:
            chg_text, chg_cls = _fmt_change(t['chg'])
        elif 'custom' in t:
            chg_text = t['custom']
            chg_cls = 'up' if 'Greed' in chg_text else ('down' if 'Fear' in chg_text else '')
        else:
            chg_text = '—'
            chg_cls = ''
            
        html += f'''
    <td class="ti">
      <div class="ti-name">{t['name']}</div>
      <div class="ti-val">{t['price']}</div>
      <div class="ti-chg {chg_cls}">{chg_text}</div>
    </td>'''
    html += '\n</tr></table>'
    return html

def render_regime_strip(data):
    """Render the regime language bar strip."""
    summary_text = data.get('ai_summary', '')
    if not summary_text:
        return ""
    return f'''
    <div style="background:rgba(245,158,11,0.06); border-left:3px solid var(--gold); border-radius:0 4px 4px 0; padding:12px 16px; margin-bottom:24px; font-size:12px; line-height:1.6; color:var(--text);">
      {summary_text}
    </div>
    '''

def render_section_divider(title, icon=None):
    """Draw a clean serif section header separator."""
    icon_str = f"{icon} &nbsp;" if icon else ""
    return f'''
    <div class="section-divider">
      <span class="section-title">{icon_str}{title}</span>
      <div class="section-line"></div>
    </div>
    '''

def render_economic_calendar(events):
    """Render the economic calendar table."""
    if not events:
        return '<div style="color:var(--dim); text-align:center; padding:12px;">No scheduled events</div>'
        
    rows = []
    for ev in events:
        actual = ev.get('actual', '—')
        forecast = ev.get('forecast', '—')
        previous = ev.get('previous', '—')
        
        actual_style = 'color:var(--dim);'
        if actual and actual != '—':
            actual_style = 'font-weight:700; color:var(--text);'
            try:
                act_num = float(actual.replace('%', '').replace('K', '').replace('M', '').replace('B', '').strip())
                fct_num = float(forecast.replace('%', '').replace('K', '').replace('M', '').replace('B', '').strip())
                higher_is_better = True
                event_lower = ev.get('event', '').lower()
                if any(kw in event_lower for kw in ['cpi', 'pce', 'inflation', 'unemployment', 'claims']):
                    higher_is_better = False
                
                if act_num > fct_num:
                    actual_style = f"font-weight:700; color:var(--{'green' if higher_is_better else 'red'});"
                elif act_num < fct_num:
                    actual_style = f"font-weight:700; color:var(--{'red' if higher_is_better else 'green'});"
            except:
                pass

        rows.append(f'''
        <tr>
          <td style="color:var(--dim); white-space:nowrap; width:12%;">{ev.get('date', '')}</td>
          <td class="mono" style="width:10%;">{ev.get('time', '')}</td>
          <td><div class="asset-name"><div class="asset-dot"></div>{ev.get('event', '')}</div></td>
          <td style="color:var(--dim); width:10%;">{ev.get('country', '')}</td>
          <td class="mono" style="color:var(--dim); text-align:right; width:10%;">{previous}</td>
          <td class="mono" style="color:var(--gold); text-align:right; width:10%;">{forecast}</td>
          <td class="mono" style="{actual_style} text-align:right; width:10%;">{actual}</td>
        </tr>''')
        
    return f'''
    <table class="data-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Time</th>
          <th>Event</th>
          <th>Country</th>
          <th style="text-align:right;">Prev</th>
          <th style="text-align:right;">Cons</th>
          <th style="text-align:right;">Actual</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    '''

def render_asset_table(assets, type_name):
    """Render Equities, Commodities, or Watchlist rows with dynamic sparklines and indicators."""
    if not assets:
        return '<div style="color:var(--dim); text-align:center; padding:15px;">No asset data available</div>'
        
    rows = []
    for a in assets:
        symbol = a.get('Symbol', '')
        name = a.get('Name', '')
        price = a.get('Price', a.get('Current Price USD', 0))
        
        # Determine column layout based on type
        if type_name == 'crypto':
            chg1h = a.get('1h %', 0)
            chg24h = a.get('24h %', 0)
            chg7d = a.get('7d %', 0)
            
            p_str = _fmt_price(price, 'crypto')
            c1h_t, c1h_cls = _fmt_change(chg1h)
            c24h_t, c24h_cls = _fmt_change(chg24h)
            c7d_t, c7d_cls = _fmt_change(chg7d)
            
            rows.append(f'''
            <tr>
              <td><div class="asset-name"><div class="asset-dot"></div><strong style="color:var(--text);">{symbol}</strong>&nbsp;<span style="color:var(--dim); font-size:10px;">{name}</span></div></td>
              <td class="mono" style="font-weight:600;">{p_str}</td>
              <td class="mono {c1h_cls}">{c1h_t}</td>
              <td class="mono {c24h_cls}">{c24h_t}</td>
              <td class="mono {c7d_cls}">{c7d_t}</td>
            </tr>''')
        else: # equities or commodities
            chg24h = a.get('Change %', 0)
            chg7d = a.get('7d %', 0)
            chg30d = a.get('30d %', 0)
            
            p_str = _fmt_price(price, 'price2' if type_name=='commodities' else 'index')
            c24h_t, c24h_cls = _fmt_change(chg24h)
            c7d_t, c7d_cls = _fmt_change(chg7d)
            c30d_t, c30d_cls = _fmt_change(chg30d)
            
            # Draw tiny inline momentum indicator
            momentum = max(0, min(100, int(50 + chg24h * 5)))
            mom_svg = f'''
            <svg width="40" height="6" style="vertical-align:middle; background:var(--bg3); border-radius:3px;">
              <rect x="0" y="0" width="{momentum}%" height="6" fill="var(--{"green" if chg24h >= 0 else "red"})"/>
            </svg>
            '''
            
            rows.append(f'''
            <tr>
              <td><div class="asset-name"><div class="asset-dot"></div><strong>{symbol}</strong>&nbsp;<span style="color:var(--dim); font-size:10px;">{name}</span></div></td>
              <td class="mono" style="font-weight:600;">{p_str}</td>
              <td class="mono {c24h_cls}">{c24h_t}</td>
              <td class="mono {c7d_cls}">{c7d_t}</td>
              <td class="mono {c30d_cls}">{c30d_t}</td>
              <td style="text-align:center;">{mom_svg}</td>
            </tr>''')
            
    if type_name == 'crypto':
        headers = '''
        <tr>
          <th>Asset</th>
          <th>Price</th>
          <th>1H</th>
          <th>24H</th>
          <th>7D</th>
        </tr>'''
    else:
        headers = '''
        <tr>
          <th>Asset</th>
          <th>Price</th>
          <th>Daily</th>
          <th>7D</th>
          <th>30D</th>
          <th style="text-align:center; width:60px;">Trend</th>
        </tr>'''
        
    return f'''
    <table class="data-table">
      <thead>{headers}</thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    '''

def render_news_section(news_data, ai_commentaries=None):
    """Render news block list with custom AI insights."""
    stories = news_data.get('news', [])
    if not stories:
        return '<div style="color:var(--dim); padding:10px;">No stories compiled today</div>'
        
    html = []
    for idx, s in enumerate(stories[:3]): # Max 3 stories
        title = s.get('title', '')
        summary = s.get('summary', '')
        url = s.get('url', '#')
        img_url = s.get('image', '')
        source = s.get('source', 'News')
        
        # Fetch matching AI commentary
        ai_commentary = ""
        if ai_commentaries and idx < len(ai_commentaries):
            insight = ai_commentaries[idx]
            ai_commentary = f'''
            <div style="margin-top:10px; padding:10px 14px; background:var(--bg3); border-left:3px solid var(--gold2); border-radius:0 4px 4px 0; font-size:11.5px; color:var(--dim); line-height:1.6;">
              <strong style="color:var(--gold2);">AI Insight:</strong> {insight}
            </div>'''
            
        img_html = ""
        if img_url:
            img_html = f'''
            <td width="100" style="vertical-align:top; padding-left:16px;">
              <img src="{img_url}" width="100" height="70" style="border-radius:4px; object-fit:cover; border:1px solid var(--border);" loading="lazy" />
            </td>'''
            
        html.append(f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:6px; padding:16px; margin-bottom:14px; page-break-inside:avoid; break-inside:avoid;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="vertical-align:top;">
                <div style="font-size:9px; text-transform:uppercase; color:var(--gold2); font-weight:600; margin-bottom:6px; letter-spacing:0.5px;">{source}</div>
                <h3 style="font-size:14px; font-weight:600; color:var(--text); margin:0 0 6px 0; line-height:1.45;"><a href="{url}" style="color:inherit; text-decoration:none;" target="_blank">{title}</a></h3>
                <div style="font-size:12px; color:var(--dim); line-height:1.5;">{summary}</div>
              </td>
              {img_html}
            </tr>
          </table>
          {ai_commentary}
        </div>''')
        
    return '\n'.join(html)

def render_footer():
    """Render footer block containing disclosure details."""
    now = datetime.now()
    return f'''
    <div style="margin-top:40px; border-top:1px solid var(--border); padding-top:20px; text-align:center; font-family:var(--sans); font-size:10px; color:var(--dim); line-height:1.75;">
      <p style="margin:0 0 10px 0; font-weight:600; color:var(--text); letter-spacing:1px;">NOCASHFLOW bültenidir.</p>
      <p style="margin:0 0 10px 0;">This document is for informational purposes only and does not constitute financial, investment, or legal advice. All investment decisions carry risks.</p>
      <p style="margin:0;">&copy; {now.year} nocashflow.net. All rights reserved. <a href="https://nocashflow.net" style="color:var(--accent); text-decoration:none;" target="_blank">nocashflow.net</a></p>
    </div>
    '''
