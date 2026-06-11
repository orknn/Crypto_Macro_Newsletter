# render/daily.py
from datetime import datetime
from render.tokens import STYLE_TOKENS
from render.svg import (
    generate_sparkline, generate_fear_greed_gauge_svg,
    generate_coinbase_premium_chart, generate_etf_flow_chart
)
from render.components import (
    html_wrapper, render_header, render_ticker, render_regime_strip,
    render_section_divider, render_economic_calendar, render_asset_table,
    render_news_section, render_footer, _fmt_change, _fmt_price
)

def render_daily(data):
    """Assemble and compile sections for the Daily edition."""
    accent_color = STYLE_TOKENS['colors']['accent']
    
    # Header
    header_html = render_header(
        title="DAILY FINANCIAL BULLETIN",
        sub_title="Global Macro & Crypto Market Intelligence",
        accent_color=accent_color,
        fng_data=data.get('fear_and_greed')
    )
    
    # Regime Strip
    regime_html = render_regime_strip(data)
    
    # Ticker Bar
    ticker_html = render_ticker(data)
    
    # Economic Calendar
    calendar_html = ""
    events = data.get('economic_calendar', [])
    if events:
        calendar_html = f'''
        {render_section_divider("Bugünün Takvimi", "📅")}
        {render_economic_calendar(events)}
        '''
        
    # Equities & Commodities
    equities_html = ""
    mag7 = data.get('magnificent_7', [])
    commodities = data.get('commodities', [])
    if mag7 or commodities:
        mag7_table = render_asset_table(mag7, "equities") if mag7 else ""
        comm_table = render_asset_table(commodities, "commodities") if commodities else ""
        equities_html = f'''
        {render_section_divider("Equities & Commodities", "📈")}
        {mag7_table}
        <div style="margin-top:16px;"></div>
        {comm_table}
        '''
        
    # S&P 500 Sectors
    sectors_html = ""
    sectors = data.get('sp500_sectors', [])
    if sectors:
        tiles = []
        for s in sectors:
            sym = s.get('Symbol', '')
            name = s.get('Name', '')
            chg = s.get('Change %', 0)
            chg_text, chg_cls = _fmt_change(chg)
            bg = 'rgba(16,185,129,0.04)' if chg >= 0 else 'rgba(239,68,68,0.04)'
            border = 'rgba(16,185,129,0.18)' if chg >= 0 else 'rgba(239,68,68,0.18)'
            tiles.append(f'''
            <div style="background:{bg}; border:1px solid {border}; padding:8px; text-align:center; border-radius:4px;">
              <div style="font-size:7.5px; color:var(--dim); text-transform:uppercase; margin-bottom:2px;">{name}</div>
              <div style="font-family:var(--mono); font-size:11px; font-weight:600; color:var(--text); margin-bottom:2px;">{sym}</div>
              <div class="{chg_cls}" style="font-family:var(--mono); font-size:10px;">{chg_text}</div>
            </div>''')
        sectors_html = f'''
        <div style="display:flex; align-items:center; gap:8px; margin:24px 0 12px 0;">
          <span style="font-size:9px; letter-spacing:1px; text-transform:uppercase; color:var(--dim); font-weight:600;">📊 S&P 500 Sectors</span>
          <div style="flex:1; height:0.5px; background:var(--border);"></div>
        </div>
        <div class="sp500-grid">
          {''.join(tiles)}
        </div>
        '''
        
    # Crypto Divider
    crypto_divider = render_section_divider("KRİPTO MASASI", "⚡")
    
    # KPI Grid
    kpi_html = ""
    fng = data.get('fear_and_greed', {})
    crypto_ov = data.get('crypto_market_overview', {})
    macro = data.get('macro_indicators', {})
    
    # Indicators note fallback
    ind_note = data.get('indicators_note', '2Y-10Y spread invert olması resesyon riskini gösterir.')
    
    kpis = [
        {'label': 'VIX INDEX', 'value': f"{macro.get('VIX', 0):.1f}", 'change': '', 'cls': ''},
        {'label': 'DOLLAR INDEX (DXY)', 'value': f"{macro.get('DXY', 0):.2f}", 'change': '', 'cls': ''},
        {'label': '2s10s SPREAD', 'value': f"{macro.get('2s10s_spread', 0):.2f}%", 'change': '', 'cls': ''},
        {'label': 'FEAR & GREED', 'value': f"{fng.get('value', 0)}", 'change': fng.get('classification', ''), 'cls': 'up' if fng.get('value', 50) >= 50 else 'down'},
        {'label': 'BTC DOMINANCE', 'value': f"{crypto_ov.get('btc_dominance', 0):.1f}%", 'change': '', 'cls': ''},
        {'label': 'TOTAL MARKET CAP', 'value': f"${crypto_ov.get('total_market_cap', 0)/1e12:.2f}T", 'change': '', 'cls': ''},
    ]
    
    kpi_cards = []
    for k in kpis:
        kpi_cards.append(f'''
        <div class="kpi-card">
          <div class="kpi-label">{k['label']}</div>
          <div class="kpi-value">{k['value']}</div>
          <div class="kpi-change {k['cls']}">{k['change']}</div>
        </div>''')
        
    kpi_html = f'''
    <div class="card-grid">
      {''.join(kpi_cards)}
    </div>
    <div style="font-size:11px; color:var(--dim); line-height:1.5; margin-bottom:24px;">
      <strong style="color:var(--gold2);">Note:</strong> {ind_note}
    </div>
    '''

    # Derivatives Desk Panel
    deriv_data = data.get('derivatives_desk', {}) or {}
    fr = data.get('funding_rates', {}) or {}
    oi = data.get('open_interest', {}) or {}
    fb = data.get('crypto_futures_basis', {}) or {}
    
    # 1. Fear/Greed Speedometer
    fng_gauge = generate_fear_greed_gauge_svg(fng.get('value', 50), fng.get('classification', 'Neutral'))
    
    # 2. Coinbase Premium
    cp = data.get('coinbase_premium', {}) or {}
    cp_chart = generate_coinbase_premium_chart(cp.get('trend_data', []), cp.get('current_value', 0))
    
    # 3. BTC Price / Support levels
    btc_price = 0
    btc_chg_24h = 0
    for c in data.get('crypto_prices', []):
        if c['Symbol'] == 'BTC':
            btc_price = c.get('Current Price USD', 0)
            btc_chg_24h = c.get('24h %', 0)
            break
            
    btc_chg_text, btc_chg_cls = _fmt_change(btc_chg_24h)
    btc_support = cp.get('btc_support_level', 0)
    btc_resistance = cp.get('btc_resistance_level', 0)
    
    if btc_price > 0 and btc_support > 0 and btc_resistance > 0:
        if btc_price > btc_resistance:
            btc_analysis = f"Price at <strong>${btc_price:,.0f}</strong> is trading above <strong>resistance</strong> (${btc_resistance:,.0f}) — upward momentum may continue."
            btc_status_color = STYLE_TOKENS['colors']['green']
        elif btc_price < btc_support:
            btc_analysis = f"Price at <strong>${btc_price:,.0f}</strong> has broken below <strong>support</strong> (${btc_support:,.0f}) — short-term selling pressure may persist."
            btc_status_color = STYLE_TOKENS['colors']['red']
        else:
            btc_analysis = f"Price at <strong>${btc_price:,.0f}</strong> is holding above <strong>support</strong> (${btc_support:,.0f}), with <strong>resistance</strong> at ${btc_resistance:,.0f}."
            btc_status_color = STYLE_TOKENS['colors']['gold']
    else:
        btc_analysis = 'BTC price levels holding neutral.'
        btc_status_color = STYLE_TOKENS['colors']['dim']

    btc_status_html = f'''
    <div class="sparkline-wrap" style="page-break-inside: avoid; break-inside: avoid;">
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

    # Futures Basis
    fb_btc = fb.get('btc_basis', 0)
    fb_eth = fb.get('eth_basis', 0)
    fb_sen = fb.get('sentiment', 'Neutral')
    fb_badges = {
        'Strong Bullish': 'background:rgba(16,185,129,0.12); color:var(--green); border:1px solid rgba(16,185,129,0.3);',
        'Bullish': 'background:rgba(16,185,129,0.08); color:var(--green); border:1px solid rgba(16,185,129,0.2);',
        'Neutral': 'background:rgba(245,158,11,0.1); color:var(--gold); border:1px solid rgba(245,158,11,0.25);',
        'Bearish': 'background:rgba(239,68,68,0.08); color:var(--red); border:1px solid rgba(239,68,68,0.2);',
        'Strong Bearish': 'background:rgba(239,68,68,0.12); color:var(--red); border:1px solid rgba(239,68,68,0.3);',
    }
    fb_badge_style = fb_badges.get(fb_sen, fb_badges['Neutral'])
    futures_note = data.get('futures_note') or fb.get('description', '')

    basis_html = f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:20px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">Annualized Futures Premium</div>
        <div style="font-family:var(--mono); font-size:9px; padding:3px 10px; border-radius:3px; font-weight:600; text-transform:uppercase; {fb_badge_style}">{fb_sen}</div>
      </div>
      <div style="display:flex; gap:28px; margin-bottom:12px;">
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">BTC Basis</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:600; color:var(--text);">{fb_btc:.2f}%</div>
        </div>
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">ETH Basis</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:600; color:var(--text);">{fb_eth:.2f}%</div>
        </div>
      </div>
      <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.6;">
        {futures_note}
      </div>
    </div>
    '''

    # Funding & OI
    btc_fr_str, btc_fr_cls = _fmt_change(fr.get('BTC', 0.0))
    eth_fr_str, eth_fr_cls = _fmt_change(fr.get('ETH', 0.0))
    sol_fr_str, sol_fr_cls = _fmt_change(fr.get('SOL', 0.0))
    
    def fmt_oi_val(val):
        if not val: return '—'
        return f"{val/1000:.1f}K" if val < 1e6 else f"{val/1e6:.2f}M"
        
    btc_oi = oi.get('BTC', {})
    eth_oi = oi.get('ETH', {})
    sol_oi = oi.get('SOL', {})
    
    btc_oi_str = fmt_oi_val(btc_oi.get('oi'))
    eth_oi_str = fmt_oi_val(eth_oi.get('oi'))
    sol_oi_str = fmt_oi_val(sol_oi.get('oi'))
    
    btc_oi_chg, btc_oi_cls = _fmt_change(btc_oi.get('oi_chg_24h', 0))
    eth_oi_chg, eth_oi_cls = _fmt_change(eth_oi.get('oi_chg_24h', 0))
    sol_oi_chg, sol_oi_cls = _fmt_change(sol_oi.get('oi_chg_24h', 0))

    derivatives_html = f'''
    {render_section_divider("Derivatives Desk", "📊")}
    {btc_status_html}
    
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px;">
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Market Sentiment (F&G)</div>
        {fng_gauge}
      </div>
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Coinbase Premium Index</div>
        {cp_chart}
      </div>
    </div>
    
    {basis_html}
    
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:24px;">
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Funding Rates (8h Eq.)</div>
        <table width="100%" style="border-collapse:collapse; font-size:12px;">
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC</td><td class="mono {btc_fr_cls}" align="right">{btc_fr_str}</td></tr>
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">ETH</td><td class="mono {eth_fr_cls}" align="right">{eth_fr_str}</td></tr>
          <tr><td style="padding:6px 0; color:var(--dim);">SOL</td><td class="mono {sol_fr_cls}" align="right">{sol_fr_str}</td></tr>
        </table>
      </div>
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Open Interest (OI)</div>
        <table width="100%" style="border-collapse:collapse; font-size:12px;">
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC</td><td class="mono" align="right">{btc_oi_str} &nbsp;<span class="{btc_oi_cls}">{btc_oi_chg}</span></td></tr>
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">ETH</td><td class="mono" align="right">{eth_oi_str} &nbsp;<span class="{eth_oi_cls}">{eth_oi_chg}</span></td></tr>
          <tr><td style="padding:6px 0; color:var(--dim);">SOL</td><td class="mono" align="right">{sol_oi_str} &nbsp;<span class="{sol_oi_cls}">{sol_oi_chg}</span></td></tr>
        </table>
      </div>
    </div>
    '''

    # Spot BTC ETF Flows
    etf_html = ""
    etf = data.get('etf_flows')
    if etf:
        ibit = etf.get('IBIT_flow_m')
        fbtc = etf.get('FBTC_flow_m')
        total = etf.get('Total_flow_m')
        sentiment = etf.get('sentiment', 'Neutral')
        etf_date = etf.get('date', '')
        etf_note = data.get('etf_note', '')
        
        ibit_cls = "up" if ibit >= 0 else "down"
        fbtc_cls = "up" if fbtc >= 0 else "down"
        total_cls = "up" if total >= 0 else "down"
        
        # 10-day history bar chart
        etf_history = data.get('etf_history_data', [])
        bar_chart_svg = ""
        if etf_history:
            bar_chart_svg = f'''
            <div style="margin-top:16px; margin-bottom:16px; border-top:1px solid var(--border); padding-top:16px;">
              <div style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--dim); margin-bottom:10px;">Spot ETF Flows History (Last 10 Days)</div>
              {generate_etf_flow_chart(etf_history)}
            </div>
            '''
            
        badge_style = 'background:rgba(245,158,11,0.1); color:var(--gold); border:1px solid rgba(245,158,11,0.3);'
        if 'Inflow' in sentiment:
            badge_style = 'background:rgba(16,185,129,0.12); color:var(--green); border:1px solid rgba(16,185,129,0.3);'
        elif 'Outflow' in sentiment:
            badge_style = 'background:rgba(239,68,68,0.12); color:var(--red); border:1px solid rgba(239,68,68,0.3);'
            
        etf_html = f'''
        {render_section_divider("Spot Bitcoin ETF Flows", "📥")}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:24px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">ETF Daily Net Flows</div>
              <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">{etf_date}</div>
            </div>
            <div style="font-family:var(--mono); font-size:9px; padding:3px 10px; border-radius:3px; font-weight:600; text-transform:uppercase; {badge_style}">{sentiment}</div>
          </div>
          <div style="display:flex; gap:28px; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">Total Flow</div>
              <div class="{total_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{total:+.1f}M</div>
            </div>
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">IBIT (BlackRock)</div>
              <div class="{ibit_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{ibit:+.1f}M</div>
            </div>
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">FBTC (Fidelity)</div>
              <div class="{fbtc_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{fbtc:+.1f}M</div>
            </div>
          </div>
          
          {bar_chart_svg}
          
          <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.5;">
            {etf_note}
          </div>
        </div>
        '''

    # Watchlist
    watchlist_html = ""
    crypto_prices = data.get('crypto_prices', [])
    if crypto_prices:
        watchlist_html = f'''
        {render_section_divider("Crypto Watchlist", "🔍")}
        {render_asset_table(crypto_prices, "crypto")}
        '''

    # Stories
    stories_html = ""
    macro_news = data.get('macro_news', {})
    if macro_news:
        stories_html = f'''
        {render_section_divider("Top Stories", "📰")}
        {render_news_section(macro_news, data.get('news_commentaries'))}
        '''
        
    # Footer
    footer_html = render_footer()
    
    # Combined Content
    content_html = f'''
    {header_html}
    {regime_html}
    {ticker_html}
    {calendar_html}
    {equities_html}
    {sectors_html}
    {crypto_divider}
    {kpi_html}
    {derivatives_html}
    {etf_html}
    {watchlist_html}
    {stories_html}
    {footer_html}
    '''
    
    return html_wrapper(
        title="Daily Financial Bulletin",
        content=content_html,
        accent_color=accent_color
    )
