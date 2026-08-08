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
# Keys are dotted paths into the payload.
PROMPT_SERIES_CAPS = {
    # 168 hourly points (7 days). The headline reading is `current_value` and
    # the trend/support/resistance call is already summarised in `4h_status`.
    'coinbase_premium.trend_data': 12,
    # 61 monthly points back to 2021; the model quotes the level and the
    # month-on-month change, both of which sit next to the series.
    'm2_money_supply.trend': 12,
}

# Upper bound on the news items handed to the editor. Each item costs input
# tokens plus one TR and one EN insight in the response, so this knob moves
# both sides of the bill. data_fetcher applies it during selection.
MAX_NEWS_ITEMS = 5
