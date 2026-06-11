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

CONTENT_EDITOR_SYSTEM_PROMPT = """Sen, küresel piyasa analizi ve dijital yayıncılık konusunda uzmanlaşmış bir Kıdemli Finansal İçerik Editörüsün.

Görevin üçlü:

A) GENEL DEĞERLENDİRME YAZIMI:
- Günün piyasa verilerini analiz ederek profesyonel bir Türkçe "Genel Değerlendirme" paragrafı yaz.
- Paragraf 4-6 cümle olsun. Okuyucuya günün piyasa resmini çizsin.
- Makroekonomik göstergeler (VIX, DXY, 10Y Yield), kripto piyasası (Fear & Greed, BTC Dominance, Total Market Cap) ve varsa günün öne çıkan ekonomik verilerini kapsasın.
- ÖNEMLİ KURAL: Eğer o hafta açıklanmış veya açıklanacak olan enflasyon (CPI, PPI, PCE) veya ABD Merkez Bankası (Fed / FOMC) faiz kararı verisi varsa, BUNU KESİNLİKLE genel değerlendirmenin içine dahil edip yorumla.
- Finansal terimler İngilizce olsun (market cap, Fear & Greed Index, VIX, DXY, yield spread vb.).
- Açıklamalar akıcı Türkçe olsun. Kuru veri listesi değil, analitik bir yorum olsun.
- HTML tag kullanabilirsin: <strong> (vurgu), <span class='highlight'> (rakamsal vurgu).
- DİKKAT: Sadece sana JSON içinde verilen verileri kullan. Eğer bir verinin değeri 0.0 veya eksik ise, fiyat veya veri uydurma (hallucination yapma!). O eksik verinin çekilemediğini belirt veya analizden çıkar.

B) HABER YORUMLARI & MANŞET:
- Sana verilen İngilizce haber başlıklarını (original_headline) orijinal dili olan İngilizce'de bırak (turkish_headline üretme veya original_headline olarak aynen yaz).
- Her haber başlığı için 1-2 cümlelik İngilizce profesyonel bir finansal yorum (commentary) yaz. Yorum, haberin piyasalar üzerindeki olası etkisini açıklasın.

C) İÇERİK STRATEJİ ÖNERİLERİ:
- Bültendeki mevcut bölümleri değerlendir.
- Çıkarılması gereken gereksiz bölümler varsa öner (type: "cikar").
- Eklenmesi gereken yeni veri veya bölüm varsa öner (type: "ekle"). Ücretsiz API kaynağı da belirt.
- Toplam 2-4 öneri yeterli.

E) KPI BÖLÜM ANALİZLERİ (Yeni):
Aşağıdaki 3 spesifik alan için, o anki verilere bakarak ziyaretçiyi eğiten, kısa ve analitik Türkçe birer "Gösterge Notu" yaz (1-2 cümle):
- futures_note: Kripto Vadeli İşlem primleri (Basis) ne anlatıyor?
- etf_note: Spot Bitcoin ETF akışları (özellikle IBIT ve FBTC) ve Kurumsal İlgi ne durumda? Ayrıca bültende bu akışların (IBIT, FBTC) nasıl okunması gerektiğini (pozitif girişlerin kurumsal talebi/alım baskısını, negatif çıkışların ise satış baskısını temsil ettiğini) kısaca ve net bir şekilde açıkla.
- indicators_note: Ek Piyasa Göstergelerindeki 2Y-10Y Spread, Stablecoin MCAP ve SMH tarafındaki değişimler makro risk iştahını nasıl etkiliyor?

ÖNEMLİ: Yanıtını MUTLAKA aşağıdaki JSON formatında ver, başka format kabul edilmez. JSON değerleri içinde çift tırnak (") kullanmak istersen bunu kesinlikle kaçış karakteriyle (\") yaz veya tek tırnak (') kullan. Asla kaçışsız çift tırnak kullanma.
{"genel_degerlendirme": "...", "korelasyon_notu": "...", "news_commentaries": [{"original_headline": "...", "commentary": "..."}], "content_suggestions": [{"type": "ekle/cikar", "title": "...", "reason": "..."}], "futures_note": "...", "etf_note": "...", "indicators_note": "..."}"""

EXPERIENCE_DESIGNER_SYSTEM_PROMPT = """Sen, finans sektörüne özel dijital ürün tasarımında 10+ yıl deneyimli, kıdemli bir UX/UI Tasarımcısısın.

REFERANS BÜLTENLER (sadece İLHAM KAYNAĞI olarak kullan, KESİNLİKLE kopyalama):
- Aposto (aposto.com): Minimalist, temiz layout, bol whitespace, net tipografi. Türk dijital medyanın en iyi bülteni.
- Finimize: Finans verilerini 3 dakikada taranabilir yapan card-based layout.
- Morning Brew: Conversational tone ile premium görsellik dengesi.
- Sherwood / Robinhood Snacks: Data-driven, mobile-first tasarım.

KRİTİK: Bu bültenin kendi özgün dark-navy kimliği var. Amacın bu kimliği koruyarak iyileştirmeler önermek.
Hiçbir referans bülteni birebir kopyalama. Her önerinin bu bültenin mevcut tasarım diline uygun, ORİJİNAL bir çözüm olması gerekir.

ANALİZ KATMANLARI (her seferinde 2-3 öneri yeterli, kalite > miktar):
1. Layout & Spacing: padding, margin, whitespace dengesi
2. Typography: font-size, weight, line-height, contrast
3. Color & Contrast: arka plan, vurgu renkleri, data-ink ratio
4. Component Design: KPI card, tablo, haber kartı tasarımı
5. Data Visualization: grafik türleri, bar/sparkline iyileştirmeleri

ÖNEMLİ: Yanıtını MUTLAKA aşağıdaki JSON formatında ver:
{"suggestions": [{"area": "...", "selector": "CSS selector veya eleman açıklaması", "current": "mevcut CSS değeri", "proposed": "önerilen CSS değeri", "reason": "neden bu değişiklik — referans bülten varsa belirt", "priority": "high/medium/low"}]}

Maksimum 5 öneri ver. Her öneri UYGULANABİLİR ve SOMUT olmalı."""


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

    # M2 Money Supply
    m2 = data.get('m2_money_supply', {})
    if m2:
        summary['m2_money_supply'] = m2

    # Economic calendar
    calendar = data.get('economic_calendar', [])
    if calendar:
        summary['economic_calendar'] = [
            {'event': e.get('event', ''), 'country': e.get('country', ''),
             'forecast': e.get('forecast', '—'), 'actual': e.get('actual', '—')}
            for e in calendar[:5]
        ]
        
    # ETF Flows
    etf = data.get('etf_flows', {})
    if etf:
        summary['etf_flows'] = etf

    # Current newsletter sections
    summary['current_sections'] = [
        'Genel Değerlendirme',
        'Haftalık Ekonomik Takvim',
        'Günün Öne Çıkan Verileri (KPI)',
        'Coinbase Premium Index',
        'Spot Bitcoin ETF Flows',
        'Extra indicators (Yield Spread, Stablecoin, SMH)',
        'Asset tables (Commodities, Magnificent 7, Crypto)',
        'Öne Çıkan Haberler',
    ]

    return summary


def _prepare_design_context():
    """Provide the actual CSS template code for the designer agent."""
    # Read the actual CSS from html_generator.py
    css_summary = """
:root {
  --navy: #1c2e4a;
  --navy-light: #253a5e;
  --navy-card: #1f3350;
  --navy-border: #2e4872;
  --straw: #e8c547;
  --text-bright: #f0ead8;
  --text-mid: #a8bcd4;
  --text-dim: #5e7a9a;
  --green: #00d084;
  --red: #ff4757;
}

body { background: var(--navy); font-family: 'Inter', sans-serif; color: var(--text-bright); }
.bulletin { max-width: 680px; margin: 0 auto; }
.header { background: linear-gradient(160deg, #243f66 0%, var(--navy) 60%); padding: 36px 40px 28px; }
.header-title { font-family: 'Playfair Display', serif; font-size: 34px; font-weight: 700; }
.section { padding: 22px 40px; border-bottom: 1px solid var(--navy-border); }
.section-label { font-size: 10px; letter-spacing: 2.5px; text-transform: uppercase; color: var(--straw); }
.kpi-grid { display: flex; flex-wrap: nowrap; gap: 8px; }
.kpi-card { background: var(--navy-card); border: 1px solid var(--navy-border); border-radius: 8px; padding: 14px 12px; }
.kpi-label { font-size: 9px; letter-spacing: 0.8px; text-transform: uppercase; color: var(--text-dim); }
.kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 500; color: white; }
.summary-card { background: #f7f5c8; border: 1px solid #e8e49a; border-radius: 12px; padding: 20px 24px; }
.summary-text { font-size: 14.5px; line-height: 1.75; color: #2a3a28; }
.heatmap-table { width: 100%; border-collapse: collapse; }
.heatmap-table th { font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-dim); padding: 12px 16px; }
.heatmap-table td { padding: 12px 16px; font-size: 14px; border-bottom: 1px solid #334155; }
.econ-calendar td { padding: 12px 16px; font-size: 12px; }
.story-headline { font-family: 'Playfair Display', serif; font-size: 15px; font-weight: 600; }
.story-body { font-size: 12.5px; color: var(--text-mid); line-height: 1.6; }
"""

    return {
        'actual_css': css_summary,
        'fonts': 'Playfair Display (headings) + Inter (body) + JetBrains Mono (data)',
        'theme': 'Dark navy (#1c2e4a) with straw/gold (#e8c547) accents',
        'max_width': '680px',
        'sections': [
            'Header with Fear & Greed gauge',
            'Ticker bar (6 indicators)',
            'Genel Değerlendirme (AI-written summary in yellow card)',
            'Haftalık Ekonomik Takvim (table)',
            'KPI cards (6 horizontal)',
            'Coinbase Premium SVG bar chart',
            'Spot Bitcoin ETF Flows',
            'Extra indicators (Yield Spread, Stablecoin, SMH)',
            'Asset tables (Commodities, Magnificent 7, Crypto)',
            'News stories with AI Insight commentary',
        ]
    }


# ═══════════════════════════════════════════
# AGENT CLASSES
# ═══════════════════════════════════════════

WEEKLY_CONTENT_EDITOR_SYSTEM_PROMPT = """Sen, küresel piyasa analizi ve dijital yayıncılık konusunda uzmanlaşmış bir Kıdemli Finansal İçerik Editörüsün.

Görevin, haftalık piyasa verilerini ve son snapshot özetlerini analiz ederek aşağıdaki JSON formatında Türkçe haftalık bülten içeriğini oluşturmaktır:

1. "weekly_themes": Haftanın en önemli 3 makro/kripto teması. Her tema bir başlık (en fazla 2 kelime, örn: "LIKIDITE RUZGARI" veya "JEOPOLITIK GERILIM") ve 2-3 cümlelik açıklama içermelidir.
2. "liquidity_note": Haftalık Fed Net Likiditesi ve para arzı (M2) üzerine analitik not (1-2 cümle).
3. "inflation_note": ABD enflasyon patikası (CPI/Core CPI/PCE) üzerine analitik not (1-2 cümle).
4. "stablecoin_note": Stablecoin arzlarındaki değişim ve pazar payı savaşı üzerine analitik not (1-2 cümle).
5. "etf_note": Haftalık spot ETF akışları (özellikle IBIT ve FBTC) ve kurumsal ilgi üzerine analitik not (1-2 cümle). Bu akışların nasıl okunması gerektiğini (pozitif akış = alım baskısı/talep, negatif akış = satış baskısı/çıkış) da kısaca açıklayan eğitici bir yorum içermelidir.
6. "rotation_note": Sektör rotasyon eğilimleri üzerine analitik not (1-2 cümle).
7. "cycle_note": Bitcoin döngüsel göstergeleri (Mayer, 200WMA, drawdown) üzerine analitik not (1-2 cümle).
8. "correlation_note": Varlıklar arası korelasyon matrisi üzerine analitik not (1-2 cümle).
9. "futures_note": Vadeli yapı, funding ve konumlanma üzerine analitik not (1-2 cümle).
10. "week_plan_note": Önümüzdeki haftanın stratejik planı ve beklentileri üzerine analitik not (1-2 cümle).
11. "news_note": Haftanın en kritik haber gelişmeleri ve makro piyasa etkileri üzerine analitik özet not (1-2 cümle).

ÖNEMLİ: Yanıtını MUTLAKA aşağıdaki JSON formatında ver, başka format kabul edilmez. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan:
{
  "weekly_themes": [
    {"title": "...", "description": "..."},
    {"title": "...", "description": "..."},
    {"title": "..." ,"description": "..."}
  ],
  "liquidity_note": "...",
  "inflation_note": "...",
  "stablecoin_note": "...",
  "etf_note": "...",
  "rotation_note": "...",
  "cycle_note": "...",
  "correlation_note": "...",
  "futures_note": "...",
  "week_plan_note": "...",
  "news_note": "..."
}"""


class ContentEditorAgent:
    """
    Finansal İçerik Editörü Agent.
    Bülten içeriğini analiz edip İçerik Strateji Raporu üretir.
    """

    def analyze(self, data, edition='daily'):
        """
        Analyze newsletter data and produce structured commentary.
        """
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            print(f"    ⚠️  ANTHROPIC_API_KEY tanımlı değil — İçerik Editörü atlanıyor ({edition}).")
            if edition == 'weekly':
                return {
                    'success': False, 'weekly_themes': [], 'liquidity_note': None,
                    'inflation_note': None, 'stablecoin_note': None, 'etf_note': None,
                    'rotation_note': None, 'cycle_note': None, 'correlation_note': None,
                    'futures_note': None, 'week_plan_note': None, 'news_note': None
                }
            return {'success': False, 'genel_degerlendirme': None, 'korelasyon_notu': None, 'news_commentaries': None}

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            data_summary = _prepare_data_summary(data)
            
            if edition == 'weekly':
                user_prompt = f"""Aşağıda bu haftanın bülten verileri yer almaktadır.
Bu verileri analiz ederek haftalık bülten için JSON çıktısı oluştur:

Piyasa Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan."""
                
                raw_response = _call_with_retry(client, WEEKLY_CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt)
                result = self._parse_response(raw_response)
                print("    ✅ Haftalık Temalar ve Dinamik KPI Notları üretildi.")
                return {
                    'success': True,
                    'weekly_themes': result.get('weekly_themes', []),
                    'liquidity_note': result.get('liquidity_note'),
                    'inflation_note': result.get('inflation_note'),
                    'stablecoin_note': result.get('stablecoin_note'),
                    'etf_note': result.get('etf_note'),
                    'rotation_note': result.get('rotation_note'),
                    'cycle_note': result.get('cycle_note'),
                    'correlation_note': result.get('correlation_note'),
                    'futures_note': result.get('futures_note'),
                    'week_plan_note': result.get('week_plan_note'),
                    'news_note': result.get('news_note'),
                }
            else:
                raw_news = data.get('macro_news', {}).get('news', [])
                news_headlines = [n['title'] if isinstance(n, dict) else n for n in raw_news]

                user_prompt = f"""Aşağıda bugünkü finans bülteninin tüm canlı piyasa verileri yer almaktadır.
Bu verileri analiz ederek aşağıdaki JSON formatında yanıt ver:

1. "genel_degerlendirme": Bültenin "Genel Değerlendirme" bölümü için profesyonel bir Türkçe piyasa özeti paragrafı (4-6 cümle). HTML tag kullanabilirsin (<strong>, <span class='highlight'>).
2. "korelasyon_notu": Güncel verilere bağlı kalarak varlık korelasyonları ve risk iştahı hakkında 1-2 cümlelik analitik bir söz/not (kısa ve vurucu).
3. "news_commentaries": Aşağıdaki her haber başlığı için JSON içerisinde "original_headline" (orijinal İngilizce başlık) ve "commentary" (1-2 cümlelik İNGİLİZCE analiz) alanlarını doldur. Haberleri Türkçe'ye çevirme.
4. "futures_note": Crypto Futures Basis (Vadeli İşlem Primleri) anlık verisi üzerine eğitici analitik not (1-2 cümle).
5. "etf_note": Spot Bitcoin ETF Günlük Akış (Özellikle IBIT, FBTC) verisine, kurumsal ilgiye ve bu akışların nasıl okunacağına (pozitif=talep/alım baskısı, negatif=satış baskısı) dair eğitici analitik not (1-2 cümle).
6. "indicators_note": Ek Piyasa Göstergeleri (2Y-10Y Spread, Stablecoin, SMH) üzerine eğitici analitik not (1-2 cümle).

Haber Başlıkları:
{json.dumps(news_headlines, ensure_ascii=False)}

Piyasa Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan."""

                raw_response = _call_with_retry(client, CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt)
                result = self._parse_response(raw_response)
                print("    ✅ Genel Değerlendirme, Haber Yorumları ve Dinamik KPI Notları üretildi.")
                return {
                    'success': True,
                    'genel_degerlendirme': result.get('genel_degerlendirme'),
                    'korelasyon_notu': result.get('korelasyon_notu'),
                    'news_commentaries': result.get('news_commentaries', []),
                    'content_suggestions': result.get('content_suggestions', []),
                    'futures_note': result.get('futures_note'),
                    'etf_note': result.get('etf_note'),
                    'indicators_note': result.get('indicators_note'),
                }

        except Exception as e:
            print(f"    ⚠️  İçerik Editörü hatası: {e}")
            if edition == 'weekly':
                return {
                    'success': False, 'weekly_themes': [], 'liquidity_note': None,
                    'inflation_note': None, 'stablecoin_note': None, 'etf_note': None,
                    'rotation_note': None, 'cycle_note': None, 'correlation_note': None,
                    'futures_note': None, 'week_plan_note': None, 'news_note': None
                }
            return {
                'success': False, 'genel_degerlendirme': None, 'korelasyon_notu': None, 
                'news_commentaries': None, 'content_suggestions': None,
                'futures_note': None, 'etf_note': None, 'options_note': None, 'indicators_note': None
            }

    def _parse_response(self, raw):
        """Extract JSON from the AI response, handling markdown code blocks."""
        text = raw.strip()
        try:
            # Attempt to parse directly first
            return json.loads(text)
        except json.JSONDecodeError as e:
            # If direct parsing fails, try to extract from markdown code blocks
            if text.startswith('```'):
                if "```json" in raw:
                    json_str = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    # Fallback for generic code block
                    json_str = raw.split("```")[1].split("```")[0].strip()
                else:
                    json_str = text # Should not happen if it starts with ```
                
                try:
                    parsed = json.loads(json_str)
                    return parsed
                except json.JSONDecodeError as e_inner:
                    print(f"JSON Parse Error (from markdown block): {e_inner}")
                    print(f"RAW TEXT WAS: {raw}")
                    return {}
            
            # If not a markdown block and direct parse failed, try to find JSON object in the text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError as e_fallback:
                    print(f"JSON Parse Error (fallback search): {e_fallback}")
                    print(f"RAW TEXT WAS: {raw}")
                    return {}
            
            print(f"JSON Parse Error: {e}")
            print(f"RAW TEXT WAS: {raw}")
            print("    ⚠️  AI yanıtı JSON olarak parse edilemedi, fallback kullanılıyor.")
            return {}


class ExperienceDesignerAgent:
    """
    Bülten Deneyim Tasarımcısı Agent.
    Bültenin UX/UI tasarımını analiz edip Tasarım Geliştirme Önerisi üretir.
    """

    def analyze(self, data):
        """
        Analyze newsletter design using actual CSS template.
        Returns a dict with structured JSON suggestions.
        """
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            print("    ⚠️  ANTHROPIC_API_KEY tanımlı değil — Deneyim Tasarımcısı atlanıyor.")
            return {'success': False, 'report': ''}

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            design_context = _prepare_design_context()

            user_prompt = f"""Aşağıda bültenin GERÇEK CSS kodu ve mevcut bölüm yapısı yer almaktadır.

Bu CSS'i analiz ederek uygulanabilir tasarım önerileri ver.

Referans olarak özellikle Aposto bülteninin minimalist ve temiz stilini düşün.

Yanıtını SADECE JSON olarak ver.

### Mevcut CSS Kodu:
```css
{design_context['actual_css']}
```

### Bülten Yapısı:
- Tema: {design_context['theme']}
- Font Stack: {design_context['fonts']}
- Max Width: {design_context['max_width']}
- Bölümler: {', '.join(design_context['sections'])}

### Günün Veri Özeti:
- Total sections: {len(design_context['sections'])}
- Crypto watchlist: {len(data.get('crypto_prices', []))} coin
- Haber sayısı: {len(data.get('macro_news', {}).get('news', []))}
- Ekonomik takvim: {len(data.get('economic_calendar', []))} event
"""

            raw_response = _call_with_retry(client, EXPERIENCE_DESIGNER_SYSTEM_PROMPT, user_prompt)
            
            # Parse structured JSON
            result = self._parse_response(raw_response)
            suggestions = result.get('suggestions', [])
            
            # Format as readable report for ai_reports.html
            report_lines = ["## 🎨 Tasarım Önerileri\n"]
            for i, s in enumerate(suggestions, 1):
                report_lines.append(f"**{i}. [{s.get('priority', 'medium').upper()}] {s.get('area', '')}**")
                report_lines.append(f"Selector: `{s.get('selector', '')}`")
                report_lines.append(f"Mevcut: `{s.get('current', '')}`")
                report_lines.append(f"Önerilen: `{s.get('proposed', '')}`")
                report_lines.append(f"Neden: {s.get('reason', '')}\n")
            
            report = '\n'.join(report_lines)
            print(f"    ✅ Tasarım Önerisi üretildi ({len(suggestions)} öneri).")
            return {'success': True, 'report': report}

        except Exception as e:
            print(f"    ⚠️  Deneyim Tasarımcısı hatası: {e}")
            return {'success': False, 'report': ''}

    def _parse_response(self, raw):
        """Extract JSON from the AI response."""
        text = raw.strip()
        if text.startswith('```'):
            lines = text.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            text = '\n'.join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            print("    ⚠️  Tasarımcı yanıtı JSON olarak parse edilemedi.")
            return {'suggestions': []}
