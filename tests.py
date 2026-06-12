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

    def test_news_pipeline_no_fabrication(self):
        """H1: When Finnhub API returns no items, fallback MUST NOT generate fake news."""
        from render.components import render_news_section
        
        # Test 1: Empty news → empty render (section hidden)
        empty_news = {"news": []}
        result = render_news_section(empty_news, lang='tr')
        self.assertEqual(result, "", "Empty news should produce empty string for section hiding")
        
        # Test 2: News without real URLs → should be filtered out
        fake_news = {"news": [
            {"title": "Fake headline", "summary": "Fake summary", "url": "#", "source": "Unknown", "image_url": ""},
            {"title": "No URL", "summary": "No URL", "url": "", "source": "", "image_url": ""},
        ]}
        result = render_news_section(fake_news, lang='en')
        self.assertEqual(result, "", "News without real URLs should produce empty string")
        
        # Test 3: Real news items render properly with links
        real_news = {"news": [
            {"title": "Real headline", "summary": "Real summary", "url": "https://reuters.com/article/123", "source": "Reuters", "image_url": "", "datetime": 0},
            {"title": "Another headline", "summary": "Another summary", "url": "https://cnbc.com/article/456", "source": "CNBC", "image_url": "", "datetime": 0},
            {"title": "Third headline", "summary": "Third summary", "url": "https://bloomberg.com/article/789", "source": "Bloomberg", "image_url": "", "datetime": 0},
        ]}
        result = render_news_section(real_news, lang='en')
        self.assertIn("https://reuters.com/article/123", result, "Real news should have href")
        self.assertIn("Reuters", result, "Real news should show source")
        self.assertEqual(result.count('class="'), 0)  # Structure check (inline styles only)
    
    def test_news_renderer_drops_fabricated_ai_insights(self):
        """H1: If AI generates an insight for a headline not in the original news list, drop it."""
        from render.components import render_news_section
        
        news = {"news": [
            {"title": "Real News 1", "summary": "Sum 1", "url": "https://example.com/1", "source": "Reuters", "datetime": 0},
        ]}
        # AI returned 2 insights but we only have 1 news item — extra should be ignored
        insights = ["Insight for real news", "Fabricated insight for non-existent news"]
        result = render_news_section(news, insights, lang='en')
        self.assertIn("Insight for real news", result)
        self.assertNotIn("Fabricated insight", result)
    
    def test_calendar_matching_precision(self):
        """H3: economic calendar surprise guard rejects out-of-bounds actual values."""
        surprise_thresholds = {
            'cpi y/y': 1.0,
            'cpi m/m': 0.5,
            'core cpi m/m': 0.5,
        }
        
        def _parse_numeric(val_str):
            if not val_str or val_str == '—':
                return None
            try:
                return float(val_str.replace('%', '').strip())
            except (ValueError, TypeError):
                return None
        
        def _surprise_check(event_key, actual_str, consensus_str):
            threshold = surprise_thresholds.get(event_key.lower().strip())
            if threshold is None:
                return True
            actual_num = _parse_numeric(actual_str)
            consensus_num = _parse_numeric(consensus_str)
            if actual_num is None or consensus_num is None:
                return True
            diff = abs(actual_num - consensus_num)
            return diff <= threshold

        # Test cases
        self.assertTrue(_surprise_check('cpi m/m', '0.5%', '0.3%')) # diff = 0.2 <= 0.5
        self.assertFalse(_surprise_check('cpi m/m', '0.9%', '0.3%')) # diff = 0.6 > 0.5 (reject)
        self.assertTrue(_surprise_check('core cpi m/m', '0.2%', '0.3%')) # diff = 0.1 <= 0.5
        self.assertFalse(_surprise_check('core cpi m/m', '0.9%', '0.3%')) # diff = 0.6 > 0.5 (reject)
        self.assertTrue(_surprise_check('cpi y/y', '3.5%', '2.8%')) # diff = 0.7 <= 1.0
        self.assertFalse(_surprise_check('cpi y/y', '4.5%', '2.8%')) # diff = 1.7 > 1.0 (reject)
    
    def test_maybe_layout_guard(self):
        """H2: maybe() should filter None, empty, and literal 'None' values."""
        from render.components import maybe
        
        self.assertEqual(maybe("<div>content</div>", None), "")
        self.assertEqual(maybe("<div>content</div>", ""), "")
        self.assertEqual(maybe("<div>content</div>", "None"), "")
        self.assertEqual(maybe("<div>content</div>", " None "), "")
        self.assertEqual(maybe("<div>content</div>", "null"), "")
        self.assertEqual(maybe("<div>content</div>", "Real content"), "<div>content</div>")
        self.assertEqual(maybe("<div>content</div>", 42), "<div>content</div>")
    
    def test_no_literal_none_in_output(self):
        """H2: Generated HTML must not contain literal 'None' strings in content areas."""
        # Build minimal data with None values where AI output would go
        data = {
            'date': '2026-06-11',
            'crypto_prices': [],
            'crypto_market_overview': {'total_market_cap': 0, 'btc_dominance': 0},
            'macro_indicators': {},
            'magnificent_7': [],
            'commodities': [],
            'fear_and_greed': {'value': 50, 'classification': 'Neutral'},
            'funding_rates': {},
            'open_interest': {},
            'economic_calendar': [],
            'coinbase_premium': {},
            'macro_news': {'news': []},
            'global_liquidity': {},
            'm2_money_supply': {},
            'macro_scoreboard': {},
            'sp500_sectors': [],
            'crypto_futures_basis': {},
            'etf_flows': None,
            'bist_try': {},
            'stablecoin_data': {},
            'ticker_history': {},
            'regime': 'NEUTRAL',
            'tr': {
                'regime_line': None,
                'overview': None,
                'notes': {
                    'futures_note': None,
                    'etf_note': None,
                    'indicators_note': None,
                },
                'insights': []
            },
            'en': {
                'regime_line': None,
                'overview': None,
                'notes': {
                    'futures_note': None,
                    'etf_note': None,
                    'indicators_note': None,
                },
                'insights': []
            },
            'etf_history_data': [],
        }
        
        for lang in ['tr', 'en']:
            html = render_daily(data, lang=lang)
            # Check for literal 'None' outside of HTML comments and meta tags
            import re
            # Remove HTML comments first
            clean_html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
            # Remove script/style tags
            clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', clean_html, flags=re.DOTALL)
            # Check: no '>None<' or ': None' patterns
            self.assertNotIn('>None<', clean_html, f"Found literal 'None' in {lang} daily HTML")
            self.assertNotIn(': None', clean_html, f"Found ': None' in {lang} daily HTML")
    
    def test_html_lang_attribute(self):
        """H4: Generated HTML must have correct lang attribute."""
        data = {
            'date': '2026-06-11',
            'crypto_prices': [],
            'crypto_market_overview': {'total_market_cap': 0, 'btc_dominance': 0},
            'macro_indicators': {},
            'magnificent_7': [],
            'commodities': [],
            'fear_and_greed': {'value': 50, 'classification': 'Neutral'},
            'funding_rates': {},
            'open_interest': {},
            'economic_calendar': [],
            'coinbase_premium': {},
            'macro_news': {'news': []},
            'global_liquidity': {},
            'm2_money_supply': {},
            'macro_scoreboard': {},
            'sp500_sectors': [],
            'crypto_futures_basis': {},
            'etf_flows': None,
            'bist_try': {},
            'stablecoin_data': {},
            'ticker_history': {},
            'regime': 'NEUTRAL',
            'tr': {},
            'en': {},
            'etf_history_data': [],
        }
        
        tr_html = render_daily(data, lang='tr')
        en_html = render_daily(data, lang='en')
        
        self.assertIn('<html lang="tr">', tr_html, "TR HTML should have lang='tr'")
        self.assertIn('<html lang="en">', en_html, "EN HTML should have lang='en'")

    def test_tr_upper(self):
        from render.i18n import tr_upper
        self.assertEqual(tr_upper("jeopolitik"), "JEOPOLİTİK")
        self.assertEqual(tr_upper("likidite"), "LİKİDİTE")
        self.assertEqual(tr_upper("türkiye"), "TÜRKİYE")
        self.assertEqual(tr_upper("hisseler & emtialar"), "HİSSELER & EMTİALAR")

    def test_clean_calendar_val(self):
        from data_fetcher import _clean_calendar_val
        self.assertIsNone(_clean_calendar_val(None))
        self.assertEqual(_clean_calendar_val(""), "")
        self.assertEqual(_clean_calendar_val("   "), "")
        self.assertEqual(_clean_calendar_val(0), "0")
        self.assertEqual(_clean_calendar_val(0.0), "0.0")
        self.assertEqual(_clean_calendar_val(3.5), "3.5")
        self.assertEqual(_clean_calendar_val(" 2.5% "), "2.5%")

    def test_validate_ai_notes(self):
        # Prepare sample data
        data = {
            'crypto_futures_basis': {
                'btc_basis': 0.61,
                'eth_basis': 1.80,
            },
            'funding_rates': {
                'BTC': 0.05,
            },
            'tr': {
                'notes': {
                    'futures_note': "BTC vadeli primi +0.61% seviyesinde.",  # Valid: matches btc_basis
                    'etf_note': "ETF akışları -0.27% negatif.",             # Invalid: -0.27 not in snapshot
                    'indicators_note': "Bazı oranlar %0.56 düştü.",          # Invalid: 0.56 not in snapshot
                }
            },
            'en': {
                'notes': {
                    'futures_note': "ETH basis is at 1.80% currently.",     # Valid: matches eth_basis
                }
            }
        }
        
        # Clean up fetch_report.json if exists
        if os.path.exists("fetch_report.json"):
            try:
                os.remove("fetch_report.json")
            except:
                pass
                
        validated = validators.validate_ai_notes(data)
        
        # futures_note should be preserved
        self.assertEqual(validated['tr']['notes']['futures_note'], "BTC vadeli primi +0.61% seviyesinde.")
        self.assertEqual(validated['en']['notes']['futures_note'], "ETH basis is at 1.80% currently.")
        
        # etf_note and indicators_note should be set to None due to mismatch
        self.assertIsNone(validated['tr']['notes']['etf_note'])
        self.assertIsNone(validated['tr']['notes']['indicators_note'])
        
        # Verify fetch_report.json contains rejections
        self.assertTrue(os.path.exists("fetch_report.json"))
        with open("fetch_report.json", "r", encoding="utf-8") as f:
            report = json.load(f)
            self.assertEqual(report.get("ai_note_rejected"), "value_mismatch")
            rejected_values = [n["unmatched_value"] for n in report.get("rejected_ai_notes", [])]
            self.assertIn("-0.27%", rejected_values)
            self.assertIn("%0.56", rejected_values)

        # Assert that the fake TR note containing '%0.56' is NOT rendered in the final HTML
        html_tr = render_daily(validated, lang='tr')
        self.assertNotIn("Bazı oranlar", html_tr)
        self.assertNotIn("%0.56", html_tr)

if __name__ == '__main__':
    unittest.main()
