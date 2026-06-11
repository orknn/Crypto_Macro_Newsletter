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
        """H3: CPI m/m FRED actual should NOT leak into Core CPI m/m event."""
        # Simulate the matching logic
        fred_actuals = {
            'cpi m/m': '0.3%',
            'core cpi m/m': '0.2%',
            'cpi y/y': '2.4%',
        }
        
        # Build mock events
        events = [
            {'event': 'Core CPI MoM', 'actual': '—', 'forecast': '0.3%'},
            {'event': 'CPI MoM', 'actual': '—', 'forecast': '0.4%'},
            {'event': 'CPI YoY', 'actual': '—', 'forecast': '2.5%'},
        ]
        
        # Simulate the matching from data_fetcher.py
        sorted_fred_keys = sorted(fred_actuals.keys(), key=len, reverse=True)
        
        for ev in events:
            event_lower = ev.get('event', '').lower().strip()
            event_normalized = event_lower.replace('mom', 'm/m').replace('yoy', 'y/y').replace('qoq', 'q/q')
            matched = None
            
            # Exact match
            if event_normalized in fred_actuals:
                matched = fred_actuals[event_normalized]
            
            # Sorted contains match (longest first)
            if not matched:
                for fk in sorted_fred_keys:
                    if event_normalized == fk or event_normalized.endswith(fk):
                        if 'core' in event_normalized and 'core' not in fk:
                            continue
                        matched = fred_actuals[fk]
                        break
            
            if matched:
                ev['actual'] = matched
        
        # Core CPI MoM should match 'core cpi m/m' = 0.2%, NOT 'cpi m/m' = 0.3%
        self.assertEqual(events[0]['actual'], '0.2%', "Core CPI MoM matched wrong FRED key")
        self.assertEqual(events[1]['actual'], '0.3%', "CPI MoM should match cpi m/m")
        self.assertEqual(events[2]['actual'], '2.4%', "CPI YoY should match cpi y/y")
    
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

if __name__ == '__main__':
    unittest.main()
