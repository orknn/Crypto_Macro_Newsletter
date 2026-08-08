# validators.py
import os
import json
from datetime import datetime

# How far a percentage quoted in an AI note may sit from the nearest real
# figure before the note is treated as unsourced and hidden.
#
# This is deliberately an absolute band, not a relative one. A relative band
# scales with the number, and the numbers that get fabricated are not small:
# on a live run the model wrote 4.77% against a payload whose nearest value
# was 4.7285 — 0.87% away, so a ±2% relative band would have published it.
# The same 0.02 absolute band rejects it while still absorbing the rounding
# drift this is meant to forgive (47.92 against a real -47.93).
AI_NOTE_TOLERANCE = 0.02

def validate_and_sanitize(data):
    """
    Validate metrics in data dictionary against predefined sane ranges.
    If a metric is out of range, set it to None and record it in fetch_report.json.
    """
    rejected = {}
    now_str = datetime.now().isoformat()

    # 1. funding_8h (%)
    funding = data.get('funding_rates')
    if isinstance(funding, dict):
        for asset in list(funding.keys()):
            val = funding[asset]
            if val is not None:
                if not (-0.75 <= val <= 0.75):
                    rejected[f"funding_8h_{asset}"] = {
                        "value": val,
                        "range": "-0.75 ... +0.75",
                        "timestamp": now_str
                    }
                    funding[asset] = None

    # 2. basis_ann (%)
    basis = data.get('crypto_futures_basis')
    if isinstance(basis, dict):
        for key in ['btc_basis', 'eth_basis']:
            val = basis.get(key)
            if val is not None:
                if not (-50.0 <= val <= 100.0):
                    rejected[key] = {
                        "value": val,
                        "range": "-50 ... +100",
                        "timestamp": now_str
                    }
                    basis[key] = None

    # 3. coinbase_premium (%)
    cp = data.get('coinbase_premium')
    if isinstance(cp, dict):
        val = cp.get('current_value')
        if val is not None:
            if not (-5.0 <= val <= 5.0):
                rejected['coinbase_premium'] = {
                    "value": val,
                    "range": "-5 ... +5",
                    "timestamp": now_str
                }
                cp['current_value'] = None

    # 4. dvol (BTC)
    options = data.get('options_data')
    if isinstance(options, dict):
        val = options.get('dvol_index')
        if val is not None:
            if not (20.0 <= val <= 250.0):
                rejected['dvol_index'] = {
                    "value": val,
                    "range": "20 ... 250",
                    "timestamp": now_str
                }
                options['dvol_index'] = None

        # 5. put_call_ratio
        pcr = options.get('put_call_ratio')
        if pcr is not None:
            if not (0.1 <= pcr <= 5.0):
                rejected['put_call_ratio'] = {
                    "value": pcr,
                    "range": "0.1 ... 5",
                    "timestamp": now_str
                }
                options['put_call_ratio'] = None

    # 6. 10y/2y yield (%)
    macro = data.get('macro_indicators')
    if isinstance(macro, dict):
        for key in ['US 10-Year Treasury Yield', 'US 2-Year Treasury Yield']:
            val = macro.get(key)
            if val is not None:
                if not (0.0 <= val <= 12.0):
                    rejected[key] = {
                        "value": val,
                        "range": "0 ... 12",
                        "timestamp": now_str
                    }
                    macro[key] = None

    if rejected:
        print(f"⚠️  Sanity check failed for {len(rejected)} metrics. Rejecting values.")
        report_path = "fetch_report.json"
        report_data = {}
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
            except:
                pass
        
        if "rejected" not in report_data:
            report_data["rejected"] = {}
        
        report_data["rejected"].update(rejected)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing to fetch_report.json: {e}")

    return data


def _collect_snapshot_numbers(data):
    """Every number the bulletin actually fetched, rounded to 4dp.

    The AI layers are skipped: checking the model's prose against the model's
    own prose would let a fabricated figure vouch for itself.
    """
    import re

    AI_KEYS = {'tr', 'en', 'ai_summary', 'news_commentaries', 'research_brief',
               'regime', 'weekly_themes', 'futures_note', 'etf_note',
               'indicators_note'}

    def walk(obj):
        numbers = set()
        if isinstance(obj, bool):
            return numbers
        if isinstance(obj, (int, float)):
            numbers.add(round(float(obj), 4))
        elif isinstance(obj, str):
            for match in re.findall(r'[+-]?\d+\.\d+', obj):
                try:
                    numbers.add(round(float(match), 4))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k in AI_KEYS:
                    continue
                numbers.update(walk(v))
        elif isinstance(obj, list):
            for item in obj:
                numbers.update(walk(item))
        return numbers

    return walk(data)


def _unsourced_figures(text, pool):
    """Percentages in `text` that no fetched number backs up.

    Both orders (+0.61% and %+0.61), both decimal marks, and whole numbers.
    An earlier pattern required a dot, so it matched nothing at all in the
    Turkish edition — where the model writes %4,68 — leaving TR unchecked.
    Turkish also writes the sign outside the percent sign (-%3,27), so the
    sign has to be picked up before the % as well, or -3.27 reads as +3.27.
    """
    import re

    if not isinstance(text, str) or not text.strip() or text.strip() == 'None':
        return []

    matches = (re.findall(r'[+-]?\d+(?:[.,]\d+)?%', text)
               + re.findall(r'[+-]?%[+-]?\d+(?:[.,]\d+)?', text))

    unsourced = []
    for match in matches:
        try:
            value = float(match.replace('%', '').replace(',', '.').strip())
        except ValueError:
            continue
        # Backed by the data if a real number sits within AI_NOTE_TOLERANCE,
        # matched on the signed value or on magnitude alone. Magnitude matters
        # because prose carries direction in words, not in the sign: a -47.93%
        # drawdown is written "%47,92 geri çekilme", and the signed test read
        # that as +47.92, found nothing near it, and suppressed a correct note.
        if any(abs(sn - value) <= AI_NOTE_TOLERANCE
               or abs(abs(sn) - abs(value)) <= AI_NOTE_TOLERANCE for sn in pool):
            continue
        unsourced.append(match)
    return unsourced


def validate_ai_numbers(data):
    """Check every figure the model wrote against the data it was given.

    This used to cover `notes` alone, which meant the bulletin's centrepiece —
    the overview — plus the news insights and the weekly themes went out
    unchecked. On a live run the model produced a 4.77% that appears nowhere in
    the payload; it was caught only because it happened to land in a note.

    The response to an unsourced figure is scaled to what it costs to lose:

      regime_line, notes  hidden, the way a note has always been
      insights[i]         blanked; the list keeps its length, because main.py
                          matches insights to headlines by position
      themes[i]           dropped, a theme built on a bad number is not worth
                          repairing
      overview            blanked and reported, because it cannot be quietly
                          dropped — an empty overview trips the quality gate,
                          which is the correct outcome. Publishing the figure
                          would be worse than publishing nothing.

    Records what it rejected in data['ai_validation'] so the gate can say why
    the overview is missing instead of only that it is.
    """
    pool = _collect_snapshot_numbers(data)
    print(f"      🔍 AI tutarlılık kontrolü: {len(pool)} gerçek sayıya karşı denetleniyor.")

    rejected = []

    def reject(lang, field, figures):
        for figure in figures:
            print(f"      ⚠️  {lang.upper()} {field}: {figure} veride yok — gizlendi.")
            rejected.append({'lang': lang, 'field': field, 'unmatched_value': figure})

    for lang in ('tr', 'en'):
        lang_data = data.get(lang)
        if not isinstance(lang_data, dict):
            continue

        for field in ('regime_line', 'overview'):
            bad = _unsourced_figures(lang_data.get(field), pool)
            if bad:
                reject(lang, field, bad)
                lang_data[field] = None

        notes = lang_data.get('notes')
        if isinstance(notes, dict):
            for key, text in list(notes.items()):
                bad = _unsourced_figures(text, pool)
                if bad:
                    reject(lang, f'notes.{key}', bad)
                    notes[key] = None

        insights = lang_data.get('insights')
        if isinstance(insights, list):
            for i, text in enumerate(insights):
                bad = _unsourced_figures(text, pool)
                if bad:
                    reject(lang, f'insights[{i}]', bad)
                    insights[i] = ""

        themes = lang_data.get('themes')
        if isinstance(themes, list):
            kept = []
            for i, theme in enumerate(themes):
                if not isinstance(theme, dict):
                    kept.append(theme)
                    continue
                bad = (_unsourced_figures(theme.get('title'), pool)
                       + _unsourced_figures(theme.get('description'), pool))
                if bad:
                    reject(lang, f'themes[{i}]', bad)
                else:
                    kept.append(theme)
            lang_data['themes'] = kept

    data['ai_validation'] = {
        'rejected': rejected,
        'overview_rejected': sorted({r['lang'] for r in rejected
                                     if r['field'] == 'overview'}),
    }
    if rejected:
        _log_ai_note_rejection(rejected)
    return data


def validate_research_brief(brief, data):
    """Same check for the Research Desk, which runs after the editor.

    Topics are dropped whole rather than patched: a research question resting
    on a number that was never fetched is not a research question. If nothing
    survives, the caller hides the section — the same rule the desk already
    applies when the model returns no usable topic.
    """
    if not isinstance(brief, dict):
        return brief, []

    pool = _collect_snapshot_numbers(data)
    rejected = []
    kept = []

    for i, topic in enumerate(brief.get('featured_topics') or []):
        bad = []
        for lang in ('tr', 'en'):
            block = topic.get(lang) if isinstance(topic, dict) else None
            if not isinstance(block, dict):
                continue
            bad += _unsourced_figures(block.get('title'), pool)
            bad += _unsourced_figures(block.get('topic'), pool)
        if bad:
            for figure in bad:
                print(f"      ⚠️  Araştırma konusu {i + 1}: {figure} veride yok — konu düşürüldü.")
                rejected.append({'lang': '-', 'field': f'research.topic[{i}]',
                                 'unmatched_value': figure})
        else:
            kept.append(topic)

    if rejected:
        _log_ai_note_rejection(rejected)
    brief['featured_topics'] = kept
    return brief, rejected


def _log_ai_note_rejection(rejected_notes):
    """Record rejected AI figures in fetch_report.json."""
    report_path = "fetch_report.json"
    report_data = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
        except Exception:
            pass
            
    report_data["ai_note_rejected"] = "value_mismatch"
    if "rejected_ai_notes" not in report_data:
        report_data["rejected_ai_notes"] = []
    
    # Append unique notes
    for note in rejected_notes:
        if note not in report_data["rejected_ai_notes"]:
            report_data["rejected_ai_notes"].append(note)
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error logging AI note rejection: {e}")
