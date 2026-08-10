# validators.py
import os
import json
from datetime import datetime

from config.metrics import METRIC_SPECS
from config.prompt_budget import prune_unrendered

# Where the run writes its account of what it suppressed and why.
BUILD_REPORT_PATH = 'build_report.json'

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

def _resolve(payload, path):
    """(holder, key, value) for a dotted path, or (None, None, _MISSING)."""
    parts = path.split('.')
    holder = payload
    for part in parts[:-1]:
        if not isinstance(holder, dict):
            return None, None, _MISSING
        holder = holder.get(part)
    if not isinstance(holder, dict):
        return None, None, _MISSING
    key = parts[-1]
    if key not in holder:
        return holder, key, _MISSING
    return holder, key, holder[key]


class _Missing:
    def __repr__(self):
        return '<missing>'


_MISSING = _Missing()


def _staleness_hours(observed_at, now):
    """Age of a reading in hours, or None when it carries no timestamp."""
    if not observed_at:
        return None
    if isinstance(observed_at, (int, float)):
        stamp = datetime.fromtimestamp(observed_at)
    else:
        try:
            stamp = datetime.fromisoformat(str(observed_at))
        except ValueError:
            return None
    if stamp.tzinfo is not None:
        stamp = stamp.replace(tzinfo=None)
    return (now - stamp).total_seconds() / 3600.0


def apply_metric_specs(data, now=None):
    """Hold every specced number to its MetricSpec; suppress the ones that fail.

    A value that fails becomes None, which the render layer prints as N/A. This
    replaces two things at once: the hand-rolled range chain that covered six
    metrics, and the habit of seeding a fetcher's result dict with 0.0 so that
    a dead feed still returned something shaped like a measurement.

    Returns (data, findings). `data` is mutated in place, which is what every
    caller already expects of this module.

    Staleness is checked against data['_observed_at'], a path -> timestamp map
    that the snapshot discipline in phase 1.3 fills in. Until it exists, specs
    that ask for a freshness guarantee they cannot yet get are reported as
    'staleness_unknown' rather than quietly passing: an unenforced rule should
    look unenforced.
    """
    now = now or datetime.now()
    observed = data.get('_observed_at') or {}
    findings = []

    for spec in METRIC_SPECS:
        holder, key, value = _resolve(data, spec.path)

        if value is _MISSING or value is None:
            # Nothing to suppress. A section with no data hides itself; that
            # is a different event from a number that was fetched and refused.
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            findings.append(_finding(spec, value, 'not_numeric'))
            holder[key] = None
            continue

        if value != value:  # NaN
            findings.append(_finding(spec, None, 'nan'))
            holder[key] = None
            continue

        if value == 0 and not spec.zero_is_valid:
            findings.append(_finding(spec, value, 'zero_not_valid'))
            holder[key] = None
            continue

        if spec.valid_range:
            low, high = spec.valid_range
            if not (low <= value <= high):
                findings.append(_finding(
                    spec, value, 'out_of_range',
                    detail=f"{low} ... {high}"))
                holder[key] = None
                continue

        if spec.max_staleness_hours is not None:
            age = _staleness_hours(observed.get(spec.path), now)
            if age is None:
                findings.append(_finding(spec, value, 'staleness_unknown',
                                         suppressed=False))
            elif age > spec.max_staleness_hours:
                findings.append(_finding(
                    spec, value, 'stale',
                    detail=f"{age:.1f}h > {spec.max_staleness_hours:.0f}h"))
                holder[key] = None
                continue

    suppressed = [f for f in findings if f['suppressed']]
    if suppressed:
        print(f"  ⚠️  {len(suppressed)} metrik denetimden geçemedi — N/A basılacak:")
        for f in suppressed:
            print(f"       {f['name']} = {f['value']} ({f['reason']}"
                  f"{', ' + f['detail'] if f['detail'] else ''})")
    else:
        print("  ✅ Tüm metrikler MetricSpec denetiminden geçti.")

    return data, findings


def _finding(spec, value, reason, detail=None, suppressed=True):
    return {
        'name': spec.name,
        'path': spec.path,
        'source': spec.source,
        'unit': spec.unit,
        'value': value,
        'reason': reason,
        'detail': detail,
        'suppressed': suppressed,
        'timestamp': datetime.now().isoformat(),
    }


def write_build_report(data, findings, edition='weekly', path=BUILD_REPORT_PATH):
    """Account for what this build suppressed, so a thin bulletin can be read.

    The bulletin itself only ever says N/A. This file says which N/A, from
    which feed, and on which rule — the difference between a quiet run and a
    run where half the macro board went dark.
    """
    suppressed = [f for f in findings if f['suppressed']]
    unenforced = [f for f in findings if not f['suppressed']]

    report = {
        'generated_at': datetime.now().isoformat(),
        'edition': edition,
        'as_of': data.get('as_of'),
        'metrics_specced': len(METRIC_SPECS),
        'metrics_na': len(suppressed),
        'na': suppressed,
        'unenforced_checks': unenforced,
        'ai_validation': data.get('ai_validation'),
    }
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  📄 build_report.json yazıldı ({len(suppressed)} N/A).")
    except Exception as e:
        print(f"  ⚠️  build_report.json yazılamadı: {e}")
    return report



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


# ═══════════════════════════════════════════════════════════════════
# Blocklist: text that is about the pipeline, not about the market
# ═══════════════════════════════════════════════════════════════════
#
# The 8 Aug weekly printed this, as an analyst note, to subscribers:
#
#   "Temiz ve net bir piyasa haberi olmayan bu genel izleme listesi için
#    ayrıca insight üretilmemiştir."
#
# It is worth being precise about where that came from, because the obvious
# reading is wrong. It is not in the codebase — nothing in this repo has ever
# emitted that sentence. The model wrote it: asked to leave an item blank when
# it had nothing to say, it explained itself instead, in prose, in the field
# where the analysis goes. No amount of care in the render layer would have
# stopped it, because to the renderer it was simply a non-empty string.
#
# So the gate is here, on the way in. A generated field that talks about the
# generation is not a weak field to be published with a caveat — it is not
# content at all, and the section it belongs to is dropped exactly as if the
# model had returned nothing.
#
# Patterns are matched case-insensitively against the model's own output only.
# They are never applied to rendered HTML: the N/A tooltip says "Veri
# alınamadı" by design, and that is the render layer doing its job.
_BLOCKLIST_PATTERNS = (
    # Turkish: the model narrating its own abstention. Suffixes vary
    # (-miştir / -di / -yor), so the stem is matched.
    r'üretil(?:me|mem)',
    r'oluşturul(?:ama|ma)',
    r'veri\s+(?:alınamadı|bulunamadı|yok|mevcut\s+değil)',
    r'bilgi\s+(?:bulunamadı|mevcut\s+değil)',
    r'yeterli\s+veri',
    # English equivalents, for the EN edition.
    r'\bno\s+(?:data|insight|information)\b',
    r'\bnot\s+(?:available|generated|provided)\b',
    r'\binsufficient\s+data\b',
    r'\bunable\s+to\s+(?:generate|determine)\b',
    # Leaked sentinels. The leading boundary is the load-bearing one:
    # "muhatap" contains the letters of "hata", and a note about a
    # counterparty is not an error message. The trailing side stays open for a
    # few characters because Turkish inflects — the leak reads "hatası", not
    # "hata".
    r'(?<![a-zçğıöşü])hata[a-zçğıöşü]{0,6}(?![a-zçğıöşü])',
    r'(?<![a-z])errors?(?![a-z])',
    r'\bNone\b',
    r'\bnull\b',
    r'\bundefined\b',
    r'\bNaN\b',
    r'\bTODO\b',
    r'\bFIXME\b',
    r'\[object\s+Object\]',
)


def blocklisted_phrases(text):
    """Blocklisted fragments in `text`. Empty list means the text is publishable."""
    import re

    if not isinstance(text, str) or not text.strip():
        return []
    found = []
    for pattern in _BLOCKLIST_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return found


def _walk_generated_fields(data, inspect, on_reject):
    """Apply `inspect` to every model-authored field, with the per-field policy.

    The policy is the same one validate_ai_numbers established, and it is
    shared rather than repeated so the two checks can never disagree about
    what happens to a bad theme or a bad insight:

      regime_line, overview   blanked — an empty overview trips the quality
                              gate, which is the correct outcome
      notes.*                 hidden
      insights[i]             blanked, list length preserved (main.py matches
                              insights to headlines by position)
      themes[i]               dropped whole
    """
    for lang in ('tr', 'en'):
        lang_data = data.get(lang)
        if not isinstance(lang_data, dict):
            continue

        for field in ('regime_line', 'overview'):
            bad = inspect(lang_data.get(field))
            if bad:
                on_reject(lang, field, bad)
                lang_data[field] = None

        notes = lang_data.get('notes')
        if isinstance(notes, dict):
            for key, note in list(notes.items()):
                # A note is now {what, so_what}; both halves are checked, and a
                # fault in either drops the note. Legacy plain strings are still
                # accepted so stored snapshots and the daily edition work.
                if isinstance(note, dict):
                    bad = inspect(note.get('what')) + inspect(note.get('so_what'))
                else:
                    bad = inspect(note)
                if bad:
                    on_reject(lang, f'notes.{key}', bad)
                    notes[key] = None

        insights = lang_data.get('insights')
        if isinstance(insights, list):
            for i, text in enumerate(insights):
                bad = inspect(text)
                if bad:
                    on_reject(lang, f'insights[{i}]', bad)
                    insights[i] = ""

        conflicts = lang_data.get('conflicting_signals')
        if isinstance(conflicts, list):
            for i, entry in enumerate(conflicts):
                if not isinstance(entry, dict):
                    continue
                bad = inspect(entry.get('reconciliation'))
                if bad:
                    on_reject(lang, f'conflicting_signals[{i}]', bad)
                    # Nulled, not dropped: the conflict itself was detected from
                    # the tape and still stands. Only the explanation goes, and
                    # the renderer then prints "the conflict stands".
                    entry['reconciliation'] = None

        themes = lang_data.get('themes')
        if isinstance(themes, list):
            kept = []
            for i, theme in enumerate(themes):
                if not isinstance(theme, dict):
                    kept.append(theme)
                    continue
                bad = inspect(theme.get('title')) + inspect(theme.get('description'))
                if bad:
                    on_reject(lang, f'themes[{i}]', bad)
                else:
                    kept.append(theme)
            lang_data['themes'] = kept


def scrub_generated_text(data):
    """Drop any generated field that talks about the pipeline instead of the market.

    Runs before the numeric check, so a note that is both self-narrating and
    unsourced is reported as the former — which is the more useful diagnosis.
    """
    rejected = []

    def on_reject(lang, field, phrases):
        for phrase in phrases:
            print(f"      🚫 {lang.upper()} {field}: '{phrase}' — "
                  "iç mesaj, bölüm düşürüldü.")
            rejected.append({'lang': lang, 'field': field, 'phrase': phrase})

    _walk_generated_fields(data, blocklisted_phrases, on_reject)

    existing = data.get('ai_validation') or {}
    existing['blocklisted'] = rejected
    data['ai_validation'] = existing
    if rejected:
        print(f"      🚫 {len(rejected)} üretilmiş alan blocklist'e takıldı.")
    return data


def unify_spot_prices(data):
    """One BTC price for the whole bulletin.

    The watchlist quoted CoinGecko live ($65,210) and the cycle panel quoted a
    yfinance daily close ($65,207), two centimetres apart on the same page.
    Two feeds cannot agree to the dollar and there is no reason for a reader to
    have to decide which one the bulletin meant.

    CoinGecko wins because it is what the watchlist, the market-cap figures and
    every other crypto number already come from. The cycle panel's derived
    figures are then recomputed off that price rather than left describing the
    close they were built from — a Mayer multiple against one spot and a
    drawdown against another is the same defect one level down.
    """
    canonical = None
    for row in data.get('crypto_prices') or []:
        if row.get('Symbol') == 'BTC':
            canonical = row.get('Current Price USD')
            break
    if canonical is None:
        return data

    cycle = data.get('btc_cycle_metrics')
    if not isinstance(cycle, dict):
        return data

    previous = cycle.get('spot')
    cycle['spot'] = canonical
    data['btc_spot'] = canonical

    wma200 = cycle.get('wma200')
    if wma200:
        cycle['distance_to_200wma'] = round(
            ((canonical - wma200) / wma200) * 100, 2)
    ath = cycle.get('ath')
    if ath:
        cycle['drawdown'] = round(((canonical - ath) / ath) * 100, 2)
    sma200 = cycle.get('sma200d')
    if sma200:
        cycle['mayer_multiple'] = round(canonical / sma200, 3)

    if previous is not None and abs(previous - canonical) > 0.005:
        print(f"      🔗 BTC spot tekilleştirildi: {previous:,.2f} → "
              f"{canonical:,.2f} (döngü paneli watchlist'e hizalandı).")
    return data


# Series the bulletin prints in more than one place. Each entry says how to
# read the same quantity out of each surface, so a split vintage shows up as a
# disagreement instead of as two confident numbers on two pages.
def _cpi_from_chart(data):
    history = data.get('inflation_history_data') or []
    return history[-1].get('cpi') if history else None


def _cpi_from_calendar(data):
    for ev in data.get('economic_calendar') or []:
        name = (ev.get('event') or '').lower()
        if 'cpi' in name and ('yoy' in name or 'y/y' in name):
            for field in ('actual', 'previous'):
                raw = ev.get(field)
                if raw in (None, '', 'None'):
                    continue
                try:
                    return float(str(raw).replace('%', '').replace(',', '.').strip())
                except ValueError:
                    continue
    return None


SHARED_SERIES = (
    {'series': 'cpi_yoy',
     'surfaces': (('inflation chart', _cpi_from_chart),
                  ('economic calendar', _cpi_from_calendar)),
     'tolerance': 0.05,
     'note': 'CPI YoY is published from the NSA index; see CPI_SERIES.'},
)


def reconcile_shared_series(data, tolerance=None):
    """Report any series the bulletin shows twice with two different values.

    This does not repair anything — a disagreement here means two feeds are
    quoting different vintages of one series, and which one is right is a
    sourcing decision, not something a formatter can settle.
    """
    conflicts = []
    for entry in SHARED_SERIES:
        band = tolerance if tolerance is not None else entry['tolerance']
        readings = {}
        for label, extract in entry['surfaces']:
            value = extract(data)
            if value is not None:
                readings[label] = value
        if len(readings) < 2:
            continue
        values = list(readings.values())
        if max(values) - min(values) > band:
            conflicts.append({
                'series': entry['series'],
                'readings': readings,
                'spread': round(max(values) - min(values), 4),
                'tolerance': band,
                'note': entry['note'],
            })
            pairs = ', '.join(f"{k}={v}" for k, v in readings.items())
            print(f"      ⚠️  {entry['series']} iki yerde farklı: {pairs}")
    return conflicts


def validate_ai_numbers(data, edition='weekly'):
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
    # Checked against what the page prints, not against everything fetched.
    # A figure that is real but unrendered is exactly the T5/T6 failure: the
    # reader cannot find it, so the bulletin must not assert it.
    pool = _collect_snapshot_numbers(prune_unrendered(data, edition=edition))
    print(f"      🔍 AI tutarlılık kontrolü: {len(pool)} render edilen sayıya karşı denetleniyor.")

    rejected = []

    def reject(lang, field, figures):
        for figure in figures:
            print(f"      ⚠️  {lang.upper()} {field}: {figure} veride yok — gizlendi.")
            rejected.append({'lang': lang, 'field': field, 'unmatched_value': figure})

    # Same field policy as the blocklist pass, shared so the two can never
    # disagree about what happens to a bad theme or a bad insight.
    _walk_generated_fields(data, lambda text: _unsourced_figures(text, pool), reject)

    existing = data.get('ai_validation') or {}
    existing.update({
        'rejected': rejected,
        'overview_rejected': sorted(
            {r['lang'] for r in rejected if r['field'] == 'overview'}
            | {r['lang'] for r in existing.get('blocklisted', [])
               if r['field'] == 'overview'}),
    })
    data['ai_validation'] = existing
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
            # Both checks, in the same order as the editor's: a topic that
            # narrates the pipeline is dropped before its figures are read.
            bad += blocklisted_phrases(block.get('title'))
            bad += blocklisted_phrases(block.get('topic'))
            bad += _unsourced_figures(block.get('title'), pool)
            bad += _unsourced_figures(block.get('topic'), pool)
        if bad:
            for figure in bad:
                print(f"      ⚠️  Araştırma konusu {i + 1}: '{figure}' — konu düşürüldü.")
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


# ═══════════════════════════════════════════════════════════════════
# Two-pass verification (phase 2.5)
# ═══════════════════════════════════════════════════════════════════

def _digest_numbers(digest):
    """Every number pass 2 was allowed to see, rounded to 4dp."""
    import re

    found = set()

    def walk(obj):
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            found.add(round(float(obj), 4))
        elif isinstance(obj, str):
            for match in re.findall(r'[+-]?\d+(?:[.,]\d+)?', obj):
                try:
                    found.add(round(float(match.replace(',', '.')), 4))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(digest)
    return found


def _figures_in(text):
    """Every number written in a piece of prose, TR and EN decimal marks."""
    import re

    if not isinstance(text, str) or not text.strip():
        return []
    out = []
    for match in re.findall(r'[+-]?\d+(?:[.,]\d+)?', text):
        try:
            out.append((match, float(match.replace(',', '.'))))
        except ValueError:
            continue
    return out


def verify_exec_summary_numbers(data, digest, tolerance=AI_NOTE_TOLERANCE):
    """Every figure in the executive summary must exist in the digest.

    The executive summary is the most quoted text in the report, so a wrong
    number costs more here than anywhere else. The check does not soften
    because a flagship model wrote it — a better model makes the failure rarer,
    not less expensive.

    Returns a list of unverified figures. A non-empty list is a build failure;
    the caller does not get to publish and log it.
    """
    pool = _digest_numbers(digest)
    unverified = []

    for lang in ('tr', 'en'):
        block = data.get(lang)
        if not isinstance(block, dict):
            continue

        surfaces = [('overview', block.get('overview')),
                    ('regime_line', block.get('regime_line')),
                    ('regime_rationale', block.get('regime_rationale'))]
        for i, theme in enumerate(block.get('themes') or []):
            if isinstance(theme, dict):
                surfaces.append((f'themes[{i}].body', theme.get('description')))

        for field, text in surfaces:
            for raw, value in _figures_in(text):
                if any(abs(known - value) <= tolerance
                       or abs(abs(known) - abs(value)) <= tolerance
                       for known in pool):
                    continue
                print(f"      ❌ {lang.upper()} {field}: '{raw}' digest'te yok.")
                unverified.append({'lang': lang, 'field': field, 'value': raw})

    if unverified:
        print(f"      ❌ Yönetici özetinde {len(unverified)} doğrulanamayan sayı.")
    else:
        print(f"      ✅ Yönetici özetindeki tüm sayılar digest'te doğrulandı "
              f"({len(pool)} bilinen değer).")
    return unverified


def verify_theme_metric_keys(data, pass_one):
    """Each theme must cite a key_metric some section actually produced.

    A theme is the report's claim about what mattered this week. Requiring it
    to name the figure it rests on, and requiring that figure to have come from
    a section, is what keeps the three themes anchored to the pages behind them
    instead of floating free.
    """
    known = {a.get('key_metric') for a in pass_one.values() if a.get('key_metric')}
    bad = []

    for lang in ('tr', 'en'):
        block = data.get(lang)
        if not isinstance(block, dict):
            continue
        themes = block.get('themes') or []
        if len(themes) != 3:
            bad.append({'lang': lang, 'issue': f'{len(themes)} tema (3 olmalı)'})
        for i, theme in enumerate(themes):
            key = (theme or {}).get('metric_key')
            if not key:
                bad.append({'lang': lang, 'issue': f'themes[{i}] metric_key yok'})
            elif key not in known:
                bad.append({'lang': lang,
                            'issue': f"themes[{i}] metric_key '{key}' hiçbir bölümde yok"})

    for entry in bad:
        print(f"      ❌ {entry['lang'].upper()}: {entry['issue']}")
    return bad
