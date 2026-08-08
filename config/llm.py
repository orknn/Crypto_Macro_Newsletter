# config/llm.py
#
# Everything about which model writes the bulletin lives here: the provider,
# the model id, how hard it is allowed to think, and what a token costs. No
# model name is spelled out anywhere else in the pipeline.

import os

# 'openai' or 'anthropic'. The Anthropic path is kept working so a bad run can
# be rolled back with a secret change instead of a deploy.
PROVIDER = os.environ.get('LLM_PROVIDER', 'openai').strip().lower()

OPENAI_MODEL = 'gpt-5.6-luna'
ANTHROPIC_MODEL = 'claude-sonnet-4-6'

# gpt-5.6-luna is a reasoning model and defaults to 'medium' when the parameter
# is omitted. That matters twice over: reasoning tokens are billed at the
# output rate, and on the Responses API they are drawn from the same
# max_output_tokens budget as the visible answer — so a thinking model can
# spend the budget reasoning and hand back JSON that stops mid-string. This
# pipeline has shipped that exact failure twice (93da3df, cb2c5d8).
#
# All three agents do schema-shaped synthesis, not deep reasoning, so effort is
# off. A live probe confirmed reasoning_tokens=0 at this setting. Raise it to
# 'low' if the prose ever feels thin; leave the budget headroom if you do.
OPENAI_REASONING_EFFORT = os.environ.get('OPENAI_REASONING_EFFORT', 'none')

# Anthropic's sampling knob. The Responses API rejects temperature on reasoning
# models, so this only applies to the fallback path.
ANTHROPIC_TEMPERATURE = 0.7

# USD per million tokens, (input, output). Used only to price the run for
# logs/cost.jsonl — it never affects what gets sent.
PRICING = {
    'gpt-5.6-luna': (0.20, 1.20),
    'claude-sonnet-4-6': (3.00, 15.00),
}

# A single run costing more than this gets a warning in the log. The daily
# edition runs about $0.01 on Luna, so this is a smoke alarm, not a budget.
COST_ALERT_USD = float(os.environ.get('LLM_COST_ALERT_USD', '0.40'))

COST_LOG_PATH = 'logs/cost.jsonl'


def active_model():
    return OPENAI_MODEL if PROVIDER == 'openai' else ANTHROPIC_MODEL


def api_key_env():
    return 'OPENAI_API_KEY' if PROVIDER == 'openai' else 'ANTHROPIC_API_KEY'


def estimate_cost(model, input_tokens, output_tokens):
    """USD for one call. Unknown models price at zero rather than guessing."""
    rate_in, rate_out = PRICING.get(model, (0.0, 0.0))
    return (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000
