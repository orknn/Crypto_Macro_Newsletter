# render/weekly.py
from datetime import datetime
from render.tokens import STYLE_TOKENS
from render.svg import (
    generate_sparkline, generate_fear_greed_gauge_svg,
    generate_winners_losers_chart, generate_correlation_matrix_svg,
    generate_cycle_heatmap_svg, generate_net_liquidity_chart,
    generate_inflation_chart, generate_ytd_comparison_chart,
    generate_stablecoin_mcap_share_chart, generate_etf_flow_chart,
    generate_coinbase_premium_chart, generate_nfci_chart,
    generate_cumulative_flow_chart
)
from render.components import (
    html_wrapper, render_header, render_ticker, render_regime_strip,
    render_section_divider, render_economic_calendar, render_asset_table,
    render_news_section, render_footer, _fmt_change, _fmt_price, _fmt_funding,
    render_coinbase_premium_card, maybe, render_fed_strip, na, _na,
    series_as_of_label, render_analyst_note, normalize_note
)
from render.i18n import STR, tr_upper

# A data section whose analyst note has no "so what" is dropped whole rather
# than printed bare. The brief's rule, and the point of the redesign: a chart
# with no reading is the market-data dump this is meant to stop being.
#
# It is a real trade — a weak model run now costs sections rather than
# producing thin ones — so it is one constant. Setting this False restores the
# old behaviour of printing the section without its note.
REQUIRE_SO_WHAT = True


# The four assets the report always discusses, plus whatever actually moved.
WATCHLIST_CORE = ('BTC', 'ETH', 'SOL', 'XRP')


def _weekly_watchlist(rows, limit=6):
    """Six rows: the four constants plus the week's best and worst.

    Ten rows of which six never got mentioned is a table nobody finishes. The
    two variable slots are the only ones that carry news, so they are chosen by
    what happened rather than by market cap.
    """
    if not rows:
        return []
    core = [r for sym in WATCHLIST_CORE
            for r in rows if r.get('Symbol') == sym]
    rest = [r for r in rows if r not in core
            and isinstance(r.get('7d %'), (int, float))]
    if rest:
        ranked = sorted(rest, key=lambda r: r['7d %'])
        extras = [ranked[-1]]                      # best
        if len(ranked) > 1:
            extras.append(ranked[0])               # worst
    else:
        extras = []
    return (core + extras)[:limit]


def _group(title, *sections):
    """A page heading and its sections, or '' when every section is empty.

    Sections drop themselves for two reasons now — no data, or no reading to
    print beside the data — so a heading has to earn its place from what
    survived rather than from the layout.
    """
    body = ''.join(part for part in sections if part and part.strip())
    if not body.strip():
        return ''
    return f"{render_section_divider(title)}\n{body}"


def _section_with_note(section_html, note, lang, accent):
    """Section plus its two-line note, or '' when the note has no `so_what`."""
    note_html = render_analyst_note(note, lang, accent)
    if note_html:
        return section_html + note_html
    return '' if REQUIRE_SO_WHAT else section_html


def _num(value, spec, prefix='', suffix='', lang='tr'):
    """A formatted number, or the one rendering of a missing one.

    Every tile in this file goes through here. The alternative — an inline
    conditional per tile — is how "MOVE 0.0", "$0.00" and a 1.000 Mayer
    multiple all reached print: each of those was a per-tile default that
    looked reasonable in isolation.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return na(lang)
    if value != value:  # NaN
        return na(lang)
    return f"{prefix}{format(value, spec)}{suffix}"


def fmt_notional(val, lang='tr'):
    if _na(val) or not val: return na(lang)
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    elif val >= 1e6:
        return f"${val/1e6:.1f}M"
    else:
        return f"${val:,.0f}"

def render_weekly(data, lang='tr', theme=None):
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
        lang=lang,
        as_of=data.get('as_of'),
    )
    
    # 1b. Regime Strip + Executive Summary (AI Generated)
    lang_data = data.get(lang, {}) or {}
    regime = data.get('regime', 'NEUTRAL')
    regime_line = lang_data.get('regime_line', '')
    regime_html = ""
    if regime and regime != 'NEUTRAL':
        regime_html = render_regime_strip(regime, regime_line, lang=lang)
    elif regime_line and regime_line.strip() and regime_line.strip() != 'None':
        regime_html = render_regime_strip(regime, regime_line, lang=lang)

    overview_html = ""
    overview_text = lang_data.get('overview', '')
    if overview_text and str(overview_text).strip() and str(overview_text).strip() != 'None':
        overview_html = f'''
        <div class="summary-card">
          <p class="summary-text">{overview_text}</p>
        </div>
        '''

    # 2. Weekly Themes (AI Generated)
    themes_html = ""
    # weekly_themes holds the TR themes — never fall back to it in the EN edition.
    themes = lang_data.get('themes', []) or (data.get('weekly_themes', []) if lang == 'tr' else [])
    if themes:
        theme_items = []
        for i, t in enumerate(themes[:3]):
            theme_title = t.get('title', '')
            if lang == 'tr':
                theme_title = tr_upper(theme_title)

            theme_items.append(f'''
            <div style="background:var(--bg2); border:1px solid var(--border); border-radius:6px; padding:16px; margin-bottom:12px;">
              <div style="font-family:var(--sans); font-size:11px; font-weight:700; color:var(--gold2); text-transform:uppercase; margin-bottom:6px; letter-spacing:0.5px;"><span style="color:var(--dim); font-weight:600;">{STR['theme'][lang]} {i+1} ·</span> {theme_title}</div>
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
    if events or normalize_note(strategy_note):
        source_date = None
        if events:
            for ev in events:
                if ev.get('source_date'):
                    source_date = ev.get('source_date')
                    break
                    
        title = STR['section_calendar_weekly'][lang]
        if source_date:
            title += f" (önceki veri · {source_date})" if lang == 'tr' else f" (previous data · {source_date})"
            
        # The group heading above says "what matters next"; a second heading
        # saying the same thing is a line of vertical space for nothing.
        calendar_weekly_html = f'''
        {render_fed_strip(data.get('fed_pricing'), lang=lang)}'''
        if source_date:
            calendar_weekly_html += (
                f'<div style="font-size:9.5px; color:var(--dim); '
                f'margin:-6px 0 10px;">{title}</div>')
        if events:
            calendar_weekly_html += f'''
        {render_economic_calendar(events, lang=lang)}'''
        
        calendar_weekly_html += render_analyst_note(strategy_note, lang, 'var(--gold2)')
        
    # 4. Liquidity Regime
    liq_html = ""
    net_liq = data.get('net_liquidity_history_data', [])
    nfci = data.get('nfci') or {}
    if net_liq or nfci.get('history'):
        liq_html = render_section_divider(STR['section_liquidity'][lang])
        liq_note = lang_data.get('notes', {}).get('liquidity_note') or data.get('liquidity_note', '')

        if net_liq:
            liq_chart = generate_net_liquidity_chart(net_liq)
            # Fed net liquidity is a weekly release; the run's cut says nothing
            # about when this series last moved, so it carries its own date.
            liq_asof = series_as_of_label(net_liq[-1].get('date'), lang)
            liq_html += f'''
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">{STR['chart_net_liq_title'][lang]}{liq_asof}</div>
          {liq_chart}
        </div>'''

        if nfci.get('history'):
            nfci_chart = generate_nfci_chart(nfci['history'])
            nfci_val = nfci.get('current')
            nfci_chg = nfci.get('chg_1w')
            nfci_stat = ""
            if nfci_val is not None:
                chg_str = f" ({nfci_chg:+.3f} w/w)" if nfci_chg is not None else ""
                nfci_stat = f'<span style="font-family:var(--mono); font-size:12px; color:var(--gold); font-weight:600;">{nfci_val:+.3f}{chg_str}</span>'
            liq_html += f'''
        <div class="sparkline-wrap" style="margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div style="font-size:12.5px; font-weight:600; color:var(--text);">{STR['chart_nfci_title'][lang]}{series_as_of_label((nfci.get('history') or [{}])[-1].get('date'), lang)}</div>
            {nfci_stat}
          </div>
          {nfci_chart}
          <div style="font-size:9.5px; color:var(--dim); margin-top:6px;">{STR['nfci_hint'][lang]}</div>
        </div>'''

        liq_html = _section_with_note(liq_html, liq_note, lang, 'var(--accent)')

    # 5. Macro Scoreboard & Inflation Path
    macro_scoreboard_html = ""
    ms = data.get('macro_scoreboard', {}) or {}
    inflation_history = data.get('inflation_history_data', [])
    if ms or inflation_history:
        # Every tile prints N/A when its metric is missing. Defaulting to 0.0
        # published "DXY 0.00" and "VIX 0.0" as if they had been measured.
        def _val(v, fmt):
            return _num(v, fmt, lang=lang)

        dxy = ms.get('DXY')
        dxy_chg = ms.get('DXY_chg')
        dxy_txt, dxy_cls = _fmt_change(dxy_chg, lang)

        hy_oas = ms.get('HY_OAS')
        hy_chg = ms.get('HY_OAS_chg_bp')
        hy_txt = f"{hy_chg:+.1f} bps" if hy_chg is not None else na(lang)
        hy_cls = '' if hy_chg is None else ('down' if hy_chg > 0 else 'up')

        move_idx = ms.get('MOVE')
        move_chg = ms.get('MOVE_chg')
        move_txt, move_cls = _fmt_change(move_chg, lang)

        macro_indicators_data = data.get('macro_indicators', {}) or {}
        vix = macro_indicators_data.get('VIX')
        vix_chg = macro_indicators_data.get('VIX_chg')
        vix_txt, vix_cls = _fmt_change(vix_chg, lang)
        
        yield_10y = macro_indicators_data.get('US 10-Year Treasury Yield')
        yield_10y_chg = macro_indicators_data.get('US 10-Year Treasury Yield_chg')
        # bps, not a percentage: the value is now a basis-point change, and
        # printing it with a % sign is exactly the confusion T9 is about.
        if yield_10y_chg is None:
            yield_10y_chg_txt, yield_10y_chg_cls = na(lang), ''
        else:
            yield_10y_chg_txt = f"{yield_10y_chg:+.1f} bps"
            yield_10y_chg_cls = 'down' if yield_10y_chg > 0 else 'up'

        # The 2s10s tile shows a LEVEL. It used to feed that level to
        # _fmt_change as well, so the same number appeared twice on one tile —
        # once as "0.41%" and once as "▲ +0.41%", inventing a weekly move out
        # of a spread reading. The sub-line now carries the unit instead of a
        # fabricated change; see MetricSpec unit=PERCENT vs PERCENT_CHANGE.
        spread_2s10s = macro_indicators_data.get('2s10s_spread')
        spread_txt = (STR['label_level'][lang] if spread_2s10s is not None
                      else na(lang))
        spread_cls = ''
        
        inflation_chart = generate_inflation_chart(inflation_history, lang=lang) if inflation_history else ""
        inflation_note = lang_data.get('notes', {}).get('inflation_note') or data.get('inflation_note', '')

        # Extra tiles: 10Y real yield, 10Y breakeven, copper/gold ratio
        rates = data.get('rates_breakevens') or {}
        rates_tiles = []
        if rates.get('real_10y') is not None:
            chg_bp = rates.get('real_10y_chg_bp', 0.0)
            cls = 'down' if chg_bp > 0 else 'up'  # rising real yields = risk headwind
            rates_tiles.append(f'''
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_real_yield'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{rates['real_10y']:.2f}%</div>
            <div class="{cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{chg_bp:+.1f} bps</div>
          </div>''')
        if rates.get('breakeven_10y') is not None:
            chg_bp = rates.get('breakeven_10y_chg_bp', 0.0)
            rates_tiles.append(f'''
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_breakeven'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{rates['breakeven_10y']:.2f}%</div>
            <div style="font-family:var(--mono); font-size:10px; color:var(--dim); margin-top:2px;">{chg_bp:+.1f} bps</div>
          </div>''')
        cg = ms.get('COPPER_GOLD')
        if cg is not None:
            cg_chg = ms.get('COPPER_GOLD_chg')
            cg_cls = '' if cg_chg is None else ('up' if cg_chg >= 0 else 'down')
            # Copper bid over gold is the growth signal; the reverse is the
            # slowdown one. The label used to be a constant, so a -5.75% week
            # was published as "büyüme sinyali".
            if cg_chg is None:
                cg_label = STR['growth_signal'][lang]
            else:
                cg_label = (STR['growth_signal'][lang] if cg_chg >= 0
                            else STR['growth_slowdown_signal'][lang])
            rates_tiles.append(f'''
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_copper_gold'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{cg:.3f}</div>
            <div class="{cg_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{f"{cg_chg:+.2f}%" if cg_chg is not None else na(lang)} · {cg_label}</div>
          </div>''')
        rates_tiles_html = ''.join(rates_tiles)
        
        macro_scoreboard_html = f'''
        {render_section_divider(STR['section_macro_scoreboard'][lang])}
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:20px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_dxy'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_val(dxy, '.2f')}</div>
            <div class="{dxy_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{dxy_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_10y_yield'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_val(yield_10y, '.2f')}%</div>
            <div class="{yield_10y_chg_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{yield_10y_chg_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_spread'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_val(spread_2s10s, '.2f')}%</div>
            <div class="{spread_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{spread_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_hy_spread'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_val(hy_oas, '.2f')}%</div>
            <div class="{hy_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{hy_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_move'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_val(move_idx, '.1f')}</div>
            <div class="{move_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{move_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_vix_index'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_val(vix, '.1f')}</div>
            <div class="{vix_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{vix_txt}</div>
          </div>
          {rates_tiles_html}
        </div>
        
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">{STR['chart_inflation_title'][lang]}{series_as_of_label(inflation_history[-1].get('date') if inflation_history else None, lang)}</div>
          {inflation_chart}
        </div>'''
        
        macro_scoreboard_html = _section_with_note(macro_scoreboard_html, inflation_note, lang, 'var(--gold)')

    # 6. Equities & Commodities (Weekly)
    equities_html = ""
    mag7 = data.get('magnificent_7', [])
    commodities = data.get('commodities', [])
    asset_sparklines = data.get('asset_sparklines', {})
    if mag7 or commodities:
        # Seven rows of megacap prices restated a single fact: whether big tech
        # was bid. One line says it, and the names that moved say the rest.
        mag7_line = ""
        if mag7:
            moves = [(m.get('Symbol', ''), m.get('Change %')) for m in mag7]
            moves = [(sym, chg) for sym, chg in moves
                     if isinstance(chg, (int, float)) and not isinstance(chg, bool)]
            if moves:
                avg = sum(c for _, c in moves) / len(moves)
                best = max(moves, key=lambda x: x[1])
                worst = min(moves, key=lambda x: x[1])
                avg_txt, avg_cls = _fmt_change(avg, lang)
                best_txt, best_cls = _fmt_change(best[1], lang)
                worst_txt, worst_cls = _fmt_change(worst[1], lang)
                spark = generate_sparkline(asset_sparklines.get('NVDA') or [], 90, 22)
                mag7_line = f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:14px 16px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; page-break-inside:avoid; break-inside:avoid;">
          <div>
            <div style="font-size:9.5px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:4px;">MAGNIFICENT 7</div>
            <span class="{avg_cls}" style="font-family:var(--mono); font-size:16px; font-weight:700;">{avg_txt}</span>
            <span style="font-size:10.5px; color:var(--dim); margin-left:10px;">
              {STR['best'][lang]} {best[0]} <span class="{best_cls}">{best_txt}</span>
              &nbsp;·&nbsp; {STR['worst'][lang]} {worst[0]} <span class="{worst_cls}">{worst_txt}</span>
            </span>
          </div>
          <div>{spark}</div>
        </div>'''

        comm_table = render_asset_table(commodities, "commodities", lang=lang, sparklines=asset_sparklines) if commodities else ""
        equities_html = f'''
        {render_section_divider(STR['section_equities_commodities'][lang])}
        {mag7_line}
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
            chg_text, chg_cls = _fmt_change(chg, lang)
            bg = 'rgba(16,185,129,0.04)' if chg >= 0 else 'rgba(239,68,68,0.04)'
            border = 'rgba(16,185,129,0.18)' if chg >= 0 else 'rgba(239,68,68,0.18)'
            tiles.append(f'''
            <div style="background:{bg}; border:1px solid {border}; padding:8px; text-align:center; border-radius:4px;">
              <div style="font-size:9px; color:var(--dim); text-transform:uppercase; margin-bottom:2px;">{name}</div>
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
        ytd_html = generate_ytd_comparison_chart(ytd_comp, lang=lang)

    # 9. Turkey Desk
    turkey_html = ""
    bist_data = data.get('bist_try', {})
    if bist_data:
        bist100 = bist_data.get('bist100')
        bist_chg = bist_data.get('bist100_chg')
        bist_txt, bist_cls = _fmt_change(bist_chg, lang)

        usd_try = bist_data.get('usd_try')
        try_chg = bist_data.get('try_chg')
        try_txt, try_cls = _fmt_change(try_chg, lang)

        # BIST in dollars needs both legs; "$0.00" is not a fallback value.
        bist_usd = (bist100 / usd_try) if (bist100 and usd_try) else None
        bist100_txt = f"{bist100:,.0f}" if bist100 else na(lang)
        usd_try_txt = f"{usd_try:.4f}" if usd_try else na(lang)
        bist_usd_txt = f"${bist_usd:.2f}" if bist_usd else na(lang)
        # Same rule as the dollar level: a dollar-denominated move needs both
        # legs, and subtracting a missing one used to raise TypeError.
        bist_usd_chg = (bist_chg - try_chg) if (bist_chg is not None
                                                and try_chg is not None) else None
        usd_bist_txt, usd_bist_cls = _fmt_change(bist_usd_chg, lang)
        
        turkey_html = f'''
        {render_section_divider(STR['section_turkey_desk'][lang])}
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:24px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">BIST 100</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{bist100_txt}</div>
            <div class="{bist_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{bist_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">USD/TRY</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{usd_try_txt}</div>
            <div class="{try_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{try_txt}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">BIST 100 ($ Denom.)</div>
            <div style="font-family:var(--mono); font-size:16px; color:var(--text); font-weight:600;">{bist_usd_txt}</div>
            <div class="{usd_bist_cls}" style="font-family:var(--mono); font-size:10px; margin-top:2px;">{usd_bist_txt}</div>
          </div>
        </div>
        '''

    # 10. Stablecoin Supply
    stablecoin_html = ""
    stable_history = data.get('stablecoin_history_data', [])
    stable_note = lang_data.get('notes', {}).get('stablecoin_note') or data.get('stablecoin_note', '')
    if stable_history:
        stable_chart = generate_stablecoin_mcap_share_chart(stable_history)
        stablecoin_html = f'''
        {render_section_divider(STR['section_stablecoin'][lang])}
        <div class="sparkline-wrap" style="margin-bottom:12px;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">{STR['chart_stablecoin_title'][lang]}{series_as_of_label(stable_history[-1].get('date') if stable_history else None, lang)}</div>
          {stable_chart}
        </div>'''
        
        stablecoin_html = _section_with_note(stablecoin_html, stable_note, lang, 'var(--green)')

    # 11. ETF Weekly Flows
    etf_weekly_html = ""
    etf_weekly_history = data.get('etf_weekly_history_data', [])
    etf_note = lang_data.get('notes', {}).get('etf_note') or data.get('etf_note', '')
    if etf_weekly_history:
        latest_etf = etf_weekly_history[-1]
        # A missing leg is not a zero flow. 0.0 here printed "+0.0M" as a
        # measured week of no interest.
        w_total = latest_etf.get('Total_flow_m')
        w_ibit = latest_etf.get('IBIT_flow_m')
        w_fbtc = latest_etf.get('FBTC_flow_m')
        w_date = latest_etf.get('date', '')
        
        total_cls = '' if w_total is None else ("up" if w_total >= 0 else "down")
        ibit_cls = '' if w_ibit is None else ("up" if w_ibit >= 0 else "down")
        fbtc_cls = '' if w_fbtc is None else ("up" if w_fbtc >= 0 else "down")
        
        etf_chart = generate_etf_flow_chart(etf_weekly_history)

        # 2.3: the flow is shown next to what tells you how to read it. A net
        # inflow is not evidence of directional demand on its own — part of it
        # can be delta-neutral basis trade (long ETF, short futures) — and
        # funding plus open interest are what separate the two.
        prev_flow = (etf_weekly_history[-2].get('Total_flow_m')
                     if len(etf_weekly_history) > 1 else None)
        prev_txt = _num(prev_flow, '+.1f', suffix='M', lang=lang)
        prev_cls = '' if prev_flow is None else ('up' if prev_flow >= 0 else 'down')

        _eth_hdr = data.get('eth_etf_weekly_data') or []
        eth_hdr_val = _eth_hdr[-1].get('Total_flow_m') if _eth_hdr else None
        eth_hdr_txt = _num(eth_hdr_val, '+.1f', suffix='M', lang=lang)
        eth_hdr_cls = '' if eth_hdr_val is None else ('up' if eth_hdr_val >= 0 else 'down')

        _btc_funding = (data.get('funding_rates') or {}).get('BTC')
        _btc_oi_chg = ((data.get('open_interest') or {}).get('BTC') or {}).get('oi_chg_7d')
        flow_context = (
            f"BTC funding {_num(_btc_funding, '+.4f', suffix='%', lang=lang)} · "
            f"OI {STR['chg_weekly_short'][lang]} "
            f"{_num(_btc_oi_chg, '+.1f', suffix='%', lang=lang)}")
        etf_weekly_html = f'''
        {render_section_divider(STR['section_etf_flows'][lang])}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:13px; color:var(--text); font-weight:600;">{STR['card_etf_weekly_title'][lang]}</div>
              <div style="font-family:var(--mono); font-size:9px; color:var(--dim); margin-top:2px;">{STR['week_ending'][lang]} · {w_date}</div>
            </div>
          </div>
          <div style="display:flex; gap:28px; flex-wrap:wrap; margin-bottom:12px;">
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">BTC ETF</div>
              <div class="{total_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{_num(w_total, '+.1f', suffix='M', lang=lang)}</div>
            </div>
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">ETH ETF</div>
              <div class="{eth_hdr_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{eth_hdr_txt}</div>
            </div>
            <div>
              <div style="font-family:var(--sans); font-size:9px; font-weight:500; text-transform:uppercase; color:var(--dim); letter-spacing:1px; margin-bottom:4px;">{STR['prev_week'][lang]}</div>
              <div class="{prev_cls}" style="font-family:var(--mono); font-size:17px; font-weight:600;">{prev_txt}</div>
            </div>
          </div>
          <div style="font-family:var(--sans); font-size:10.5px; color:var(--dim); margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid var(--border);">
            <strong style="color:var(--text); font-weight:600;">{STR['flow_context'][lang]}:</strong> {flow_context}
            <div style="margin-top:4px; font-size:10px;">IBIT {_num(w_ibit, '+.1f', suffix='M', lang=lang)} · FBTC {_num(w_fbtc, '+.1f', suffix='M', lang=lang)}</div>
          </div>
          <div class="sparkline-wrap" style="margin-bottom:12px; padding-top:12px; border-top:1px solid var(--border);">
            <div style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--dim); margin-bottom:10px;">{STR['card_etf_weekly_history_title'][lang]}</div>
            {etf_chart}
          </div>'''

        # ETH weekly total (one-line summary under the BTC numbers)
        eth_weekly = data.get('eth_etf_weekly_data') or []
        if eth_weekly:
            ew = eth_weekly[-1]
            ew_total = ew.get('Total_flow_m', 0.0)
            ew_cls = 'up' if ew_total >= 0 else 'down'
            ew_etha = ew.get('ETHA_flow_m')
            ew_feth = ew.get('FETH_flow_m')
            ew_detail = ""
            if ew_etha is not None and ew_feth is not None:
                ew_detail = f'&nbsp;·&nbsp;<span style="color:var(--dim);">ETHA {ew_etha:+.1f}M · FETH {ew_feth:+.1f}M</span>'
            etf_weekly_html += f'''
          <div style="border-top:1px solid var(--border); padding-top:12px; margin-bottom:12px; font-family:var(--sans); font-size:11.5px; color:var(--dim);">
            <span style="font-weight:600; text-transform:uppercase; font-size:9.5px; letter-spacing:0.5px;">{STR['card_eth_etf_title'][lang].replace('Günlük', 'Haftalık') if lang == 'tr' else STR['card_eth_etf_title'][lang].replace('Daily', 'Weekly')}:</span>
            <span class="{ew_cls}" style="font-family:var(--mono); font-size:13px; font-weight:600;">&nbsp;{ew_total:+.1f}M</span>{ew_detail}
          </div>'''

        cumulative = data.get('etf_cumulative_data', [])
        if cumulative:
            cum_chart = generate_cumulative_flow_chart(cumulative)
            cum_total_b = cumulative[-1]['value'] / 1000.0
            etf_weekly_html += f'''
          <div class="sparkline-wrap" style="margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <div style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--dim);">{STR['chart_cumulative_title'][lang]}</div>
              <div style="font-family:var(--mono); font-size:12px; color:var(--green); font-weight:600;">${cum_total_b:.1f}B</div>
            </div>
            {cum_chart}
          </div>'''
          
        _etf_note_html = render_analyst_note(etf_note, lang, 'var(--accent)')
        if _etf_note_html:
            etf_weekly_html += _etf_note_html + '</div>'
        elif REQUIRE_SO_WHAT:
            etf_weekly_html = ''
        else:
            etf_weekly_html += '</div>'

    # 12. Winners & Losers — folded into ROTATION below (phase 4).
    # The same story was being told in four places: the winners chart, the
    # losers chart, the sector table and the ETH/BTC card all answer "what is
    # money moving into". One section, one answer.
    winners_losers_html = ""

    # 13. Watchlist Weekly (top 10 by market cap)
    watchlist_html = ""
    watchlist_rows = _weekly_watchlist(
        data.get('crypto_prices_display') or data.get('crypto_prices', []))
    if watchlist_rows:
        watchlist_html = f'''
        {render_section_divider(STR['section_watchlist'][lang])}
        {render_asset_table(watchlist_rows, "crypto", lang=lang)}
        '''

    # 13b. Hype Radar — removed from the PDF (phase 4).
    #
    # "TUT +93.43%" is a fact with nowhere to go: it does not feed the regime,
    # it is not referenced by any note, and a reader cannot act on it. The
    # trending list still ships in data['trending_coins'] for the web
    # dashboard; it just stops taking a page here.
    hype_html = ""

    # 14. Crypto Sector Rotation
    rotation_html = ""
    winners = data.get('winners', [])
    losers = data.get('losers', [])
    rotation_data = data.get('crypto_sector_rotation_data', {})
    rotation_note = lang_data.get('notes', {}).get('rotation_note') or data.get('rotation_note', '')

    # ETH/BTC ratio card (rotation gauge)
    eth_btc = data.get('eth_btc') or {}
    eth_btc_card = ""
    if eth_btc.get('ratio'):
        eb_chg = eth_btc.get('chg_7d')
        eb_txt, eb_cls = _fmt_change(eb_chg, lang)
        eb_spark = generate_sparkline(eth_btc.get('history', []), width=90, height=22)
        eth_btc_card = f'''
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:14px 16px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; page-break-inside:avoid; break-inside:avoid;">
          <div>
            <div style="font-size:9.5px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:4px;">{STR['card_eth_btc'][lang]}</div>
            <span style="font-family:var(--mono); font-size:17px; font-weight:700; color:var(--text);">{eth_btc['ratio']:.5f}</span>
            <span class="{eb_cls}" style="font-family:var(--mono); font-size:11px; margin-left:8px;">{eb_txt} {'(7g)' if lang == 'tr' else '(7D)'}</span>
          </div>
          <div>{eb_spark}</div>
        </div>'''

    if rotation_data:
        rows = []
        for sector, score in rotation_data.items():
            score_txt, score_cls = _fmt_change(score, lang)   # None -> N/A
            rows.append(f'''
            <tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
              <td style="padding:8px 12px; font-weight:600; color:var(--text);">{sector}</td>
              <td class="mono {score_cls}" style="padding:8px 12px; text-align:right;">{score_txt}</td>
            </tr>''')
        wl_chart = ""
        if winners or losers:
            wl_chart = f'''
        <div class="sparkline-wrap" style="padding:16px 20px; margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
          {generate_winners_losers_chart(winners, losers)}
        </div>'''

        rotation_html = f'''
        {render_section_divider(STR['section_rotation_merged'][lang])}
        {eth_btc_card}
        {wl_chart}
        <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; overflow:hidden; padding:12px; margin-bottom:24px; page-break-inside:avoid; break-inside:avoid;">
          <table width="100%" style="border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border);"><th style="text-align:left; padding:8px 12px; color:var(--dim);">{STR['col_sector'][lang]}</th><th style="text-align:right; padding:8px 12px; color:var(--dim);">{STR['col_7d_avg_return'][lang]}</th></tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>'''
          
        # The wrapper div has to close before the section can be dropped, or a
        # bare </div> escapes into the page — and an unbalanced tag makes
        # _group think the section still has content, so the heading prints
        # over nothing. Same shape as the ETF card's close.
        rotation_html += '</div>'
        rotation_html = _section_with_note(rotation_html, rotation_note, lang,
                                           'var(--gold2)')

    # 15. Cycle Panel
    cycle_html = ""
    cycle = data.get('btc_cycle_metrics', {})
    cycle_note = lang_data.get('notes', {}).get('cycle_note') or data.get('cycle_note', '')
    if cycle:
        # No `or 0` defaults here: a Mayer multiple of 1.0 and a drawdown of
        # 0.0 are both readings a reader would act on, so neither may stand in
        # for a value the pipeline does not have.
        spot = cycle.get('spot')
        wma = cycle.get('wma200')
        mm = cycle.get('mayer_multiple')
        drawdown = cycle.get('drawdown')
        dist_wma = cycle.get('distance_to_200wma')
        ath = cycle.get('ath')
        
        heatmap_svg = generate_cycle_heatmap_svg(cycle.get('monthly_heatmap'))
        
        cycle_html = f'''
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); border-radius:4px; overflow:hidden; margin-bottom:20px;">
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_mayer_multiple'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_num(mm, '.3f', lang=lang)}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">Spot / 200d SMA</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_200wma_distance'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_num(dist_wma, '+.1f', suffix='%', lang=lang)}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">WMA: {_num(wma, ',.0f', prefix='$', lang=lang)}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_drawdown'][lang]}</div>
            <div class="{'down' if drawdown is not None else ''}" style="font-family:var(--mono); font-size:15px; font-weight:600;">{_num(drawdown, '.1f', suffix='%', lang=lang)}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">ATH: {_num(ath, ',.0f', prefix='$', lang=lang)}</div>
          </div>
          <div style="background:var(--bg2); padding:12px; text-align:center;">
            <div style="font-size:8px; color:var(--dim); text-transform:uppercase; margin-bottom:4px; font-weight:600;">{STR['card_spot_price'][lang]}</div>
            <div style="font-family:var(--mono); font-size:15px; color:var(--text); font-weight:600;">{_num(spot, ',.0f', prefix='$', lang=lang)}</div>
            <div style="font-size:9.5px; color:var(--dim); margin-top:2px;">{STR['label_realtime'][lang]}</div>
          </div>
        </div>
        
        <div class="sparkline-wrap" style="margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:8px;">{STR['chart_heatmap_title'][lang]}</div>
          {heatmap_svg}
          <div style="font-size:9px; color:var(--dim); margin-top:6px; text-align:right;">{STR['heatmap_footnote'][lang]}</div>
        </div>'''
        
        cycle_html = _section_with_note(cycle_html, cycle_note, lang, 'var(--gold2)')

    # 16. Correlation Matrix
    correlation_html = ""
    corr = data.get('correlation_matrix', {})
    corr_note = lang_data.get('notes', {}).get('correlation_note') or data.get('correlation_note', '')
    if corr:
        corr_chart = generate_correlation_matrix_svg(corr)
        correlation_html = f'''
        {render_section_divider(STR['section_correlation'][lang])}
        <div class="sparkline-wrap" style="margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
          <div style="font-size:12.5px; font-weight:600; color:var(--text); margin-bottom:12px;">{STR['chart_correlation_title'][lang]}</div>
          {corr_chart}
        </div>'''
        
        correlation_html = _section_with_note(correlation_html, corr_note, lang, 'var(--accent)')

    # 17. Futures Positioning Desk
    positioning_html = ""
    fr = data.get('funding_rates', {}) or {}
    oi = data.get('open_interest', {}) or {}
    fb = data.get('crypto_futures_basis', {}) or {}
    options_data = data.get('options_data', {}) or {}
    futures_note = lang_data.get('notes', {}).get('futures_note') or data.get('futures_note', '')
    
    # Fear & Greed Speedometer
    fng = data.get('fear_and_greed', {}) or {}
    fng_gauge = generate_fear_greed_gauge_svg(fng.get('value', 50), fng.get('classification', 'Neutral'), lang=lang)
    
    # Coinbase Premium chart
    cp = data.get('coinbase_premium', {}) or {}
    cp_card_html = render_coinbase_premium_card(cp, "180D", lang=lang)
    
    btc_fr_str, btc_fr_cls = _fmt_funding(fr.get('BTC'), lang)
    eth_fr_str, eth_fr_cls = _fmt_funding(fr.get('ETH'), lang)
    
    btc_oi = oi.get('BTC', {})
    eth_oi = oi.get('ETH', {})
    
    def fmt_oi_val(val):
        if _na(val) or not val: return na(lang)
        return f"{val/1000:.1f}K" if val < 1e6 else f"{val/1e6:.2f}M"

    btc_oi_str = fmt_oi_val(btc_oi.get('oi'))
    eth_oi_str = fmt_oi_val(eth_oi.get('oi'))
    
    # Hide OI changes if they are None (Sıfır basmak yok)
    if btc_oi.get('oi_chg_7d') is not None:
        btc_oi_chg_val, btc_oi_cls = _fmt_change(btc_oi['oi_chg_7d'], lang)
        btc_oi_chg = f'&nbsp;<span class="{btc_oi_cls}">{btc_oi_chg_val}</span>'
    else:
        btc_oi_chg = ""
        
    if eth_oi.get('oi_chg_7d') is not None:
        eth_oi_chg_val, eth_oi_cls = _fmt_change(eth_oi['oi_chg_7d'], lang)
        eth_oi_chg = f'&nbsp;<span class="{eth_oi_cls}">{eth_oi_chg_val}</span>'
    else:
        eth_oi_chg = ""
    
    fb_btc = fb.get('btc_basis')
    fb_eth = fb.get('eth_basis')
    fb_btc_txt = f"{fb_btc:.2f}%" if fb_btc is not None else na(lang)
    fb_eth_txt = f"{fb_eth:.2f}%" if fb_eth is not None else na(lang)

    basis_column_html = f'''
    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
      <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">Futures Term Structure</div>
      <table width="100%" style="border-collapse:collapse; font-size:12px;">
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:8px 0; color:var(--dim);">BTC Futures Basis</td><td class="mono" align="right" style="color:var(--text); font-weight:600; padding:8px 0;">{fb_btc_txt}</td></tr>
        <tr><td style="padding:8px 0; color:var(--dim);">ETH Futures Basis</td><td class="mono" align="right" style="color:var(--text); font-weight:600; padding:8px 0;">{fb_eth_txt}</td></tr>
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
            notional_str = fmt_notional(item.get('notional'), lang)
            max_pain_str = f"${item['max_pain']:,.0f}" if item.get('max_pain') is not None else na(lang)
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
    {cp_card_html}
    
    <div class="pair-grid" style="page-break-inside:avoid; break-inside:avoid;">
      <div style="background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:16px;">
        <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:12px;">{STR['card_fng'][lang]}</div>
        {fng_gauge}
      </div>
      {basis_column_html}
    </div>
    
    {positioning_cards_html}
    
    {large_exp_html}
    '''
    
    positioning_html = _section_with_note(positioning_html, futures_note, lang, 'var(--gold)')

    # 17b. Conflicting Signals
    #
    # Detected in signals.py before anything was written, so this section can
    # only appear when two readings genuinely disagree. The reconciliation is
    # either structural (from signals.MECHANISM) or the model's; when there is
    # neither, the section says so instead of reaching for an explanation.
    conflicts_html = ""
    conflicts = data.get('signal_conflicts') or []
    if conflicts:
        model_reconciliations = {
            c.get('pair'): (c.get('reconciliation') or '').strip()
            for c in (lang_data.get('conflicting_signals') or [])
            if isinstance(c, dict)
        }

        cards = []
        for c in conflicts:
            a, b = c['signal_a'], c['signal_b']
            a_cls = 'up' if a['direction'] > 0 else 'down'
            b_cls = 'up' if b['direction'] > 0 else 'down'

            mechanism = (c.get('mechanism') or {}).get(lang)
            reconciliation = mechanism or model_reconciliations.get(c['pair'], '')
            if not reconciliation or reconciliation.upper() == 'UNRESOLVED':
                reconciliation = STR['conflict_unresolved'][lang]

            cards.append(f"""
            <div style="background:var(--bg2); border:1px solid var(--border); border-left:3px solid var(--gold2); border-radius:0 4px 4px 0; padding:14px 16px; margin-bottom:12px; page-break-inside:avoid; break-inside:avoid;">
              <div style="display:flex; flex-wrap:wrap; gap:18px; margin-bottom:10px;">
                <div>
                  <div style="font-size:9px; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:3px;">{a['labels'][lang]}</div>
                  <span class="{a_cls}" style="font-family:var(--mono); font-size:14px; font-weight:700;">{a['value'] or na(lang)}</span>
                </div>
                <div style="align-self:center; color:var(--dim); font-size:13px;">&#8646;</div>
                <div>
                  <div style="font-size:9px; text-transform:uppercase; color:var(--dim); letter-spacing:0.5px; margin-bottom:3px;">{b['labels'][lang]}</div>
                  <span class="{b_cls}" style="font-family:var(--mono); font-size:14px; font-weight:700;">{b['value'] or na(lang)}</span>
                </div>
              </div>
              <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6;">
                <strong style="color:var(--text); font-weight:600;">{STR['conflict_reads'][lang]}:</strong> {reconciliation}
              </div>
            </div>""")

        conflicts_html = f"""
        {render_section_divider(STR['section_conflicts'][lang])}
        {''.join(cards)}
        """

    # 18. Stories — as transmission, not as summary (phase 5).
    #
    # The reader has seen the headline. What they have not seen is the path
    # from the event to their portfolio, so each story prints the chain and
    # where the tape currently sits on it. A story with no chain is dropped:
    # the agent is told to skip anything with no transmission path, and an
    # untransmitted headline is news, not analysis.
    stories_html = ""
    transmissions = [t for t in (lang_data.get('news_transmission') or [])
                     if isinstance(t, dict) and (t.get('chain') or '').strip()]
    news_note = lang_data.get('notes', {}).get('news_note')
    if transmissions:
        items = []
        for i, t in enumerate(transmissions, 1):
            this_week = (t.get('this_week') or '').strip()
            week_html = ''
            if this_week:
                week_html = (f'<div style="margin-top:5px;"><strong style="color:var(--text); '
                             f'font-weight:600;">{STR["news_this_week"][lang]}:</strong> '
                             f'{this_week}</div>')
            items.append(f'''
        <div style="margin-bottom:14px; padding-bottom:14px; border-bottom:1px solid var(--border); page-break-inside:avoid; break-inside:avoid;">
          <div style="font-family:var(--sans); font-size:12.5px; font-weight:700; color:var(--text); margin-bottom:5px;">
            <span style="color:var(--gold);">{i}.</span> {t.get('title', '')}
          </div>
          <div style="font-family:var(--mono); font-size:11px; color:var(--gold2); margin-bottom:4px;">
            {STR['news_chain'][lang]}: {t.get('chain', '')}
          </div>
          <div style="font-family:var(--sans); font-size:11.5px; color:var(--dim); line-height:1.6;">
            {week_html}
          </div>
        </div>''')

        stories_html = f'''
        {render_section_divider(STR['section_themes_risks'][lang])}
        {''.join(items)}
        '''
        stories_html = _section_with_note(stories_html, news_note, lang, 'var(--gold2)')

    # Footer
    footer_html = render_footer(lang=lang, is_weekly=True)

    # ── Page order (phase 5) ────────────────────────────────────────
    #
    # The old order was the order the data happened to be fetched in, so the
    # report opened with whatever loaded first and a reader had to assemble the
    # week themselves. This is the order a reader needs it in: the verdict,
    # then what set it, then what could change it, then the evidence.
    #
    # Sections hide themselves when their data is absent, so the two phase-3
    # slots below (the scenario matrix and last week's scorecard) simply do not
    # render until they exist.
    scenario_html = data.get('_scenario_html', '')
    scorecard_html = data.get('_scorecard_html', '')

    content_html = f'''
    {header_html}
    {_group(STR['section_week_in_one_minute'][lang], regime_html, overview_html, themes_html)}
    {_group(STR['section_macro_regime'][lang], macro_scoreboard_html, liq_html)}
    {_group(STR['section_what_matters_next'][lang], calendar_weekly_html, scenario_html, scorecard_html)}
    {_group(STR['section_cross_asset'][lang], equities_html, sectors_html, ytd_html, correlation_html, turkey_html)}
    {_group(STR['section_crypto_flows'][lang], etf_weekly_html, stablecoin_html, conflicts_html)}
    {_group(STR['section_crypto_market'][lang], watchlist_html, rotation_html)}
    {_group(STR['section_btc_regime'][lang], cycle_html)}
    {_group(STR['section_positioning'][lang], positioning_html)}
    {stories_html}
    {footer_html}
    '''

    return html_wrapper(
        title="Haftalık Stratejik Analiz" if lang == 'tr' else "Weekly Deep Dive Bulletin",
        content=content_html,
        accent_color=gold_color,
        lang=lang,
        is_weekly=True,
        theme=theme
    )
