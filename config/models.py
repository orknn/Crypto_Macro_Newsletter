# config/models.py
#
# Which model runs which call. One file, one constant per call site.
#
# The rule this exists to enforce: never write a bare `gpt-5.6`. An
# unqualified alias routes to the flagship and bills at flagship rates, so a
# model string that looks like a harmless default is a 25x price difference
# hiding in a literal. `tests.ModelRoutingTests` fails the build if a bare
# alias appears anywhere in the source, which is cheaper than noticing it on an
# invoice.
#
# Tiering, priced per million tokens (input / output):
#
#   SOL    $5.00 / $30.00   flagship
#   TERRA  $2.00 / $12.00   balanced
#   LUNA   $0.20 /  $1.20   fast
#
# The weekly edition runs two passes:
#
#   Pass 1  one TERRA call per section, in parallel, each returning structured
#           facts rather than prose. ~11 calls.
#   Pass 2  one SOL call, fed Pass 1's structured output plus a compact numeric
#           digest — never the raw payload. That restriction is the point of
#           the split: page one cannot contradict the sections below it if it
#           never saw a different set of numbers than they did.
#
# Measured at roughly $0.22 a run against $0.0098 for the single-call design it
# replaces. That was a deliberate trade, made with the numbers in hand.

SOL = 'gpt-5.6-sol'
TERRA = 'gpt-5.6-terra'
LUNA = 'gpt-5.6-luna'


class MODEL:
    """Call site -> model. Every request names one of these, never a literal."""

    # Pass 1. Section notes are schema-shaped synthesis over a small slice of
    # data; balanced is the right tier and the volume makes flagship absurd.
    SECTION_NOTE = TERRA
    # Per-headline commentary, same shape of work.
    NEWS_INSIGHT = TERRA
    # Translation, classification and de-duplication: mechanical, but wrong
    # answers here are visible to the reader, so not the cheapest tier.
    TRANSLATION = TERRA

    # Pass 2. The executive summary is the most quoted text in the report and
    # the only place where one call decides how the whole week reads.
    EXEC_SUMMARY = SOL

    # The daily edition is untouched: 22 runs a month against the weekly's 4.3,
    # so the same routing would cost about five times more in aggregate. Left
    # on the fast tier until that is decided separately.
    DAILY_EDITOR = LUNA
    RESEARCH_DESK = LUNA


# USD per million tokens, (input, output). Used to price a run for
# logs/cost.jsonl; it never affects what gets sent.
PRICING = {
    SOL: (5.00, 30.00),
    TERRA: (2.00, 12.00),
    LUNA: (0.20, 1.20),
    'claude-sonnet-4-6': (3.00, 15.00),
}

# Cached input bills at a tenth. Applies to the shared prefix only — see
# CACHEABLE_PREFIX_FIRST below.
CACHED_INPUT_DISCOUNT = 0.1

# Prompt caching is on, and it only works if the prompt is built in this order:
# stable prefix first (system prompt, schema, instructions), volatile content
# last (this week's numbers). Putting the date or the payload near the top
# breaks the prefix match on every run and the cache never hits.
#
# It discounts input only. In this pipeline input is roughly half the bill, so
# caching moves a weekly run from about $0.249 to $0.219 — real, but not the
# reason the two-pass design is worth having.
CACHEABLE_PREFIX_FIRST = True

# Reasoning effort per tier. Pass 2 is a templated compression task over
# material that has already been analysed, not an exploration, so it stays low;
# on the Responses API reasoning tokens bill at the output rate and share the
# max_output_tokens budget with the visible answer, which is how this pipeline
# has twice shipped JSON that stopped mid-string.
REASONING_EFFORT = {
    SOL: 'low',
    TERRA: 'none',
    LUNA: 'none',
}


def price(model):
    """(input, output) USD per million tokens. Unknown models price at zero."""
    return PRICING.get(model, (0.0, 0.0))


def estimate_cost(model, input_tokens, output_tokens, cached_input_tokens=0):
    """USD for one call, with cached input billed at the reduced rate."""
    rate_in, rate_out = price(model)
    fresh = max(input_tokens - cached_input_tokens, 0)
    return (fresh * rate_in
            + cached_input_tokens * rate_in * CACHED_INPUT_DISCOUNT
            + output_tokens * rate_out) / 1_000_000


def reasoning_effort(model):
    return REASONING_EFFORT.get(model, 'none')
