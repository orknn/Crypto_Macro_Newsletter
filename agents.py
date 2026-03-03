"""
AI Agents — Financial Content Editor & Bulletin Experience Designer
Uses Anthropic Claude API to generate strategic reports in Turkish.
"""
import os
import json
import time


def _call_with_retry(client, system_prompt, user_prompt, max_retries=3):
    """Call Claude API with automatic retry on rate limit errors."""
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            error_str = str(e)
            if ('429' in error_str or 'rate' in error_str.lower()) and attempt < max_retries - 1:
                wait_time = 15 * (attempt + 1)
                print(f"    ⏳ Rate limit, {wait_time}s bekleniyor... (deneme {attempt + 2}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise


# ═══════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════

CONTENT_EDITOR_SYSTEM_PROMPT = """Sen, küresel piyasa analizi ve dijital yayıncılık konusunda uzmanlaşmış bir Kıdemli Finansal İçerik Editörüsün. Amacın, günlük finans bülteninin değerini en üst düzeye çıkarmak için içerikleri optimize etmektir.

ÖNEMLİ: Bu bülten GERÇEK ve CANLI veri kaynakları kullanır. Mock data KULLANMIYORUZ.
Mevcut gerçek veri kaynakları:
- Crypto fiyatları ve market cap: CoinGecko API (gerçek zamanlı)
- Fear & Greed Index: alternative.me API (gerçek zamanlı)
- Funding Rates: Binance Futures API (gerçek zamanlı)
- VIX, DXY, NASDAQ 100, US 10Y/2Y Yield, SMH ETF: yfinance (gerçek zamanlı)
- Magnificent 7 hisseleri: yfinance (gerçek zamanlı)
- Commodities (Gold, Copper, Cocoa, Coffee, Brent): yfinance (gerçek zamanlı)
- Coinbase Premium: Coinbase vs Binance price diff (gerçek zamanlı)
- Ekonomik Takvim: Forex Factory XML feed (gerçek zamanlı)
- Stablecoin Market Cap: CoinGecko /global (gerçek zamanlı)
- Opsiyon Piyasaları (DVOL, Put/Call, OI): Simüle (gerçek API yok henüz)
- Macro Haberler: Simüle (gerçek API yok henüz)

Yeni veri kaynağı önerirken, ücretsiz ve API anahtarı gerektirmeyen kaynakları tercih et.

Temel Sorumluluklar:

1. Mevcut İçerik Denetimi: Bültendeki bölümleri incele. Okuyucu için değer yaratmayan içerikleri çıkarmayı öner.

2. Piyasa Araştırması: Financial Times, Bloomberg, The Economist, Morning Brew, Sherwood gibi platformların gündemini takip et.

3. Yeni İçerik Teklifleri: Gündemde yükselen ama bültende olmayan konuları öner. Veri kaynağını da belirt (hangi API'den alınabilir?).

4. Onay Mekanizması: "İçerik Strateji Raporu" sun.

Not: Finansal terimler için İngilizce kullan (current asset, cash flow, market cap). Açıklamalar Türkçe olsun."""

EXPERIENCE_DESIGNER_SYSTEM_PROMPT = """Sen, finans sektörüne özel dijital ürün tasarımında 10+ yıl deneyimli, kıdemli bir UX/UI Tasarımcısısın. Görevin, bülteni sektörün en iyi örneklerinden (Finimize, Morning Brew, Sherwood, The Hustle, Robinhood Snacks) biri haline getirmek.

Sen basit font ve renk önerileri yapan bir junior değilsin. Sen derin mimari tasarım kararları veren bir senior'sün.

Analiz Derinliği — Aşağıdaki katmanların HER BİRİNE değin:

1. Background & Atmosfer: Gradient yönleri, grain/noise texture, glassmorphism, frosted glass efektleri, section arka plan geçişleri. Dark mode'da derinlik hissi nasıl artırılır?

2. Layout Grid & Spacing: Bölümler arası padding, card spacing, whitespace dengesi. Bilgi yoğunluğu ile nefes alma alanı arasındaki optimal denge nedir?

3. Information Architecture: Bölüm sıralaması, visual flow (Z-pattern mi F-pattern mi?), ilk 5 saniyede hangi bilgi görülmeli? Kritik verilerin hierarchy'si doğru mu?

4. Veri Görselleştirme: Bar chart, sparkline, heatmap, momentum bar — hangisi hangi veri için optimal? Yeni grafik türleri eklenebilir mi? (mini gauge, radial chart, bullet chart)

5. Micro-interactions & Animation (CSS): Hover effects, transition timing, subtle animations. Print/PDF'de çalışmayacak olanları belirt.

6. Typography System: Font pairing (serif + sans-serif + mono), heading hierarchy, text contrast ratio. WCAG AA uyumluluğu.

7. Component Design: KPI card tasarımı, tablo row tasarımı, news card yapısı. Her bir component nasıl iyileştirilebilir?

8. Color System: Sadece hex kod değil — renk psikolojisi, data-ink ratio, semantic renk kullanımı (kırmızı=düşüş sadece mı yoksa uyarı da mı?).

Her önerinde:
- Tam CSS kodu ver (property: value)
- Hangi HTML elementine uygulanacağını belirt (CSS selector veya açıklama)
- Neden bu değişikliği önerdiğini kısaca açıkla
- Referans bülten varsa belirt (Ör: 'Finimize bunu şu şekilde yapıyor')

Hedef: Bülteni 60 saniyenin altında taranabilir, premium hissiyat veren, market sentiment'in anında anlaşılabileceği bir yapıya kavuşturmak."""


# ═══════════════════════════════════════════
# HELPER: Prepare data summary for LLM
# ═══════════════════════════════════════════

def _prepare_data_summary(data):
    """Create a concise JSON summary of the newsletter data for the LLM."""
    summary = {}

    # Crypto prices (top 5 + notable movers)
    crypto = data.get('crypto_prices', [])
    if crypto:
        summary['crypto_top5'] = [
            {'symbol': c['Symbol'], 'price': c.get('Current Price USD', 0),
             '24h': c.get('24h %', 0), '7d': c.get('7d %', 0)}
            for c in crypto[:5]
        ]
        sorted_by_change = sorted(crypto, key=lambda x: abs(x.get('24h %', 0)), reverse=True)
        summary['biggest_movers'] = [
            {'symbol': c['Symbol'], '24h': c.get('24h %', 0)}
            for c in sorted_by_change[:3]
        ]

    # Market overview
    overview = data.get('crypto_market_overview', {})
    if overview:
        summary['market_overview'] = {
            'total_market_cap_usd': overview.get('total_market_cap', 0),
            'btc_dominance': overview.get('btc_dominance', 0),
            'market_cap_change_24h': overview.get('market_cap_change_24h', 0),
        }

    # Fear & Greed
    fng = data.get('fear_and_greed', {})
    if fng:
        summary['fear_greed'] = fng

    # Macro indicators
    macro = data.get('macro_indicators', {})
    if macro:
        summary['macro'] = {k: v for k, v in macro.items() if not k.endswith('_chg')}
        summary['macro_changes'] = {k: v for k, v in macro.items() if k.endswith('_chg')}

    # Commodities
    commodities = data.get('commodities', [])
    if commodities:
        summary['commodities'] = [
            {'name': c['Name'], 'price': c.get('Price', 0), 'change': c.get('Change %', 0)}
            for c in commodities
        ]

    # Magnificent 7
    mag7 = data.get('magnificent_7', [])
    if mag7:
        summary['magnificent_7'] = [
            {'symbol': s['Symbol'], 'price': s.get('Price', 0), 'change': s.get('Change %', 0)}
            for s in mag7
        ]

    # Funding rates
    funding = data.get('funding_rates', {})
    if funding:
        summary['funding_rates'] = funding

    # Coinbase Premium
    cp = data.get('coinbase_premium', {})
    if cp:
        summary['coinbase_premium'] = cp.get('current_value', 0)

    # News
    news = data.get('macro_news', {})
    if news:
        summary['news_headlines'] = news.get('news', [])

    # Options data
    options = data.get('options_data', {})
    if options:
        summary['options'] = options

    # Economic calendar
    calendar = data.get('economic_calendar', [])
    if calendar:
        summary['economic_calendar'] = [
            {'event': e.get('event', ''), 'country': e.get('country', ''),
             'forecast': e.get('forecast', '—'), 'actual': e.get('actual', '—')}
            for e in calendar[:5]
        ]

    # Current newsletter sections
    summary['current_sections'] = [
        'Genel Değerlendirme',
        'Haftalık Ekonomik Takvim',
        'Günün Öne Çıkan Verileri (KPI)',
        'Coinbase Premium Index',
        'BTC Support & Resistance Analizi',
        'Deribit Opsiyon Piyasaları Analizi',
        'Asset Summary (Commodities, Magnificent 7, Crypto Watchlist)',
        'Öne Çıkan Haberler',
    ]

    return summary


def _prepare_design_context():
    """Provide key design parameters of the current template."""
    return {
        'color_palette': {
            'navy': '#1c2e4a',
            'navy_light': '#253a5e',
            'navy_card': '#1f3350',
            'straw (accent)': '#e8c547',
            'text_bright': '#f0ead8',
            'text_mid': '#a8bcd4',
            'text_dim': '#5e7a9a',
            'green': '#4ecb8d',
            'red': '#e05c6b',
        },
        'fonts': {
            'headings': 'Playfair Display (serif)',
            'body': 'Inter (sans-serif)',
            'monospace_data': 'JetBrains Mono',
        },
        'layout': {
            'max_width': '680px',
            'section_padding': '22px 40px',
            'kpi_font_size': '16px',
            'body_font_size': '13-14px',
            'table_font_size': '12-13px',
        },
        'sections_count': 8,
        'current_design_elements': [
            'Top ticker bar with 6 indicators',
            'Yellow summary card (Genel Değerlendirme)',
            'Economic calendar table',
            '6 KPI cards in horizontal layout',
            'SVG bar chart for Coinbase Premium',
            'BTC Support/Resistance card with border-left highlight',
            'Options market KPI cards',
            'Heatmap tables with momentum bars (Commodities, Mag7, Crypto)',
            'News stories with AI Insight commentary',
            'Dark navy theme with straw/gold accents',
        ]
    }


# ═══════════════════════════════════════════
# AGENT CLASSES
# ═══════════════════════════════════════════

class ContentEditorAgent:
    """
    Finansal İçerik Editörü Agent.
    Bülten içeriğini analiz edip İçerik Strateji Raporu üretir.
    """

    def analyze(self, data):
        """
        Analyze newsletter data and produce a content strategy report.
        Returns a dict with 'report' (str) and 'success' (bool).
        """
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            print("    ⚠️  ANTHROPIC_API_KEY tanımlı değil — İçerik Editörü atlanıyor.")
            return {'success': False, 'report': self._fallback_report()}

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            data_summary = _prepare_data_summary(data)

            user_prompt = f"""Aşağıda bugünkü finans bülteninin tüm verileri ve mevcut bölümleri yer almaktadır.

Bu verileri ve mevcut bölüm yapısını analiz ederek bir "İçerik Strateji Raporu" hazırla.

Rapor formatı şu şekilde olmalı:

## 📋 Çıkarılması Önerilenler
(Her öneriyi numaralandır. Ör: 1. ... 2. ... 3. ...)
(Hangi içerik veya veri bültenden çıkarılmalı ve neden?)

## 📌 Eklenmesi Önerilenler
(Her öneriyi numaralandır. Numaralamaya kaldığın yerden devam et.)
(Gündemde hızla yükselen ama bültende yer almayan konu/haber/analiz önerileri)

## 💡 Gerekçe
(Bu değişikliklerin yatırımcı kararlarına — örneğin current asset yönetimi, risk management, portfolio allocation — katkısı nedir?)

Finansal terimleri İngilizce kullan. Açıklamaları Türkçe yaz. Kısa ve öz ol.

### Bugünkü Bülten Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```"""

            report = _call_with_retry(client, CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt)
            print("    ✅ İçerik Strateji Raporu üretildi.")
            return {'success': True, 'report': report}

        except Exception as e:
            print(f"    ⚠️  İçerik Editörü hatası: {e}")
            return {'success': False, 'report': self._fallback_report()}

    def _fallback_report(self):
        return (
            "## 📋 Çıkarılması Önerilenler\n"
            "AI analizi şu an kullanılamıyor.\n\n"
            "## 📌 Eklenmesi Önerilenler\n"
            "AI analizi şu an kullanılamıyor.\n\n"
            "## 💡 Gerekçe\n"
            "ANTHROPIC_API_KEY yapılandırıldığında bu bölüm otomatik olarak güncellenecektir."
        )


class ExperienceDesignerAgent:
    """
    Bülten Deneyim Tasarımcısı Agent.
    Bültenin UX/UI tasarımını analiz edip Tasarım Geliştirme Önerisi üretir.
    """

    def analyze(self, data):
        """
        Analyze newsletter design and produce a design improvement report.
        Returns a dict with 'report' (str) and 'success' (bool).
        """
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            print("    ⚠️  ANTHROPIC_API_KEY tanımlı değil — Deneyim Tasarımcısı atlanıyor.")
            return {'success': False, 'report': self._fallback_report()}

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            design_context = _prepare_design_context()
            data_summary = _prepare_data_summary(data)

            user_prompt = f"""Aşağıda bültenin mevcut tasarım detayları ve günün verileri yer almaktadır.

Bu bilgileri analiz ederek bir "Tasarım Geliştirme Önerisi" hazırla.

Rapor formatı şu şekilde olmalı:

## 🔍 Mevcut Durum
(Tasarımdaki zayıf halka veya geliştirilmesi gereken alan nedir?)

## 🎨 Önerilen Değişiklikler
(Her öneriyi numaralandır. Ör: 1. ... 2. ... 3. ...)
(Şablonda, renklerde, fontlarda veya veri görselleştirmesinde yapılacak spesifik güncelleme. CSS property, hex code, px değeri gibi somut öneriler ver.)

## 📈 Beklenen Etki
(Bu değişiklikler okuyucunun bültende geçirdiği süreyi veya bilgiye ulaşma hızını nasıl artıracak?)

Hedef: Bülteni 60 saniyenin altında taranabilir ve market sentiment'in anında anlaşılabileceği bir yapıya kavuşturmak.

Kısa ve öz ol. Somut öneriler ver.

### Mevcut Tasarım Parametreleri:
```json
{json.dumps(design_context, ensure_ascii=False, indent=2)}
```

### Günün Veri Özeti:
```json
{json.dumps({
    'total_sections': len(data_summary.get('current_sections', [])),
    'crypto_count': len(data.get('crypto_prices', [])),
    'news_count': len(data.get('macro_news', {}).get('news', [])),
    'calendar_events': len(data.get('economic_calendar', [])),
    'fear_greed': data_summary.get('fear_greed', {}),
}, ensure_ascii=False, indent=2)}
```"""

            report = _call_with_retry(client, EXPERIENCE_DESIGNER_SYSTEM_PROMPT, user_prompt)
            print("    ✅ Tasarım Geliştirme Önerisi üretildi.")
            return {'success': True, 'report': report}

        except Exception as e:
            print(f"    ⚠️  Deneyim Tasarımcısı hatası: {e}")
            return {'success': False, 'report': self._fallback_report()}

    def _fallback_report(self):
        return (
            "## 🔍 Mevcut Durum\n"
            "AI analizi şu an kullanılamıyor.\n\n"
            "## 🎨 Önerilen Değişiklik\n"
            "AI analizi şu an kullanılamıyor.\n\n"
            "## 📈 Beklenen Etki\n"
            "ANTHROPIC_API_KEY yapılandırıldığında bu bölüm otomatik olarak güncellenecektir."
        )
