# config/metrics.py
#
# One place that says what every published number is allowed to be.
#
# Until now plausibility lived in two places and covered six metrics: a hand
# written chain of ifs in validators.py, and whatever each fetcher happened to
# seed its result dict with. The second one is the reason the bulletin printed
# "MOVE 0.0" — get_macro_scoreboard pre-fills its dict with 0.0, so a failed
# fetch leaves a sentinel behind that every layer downstream reads as a
# measurement. Nothing distinguished "we measured zero" from "we measured
# nothing", so nothing could.
#
# A MetricSpec answers four questions about one number:
#
#   valid_range           what values are physically possible
#   zero_is_valid         is 0 a reading, or is it the shape of a failure
#   max_staleness_hours   how old may it be before it stops being today's
#   unit                  what kind of quantity it is
#
# A value that fails any of them becomes None. None renders as N/A. There is
# no third state — no 0.0, no em dash, no blank.
#
# On `unit`: the brief's vocabulary is index | percent | bps | usd | ratio |
# count, and PERCENT_CHANGE is added to it. That addition is the whole point of
# having units at all here. Two of the nine defects this layer exists to stop
# are a level being read as a change: the 2s10s spread printed as its own
# weekly move, and a 2Y yield whose *relative* change (+1.67%) was written into
# prose as if it were a level or a basis-point move. Those are not range
# errors — every number involved is plausible. They are unit errors, and they
# are only catchable if a level and a change are different kinds of thing.

from dataclasses import dataclass
from typing import Optional, Tuple

# ── Unit vocabulary ──
# A level in index points (VIX, MOVE, DXY, NFCI).
INDEX = 'index'
# A level expressed in percent (a yield of 4.28%, a spread of 2.71%).
PERCENT = 'percent'
# A *change* expressed in percent of the previous value. Never a level.
PERCENT_CHANGE = 'percent_change'
# A change in basis points. Never a level, never a percent.
BPS = 'bps'
# A money amount, in whatever scale the fetcher returns (documented per spec).
USD = 'usd'
# A dimensionless quotient (Mayer multiple, put/call, ETH/BTC).
RATIO = 'ratio'
# A whole-number tally (open interest contracts, days to FOMC).
COUNT = 'count'

UNITS = {INDEX, PERCENT, PERCENT_CHANGE, BPS, USD, RATIO, COUNT}

# Units that describe a movement rather than a state. A spec in this set may
# never share a source field with a level — see tests T3/T9.
CHANGE_UNITS = {PERCENT_CHANGE, BPS}


@dataclass(frozen=True)
class MetricSpec:
    """What one published number is allowed to be.

    `path` is a dotted route into the payload dict, e.g.
    'macro_scoreboard.MOVE'. Keys may contain spaces (they do — the macro
    indicators are keyed by their display names); they may not contain dots,
    and none of them do.

    `source_field` names where the number comes from, and exists so that a
    level and a change can be shown to be fed by different things. When two
    specs share a source_field and one of them is a change unit, the pair is a
    bug: it means the same fetched value is being presented twice, once as a
    state and once as a movement.
    """

    name: str
    path: str
    source: str
    unit: str
    valid_range: Optional[Tuple[float, float]] = None
    max_staleness_hours: Optional[float] = None
    zero_is_valid: bool = False
    source_field: Optional[str] = None

    def __post_init__(self):
        if self.unit not in UNITS:
            raise ValueError(f"{self.name}: unknown unit {self.unit!r}")
        if self.valid_range and self.valid_range[0] >= self.valid_range[1]:
            raise ValueError(f"{self.name}: empty valid_range {self.valid_range}")

    @property
    def is_change(self):
        return self.unit in CHANGE_UNITS


# ── Staleness budgets ──
#
# Read these as "how long before this number stops describing today". They
# follow the release cadence of the underlying series, not our fetch cadence:
# a weekly series is not stale at 25 hours, and an intraday crypto price is.
INTRADAY = 6.0        # continuously traded, fetched live
DAILY = 48.0          # one print per session, plus a weekend's grace
WEEKLY = 240.0        # weekly release (NFCI, Fed balance sheet) + late-publish room
MONTHLY = 1200.0      # monthly release (CPI, M2) — 50 days covers a delayed print


METRIC_SPECS = (
    # ═══ Macro scoreboard ═══════════════════════════════════════════
    # Every one of these sits in a dict that get_macro_scoreboard pre-fills
    # with 0.0, which is why they all carry zero_is_valid=False. None of these
    # quantities can actually be zero: an index at 0, a dollar index at 0 and a
    # credit spread at 0 are all failures wearing a number.
    MetricSpec('dxy', 'macro_scoreboard.DXY', 'yfinance DX-Y.NYB', INDEX,
               (70, 130), DAILY, source_field='dxy_close'),
    MetricSpec('dxy_chg', 'macro_scoreboard.DXY_chg', 'yfinance DX-Y.NYB',
               PERCENT_CHANGE, (-5, 5), DAILY, zero_is_valid=True,
               source_field='dxy_close_pair'),
    MetricSpec('move', 'macro_scoreboard.MOVE', 'yfinance ^MOVE', INDEX,
               (40, 250), DAILY, source_field='move_close'),
    MetricSpec('move_chg', 'macro_scoreboard.MOVE_chg', 'yfinance ^MOVE',
               PERCENT_CHANGE, (-40, 40), DAILY, zero_is_valid=True,
               source_field='move_close_pair'),
    MetricSpec('hy_oas', 'macro_scoreboard.HY_OAS', 'FRED BAMLH0A0HYM2',
               PERCENT, (1.0, 25.0), DAILY, source_field='hy_oas_level'),
    MetricSpec('hy_oas_chg_bp', 'macro_scoreboard.HY_OAS_chg_bp',
               'FRED BAMLH0A0HYM2', BPS, (-500, 500), DAILY,
               zero_is_valid=True, source_field='hy_oas_pair'),
    MetricSpec('m2', 'macro_scoreboard.M2', 'FRED M2SL', USD,
               (10, 60), MONTHLY, source_field='m2_level'),  # trillions
    MetricSpec('m2_chg', 'macro_scoreboard.M2_chg', 'FRED M2SL',
               PERCENT_CHANGE, (-5, 5), MONTHLY, zero_is_valid=True,
               source_field='m2_pair'),
    # x1000 for readability, so ~1.5 rather than ~0.0015.
    MetricSpec('copper_gold', 'macro_scoreboard.COPPER_GOLD',
               'yfinance HG=F / GC=F', RATIO, (0.3, 10.0), DAILY,
               source_field='copper_gold_level'),
    MetricSpec('copper_gold_chg', 'macro_scoreboard.COPPER_GOLD_chg',
               'yfinance HG=F / GC=F', PERCENT_CHANGE, (-25, 25), DAILY,
               zero_is_valid=True, source_field='copper_gold_pair'),

    # ═══ Macro indicators ═══════════════════════════════════════════
    MetricSpec('us10y', 'macro_indicators.US 10-Year Treasury Yield',
               'yfinance ^TNX', PERCENT, (0.3, 12.0), DAILY,
               source_field='us10y_close'),
    # bps, not percent-of-level: see data_fetcher._yield_change_bp.
    MetricSpec('us10y_chg', 'macro_indicators.US 10-Year Treasury Yield_chg',
               'yfinance ^TNX', BPS, (-200, 200), DAILY,
               zero_is_valid=True, source_field='us10y_close_pair'),
    MetricSpec('us2y', 'macro_indicators.US 2-Year Treasury Yield', 'FRED DGS2',
               PERCENT, (0.05, 12.0), DAILY, source_field='us2y_level'),
    MetricSpec('us2y_chg', 'macro_indicators.US 2-Year Treasury Yield_chg',
               'FRED DGS2', BPS, (-200, 200), DAILY,
               zero_is_valid=True, source_field='us2y_pair'),
    # A spread genuinely crosses zero — that crossing is the whole reason
    # anyone watches it — so this is the rare metric where 0 is a reading.
    # It is safe to allow only because get_macro_indicators now propagates
    # None when either leg is missing, instead of subtracting two zeroes.
    MetricSpec('spread_2s10s', 'macro_indicators.2s10s_spread',
               'derived: yfinance ^TNX - FRED DGS2', PERCENT, (-4.0, 4.0), DAILY,
               zero_is_valid=True, source_field='2s10s_level'),
    MetricSpec('vix', 'macro_indicators.VIX', 'yfinance ^VIX', INDEX,
               (8, 100), DAILY, source_field='vix_close'),
    MetricSpec('vix_chg', 'macro_indicators.VIX_chg', 'yfinance ^VIX',
               PERCENT_CHANGE, (-60, 130), DAILY, zero_is_valid=True,
               source_field='vix_close_pair'),
    MetricSpec('ndx_futures', 'macro_indicators.NASDAQ 100 Futures',
               'yfinance NQ=F', INDEX, (1000, 100000), DAILY),
    MetricSpec('smh', 'macro_indicators.SMH (Semiconductor ETF)',
               'yfinance SMH', USD, (10, 2000), DAILY),

    # ═══ Rates & breakevens ═════════════════════════════════════════
    # Real yields are routinely negative and legitimately cross zero.
    MetricSpec('real_10y', 'rates_breakevens.real_10y', 'FRED DFII10',
               PERCENT, (-3.0, 6.0), DAILY, zero_is_valid=True),
    MetricSpec('real_10y_chg_bp', 'rates_breakevens.real_10y_chg_bp',
               'FRED DFII10', BPS, (-200, 200), DAILY, zero_is_valid=True),
    MetricSpec('breakeven_10y', 'rates_breakevens.breakeven_10y', 'FRED T10YIE',
               PERCENT, (0.0, 6.0), DAILY, zero_is_valid=True),
    MetricSpec('breakeven_10y_chg_bp', 'rates_breakevens.breakeven_10y_chg_bp',
               'FRED T10YIE', BPS, (-200, 200), DAILY, zero_is_valid=True),

    # ═══ Liquidity ══════════════════════════════════════════════════
    # NFCI is an index centred on zero by construction: 0 means "financial
    # conditions at their historical average". Suppressing that would be
    # suppressing the single most meaningful value the series can take.
    MetricSpec('nfci', 'nfci.current', 'FRED NFCI', INDEX, (-2.0, 5.0),
               WEEKLY, zero_is_valid=True),
    MetricSpec('nfci_chg_1w', 'nfci.chg_1w', 'FRED NFCI', INDEX, (-2.0, 2.0),
               WEEKLY, zero_is_valid=True),
    MetricSpec('global_liquidity', 'global_liquidity.value', 'FRED WALCL',
               USD, (1.0, 20.0), WEEKLY),  # trillions, as value_formatted shows
    MetricSpec('global_liquidity_wk_chg', 'global_liquidity.weekly_change',
               'FRED WALCL', PERCENT_CHANGE, (-20, 20), WEEKLY,
               zero_is_valid=True),
    MetricSpec('m2_series', 'm2_money_supply.value', 'FRED M2SL', USD,
               (10, 60), MONTHLY),  # trillions, same scale as macro_scoreboard.M2
    MetricSpec('m2_series_chg', 'm2_money_supply.monthly_change', 'FRED M2SL',
               PERCENT_CHANGE, (-5, 5), MONTHLY, zero_is_valid=True),

    # ═══ Crypto — market ════════════════════════════════════════════
    # alternative.me publishes 1-100 and has no zero. A 0 here has always meant
    # the fetch failed; a 50 used to mean the same thing until the fabricated
    # fallback was removed (see data_fetcher.get_fear_and_greed_index).
    MetricSpec('fear_greed', 'fear_and_greed.value', 'alternative.me', INDEX,
               (1, 100), DAILY),
    MetricSpec('total_mcap', 'crypto_market_overview.total_market_cap',
               'CoinGecko /global', USD, (1e11, 1e14), INTRADAY),
    MetricSpec('total3', 'crypto_market_overview.total3',
               'CoinGecko /global', USD, (1e10, 1e13), INTRADAY),
    MetricSpec('btc_dominance', 'crypto_market_overview.btc_dominance',
               'CoinGecko /global', PERCENT, (5, 90), INTRADAY),
    MetricSpec('eth_dominance', 'crypto_market_overview.eth_dominance',
               'CoinGecko /global', PERCENT, (1, 50), INTRADAY),
    MetricSpec('stablecoin_dominance',
               'crypto_market_overview.stablecoin_dominance',
               'CoinGecko /global', PERCENT, (0.5, 30), INTRADAY),
    MetricSpec('total_volume', 'crypto_market_overview.total_volume',
               'CoinGecko /global', USD, (1e9, 1e13), INTRADAY),
    MetricSpec('mcap_chg_24h', 'crypto_market_overview.market_cap_change_24h',
               'CoinGecko /global', PERCENT_CHANGE, (-40, 40), INTRADAY,
               zero_is_valid=True),

    # ═══ Crypto — derivatives ═══════════════════════════════════════
    MetricSpec('funding_btc', 'funding_rates.BTC', 'Kraken Futures', PERCENT,
               (-0.75, 0.75), INTRADAY),
    MetricSpec('funding_eth', 'funding_rates.ETH', 'Kraken Futures', PERCENT,
               (-0.75, 0.75), INTRADAY),
    MetricSpec('funding_sol', 'funding_rates.SOL', 'Kraken Futures', PERCENT,
               (-0.75, 0.75), INTRADAY),
    # calc_annualized_premium returns exactly 0.0 when the contract has already
    # expired, and the old module-level defaults were 0.0 too, so a zero basis
    # has never once been a measurement.
    MetricSpec('btc_basis', 'crypto_futures_basis.btc_basis',
               'Binance dapi CURRENT_QUARTER', PERCENT, (-50, 100), INTRADAY),
    MetricSpec('eth_basis', 'crypto_futures_basis.eth_basis',
               'Binance dapi CURRENT_QUARTER', PERCENT, (-50, 100), INTRADAY),
    MetricSpec('coinbase_premium', 'coinbase_premium.current_value',
               'Binance klines vs Coinbase candles', PERCENT, (-5, 5),
               INTRADAY),
    MetricSpec('dvol', 'options_data.dvol_index', 'Deribit', INDEX,
               (20, 250), INTRADAY),
    MetricSpec('dvol_chg_24h', 'options_data.dvol_change_24h', 'Deribit',
               INDEX, (-100, 100), INTRADAY, zero_is_valid=True),
    # pcr is computed as put_oi / call_oi and falls back to 0.0 when call OI is
    # zero, which is a division guard rather than a market state.
    MetricSpec('put_call_ratio', 'options_data.put_call_ratio', 'Deribit',
               RATIO, (0.1, 5.0), INTRADAY),
    MetricSpec('max_pain', 'options_data.max_pain_price', 'Deribit', USD,
               (1000, 1_000_000), INTRADAY),
    MetricSpec('risk_reversal_25d', 'options_data.risk_reversal_25d',
               'Deribit', PERCENT, (-30, 30), INTRADAY, zero_is_valid=True),
    MetricSpec('options_oi_btc', 'options_data.open_interest_btc', 'Deribit',
               COUNT, (1, 5_000_000), INTRADAY),

    # ═══ Crypto — cycle ═════════════════════════════════════════════
    MetricSpec('btc_spot_cycle', 'btc_cycle_metrics.spot',
               'yfinance BTC-USD daily close', USD, (1000, 1e7), DAILY,
               source_field='btc_yfinance_close'),
    MetricSpec('btc_wma200', 'btc_cycle_metrics.wma200',
               'yfinance BTC-USD daily close', USD, (1000, 1e7), DAILY),
    MetricSpec('mayer_multiple', 'btc_cycle_metrics.mayer_multiple',
               'derived: yfinance BTC-USD / 200d SMA', RATIO, (0.2, 5.0), DAILY),
    MetricSpec('distance_to_200wma', 'btc_cycle_metrics.distance_to_200wma',
               'derived: yfinance BTC-USD vs 200w MA', PERCENT, (-95, 900), DAILY, zero_is_valid=True),
    MetricSpec('btc_ath', 'btc_cycle_metrics.ath',
               'yfinance BTC-USD daily close', USD, (1000, 1e7), DAILY),
    # Drawdown from ATH is <= 0 and is exactly 0 on the day a new high prints.
    MetricSpec('btc_drawdown', 'btc_cycle_metrics.drawdown',
               'derived: yfinance BTC-USD vs ATH', PERCENT, (-99, 0), DAILY, zero_is_valid=True),

    # ═══ Crypto — rotation & supply ═════════════════════════════════
    MetricSpec('eth_btc_ratio', 'eth_btc.ratio', 'Binance ETHBTC', RATIO,
               (0.005, 0.3), INTRADAY),
    MetricSpec('eth_btc_chg_7d', 'eth_btc.chg_7d', 'Binance ETHBTC',
               PERCENT_CHANGE, (-40, 40), INTRADAY, zero_is_valid=True),
    MetricSpec('stablecoin_mcap', 'stablecoin_data.combined_mcap',
               'CoinGecko', USD, (1e10, 1e13), INTRADAY),
    MetricSpec('stablecoin_chg_24h', 'stablecoin_data.change_24h_pct',
               'CoinGecko', PERCENT_CHANGE, (-20, 20), INTRADAY,
               zero_is_valid=True),

    # ═══ Turkey desk ════════════════════════════════════════════════
    MetricSpec('bist100', 'bist_try.bist100', 'yfinance XU100.IS', INDEX,
               (1000, 1_000_000), DAILY),
    MetricSpec('bist100_chg', 'bist_try.bist100_chg', 'yfinance XU100.IS',
               PERCENT_CHANGE, (-30, 30), DAILY, zero_is_valid=True),
    MetricSpec('usd_try', 'bist_try.usd_try', 'yfinance USDTRY=X', RATIO,
               (1, 1000), DAILY),
    MetricSpec('usd_try_chg', 'bist_try.try_chg', 'yfinance USDTRY=X',
               PERCENT_CHANGE, (-30, 30), DAILY, zero_is_valid=True),

    # ═══ Fed pricing ════════════════════════════════════════════════
    MetricSpec('fomc_dots_median', 'fed_pricing.dots_median', 'FRED FEDTARMD',
               PERCENT, (0, 10), MONTHLY, zero_is_valid=True),
    MetricSpec('fomc_cut_odds', 'fed_pricing.cut_odds', 'Kalshi', PERCENT,
               (0, 100), DAILY, zero_is_valid=True),
)


# Fast lookup by dotted path, and by name.
SPECS_BY_PATH = {s.path: s for s in METRIC_SPECS}
SPECS_BY_NAME = {s.name: s for s in METRIC_SPECS}

assert len(SPECS_BY_PATH) == len(METRIC_SPECS), "duplicate MetricSpec path"
assert len(SPECS_BY_NAME) == len(METRIC_SPECS), "duplicate MetricSpec name"


# ── Where a metric's age comes from ─────────────────────────────────
#
# Each spec already names its origin in `source`, so nothing extra has to be
# declared and nothing can fall out of sync with it. Two token shapes are
# recognised — "FRED <SERIES>" and "yfinance <TICKER>" — and a source may name
# more than one, in which case the metric is only as fresh as its oldest input.
# That is the correct rule for derived numbers: a 2s10s spread built from a
# three-week-old 2Y yield is three weeks old, however recently it was computed.
#
# A source naming neither (CoinGecko, Deribit, Kraken, Binance,
# alternative.me, Kalshi) is a continuously traded feed, genuinely observed at
# fetch time, and takes the run's as_of.

import re as _re

_FRED_TOKEN = _re.compile(r'\bFRED\s+([A-Z0-9]+)')
_YF_TOKEN = _re.compile(r'\byfinance\s+([A-Za-z0-9^=.\-]+)')


def observation_sources(spec):
    """(fred_series, yfinance_tickers) named by this spec's `source` string."""
    return (_FRED_TOKEN.findall(spec.source),
            [t.rstrip('.,') for t in _YF_TOKEN.findall(spec.source)])


def build_observed_at(fred_obs, yf_obs, run_as_of):
    """path -> observation datetime, for every spec in the registry.

    Oldest input wins; a spec with no published input is stamped with the
    run's as_of because that is genuinely when it was seen.
    """
    observed = {}
    for spec in METRIC_SPECS:
        fred_ids, tickers = observation_sources(spec)
        stamps = [fred_obs[i] for i in fred_ids if i in fred_obs]
        stamps += [yf_obs[t] for t in tickers if t in yf_obs]
        if stamps:
            observed[spec.path] = min(stamps)
        elif not fred_ids and not tickers:
            observed[spec.path] = run_as_of
        # A spec that names a published input we failed to fetch is left
        # unstamped on purpose: "we could not tell how old this is" is a real
        # state and build_report.json should say so rather than guess.
    return observed
