# render/weekly.py
from datetime import datetime
from render.tokens import STYLE_TOKENS
from render.svg import (
    generate_sparkline, generate_fear_greed_gauge_svg,
    generate_winners_losers_chart, generate_correlation_matrix_svg,
    generate_cycle_heatmap_svg, generate_net_liquidity_chart,
    generate_inflation_chart, generate_ytd_comparison_chart,
    generate_stablecoin_mcap_share_chart, generate_etf_flow_chart
)
from render.components import (
    html_wrapper, render_header, render_ticker, render_regime_strip,
    render_section_divider, render_economic_calendar, render_asset_table,
    render_news_section, render_footer, _fmt_change, _fmt_price
)

def render_weekly(data):
    """Assemble and compile sections for the Weekly edition."""
    accent_color = STYLE_TOKENS['colors']['accent']
    gold_color = STYLE_TOKENS['colors']['gold']
    
    # 1. Header
    header_html = render_header(
        title="WEEKLY DEEP DIVE",
        sub_title="Strategic Liquidity, Macro Themes & Crypto Rotation",
        accent_color=gold_color, # Gold accent for weekly
        fng_data=data.get('fear_and_greed')
    )
    
    # 2. Weekly Themes (AI Generated)
    themes_html = ""
    themes = data.get('weekly_themes', [])
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
        {render_section_divider("Haftanın Üç Teması", "🔑")}
        {''.join(theme_items)}
        '''
        
    # 3. Liquidity Regime
    liq_html = ""
    net_liq = data.get('net_liquidity_history_data', [])
    m2 = data.get('m2_money_supply', {})
    if net_liq:
        liq_chart = generate_net_liquidity_chart(net_liq)
        liq_note = data.get('liquidity_note', 'Fed Net Likiditesi küresel piyasalar için kritik bir göstergedir.')
        liq_html = f'''
        {render_section_divider("Likidite Rejimi", "💧")}
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">US Federal Reserve Net Liquidity (3-Year Weekly)</div>
          {liq_chart}
        </div>
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
          <strong style="color:var(--text);">Liquidity Analyst Note:</strong> {liq_note}
        </div>
        '''

    # 4. Macro Scoreboard & Inflation Path
    macro_scoreboard_html = ""
    ms = data.get('macro_scoreboard', {}) or {}
    inflation_history = data.get('inflation_history_data', [])
    if ms or inflation_history:
        dxy = ms.get('DXY', 0.0)
        dxy_chg = ms.get('DXY_chg', 0.0)
        dxy_txt, dxy_cls = _fmt_change(dxy_chg)
        
        m2_supply = ms.get('M2', 0.0)
        m2_chg = ms.get('M2_chg', 0.0)
        m2_txt, m2_cls = _fmt_change(m2_chg)
        
        hy_oas = ms.get('HY_OAS', 0.0)
        hy_chg = ms.get('HY_OAS_chg_bp', 0.0)
        hy_txt = f"{hy_chg:+.1f} bps"
        hy_cls = 'down' if hy_chg > 0 else 'up' # BP widening is negative (down/red), narrowing is positive (up/green)
        
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
        inflation_note = data.get('inflation_note', 'Enflasyon patikası %2 hedefinin üzerinde kalmaya devam ediyor.')
        
        macro_scoreboard_html = f'''
        {render_section_divider("Macro Scoreboard", "🌍")}
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:20px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">DXY (Dollar Index)</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{dxy:.2f}</div>
            <div class="{dxy_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{dxy_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">US 10Y Yield</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{yield_10y:.2f}%</div>
            <div style="font-family:var(--mono); font-size:10px; color:var(--dim); margin-top:2px;">Consolidated</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">2s10s Spread</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{spread_2s10s:.2f}%</div>
            <div class="{spread_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{spread_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">HY Credit Spread</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{hy_oas:.2f}%</div>
            <div class="{hy_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{hy_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">MOVE Index</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{move_idx:.1f}</div>
            <div class="{move_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{move_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">VIX Index</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{vix:.1f}</div>
            <div class="{vix_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{vix_txt}</div>
          </div>
        </div>
        
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">US Inflation Path (CPI, Core CPI, Core PCE YoY - 5-Year)</div>
          {inflation_chart}
        </div>
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold); border-radius:0 4px 4px 0;">
          <strong style="color:var(--text);">Inflation Analysis Note:</strong> {inflation_note}
        </div>
        '''

    # 5. Equities & Commodities (Weekly)
    equities_html = ""
    mag7 = data.get('magnificent_7', [])
    commodities = data.get('commodities', [])
    if mag7 or commodities:
        mag7_table = render_asset_table(mag7, "equities") if mag7 else ""
        comm_table = render_asset_table(commodities, "commodities") if commodities else ""
        equities_html = f'''
        {render_section_divider("Equities & Commodities (7D/30D/YTD)", "📈")}
        {mag7_table}
        <div style="margin-top:16px;"></div>
        {comm_table}
        '''

    # 6. S&P 500 Sectors
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
          <span style="font-size:9px; letter-spacing:1px; text-transform:uppercase; color:var(--dim); font-weight:600;">📊 S&P 500 Sector Map (Weekly Performance)</span>
          <div style="flex:1; height:0.5px; background:var(--border);"></div>
        </div>
        <div class="sp500-grid">
          {''.join(tiles)}
        </div>
        '''

    # 7. BTC vs NDX vs Gold YTD
    ytd_html = ""
    ytd_comp = data.get('ytd_comparison_data', {})
    if ytd_comp:
        ytd_html = generate_ytd_comparison_chart(ytd_comp)

    # 8. Turkey Desk
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
        # For weekly, we estimate USD change as BIST change minus USDTRY change
        bist_usd_chg = bist_chg - try_chg
        usd_bist_txt, usd_bist_cls = _fmt_change(bist_usd_chg)
        
        turkey_html = f'''
        {render_section_divider("Türkiye Masası", "🇹🇷")}
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
    crypto_divider = render_section_divider("KRİPTO MASASI (WEEKLY DEEP DIVE)", "⚡")

    # 9. Stablecoin Supply
    stablecoin_html = ""
    stable_history = data.get('stablecoin_history_data', [])
    stable_note = data.get('stablecoin_note', 'USDT ve USDC arzlarındaki değişim kripto piyasası likiditesi için öncüdür.')
    if stable_history:
        stable_chart = generate_stablecoin_mcap_share_chart(stable_history)
        stablecoin_html = f'''
        {render_section_divider("Stablecoin Supply & Share", "🪙")}
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">Stablecoin Market Cap & USDT/USDC Shares (3-Year Weekly)</div>
          {stable_chart}
        </div>
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--green); border-radius:0 4px 4px 0;">
          <strong style="color:var(--text);">Stablecoin Analysis Note:</strong> {stable_note}
        </div>
        '''

    # 10. ETF Weekly Flows
    etf_weekly_html = ""
    etf_weekly_history = data.get('etf_weekly_history_data', [])
    etf_note = data.get('etf_note', 'Spot Bitcoin ETF akışları kurumsal ilgiyi ölçer.')
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
        {render_section_divider("ETF Weekly Net Flows", "📥")}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:24px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">ETF Weekly Net Flows</div>
              <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">Week ending {w_date}</div>
            </div>
          </div>
          <div style="display:flex; gap:28px; margin-bottom:16px;">
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">Weekly Total</div>
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
            <div style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--dim); margin-bottom:10px;">Bitcoin Spot ETF Weekly Net Flows ($ Millions)</div>
            {etf_chart}
          </div>
          <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; background:var(--bg3); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
            <strong style="color:var(--text);">ETF Analysis Note:</strong> {etf_note}
          </div>
        </div>
        '''

    # 11. Winners & Losers
    winners_losers_html = ""
    winners = data.get('winners', [])
    losers = data.get('losers', [])
    if winners or losers:
        wl_chart = generate_winners_losers_chart(winners, losers)
        winners_losers_html = f'''
        {render_section_divider("Haftanın Kazananları & Kaybedenleri", "⚔️")}
        <div class="sparkline-wrap" style="padding:20px 24px; margin-bottom:24px;">
          {wl_chart}
        </div>
        '''

    # 12. Watchlist Weekly
    watchlist_html = ""
    crypto_prices = data.get('crypto_prices', [])
    if crypto_prices:
        watchlist_html = f'''
        {render_section_divider("Crypto Watchlist (7D/30D/YTD)", "🔍")}
        {render_asset_table(crypto_prices, "crypto")}
        '''

    # 13. Crypto Sector Rotation
    rotation_html = ""
    rotation_data = data.get('crypto_sector_rotation_data', {})
    rotation_note = data.get('rotation_note', 'Kripto alt sektörleri arasındaki rotasyon eğilimleri.')
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
        {render_section_divider("Kripto Sektör Rotasyonu (7D Avg)", "🔄")}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; overflow:hidden; padding:12px; margin-bottom:24px;">
          <table width="100%" style="border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border);"><th style="text-align:left; padding:8px 12px; color:var(--dim);">Sector Category</th><th style="text-align:right; padding:8px 12px; color:var(--dim);">7D Basket Avg Return</th></tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <div style="font-family:var(--sans); font-size:11px; color:var(--dim); line-height:1.5; margin-top:12px;">
            <strong style="color:var(--gold2);">Note:</strong> {rotation_note}
          </div>
        </div>
        '''

    # 14. Cycle Panel
    cycle_html = ""
    cycle = data.get('btc_cycle_metrics', {})
    cycle_note = data.get('cycle_note', 'Bitcoin döngüsel göstergeleri uzun vadeli dipleri ve zirveleri analiz eder.')
    if cycle:
        spot = cycle.get('spot', 0)
        wma = cycle.get('wma200', 0)
        mm = cycle.get('mayer_multiple', 1.0)
        drawdown = cycle.get('drawdown', 0.0)
        dist_wma = cycle.get('distance_to_200wma', 0.0)
        
        heatmap_svg = generate_cycle_heatmap_svg(cycle.get('monthly_heatmap'))
        
        cycle_html = f'''
        {render_section_divider("Bitcoin Döngü Paneli", "🔄")}
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:20px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">Mayer Multiple</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{mm:.3f}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">Spot / 200d SMA</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">200WMA Distance</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{dist_wma:+.1f}%</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">WMA: ${wma:,.0f}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">Drawdown from ATH</div>
            <div class="down" style="font-family:var(--mono); font-size:16px; font-weight:600;">{drawdown:.1f}%</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">ATH: ${cycle.get("ath", 0):,.0f}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">BTC Spot Price</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">${spot:,.0f}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">Real-time</div>
          </div>
        </div>
        
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">Bitcoin Monthly Return Heatmap (2024-2026)</div>
          {heatmap_svg}
          <div style="font-size:9px; color:var(--dim); margin-top:6px; text-align:right;">* Current month is marked.</div>
        </div>
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold2); border-radius:0 4px 4px 0;">
          <strong style="color:var(--text);">Cycle Analysis Note:</strong> {cycle_note}
        </div>
        '''

    # 15. Correlation Matrix
    correlation_html = ""
    corr = data.get('correlation_matrix', {})
    corr_note = data.get('correlation_note', 'BTC ve makro varlıklar arasındaki rolling 30 günlük günlük getiri korelasyonu.')
    if corr:
        corr_chart = generate_correlation_matrix_svg(corr)
        correlation_html = f'''
        {render_section_divider("Korelasyon Matrisi", "🤝")}
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:12px;">Macro & Crypto Assets Correlation Matrix (30-Day Rolling Daily Returns)</div>
          {corr_chart}
        </div>
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--accent); border-radius:0 4px 4px 0;">
          <strong style="color:var(--text);">Correlation Analysis Note:</strong> {corr_note}
        </div>
        '''

    # 16. Futures Positioning Desk
    positioning_html = ""
    fr = data.get('funding_rates', {}) or {}
    oi = data.get('open_interest', {}) or {}
    fb = data.get('crypto_futures_basis', {}) or {}
    futures_note = data.get('futures_note', 'Vadeli yapı ve konumlanma analizleri kaldıraç durumunu gösterir.')
    
    btc_fr_str, btc_fr_cls = _fmt_change(fr.get('BTC', 0.0))
    eth_fr_str, eth_fr_cls = _fmt_change(fr.get('ETH', 0.0))
    
    def fmt_oi_val(val):
        if not val: return '—'
        return f"{val/1000:.1f}K" if val < 1e6 else f"{val/1e6:.2f}M"
        
    btc_oi_str = fmt_oi_val(oi.get('BTC', {}).get('oi'))
    eth_oi_str = fmt_oi_val(oi.get('ETH', {}).get('oi'))
    btc_oi_chg, btc_oi_cls = _fmt_change(oi.get('BTC', {}).get('oi_chg_24h', 0))
    eth_oi_chg, eth_oi_cls = _fmt_change(oi.get('ETH', {}).get('oi_chg_24h', 0))
    
    fb_btc = fb.get('btc_basis', 0)
    fb_eth = fb.get('eth_basis', 0)

    positioning_html = f'''
    {render_section_divider("Vadeli Yapı & Konumlanma", "🎯")}
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px;">
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">7D Avg Funding Rates</div>
        <table width="100%" style="border-collapse:collapse; font-size:12px;">
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC 7D Avg</td><td class="mono {btc_fr_cls}" align="right">{btc_fr_str}</td></tr>
          <tr><td style="padding:6px 0; color:var(--dim);">ETH 7D Avg</td><td class="mono {eth_fr_cls}" align="right">{eth_fr_str}</td></tr>
        </table>
      </div>
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Open Interest w/w Change</div>
        <table width="100%" style="border-collapse:collapse; font-size:12px;">
          <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC OI Change</td><td class="mono" align="right">{btc_oi_str} &nbsp;<span class="{btc_oi_cls}">{btc_oi_chg}</span></td></tr>
          <tr><td style="padding:6px 0; color:var(--dim);">ETH OI Change</td><td class="mono" align="right">{eth_oi_str} &nbsp;<span class="{eth_oi_cls}">{eth_oi_chg}</span></td></tr>
        </table>
      </div>
    </div>
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px; margin-bottom:20px;">
      <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Futures Term Structure (Annualized Premium)</div>
      <table width="100%" style="border-collapse:collapse; font-size:12px;">
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:6px 0; color:var(--dim);">BTC Futures Basis (Current)</td><td class="mono" align="right" style="color:var(--text); font-weight:600;">{fb_btc:.2f}%</td></tr>
        <tr><td style="padding:6px 0; color:var(--dim);">ETH Futures Basis (Current)</td><td class="mono" align="right" style="color:var(--text); font-weight:600;">{fb_eth:.2f}%</td></tr>
      </table>
    </div>
    <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-bottom:24px; background:var(--bg2); padding:10px 14px; border-left:3px solid var(--gold); border-radius:0 4px 4px 0;">
      <strong style="color:var(--text);">Futures Analysis Note:</strong> {futures_note}
    </div>
    '''

    # 17. Next Week Calendar & Unlocks & Weekly strategy note
    calendar_weekly_html = ""
    events = data.get('economic_calendar', [])
    strategy_note = data.get('week_plan_note', 'Önümüzdeki hafta piyasa beklentileri ve haftalık plan.')
    if events or strategy_note:
        calendar_weekly_html = f'''
        {render_section_divider("Önümüzdeki Hafta", "📅")}
        {render_economic_calendar(events)}
        <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6; margin-top:16px; background:var(--bg2); padding:14px 18px; border-left:3px solid var(--gold2); border-radius:0 4px 4px 0; page-break-inside: avoid; break-inside: avoid;">
          <strong style="color:var(--text);">Weekly Outlook & Strategy:</strong> {strategy_note}
        </div>
        '''

    # Footer
    footer_html = render_footer()

    # Combine everything
    content_html = f'''
    {header_html}
    {themes_html}
    {liq_html}
    {macro_scoreboard_html}
    {equities_html}
    {sectors_html}
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
    {calendar_weekly_html}
    {footer_html}
    '''

    return html_wrapper(
        title="Weekly Deep Dive Bulletin",
        content=content_html,
        accent_color=gold_color
    )
