import os
import sys
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from data_fetcher import (
    preload_yfinance_data, get_crypto_prices, get_macro_indicators, 
    get_fear_and_greed_index, get_macro_news, get_coinbase_premium_index,
    get_funding_rates, get_crypto_market_overview, get_magnificent_7, 
    get_commodities, get_economic_calendar, get_global_liquidity_index, 
    get_macro_scoreboard, get_sp500_sectors, get_crypto_futures_basis, 
    get_etf_flows, get_bist_data, get_m2_money_supply, get_stablecoin_data,
    get_net_liquidity, get_stablecoin_history, get_inflation_path, 
    get_btc_cycle_metrics, get_correlation_matrix, get_etf_flows_history,
    get_yfinance_data
)
from agents import ContentEditorAgent, ExperienceDesignerAgent
from render.daily import render_daily
from render.weekly import render_weekly
from ai_report_generator import generate_ai_report
from email_sender import send_newsletter_email


def push_file_to_website(local_path, repo_path):
    """
    Push a file to nocashflow.net repo.
    Requires GITHUB_TOKEN env variable (set as GitHub Secret).
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("⚠️  GITHUB_TOKEN not set — skipping website push.")
        return False

    if not os.path.isfile(local_path):
        print(f"❌ File not found: {local_path}")
        return False

    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")

    api_url = f"https://api.github.com/repos/orknn/nocashflow.net/contents/{repo_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "nocashflow-bulletin-bot",
    }

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            file_info = json.loads(resp.read().decode("utf-8"))
        sha = file_info.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sha = None  # File doesn't exist yet
        else:
            print(f"❌ GitHub API error getting SHA for {repo_path}: {e.code}")
            return False

    # Commit message with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    payload = {
        "message": f"bulletin: auto-update {repo_path} {today}",
        "content": content_b64,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url, data=data, headers={**headers, "Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req) as resp:
            print(f"  ✅ Website updated: {repo_path}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  ❌ GitHub push failed for {repo_path}: {e.code} — {body}")
        return False


def html_to_pdf(html_path, pdf_path):
    """Convert HTML to PDF using playwright."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            abs_path = os.path.abspath(html_path)
            page.goto(f'file://{abs_path}')
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'}
            )
            browser.close()
        print(f"  ✅ PDF oluşturuldu: {os.path.abspath(pdf_path)}")
        return True
    except ImportError:
        print("  ⚠️  playwright yüklü değil. Yalnızca HTML oluşturuldu.")
        return False
    except Exception as e:
        print(f"  ⚠️  PDF dönüştürme hatası: {e}")
        return False


def validate_snapshot(snapshot_data):
    """Validate daily snapshot JSON against schema."""
    try:
        import jsonschema
        schema_path = 'schemas/snapshot.schema.json'
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            jsonschema.validate(instance=snapshot_data, schema=schema)
            print("  ✅ Snapshot schema validation SUCCESS.")
            return True
        else:
            print("  ⚠️  Schema file schemas/snapshot.schema.json not found — skipping validation.")
            return True
    except ImportError:
        print("  ⚠️  jsonschema not installed — skipping snapshot validation.")
        return True
    except Exception as e:
        print(f"  ❌ Snapshot schema validation FAILED: {e}")
        return False


def get_ytd_comparison_data():
    """Calculate YTD returns starting from Jan 1st of the current year."""
    tickers = {
        'BTC': 'BTC-USD',
        'NDX': '^NDX',
        'GOLD': 'GC=F'
    }
    
    current_year = datetime.now().year
    start_of_year = f"{current_year}-01-01"
    
    res = {}
    for name, ticker in tickers.items():
        try:
            df = get_yfinance_data(ticker, period='2y')
            if not df.empty and 'Close' in df:
                df_ytd = df[df.index >= start_of_year].copy()
                if not df_ytd.empty:
                    first_close = float(df_ytd['Close'].iloc[0].item())
                    df_ytd['ytd_return'] = ((df_ytd['Close'] - first_close) / first_close) * 100
                    res[name] = [
                        {'date': idx.strftime('%Y-%m-%d'), 'value': float(row['ytd_return'])}
                        for idx, row in df_ytd.iterrows()
                    ]
        except Exception as e:
            print(f"      ⚠️  Error calculating YTD for {name}: {e}")
            res[name] = []
    return res


def calculate_crypto_sector_rotation(crypto_prices):
    """Calculate average 7D returns for representative crypto categories."""
    sectors = {
        'Layer 1 Protocols': ['ETH', 'SOL', 'AVAX', 'SUI', 'TON'],
        'DeFi Protocols': ['UNI', 'AAVE', 'LINK'],
        'AI & Decentralized Compute': ['RENDER'],
        'Meme Tokens': ['DOGE', 'PEPE']
    }
    
    price_by_sym = {c['Symbol']: c for c in crypto_prices}
    
    results = {}
    for sector, symbols in sectors.items():
        vals = []
        for sym in symbols:
            if sym in price_by_sym:
                val = price_by_sym[sym].get('7d %')
                if val is not None:
                    vals.append(val)
        if vals:
            results[sector] = sum(vals) / len(vals)
        else:
            results[sector] = 0.0
            
    return results


def get_weekly_etf_flows(etf_daily_history):
    """Aggregate daily ETF flows into weekly sums by Sunday."""
    import pandas as pd
    if not etf_daily_history:
        return []
        
    try:
        df = pd.DataFrame(etf_daily_history)
        df['parsed_date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['parsed_date'])
        df.set_index('parsed_date', inplace=True)
        
        # Resample weekly and sum
        weekly = df.resample('W-SUN').sum()
        
        results = []
        for d, row in weekly.iterrows():
            results.append({
                'date': d.strftime('%Y-%m-%d'),
                'Total_flow_m': float(row['Total_flow_m']),
                'IBIT_flow_m': float(row['IBIT_flow_m']),
                'FBTC_flow_m': float(row['FBTC_flow_m'])
            })
        return results
    except Exception as e:
        print(f"      ⚠️  Error aggregating weekly ETF flows: {e}")
        return []


def get_winners_losers(crypto_prices):
    """Calculate the 5 biggest gainers and losers in the crypto watchlist over 7 days."""
    sorted_assets = sorted(crypto_prices, key=lambda x: x.get('7d %', 0.0), reverse=True)
    
    winners = []
    for c in sorted_assets[:5]:
        winners.append({
            'Symbol': c['Symbol'],
            'Change %': c.get('7d %', 0.0)
        })
        
    losers = []
    for c in reversed(sorted_assets[-5:]):
        losers.append({
            'Symbol': c['Symbol'],
            'Change %': c.get('7d %', 0.0)
        })
        
    return winners, losers


def run_pipeline():
    # Parse CLI Arguments
    edition = 'daily'
    if '--edition' in sys.argv:
        idx = sys.argv.index('--edition')
        if idx + 1 < len(sys.argv):
            edition = sys.argv[idx + 1].lower()
            
    dry_run = '--dry-run' in sys.argv
    skip_agents = '--no-agents' in sys.argv
    send_email_arg = '--send-email' in sys.argv
    
    print(f"Running pipeline in {edition.upper()} edition...")
    if dry_run:
        print("  ⚠️  DRY RUN mode active — no emails, no web push.")
        
    watchlist = [
        'BTC', 'ETH', 'XRP', 'SOL', 'TRX', 'DOGE', 'HYPE', 'LINK',
        'AVAX', 'SUI', 'TON', 'UNI', 'AAVE', 'PEPE', 'RENDER', 'JUP'
    ]

    # Preload yfinance data to cache
    yf_tickers = [
        '^TNX', '^IRX', '^VIX', 'DX-Y.NYB', 'NQ=F', 'SMH', '^MOVE',
        'XLE', 'XLF', 'XLK', 'XLY', 'XLP', 'XLV', 'XLI', 'XLC', 'XLB', 'XLRE', 'XLU',
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA',
        'GC=F', 'SI=F', 'CL=F', 'HG=F', 'XU100.IS', 'USDTRY=X',
        'BTC-USD', '^NDX'
    ]
    preload_period = '2y' if edition == 'weekly' else '35d'
    preload_yfinance_data(yf_tickers, period=preload_period)

    # ── 1. Fetch Shared Core Data ──
    print("  → Crypto prices...")
    crypto_prices = get_crypto_prices(watchlist)
    
    print("  → Crypto market overview...")
    crypto_market_overview = get_crypto_market_overview()
    
    print("  → Macro indicators...")
    macro_indicators = get_macro_indicators()
    
    print("  → Magnificent 7...")
    magnificent_7 = get_magnificent_7()
    
    print("  → Commodities...")
    commodities = get_commodities()
    
    print("  → Fear & Greed Index...")
    fear_and_greed = get_fear_and_greed_index()
    
    print("  → Funding rates and Open Interest...")
    funding_rates, open_interest = get_funding_rates()
    
    print("  → Economic calendar...")
    economic_calendar = get_economic_calendar()
    
    print("  → Coinbase premium...")
    coinbase_premium = get_coinbase_premium_index()
    
    print("  → Macro news...")
    macro_news = get_macro_news()
    
    print("  → Global Liquidity...")
    global_liquidity = get_global_liquidity_index()
    
    print("  → M2 Money Supply...")
    m2_money_supply = get_m2_money_supply()
    
    print("  → Macro Scoreboard...")
    macro_scoreboard = get_macro_scoreboard()
    
    print("  → S&P 500 Sectors...")
    sp500_sectors = get_sp500_sectors()
    
    print("  → Crypto Futures Basis...")
    crypto_futures_basis = get_crypto_futures_basis()
    
    print("  → Spot Bitcoin ETF Flows...")
    etf_flows = get_etf_flows()
    
    print("  → BIST 100 & USD/TRY...")
    bist_try = get_bist_data()
    
    print("  → Stablecoin data...")
    stablecoin_data = get_stablecoin_data()

    # Combine into core data dict
    data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'crypto_prices': crypto_prices,
        'crypto_market_overview': crypto_market_overview,
        'macro_indicators': macro_indicators,
        'magnificent_7': magnificent_7,
        'commodities': commodities,
        'fear_and_greed': fear_and_greed,
        'funding_rates': funding_rates,
        'open_interest': open_interest,
        'economic_calendar': economic_calendar,
        'coinbase_premium': coinbase_premium,
        'macro_news': macro_news,
        'global_liquidity': global_liquidity,
        'm2_money_supply': m2_money_supply,
        'macro_scoreboard': macro_scoreboard,
        'sp500_sectors': sp500_sectors,
        'crypto_futures_basis': crypto_futures_basis,
        'etf_flows': etf_flows,
        'bist_try': bist_try,
        'stablecoin_data': stablecoin_data,
    }

    # ── 2. Fetch Weekly Specific Data (if weekly) ──
    if edition == 'weekly':
        print("  → Net Liquidity historical (3-Year Weekly)...")
        data['net_liquidity_history_data'] = get_net_liquidity()
        
        print("  → Stablecoin history (3-Year Weekly)...")
        data['stablecoin_history_data'] = get_stablecoin_history()
        
        print("  → Inflation path history (5-Year)...")
        data['inflation_history_data'] = get_inflation_path()
        
        print("  → BTC cycle metrics...")
        data['btc_cycle_metrics'] = get_btc_cycle_metrics()
        
        print("  → Correlation matrix (30D daily returns)...")
        data['correlation_matrix'] = get_correlation_matrix()
        
        print("  → YTD asset comparison...")
        data['ytd_comparison_data'] = get_ytd_comparison_data()
        
        print("  → Weekly ETF flows...")
        etf_history = get_etf_flows_history(limit=30)
        data['etf_weekly_history_data'] = get_weekly_etf_flows(etf_history)
        
        print("  → Winners & Losers (7D)...")
        winners, losers = get_winners_losers(crypto_prices)
        data['winners'] = winners
        data['losers'] = losers
        
        print("  → Crypto sector rotation...")
        data['crypto_sector_rotation_data'] = calculate_crypto_sector_rotation(crypto_prices)
    else:
        # For daily ETF bar chart (last 10 days)
        print("  → ETF daily history...")
        data['etf_history_data'] = get_etf_flows_history(limit=10)

    # ── 3. AI Agent Analysis ──
    if skip_agents:
        print("\n⏭️  AI Agent'lar atlanıyor (--no-agents)")
        data['ai_summary'] = None
        data['news_commentaries'] = None
        data['design_improvement_report'] = None
        data['futures_note'] = None
        data['etf_note'] = None
        data['options_note'] = None
        data['indicators_note'] = None
        data['weekly_themes'] = []
    else:
        print("\n🤖 AI Agent'lar çalıştırılıyor...")
        print("  → Finansal İçerik Editörü...")
        editor_result = ContentEditorAgent().analyze(data, edition=edition)
        
        if edition == 'weekly':
            data['weekly_themes'] = editor_result.get('weekly_themes', [])
            data['liquidity_note'] = editor_result.get('liquidity_note')
            data['inflation_note'] = editor_result.get('inflation_note')
            data['stablecoin_note'] = editor_result.get('stablecoin_note')
            data['etf_note'] = editor_result.get('etf_note')
            data['rotation_note'] = editor_result.get('rotation_note')
            data['cycle_note'] = editor_result.get('cycle_note')
            data['correlation_note'] = editor_result.get('correlation_note')
            data['futures_note'] = editor_result.get('futures_note')
            data['week_plan_note'] = editor_result.get('week_plan_note')
            data['news_note'] = editor_result.get('news_note')
        else:
            data['ai_summary'] = editor_result.get('genel_degerlendirme')
            data['korelasyon_notu'] = editor_result.get('korelasyon_notu')
            data['news_commentaries'] = editor_result.get('news_commentaries')
            data['content_suggestions'] = editor_result.get('content_suggestions')
            data['futures_note'] = editor_result.get('futures_note')
            data['etf_note'] = editor_result.get('etf_note')
            data['indicators_note'] = editor_result.get('indicators_note')

        # Short sleep to prevent Anthropic rate limiting
        import time
        time.sleep(2)

        print("  → Bülten Deneyim Tasarımcısı...")
        design_report = ExperienceDesignerAgent().analyze(data)
        data['design_improvement_report'] = design_report

    # ── 4. Save Daily Snapshot and Validate (if daily run) ──
    if edition == 'daily' and not dry_run:
        print("\n💾 Daily Snapshot kaydediliyor...")
        os.makedirs('snapshots', exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        snapshot_path = f"snapshots/{today_str}.json"
        
        # Strip complex/non-serializable types if any
        serializable_data = json.loads(json.dumps(data, default=str))
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ Snapshot saved to {snapshot_path}")
        
        # Validate snapshot schema
        validate_snapshot(serializable_data)

    # ── 5. Generate HTML and PDFs ──
    print(f"\nHTML bülten oluşturuluyor ({edition})...")
    html_filename = 'weekly_bulletin.html' if edition == 'weekly' else 'daily_bulletin.html'
    pdf_filename = 'weekly_bulletin.pdf' if edition == 'weekly' else 'daily_bulletin.pdf'
    
    if edition == 'weekly':
        html_content = render_weekly(data)
    else:
        html_content = render_daily(data)
        
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"  ✅ HTML bülten oluşturuldu: {os.path.abspath(html_filename)}")

    # Convert to PDF
    html_to_pdf(html_filename, pdf_filename)

    # ── 6. Push to website (if not dry run) ──
    if not dry_run:
        print("\nWebsite güncelleniyor...")
        today_str = datetime.now().strftime("%Y-%m-%d")
        week_str = datetime.now().strftime("%Y-W%U")
        
        if edition == 'weekly':
            push_file_to_website(html_filename, f"bulletins/weekly/{week_str}.html")
            push_file_to_website(html_filename, "weekly_bulletin.html")
            if os.path.exists(pdf_filename):
                push_file_to_website(pdf_filename, f"bulletins/weekly/{week_str}.pdf")
                push_file_to_website(pdf_filename, "weekly_bulletin.pdf")
        else:
            push_file_to_website(html_filename, f"bulletins/daily/{today_str}.html")
            push_file_to_website(html_filename, "daily_bulletin.html")
            if os.path.exists(pdf_filename):
                push_file_to_website(pdf_filename, f"bulletins/daily/{today_str}.pdf")
                push_file_to_website(pdf_filename, "daily_bulletin.pdf")

    # ── 7. Generate Private AI Report ──
    print("\nAI raporları oluşturuluyor (sadece editör için)...")
    ai_report_file = generate_ai_report(data, output_filename="ai_reports.html")

    print(f"\n{'='*50}")
    print(f"  ✅ Bülten hazır!")
    print(f"  HTML: {os.path.abspath(html_filename)}")
    if os.path.exists(pdf_filename):
        print(f"  PDF:  {os.path.abspath(pdf_filename)}")
    if ai_report_file:
        print(f"  📋 AI Rapor: {os.path.abspath(ai_report_file)}")
    print(f"{'='*50}")

    # ── 8. Send Email ──
    is_ci = os.environ.get("CI", "").lower() == "true"
    env_send = os.environ.get("SEND_EMAIL", "").lower() == "true"
    should_email = (is_ci or env_send or send_email_arg) and not dry_run
    
    if should_email:
        print("\n📧 E-posta gönderimi başlatılıyor...")
        try:
            send_newsletter_email(html_filename, data=data)
        except Exception as e:
            print(f"  ❌ E-posta gönderimi sırasında beklenmedik hata: {e}")
    else:
        print("\n💡 E-posta gönderimi atlandı.")


if __name__ == "__main__":
    print("=" * 50)
    print("  Orkun Biçen — Financial Bulletin Pipeline")
    print("=" * 50)
    print()
    run_pipeline()
