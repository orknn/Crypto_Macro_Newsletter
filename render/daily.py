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
    render_news_section, render_footer, _fmt_change, _fmt_price,
    render_coinbase_premium_card
)
from render.i18n import STR

def render_daily(data, lang='tr'):
    """Assemble and compile sections for the Daily edition."""
    accent_color = STYLE_TOKENS['colors']['accent']
    
    # Title & Subtitle translations
    title = "GÜNLÜK FİNANS BÜLTENİ" if lang == 'tr' else "DAILY FINANCIAL BULLETIN"
    sub_title = "Küresel Makro ve Kripto Piyasa İstihbaratı" if lang == 'tr' else "Global Macro & Crypto Market Intelligence"
    
    # Header
    header_html = render_header(
        title=title,
        sub_title=sub_title,
        accent_color=accent_color,
        fng_data=data.get('fear_and_greed'),
        lang=lang
    )
    
    # Regime Strip
    # Read regime and regime_line from localized data block
    lang_data = data.get(lang, {}) or {}
    regime = data.get('regime', 'NEUTRAL')
    regime_line = lang_data.get('regime_line', '')
    regime_html = render_regime_strip(regime, regime_line, lang=lang)
    
    # Overview (Genel Değerlendirme)
    overview_html = ""
    overview_text = lang_data.get('overview', '') or data.get('ai_summary', '')
    if overview_text:
        overview_html = f'''
        <div class="summary-card">
          <p class="summary-text">{overview_text}</p>
        </div>
        '''
        
    # Ticker Bar
    ticker_html = render_ticker(data, lang=lang)
    
    # Economic Calendar
    calendar_html = ""
    events = data.get('economic_calendar', [])
    if events:
        calendar_html = f'''
        {render_section_divider(STR['section_calendar'][lang])}
        {render_economic_calendar(events, lang=lang)}
        '''
        
    # Equities & Commodities
    equities_html = ""
    mag7 = data.get('magnificent_7', [])
    commodities = data.get('commodities', [])
    if mag7 or commodities:
        mag7_table = render_asset_table(mag7, "equities", lang=lang) if mag7 else ""
        comm_table = render_asset_table(commodities, "commodities", lang=lang) if commodities else ""
        equities_html = f'''
        {render_section_divider(STR['section_equities_commodities'][lang])}
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
          <span style="font-family:var(--sans); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:1.5px; color:var(--text); white-space:nowrap;">{STR['section_sp500_sectors'][lang]}</span>
          <div style="flex:1; height:0.5px; background:var(--border);"></div>
        </div>
        <div class="sp500-grid">
          {''.join(tiles)}
        </div>
        '''
        
    # Crypto Divider
    crypto_divider = render_section_divider(STR['section_crypto_desk'][lang])
    
    # Key Metrics Grid (Only Total Mcap, BTC Dominance, Fear & Greed)
    kpi_html = ""
    fng = data.get('fear_and_greed', {})
    crypto_ov = data.get('crypto_market_overview', {})
    
    # Localized Indicators Note
    ind_note = lang_data.get('notes', {}).get('indicators_note') or data.get('indicators_note', '')
    
    kpis = [
        {'label': STR['card_mcap'][lang], 'value': f"${crypto_ov.get('total_market_cap', 0)/1e12:.2f}T", 'change': '', 'cls': ''},
        {'label': STR['card_dominance'][lang], 'value': f"{crypto_ov.get('btc_dominance', 0):.1f}%", 'change': '', 'cls': ''},
        {'label': STR['card_fng'][lang], 'value': f"{fng.get('value', 0)}", 'change': fng.get('classification', ''), 'cls': 'up' if fng.get('value', 50) >= 50 else 'down'},
    ]
    
    # Map F&G labels
    lbl_tr = {
        'Neutral': 'Nötr',
        'Fear': 'Korku',
        'Extreme Fear': 'Aşırı Korku',
        'Greed': 'Açgözlülük',
        'Extreme Greed': 'Aşırı Açgözlülük'
    }
    if lang == 'tr':
        kpis[2]['change'] = lbl_tr.get(kpis[2]['change'], kpis[2]['change'])

    kpi_cards = []
    for k in kpis:
        kpi_cards.append(f'''
        <div class="kpi-card">
          <div class="kpi-label">{k['label']}</div>
          <div class="kpi-value">{k['value']}</div>
          <div class="kpi-change {k['cls']}">{k['change']}</div>
        </div>''')
        
    kpi_note_html = ""
    if ind_note:
        kpi_note_html = f'''
        <div style="font-size:11px; color:var(--dim); line-height:1.5; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
          <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {ind_note}
        </div>'''

    kpi_html = f'''
    <div class="card-grid" style="grid-template-columns: repeat(3, 1fr);">
      {''.join(kpi_cards)}
    </div>
    {kpi_note_html}
    '''

    # Derivatives Desk Panel
    fr = data.get('funding_rates', {}) or {}
    oi = data.get('open_interest', {}) or {}
    fb = data.get('crypto_futures_basis', {}) or {}
    options_data = data.get('options_data', {}) or {}
    
    # 1. Fear/Greed Speedometer
    fng_gauge = generate_fear_greed_gauge_svg(fng.get('value', 50), fng.get('classification', 'Neutral'))
    
    # 2. Coinbase Premium
    cp = data.get('coinbase_premium', {}) or {}
    cp_card_html = render_coinbase_premium_card(cp, "7D", lang=lang)
    
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
        if lang == 'tr':
            if btc_price > btc_resistance:
                btc_analysis = f"Fiyat <strong>${btc_price:,.0f}</strong> ile <strong>direnç</strong> (${btc_resistance:,.0f}) seviyesinin üzerinde işlem görüyor — yukarı yönlü ivme devam edebilir."
                btc_status_color = STYLE_TOKENS['colors']['green']
            elif btc_price < btc_support:
                btc_analysis = f"Fiyat <strong>${btc_price:,.0f}</strong> ile <strong>destek</strong> (${btc_support:,.0f}) seviyesinin altına sarktı — kısa vadeli satış baskısı sürebilir."
                btc_status_color = STYLE_TOKENS['colors']['red']
            else:
                btc_analysis = f"Fiyat <strong>${btc_price:,.0f}</strong> ile <strong>destek</strong> (${btc_support:,.0f}) seviyesinin üzerinde tutunuyor, <strong>direnç</strong> ise ${btc_resistance:,.0f} seviyesinde."
                btc_status_color = STYLE_TOKENS['colors']['gold']
        else:
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
        btc_analysis = 'BTC fiyat seviyeleri yatay.' if lang == 'tr' else 'BTC price levels holding neutral.'
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
                <td style="padding-right:24px; text-align:center;"><div style="color:var(--dim); margin-bottom:3px;">{STR['card_support'][lang]}</div><div style="font-family:var(--mono); color:var(--green); font-size:13px;">${btc_support:,.0f}</div></td>
                <td style="text-align:center;"><div style="color:var(--dim); margin-bottom:3px;">{STR['card_resistance'][lang]}</div><div style="font-family:var(--mono); color:var(--red); font-size:13px;">${btc_resistance:,.0f}</div></td>
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
    futures_note = lang_data.get('notes', {}).get('futures_note') or data.get('futures_note') or fb.get('description', '')

    basis_column_html = f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px;">{STR['section_positioning'][lang]}</div>
        <div style="font-family:var(--mono); font-size:9px; padding:2px 8px; border-radius:3px; font-weight:600; text-transform:uppercase; {fb_badge_style}">{fb_sen}</div>
      </div>
      <div style="display:flex; gap:24px; margin-bottom:12px;">
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">BTC Basis</div>
          <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--text);">{fb_btc:.2f}%</div>
        </div>
        <div>
          <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">ETH Basis</div>
          <div style="font-family:var(--mono); font-size:16px; font-weight:600; color:var(--text);">{fb_eth:.2f}%</div>
        </div>
      </div>
      <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.5;">
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
    
    # Hide OI changes if they are None (Sıfır basmak yok)
    if btc_oi.get('oi_chg_24h') is not None:
        btc_oi_chg_val, btc_oi_cls = _fmt_change(btc_oi['oi_chg_24h'])
        btc_oi_chg = f'&nbsp;<span class="{btc_oi_cls}">{btc_oi_chg_val}</span>'
    else:
        btc_oi_chg = ""
        
    if eth_oi.get('oi_chg_24h') is not None:
        eth_oi_chg_val, eth_oi_cls = _fmt_change(eth_oi['oi_chg_24h'])
        eth_oi_chg = f'&nbsp;<span class="{eth_oi_cls}">{eth_oi_chg_val}</span>'
    else:
        eth_oi_chg = ""
        
    if sol_oi.get('oi_chg_24h') is not None:
        sol_oi_chg_val, sol_oi_cls = _fmt_change(sol_oi['oi_chg_24h'])
        sol_oi_chg = f'&nbsp;<span class="{sol_oi_cls}">{sol_oi_chg_val}</span>'
    else:
        sol_oi_chg = ""

    # Extra derivatives cards (Max Pain, DVOL, PCR)
    max_pain_price = options_data.get('max_pain_price')
    dvol_index = options_data.get('dvol_index')
    dvol_change_24h = options_data.get('dvol_change_24h')
    put_call_ratio = options_data.get('put_call_ratio')
    
    options_cards = []
    if max_pain_price is not None:
        options_cards.append(f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:14px 16px; text-align:center; flex:1; min-width:160px;">
          <div style="font-size:9.5px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:8px;">{STR['card_max_pain'][lang]}</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:700; color:var(--text);">${max_pain_price:,.0f}</div>
        </div>''')
        
    if dvol_index is not None:
        if dvol_change_24h is not None:
            sign = "+" if dvol_change_24h >= 0 else ""
            dvol_cls = "up" if dvol_change_24h >= 0 else "down"
            arrow = "▲" if dvol_change_24h >= 0 else "▼"
            dvol_chg_str = f"&nbsp;<span class='{dvol_cls}' style='font-size:11px; font-weight:normal;'>{arrow} {sign}{dvol_change_24h:.2f}</span>"
        else:
            dvol_chg_str = ""
            
        options_cards.append(f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:14px 16px; text-align:center; flex:1; min-width:160px;">
          <div style="font-size:9.5px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:8px;">{STR['card_dvol'][lang]}</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:700; color:var(--text);">{dvol_index:.2f}{dvol_chg_str}</div>
        </div>''')
        
    if put_call_ratio is not None:
        options_cards.append(f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:14px 16px; text-align:center; flex:1; min-width:160px;">
          <div style="font-size:9.5px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:8px;">{STR['card_pcr'][lang]}</div>
          <div style="font-family:var(--mono); font-size:17px; font-weight:700; color:var(--text);">{put_call_ratio:.2f}</div>
        </div>''')
        
    options_cards_html = ""
    if options_cards:
        options_cards_html = f'''
        <div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:20px; page-break-inside:avoid; break-inside:avoid;">
          {"".join(options_cards)}
        </div>
        '''

    derivatives_html = f'''
    {render_section_divider(STR['section_derivatives_desk'][lang])}
    {btc_status_html}
    
    {cp_card_html}
    
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px; page-break-inside:avoid; break-inside:avoid;">
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">{STR['card_fng'][lang]}</div>
        {fng_gauge}
      </div>
      {basis_column_html}
    </div>
    
    {options_cards_html}
    
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
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
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC</td><td class="mono" align="right">{btc_oi_str}{btc_oi_chg}</td></tr>
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">ETH</td><td class="mono" align="right">{eth_oi_str}{eth_oi_chg}</td></tr>
          <tr><td style="padding:6px 0; color:var(--dim);">SOL</td><td class="mono" align="right">{sol_oi_str}{sol_oi_chg}</td></tr>
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
        etf_note = lang_data.get('notes', {}).get('etf_note') or data.get('etf_note', '')
        
        ibit_cls = "up" if ibit >= 0 else "down"
        fbtc_cls = "up" if fbtc >= 0 else "down"
        total_cls = "up" if total >= 0 else "down"
        
        # 10-day history bar chart
        etf_history = data.get('etf_history_data', [])
        bar_chart_svg = ""
        if etf_history:
            bar_chart_svg = f'''
            <div style="margin-top:16px; margin-bottom:16px; border-top:1px solid var(--border); padding-top:16px;">
              <div style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--dim); margin-bottom:10px;">{STR['card_etf_history_title'][lang]}</div>
              {generate_etf_flow_chart(etf_history)}
            </div>
            '''
            
        badge_style = 'background:rgba(245,158,11,0.1); color:var(--gold); border:1px solid rgba(245,158,11,0.3);'
        if 'Inflow' in sentiment:
            badge_style = 'background:rgba(16,185,129,0.12); color:var(--green); border:1px solid rgba(16,185,129,0.3);'
        elif 'Outflow' in sentiment:
            badge_style = 'background:rgba(239,68,68,0.12); color:var(--red); border:1px solid rgba(239,68,68,0.3);'
            
        etf_html = f'''
        {render_section_divider(STR['section_etf_flows'][lang])}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">{STR['card_etf_flows_title'][lang]}</div>
              <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">{etf_date}</div>
            </div>
            <div style="font-family:var(--mono); font-size:9px; padding:3px 10px; border-radius:3px; font-weight:600; text-transform:uppercase; {badge_style}">{sentiment}</div>
          </div>
          <div style="display:flex; gap:28px; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">{STR['card_daily_total'][lang]}</div>
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
          
          <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.5; background:var(--bg3); padding:10px 14px; border-left:3px solid var(--gold); border-radius:0 4px 4px 0;">
            <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {etf_note}
          </div>
        </div>
        '''

    # Watchlist
    watchlist_html = ""
    crypto_prices = data.get('crypto_prices', [])
    if crypto_prices:
        watchlist_html = f'''
        {render_section_divider(STR['section_watchlist'][lang])}
        {render_asset_table(crypto_prices, "crypto", lang=lang)}
        '''

    # Stories
    stories_html = ""
    macro_news = data.get('macro_news', {})
    if macro_news:
        stories_html = f'''
        {render_section_divider(STR['section_stories'][lang])}
        {render_news_section(macro_news, lang_data.get('insights'), lang=lang)}
        '''
        
    # Footer
    footer_html = render_footer(lang=lang, is_weekly=False)
    
    # Combined Content
    content_html = f'''
    {header_html}
    {regime_html}
    {overview_html}
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
        title="Daily Financial Bulletin" if lang == 'en' else "Günlük Finans Bülteni",
        content=content_html,
        accent_color=accent_color
    )
