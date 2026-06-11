# render/weekly.py
from datetime import datetime
from render.tokens import STYLE_TOKENS
from render.svg import (
    generate_sparkline, generate_fear_greed_gauge_svg,
    generate_winners_losers_chart, generate_correlation_matrix_svg,
    generate_cycle_heatmap_svg, generate_net_liquidity_chart,
    generate_inflation_chart, generate_ytd_comparison_chart,
    generate_stablecoin_mcap_share_chart, generate_etf_flow_chart,
    generate_coinbase_premium_chart
)
from render.components import (
    html_wrapper, render_header, render_ticker, render_regime_strip,
    render_section_divider, render_economic_calendar, render_asset_table,
    render_news_section, render_footer, _fmt_change, _fmt_price,
    render_coinbase_premium_card
)
from render.i18n import STR

def fmt_notional(val):
    if not val: return '—'
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    elif val >= 1e6:
        return f"${val/1e6:.1f}M"
    else:
        return f"${val:,.0f}"

def render_weekly(data, lang='tr'):
    """Assemble and compile sections for the Weekly edition."""
    accent_color = STYLE_TOKENS['colors']['accent']
    gold_color = STYLE_TOKENS['colors']['gold']
    
    # Title & Subtitle translations
    title = "HAFTALIK STRATEJİK ANALİZ" if lang == 'tr' else "WEEKLY DEEP DIVE"
    sub_title = "Likidite, Makro Temalar ve Kripto Rotasyonu" if lang == 'tr' else "Strategic Liquidity, Macro Themes & Crypto Rotation"
    
    # 1. Header
    header_html = render_header(
        title=title,
        sub_title=sub_title,
        accent_color=gold_color, # Gold accent for weekly
        fng_data=data.get('fear_and_greed'),
        lang=lang
    )
    
    # 2. Weekly Themes (AI Generated)
    themes_html = ""
    lang_data = data.get(lang, {}) or {}
    themes = lang_data.get('themes', []) or data.get('weekly_themes', [])
    if themes:
        theme_items = []
        for i, t in enumerate(themes[:3]):
            icons = ["🌍", "💧", "🪙"]
            icon = icons[i] if i < len(icons) else "💡"
            theme_items.append(f'''
            <div style="background:var(--bg2); border:1px solid var(--border); border-radius:6px; padding:16px; margin-bottom:12px;">
              <div style="font-family:var(--sans); font-size:11px; font-weight:700; color:var(--gold2); text-transform:uppercase; margin-bottom:6px; letter-spacing:0.5px;">Theme {i+1}: {icon} {t.get('title', '')}</div>
              <div style="font-family:var(--sans); font-size:12.5px; color:var(--text); line-height:1.7;">{t.get('description', '')}</div>
            </div>''')
            
        themes_html = f'''
        {render_section_divider(STR['section_themes'][lang])}
        {''.join(theme_items)}
        '''
        
    # 3. Next Week Calendar & Unlocks & Weekly strategy note
    calendar_weekly_html = ""
    events = data.get('economic_calendar', [])
    strategy_note = lang_data.get('notes', {}).get('week_plan_note') or data.get('week_plan_note', '')
    if events or strategy_note:
        calendar_weekly_html = f'''
        {render_section_divider(STR['section_calendar_weekly'][lang])}
        {render_economic_calendar(events, lang=lang)}'''
        
        if strategy_note:
            calendar_weekly_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-top:16px; background:var(--bg2); padding:14px 18px; border-left:3px solid var(--gold2); border-radius:0 4px 4px 0; page-break-inside: avoid; break-inside: avoid;">
              <strong style="color:var(--text);">{STR['outlook_strategy'][lang]}:</strong> {strategy_note}
            </div>'''
        
    # 4. Liquidity Regime
    liq_html = ""
    net_liq = data.get('net_liquidity_history_data', [])
    if net_liq:
        liq_chart = generate_net_liquidity_chart(net_liq)
        liq_note = lang_data.get('notes', {}).get('liquidity_note') or data.get('liquidity_note', '')
        liq_html = f'''
        {render_section_divider(STR['section_liquidity'][lang])}
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">US Federal Reserve Net Liquidity (3-Year Weekly)</div>
          {liq_chart}
        </div>'''
        
        if liq_note:
            liq_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {liq_note}
            </div>'''

    # 5. Macro Scoreboard & Inflation Path
    macro_scoreboard_html = ""
    ms = data.get('macro_scoreboard', {}) or {}
    inflation_history = data.get('inflation_history_data', [])
    if ms or inflation_history:
        dxy = ms.get('DXY', 0.0)
        dxy_chg = ms.get('DXY_chg', 0.0)
        dxy_txt, dxy_cls = _fmt_change(dxy_chg)
        
        hy_oas = ms.get('HY_OAS', 0.0)
        hy_chg = ms.get('HY_OAS_chg_bp', 0.0)
        hy_txt = f"{hy_chg:+.1f} bps"
        hy_cls = 'down' if hy_chg > 0 else 'up'
        
        move_idx = ms.get('MOVE', 0.0)
        move_chg = ms.get('MOVE_chg', 0.0)
        move_txt, move_cls = _fmt_change(move_chg)
        
        macro_indicators_data = data.get('macro_indicators', {}) or {}
        vix = macro_indicators_data.get('VIX', 0.0)
        vix_chg = macro_indicators_data.get('VIX_chg', 0.0)
        vix_txt, vix_cls = _fmt_change(vix_chg)
        
        yield_10y = macro_indicators_data.get('US 10-Year Treasury Yield', 0.0)
        spread_2s10s = macro_indicators_data.get('2s10s_spread', 0.0)
        spread_txt, spread_cls = _fmt_change(spread_2s10s)
        
        inflation_chart = generate_inflation_chart(inflation_history) if inflation_history else ""
        inflation_note = lang_data.get('notes', {}).get('inflation_note') or data.get('inflation_note', '')
        
        macro_scoreboard_html = f'''
        {render_section_divider(STR['section_macro_scoreboard'][lang])}
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:20px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_dxy'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{dxy:.2f}</div>
            <div class="{dxy_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{dxy_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_10y_yield'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{yield_10y:.2f}%</div>
            <div style="font-family:var(--mono); font-size:10px; color:var(--dim); margin-top:2px;">Consolidated</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_spread'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{spread_2s10s:.2f}%</div>
            <div class="{spread_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{spread_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_hy_spread'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{hy_oas:.2f}%</div>
            <div class="{hy_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{hy_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_move'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{move_idx:.1f}</div>
            <div class="{move_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{move_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_vix_index'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{vix:.1f}</div>
            <div class="{vix_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{vix_txt}</div>
          </div>
        </div>
        
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">{STR['card_inflation_path'][lang]} (CPI, Core CPI, Core PCE YoY - 5-Year)</div>
          {inflation_chart}
        </div>'''
        
        if inflation_note:
            macro_scoreboard_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold); border-radius:0 4px 4px 0;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {inflation_note}
            </div>'''

    # 6. Equities & Commodities (Weekly)
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

    # 7. S&P 500 Sectors
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

    # 8. BTC vs NDX vs Gold YTD
    ytd_html = ""
    ytd_comp = data.get('ytd_comparison_data', {})
    if ytd_comp:
        ytd_html = generate_ytd_comparison_chart(ytd_comp)

    # 9. Turkey Desk
    turkey_html = ""
    bist_data = data.get('bist_try', {})
    if bist_data:
        bist100 = bist_data.get('bist100', 0.0)
        bist_chg = bist_data.get('bist100_chg', 0.0)
        bist_txt, bist_cls = _fmt_change(bist_chg)
        
        usd_try = bist_data.get('usd_try', 0.0)
        try_chg = bist_data.get('try_chg', 0.0)
        try_txt, try_cls = _fmt_change(try_chg)
        
        bist_usd = bist100 / usd_try if usd_try > 0 else 0.0
        bist_usd_chg = bist_chg - try_chg
        usd_bist_txt, usd_bist_cls = _fmt_change(bist_usd_chg)
        
        turkey_html = f'''
        {render_section_divider(STR['section_turkey_desk'][lang])}
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:24px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">BIST 100</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{bist100:,.0f}</div>
            <div class="{bist_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{bist_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">USD/TRY</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{usd_try:.4f}</div>
            <div class="{try_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{try_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">BIST 100 ($ Denom.)</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">${bist_usd:.2f}</div>
            <div class="{usd_bist_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{usd_bist_txt}</div>
          </div>
        </div>
        '''

    # Crypto Divider
    crypto_divider = render_section_divider(STR['section_crypto_desk'][lang])

    # 10. Stablecoin Supply
    stablecoin_html = ""
    stable_history = data.get('stablecoin_history_data', [])
    stable_note = lang_data.get('notes', {}).get('stablecoin_note') or data.get('stablecoin_note', '')
    if stable_history:
        stable_chart = generate_stablecoin_mcap_share_chart(stable_history)
        stablecoin_html = f'''
        {render_section_divider(STR['section_stablecoin'][lang])}
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">{STR['card_stablecoin_mcap'][lang]} & USDT/USDC Shares (3-Year Weekly)</div>
          {stable_chart}
        </div>'''
        
        if stable_note:
            stablecoin_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--green); border-radius:0 4px 4px 0;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {stable_note}
            </div>'''

    # 11. ETF Weekly Flows
    etf_weekly_html = ""
    etf_weekly_history = data.get('etf_weekly_history_data', [])
    etf_note = lang_data.get('notes', {}).get('etf_note') or data.get('etf_note', '')
    if etf_weekly_history:
        latest_etf = etf_weekly_history[-1]
        w_total = latest_etf.get('Total_flow_m', 0.0)
        w_ibit = latest_etf.get('IBIT_flow_m', 0.0)
        w_fbtc = latest_etf.get('FBTC_flow_m', 0.0)
        w_date = latest_etf.get('date', '')
        
        total_cls = "up" if w_total >= 0 else "down"
        ibit_cls = "up" if w_ibit >= 0 else "down"
        fbtc_cls = "up" if w_fbtc >= 0 else "down"
        
        etf_chart = generate_etf_flow_chart(etf_weekly_history)
        etf_weekly_html = f'''
        {render_section_divider(STR['section_etf_flows'][lang])}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">{STR['card_etf_weekly_title'][lang]}</div>
              <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">Week ending {w_date}</div>
            </div>
          </div>
          <div style="display:flex; gap:28px; margin-bottom:16px;">
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">{STR['card_weekly_total'][lang]}</div>
              <div class="{total_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{w_total:+.1f}M</div>
            </div>
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">IBIT (BlackRock)</div>
              <div class="{ibit_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{w_ibit:+.1f}M</div>
            </div>
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">FBTC (Fidelity)</div>
              <div class="{fbtc_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{w_fbtc:+.1f}M</div>
            </div>
          </div>
          <div class="sparkline-wrap" style="margin-bottom:12px; padding-top:12px; border-top:1px solid var(--border);">
            <div style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--dim); margin-bottom:10px;">{STR['card_etf_weekly_history_title'][lang]}</div>
            {etf_chart}
          </div>'''
          
        if etf_note:
            etf_weekly_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; background:var(--bg3); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {etf_note}
            </div>'''
            
        etf_weekly_html += '</div>'

    # 12. Winners & Losers
    winners_losers_html = ""
    winners = data.get('winners', [])
    losers = data.get('losers', [])
    if winners or losers:
        wl_chart = generate_winners_losers_chart(winners, losers)
        winners_losers_html = f'''
        {render_section_divider(STR['section_winners_losers'][lang])}
        <div class="sparkline-wrap" style="padding:20px 24px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
          {wl_chart}
        </div>
        '''

    # 13. Watchlist Weekly
    watchlist_html = ""
    crypto_prices = data.get('crypto_prices', [])
    if crypto_prices:
        watchlist_html = f'''
        {render_section_divider(STR['section_watchlist'][lang])}
        {render_asset_table(crypto_prices, "crypto", lang=lang)}
        '''

    # 14. Crypto Sector Rotation
    rotation_html = ""
    rotation_data = data.get('crypto_sector_rotation_data', {})
    rotation_note = lang_data.get('notes', {}).get('rotation_note') or data.get('rotation_note', '')
    if rotation_data:
        rows = []
        for sector, score in rotation_data.items():
            score_txt, score_cls = _fmt_change(score)
            rows.append(f'''
            <tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
              <td style="padding:8px 12px; font-weight:600; color:var(--text);">{sector}</td>
              <td class="mono {score_cls}" style="padding:8px 12px; text-align:right;">{score_txt}</td>
            </tr>''')
        rotation_html = f'''
        {render_section_divider(STR['section_rotation'][lang])}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; overflow:hidden; padding:12px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
          <table width="100%" style="border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border);"><th style="text-align:left; padding:8px 12px; color:var(--dim);">{STR['col_sector'][lang]}</th><th style="text-align:right; padding:8px 12px; color:var(--dim);">{STR['col_7d_avg_return'][lang]}</th></tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>'''
          
        if rotation_note:
            rotation_html += f'''
            <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.5; margin-top:12px;">
              <strong style="color:var(--gold2);">{STR['analyst_note'][lang]}:</strong> {rotation_note}
            </div>'''
            
        rotation_html += '</div>'

    # 15. Cycle Panel
    cycle_html = ""
    cycle = data.get('btc_cycle_metrics', {})
    cycle_note = lang_data.get('notes', {}).get('cycle_note') or data.get('cycle_note', '')
    if cycle:
        spot = cycle.get('spot', 0)
        wma = cycle.get('wma200', 0)
        mm = cycle.get('mayer_multiple', 1.0)
        drawdown = cycle.get('drawdown', 0.0)
        dist_wma = cycle.get('distance_to_200wma', 0.0)
        
        heatmap_svg = generate_cycle_heatmap_svg(cycle.get('monthly_heatmap'))
        
        cycle_html = f'''
        {render_section_divider(STR['section_cycle'][lang])}
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:20px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_mayer_multiple'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{mm:.3f}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">Spot / 200d SMA</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_200wma_distance'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{dist_wma:+.1f}%</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">WMA: ${wma:,.0f}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_drawdown'][lang]}</div>
            <div class="down" style="font-family:var(--mono); font-size:15px; font-weight:600;">{drawdown:.1f}%</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">ATH: ${cycle.get("ath", 0):,.0f}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_spot_price'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">${spot:,.0f}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">Real-time</div>
          </div>
        </div>
        
        <div class="sparkline-wrap" style="margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">Bitcoin Monthly Return Heatmap (2024-2026)</div>
          {heatmap_svg}
          <div style="font-size:9px; color:var(--dim); margin-top:6px; text-align:right;">* Current month is marked.</div>
        </div>'''
        
        if cycle_note:
            cycle_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold2); border-radius:0 4px 4px 0;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {cycle_note}
            </div>'''

    # 16. Correlation Matrix
    correlation_html = ""
    corr = data.get('correlation_matrix', {})
    corr_note = lang_data.get('notes', {}).get('correlation_note') or data.get('correlation_note', '')
    if corr:
        corr_chart = generate_correlation_matrix_svg(corr)
        correlation_html = f'''
        {render_section_divider(STR['section_correlation'][lang])}
        <div class="sparkline-wrap" style="margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:12px;">Macro & Crypto Assets Correlation Matrix (30-Day Rolling Daily Returns)</div>
          {corr_chart}
        </div>'''
        
        if corr_note:
            correlation_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {corr_note}
            </div>'''

    # 17. Futures Positioning Desk
    positioning_html = ""
    fr = data.get('funding_rates', {}) or {}
    oi = data.get('open_interest', {}) or {}
    fb = data.get('crypto_futures_basis', {}) or {}
    options_data = data.get('options_data', {}) or {}
    futures_note = lang_data.get('notes', {}).get('futures_note') or data.get('futures_note', '')
    
    # Fear & Greed Speedometer
    fng_gauge = generate_fear_greed_gauge_svg(fng.get('value', 50), fng.get('classification', 'Neutral'))
    
    # Coinbase Premium chart
    cp = data.get('coinbase_premium', {}) or {}
    cp_card_html = render_coinbase_premium_card(cp, "180D", lang=lang)
    
    btc_fr_str, btc_fr_cls = _fmt_change(fr.get('BTC', 0.0))
    eth_fr_str, eth_fr_cls = _fmt_change(fr.get('ETH', 0.0))
    
    btc_oi = oi.get('BTC', {})
    eth_oi = oi.get('ETH', {})
    
    btc_oi_str = fmt_oi_val(btc_oi.get('oi'))
    eth_oi_str = fmt_oi_val(eth_oi.get('oi'))
    
    # Hide OI changes if they are None (Sıfır basmak yok)
    if btc_oi.get('oi_chg_7d') is not None:
        btc_oi_chg_val, btc_oi_cls = _fmt_change(btc_oi['oi_chg_7d'])
        btc_oi_chg = f'&nbsp;<span class="{btc_oi_cls}">{btc_oi_chg_val}</span>'
    else:
        btc_oi_chg = ""
        
    if eth_oi.get('oi_chg_7d') is not None:
        eth_oi_chg_val, eth_oi_cls = _fmt_change(eth_oi['oi_chg_7d'])
        eth_oi_chg = f'&nbsp;<span class="{eth_oi_cls}">{eth_oi_chg_val}</span>'
    else:
        eth_oi_chg = ""
    
    fb_btc = fb.get('btc_basis', 0)
    fb_eth = fb.get('eth_basis', 0)

    basis_column_html = f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
      <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Futures Term Structure</div>
      <table width="100%" style="border-collapse:collapse; font-size:12px;">
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:8px 0; color:var(--dim);">BTC Futures Basis</td><td class="mono" align="right" style="color:var(--text); font-weight:600; padding:8px 0;">{fb_btc:.2f}%</td></tr>
        <tr><td style="padding:8px 0; color:var(--dim);">ETH Futures Basis</td><td class="mono" align="right" style="color:var(--text); font-weight:600; padding:8px 0;">{fb_eth:.2f}%</td></tr>
      </table>
    </div>
    '''

    # Build 3 positioning cards using flexbox
    positioning_cards = []
    positioning_cards.append(f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px; flex:1; min-width:180px;">
      <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">7D Avg Funding Rates</div>
      <table width="100%" style="border-collapse:collapse; font-size:12px;">
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC 7D Avg</td><td class="mono {btc_fr_cls}" align="right">{btc_fr_str}</td></tr>
        <tr><td style="padding:6px 0; color:var(--dim);">ETH 7D Avg</td><td class="mono {eth_fr_cls}" align="right">{eth_fr_str}</td></tr>
      </table>
    </div>''')
    
    positioning_cards.append(f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px; flex:1; min-width:180px;">
      <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Open Interest w/w Change</div>
      <table width="100%" style="border-collapse:collapse; font-size:12px;">
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC OI Change</td><td class="mono" align="right">{btc_oi_str}{btc_oi_chg}</td></tr>
        <tr><td style="padding:6px 0; color:var(--dim);">ETH OI Change</td><td class="mono" align="right">{eth_oi_str}{eth_oi_chg}</td></tr>
      </table>
    </div>''')
    
    # 25Δ Risk Reversal Card
    risk_reversal_25d = options_data.get('risk_reversal_25d')
    rr_expiry = options_data.get('risk_reversal_expiry')
    if risk_reversal_25d is not None:
        rr_color = "var(--green)" if risk_reversal_25d >= 0 else "var(--red)"
        positioning_cards.append(f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px; text-align:center; flex:1; min-width:180px;">
          <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">{STR['card_risk_reversal'][lang]}</div>
          <div style="font-family:var(--mono); font-size:16px; font-weight:700; color:{rr_color}; margin-bottom:6px;">{risk_reversal_25d:+.2f}%</div>
          <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">Call IV - Put IV ({rr_expiry})</div>
        </div>''')

    positioning_cards_html = f'''
    <div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:20px; page-break-inside:avoid; break-inside:avoid;">
      {"".join(positioning_cards)}
    </div>
    '''

    # Large Options Expirations Table
    large_exp = options_data.get('large_expirations', [])
    large_exp_html = ""
    if large_exp:
        rows = []
        for item in large_exp:
            notional_str = fmt_notional(item['notional'])
            max_pain_str = f"${item['max_pain']:,.0f}" if item['max_pain'] is not None else "—"
            rows.append(f'''
            <tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
              <td style="padding:8px 0; font-weight:600; color:var(--text);">{item['expiry']} <span style="font-size:10px; color:var(--dim); font-weight:normal;">({item['date_str']})</span></td>
              <td class="mono" align="right" style="color:var(--text); font-weight:600; padding:8px 0;">{notional_str}</td>
              <td class="mono" align="right" style="color:var(--text); font-weight:600; padding:8px 0;">{max_pain_str}</td>
            </tr>''')
            
        large_exp_html = f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px; margin-bottom:20px; page-break-inside:avoid; break-inside:avoid;">
          <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">{STR['section_large_expirations'][lang]}</div>
          <table width="100%" style="border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); text-align:left;">
                <th style="padding:6px 0; color:var(--dim); font-weight:600;">{STR['col_expiry_date'][lang]}</th>
                <th style="padding:6px 0; color:var(--dim); font-weight:600; text-align:right;">{STR['col_total_notional'][lang]}</th>
                <th style="padding:6px 0; color:var(--dim); font-weight:600; text-align:right;">{STR['col_max_pain_strike'][lang]}</th>
              </tr>
            </thead>
            <tbody>
              {"".join(rows)}
            </tbody>
          </table>
        </div>
        '''

    positioning_html = f'''
    {render_section_divider(STR['section_positioning'][lang])}
    
    {cp_card_html}
    
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px; page-break-inside:avoid; break-inside:avoid;">
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">{STR['card_fng'][lang]}</div>
        {fng_gauge}
      </div>
      {basis_column_html}
    </div>
    
    {positioning_cards_html}
    
    {large_exp_html}
    '''
    
    if futures_note:
        positioning_html += f'''
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold); border-radius:0 4px 4px 0; page-break-inside:avoid; break-inside:avoid;">
          <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {futures_note}
        </div>'''

    # 18. Stories (Weekly News)
    stories_html = ""
    macro_news = data.get('macro_news', {})
    news_note = lang_data.get('notes', {}).get('news_note') or data.get('news_note', '')
    if macro_news:
        stories_html = f'''
        {render_section_divider(STR['section_stories'][lang])}
        {render_news_section(macro_news, lang_data.get('insights'), lang=lang)}'''
        
        if news_note:
            stories_html += f'''
            <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold2); border-radius:0 4px 4px 0; page-break-inside:avoid; break-inside:avoid;">
              <strong style="color:var(--text);">{STR['analyst_note'][lang]}:</strong> {news_note}
            </div>'''

    # Footer
    footer_html = render_footer(lang=lang, is_weekly=True)

    # Combine everything
    content_html = f'''
    {header_html}
    {themes_html}
    {calendar_weekly_html}
    {liq_html}
    {macro_scoreboard_html}
    {equities_html}
    {sectors_html}
    <div style="margin-top:16px;"></div>
    {ytd_html}
    {turkey_html}
    {crypto_divider}
    {stablecoin_html}
    {etf_weekly_html}
    {winners_losers_html}
    {watchlist_html}
    {rotation_html}
    {cycle_html}
    {correlation_html}
    {positioning_html}
    {stories_html}
    {footer_html}
    '''

    return html_wrapper(
        title="Weekly Strategic Analysis" if lang == 'tr' else "Weekly Deep Dive Bulletin",
        content=content_html,
        accent_color=gold_color
    )
