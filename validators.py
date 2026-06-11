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
