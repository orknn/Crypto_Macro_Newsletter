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
