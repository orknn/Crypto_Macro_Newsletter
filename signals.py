# signals.py
"""Signals that disagree with each other, found before anything is written.

The 8 Aug weekly printed these three numbers on three different pages and
never once put them in the same sentence:

    BTC ETF weekly flow   +865M      institutional buying
    Coinbase premium      -0.076%    US selling pressure
    Fear & Greed          31         fear

A reader who noticed had no way to resolve it, and the bulletin did not admit
there was anything to resolve. That is the gap this file exists to close, and
it is a data problem rather than a writing one: which pairs of readings can
contradict each other is knowable in advance, and whether they currently do is
arithmetic.

So the contradiction is detected here, deterministically, and only the prose
is left to the model. Two consequences follow, and both are deliberate:

  * The model is never asked whether a conflict exists. It is told that one
    does, with both readings, and asked to reconcile them. It cannot invent a
    conflict, and it cannot quietly decline to mention one.

  * Where the reconciliation is mechanical rather than interpretive, it is
    written down here (see MECHANISM) instead of being regenerated weekly. An
    ETF creation clearing through an OTC desk does not touch the Coinbase spot
    book — that is how the plumbing works, it will be equally true next week,
    and asking a model to rediscover it every Sunday is a way of eventually
    getting it wrong.

UNRESOLVED is a legitimate outcome. Two signals genuinely disagreeing and
nobody knowing why is information; a fabricated explanation is not.
"""

# Direction convention, shared by every reading below:
#   +1  risk-on / bullish
#   -1  risk-off / bearish
#    0  inside the dead band — a move too small to mean anything
#   None unavailable
RISK_ON = 1
RISK_OFF = -1
NEUTRAL = 0


def _sign(value, dead_band):
    if value is None:
        return None
    if abs(value) < dead_band:
        return NEUTRAL
    return RISK_ON if value > 0 else RISK_OFF


# ── Readings ────────────────────────────────────────────────────────
#
# Each returns (direction, display_value). The dead bands are wide on purpose:
# this looks for disagreement worth a paragraph, and two signals drifting a
# few basis points apart is not one.

def _etf_flow(data):
    history = data.get('etf_weekly_history_data') or []
    if not history:
        return None, None
    flow = history[-1].get('Total_flow_m')
    # $50M on a multi-billion complex is noise.
    return _sign(flow, 50.0), (f"{flow:+.0f}M" if flow is not None else None)


def _coinbase_premium(data):
    cp = (data.get('coinbase_premium') or {}).get('current_value')
    return _sign(cp, 0.02), (f"{cp:+.3f}%" if cp is not None else None)


def _funding(data):
    rate = (data.get('funding_rates') or {}).get('BTC')
    return _sign(rate, 0.002), (f"{rate:+.4f}%" if rate is not None else None)


def _risk_reversal(data):
    rr = (data.get('options_data') or {}).get('risk_reversal_25d')
    return _sign(rr, 0.5), (f"{rr:+.2f}%" if rr is not None else None)


def _sector_breadth(data):
    sectors = data.get('sp500_sectors') or []
    moves = [s.get('Change %') for s in sectors
             if isinstance(s.get('Change %'), (int, float))]
    if len(moves) < 5:
        return None, None
    share = sum(1 for m in moves if m > 0) / len(moves)
    # Breadth is a proportion, so it is centred on a half rather than on zero.
    return _sign(share - 0.5, 0.1), f"{share * 100:.0f}%"


def _btc_7d(data):
    for row in data.get('crypto_prices') or []:
        if row.get('Symbol') == 'BTC':
            move = row.get('7d %')
            return _sign(move, 1.0), (f"{move:+.2f}%" if move is not None else None)
    return None, None


def _vix(data):
    # Falling volatility is the risk-on direction, hence the inversion.
    chg = (data.get('macro_indicators') or {}).get('VIX_chg')
    direction = _sign(chg, 2.0)
    return (None if direction is None else -direction), \
           (f"{chg:+.2f}%" if chg is not None else None)


def _credit_spreads(data):
    # Widening spreads are risk-off, so this inverts too.
    chg = (data.get('macro_scoreboard') or {}).get('HY_OAS_chg_bp')
    direction = _sign(chg, 5.0)
    return (None if direction is None else -direction), \
           (f"{chg:+.1f} bps" if chg is not None else None)


SIGNALS = {
    'etf_flow': (_etf_flow, {'tr': 'BTC ETF haftalık akışı',
                             'en': 'BTC ETF weekly flow'}),
    'coinbase_premium': (_coinbase_premium, {'tr': 'Coinbase primi',
                                             'en': 'Coinbase premium'}),
    'funding': (_funding, {'tr': 'BTC funding oranı', 'en': 'BTC funding rate'}),
    'risk_reversal': (_risk_reversal, {'tr': '25Δ risk reversal',
                                       'en': '25Δ risk reversal'}),
    'sector_breadth': (_sector_breadth, {'tr': 'S&P 500 sektör genişliği',
                                         'en': 'S&P 500 sector breadth'}),
    'btc_7d': (_btc_7d, {'tr': 'BTC 7 günlük performans',
                         'en': 'BTC 7-day performance'}),
    'vix': (_vix, {'tr': 'VIX', 'en': 'VIX'}),
    'credit_spreads': (_credit_spreads, {'tr': 'Yüksek getirili kredi makası',
                                         'en': 'HY credit spread'}),
}


# ── Reconciliations that are mechanical ─────────────────────────────
#
# Only fill this in where the explanation is a fact about market structure
# rather than a judgment about this particular week. Anything that depends on
# what is happening right now belongs to the model, not to this table.
MECHANISM = {
    ('etf_flow', 'coinbase_premium'): {
        'tr': "Bu ikisi çelişmiyor; farklı alıcı tiplerini ölçüyorlar. ABD spot "
              "ETF yaratımları OTC masaları üzerinden yürür ve Coinbase spot "
              "emir defterine yansımaz. Kurumsal talep ETF akışında görünürken "
              "perakende/ABD spot tarafı aynı anda satıcı olabilir.",
        'en': "These are not in conflict; they measure different buyers. US spot "
              "ETF creations clear through OTC desks and never touch the "
              "Coinbase spot order book, so institutional demand can show up in "
              "flows while US spot itself is being sold.",
    },
    ('funding', 'risk_reversal'): {
        'tr': "Perpetual funding kaldıraçlı yönlü konumlanmayı, risk reversal ise "
              "opsiyon tarafındaki korunma iştahını ölçer. Pozitif funding ile "
              "negatif risk reversal, long'ların aynı anda aşağı korunma satın "
              "aldığı bir piyasadır — ikisi farklı vadeleri fiyatlıyor.",
        'en': "Perpetual funding measures levered directional positioning; the "
              "risk reversal measures demand for optional protection. Positive "
              "funding against a negative risk reversal is a market that is long "
              "and hedged at once — the two price different horizons.",
    },
}


def read_all(data):
    """Every signal's direction and printable value."""
    readings = {}
    for name, (reader, labels) in SIGNALS.items():
        try:
            direction, display = reader(data)
        except Exception:
            direction, display = None, None
        readings[name] = {'direction': direction, 'value': display,
                          'labels': labels}
    return readings


# Pairs that can meaningfully contradict each other. Ordering inside a pair is
# fixed so MECHANISM lookups and rendered output stay stable week to week.
PAIRS = (
    ('etf_flow', 'coinbase_premium'),
    ('funding', 'risk_reversal'),
    ('sector_breadth', 'btc_7d'),
    ('vix', 'credit_spreads'),
)


def detect_conflicts(data):
    """Pairs currently pointing opposite ways, with both readings attached.

    A pair is only a conflict when both legs are present and both are outside
    their dead band. A missing leg is not a disagreement, and neither is a flat
    one — saying otherwise would manufacture a section every week, which is the
    fastest way to make readers stop reading it.
    """
    readings = read_all(data)
    conflicts = []

    for a, b in PAIRS:
        ra, rb = readings.get(a, {}), readings.get(b, {})
        da, db = ra.get('direction'), rb.get('direction')
        if da is None or db is None:
            continue
        if da == NEUTRAL or db == NEUTRAL:
            continue
        if da == db:
            continue

        conflicts.append({
            'pair': f'{a}|{b}',
            'signal_a': {'name': a, 'labels': ra['labels'],
                         'value': ra['value'], 'direction': da},
            'signal_b': {'name': b, 'labels': rb['labels'],
                         'value': rb['value'], 'direction': db},
            # Present when the reconciliation is structural; the model is asked
            # only for the ones where it is absent.
            'mechanism': MECHANISM.get((a, b)),
        })

    return conflicts
