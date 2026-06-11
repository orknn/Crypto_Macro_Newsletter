import unittest
import os
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from data_fetcher import normalize_funding, calculate_oi_change_from_snapshots
import validators
from render.i18n import STR, format_bulletin_date
from render.daily import render_daily
from render.weekly import render_weekly

class NewsletterTests(unittest.TestCase):
    
    def test_normalize_funding(self):
        # Binance test
        self.assertAlmostEqual(normalize_funding(0.0001, 'binance'), 0.01)
        self.assertAlmostEqual(normalize_funding(-0.00025, 'binance'), -0.025)
        
        # Kraken linear test
        self.assertAlmostEqual(normalize_funding(0.00001, 'kraken', symbol='PF_SOLUSD'), 0.008)
        
        # Kraken inverse test (XBTUSD)
        # raw value of 0.05 absolute hourly on $50,000 spot price
        # relative hourly: 0.05 / 50000 = 0.000001
        # 8h percentage: 0.000001 * 8 * 100 = 0.0008%
        self.assertAlmostEqual(normalize_funding(0.05, 'kraken', price=50000, symbol='PF_XBTUSD'), 0.0008)

    def test_validators_sanitize(self):
        # Prepare sample out-of-range data
        sample_data = {
            'funding_rates': {
                'BTC': 0.85, # out of range [-0.75, 0.75]
                'ETH': 0.05  # within range
            },
            'crypto_futures_basis': {
                'btc_basis': 150.0, # out of range [-50, 100]
                'eth_basis': 5.0
            },
            'coinbase_premium': {
                'current_value': 8.5 # out of range [-5, 5]
            },
            'options_data': {
                'dvol_index': 300.0, # out of range [20, 250]
                'put_call_ratio': 6.0 # out of range [0.1, 5]
            },
            'macro_indicators': {
                'US 10-Year Treasury Yield': 15.0 # out of range [0, 12]
            }
        }
        
        # Clean up fetch_report.json if exists
        if os.path.exists("fetch_report.json"):
            try:
                os.remove("fetch_report.json")
            except:
                pass
                
        sanitized = validators.validate_and_sanitize(sample_data)
        
        # Verify values are set to None
        self.assertIsNone(sanitized['funding_rates']['BTC'])
        self.assertEqual(sanitized['funding_rates']['ETH'], 0.05)
        self.assertIsNone(sanitized['crypto_futures_basis']['btc_basis'])
        self.assertEqual(sanitized['crypto_futures_basis']['eth_basis'], 5.0)
        self.assertIsNone(sanitized['coinbase_premium']['current_value'])
        self.assertIsNone(sanitized['options_data']['dvol_index'])
        self.assertIsNone(sanitized['options_data']['put_call_ratio'])
        self.assertIsNone(sanitized['macro_indicators']['US 10-Year Treasury Yield'])
        
        # Verify fetch_report.json contains rejected entries
        self.assertTrue(os.path.exists("fetch_report.json"))
        with open("fetch_report.json", "r", encoding="utf-8") as f:
            report = json.load(f)
            self.assertIn("rejected", report)
            self.assertIn("funding_8h_BTC", report["rejected"])
            self.assertIn("btc_basis", report["rejected"])
            self.assertIn("coinbase_premium", report["rejected"])
            self.assertIn("dvol_index", report["rejected"])
            self.assertIn("put_call_ratio", report["rejected"])
            self.assertIn("US 10-Year Treasury Yield", report["rejected"])

    def test_i18n_completeness(self):
        # Check that all keys in STR have both 'tr' and 'en' keys and are non-empty
        for key, value in STR.items():
            self.assertIn('tr', value, f"Missing 'tr' key for {key}")
            self.assertIn('en', value, f"Missing 'en' key for {key}")
            self.assertTrue(len(value['tr']) > 0, f"Empty 'tr' value for {key}")
            self.assertTrue(len(value['en']) > 0, f"Empty 'en' value for {key}")

    def test_snapshot_oi_change(self):
        # Create a mock snapshot from 24h ago
        os.makedirs("snapshots", exist_ok=True)
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        mock_snapshot_path = f"snapshots/{yesterday_str}.json"
        
        mock_snap_data = {
            "open_interest": {
                "BTC": {"oi": 1000.0},
                "ETH": {"oi": 500.0}
            }
        }
        
        with open(mock_snapshot_path, "w", encoding="utf-8") as f:
            json.dump(mock_snap_data, f)
            
        try:
            current_oi = {
                "BTC": {"oi": 1050.0},  # should be +5.0%
                "ETH": {"oi": 490.0}    # should be -2.0%
            }
            
            updated_oi = calculate_oi_change_from_snapshots(current_oi, edition='daily')
            
            self.assertAlmostEqual(updated_oi['BTC']['oi_chg_24h'], 5.0)
            self.assertAlmostEqual(updated_oi['ETH']['oi_chg_24h'], -2.0)
        finally:
            if os.path.exists(mock_snapshot_path):
                os.remove(mock_snapshot_path)

    def test_smoke_dry_run(self):
        import sys
        # Run the pipeline in dry-run mode for daily, using both languages
        shutil.rmtree('out', ignore_errors=True)
        
        cmd = [sys.executable, "main.py", "--edition", "daily", "--lang", "both", "--dry-run", "--no-agents"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(res.returncode, 0, f"main.py execution failed: {res.stderr}\nStdout: {res.stdout}")
        
        # Verify that output files are produced
        self.assertTrue(os.path.exists("out/daily_tr.html"))
        self.assertTrue(os.path.exists("out/daily_en.html"))
        
        # Check size limit constraint (< 150KB)
        tr_size_kb = os.path.getsize("out/daily_tr.html") / 1024.0
        en_size_kb = os.path.getsize("out/daily_en.html") / 1024.0
        self.assertLess(tr_size_kb, 150.0, f"Turkish daily HTML size {tr_size_kb:.2f} KB exceeds 150 KB limit")
        self.assertLess(en_size_kb, 150.0, f"English daily HTML size {en_size_kb:.2f} KB exceeds 150 KB limit")

if __name__ == '__main__':
    unittest.main()
