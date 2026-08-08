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
_REGIME = {'type': 'string', 'enum': ['RISK_ON', 'NEUTRAL', 'RISK_OFF']}


def _language_block(note_fields, extra=None):
    props = {
        'regime_line': _STR,
        'overview': _STR,
        **(extra or {}),
        'notes': _obj({name: _STR for name in note_fields}),
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
    'regime': _REGIME,
    'tr': _language_block(DAILY_NOTE_FIELDS),
    'en': _language_block(DAILY_NOTE_FIELDS),
})

CONTENT_EDITOR_WEEKLY_SCHEMA = _obj({
    'regime': _REGIME,
    'tr': _language_block(WEEKLY_NOTE_FIELDS, extra={'themes': _THEMES}),
    'en': _language_block(WEEKLY_NOTE_FIELDS, extra={'themes': _THEMES}),
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
