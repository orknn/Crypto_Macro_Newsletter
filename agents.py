"""
AI Agents — Financial Content Editor & Research Desk
Generates the bulletin's written layer. Provider and model come from
config/llm.py; nothing here names a model.
"""
import os
import json
import time
from datetime import datetime

from config import llm
from config import models
from config.prompt_budget import (PROMPT_EXCLUDED_KEYS, PROMPT_SERIES_CAPS,
                                  PROMPT_SERIES_CAPS_WEEKLY, prune_unrendered)
from schemas.agent_responses import (CONTENT_EDITOR_DAILY_SCHEMA,
                                     CONTENT_EDITOR_WEEKLY_SCHEMA,
                                     RESEARCH_DESK_SCHEMA,
                                     SECTION_ANALYSIS_SCHEMA,
                                     EXEC_SUMMARY_SCHEMA,
                                     NEWS_TRANSMISSION_SCHEMA,
                                     OVERVIEW_RETRY_SCHEMA)


# How much more room a truncated call gets on its one retry. Generous on
# purpose: a second truncation costs another full call and leaves the section
# hidden anyway, so shaving this saves nothing worth having.
TRUNCATION_RETRY_FACTOR = 1.75


def llm_available():
    """True when the active provider has a key to call with."""
    return bool(os.environ.get(llm.api_key_env(), '').strip())


def _call_openai(system_prompt, user_prompt, max_tokens, schema, schema_name,
                 model=None):
    """One Responses API call. Returns (text, usage dict).

    `model` is always passed explicitly by the two-pass code (config/models.py)
    and falls back to config/llm.py only for the daily edition, which has not
    been re-routed. Nothing here defaults to a bare alias: an unqualified
    `gpt-5.6` routes to the flagship and bills at flagship rates.

    max_output_tokens covers reasoning and visible output together, which is
    why reasoning effort is held down — otherwise the model can spend the
    budget thinking and return JSON that stops mid-string.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    model = model or llm.OPENAI_MODEL
    effort = (models.reasoning_effort(model) if model in models.PRICING
              else llm.OPENAI_REASONING_EFFORT)

    kwargs = {
        'model': model,
        'reasoning': {'effort': effort},
        'max_output_tokens': max_tokens,
        'instructions': system_prompt,
        'input': user_prompt,
    }
    if schema is not None:
        kwargs['text'] = {'format': {
            'type': 'json_schema',
            'name': schema_name,
            'schema': schema,
            'strict': True,
        }}

    r = client.responses.create(**kwargs)

    # 'incomplete' is the Responses API's way of saying it ran out of budget.
    # Say so loudly: a silently truncated answer is how this pipeline shipped
    # empty bulletins twice while printing a tick.
    truncated = r.status == 'incomplete'
    if truncated:
        reason = getattr(getattr(r, 'incomplete_details', None), 'reason', '?')
        print(f"    ⚠️  Yanıt tamamlanmadı (status=incomplete, reason={reason}, "
              f"max_output_tokens={max_tokens}) — JSON büyük ihtimalle kesik.")

    u = r.usage
    details = getattr(u, 'output_tokens_details', None)
    in_details = getattr(u, 'input_tokens_details', None)
    usage = {
        'model': r.model,
        'input_tokens': u.input_tokens,
        # Cached input bills at a tenth. Reported so logs/cost.jsonl shows what
        # caching actually saved rather than what it was expected to.
        'cached_input_tokens': getattr(in_details, 'cached_tokens', 0) or 0,
        'output_tokens': u.output_tokens,
        'reasoning_tokens': getattr(details, 'reasoning_tokens', 0) or 0,
        'truncated': truncated,
    }
    return r.output_text.strip(), usage


def _call_anthropic(system_prompt, user_prompt, max_tokens):
    """Rollback path. No strict schema here — the text parser still applies."""
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    r = client.messages.create(
        model=llm.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        temperature=llm.ANTHROPIC_TEMPERATURE,
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    truncated = getattr(r, 'stop_reason', None) == 'max_tokens'
    if truncated:
        print(f"    ⚠️  AI yanıtı max_tokens={max_tokens} sınırında KESİLDİ — "
              "JSON büyük ihtimalle bozuk.")

    u = r.usage
    usage = {
        'model': llm.ANTHROPIC_MODEL,
        'input_tokens': u.input_tokens,
        'output_tokens': u.output_tokens,
        'reasoning_tokens': 0,
        'truncated': truncated,
    }
    return r.content[0].text.strip(), usage


def _call_with_retry(system_prompt, user_prompt, max_tokens=4000,
                     schema=None, schema_name='response', max_retries=3,
                     agent='?', model=None):
    """Call the active provider, retrying on rate limits and on truncation.

    A truncated answer is retried once with a larger budget. Cutting the JSON
    mid-string is the failure this pipeline has shipped twice — a run that
    printed a tick and mailed an empty bulletin (93da3df, cb2c5d8) — and it is
    the one failure where trying again is almost certain to work, because the
    cause is a number we control rather than anything about the request.
    Retrying blind would be wasteful; retrying with more room is not.
    """
    budget = max_tokens
    grown = False

    for attempt in range(max_retries):
        try:
            if llm.PROVIDER == 'openai':
                text, usage = _call_openai(system_prompt, user_prompt,
                                           budget, schema, schema_name, model)
            else:
                text, usage = _call_anthropic(system_prompt, user_prompt, budget)
            _log_ai_call(agent=agent, max_tokens=budget,
                         prompt_chars=len(user_prompt) + len(system_prompt),
                         response_chars=len(text), status='success', **usage)

            if usage.get('truncated') and not grown:
                grown = True
                budget = int(budget * TRUNCATION_RETRY_FACTOR)
                print(f"    ↻ Kesik yanıt — max_output_tokens {max_tokens} → {budget} "
                      "ile bir kez daha deneniyor.")
                continue

            return text
        except Exception as e:
            error_str = str(e)
            if ('429' in error_str or 'rate' in error_str.lower()) and attempt < max_retries - 1:
                wait_time = 15 * (attempt + 1)
                print(f"    ⏳ Rate limit, {wait_time}s bekleniyor... (deneme {attempt + 2}/{max_retries})")
                time.sleep(wait_time)
            else:
                _log_ai_call(agent=agent, model=llm.active_model(),
                             max_tokens=max_tokens,
                             prompt_chars=len(user_prompt) + len(system_prompt),
                             response_chars=0,
                             status=f"error: {error_str[:200]}")
                raise


def _log_ai_call(agent, max_tokens, prompt_chars, response_chars, status,
                 model=None, input_tokens=0, output_tokens=0,
                 reasoning_tokens=0, truncated=False, cached_input_tokens=0):
    """Record one call to logs/cost.jsonl and to fetch_report.json.

    Token counts come from the provider's own usage block, so the cost here is
    what was billed rather than a guess from character counts.
    """
    cost = models.estimate_cost(model or '', input_tokens, output_tokens,
                                cached_input_tokens)
    entry = {
        'timestamp': datetime.now().isoformat(),
        'agent': agent,
        'provider': llm.PROVIDER,
        'model': model,
        'max_tokens': max_tokens,
        'input_tokens': input_tokens,
        'cached_input_tokens': cached_input_tokens,
        'output_tokens': output_tokens,
        'reasoning_tokens': reasoning_tokens,
        'estimated_usd': round(cost, 6),
        'truncated': truncated,
        'prompt_chars': prompt_chars,
        'response_chars': response_chars,
        'status': status,
    }

    if status == 'success':
        print(f"       {agent}: in={input_tokens} out={output_tokens}"
              f"{f' (reasoning={reasoning_tokens})' if reasoning_tokens else ''}"
              f" — ${cost:.4f}")
    if cost > llm.COST_ALERT_USD:
        print(f"    ⚠️  Tek çağrı eşiği aştı: ${cost:.4f} > ${llm.COST_ALERT_USD:.2f}")

    try:
        os.makedirs(os.path.dirname(llm.COST_LOG_PATH), exist_ok=True)
        with open(llm.COST_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass

    report_path = 'fetch_report.json'
    report_data = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
        except Exception:
            pass
    report_data.setdefault('ai_calls', []).append(entry)
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
Rejim SANA VERİLİR — piyasa verisinden deterministik olarak hesaplanmıştır, sen SEÇMEZSİN.
Girdideki "regime" alanını oku ve "regime_line" cümleni O rejimi savunacak şekilde yaz.
Rejimle çelişen bir hüküm kurma.

Her dil (tr ve en) için aşağıdaki alanları doldurmalısın:
1. "regime_line": VERİLEN rejim için tek cümlelik, vurucu bir piyasa hükmü (Örn: TR: "Hisse senetlerindeki ralli ve ETF girişleri risk iştahını destekliyor." / EN: "Stock rally and ETF inflows support risk appetite.")
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
Rejim SANA VERİLİR — piyasa verisinden deterministik olarak hesaplanmıştır, sen SEÇMEZSİN.
Girdideki "regime" alanını oku ve "regime_line" cümleni O rejimi savunacak şekilde yaz.
Rejimle çelişen bir hüküm kurma.

Her dil (tr ve en) için aşağıdaki alanları doldurmalısın:
1. "regime_line": VERİLEN rejim için tek cümlelik, vurucu bir piyasa hükmü (Örn: TR: "Likidite daralması ve artan tahvil faizleri risk iştahını gölgeliyor." / EN: "Liquidity contraction and rising bond yields shadow risk appetite.")
1b. "overview": Haftanın YÖNETİCİ ÖZETİ (executive summary) — 3-4 cümle. Haftanın en önemli makro gelişmesi, kripto piyasasının genel yönü, ETF/kurumsal akım resmi ve önümüzdeki haftanın en kritik katalizörünü tek paragrafta birleştir. Bültenin tamamını okumayan birinin haftayı anlaması için yeterli olmalı. Önemli sayıları <strong> etiketiyle vurgulayabilirsin.
2. "themes":
   - Haftanın en önemli 3 makro/kripto teması. Her tema bir başlık ("title", en fazla 2-3 kelime, örn: "LIKIDITE RUZGARI" veya "JEOPOLITIK GERILIM") ve 2-3 cümlelik açıklama ("description") içermelidir.
2b. "conflicting_signals":
   - SANA "ÇELİŞEN SİNYALLER" başlığı altında, piyasa verisinden DETERMİNİSTİK olarak tespit edilmiş çelişki çiftleri verilir. Çelişkiyi sen BULMAZSIN; sana verilir.
   - Her çift için "pair" alanını sana verilen değerle HARFİ HARFİNE aynı yaz.
   - "reconciliation": iki ölçümün neden aynı anda doğru olabileceğini açıklayan 1-2 cümle. Piyasa YAPISINA dayanan mekanik bir açıklama ara (hangi alıcı tipi, hangi işlem yeri, hangi vade, hangi enstrüman).
   - MUTLAK KURAL: Uzlaştıracak gerçek bir mekanizma bulamıyorsan "reconciliation" alanına tam olarak "UNRESOLVED" yaz. Çelişkinin sürdüğünü söylemek geçerli ve dürüst bir çıktıdır. ASLA uydurma açıklama üretme.
   - Sana "mekanizma zaten biliniyor" diye işaretlenmiş bir çift verilirse onun için "UNRESOLVED" yaz; o çiftin metni koddan gelir.
3. "notes" — HER NOT İKİ ALANDAN OLUŞUR:
   - "what": Veriyi tekrar eden TEK cümle. Okuyucunun az önce baktığı sayıyı özetler.
   - "so_what": O verinin NE ANLAMA GELDİĞİNİ söyleyen TEK cümle. Konumlanma veya varlık etkisi İÇERMEK ZORUNDA — hangi varlık, hangi yön, hangi vade, hangi eşik.
   - "so_what" alanı ASLA "what"ın yeniden yazımı olamaz. Sayıyı tekrarlamak analiz değildir.
   - MUTLAK KURAL: Bir bölüm için gerçek bir "so_what" üretemiyorsan o notun İKİ alanını da boş string ("") bırak. Bölüm bültenden tamamen çıkarılır. Yarım not basmak yerine bölümü kaybetmek tercih edilir.
   Notlar:
   - "liquidity_note": Haftalık Fed Net Likiditesi ve finansal koşullar (NFCI).
   - "inflation_note": ABD enflasyon patikası (CPI/PCE).
   - "stablecoin_note": Stablecoin TOPLAM ARZININ haftalık değişimi — bunu kenarda bekleyen alım gücü ("dry powder") sinyali olarak yorumla. "Pazar payı savaşı" anlatısı KULLANMA.
   - "etf_note": Haftalık spot ETF akışları. DİKKAT: pozitif akışı doğrudan "yönlü kurumsal talep" diye SUNMA. ABD spot BTC ETF'leri nakit-yaratım modeliyle çalışır; net akışın bir bölümü delta-nötr baz işlemi (ETF long + vadeli short) olabilir ve bu yönlü talep DEĞİLDİR. Akışı funding oranı ve açık pozisyon (OI) değişimiyle BİRLİKTE değerlendir: yüksek akış + yükselen funding + artan OI baz işlemine işaret eder; yüksek akış + durgun funding yönlü talebe daha yakındır.
   - "rotation_note": Sektör rotasyon eğilimleri.
   - "cycle_note": Bitcoin döngüsel göstergeleri (Mayer, 200WMA, drawdown).
   - "correlation_note": Varlıklar arası korelasyon.
   - "futures_note": Vadeli yapı, funding ve konumlanma.
   - "week_plan_note": Önümüzdeki haftanın stratejik planı.
   - "news_note": Haftanın kritik haberlerinin makro etkileri.
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
  "tr": {
    "regime_line": "...",
    "overview": "...",
    "themes": [
      {"title": "...", "description": "..."},
      {"title": "...", "description": "..."},
      {"title": "..." ,"description": "..."}
    ],
    "conflicting_signals": [
      {"pair": "...", "reconciliation": "... veya UNRESOLVED"}
    ],
    "notes": {
      "liquidity_note": {"what": "...", "so_what": "..."},
      "inflation_note": {"what": "...", "so_what": "..."},
      "stablecoin_note": {"what": "...", "so_what": "..."},
      "etf_note": {"what": "...", "so_what": "..."},
      "rotation_note": {"what": "...", "so_what": "..."},
      "cycle_note": {"what": "...", "so_what": "..."},
      "correlation_note": {"what": "...", "so_what": "..."},
      "futures_note": {"what": "...", "so_what": "..."},
      "week_plan_note": {"what": "...", "so_what": "..."},
      "news_note": {"what": "...", "so_what": "..."}
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
    "conflicting_signals": [
      {"pair": "...", "reconciliation": "... or UNRESOLVED"}
    ],
    "notes": {
      "liquidity_note": {"what": "...", "so_what": "..."},
      "inflation_note": {"what": "...", "so_what": "..."},
      "stablecoin_note": {"what": "...", "so_what": "..."},
      "etf_note": {"what": "...", "so_what": "..."},
      "rotation_note": {"what": "...", "so_what": "..."},
      "cycle_note": {"what": "...", "so_what": "..."},
      "correlation_note": {"what": "...", "so_what": "..."},
      "futures_note": {"what": "...", "so_what": "..."},
      "week_plan_note": {"what": "...", "so_what": "..."},
      "news_note": {"what": "...", "so_what": "..."}
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
    # The model may only reason over what the reader will see. Anything the
    # edition does not print is removed here, which is what stops a note from
    # citing a real figure the reader cannot find on the page.
    summary = prune_unrendered(summary, edition=edition)
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
        if not llm_available():
            print(f"    ⚠️  {llm.api_key_env()} tanımlı değil — İçerik Editörü atlanıyor ({edition}).")
            return {'success': False, 'tr': {}, 'en': {}}

        try:
            data_summary = _prepare_data_summary(data, edition=edition)
            # The regime is decided before the model is called; it reads it.
            computed_regime = data.get('regime', 'NEUTRAL')
            
            raw_news = data.get('macro_news', {}).get('news', [])
            news_inputs = [{"title": n.get('title'), "summary": n.get('summary')} for n in raw_news]

            if edition == 'weekly':
                conflicts = data.get('signal_conflicts') or []
                conflict_inputs = [{
                    'pair': c['pair'],
                    'signal_a': f"{c['signal_a']['labels']['tr']} = {c['signal_a']['value']}",
                    'signal_b': f"{c['signal_b']['labels']['tr']} = {c['signal_b']['value']}",
                    # Mechanically explained pairs are answered by the code, so
                    # the model is told not to spend a paragraph on them.
                    'mekanizma_zaten_biliniyor': bool(c.get('mechanism')),
                } for c in conflicts]

                user_prompt = f"""HESAPLANMIŞ PİYASA REJİMİ: {computed_regime}

ÇELİŞEN SİNYALLER (piyasa verisinden deterministik olarak tespit edildi — sen bulmadın, sana veriliyor):
{json.dumps(conflict_inputs, ensure_ascii=False, indent=2) if conflict_inputs else "Bu hafta çelişen sinyal çifti tespit edilmedi. conflicting_signals: [] dön."}

Aşağıda bu haftanın bülten verileri ve haber gelişmeleri yer almaktadır.
Bu verileri analiz ederek haftalık bülten için tek bir dual-language JSON çıktısı oluştur:

Haber Maddeleri:
{json.dumps(news_inputs, ensure_ascii=False, indent=2)}

Piyasa Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan."""
                
                raw_response = _call_with_retry(
                    WEEKLY_CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt, max_tokens=10000,
                    schema=CONTENT_EDITOR_WEEKLY_SCHEMA, schema_name='weekly_bulletin',
                    agent='ContentEditor/weekly')
                result = self._parse_response(raw_response)
                if not result.get('tr') and not result.get('en'):
                    print("    ❌ Haftalık editör yanıtı parse edilemedi — AI bölümleri gizlenecek.")
                    return {'success': False, 'tr': {}, 'en': {}}
                print("    ✅ Haftalık Temalar ve Dinamik KPI Notları (TR/EN) üretildi.")
                return {'success': True,
                        'tr': result.get('tr', {}), 'en': result.get('en', {})}
            else:
                user_prompt = f"""HESAPLANMIŞ PİYASA REJİMİ: {computed_regime}

Aşağıda bugünkü finans bülteninin tüm canlı piyasa verileri ve haber gelişmeleri yer almaktadır.
Bu verileri analiz ederek günlük bülten için tek bir dual-language JSON çıktısı oluştur:

Haber Maddeleri:
{json.dumps(news_inputs, ensure_ascii=False, indent=2)}

Piyasa Verileri:
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER, başka metin ekleme. JSON içindeki metin alanlarında çift tırnak işaretlerini kesinlikle kaçış karakteriyle (\\") yaz veya tek tırnak (') kullan."""

                raw_response = _call_with_retry(
                    CONTENT_EDITOR_SYSTEM_PROMPT, user_prompt, max_tokens=6000,
                    schema=CONTENT_EDITOR_DAILY_SCHEMA, schema_name='daily_bulletin',
                    agent='ContentEditor/daily')
                result = self._parse_response(raw_response)
                if not result.get('tr') and not result.get('en'):
                    print("    ❌ Günlük editör yanıtı parse edilemedi — AI bölümleri gizlenecek.")
                    return {'success': False, 'tr': {}, 'en': {}}
                print("    ✅ Genel Değerlendirme, Haber Yorumları ve Dinamik KPI Notları (TR/EN) üretildi.")
                return {'success': True,
                        'tr': result.get('tr', {}), 'en': result.get('en', {})}

        except Exception as e:
            print(f"    ⚠️  İçerik Editörü hatası: {e}")
            return {'success': False, 'tr': {}, 'en': {}}

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


OVERVIEW_RETRY_SYSTEM_PROMPT = """Sen, bir finans bülteninin Kıdemli İçerik Editörüsün.

Bültenin GENEL DEĞERLENDİRME paragrafı yazıldı ve sayı denetiminden geçemedi:
içinde, sana verilen veride karşılığı olmayan en az bir rakam vardı. O paragraf
silindi. Görevin onu bir kez daha yazmak.

Bu bir düzeltme değil, yeniden yazımdır: reddedilen rakamı "düzeltmeye"
çalışma, doğru değerini tahmin etme. O rakamın ne olduğunu bilmiyorsun.

MUTLAK KURALLAR:
1. Yazdığın HER yüzde ve HER fiyat, sana aşağıda verilen veride birebir
   bulunmalıdır. Veride olmayan hiçbir sayıyı yazma.
2. REDDEDİLEN RAKAMLAR listesindeki değerleri bir daha kullanma.
3. Bir hareketten emin değilsen sayıyı hiç yazma — yönü kelimeyle anlat
   ("geriledi", "sınırlı toparlanma", "yatay seyretti"). Sayısız bir cümle,
   uydurma rakamlı bir cümleden her zaman iyidir.
4. Paragrafta hiç rakam olmaması kabul edilebilir bir sonuçtur.

BİÇİM:
- 4-6 cümlelik profesyonel bir özet paragrafı, tek parça metin.
- Verilen rejimi savunur, onunla çelişmez.
- <strong> ve <span class='highlight'> etiketleri kullanılabilir.
- tr ve en aynı analizi anlatır; motamot çeviri şart değil, ama iki dildeki
  SAYILAR birebir aynı olmalıdır.

ÇIKTI JSON ŞEMASI:
{"tr": {"overview": "..."}, "en": {"overview": "..."}}
"""


class OverviewRetryAgent:
    """Rewrites the overview once, after the figure audit rejected the first.

    The overview is the only generated field with no graceful degradation. A
    note that fails the audit is hidden, an insight is blanked, a theme is
    dropped — the bulletin ships without them. The overview instead trips the
    content quality gate, which skips the mail and fails the run, so a single
    invented percentage costs subscribers the whole day's bulletin. That is
    what happened on 13 Aug: the model wrote %4,8, no fetched number was within
    tolerance of it, and both editions went unsent.

    Failing there is right — publishing the figure would be worse. But failing
    there *without asking again* is not, because the fault is not in the data.
    Nothing was missing and nothing was stale; the writer simply wrote a number
    it should not have. That is the class of failure a second attempt fixes,
    and this pipeline already accepts that reasoning elsewhere: a truncated
    response is retried with a larger budget for exactly the same reason.

    One attempt, not a loop. If the second overview also quotes an unsourced
    figure, the model is wrong about the data in a way that repetition will not
    settle, and the gate does its original job.

    The retry is told which figures were rejected and forbidden from reusing
    them, because a bare "try again" over an unchanged prompt is a coin flip.
    It is also told, explicitly, that a paragraph with no numbers at all is an
    acceptable answer — the failure mode being escaped is a model that reaches
    for a figure it does not have.
    """

    def analyze(self, data, langs, rejected_figures, edition='daily'):
        """Return {lang: overview} for the languages that came back clean.

        Languages absent from the result keep their blanked overview, so a
        partial success is honoured: TR recovering while EN does not is a
        better outcome than discarding both.
        """
        if not llm_available():
            print(f"    ⚠️  {llm.api_key_env()} yok — genel değerlendirme yeniden denenmiyor.")
            return {}

        # Each edition's retry sees exactly what that edition's writer saw. For
        # the weekly that is the digest, never the raw payload — page one is
        # not allowed to reach past the sections below it on a retry any more
        # than it was on the first pass.
        if edition == 'weekly':
            payload = data.get('_digest')
            model = models.MODEL.EXEC_SUMMARY
            if not payload:
                print("    ⚠️  Digest yok — genel değerlendirme yeniden denenmiyor.")
                return {}
        else:
            payload = _prepare_data_summary(data, edition=edition)
            model = models.MODEL.DAILY_EDITOR

        user_prompt = f"""HESAPLANMIŞ PİYASA REJİMİ: {data.get('regime', 'NEUTRAL')}

REDDEDİLEN RAKAMLAR (bunlar veride yok — bir daha yazma):
{json.dumps(rejected_figures, ensure_ascii=False)}

YENİDEN YAZILACAK DİLLER: {', '.join(langs)}

Yazabileceğin TÜM sayılar aşağıdaki veridedir. Burada olmayan bir sayı yazma.

```json
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER."""

        print(f"    ↻ Genel değerlendirme yeniden yazılıyor ({model}) — "
              f"reddedilen: {', '.join(rejected_figures)}")
        try:
            raw = _call_with_retry(
                OVERVIEW_RETRY_SYSTEM_PROMPT, user_prompt, max_tokens=2000,
                schema=OVERVIEW_RETRY_SCHEMA, schema_name='overview_retry',
                agent=f'OverviewRetry/{edition}', model=model)
            parsed = ContentEditorAgent()._parse_response(raw) or {}
        except Exception as e:
            print(f"    ⚠️  Genel değerlendirme yeniden yazılamadı: {e}")
            return {}

        out = {}
        for lang in langs:
            text = (parsed.get(lang) or {}).get('overview')
            if isinstance(text, str) and text.strip():
                out[lang] = text.strip()
        return out


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
        if not llm_available():
            print(f"    ⚠️  {llm.api_key_env()} tanımlı değil — Araştırma Masası atlanıyor.")
            return {'success': False, 'featured_topics': []}

        news_items = data.get('macro_news', {}).get('news', []) or []
        if not news_items:
            print("    ℹ️  Gerçek haber yok — Araştırma Gündemi üretilmiyor (bölüm gizlenecek).")
            return {'success': False, 'featured_topics': []}

        try:
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
                RESEARCH_DESK_SYSTEM_PROMPT, user_prompt, max_tokens=8000,
                schema=RESEARCH_DESK_SCHEMA, schema_name='research_brief',
                agent='ResearchDesk')
            result = ContentEditorAgent()._parse_response(raw_response)
            topics = self._sanitize(result.get('featured_topics', []), allowed_sources)

            if not topics:
                print("    ❌ Araştırma Masası yanıtı kullanılabilir konu içermiyor — bölüm gizlenecek.")
                return {'success': False, 'featured_topics': []}

            print(f"    ✅ Stratejik Araştırma Gündemi üretildi ({len(topics)} konu).")
            return {'success': True, 'featured_topics': topics}

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


# ═══════════════════════════════════════════════════════════════════
# TWO-PASS WEEKLY  (phase 2.5)
# ═══════════════════════════════════════════════════════════════════
#
# Pass 1 runs one call per section over that section's slice of data, and
# returns structure rather than prose. Pass 2 gets those structures plus a
# compact numeric digest — never the raw payload.
#
# That restriction is the whole design. Under the single-call version the
# executive summary and the section notes were written from the same undifferen-
# tiated dump, and nothing stopped page one from quoting a figure the sections
# below it never mentioned, or from reading the week differently than they did.
# Pass 2 can only cite what pass 1 surfaced.

# Which payload keys each section is allowed to see. Narrow on purpose: a
# section note that draws on the whole bulletin is how notes end up citing
# numbers that belong to some other section's chart.
SECTION_CONTEXT = {
    'liquidity_note': ('net_liquidity_history_data', 'nfci', 'global_liquidity'),
    'inflation_note': ('inflation_history_data', 'economic_calendar', 'fed_pricing'),
    'stablecoin_note': ('stablecoin_history_data',),
    'etf_note': ('etf_weekly_history_data', 'eth_etf_weekly_data',
                 'etf_cumulative_data', 'funding_rates', 'open_interest'),
    'rotation_note': ('crypto_sector_rotation_data', 'eth_btc', 'winners', 'losers'),
    'cycle_note': ('btc_cycle_metrics',),
    'correlation_note': ('correlation_matrix', 'ytd_comparison_data'),
    'futures_note': ('funding_rates', 'open_interest', 'crypto_futures_basis',
                     'options_data', 'coinbase_premium', 'fear_and_greed'),
    'week_plan_note': ('economic_calendar', 'fed_pricing'),
    'news_note': ('macro_news',),
}

# The stable half of every pass-1 call. It is sent first and byte-identical
# across all ~11 calls so prompt caching has a prefix to match; see
# config/models.CACHEABLE_PREFIX_FIRST. Anything week-specific goes in the user
# message, never here.
SECTION_ANALYST_SYSTEM_PROMPT = """Sen bir finans yayınının kıdemli analistisin. Sana TEK BİR BÖLÜMÜN verisi verilir ve o bölüm için yapılandırılmış bir analiz üretirsin.

ÇIKTI ALANLARI:
- "section": Sana verilen bölüm adını harfi harfine kopyala.
- "facts": Bölümdeki önemli sayıları `anahtar=değer` biçiminde listele (örn: "btc_etf_weekly_net=+865.3M"). SADECE sana verilen veriden al. Uydurma.
- "direction": bullish | bearish | neutral — bu bölümün risk iştahına işareti.
- "strength": 0.0-1.0 arası, sinyalin gücü.
- "key_metric": Bu bölümün üzerinde döndüğü TEK figürün anahtarı ("facts" içindeki anahtarlardan biri).
- "tr" ve "en": İkisi de {"what": "...", "so_what": "..."} biçiminde.

"what" ve "so_what" KURALLARI:
- "what": Veriyi özetleyen TEK cümle.
- "so_what": O verinin NE ANLAMA GELDİĞİNİ söyleyen TEK cümle. Konumlanma veya varlık etkisi İÇERMEK ZORUNDA — hangi varlık, hangi yön, hangi vade, hangi eşik.
- "so_what" ASLA "what"ın yeniden yazımı olamaz. Sayıyı tekrarlamak analiz değildir.
- MUTLAK KURAL: Gerçek bir "so_what" üretemiyorsan her iki dilde de "what" ve "so_what" alanlarını boş string ("") bırak. Bölüm bültenden tamamen çıkarılır. Yarım not basmaktansa bölümü kaybetmek tercih edilir.

SAYI KURALI: Yazdığın her sayı sana verilen veride BULUNMAK ZORUNDA. Hesaplama yapma, yuvarlama uydurma.
DİL: İki dil aynı analizi anlatır; sayılar birebir aynı olmalıdır."""


def _section_payload(section, data):
    """The slice of the bulletin one section is allowed to reason over."""
    keys = SECTION_CONTEXT.get(section, ())
    slice_ = {k: data.get(k) for k in keys if data.get(k) is not None}
    return _trim_for_prompt(slice_, edition='weekly')


class SectionAnalystAgent:
    """Pass 1. One call, one section, structured output."""

    def analyze(self, section, data):
        payload = _section_payload(section, data)
        if not payload:
            print(f"    ℹ️  {section}: veri yok — bölüm atlanıyor.")
            return None

        # Volatile content last: the cacheable prefix is the system prompt.
        user_prompt = f"""BÖLÜM: {section}

Bu bölümün verileri:
```json
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER."""

        try:
            raw = _call_with_retry(
                SECTION_ANALYST_SYSTEM_PROMPT, user_prompt, max_tokens=1500,
                schema=SECTION_ANALYSIS_SCHEMA, schema_name='section_analysis',
                agent=f'Pass1/{section}', model=models.MODEL.SECTION_NOTE)
            result = ContentEditorAgent()._parse_response(raw)
            if not result:
                return None
            result['section'] = section
            return result
        except Exception as e:
            print(f"    ⚠️  {section} analiz hatası: {e}")
            return None


def run_pass_one(data, sections=None):
    """Every section's structured analysis, keyed by section name.

    Sections are independent, so a failure is contained: one dead section costs
    that section, not the run.
    """
    sections = sections or [s for s in SECTION_CONTEXT if _section_payload(s, data)]
    print(f"\n🔷 Pass 1 — {len(sections)} bölüm ({models.MODEL.SECTION_NOTE})")

    results = {}
    agent = SectionAnalystAgent()
    for section in sections:
        analysis = agent.analyze(section, data)
        if analysis:
            results[section] = analysis
            print(f"    ✅ {section}: {analysis.get('direction')} "
                  f"({analysis.get('key_metric')})")
    return results


def build_digest(pass_one, data):
    """The compact numeric record pass 2 is allowed to quote from.

    Deliberately not the payload. Pass 2 sees each section's own `facts` plus
    the handful of headline figures, and nothing else — so every number it can
    write is a number some section already published.
    """
    digest = {'sections': {}, 'headline': {}}
    for section, analysis in pass_one.items():
        digest['sections'][section] = {
            'facts': analysis.get('facts', []),
            'direction': analysis.get('direction'),
            'strength': analysis.get('strength'),
            'key_metric': analysis.get('key_metric'),
        }

    fng = (data.get('fear_and_greed') or {}).get('value')
    if fng is not None:
        digest['headline']['fear_greed'] = fng
    overview = data.get('crypto_market_overview') or {}
    for key in ('total_market_cap', 'btc_dominance'):
        if overview.get(key) is not None:
            digest['headline'][key] = overview[key]
    for row in data.get('crypto_prices') or []:
        if row.get('Symbol') == 'BTC':
            digest['headline']['btc_price'] = row.get('Current Price USD')
            digest['headline']['btc_7d_pct'] = row.get('7d %')
            break
    return digest


EXEC_SUMMARY_SYSTEM_PROMPT = """Sen bir finans yayınının baş editörüsün. Haftanın TÜM bölüm analizleri sana YAPILANDIRILMIŞ biçimde verilir; senin işin onları tek bir yönetici görüşüne sıkıştırmaktır.

MUTLAK KURAL — SAYILAR: Yazdığın her sayı sana verilen digest'te BULUNMAK ZORUNDA. Digest dışından sayı getiremezsin, hesap yapamazsın, yuvarlayamazsın. Bu kural denetleniyor; ihlal eden çıktı reddedilir ve build FAIL olur.

ÜRETECEKLERİN (her biri hem "tr" hem "en"):
1. "regime_line": VERİLEN rejim için tek cümlelik vurucu piyasa hükmü. Rejimi sen SEÇMEZSİN, sana verilir.
2. "regime_rationale": Rejimi savunan en fazla 2 cümle.
3. "overview": Haftanın yönetici özeti, 3-4 cümle. Bültenin tamamını okumayanın haftayı anlaması için yeterli olmalı.
4. "themes": TAM OLARAK 3 tema. Her tema:
   - "title": 2-3 kelime.
   - "body": en fazla 2 cümle.
   - "metric_key": ZORUNLU. Sana verilen bölüm analizlerindeki "key_metric" değerlerinden BİRİ olmak zorunda. Uydurulmuş bir metric_key build'i düşürür.
5. "conflicting_signals": Sana verilen çelişki çiftleri için uzlaştırma. "pair" alanını harfi harfine kopyala. Gerçek bir mekanizma bulamıyorsan "reconciliation" alanına tam olarak "UNRESOLVED" yaz. ASLA uydurma açıklama üretme.
6. "scenarios": bear / base / bull. Her biri {"label", "condition", "transmission"}. "condition" olayın eşiği, "transmission" o eşik gerçekleşirse zincirin nasıl işleyeceği. Fiyat seviyesi UYDURMA — seviyeler koddan gelir.

DİL: İki dil aynı analizi anlatır; sayılar birebir aynı olmalıdır."""


class ExecutiveSummaryAgent:
    """Pass 2. One call, flagship tier, over pass 1's output only."""

    def analyze(self, data, pass_one):
        if not llm_available():
            print(f"    ⚠️  {llm.api_key_env()} yok — yönetici özeti atlanıyor.")
            return {}
        if not pass_one:
            print("    ⚠️  Pass 1 hiçbir bölüm üretmedi — yönetici özeti atlanıyor.")
            return {}

        digest = build_digest(pass_one, data)
        conflicts = [{
            'pair': c['pair'],
            'signal_a': f"{c['signal_a']['labels']['tr']} = {c['signal_a']['value']}",
            'signal_b': f"{c['signal_b']['labels']['tr']} = {c['signal_b']['value']}",
            'mekanizma_zaten_biliniyor': bool(c.get('mechanism')),
        } for c in (data.get('signal_conflicts') or [])]

        user_prompt = f"""HESAPLANMIŞ PİYASA REJİMİ: {data.get('regime', 'NEUTRAL')}

BÖLÜM ANALİZLERİ VE SAYISAL DIGEST (yazabileceğin TÜM sayılar burada):
```json
{json.dumps(digest, ensure_ascii=False, indent=2, default=str)}
```

ÇELİŞEN SİNYALLER (deterministik olarak tespit edildi):
{json.dumps(conflicts, ensure_ascii=False, indent=2) if conflicts else "Bu hafta çelişki yok. conflicting_signals: [] dön."}

YANITINI SADECE JSON OLARAK VER."""

        print(f"\n🔶 Pass 2 — yönetici özeti ({models.MODEL.EXEC_SUMMARY})")
        try:
            raw = _call_with_retry(
                EXEC_SUMMARY_SYSTEM_PROMPT, user_prompt, max_tokens=6000,
                schema=EXEC_SUMMARY_SCHEMA, schema_name='exec_summary',
                agent='Pass2/exec', model=models.MODEL.EXEC_SUMMARY)
            return ContentEditorAgent()._parse_response(raw) or {}
        except Exception as e:
            print(f"    ⚠️  Yönetici özeti hatası: {e}")
            return {}


def assemble_weekly(pass_one, pass_two):
    """Fold the two passes into the shape render/weekly.py already reads.

    Notes come from pass 1 (one section, one call, its own data); everything
    above them — the regime line, the overview, the themes, the reconciliations
    — comes from pass 2. Nothing is merged from both, so no field has two
    authors.
    """
    assembled = {}
    for lang in ('tr', 'en'):
        block = pass_two.get(lang) or {}
        themes = []
        for theme in (block.get('themes') or [])[:3]:
            if not isinstance(theme, dict):
                continue
            themes.append({
                'title': theme.get('title', ''),
                # render/weekly.py reads `description`; pass 2 calls it `body`.
                'description': theme.get('body', ''),
                'metric_key': theme.get('metric_key'),
            })

        notes = {}
        for section, analysis in pass_one.items():
            note = analysis.get(lang)
            if isinstance(note, dict):
                notes[section] = {'what': note.get('what', ''),
                                  'so_what': note.get('so_what', '')}

        assembled[lang] = {
            'regime_line': block.get('regime_line', ''),
            'overview': block.get('overview', ''),
            'regime_rationale': block.get('regime_rationale', ''),
            'themes': themes,
            'conflicting_signals': block.get('conflicting_signals') or [],
            'scenarios': block.get('scenarios') or {},
            'notes': notes,
            # Pass 1 has no news-insight call yet; the news section carries its
            # own note instead, and an empty list keeps main.py's
            # length-matching guard from shifting commentary onto wrong
            # headlines.
            'insights': [],
        }
    return assembled


def run_weekly_two_pass(data):
    """The weekly writing layer: pass 1 per section, then one pass 2.

    Returns (assembled, pass_one, digest). The digest goes back to the caller
    because the executive summary's figures are checked against it — that check
    is the only thing standing between the most-quoted paragraph in the report
    and a number nobody printed.
    """
    pass_one = run_pass_one(data)
    if not pass_one:
        return {}, {}, {}

    news_items = NewsTransmissionAgent().analyze(data)
    pass_two = ExecutiveSummaryAgent().analyze(data, pass_one)
    digest = build_digest(pass_one, data)

    assembled = assemble_weekly(pass_one, pass_two)
    for lang in ('tr', 'en'):
        assembled[lang]['news_transmission'] = [
            {'title': item.get('title', ''),
             **(item.get(lang) or {})}
            for item in news_items
        ]
    return assembled, pass_one, digest


NEWS_TRANSMISSION_SYSTEM_PROMPT = """Sen bir makro analistsin. Sana haftanın gerçek haber başlıkları verilir; her biri için haberin piyasaya ULAŞMA ZİNCİRİNİ yazarsın.

Bu bir haber özeti DEĞİLDİR. Okuyucu başlığı zaten gördü. Göremediği şey, olayın onun portföyüne hangi yoldan geldiğidir.

HER HABER İÇİN:
- "index": Sana verilen listedeki sırasını AYNEN kopyala.
- "title": Başlığı kısalt (2-4 kelime, örn: "Hormuz / İran").
- "chain": İletim zinciri, ok işaretiyle. Örnek: "Petrol arzı → enflasyon → faiz → risk varlıkları". En fazla 4 halka.
- "this_week": Zincirin BU HAFTA nerede olduğunu söyleyen tek cümle, İÇİNDE SANA VERİLEN VERİDEN BİR RAKAMLA. Örnek: "Brent 83,55$ (7g -%7,29) — piyasa manşet riskini fiyatlıyor, kalıcı arz şokunu fiyatlamıyor."

KURALLAR:
- Rakam UYDURMA. Sadece sana verilen piyasa verisindeki sayıları kullan; uygun sayı yoksa rakamsız yaz.
- Piyasaya iletim yolu olmayan haberi ATLA — listede o maddeyi hiç döndürme. Genel piyasa yorumu ve listicle haberleri de atla.
- Haber UYDURMA. Sadece sana verilen başlıklar için yaz.
DİL: "tr" ve "en" aynı analizi anlatır; sayılar birebir aynı olmalıdır."""


class NewsTransmissionAgent:
    """Pass 1, news. One call for every headline, in transmission form."""

    CONTEXT_KEYS = ('commodities', 'macro_indicators', 'macro_scoreboard',
                    'fed_pricing', 'economic_calendar')

    def analyze(self, data):
        stories = (data.get('macro_news') or {}).get('news') or []
        if not stories:
            print("    ℹ️  Haber yok — iletim analizi atlanıyor.")
            return []

        headlines = [{'index': i, 'title': n.get('title'),
                      'summary': n.get('summary')}
                     for i, n in enumerate(stories)]
        context = _trim_for_prompt(
            {k: data.get(k) for k in self.CONTEXT_KEYS if data.get(k)},
            edition='weekly')

        user_prompt = f"""HAFTANIN HABERLERİ:
{json.dumps(headlines, ensure_ascii=False, indent=2)}

PİYASA VERİSİ (rakamları SADECE buradan alabilirsin):
```json
{json.dumps(context, ensure_ascii=False, indent=2, default=str)}
```

YANITINI SADECE JSON OLARAK VER."""

        try:
            raw = _call_with_retry(
                NEWS_TRANSMISSION_SYSTEM_PROMPT, user_prompt, max_tokens=3000,
                schema=NEWS_TRANSMISSION_SCHEMA, schema_name='news_transmission',
                agent='Pass1/news_transmission', model=models.MODEL.NEWS_INSIGHT)
            result = ContentEditorAgent()._parse_response(raw) or {}
            items = [i for i in (result.get('items') or []) if isinstance(i, dict)]
            print(f"    ✅ {len(items)}/{len(stories)} haber için iletim zinciri.")
            return items
        except Exception as e:
            print(f"    ⚠️  Haber iletim analizi hatası: {e}")
            return []
