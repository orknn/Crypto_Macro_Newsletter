# config/editions.py

EDITIONS = {
    'daily': {
        'title': 'DAILY FINANCIAL BULLETIN',
        'sub_title': 'Global Macro & Crypto Market Intelligence',
        'accent_color': '#3b82f6', # blue
        'sections': [
            'header',
            'regime_strip',
            'ticker',
            'market_overview',
            'calendar',
            'equities_commodities',
            'crypto_divider',
            'key_metrics',
            'derivatives_desk',
            'etf_flows',
            'crypto_watchlist',
            'top_stories',
            'footer'
        ]
    },
    'weekly': {
        'title': 'WEEKLY DEEP DIVE',
        'sub_title': 'Strategic Liquidity, Macro Themes & Crypto Rotation',
        'accent_color': '#f59e0b', # gold
        'sections': [
            'header',
            'weekly_themes',
            'next_week_calendar_unlocks',
            'liquidity_regime',
            'macro_scoreboard',
            'equities_commodities_weekly',
            'sp500_sectors',
            'btc_ndx_gold_ytd',
            'turkey_desk',
            'crypto_divider',
            'stablecoin_supply',
            'etf_weekly_net_flow',
            'winners_losers',
            'crypto_watchlist_weekly',
            'crypto_sector_rotation',
            'cycle_panel',
            'correlation_matrix',
            'futures_positioning_desk',
            'top_stories',
            'footer'
        ]
    }
}
