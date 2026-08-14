# config/prompt_budget.py
#
# Caps on what the newsletter data sends to the language model.
#
# None of this touches `data` itself: rendering, charts, the snapshot and the
# published bulletin keep the full payload. Only the copy handed to the agents
# is trimmed, so no figure the reader sees is affected by anything in here.

# Keys the model is never asked to reason about: raw chart series that exist
# only so a sparkline can be drawn, and slices that duplicate another key
# already in the payload.
PROMPT_EXCLUDED_KEYS = {
    # 7-day close series behind the equity/commodity sparklines. The percentage
    # moves the model actually quotes are already in magnificent_7/commodities.
    'asset_sparklines',
    # Same, for the six-slot ticker bar (NASDAQ 100, DXY, GOLD, 10Y, VIX, BTC);
    # their current values and changes arrive via macro_indicators.
    'ticker_history',
    # Strict top-10 subset of crypto_prices, split out purely for the table.
    'crypto_prices_display',
    # The news reaches the model as `news_inputs` (title + summary). The raw
    # key repeats all of it and adds the Google-RSS URLs, which are long,
    # opaque, and useless to the editor.
    'macro_news',
}

# Long point-series are truncated to their most recent N entries, so the model
# can still describe a recent trend without paying for history it never quotes.
#
# Paths are one of three shapes:
#   'key'          the value itself is the series
#   'key.field'    the series sits under a field
#   'key.*'        every list-valued field is a series (one per asset)
#
# The cap is a number of points, so it only means something next to the
# resolution of the series. Read each one as a span, not as a size.
PROMPT_SERIES_CAPS = {
    # Hourly, 168 points (7 days) -> the last day. The headline reading is
    # `current_value` and the trend/support/resistance call is already
    # summarised in `4h_status`.
    'coinbase_premium.trend_data': 24,
    # Monthly, 61 points back to 2021 -> the last year. The model quotes the
    # level and the month-on-month change, both of which sit next to the series.
    'm2_money_supply.trend': 13,
}

# The Weekly Deep Dive carries a second set of series, and they are the larger
# problem: ~114k characters of chart history against the daily edition's ~47k
# total payload. Same rule, but the resolutions differ, so the spans are set
# per key rather than inherited from the daily table.
PROMPT_SERIES_CAPS_WEEKLY = {
    **PROMPT_SERIES_CAPS,
    # Daily candles here, not hourly -> a month of context for a weekly read.
    'coinbase_premium.trend_data': 30,
    # YTD percentage paths, one daily series per asset (BTC 220, NDX and GOLD
    # 150 each) -> the last month, enough to describe how they have diverged.
    'ytd_comparison_data.*': 20,
    # The rest are weekly or monthly points -> roughly a quarter, except
    # inflation which is monthly and so gets a year.
    'stablecoin_history_data': 13,
    'net_liquidity_history_data': 13,
    'etf_cumulative_data': 13,
    'inflation_history_data': 13,
    # `.current` and `.chg_1w` sit right beside this; the history is the chart.
    'nfci.history': 13,
}

# Upper bound on the news items handed to the editor. Each item costs input
# tokens plus one TR and one EN insight in the response, so this knob moves
# both sides of the bill. data_fetcher applies it during selection.
MAX_NEWS_ITEMS = 5


# ═══════════════════════════════════════════════════════════════════
# What the Weekly page does NOT print
# ═══════════════════════════════════════════════════════════════════
#
# Two of the nine defects in the 8 Aug bulletin were the same defect: the model
# quoted a figure that was real, was in the payload, and was nowhere on the
# page. The note said "max pain 70.000$" (the quarterly strike) while the table
# printed 65.000$ (the nearest expiry); another note cited "put/call 0,575",
# which the weekly edition renders nowhere at all.
#
# Neither could be caught by checking prose against the payload, because the
# payload contained both numbers. The check has to be against what was printed.
#
# So this list is the difference between the two, and it is used twice: to
# decide what the model is shown, and to decide what its figures are checked
# against. One list, so the two can never drift apart.
WEEKLY_UNRENDERED_PATHS = (
    # Deribit: the weekly page prints only the 25Δ risk reversal and the
    # per-expiry max pain table. The quarterly strike, put/call, DVOL and total
    # OI are daily-edition tiles.
    'options_data.max_pain_price',
    'options_data.put_call_ratio',
    'options_data.dvol_index',
    'options_data.dvol_change_24h',
    'options_data.open_interest_btc',
    # A verdict string the model could quote back as a finding of its own.
    'crypto_futures_basis.sentiment',
    # Macro tiles the weekly scoreboard does not carry.
    'macro_scoreboard.M2',
    'macro_scoreboard.M2_chg',
    'macro_indicators.NASDAQ 100 Futures',
    'macro_indicators.NASDAQ 100 Futures_chg',
    'macro_indicators.SMH (Semiconductor ETF)',
    'macro_indicators.SMH (Semiconductor ETF)_chg',
    # Weekly charts liquidity as the Fed net-liquidity and NFCI series; the
    # single-point WALCL and M2 readings belong to the daily edition.
    'global_liquidity',
    'm2_money_supply',
    'stablecoin_data',
    # The rotation card shows the 7-day move only.
    'eth_btc.chg_24h',
)

UNRENDERED_PATHS = {'weekly': WEEKLY_UNRENDERED_PATHS, 'daily': ()}


def prune_unrendered(payload, edition='weekly'):
    """A copy of `payload` without the fields that edition never prints.

    Returns a new dict; nested holders are copied only where something is
    actually removed, so the cost is proportional to the list above rather
    than to the payload.
    """
    pruned = dict(payload)
    for path in UNRENDERED_PATHS.get(edition, ()):
        parts = path.split('.')
        if len(parts) == 1:
            pruned.pop(parts[0], None)
            continue
        holder = pruned.get(parts[0])
        if not isinstance(holder, dict) or parts[1] not in holder:
            continue
        holder = dict(holder)
        holder.pop(parts[1], None)
        pruned[parts[0]] = holder
    return pruned
