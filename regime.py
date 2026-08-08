# regime.py
"""Market regime, computed from the tape instead of asked for.

The regime used to be one of the fields the model returned, which put the
bulletin's headline judgment on the far side of a temperature setting: the same
day's data could read RISK_ON or NEUTRAL depending on the sampling, and nothing
tied the verdict to the Macro Scoreboard printed a few centimetres below it.

So it is counted here, before any model is called, and handed to the editor as
a given. The model still writes the sentence — it just no longer decides what
the sentence has to argue.

The method is a vote, not a model. Each input contributes -1, 0 or +1 on the
direction it moved, the votes are summed, and the sum is bucketed. There are no
fitted weights and no thresholds beyond a dead band, because anything more
would be a methodology this file is not entitled to invent.

Each direction below is the textbook one, and they are listed so the mapping
can be argued with rather than discovered:

  DXY down          a softer dollar loosens global financial conditions
  HY OAS narrower   credit is the market that notices stress first
  MOVE down         falling rate volatility is what lets risk be taken
  Copper/Gold up    cyclical demand bid over the defensive one
  VIX down          equity volatility, the conventional risk proxy
  Fear & Greed      positioning, and the only crypto-native input here. It
                    arrives as a level rather than a change, so it votes on the
                    index's own published bands — greed from 55, fear below 46 —
                    rather than a cut this file would have had to invent.

A move too small to mean anything counts as zero. The bands are deliberately
wide: this reads the day, and a dollar drifting 0.05% is not a day.
"""

RISK_ON = 'RISK_ON'
NEUTRAL = 'NEUTRAL'
RISK_OFF = 'RISK_OFF'

# Percentage moves smaller than these are noise, and vote zero. Fear & Greed is
# an index level rather than a percentage, so its band is in points.
DEAD_BANDS = {
    'dxy': 0.15,
    'move': 1.0,
    'copper_gold': 0.5,
    'vix': 2.0,
}

# Alternative.me's own banding: 0-25 extreme fear, 26-46 fear, 47-54 neutral,
# 55-75 greed, 76-100 extreme greed. Using the publisher's cuts keeps this file
# out of the business of deciding what counts as fear.
FEAR_GREED_GREED_AT = 55
FEAR_GREED_FEAR_BELOW = 47
# High-yield spreads are quoted in basis points and move in much smaller steps.
HY_OAS_DEAD_BAND_BP = 2.0

# A single vote either way is one indicator disagreeing with five, which is a
# normal day rather than a regime.
RISK_ON_AT = 2
RISK_OFF_AT = -2


def _vote(change, dead_band, risk_on_when_rising):
    """-1, 0 or +1 for one indicator's move."""
    if change is None:
        return None
    if abs(change) < dead_band:
        return 0
    rising = change > 0
    return 1 if rising == risk_on_when_rising else -1


def _fear_greed_vote(value):
    """Fear & Greed votes on its level, since no change is published with it."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value >= FEAR_GREED_GREED_AT:
        return 1
    if value < FEAR_GREED_FEAR_BELOW:
        return -1
    return 0


def compute_regime(data):
    """Return (regime, detail) for today's tape.

    detail carries every vote and the score, so the decision can be read back
    later from the snapshot instead of guessed at.
    """
    board = data.get('macro_scoreboard') or {}
    macro = data.get('macro_indicators') or {}
    fng = data.get('fear_and_greed') or {}

    inputs = [
        ('DXY', _vote(board.get('DXY_chg'), DEAD_BANDS['dxy'], risk_on_when_rising=False)),
        ('HY_OAS', _vote(board.get('HY_OAS_chg_bp'), HY_OAS_DEAD_BAND_BP, risk_on_when_rising=False)),
        ('MOVE', _vote(board.get('MOVE_chg'), DEAD_BANDS['move'], risk_on_when_rising=False)),
        ('COPPER_GOLD', _vote(board.get('COPPER_GOLD_chg'), DEAD_BANDS['copper_gold'], risk_on_when_rising=True)),
        ('VIX', _vote(macro.get('VIX_chg'), DEAD_BANDS['vix'], risk_on_when_rising=False)),
        ('FEAR_GREED', _fear_greed_vote(fng.get('value'))),
    ]

    votes = {name: v for name, v in inputs if v is not None}

    # Three live inputs is the floor. Below that the score is a coin toss
    # dressed as a verdict, and NEUTRAL hides the strip.
    if len(votes) < 3:
        return NEUTRAL, {'score': None, 'votes': votes,
                         'reason': 'insufficient_inputs', 'available': len(votes)}

    score = sum(votes.values())
    if score >= RISK_ON_AT:
        regime = RISK_ON
    elif score <= RISK_OFF_AT:
        regime = RISK_OFF
    else:
        regime = NEUTRAL

    return regime, {'score': score, 'votes': votes, 'available': len(votes)}
