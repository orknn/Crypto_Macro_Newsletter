# schemas/agent_responses.py
#
# Response schemas handed to the OpenAI Responses API as strict json_schema.
# With strict mode the model cannot return a shape that fails to parse, which
# retires the "load it, and if that fails go hunting for the first { and the
# last }" step the pipeline used to depend on.
#
# Strict mode has two rules worth remembering when editing these: every object
# needs additionalProperties=false, and every property must be listed in
# required. There are no optional fields — a value that may be absent is typed
# as nullable instead. Keep them in step with the ÇIKTI JSON ŞEMASI block of
# the matching prompt in agents.py; the prompt is what the model reads, this is
# what the API enforces.


def _obj(properties):
    return {
        'type': 'object',
        'properties': properties,
        'required': list(properties),
        'additionalProperties': False,
    }


_STR = {'type': 'string'}
_STR_LIST = {'type': 'array', 'items': _STR}


# An analyst note is two sentences with different jobs, and the schema makes
# them different fields so the second one cannot quietly go missing. `what`
# restates the reading; `so_what` says what it means for positioning or for an
# asset. A note that only restates the number is the data dump this redesign
# exists to leave behind, and when the model had one free-text box it wrote
# that note most of the time.
_NOTE = _obj({'what': _STR, 'so_what': _STR})


def _language_block(note_fields, extra=None, note_schema=_STR):
    props = {
        'regime_line': _STR,
        'overview': _STR,
        **(extra or {}),
        'notes': _obj({name: note_schema for name in note_fields}),
        # One entry per news item handed to the model, in the same order.
        # Skipped items come back as "" — main.py drops the whole list if the
        # count does not match, because a short list slides every commentary
        # onto the wrong headline.
        'insights': _STR_LIST,
    }
    return _obj(props)


DAILY_NOTE_FIELDS = ('futures_note', 'etf_note', 'indicators_note')

WEEKLY_NOTE_FIELDS = (
    'liquidity_note', 'inflation_note', 'stablecoin_note', 'etf_note',
    'rotation_note', 'cycle_note', 'correlation_note', 'futures_note',
    'week_plan_note', 'news_note',
)

_THEMES = {
    'type': 'array',
    'items': _obj({'title': _STR, 'description': _STR}),
}

CONTENT_EDITOR_DAILY_SCHEMA = _obj({
    'tr': _language_block(DAILY_NOTE_FIELDS),
    'en': _language_block(DAILY_NOTE_FIELDS),
})

# Conflicting signals are detected in signals.py, not here: the model is handed
# the pairs that already disagree and asked to reconcile them. `reconciliation`
# is nullable because "these two still disagree and I do not know why" is a
# real answer, and a better one than an invented mechanism.
_CONFLICT = _obj({
    'pair': _STR,
    'reconciliation': {'type': ['string', 'null']},
})

_WEEKLY_EXTRA = {'themes': _THEMES,
                 'conflicting_signals': {'type': 'array', 'items': _CONFLICT}}

CONTENT_EDITOR_WEEKLY_SCHEMA = _obj({
    'tr': _language_block(WEEKLY_NOTE_FIELDS, extra=_WEEKLY_EXTRA,
                          note_schema=_NOTE),
    'en': _language_block(WEEKLY_NOTE_FIELDS, extra=_WEEKLY_EXTRA,
                          note_schema=_NOTE),
})

# `url` is nullable on purpose. The desk may only cite URLs from the allow-list
# it is given, and null is the correct answer when none of them fit — the
# schema has to permit that, or the model is cornered into inventing a link.
# _sanitize in agents.py re-checks every URL against the allow-list regardless.
_SOURCE = _obj({
    'name': _STR,
    'url': {'type': ['string', 'null']},
    'description': _STR,
})

_TOPIC_LANG = _obj({
    'beat': _STR,
    'title': _STR,
    'topic': _STR,
    'primary_sources': {'type': 'array', 'items': _SOURCE},
})

RESEARCH_DESK_SCHEMA = _obj({
    'featured_topics': {
        'type': 'array',
        'items': _obj({'tr': _TOPIC_LANG, 'en': _TOPIC_LANG}),
    },
})


# ═══════════════════════════════════════════════════════════════════
# Two-pass weekly (phase 2.5)
# ═══════════════════════════════════════════════════════════════════

_NUM = {'type': 'number'}

# Pass 1: one call per section, structured rather than prose.
#
# `facts` is the section's numbers in `key=value` form. It exists so pass 2 can
# be handed a compact digest instead of the raw payload — which is what stops
# page one from quoting a different set of numbers than the sections below it.
#
# `key_metric` names the single figure the section turns on. Pass 2's themes
# must each cite one of these, and a theme citing a key_metric that no section
# produced fails the build.
SECTION_ANALYSIS_SCHEMA = _obj({
    'section': _STR,
    'facts': _STR_LIST,
    'direction': {'type': 'string', 'enum': ['bullish', 'bearish', 'neutral']},
    'strength': _NUM,
    'key_metric': _STR,
    'tr': _NOTE,
    'en': _NOTE,
})

_THEME_V2 = _obj({
    'title': _STR,
    'body': _STR,
    # Required, and checked against pass 1's key_metrics.
    'metric_key': _STR,
})

_SCENARIO = _obj({
    'label': _STR,
    'condition': _STR,
    'transmission': _STR,
})

_EXEC_LANG = _obj({
    'regime_rationale': _STR,
    'themes': {'type': 'array', 'items': _THEME_V2},
    'conflicting_signals': {'type': 'array', 'items': _CONFLICT},
    'scenarios': _obj({'bear': _SCENARIO, 'base': _SCENARIO, 'bull': _SCENARIO}),
    'overview': _STR,
    'regime_line': _STR,
})

# Pass 2: a single call over pass 1's output plus a numeric digest. The regime
# itself is not here — regime.py counts it from the tape before any model runs,
# so the model argues the verdict rather than choosing it.
EXEC_SUMMARY_SCHEMA = _obj({'tr': _EXEC_LANG, 'en': _EXEC_LANG})
