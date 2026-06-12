"""
AI Agents — Financial Content Editor & Bulletin Experience Designer
Uses Anthropic Claude API to generate strategic reports in Turkish.
"""
import os
import json
import time


def _call_with_retry(client, system_prompt, user_prompt, max_tokens=4000, max_retries=3):
    """Call Claude API with automatic retry on rate limit errors and logging."""
    import os as _os
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            result_text = response.content[0].text.strip()
            
            # Log AI call to fetch_report.json
            _log_ai_call(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                prompt_length=len(user_prompt),
                response_length=len(result_text),
                status="success"
            )
            
            return result_text
        except Exception as e:
            error_str = str(e)
            if ('429' in error_str or 'rate' in error_str.lower()) and attempt < max_retries - 1:
                wait_time = 15 * (attempt + 1)
                print(f"    ⏳ Rate limit, {wait_time}s bekleniyor... (deneme {attempt + 2}/{max_retries})")
                time.sleep(wait_time)
            else:
                _log_ai_call(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    prompt_length=len(user_prompt),
                    response_length=0,
                    status=f"error: {error_str[:200]}"
                )
                raise


def _log_ai_call(model, max_tokens, prompt_length, response_length, status):
    """Log AI API call details to fetch_report.json under 'ai_call' key."""
    import os as _os
    report_path = "fetch_report.json"
    report_data = {}
    if _os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
        except Exception:
            pass
    
    if "ai_calls" not in report_data:
        report_data["ai_calls"] = []
    
    from datetime import datetime as _dt
    report_data["ai_calls"].append({
        "model": model,
        "max_tokens": max_tokens,
        "prompt_chars": prompt_length,
        "response_chars": response_length,
        "status": status,
        "timestamp": _dt.now().isoformat()
    })
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ═══════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════

CONTENT_EDITOR_SYSTEM_PROMPT = """Sen, küresel piyasa analizi ve dijital yayıncılık konusunda uzmanlaşmış bir Kıdemli Finansal İçerik Editörüsün.

Görevin, günlük piyasa verilerini ve haber gelişmelerini analiz ederek hem Türkçe (tr) hem de İngilizce (en) dillerinde bülten içeriğini tek bir JSON nesnesinde üretmektir.

Piyasa Durumu Rejimi (regime):
Piyasa verilerine ve risk duyarlılığına dayanarak şu üç rejimden birini seç: "RISK_ON", "NEUTRAL" veya "RISK_OFF".

Her dil (tr ve en) için aşağıdaki alanları doldurmalısın:
1. "regime_line": Seçilen rejim için tek cümlelik, vurucu bir piyasa hükmü (Örn: TR: "Hisse senetlerindeki ralli ve ETF girişleri risk iştahını destekliyor." / EN: "Stock rally and ETF inflows support risk appetite.")
2. "overview" (Genel Değerlendirme):
   - Günün piyasa verilerini analiz eden profesyonel bir özet paragrafı (4-6 cümle).
   - Makroekonomik göstergeleri (VIX, DXY, 10Y Yield), kripto piyasasını (Fear & Greed, BTC Dominance, Total Market Cap) ve varsa günün öne çıkan ekonomik verilerini içermelidir.
   - ÖNEMLİ: Eğer o hafta açıklanmış veya açıklanacak olan enflasyon (CPI, PPI, PCE) veya Fed / FOMC faiz kararı verisi varsa, bunu kesinlikle genel değerlendirme içine dahil edip yorumla.
   - HTML etiketleri kullanabilirsin: <strong> (vurgu), <span class='highlight'> (rakamsal vurgu).
   - Fiyat veya veri uydurma (hallucinate yapma!). Eksik veya 0.0 olan verileri analizden çıkar.
3. "notes" (Gösterge Notları):
   - "futures_note": Kripto vadeli işlem primleri (Basis) ve funding rate'ler hakkında 1-2 cümlelik analitik not.
   - "etf_note": Spot Bitcoin ETF akışları (özellikle IBIT ve FBTC) ve bu akışların nasıl okunması gerektiğine dair (pozitif girişler = alım baskısı, negatif çıkışlar = satış baskısı) 1-2 cümlelik eğitici not.
   - "indicators_note": Ek piyasa göstergelerindeki (2Y-10Y Spread, Stablecoin MCAP, SMH) değişimlerin risk iştahı üzerindeki etkisi hakkında 1-2 cümlelik analitik not.
4. "insights":
   - Sana verilen her haber maddesi için sırasıyla 1-2 cümlelik profesyonel bir finansal yorum (commentary).
   - KRİTİK FİLTRE KURALI: Eğer haber zaten genel bir piyasa yorumu veya listicle ise (örneğin "Cramer'ın izlenmesi gereken listesi", "İşte piyasada bilmeniz gerekenler"), bu haber için insight üretme ve listedeki o elemanı boş string ("") olarak bırak.
   - Her geçerli insight, haberi bültendeki diğer verilerle (funding rates, ETF flows, Coinbase premium, macro yields) ilişkilendirmelidir.
   - insights listesindeki eleman sayısı, giriş haber sayısı ile tam olarak aynı olmalıdır.
   - MUTLAK KURAL: Haber listesi boşsa insights: [] dön. Asla haber UYDURMA. AI'ın haber konusundaki tek görevi, kendisine verilen gerçek haberlere insight yazmaktır.

DİL VE ANLATIM KURALLARI:
- İki dil aynı analizi anlatmalıdır; birebir motamot çeviri olması gerekmez, her dilde doğal ve akıcı finansal terminoloji kullanılmalıdır. Sayılar ve veriler iki dilde de tamamen aynı olmalıdır.

ÇIKTI JSON ŞEMASI (MUTLAKA BU FORMATTA OLMALIDIR):
{
  "regime": "RISK_ON" | "NEUTRAL" | "RISK_OFF",
  "tr": {
    "regime_line": "...",
    "overview": "...",
    "notes": {
      "futures_note": "...",
      "etf_note": "...",
      "indicators_note": "..."
    },
    "insights": ["...", "..."]
  },
  "en": {
    "regime_line": "...",
    "overview": "...",
    "notes": {
      "futures_note": "...",
      "etf_note": "...",
      "indicators_note": "..."
    },
    "insights": ["...", "..."]
  }
}
"""

WEEKLY_CONTENT_EDITOR_SYSTEM_PROMPT = """Sen, küresel piyasa analizi ve stratejik finansal yayıncılık konusunda uzmanlaşmış bir Kıdemli Finansal İçerik Editörüsün.

Görevin, haftalık piyasa verilerini ve haber gelişmelerini analiz ederek hem Türkçe (tr) hem de İngilizce (en) dillerinde bülten içeriğini tek bir JSON nesnesinde üretmektir.

Piyasa Durumu Rejimi (regime):
Piyasa verilerine ve risk duyarlılığına dayanarak şu üç rejimden birini seç: "RISK_ON", "NEUTRAL" veya "RISK_OFF".

Her dil (tr ve en) için aşağıdaki alanları doldurmalısın:
1. "regime_line": Seçilen rejim için tek cümlelik, vurucu bir piyasa hükmü (Örn: TR: "Likidite daralması ve artan tahvil faizleri risk iştahını gölgeliyor." / EN: "Liquidity contraction and rising bond yields shadow risk appetite.")
2. "themes":
   - Haftanın en önemli 3 makro/kripto teması. Her tema bir başlık ("title", en fazla 2-3 kelime, örn: "LIKIDITE RUZGARI" veya "JEOPOLITIK GERILIM") ve 2-3 cümlelik açıklama ("description") içermelidir.
3. "notes":
   - "liquidity_note": Haftalık Fed Net Likiditesi ve para arzı (M2) üzerine analitik not (1-2 cümle).
   - "inflation_note": ABD enflasyon patikası (CPI/PCE) üzerine analitik not (1-2 cümle).
   - "stablecoin_note": Stablecoin arzlarındaki değişim ve pazar payı savaşı üzerine analitik not (1-2 cümle).
   - "etf_note": Haftalık spot ETF akışları (IBIT, FBTC) ve kurumsal ilginin nasıl okunacağına dair (pozitif akış = alım baskısı, negatif akış = satış baskısı) eğitici analitik not (1-2 cümle).
   - "rotation_note": Sektör rotasyon eğilimleri üzerine analitik not (1-2 cümle).
   - "cycle_note": Bitcoin döngüsel göstergeleri (Mayer, 200WMA, drawdown) üzerine analitik not (1-2 cümle).
   - "correlation_note": Varlıklar arası korelasyon matrisi üzerine analitik not (1-2 cümle).
   - "futures_note": Vadeli yapı, funding ve konumlanma üzerine analitik not (1-2 cümle).
   - "week_plan_note": Önümüzdeki haftanın stratejik planı ve beklentileri üzerine analitik not (1-2 cümle).
   - "news_note": Haftanın en kritik haber gelişmelerinin makro etkileri üzerine analitik özet not (1-2 cümle).
4. "insights":
   - Sana verilen her haber maddesi için sırasıyla 1-2 cümlelik profesyonel bir finansal yorum (commentary).
   - KRİTİK FİLTRE KURALI: Eğer haber zaten genel bir piyasa yorumu veya listicle ise (örneğin "Cramer'ın izlenmesi gereken listesi", "İşte piyasada bilmeniz gerekenler"), bu haber için insight üretme ve listedeki o elemanı boş string ("") olarak bırak.
   - Her geçerli insight, haberi bültendeki diğer verilerle ilişkilendirerek analitik bağ kurmalıdır.
   - insights listesindeki eleman sayısı, giriş haber sayısı ile tam olarak aynı olmalıdır.
   - MUTLAK KURAL: Haber listesi boşsa insights: [] dön. Asla haber UYDURMA. AI'ın haber konusundaki tek görevi, kendisine verilen gerçek haberlere insight yazmaktır.

DİL VE ANLATIM KURALLARI:
- İki dil aynı analizi anlatmalıdır; birebir motamot çeviri olması gerekmez, her dilde doğal ve akıcı finansal terminoloji kullanılmalıdır. Sayılar ve veriler iki dilde de tamamen aynı olmalıdır.

ÇIKTI JSON ŞEMASI (MUTLAKA BU FORMATTA OLMALIDIR):
{
  "regime": "RISK_ON" | "NEUTRAL" | "RISK_OFF",
  "tr": {
    "regime_line": "...",
    "themes": [
      {"title": "...", "description": "..."},
      {"title": "...", "description": "..."},
      {"title": "..." ,"description": "..."}
    ],
    "notes": {
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
    },
    "insights": ["...", "..."]
  },
  "en": {
    "regime_line": "...",
    "themes": [
      {"title": "...", "description": "..."},
      {"title": "...", "description": "..."},
      {"title": "...", "description": "..."}
    ],
    "notes": {
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
    },
    "insights": ["...", "..."]
  }
}
"""

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
    """Create a clean copy of the newsletter data for the LLM, excluding AI outputs."""
    exclude_keys = {
        'tr', 'en', 'ai_summary', 'news_commentaries', 
        'design_improvement_report', 'futures_note', 
        'etf_note', 'indicators_note', 'weekly_themes'
    }
    summary = {k: v for k, v in data.items() if k not in exclude_keys}
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

class ContentEditorAgent:
    """
    Finansal İçerik Editörü Agent.
    Bülten içeriğini analiz edip hem Türkçe hem İngilizce bülten çıktısı üretir.
    """

    def analyze(self, data, edition='daily'):
        """
        Analyze newsletter data and produce structured commentary.
        """
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            print(f"    ⚠️  ANTHROPIC_API_KEY tanımlı değil — İçerik Editörü atlanıyor ({edition}).")
            return {
                'success': False,
                'regime': 'NEUTRAL',
                'tr': {},
                'en': {}
            }

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            data_summary = _prepare_data_summary(data)
            
            raw_news = data.get('macro_news', {}).get('news', [])
            news_inputs = [{"title": n.get('title'), "summary": n.get('summary')} for n in raw_news]

            if edition == 'weekly':
                user_prompt = f"""Aşağıda bu haftanın bülten verileri ve haber gelişmeleri yer almaktadır.
Bu verileri analiz ederek haftalık bülten için tek bir dual-language JSON çıktısı oluştur:

Haber Maddeleri:
{json.dumps(news_inputs, ensure_ascii=False, indent=2)}

Piyasa Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan."""
                
                raw_response = _call_with_retry(client, WEEKLY_CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt, max_tokens=4000)
                result = self._parse_response(raw_response)
                print("    ✅ Haftalık Temalar ve Dinamik KPI Notları (TR/EN) üretildi.")
                return {
                    'success': True,
                    'regime': result.get('regime', 'NEUTRAL'),
                    'tr': result.get('tr', {}),
                    'en': result.get('en', {})
                }
            else:
                user_prompt = f"""Aşağıda bugünkü finans bülteninin tüm canlı piyasa verileri ve haber gelişmeleri yer almaktadır.
Bu verileri analiz ederek günlük bülten için tek bir dual-language JSON çıktısı oluştur:

Haber Maddeleri:
{json.dumps(news_inputs, ensure_ascii=False, indent=2)}

Piyasa Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan."""

                raw_response = _call_with_retry(client, CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt, max_tokens=4000)
                result = self._parse_response(raw_response)
                print("    ✅ Genel Değerlendirme, Haber Yorumları ve Dinamik KPI Notları (TR/EN) üretildi.")
                return {
                    'success': True,
                    'regime': result.get('regime', 'NEUTRAL'),
                    'tr': result.get('tr', {}),
                    'en': result.get('en', {})
                }

        except Exception as e:
            print(f"    ⚠️  İçerik Editörü hatası: {e}")
            return {
                'success': False,
                'regime': 'NEUTRAL',
                'tr': {},
                'en': {}
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
                    json_str = raw.split("```")[1].split("```")[0].strip()
                else:
                    json_str = text
                
                try:
                    parsed = json.loads(json_str)
                    return parsed
                except json.JSONDecodeError as e_inner:
                    print(f"JSON Parse Error (from markdown block): {e_inner}")
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
