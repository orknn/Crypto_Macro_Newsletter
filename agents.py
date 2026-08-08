"""
AI Agents — Financial Content Editor & Research Desk
Uses Anthropic Claude API to generate strategic reports in Turkish.
"""
import os
import json
import time

from config.prompt_budget import (PROMPT_EXCLUDED_KEYS, PROMPT_SERIES_CAPS,
                                  PROMPT_SERIES_CAPS_WEEKLY)


def _call_with_retry(client, system_prompt, user_prompt, max_tokens=4000, max_retries=3):
    """Call Claude API with automatic retry on rate limit errors and logging."""
    import os as _os
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            result_text = response.content[0].text.strip()

            if getattr(response, 'stop_reason', None) == 'max_tokens':
                print(f"    ⚠️  AI yanıtı max_tokens={max_tokens} sınırında KESİLDİ — JSON büyük ihtimalle bozuk.")

            # Log AI call to fetch_report.json
            _log_ai_call(
                model="claude-sonnet-4-6",
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
                    model="claude-sonnet-4-6",
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
1b. "overview": Haftanın YÖNETİCİ ÖZETİ (executive summary) — 3-4 cümle. Haftanın en önemli makro gelişmesi, kripto piyasasının genel yönü, ETF/kurumsal akım resmi ve önümüzdeki haftanın en kritik katalizörünü tek paragrafta birleştir. Bültenin tamamını okumayan birinin haftayı anlaması için yeterli olmalı. Önemli sayıları <strong> etiketiyle vurgulayabilirsin.
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
    "overview": "...",
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
    "overview": "...",
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

RESEARCH_DESK_SYSTEM_PROMPT = """Sen, bir finans yayınının Araştırma Masası'nı (Research Desk) yöneten kıdemli bir analistsin.

Görevin, günün gerçek haber akışını ve piyasa verilerini okuyup okuyucunun BUGÜN derinlemesine takip etmesi gereken 3 stratejik konuyu belirlemek ve her konu için nereden birincil kaynak okuyacağını göstermektir.

Bu bölüm haber özeti DEĞİLDİR. Haber "ne oldu"yu anlatır; senin işin "bunu anlamak için neyi kazmak gerekiyor"u göstermektir. Her konu bir araştırma sorusu etrafında kurulmalıdır.

KONU SEÇİM KURALLARI:
- Tam olarak 3 konu seç. Mümkünse farklı beat'lerden (KRİPTO / MAKRO / EMTİA / HİSSE / POLİTİKA / LİKİDİTE) seç, hepsi aynı temadan olmasın.
- Konular SANA VERİLEN gerçek haberlere ve piyasa verilerine dayanmalıdır. Haber akışında veya veride karşılığı olmayan bir olay UYDURMA.
- Rakam uydurma. Sadece sana verilen verilerdeki sayıları kullan; emin değilsen sayı verme.
- Yaklaşan ekonomik takvim olayları (CPI, PCE, FOMC, NFP) güçlü konu adaylarıdır — piyasa fiyatlamasıyla ilişkilendir. Takvimdeki bir olayın tarihi verideki "date" alanından ÖNCEYSE o olay çoktan gerçekleşmiştir; onu "bekleniyor/açıklanacak" diye yazma, açıklanmış veri olarak yorumla.
- "topic" alanı 2-3 cümle olmalı: ne olduğu, neden önemli olduğu ve izlenecek somut sinyal/eşik.

KAYNAK KURALLARI (ÇOK KRİTİK):
- Her konu için 2-3 birincil kaynak ver.
- "url" alanına SADECE sana IZINLI KAYNAK LISTESI'nde verilen URL'lerden birini, harfi harfine kopyalayarak yazabilirsin.
- Listede uygun bir URL yoksa "url": null yaz ve kaynağı sadece adıyla tarif et. ASLA URL uydurma, tahmin etme veya listedeki bir URL'yi değiştirme.
- Kaynak "description" alanı, o kaynakta tam olarak NEYE bakılacağını söylemelidir (örn. "8-K'nın 8.01 kaleminde haftalık alım tutarı ve ortalama maliyet").

DİL: Her konuyu hem Türkçe (tr) hem İngilizce (en) üret. Aynı analizi anlatsınlar; motamot çeviri şart değil ama sayılar ve kaynak URL'leri iki dilde de birebir aynı olmalıdır. "beat" alanını her dilde o dilin kelimesiyle yaz (TR: KRİPTO / MAKRO / EMTİA / HİSSE / POLİTİKA / LİKİDİTE — EN: CRYPTO / MACRO / COMMODITIES / EQUITIES / POLICY / LIQUIDITY).

ÇIKTI JSON ŞEMASI (MUTLAKA BU FORMATTA OLMALIDIR):
{
  "featured_topics": [
    {
      "tr": {
        "beat": "KRİPTO",
        "title": "...",
        "topic": "...",
        "primary_sources": [
          {"name": "...", "url": "https://... veya null", "description": "..."}
        ]
      },
      "en": {
        "beat": "CRYPTO",
        "title": "...",
        "topic": "...",
        "primary_sources": [
          {"name": "...", "url": "https://... veya null", "description": "..."}
        ]
      }
    }
  ]
}
"""


# Curated registry of stable, canonical primary-source landing pages.
# The Research Desk agent may ONLY emit URLs from this registry or from the
# day's real news items; anything else is stripped in post-validation.
CANONICAL_SOURCES = {
    "SEC EDGAR Full-Text Search": "https://www.sec.gov/edgar/search/",
    "Federal Reserve — FOMC Calendar & Statements": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "Federal Reserve — H.4.1 Balance Sheet Release": "https://www.federalreserve.gov/releases/h41/",
    "Federal Reserve — H.6 Money Stock (M2)": "https://www.federalreserve.gov/releases/h6/",
    "BLS — Consumer Price Index (CPI)": "https://www.bls.gov/cpi/",
    "BLS — Employment Situation (NFP)": "https://www.bls.gov/news.release/empsit.toc.htm",
    "BEA — PCE Price Index": "https://www.bea.gov/data/personal-consumption-expenditures-price-index",
    "FRED — St. Louis Fed Economic Data": "https://fred.stlouisfed.org/",
    "US Treasury — Daily Yield Curve Rates": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
    "US Treasury — Daily Treasury Statement (TGA)": "https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/",
    "Farside — Bitcoin ETF Flows (All Data)": "https://farside.co.uk/bitcoin-etf-flow-all-data/",
    "Farside — Ethereum ETF Flows": "https://farside.co.uk/ethereum-etf-flow-all-data/",
    "CME FedWatch Tool": "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
    "ISM — Report on Business (PMI)": "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/",
    "ECB — Press Releases": "https://www.ecb.europa.eu/press/pr/date/html/index.en.html",
    "Bank of Japan": "https://www.boj.or.jp/en/",
    "BIS — Bank for International Settlements": "https://www.bis.org/",
    "IMF — World Economic Outlook": "https://www.imf.org/en/Publications/WEO",
    "EIA — Weekly Petroleum Status Report": "https://www.eia.gov/petroleum/supply/weekly/",
    "Coinglass — Derivatives Data": "https://www.coinglass.com/",
    "DefiLlama — Stablecoins & TVL": "https://defillama.com/stablecoins",
    "Glassnode Insights": "https://insights.glassnode.com/",
    "CoinGecko": "https://www.coingecko.com/",
}


# ═══════════════════════════════════════════
# HELPER: Prepare data summary for LLM
# ═══════════════════════════════════════════

def _trim_for_prompt(payload, edition='daily'):
    """Drop render-only keys and shorten long point-series for the LLM copy.

    Returns a new dict. `data` itself is never touched, so the bulletin, the
    charts and the snapshot still see every point that was fetched — this only
    decides what the model is billed to read. See config/prompt_budget.py.
    """
    caps = PROMPT_SERIES_CAPS_WEEKLY if edition == 'weekly' else PROMPT_SERIES_CAPS
    trimmed = {k: v for k, v in payload.items() if k not in PROMPT_EXCLUDED_KEYS}

    def tail(series, limit):
        return series[-limit:] if isinstance(series, list) and len(series) > limit else series

    for path, limit in caps.items():
        key, _, field = path.partition('.')
        holder = trimmed.get(key)

        if not field:
            # The value is the series itself.
            trimmed[key] = tail(holder, limit)
            continue

        if not isinstance(holder, dict):
            continue

        # Copy the holder so a cap never propagates back into `data`.
        if field == '*':
            trimmed[key] = {f: tail(v, limit) for f, v in holder.items()}
        elif isinstance(holder.get(field), list):
            holder = dict(holder)
            holder[field] = tail(holder[field], limit)
            trimmed[key] = holder

    return trimmed


def _prepare_data_summary(data, edition='daily'):
    """Create a clean copy of the newsletter data for the LLM, excluding AI outputs."""
    exclude_keys = {
        'tr', 'en', 'ai_summary', 'news_commentaries',
        'futures_note',
        'etf_note', 'indicators_note', 'weekly_themes'
    }
    if edition == 'weekly':
        # The weekly bulletin renders weekly aggregates (etf_weekly_history_data);
        # hide the single-day ETF numbers so the AI notes can't quote figures
        # that contradict the weekly totals shown on the card.
        exclude_keys |= {'etf_flows', 'etf_history_data'}
    summary = {k: v for k, v in data.items() if k not in exclude_keys}
    return _trim_for_prompt(summary, edition=edition)



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

            data_summary = _prepare_data_summary(data, edition=edition)
            
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
                
                raw_response = _call_with_retry(client, WEEKLY_CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt, max_tokens=10000)
                result = self._parse_response(raw_response)
                if not result.get('tr') and not result.get('en'):
                    print("    ❌ Haftalık editör yanıtı parse edilemedi — AI bölümleri gizlenecek.")
                    return {'success': False, 'regime': 'NEUTRAL', 'tr': {}, 'en': {}}
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

                raw_response = _call_with_retry(client, CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt, max_tokens=6000)
                result = self._parse_response(raw_response)
                if not result.get('tr') and not result.get('en'):
                    print("    ❌ Günlük editör yanıtı parse edilemedi — AI bölümleri gizlenecek.")
                    return {'success': False, 'regime': 'NEUTRAL', 'tr': {}, 'en': {}}
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


class ResearchDeskAgent:
    """
    Araştırma Masası Agent.
    Günün gerçek haber akışı ve piyasa verisinden 3 stratejik araştırma konusu
    ve her konu için birincil kaynak listesi üretir.

    Kaynak URL'leri asla modele bırakılmaz: yanıt, günün haber linkleri +
    CANONICAL_SOURCES kayıtlarından oluşan izinli listeye karşı doğrulanır,
    listede olmayan her URL null'a düşürülür (uydurma link basılmaz).
    """

    # Research-relevant slice of the newsletter data. The full payload is
    # ~10x bigger and mostly chart series the desk does not need. The slice is
    # still put through _trim_for_prompt: coinbase_premium alone carried 168
    # hourly points, half of this agent's prompt.
    CONTEXT_KEYS = (
        'date', 'crypto_market_overview', 'macro_indicators', 'fear_and_greed',
        'funding_rates', 'open_interest', 'economic_calendar', 'coinbase_premium',
        'macro_scoreboard', 'crypto_futures_basis', 'etf_flows', 'eth_etf_flows',
        'stablecoin_data', 'global_liquidity', 'fed_pricing', 'sp500_sectors',
    )

    def analyze(self, data):
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            print("    ⚠️  ANTHROPIC_API_KEY tanımlı değil — Araştırma Masası atlanıyor.")
            return {'success': False, 'featured_topics': []}

        news_items = data.get('macro_news', {}).get('news', []) or []
        if not news_items:
            print("    ℹ️  Gerçek haber yok — Araştırma Gündemi üretilmiyor (bölüm gizlenecek).")
            return {'success': False, 'featured_topics': []}

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            news_inputs = [
                {
                    "title": n.get('title'),
                    "summary": n.get('summary'),
                    "source": n.get('source'),
                    "url": n.get('url'),
                }
                for n in news_items
            ]
            context = _trim_for_prompt(
                {k: data.get(k) for k in self.CONTEXT_KEYS if data.get(k)}
            )

            allowed_sources = dict(CANONICAL_SOURCES)
            for n in news_inputs:
                if n.get('url'):
                    allowed_sources[f"{n.get('source', 'News')} — {n.get('title', '')}"] = n['url']

            user_prompt = f"""Bugünün gerçek haber akışı, piyasa verileri ve izinli kaynak listesi aşağıdadır.
Okuyucunun bugün derinlemesine takip etmesi gereken 3 stratejik araştırma konusunu üret.

### Günün Haberleri (gerçek, doğrulanmış):
{json.dumps(news_inputs, ensure_ascii=False, indent=2)}

### İZİNLİ KAYNAK LİSTESİ (url alanına SADECE buradaki URL'ler harfi harfine yazılabilir; uygun yoksa null):
{json.dumps(allowed_sources, ensure_ascii=False, indent=2)}

### Piyasa Verileri:
```json
{json.dumps(context, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme."""

            # 3 topics x 2 languages x 3 sourced bullets runs ~5-6k tokens;
            # 4000 truncated the JSON mid-string in testing.
            raw_response = _call_with_retry(
                client, RESEARCH_DESK_SYSTEM_PROMPT, user_prompt, max_tokens=8000
            )
            result = ContentEditorAgent()._parse_response(raw_response)
            topics = self._sanitize(result.get('featured_topics', []), allowed_sources)

            if not topics:
                print("    ❌ Araştırma Masası yanıtı kullanılabilir konu içermiyor — bölüm gizlenecek.")
                return {'success': False, 'featured_topics': []}

            print(f"    ✅ Stratejik Araştırma Gündemi üretildi ({len(topics)} konu).")
            return {
                'success': True,
                'has_featured_topics': True,
                'featured_topics': topics,
            }

        except Exception as e:
            print(f"    ⚠️  Araştırma Masası hatası: {e}")
            return {'success': False, 'featured_topics': []}

    def _sanitize(self, topics, allowed_sources):
        """Drop malformed topics and null out any URL the agent invented."""
        allowed_urls = set(allowed_sources.values())
        clean_topics = []
        stripped = 0

        for t in topics[:3]:
            if not isinstance(t, dict):
                continue
            clean = {}
            for lang in ('tr', 'en'):
                content = t.get(lang)
                if not isinstance(content, dict):
                    continue
                title = (content.get('title') or '').strip()
                topic = (content.get('topic') or '').strip()
                if not title or not topic:
                    continue

                sources = []
                for s in content.get('primary_sources', []) or []:
                    if not isinstance(s, dict) or not (s.get('name') or '').strip():
                        continue
                    url = (s.get('url') or '').strip()
                    if url and url not in allowed_urls:
                        stripped += 1
                        url = None
                    sources.append({
                        'name': s.get('name', '').strip(),
                        'url': url or None,
                        'description': (s.get('description') or '').strip(),
                    })

                clean[lang] = {
                    'beat': (content.get('beat') or '').strip(),
                    'title': title,
                    'topic': topic,
                    'primary_sources': sources,
                }

            # Both languages are required — a half-rendered topic would leave
            # one edition with a blank card.
            if 'tr' in clean and 'en' in clean:
                clean_topics.append(clean)

        if stripped:
            print(f"    🧹 {stripped} uydurma/izinsiz kaynak URL'si temizlendi.")
        return clean_topics
