import os
import sys
from data_fetcher import (
    get_crypto_prices, get_macro_indicators, get_fear_and_greed_index,
    get_macro_news,
    get_coinbase_premium_index, get_funding_rates, get_crypto_market_overview,
    get_magnificent_7, get_commodities, get_economic_calendar, get_options_market_data,
    get_global_liquidity_index, get_macro_scoreboard, get_sp500_sectors,
    get_crypto_futures_basis
)
from agents import ContentEditorAgent, ExperienceDesignerAgent
from html_generator import generate_newsletter_html
from ai_report_generator import generate_ai_report
from design_preview_generator import generate_design_preview
from email_sender import send_newsletter_email


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
            # Wait a bit for fonts to load
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
        print("     PDF için: pip install playwright && python -m playwright install chromium")
        return False
    except Exception as e:
        print(f"  ⚠️  PDF dönüştürme hatası: {e}")
        return False


def generate_daily_newsletter():
    print("Veriler çekiliyor...")
    watchlist = [
        'BTC', 'ETH', 'XRP', 'SOL', 'TRX', 'DOGE', 'HYPE', 'LINK',
        'AVAX', 'SUI', 'TON', 'UNI', 'AAVE', 'PEPE', 'RENDER', 'JUP'
    ]

    # ── Fetch all data ──
    print("  → Crypto fiyatları...")
    crypto_prices = get_crypto_prices(watchlist)
    btc_price = 0
    for c in crypto_prices:
        if c['Symbol'] == 'BTC':
            btc_price = c.get('Current Price USD', 0)
            break

    print("  → Crypto piyasa özeti...")
    crypto_market_overview = get_crypto_market_overview()

    print("  → Makro göstergeler...")
    macro_indicators = get_macro_indicators()

    print("  → Magnificent 7...")
    magnificent_7 = get_magnificent_7()

    print("  → Emtialar...")
    commodities = get_commodities()

    print("  → Fear & Greed Index...")
    fear_and_greed = get_fear_and_greed_index()

    print("  → Funding rates...")
    funding_rates = get_funding_rates()

    print("  → Ekonomik takvim...")
    economic_calendar = get_economic_calendar()

    print("  → Coinbase premium...")
    coinbase_premium = get_coinbase_premium_index()

    print("  → Macro haberler...")
    macro_news = get_macro_news()

    print("  → Opsiyon Piyasaları...")
    options_data = get_options_market_data()

    print("  → Global Liquidity...")
    global_liquidity = get_global_liquidity_index()
    
    print("  → Makro Scoreboard...")
    macro_scoreboard = get_macro_scoreboard()

    print("  → S&P 500 Sektörleri...")
    sp500_sectors = get_sp500_sectors()

    print("  → Crypto Futures Basis...")
    crypto_futures_basis = get_crypto_futures_basis()

    data = {
        'crypto_prices': crypto_prices,
        'crypto_market_overview': crypto_market_overview,
        'macro_indicators': macro_indicators,
        'magnificent_7': magnificent_7,
        'commodities': commodities,
        'fear_and_greed': fear_and_greed,
        'funding_rates': funding_rates,
        'economic_calendar': economic_calendar,
        'coinbase_premium': coinbase_premium,
        'macro_news': macro_news,
        'options_data': options_data,
        'global_liquidity': global_liquidity,
        'macro_scoreboard': macro_scoreboard,
        'sp500_sectors': sp500_sectors,
        'crypto_futures_basis': crypto_futures_basis,
    }

    # ── AI Agent Analysis ──
    skip_agents = "--no-agents" in sys.argv
    if skip_agents:
        print("\n⏭️  AI Agent'lar atlanıyor (--no-agents)")
        data['ai_summary'] = None
        data['news_commentaries'] = None
        data['design_improvement_report'] = None
        data['futures_note'] = None
        data['options_note'] = None
        data['indicators_note'] = None
    else:
        print("\n🤖 AI Agent'lar çalıştırılıyor...")

        print("  → Finansal İçerik Editörü...")
        editor_result = ContentEditorAgent().analyze(data)
        data['ai_summary'] = editor_result.get('genel_degerlendirme')
        data['korelasyon_notu'] = editor_result.get('korelasyon_notu')
        data['news_commentaries'] = editor_result.get('news_commentaries')
        data['content_suggestions'] = editor_result.get('content_suggestions')
        data['futures_note'] = editor_result.get('futures_note')
        data['options_note'] = editor_result.get('options_note')
        data['indicators_note'] = editor_result.get('indicators_note')

        # Kota aşımını önlemek için kısa bekleme
        import time
        time.sleep(5)

        print("  → Bülten Deneyim Tasarımcısı...")
        design_report = ExperienceDesignerAgent().analyze(data)
        data['design_improvement_report'] = design_report

    # ── Generate HTML ──
    print("\nHTML bülten oluşturuluyor...")
    html_filename = 'daily_bulletin.html'
    generate_newsletter_html(data, html_filename)

    # ── Convert to PDF ──
    print("\nPDF'e dönüştürülüyor...")
    pdf_filename = 'daily_bulletin.pdf'
    html_to_pdf(html_filename, pdf_filename)

    # ── Generate private AI report ──
    print("\nAI raporları oluşturuluyor (sadece editör için)...")
    ai_report_file = generate_ai_report(data)

    # ── Generate design preview ──
    design_report = data.get('design_improvement_report', {})
    design_preview_file = None
    if design_report and design_report.get('success') and design_report.get('report'):
        design_preview_file = generate_design_preview(design_report['report'])

    print(f"\n{'='*50}")
    print(f"  ✅ Bülten hazır!")
    print(f"  HTML: {os.path.abspath(html_filename)}")
    if os.path.exists(pdf_filename):
        print(f"  PDF:  {os.path.abspath(pdf_filename)}")
    if ai_report_file:
        print(f"  📋 AI Rapor: {os.path.abspath(ai_report_file)}")
    if design_preview_file:
        print(f"  🎨 Tasarım Önizleme: {os.path.abspath(design_preview_file)}")
    print(f"{'='*50}")

    # ── Send email (if configured) ──
    should_email = (
        os.environ.get("SEND_EMAIL", "").lower() == "true"
        or os.environ.get("CI", "").lower() == "true"
        or "--send-email" in sys.argv
    )

    if should_email:
        print("\n📧 E-posta gönderimi başlatılıyor...")
        send_newsletter_email(html_filename, pdf_filename, data=data)
    else:
        print("\n💡 E-posta göndermek için:")
        print("   • SEND_EMAIL=true python main.py")
        print("   • python main.py --send-email")
        print("   • GitHub Actions otomatik olarak gönderir")


if __name__ == "__main__":
    print("=" * 50)
    print("  Orkun Biçen — Daily Financial Bulletin")
    print("=" * 50)
    print()
    generate_daily_newsletter()
