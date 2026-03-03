import os
import sys
from data_fetcher import (
    get_crypto_prices, get_macro_indicators, get_fear_and_greed_index,
    get_macro_news_mock,
    get_coinbase_premium_index, get_funding_rates, get_crypto_market_overview,
    get_magnificent_7, get_commodities, get_economic_calendar, get_options_market_data
)
from agents import ContentEditorAgent, ExperienceDesignerAgent
from html_generator import generate_newsletter_html
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
    macro_news = get_macro_news_mock()

    print("  → Opsiyon Piyasaları...")
    options_data = get_options_market_data()

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
    }

    # ── AI Agent Analysis ──
    print("\n🤖 AI Agent'lar çalıştırılıyor...")

    print("  → Finansal İçerik Editörü...")
    content_report = ContentEditorAgent().analyze(data)
    data['content_strategy_report'] = content_report

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

    print(f"\n{'='*50}")
    print(f"  ✅ Bülten hazır!")
    print(f"  HTML: {os.path.abspath(html_filename)}")
    if os.path.exists(pdf_filename):
        print(f"  PDF:  {os.path.abspath(pdf_filename)}")
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
