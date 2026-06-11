# validators.py
import os
import json
from datetime import datetime

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


def validate_ai_notes(data):
    """
    Scan AI generated notes for percentage figures (regex: [+-]?\d+\.\d+%).
    If a mentioned value does not exist in the non-AI metrics of data,
    the note is hidden (cleared to None) and 'ai_note_rejected': 'value_mismatch'
    is logged to fetch_report.json.
    """
    import re
    
    # 1. Recursively extract all numbers (int/float) from the snapshot data dictionary
    def collect_numbers(obj):
        numbers = set()
        if isinstance(obj, (int, float)):
            # Round to 4 decimal places to prevent floating point issues
            numbers.add(round(float(obj), 4))
        elif isinstance(obj, str):
            # Extract decimals, e.g. "0.61" or "-0.27" or "1.80"
            for match in re.findall(r'[+-]?\d+\.\d+', obj):
                try:
                    numbers.add(round(float(match), 4))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for k, v in obj.items():
                # Skip the AI-generated language layers to avoid self-referencing
                if k in ['tr', 'en', 'ai_summary', 'news_commentaries', 'design_improvement_report']:
                    continue
                numbers.update(collect_numbers(v))
        elif isinstance(obj, list):
            for item in obj:
                numbers.update(collect_numbers(item))
        return numbers

    snapshot_numbers = collect_numbers(data)
    
    # Debug print
    print(f"      🔍 Snapshot numbers collected for AI consistency check: {sorted(list(snapshot_numbers))}")
    
    mismatch_detected = False
    rejected_notes = []
    
    # 2. Iterate through notes in TR and EN
    for lang in ['tr', 'en']:
        lang_data = data.get(lang, {})
        notes = lang_data.get('notes', {})
        if isinstance(notes, dict):
            for note_key, note_text in list(notes.items()):
                if isinstance(note_text, str) and note_text.strip() and note_text.strip() != 'None':
                    # Find percentages like +0.61% or -0.27% or 1.80%
                    percentage_matches = re.findall(r'[+-]?\d+\.\d+%', note_text)
                    for match in percentage_matches:
                        val_str = match.replace('%', '').strip()
                        try:
                            val_float = float(val_str)
                        except ValueError:
                            continue
                        
                        # Check if the float exists in snapshot_numbers within 0.015 tolerance
                        found = False
                        for sn in snapshot_numbers:
                            if abs(sn - val_float) <= 0.015:
                                found = True
                                break
                        
                        if not found:
                            print(f"      ⚠️  AI Note Mismatch: {note_key} in {lang} mentions {match} which is not in snapshot.")
                            mismatch_detected = True
                            notes[note_key] = None  # Clear the note so it is hidden in layout
                            rejected_notes.append({
                                "lang": lang,
                                "note": note_key,
                                "unmatched_value": match
                            })
                            break  # Invalidate the entire note on first mismatch
                            
    if mismatch_detected:
        _log_ai_note_rejection(rejected_notes)
        
    return data

def _log_ai_note_rejection(rejected_notes):
    """Write ai_note_rejected: value_mismatch to fetch_report.json."""
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
