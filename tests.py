import unittest
import os
import json
import shutil
import tempfile
import subprocess
from datetime import datetime, timedelta
from data_fetcher import normalize_funding, calculate_oi_change_from_snapshots
import validators
import signals
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

    def test_metric_specs_suppress_out_of_range(self):
        """Every specced number is held to its MetricSpec, not to a local if."""
        sample_data = {
            'funding_rates': {
                'BTC': 0.85,   # out of range [-0.75, 0.75]
                'ETH': 0.05,   # within range
            },
            'crypto_futures_basis': {
                'btc_basis': 150.0,   # out of range [-50, 100]
                'eth_basis': 5.0,
            },
            'coinbase_premium': {'current_value': 8.5},   # out of range [-5, 5]
            'options_data': {
                'dvol_index': 300.0,      # out of range [20, 250]
                'put_call_ratio': 6.0,    # out of range [0.1, 5]
            },
            'macro_indicators': {
                'US 10-Year Treasury Yield': 15.0,   # out of range [0.3, 12]
            },
        }

        sanitized, findings = validators.apply_metric_specs(sample_data)

        self.assertIsNone(sanitized['funding_rates']['BTC'])
        self.assertEqual(sanitized['funding_rates']['ETH'], 0.05)
        self.assertIsNone(sanitized['crypto_futures_basis']['btc_basis'])
        self.assertEqual(sanitized['crypto_futures_basis']['eth_basis'], 5.0)
        self.assertIsNone(sanitized['coinbase_premium']['current_value'])
        self.assertIsNone(sanitized['options_data']['dvol_index'])
        self.assertIsNone(sanitized['options_data']['put_call_ratio'])
        self.assertIsNone(sanitized['macro_indicators']['US 10-Year Treasury Yield'])

        suppressed = {f['name'] for f in findings if f['suppressed']}
        self.assertEqual(
            suppressed,
            {'funding_btc', 'btc_basis', 'coinbase_premium', 'dvol',
             'put_call_ratio', 'us10y'})
        for f in findings:
            if f['suppressed']:
                self.assertEqual(f['reason'], 'out_of_range')

    def test_build_report_lists_every_na(self):
        """A thin bulletin must be readable from build_report.json alone."""
        data = {'macro_scoreboard': {'MOVE': 0.0}}
        data, findings = validators.apply_metric_specs(data)
        path = os.path.join(tempfile.mkdtemp(), 'build_report.json')
        report = validators.write_build_report(data, findings,
                                               edition='weekly', path=path)

        self.assertTrue(os.path.exists(path))
        self.assertEqual(report['metrics_na'], 1)
        self.assertEqual(report['na'][0]['name'], 'move')
        self.assertEqual(report['na'][0]['reason'], 'zero_not_valid')
        self.assertEqual(report['na'][0]['source'], 'yfinance ^MOVE')

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
                
        validated = validators.validate_ai_numbers(data)
        
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


class DataIntegrityTests(unittest.TestCase):
    """T1-T9: the nine defects the 8 Aug 2026 weekly PDF actually shipped.

    Each test names the failure it locks down. They are written against the
    render and validation layers, so the whole class runs offline — no network,
    no model, no key.
    """

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _body(html):
        """The rendered page without <head>, so CSS text is not searched."""
        return html.split('</head>')[-1]

    @staticmethod
    def _weekly(**overrides):
        payload = {
            'macro_scoreboard': {'DXY': 100.85, 'DXY_chg': -0.53,
                                 'MOVE': 94.4, 'MOVE_chg': -2.08,
                                 'HY_OAS': 2.74, 'HY_OAS_chg_bp': -2.0,
                                 'COPPER_GOLD': 1.492, 'COPPER_GOLD_chg': -5.75},
            'macro_indicators': {'US 10-Year Treasury Yield': 4.48,
                                 'US 2-Year Treasury Yield': 4.17,
                                 '2s10s_spread': 0.31,
                                 'VIX': 16.1, 'VIX_chg': -2.65},
            'crypto_futures_basis': {'btc_basis': 5.4, 'eth_basis': 6.1},
            'options_data': {}, 'funding_rates': {}, 'open_interest': {},
            'fear_and_greed': {'value': 31, 'classification': 'Fear'},
            'crypto_prices': [], 'crypto_market_overview': {},
            'economic_calendar': [], 'macro_news': {},
            # Sections are dropped when their note has no "so what"
            # (render.weekly.REQUIRE_SO_WHAT), so a fixture that wants a
            # section rendered has to carry a usable note for it.
            'tr': {'notes': {
                'inflation_note': {'what': 'Manşet TÜFE yataylaştı.',
                                   'so_what': 'Reel faiz baskısı sürüyor; uzun vadeli tahvil ağırlığı korunur.'},
                'futures_note': {'what': 'Vadeli primler ölçülü.',
                                 'so_what': 'Kaldıraç birikmiş değil; sert tasfiye riski düşük.'},
            }},
            'en': {'notes': {
                'inflation_note': {'what': 'Headline CPI flattened.',
                                   'so_what': 'Real-rate pressure persists; stay long duration.'},
                'futures_note': {'what': 'Futures premia are moderate.',
                                 'so_what': 'Leverage is not crowded; liquidation risk is low.'},
            }},
        }
        payload.update(overrides)
        return payload

    # ── T1 ───────────────────────────────────────────────────────────

    def test_T1_move_zero_renders_na(self):
        """MOVE 0.0 was a failed fetch wearing a measurement."""
        data = self._weekly()
        data['macro_scoreboard']['MOVE'] = 0.0
        data, findings = validators.apply_metric_specs(data)

        self.assertIsNone(data['macro_scoreboard']['MOVE'])
        self.assertEqual(
            [f['reason'] for f in findings
             if f['name'] == 'move' and f['suppressed']],
            ['zero_not_valid'])

        body = self._body(render_weekly(data, lang='tr'))
        self.assertIn('class="na"', body)
        self.assertNotRegex(body, r'MOVE[\s\S]{0,200}?>\s*0\.0\s*<')

    # ── T2 ───────────────────────────────────────────────────────────

    def test_T2_missing_basis_renders_na_not_dash(self):
        """A dead Binance leg printed an em dash that read as 'flat'."""
        data = self._weekly(crypto_futures_basis=None)
        body = self._body(render_weekly(data, lang='tr'))

        self.assertNotRegex(body, r'>\s*—\s*<')
        self.assertIn('class="na"', body)

    # ── T3 ───────────────────────────────────────────────────────────

    def test_T3_level_and_change_never_share_a_source(self):
        """A level fed to a change formatter invents a move that never happened.

        The 2s10s tile printed 0.41% as its level and +0.41% as its weekly
        change, both from the same subtraction. This asserts the structural
        rule rather than that one tile: no change-unit metric may draw on the
        same source_field as a level-unit metric.
        """
        from config.metrics import METRIC_SPECS

        by_source = {}
        for spec in METRIC_SPECS:
            if spec.source_field:
                by_source.setdefault(spec.source_field, []).append(spec)

        for source_field, specs in by_source.items():
            kinds = {s.is_change for s in specs}
            self.assertNotEqual(
                kinds, {True, False},
                f"source_field {source_field!r} feeds both a level and a "
                f"change: {[s.name for s in specs]}")

    def test_T3_spread_tile_shows_level_not_a_fabricated_change(self):
        data = self._weekly()
        body = self._body(render_weekly(data, lang='tr'))

        # 0.31 = 4.48 - 4.17. It must appear once as a level, and must not be
        # repeated as a signed percentage move.
        self.assertIn('0.31%', body)
        self.assertNotIn('+0.31%', body)
        self.assertIn(STR['label_level']['tr'], body)

    # ── T4 ───────────────────────────────────────────────────────────

    def test_T4_copper_gold_label_follows_direction(self):
        """The label was hardcoded, so a fall still read 'growth signal'."""
        falling = self._weekly()
        falling['macro_scoreboard']['COPPER_GOLD_chg'] = -5.75
        body = self._body(render_weekly(falling, lang='tr'))
        self.assertIn(STR['growth_slowdown_signal']['tr'], body)
        self.assertNotIn(STR['growth_signal']['tr'], body)

        rising = self._weekly()
        rising['macro_scoreboard']['COPPER_GOLD_chg'] = 4.77
        body = self._body(render_weekly(rising, lang='tr'))
        self.assertIn(STR['growth_signal']['tr'], body)

    # ── T5 / T6 ──────────────────────────────────────────────────────

    def test_T5_model_never_sees_an_unrendered_max_pain(self):
        """The note said 70,000; the table said 65,000. Both were real.

        The quarterly max_pain_price is in the payload but the weekly page only
        prints per-expiry max pain, so the model could quote a figure the
        reader could not find. The model's copy must not contain it.
        """
        from agents import _prepare_data_summary

        data = self._weekly(options_data={
            'max_pain_price': 70000,          # quarterly, never rendered weekly
            'put_call_ratio': 0.575,          # never rendered weekly
            'dvol_index': 45.2,               # never rendered weekly
            'risk_reversal_25d': 1.4,         # rendered
            'large_expirations': [{'expiry': '29AUG26', 'date_str': '29 Aug 2026',
                                   'notional': 1.2e9, 'max_pain': 65000}],
        })
        summary = _prepare_data_summary(data, edition='weekly')
        opts = summary.get('options_data', {})

        self.assertNotIn('max_pain_price', opts)
        self.assertNotIn('put_call_ratio', opts)
        self.assertNotIn('dvol_index', opts)
        self.assertIn('risk_reversal_25d', opts)
        self.assertIn('large_expirations', opts)

    def test_T6_note_figure_absent_from_the_page_is_suppressed(self):
        """'put/call 0,575' appeared in prose with no field to check it against."""
        data = self._weekly(options_data={'put_call_ratio': 0.575})
        data['tr'] = {'notes': {'futures_note': {
            'what': 'Put/call orani %0,575 seviyesinde.',
            'so_what': 'Opsiyon tarafinda korunma talebi arttigina isaret eder.'}}}
        data['en'] = {}

        validated = validators.validate_ai_numbers(data, edition='weekly')
        self.assertIsNone(validated['tr']['notes']['futures_note'])

    # ── T7 ───────────────────────────────────────────────────────────

    def test_T7_cpi_chart_and_calendar_agree(self):
        """Calendar said 3.5%, the chart said 3.73% — same series, two vintages."""
        from data_fetcher import CPI_SERIES

        # The published headline YoY comes from the NOT seasonally adjusted
        # index. Computing YoY off the SA series cannot reproduce it, which is
        # what put two different CPI numbers on two pages of one bulletin.
        self.assertEqual(CPI_SERIES['cpi'], 'CPIAUCNS')
        self.assertEqual(CPI_SERIES['core_cpi'], 'CPILFENS')

    def test_T7_reconciler_flags_a_split_vintage(self):
        data = self._weekly(
            inflation_history_data=[{'date': '2026-06', 'cpi': 3.73,
                                     'core_cpi': 3.1, 'core_pce': 2.9}],
            economic_calendar=[{'event': 'CPI YoY', 'country': 'USD',
                                'previous': '3.5%', 'forecast': '', 'actual': '',
                                'importance': 3, 'date': '12 Aug Wed', 'time': '15:30'}])
        conflicts = validators.reconcile_shared_series(data)
        self.assertTrue(any(c['series'] == 'cpi_yoy' for c in conflicts), conflicts)

    # ── T8 ───────────────────────────────────────────────────────────

    def test_T8_one_btc_price_across_the_bulletin(self):
        """$65,210 in the watchlist, $65,207 in the cycle panel."""
        data = self._weekly(
            crypto_prices=[{'Symbol': 'BTC', 'Current Price USD': 65210.0,
                            '7d %': 1.2, 'Market Cap': 1.3e12}],
            btc_cycle_metrics={'spot': 65207.0, 'wma200': 48000.0,
                               'mayer_multiple': 1.21, 'ath': 126000.0,
                               'drawdown': -48.2, 'distance_to_200wma': 35.8,
                               'monthly_heatmap': None})
        data = validators.unify_spot_prices(data)

        self.assertEqual(data['btc_cycle_metrics']['spot'], 65210.0)
        # The derived figures must be recomputed, not left describing the old spot.
        self.assertAlmostEqual(
            data['btc_cycle_metrics']['distance_to_200wma'],
            ((65210.0 - 48000.0) / 48000.0) * 100, places=2)
        self.assertAlmostEqual(
            data['btc_cycle_metrics']['drawdown'],
            ((65210.0 - 126000.0) / 126000.0) * 100, places=2)

    # ── T9 ───────────────────────────────────────────────────────────

    def test_T9_yield_changes_are_basis_points_not_relative_percent(self):
        """'2 yillik tahvil faizi %1,67 yukselirken' was a relative move.

        A 4.10 -> 4.17 yield is +7 bps. Expressed as a percentage change it is
        +1.67%, which reads in prose as either a level or a 167 bp move — both
        wrong, and both were published.
        """
        from data_fetcher import _yield_change_bp

        self.assertAlmostEqual(_yield_change_bp(4.17, 4.10), 7.0, places=4)
        self.assertAlmostEqual(_yield_change_bp(4.10, 4.17), -7.0, places=4)
        self.assertIsNone(_yield_change_bp(4.17, None))

    def test_T9_yield_change_specs_are_bps(self):
        from config.metrics import SPECS_BY_NAME, BPS

        for name in ('us2y_chg', 'us10y_chg'):
            self.assertEqual(SPECS_BY_NAME[name].unit, BPS,
                             f"{name} must be a basis-point change")

    def test_T9_yield_tile_labels_its_unit(self):
        data = self._weekly()
        data['macro_indicators']['US 10-Year Treasury Yield_chg'] = 7.0
        body = self._body(render_weekly(data, lang='tr'))
        self.assertIn('bps', body)


class SnapshotDisciplineTests(unittest.TestCase):
    """Phase 1.3: one cut for the run, and an age for every number."""

    def test_header_prints_the_data_cut(self):
        from render.components import format_as_of
        label = format_as_of('2026-08-09T14:00:00', lang='tr')
        self.assertIn('Veri kesim', label)
        self.assertIn('TSİ', label)
        self.assertIn('2026-08-09', label)

    def test_header_omits_the_cut_when_there_is_none(self):
        from render.components import format_as_of
        self.assertIsNone(format_as_of(None, lang='tr'))
        self.assertIsNone(format_as_of('not a timestamp', lang='tr'))

    def test_weekly_header_carries_the_cut(self):
        data = DataIntegrityTests._weekly(as_of='2026-08-09T14:00:00')
        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn('Veri kesim', body)

    def test_stale_value_is_suppressed(self):
        """Freshly fetched is not the same as fresh."""
        now = datetime(2026, 8, 9, 14, 0, 0)
        data = {
            'macro_scoreboard': {'MOVE': 94.4},
            '_observed_at': {
                # Fetched seconds ago, but the newest bar is three weeks old.
                'macro_scoreboard.MOVE': (now - timedelta(days=21)).isoformat(),
            },
        }
        data, findings = validators.apply_metric_specs(data, now=now)

        self.assertIsNone(data['macro_scoreboard']['MOVE'])
        stale = [f for f in findings if f['name'] == 'move']
        self.assertEqual(stale[0]['reason'], 'stale')

    def test_fresh_value_survives(self):
        now = datetime(2026, 8, 9, 14, 0, 0)
        data = {
            'macro_scoreboard': {'MOVE': 94.4},
            '_observed_at': {
                'macro_scoreboard.MOVE': (now - timedelta(hours=20)).isoformat(),
            },
        }
        data, findings = validators.apply_metric_specs(data, now=now)
        self.assertEqual(data['macro_scoreboard']['MOVE'], 94.4)
        self.assertFalse([f for f in findings if f['name'] == 'move'])

    def test_derived_metric_inherits_its_oldest_input(self):
        """A spread built from a stale leg is stale, however recently computed."""
        from config.metrics import build_observed_at

        now = datetime(2026, 8, 9, 14, 0, 0)
        observed = build_observed_at(
            fred_obs={'DGS2': now - timedelta(days=30)},      # stale leg
            yf_obs={'^TNX': now - timedelta(hours=2)},        # fresh leg
            run_as_of=now)

        self.assertEqual(observed['macro_indicators.2s10s_spread'],
                         now - timedelta(days=30))

    def test_live_feed_is_stamped_with_the_run_cut(self):
        from config.metrics import build_observed_at

        now = datetime(2026, 8, 9, 14, 0, 0)
        observed = build_observed_at({}, {}, run_as_of=now)
        # alternative.me is polled live, so fetch time really is observation time.
        self.assertEqual(observed['fear_and_greed.value'], now)
        # A yfinance-backed metric we never managed to fetch stays unstamped,
        # so build_report.json reports it rather than guessing an age.
        self.assertNotIn('macro_scoreboard.MOVE', observed)

    def test_every_spec_can_be_aged(self):
        """No spec may be silently un-ageable once its feed is working."""
        from config.metrics import METRIC_SPECS, build_observed_at, observation_sources

        now = datetime(2026, 8, 9, 14, 0, 0)
        fred_obs, yf_obs = {}, {}
        for spec in METRIC_SPECS:
            fred_ids, tickers = observation_sources(spec)
            for i in fred_ids:
                fred_obs[i] = now
            for t in tickers:
                yf_obs[t] = now

        observed = build_observed_at(fred_obs, yf_obs, run_as_of=now)
        missing = [s.name for s in METRIC_SPECS if s.path not in observed]
        self.assertEqual(missing, [], f"specs with no reachable age: {missing}")

    def test_no_unenforced_staleness_when_stamps_are_present(self):
        from config.metrics import METRIC_SPECS, build_observed_at, observation_sources

        now = datetime(2026, 8, 9, 14, 0, 0)
        fred_obs, yf_obs = {}, {}
        for spec in METRIC_SPECS:
            f, t = observation_sources(spec)
            fred_obs.update({i: now for i in f})
            yf_obs.update({k: now for k in t})

        data = {'_observed_at': {p: s.isoformat() for p, s
                                 in build_observed_at(fred_obs, yf_obs, now).items()},
                'macro_scoreboard': {'MOVE': 94.4}}
        _, findings = validators.apply_metric_specs(data, now=now)
        self.assertFalse([f for f in findings if f['reason'] == 'staleness_unknown'])


class BlocklistTests(unittest.TestCase):
    """Phase 1.4: text about the pipeline is not content about the market."""

    # The exact sentence the 8 Aug weekly mailed to subscribers.
    LEAKED = ("Temiz ve net bir piyasa haberi olmayan bu genel izleme listesi "
              "için ayrıca insight üretilmemiştir.")

    def test_the_sentence_that_shipped_is_caught(self):
        self.assertTrue(validators.blocklisted_phrases(self.LEAKED))

    def test_leaked_note_is_dropped_not_published(self):
        clean = {'what': 'ETF girişleri haftalık bazda güçlendi.',
                 'so_what': 'Kurumsal talep sürüyor; geri çekilmeler alım fırsatı.'}
        data = {'tr': {'notes': {'futures_note': {'what': 'Vadeli primler ölçülü.',
                                                  'so_what': self.LEAKED},
                                 'etf_note': clean}},
                'en': {}}
        validators.scrub_generated_text(data)

        # A fault in either half drops the whole note.
        self.assertIsNone(data['tr']['notes']['futures_note'])
        # A clean note in the same block is untouched.
        self.assertEqual(data['tr']['notes']['etf_note'], clean)

    def test_leaked_note_never_reaches_the_page(self):
        data = DataIntegrityTests._weekly()
        data['tr'] = {'notes': {'futures_note': {'what': self.LEAKED,
                                                 'so_what': self.LEAKED}}}
        validators.scrub_generated_text(data)

        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertNotIn('üretilmemiştir', body)
        self.assertNotIn('izleme listesi için ayrıca', body)

    def test_sentinels_are_blocked(self):
        for text in ('Sonuç: None', 'value is undefined', 'TODO: revise this',
                     'Hesaplama hatası oluştu', 'null döndü', 'NaN'):
            self.assertTrue(validators.blocklisted_phrases(text),
                            f"should be blocked: {text!r}")

    def test_english_edition_is_covered(self):
        for text in ('No insight was generated for this watchlist.',
                     'Data not available for this section.',
                     'Unable to determine the trend.'):
            self.assertTrue(validators.blocklisted_phrases(text),
                            f"should be blocked: {text!r}")

    def test_real_market_prose_survives(self):
        """The blocklist must not eat the product it is protecting."""
        clean = [
            'Fed net likiditesi haftalık bazda daraldı, risk iştahı zayıf.',
            'ETF girişleri güçlü ancak Coinbase primi negatif.',
            'Karşı tarafın muhatabı olarak takas riski sınırlı kaldı.',
            'Muhatap kurum takas riskini üstlendi.',
            'Piyasa, enflasyon patikasının yataylaştığını fiyatlıyor.',
            'Volatilite hatırı sayılır ölçüde geriledi.',
            'Credit spreads narrowed while equity vol stayed contained.',
            'The nonfarm print landed above consensus.',
        ]
        for text in clean:
            self.assertEqual(validators.blocklisted_phrases(text), [],
                             f"false positive on: {text!r}")

    def test_insight_is_blanked_and_list_length_preserved(self):
        """main.py matches insights to headlines by position."""
        data = {'tr': {'insights': ['Gerçek bir yorum.', self.LEAKED,
                                    'Başka bir yorum.']},
                'en': {}}
        validators.scrub_generated_text(data)

        self.assertEqual(len(data['tr']['insights']), 3)
        self.assertEqual(data['tr']['insights'][1], "")
        self.assertEqual(data['tr']['insights'][0], 'Gerçek bir yorum.')

    def test_theme_is_dropped_whole(self):
        data = {'tr': {'themes': [
            {'title': 'LİKİDİTE', 'description': 'Fed bilançosu daraldı.'},
            {'title': 'BELİRSİZ', 'description': 'Yeterli veri bulunamadı.'},
        ]}, 'en': {}}
        validators.scrub_generated_text(data)

        self.assertEqual(len(data['tr']['themes']), 1)
        self.assertEqual(data['tr']['themes'][0]['title'], 'LİKİDİTE')

    def test_blocked_overview_trips_the_quality_gate(self):
        """An empty overview must fail the run, not ship a hollow bulletin."""
        data = {'tr': {'overview': self.LEAKED}, 'en': {}}
        validators.scrub_generated_text(data)

        self.assertIsNone(data['tr']['overview'])
        self.assertTrue(data['ai_validation']['blocklisted'])

    def test_research_topic_carrying_an_internal_message_is_dropped(self):
        brief = {'featured_topics': [
            {'tr': {'title': 'CPI', 'topic': 'Enflasyon patikası izlenmeli.'},
             'en': {'title': 'CPI', 'topic': 'Watch the inflation path.'}},
            {'tr': {'title': 'X', 'topic': 'Bu konu için veri bulunamadı.'},
             'en': {'title': 'X', 'topic': 'No data for this topic.'}},
        ]}
        cleaned, rejected = validators.validate_research_brief(brief, {})

        self.assertEqual(len(cleaned['featured_topics']), 1)
        self.assertEqual(cleaned['featured_topics'][0]['tr']['title'], 'CPI')
        self.assertTrue(rejected)

    def test_blocklist_is_not_applied_to_the_na_tooltip(self):
        """The render layer says 'Veri alınamadı' on purpose; that is not a leak."""
        from render.components import na
        body = render_weekly(DataIntegrityTests._weekly(
            crypto_futures_basis=None), lang='tr').split('</head>')[-1]

        self.assertIn('Veri alınamadı', body)   # the tooltip, by design
        self.assertIn('class="na"', body)


class InsightLayerTests(unittest.TestCase):
    """Phase 2: a reading beside every number, and the contradictions named."""

    # ── 2.1 so-what ──────────────────────────────────────────────────

    def test_note_without_so_what_is_not_rendered(self):
        from render.components import render_analyst_note
        self.assertEqual(
            render_analyst_note({'what': 'ETF akışı +865M.', 'so_what': ''}, 'tr'), '')
        self.assertEqual(render_analyst_note('Sadece düz metin.', 'tr'), '')
        self.assertEqual(render_analyst_note(None, 'tr'), '')

    def test_note_with_so_what_renders_both_lines(self):
        from render.components import render_analyst_note
        html = render_analyst_note(
            {'what': 'ETF akışı +865M.',
             'so_what': 'Kurumsal talep sürüyor; geri çekilmeler alım fırsatı.'}, 'tr')
        self.assertIn('Ne oldu', html)
        self.assertIn('Ne demek', html)
        self.assertIn('alım fırsatı', html)

    def test_section_disappears_without_a_so_what(self):
        """The brief's rule: no reading means no section, not a bare chart."""
        from render.weekly import REQUIRE_SO_WHAT
        self.assertTrue(REQUIRE_SO_WHAT)

        data = DataIntegrityTests._weekly()
        with_note = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn(STR['section_macro_scoreboard']['tr'], with_note)

        data['tr']['notes']['inflation_note'] = {'what': 'TÜFE yataylaştı.',
                                                 'so_what': ''}
        without = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertNotIn(STR['section_macro_scoreboard']['tr'], without)

    def test_note_dict_is_checked_on_both_halves(self):
        data = {'tr': {'notes': {
            'etf_note': {'what': 'Akış güçlü.', 'so_what': 'Bu konu için veri yok.'}}},
            'en': {}}
        validators.scrub_generated_text(data)
        self.assertIsNone(data['tr']['notes']['etf_note'])

    # ── 2.2 conflicting signals ──────────────────────────────────────

    def test_the_conflict_that_shipped_is_detected(self):
        """+865M of ETF inflow against a negative Coinbase premium."""
        data = {
            'etf_weekly_history_data': [{'date': '2026-08-09', 'Total_flow_m': 865.3}],
            'coinbase_premium': {'current_value': -0.076},
        }
        conflicts = signals.detect_conflicts(data)
        pairs = [c['pair'] for c in conflicts]
        self.assertIn('etf_flow|coinbase_premium', pairs)

        conflict = next(c for c in conflicts if c['pair'] == 'etf_flow|coinbase_premium')
        self.assertEqual(conflict['signal_a']['direction'], signals.RISK_ON)
        self.assertEqual(conflict['signal_b']['direction'], signals.RISK_OFF)
        # This one is mechanical, so the explanation comes from the code.
        self.assertIn('OTC', conflict['mechanism']['tr'])

    def test_agreeing_signals_are_not_a_conflict(self):
        data = {
            'etf_weekly_history_data': [{'date': '2026-08-09', 'Total_flow_m': 865.3}],
            'coinbase_premium': {'current_value': 0.09},
        }
        self.assertEqual(signals.detect_conflicts(data), [])

    def test_dead_band_prevents_a_manufactured_conflict(self):
        """A section that appears every week stops being read."""
        data = {
            'etf_weekly_history_data': [{'date': '2026-08-09', 'Total_flow_m': 12.0}],
            'coinbase_premium': {'current_value': -0.004},
        }
        self.assertEqual(signals.detect_conflicts(data), [])

    def test_missing_leg_is_not_a_conflict(self):
        data = {'etf_weekly_history_data': [{'Total_flow_m': 865.3}],
                'coinbase_premium': {'current_value': None}}
        self.assertEqual(signals.detect_conflicts(data), [])

    def test_breadth_signal_is_centred_on_a_half(self):
        weak = {'sp500_sectors': [{'Change %': v} for v in
                                  (-1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1)]}
        strong = {'sp500_sectors': [{'Change %': v} for v in
                                    (1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1)]}
        self.assertEqual(signals.read_all(weak)['sector_breadth']['direction'],
                         signals.RISK_OFF)
        self.assertEqual(signals.read_all(strong)['sector_breadth']['direction'],
                         signals.RISK_ON)

    def test_mechanical_conflict_uses_the_code_not_the_model(self):
        data = DataIntegrityTests._weekly()
        data['signal_conflicts'] = signals.detect_conflicts({
            'etf_weekly_history_data': [{'Total_flow_m': 865.3}],
            'coinbase_premium': {'current_value': -0.076}})
        # Even with the model claiming otherwise, the structural answer wins.
        data['tr']['conflicting_signals'] = [
            {'pair': 'etf_flow|coinbase_premium', 'reconciliation': 'Model uydurması.'}]

        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn(STR['section_conflicts']['tr'], body)
        self.assertIn('OTC', body)
        self.assertNotIn('Model uydurması', body)

    def test_unresolved_conflict_says_so(self):
        data = DataIntegrityTests._weekly()
        data['signal_conflicts'] = [{
            'pair': 'vix|credit_spreads',
            'signal_a': {'name': 'vix', 'labels': signals.SIGNALS['vix'][1],
                         'value': '-4.10%', 'direction': signals.RISK_ON},
            'signal_b': {'name': 'credit_spreads',
                         'labels': signals.SIGNALS['credit_spreads'][1],
                         'value': '+18.0 bps', 'direction': signals.RISK_OFF},
            'mechanism': None,
        }]
        data['tr']['conflicting_signals'] = [
            {'pair': 'vix|credit_spreads', 'reconciliation': 'UNRESOLVED'}]

        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn('Çelişki devam ediyor', body)

    def test_no_conflicts_means_no_section(self):
        data = DataIntegrityTests._weekly()
        data['signal_conflicts'] = []
        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertNotIn(STR['section_conflicts']['tr'], body)

    def test_model_reconciliation_is_number_checked(self):
        data = {'tr': {'conflicting_signals': [
                    {'pair': 'vix|credit_spreads',
                     'reconciliation': 'Kredi makası %99,99 genişledi.'}]},
                'en': {}, 'macro_scoreboard': {'HY_OAS_chg_bp': 18.0}}
        validators.validate_ai_numbers(data, edition='weekly')
        self.assertIsNone(data['tr']['conflicting_signals'][0]['reconciliation'])

    # ── 2.3 institutional flows ──────────────────────────────────────

    def test_etf_card_shows_flow_beside_its_context(self):
        """A net inflow alone cannot tell directional demand from basis trade."""
        data = DataIntegrityTests._weekly()
        data['etf_weekly_history_data'] = [
            {'date': '2026-08-02', 'Total_flow_m': -61.0, 'IBIT_flow_m': -20.0, 'FBTC_flow_m': -41.0},
            {'date': '2026-08-09', 'Total_flow_m': 865.3, 'IBIT_flow_m': 500.0, 'FBTC_flow_m': 200.0}]
        data['eth_etf_weekly_data'] = [{'date': '2026-08-09', 'Total_flow_m': 243.7}]
        data['funding_rates'] = {'BTC': 0.0039}
        data['open_interest'] = {'BTC': {'oi': 150600000, 'oi_chg_7d': 4.2}}
        data['tr']['notes']['etf_note'] = {
            'what': 'BTC ETF haftalık net akış +865M.',
            'so_what': 'Funding durgun; akış baz işleminden çok yönlü talebe yakın.'}

        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn('BTC ETF', body)
        self.assertIn('ETH ETF', body)
        self.assertIn('Önceki hafta', body)
        self.assertIn('-61.0M', body)
        self.assertIn('Bağlam', body)
        self.assertIn('+0.0039%', body)

    def test_etf_card_handles_a_missing_leg(self):
        data = DataIntegrityTests._weekly()
        data['etf_weekly_history_data'] = [
            {'date': '2026-08-09', 'Total_flow_m': None,
             'IBIT_flow_m': None, 'FBTC_flow_m': None}]
        data['tr']['notes']['etf_note'] = {'what': 'x', 'so_what': 'y'}
        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn('class="na"', body)


class ModelRoutingTests(unittest.TestCase):
    """Phase 2.5: which model runs which call, and the lint that keeps it so."""

    def test_no_bare_alias_anywhere_in_the_source(self):
        """An unqualified gpt-5.6 routes to flagship and bills at flagship rates.

        This is the lint rule the brief asks for. It is a test rather than a
        comment because the failure mode is silent: the call succeeds, the
        output looks right, and the difference only shows up on an invoice.
        """
        import glob
        import re

        # Only string literals matter: a bare alias inside quotes is what
        # reaches the API. The same characters in a comment are prose about
        # the rule, not a violation of it.
        bare = re.compile(r'''['\"]gpt-5\.6(?!-(?:sol|terra|luna))''')
        offenders = []
        for path in glob.glob('**/*.py', recursive=True):
            if '.venv' in path or path.endswith('tests.py'):
                continue
            with open(path, encoding='utf-8') as f:
                for lineno, line in enumerate(f, 1):
                    if bare.search(line):
                        offenders.append(f'{path}:{lineno}: {line.strip()}')

        self.assertEqual(offenders, [],
                         'bare gpt-5.6 alias found:\n' + '\n'.join(offenders))

    def test_the_lint_would_catch_a_real_violation(self):
        """A lint that cannot fail is not a lint."""
        import re
        bare = re.compile(r'''['\"]gpt-5\.6(?!-(?:sol|terra|luna))''')

        self.assertTrue(bare.search("model = 'gpt-5.6'"))
        self.assertTrue(bare.search('model = "gpt-5.6"'))
        self.assertIsNone(bare.search("model = 'gpt-5.6-terra'"))
        self.assertIsNone(bare.search('# never write a bare `gpt-5.6` here'))

    def test_every_call_site_names_a_qualified_model(self):
        from config.models import MODEL, PRICING

        for attr in dir(MODEL):
            if attr.startswith('_'):
                continue
            model = getattr(MODEL, attr)
            self.assertIn(model, PRICING, f'{attr} -> {model} is unpriced')
            self.assertRegex(model, r'-(?:sol|terra|luna)$')

    def test_routing_matches_the_agreed_tiers(self):
        from config import models
        self.assertEqual(models.MODEL.SECTION_NOTE, models.TERRA)
        self.assertEqual(models.MODEL.NEWS_INSIGHT, models.TERRA)
        self.assertEqual(models.MODEL.EXEC_SUMMARY, models.SOL)
        # The daily edition runs 22 times a month against the weekly's 4.3 and
        # was deliberately left alone.
        self.assertEqual(models.MODEL.DAILY_EDITOR, models.LUNA)

    def test_flagship_is_used_exactly_once(self):
        from config import models
        flagship = [a for a in dir(models.MODEL)
                    if not a.startswith('_')
                    and getattr(models.MODEL, a) == models.SOL]
        self.assertEqual(flagship, ['EXEC_SUMMARY'])

    def test_cached_input_is_billed_at_a_tenth(self):
        from config import models
        full = models.estimate_cost(models.SOL, 10_000, 0)
        cached = models.estimate_cost(models.SOL, 10_000, 0,
                                      cached_input_tokens=10_000)
        self.assertAlmostEqual(cached, full * 0.1, places=8)

    def test_pass_two_reasoning_effort_is_low_not_off(self):
        """Templated compression, not exploration — but not zero either."""
        from config import models
        self.assertEqual(models.reasoning_effort(models.SOL), 'low')
        self.assertEqual(models.reasoning_effort(models.TERRA), 'none')

    # ── the two passes ───────────────────────────────────────────────

    def test_section_context_is_narrow(self):
        """A section note must not be able to quote another section's chart."""
        from agents import SECTION_CONTEXT

        data = {'btc_cycle_metrics': {'spot': 65210.0},
                'etf_weekly_history_data': [{'Total_flow_m': 865.3}],
                'macro_news': {'news': [{'title': 'x'}]}}
        from agents import _section_payload

        cycle = _section_payload('cycle_note', data)
        self.assertIn('btc_cycle_metrics', cycle)
        self.assertNotIn('etf_weekly_history_data', cycle)
        self.assertNotIn('macro_news', cycle)

    def test_digest_carries_only_what_sections_published(self):
        """Pass 2 must not see the raw payload."""
        from agents import build_digest

        pass_one = {'etf_note': {'section': 'etf_note',
                                 'facts': ['btc_etf_weekly_net=+865.3M'],
                                 'direction': 'bullish', 'strength': 0.7,
                                 'key_metric': 'btc_etf_weekly_net'}}
        data = {'fear_and_greed': {'value': 31},
                'crypto_prices': [{'Symbol': 'BTC', 'Current Price USD': 65210.0,
                                   '7d %': 1.2}],
                'options_data': {'put_call_ratio': 0.575},
                'correlation_matrix': {'BTC': {'NDX': 0.62}}}
        digest = build_digest(pass_one, data)

        flat = json.dumps(digest)
        self.assertIn('btc_etf_weekly_net', flat)
        self.assertIn('65210', flat)
        # Raw payload keys no section surfaced must not leak through.
        self.assertNotIn('put_call_ratio', flat)
        self.assertNotIn('correlation_matrix', flat)

    def test_assembly_gives_each_field_one_author(self):
        from agents import assemble_weekly

        pass_one = {'etf_note': {'section': 'etf_note',
                                 'key_metric': 'btc_etf_weekly_net',
                                 'tr': {'what': 'Akış +865M.',
                                        'so_what': 'Yönlü talep sürüyor.'},
                                 'en': {'what': 'Flow +865M.',
                                        'so_what': 'Directional demand persists.'}}}
        pass_two = {'tr': {'overview': 'Hafta özeti.', 'regime_line': 'Risk iştahı zayıf.',
                           'themes': [{'title': 'LİKİDİTE', 'body': 'Daraldı.',
                                       'metric_key': 'btc_etf_weekly_net'}],
                           'conflicting_signals': [], 'scenarios': {}},
                    'en': {'overview': 'Week summary.', 'regime_line': 'Risk appetite weak.',
                           'themes': [], 'conflicting_signals': [], 'scenarios': {}}}
        out = assemble_weekly(pass_one, pass_two)

        # Notes come from pass 1, the summary from pass 2 — never merged.
        self.assertEqual(out['tr']['notes']['etf_note']['so_what'],
                         'Yönlü talep sürüyor.')
        self.assertEqual(out['tr']['overview'], 'Hafta özeti.')
        # `body` is renamed to what the renderer reads.
        self.assertEqual(out['tr']['themes'][0]['description'], 'Daraldı.')

    # ── the two build gates ──────────────────────────────────────────

    def test_exec_summary_number_outside_the_digest_fails_the_build(self):
        digest = {'sections': {'etf_note': {'facts': ['btc_etf_weekly_net=+865.3']}},
                  'headline': {'fear_greed': 31}}
        data = {'tr': {'overview': 'ETF akışı +865.3M, korku endeksi 31.',
                       'themes': []},
                'en': {'overview': 'Piyasa değeri 2.27 trilyon dolara ulaştı.',
                       'themes': []}}
        unverified = validators.verify_exec_summary_numbers(data, digest)

        self.assertTrue(unverified)
        self.assertEqual(unverified[0]['lang'], 'en')
        self.assertIn('2.27', [u['value'] for u in unverified])

    def test_exec_summary_passes_when_every_figure_is_sourced(self):
        digest = {'sections': {'etf_note': {'facts': ['btc_etf_weekly_net=+865.3']}},
                  'headline': {'fear_greed': 31}}
        data = {'tr': {'overview': 'ETF akışı +865.3M, korku endeksi 31.',
                       'themes': []}, 'en': {}}
        self.assertEqual(validators.verify_exec_summary_numbers(data, digest), [])

    def test_theme_citing_an_unknown_metric_fails_the_build(self):
        pass_one = {'etf_note': {'key_metric': 'btc_etf_weekly_net'}}
        data = {'tr': {'themes': [
                    {'title': 'A', 'description': 'x', 'metric_key': 'btc_etf_weekly_net'},
                    {'title': 'B', 'description': 'y', 'metric_key': 'uydurma_metrik'},
                    {'title': 'C', 'description': 'z', 'metric_key': None}]},
                'en': {'themes': []}}
        bad = validators.verify_theme_metric_keys(data, pass_one)

        issues = ' '.join(b['issue'] for b in bad)
        self.assertIn('uydurma_metrik', issues)
        self.assertIn('metric_key yok', issues)
        # EN has no themes at all, which is also a failure.
        self.assertIn('0 tema', issues)

    def test_three_valid_themes_pass(self):
        pass_one = {'a': {'key_metric': 'm1'}, 'b': {'key_metric': 'm2'}}
        themes = [{'title': 'A', 'description': 'x', 'metric_key': 'm1'},
                  {'title': 'B', 'description': 'y', 'metric_key': 'm2'},
                  {'title': 'C', 'description': 'z', 'metric_key': 'm1'}]
        data = {'tr': {'themes': themes}, 'en': {'themes': themes}}
        self.assertEqual(validators.verify_theme_metric_keys(data, pass_one), [])


class CompressionAndLayoutTests(unittest.TestCase):
    """Phases 4 and 5: less page, in the order a reader needs it."""

    # ── 4: compression ───────────────────────────────────────────────

    def test_correlation_is_one_row_not_a_mirrored_grid(self):
        from render.svg import generate_correlation_matrix_svg
        corr = {'base': 'BTC', 'peers': {
            'NDX': {'30d': 0.62, '90d': 0.41},
            'GOLD': {'30d': -0.12, '90d': 0.05},
            'DXY': {'30d': -0.58, '90d': None},
            'US10Y': {'30d': 0.09, '90d': 0.22}}}
        html = generate_correlation_matrix_svg(corr)

        self.assertEqual(html.count('BTC &times;'), 4)
        self.assertIn('30G', html)
        self.assertIn('90G', html)
        # A window we could not compute says so rather than printing 0.00.
        self.assertIn('N/A', html)

    def test_watchlist_is_six_rows_chosen_by_what_moved(self):
        from render.weekly import _weekly_watchlist
        rows = [{'Symbol': s, '7d %': p} for s, p in
                [('BTC', 1.0), ('ETH', 0.5), ('SOL', 2.0), ('XRP', -1.0),
                 ('TRX', 0.2), ('DOGE', 14.0), ('HYPE', -9.0),
                 ('LINK', 1.1), ('AVAX', 0.9), ('SUI', 3.0)]]
        picked = [r['Symbol'] for r in _weekly_watchlist(rows)]

        self.assertEqual(len(picked), 6)
        for core in ('BTC', 'ETH', 'SOL', 'XRP'):
            self.assertIn(core, picked)
        self.assertIn('DOGE', picked)   # best
        self.assertIn('HYPE', picked)   # worst

    def test_commodities_dropped_the_three_that_transmitted_nothing(self):
        import inspect
        from data_fetcher import get_commodities
        src = inspect.getsource(get_commodities)
        for kept in ('GC=F', 'SI=F', 'HG=F', 'BZ=F'):
            self.assertIn(kept, src)
        for dropped in ('CC=F', 'KC=F', 'NG=F'):
            self.assertNotIn(dropped, src)

    def test_hype_radar_is_out_of_the_pdf(self):
        data = DataIntegrityTests._weekly()
        data['trending_coins'] = [{'symbol': 'TUT', 'name': 'Tutorial',
                                   'rank': 400, 'chg_24h': 93.43}]
        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertNotIn('TUT', body)
        self.assertNotIn(STR['section_hype_radar']['tr'], body)

    def test_winners_and_rotation_are_one_section(self):
        data = DataIntegrityTests._weekly()
        data['crypto_sector_rotation_data'] = {'Layer 1 Protocols': 2.1}
        data['winners'] = [{'Symbol': 'SOL', 'Change %': 9.0}]
        data['losers'] = [{'Symbol': 'HYPE', 'Change %': -7.0}]
        data['tr']['notes']['rotation_note'] = {'what': 'L1 sepeti önde.',
                                                'so_what': 'Risk iştahı kripto içinde yukarı kayıyor.'}
        body = render_weekly(data, lang='tr').split('</head>')[-1]

        self.assertIn(STR['section_rotation_merged']['tr'], body)
        self.assertNotIn(STR['section_winners_losers']['tr'], body)

    def test_turkey_desk_stays(self):
        """Kept by explicit decision — the alternative was deleting it."""
        data = DataIntegrityTests._weekly()
        data['bist_try'] = {'bist100': 13779.0, 'bist100_chg': 1.2,
                            'usd_try': 47.6937, 'try_chg': 0.3}
        body = render_weekly(data, lang='tr').split('</head>')[-1]
        self.assertIn(STR['section_turkey_desk']['tr'], body)
        self.assertIn('13,779', body)

    # ── 5: layout ────────────────────────────────────────────────────

    def test_pages_appear_in_the_briefed_order(self):
        data = DataIntegrityTests._weekly()
        data['bist_try'] = {'bist100': 13779.0, 'bist100_chg': 1.2,
                            'usd_try': 47.69, 'try_chg': 0.3}
        data['crypto_prices'] = [{'Symbol': 'BTC', 'Current Price USD': 65210.0,
                                  '7d %': 1.2, 'Market Cap': 1.3e12}]
        data['btc_cycle_metrics'] = {'spot': 65210.0, 'wma200': 48000.0,
                                     'mayer_multiple': 1.2, 'ath': 126000.0,
                                     'drawdown': -48.2,
                                     'distance_to_200wma': 35.8,
                                     'monthly_heatmap': None}
        data['tr']['notes']['cycle_note'] = {'what': 'x', 'so_what': 'y'}
        body = render_weekly(data, lang='tr').split('</head>')[-1]

        order = ['section_macro_regime', 'section_cross_asset',
                 'section_crypto_market', 'section_btc_regime']
        positions = [body.find(STR[key]['tr']) for key in order]
        for key, pos in zip(order, positions):
            self.assertNotEqual(pos, -1, f'{key} missing')
        self.assertEqual(positions, sorted(positions),
                         f'page order is wrong: {list(zip(order, positions))}')

    def test_empty_group_prints_no_heading(self):
        """A page title with nothing under it is worse than no page title."""
        from render.weekly import _group
        self.assertEqual(_group('CROSS-ASSET', '', '   ', None), '')
        self.assertIn('CROSS-ASSET', _group('CROSS-ASSET', '<div>x</div>'))

    def test_news_renders_as_transmission(self):
        data = DataIntegrityTests._weekly()
        data['tr']['news_transmission'] = [{
            'title': 'Hormuz / İran',
            'chain': 'Petrol arzı → enflasyon → faiz → risk varlıkları',
            'this_week': 'Brent 83,55$ (7g -%7,29) — piyasa manşet riskini fiyatlıyor.'}]
        data['tr']['notes']['news_note'] = {'what': 'Jeopolitik risk primi geriledi.',
                                            'so_what': 'Enerji hedge ihtiyacı azaldı.'}
        body = render_weekly(data, lang='tr').split('</head>')[-1]

        self.assertIn('Hormuz', body)
        self.assertIn('Zincir', body)
        self.assertIn('→', body)
        self.assertIn('Bu hafta', body)

    def test_story_without_a_chain_is_dropped(self):
        data = DataIntegrityTests._weekly()
        data['tr']['news_transmission'] = [
            {'title': 'İyi haber', 'chain': 'A → B', 'this_week': 'x'},
            {'title': 'Zincirsiz haber', 'chain': '', 'this_week': 'y'}]
        data['tr']['notes']['news_note'] = {'what': 'a', 'so_what': 'b'}
        body = render_weekly(data, lang='tr').split('</head>')[-1]

        self.assertIn('İyi haber', body)
        self.assertNotIn('Zincirsiz haber', body)


if __name__ == '__main__':
    unittest.main()
