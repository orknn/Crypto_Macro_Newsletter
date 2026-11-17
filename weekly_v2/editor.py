"""Editor's read — a short model-written paragraph on top of the rule-written page.

The rules still produce every number and every condition. The model only gets
the finished page as text (TR and EN) and writes 3–5 sentences that connect the
sections. Its output is printed only if it passes `check`:

  * every number in it appears on the page in the same language;
  * no flow language, no advice language.

A failed check is retried once with the reasons; a second failure prints
nothing and the page goes out without the paragraph. Cash and total portfolio
value are marked `priv` in the page and never sent.
"""
import json
import os
import re
import html as H

from config import models

# Chosen 2026-11-17 after a side-by-side on the 13 Nov issue (terra / sol, thinking off and free):
# sol with free thinking found the cross-section link that mattered (NVDA −12.7% vs SOX +8.1%)
# for $0.023 a run. Free = no reasoning setting is sent; the model picks its own depth.
MODEL = os.environ.get("WEEKLY_EDITOR_MODEL", "gpt-6.1-sol")
# USD per million tokens (input, output) — same table as stock-analyzer/src/providers.py
PRICES = {"gpt-6.1-terra": (1.00, 5.00), "gpt-6.1-sol": (2.00, 10.00)}
# reasoning tokens share max_output_tokens with the answer, so leave room
MAX_OUT = 20000

BANNED = {
    "tr": [r"para akt", r"para gir", r"para çık", r"akın", r"\balın\b", r"\bsatın\b", r"\balmalı", r"\bsatmalı",
           r"öneri", r"tavsiye", r"fırsat", r"kaçırma", r"\bkesin(likle)?\b"],
    "en": [r"\bflow(s|ed)?\b", r"\binflows?\b", r"\boutflows?\b", r"\bbuy\b", r"\bsell\b", r"\bshould\b", r"\brecommend",
           r"\bopportunit", r"\bmust\b", r"\bdefinitely\b"],
}

SYSTEM = """You are the editor of a personal weekly decision bulletin. Its only reader is its owner, who trades AI-chain equities.
You receive the finished page as text, in Turkish and in English. Every number and condition on it was produced by fixed rules.

Write "the week's read": 3 to 5 sentences that connect what matters across sections — which rule conditions are close,
what changed in the regime, financing stress or the AI chain. Point out a disagreement only if two numbers on the page
genuinely pull in opposite directions; if none does, say nothing about disagreement. Never invent a tension.

Hard rules — a draft that breaks one is discarded:
1. Use only numbers that appear on the page, copied exactly as printed there. Do not compute new numbers (no differences, sums or averages)
   and do not round. Dates may be written as the page writes them.
2. Name a cause only where the page itself names it. The page states a cause only when its correlation test passed; if it does not, neither do you.
3. One week of price is never a flow: no "money flowed / inflows / para aktı". Where the page labels a basket "tepki / rebound", use that word.
4. No advice: never buy, sell, should, recommend, opportunity (TR: al, sat, öneri, tavsiye, fırsat). State conditions instead:
   "if X closes below Y, the stop triggers".
5. Do not repeat the page's headline sentence, and do not mention that you are a model.
6. Turkish: natural Turkish, Turkish number format exactly as the Turkish page prints it (%3,5 · $740,00 · 28.039,34);
   keep YTD, 1W, 1M, 3M, 52W, MA50, MA200 in English. English: numbers exactly as the English page prints them.
Both versions say the same thing."""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["tr", "en"],
          "properties": {"tr": {"type": "string"}, "en": {"type": "string"}}}


# ── page text and numbers ───────────────────────────────────────────────────
def page_text(html):
    """Visible text of a rendered page, without private spans, styles or charts."""
    html = re.sub(r'<span class="[^"]*\bpriv\b[^"]*">.*?</span>', " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>|<svg.*?</svg>|<head>.*?</head>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", H.unescape(html)).strip()


NUM = re.compile(r"\d[\d.,]*\d|\d")


def _val(tok, lang):
    tok = tok.strip(".,")
    if lang == "tr":
        tok = tok.replace(".", "").replace(",", ".")
    else:
        tok = tok.replace(",", "")
    try:
        return round(float(tok), 4)
    except ValueError:
        return None


def numbers(text, lang):
    return {v for v in (_val(t, lang) for t in NUM.findall(text)) if v is not None}


def check(text, page, lang):
    """List of problems; empty means the text may be printed."""
    probs = []
    if not text or len(text) < 40:
        return ["empty or too short"]
    allowed = numbers(page, lang)
    for tok in NUM.findall(text):
        v = _val(tok, lang)
        if v is not None and v not in allowed:
            probs.append(f"number not on the page: {tok}")
    for pat in BANNED[lang]:
        m = re.search(pat, text, re.I)
        if m:
            probs.append(f"banned wording: {m.group(0)}")
    n = len(re.findall(r"[.!?](\s|$)", text))
    if n > 6:
        probs.append(f"too long: {n} sentences")
    return probs


# ── model call ──────────────────────────────────────────────────────────────
def _call(prompt, model=None):
    """One Responses API call with no reasoning setting: the model thinks as much as it decides to."""
    from openai import OpenAI
    model = model or MODEL
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = client.responses.create(model=model, max_output_tokens=MAX_OUT, instructions=SYSTEM, input=prompt,
                                text={"format": {"type": "json_schema", "name": "editor_read", "schema": SCHEMA, "strict": True}})
    if r.status == "incomplete":
        raise RuntimeError("editor answer incomplete")
    u = r.usage
    pin, pout = PRICES.get(model) or models.price(model)
    cost = (u.input_tokens * pin + u.output_tokens * pout) / 1e6
    rt = getattr(getattr(u, "output_tokens_details", None), "reasoning_tokens", 0) or 0
    return json.loads(r.output_text), {"model": r.model, "in": u.input_tokens, "out": u.output_tokens, "reasoning": rt, "usd": round(cost, 4)}


def write(page_tr, page_en, call=None, model=None):
    """Return {"tr", "en", "model", "usage", "rejected"}; tr/en are None when the draft did not pass."""
    call = call or (lambda p: _call(p, model))
    t_tr, t_en = page_text(page_tr), page_text(page_en)
    prompt = f"TURKISH PAGE:\n{t_tr}\n\nENGLISH PAGE:\n{t_en}"
    usage, last = [], {}
    for attempt in range(2):
        out, u = call(prompt)
        usage.append(u)
        last = {"tr": check(out.get("tr", ""), t_tr, "tr"), "en": check(out.get("en", ""), t_en, "en")}
        if not last["tr"] and not last["en"]:
            return {"tr": out["tr"].strip(), "en": out["en"].strip(), "model": u["model"], "usage": usage, "rejected": None}
        prompt += ("\n\nYOUR PREVIOUS DRAFT WAS REJECTED:\n" + json.dumps(out, ensure_ascii=False)
                   + "\nProblems: " + "; ".join(f"{k}: {p}" for k in last for p in last[k])
                   + "\nRewrite both versions fixing every problem.")
    return {"tr": None, "en": None, "model": usage[-1]["model"], "usage": usage, "rejected": last}
