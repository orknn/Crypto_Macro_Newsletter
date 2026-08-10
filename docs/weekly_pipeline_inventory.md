# Weekly Bulletin — Pipeline Envanteri (Faz 0)

Statik kod okumasıyla çıkarıldı. Hiçbir pipeline koşusu yapılmadı, hiçbir API
çağrısı gönderilmedi. Rendered değerler için 8 Ağustos 2026 tarihli
`weekly_bulletin_tr.html` artefaktı okundu.

Kapsam: `main.py --edition weekly`. Sadece daily'ye ait yollar (Araştırma
Masası, günlük snapshot, `etf_history_data`) kapsam dışı işaretlendi.

---

## 1. Modül haritası

| Modül | Satır | Rol |
|---|---|---|
| `main.py` | 806 | Orkestrasyon: fetch → validate → regime → LLM → snapshot → kalite kapısı → render → PDF → e-posta |
| `data_fetcher.py` | 2522 | Tüm dış veri çekimi (38 fetcher fonksiyonu) |
| `validators.py` | 347 | İki denetim: `validate_and_sanitize` (aralık) + `validate_ai_numbers` (LLM sayı denetimi) |
| `regime.py` | 122 | Rejim oyu — deterministik, LLM'den önce |
| `agents.py` | 747 | LLM çağrı katmanı + promptlar + `ContentEditorAgent`, `ResearchDeskAgent` |
| `config/llm.py` | 57 | Sağlayıcı/model/fiyat — tek merkez |
| `config/prompt_budget.py` | 71 | Prompt'a giren seri uzunluk capleri |
| `schemas/agent_responses.py` | — | OpenAI strict JSON şemaları |
| `render/weekly.py` | 856 | Weekly HTML montajı (18 bölüm) |
| `render/components.py` | 1047 | Ortak bileşenler + formatters |
| `render/svg.py` | 960 | Tüm grafikler (saf SVG, matplotlib yok) |
| `render/i18n.py` | 217 | TR/EN string tablosu |
| `email_sender.py` | 367 | Resend + D1 abone listesi |
| `tests.py` | 379 | `unittest`, LLM çağrısı yok — T1–T9 buraya eklenebilir |

### Weekly akış sırası (`main.py:315-806`)

```
preload_yfinance_data(37 ticker, period='2y')
  ↓
23 ortak fetcher  (main.py:372-483)
  ↓
14 weekly-özel fetcher  (main.py:521-570)
  ↓
validators.validate_and_sanitize(data)          # 6 metrik, aralık denetimi
  ↓
regime.compute_regime(data)                     # deterministik, modelden ÖNCE
  ↓
ContentEditorAgent().analyze(data, 'weekly')    # ★ TEK LLM ÇAĞRISI
  ↓
validators.validate_ai_numbers(data)            # LLM sayılarını payload'a karşı denetler
  ↓
kalite kapısı (4 kontrol)  →  render_weekly(TR) → PDF → mail
                           →  render_weekly(EN) → PDF → mail
  ↓
ai_report_generator.generate_ai_report()        # özel editör raporu
```

**Kritik gözlem:** Weekly'de snapshot **yazılmıyor** (`main.py:677` —
`if edition == 'daily'`). Yani Faz 3.2'nin "geçen haftanın karnesi" için
gereken kalıcı hafıza weekly tarafında bugün hiç yok. Weekly ayrıca
`calculate_oi_change_from_snapshots(..., edition='weekly')` ile geçen haftanın
daily snapshot'ını **okuyor** ama kendi kaydını bırakmıyor.

---

## 2. Metrik envanteri

`fetch zamanı` sütunu: hiçbir fetcher kendi `as_of` damgasını döndürmüyor.
Tüm değerler "pipeline'ın o satıra geldiği an" ile damgasız çekiliyor;
tabloda serinin **doğal çözünürlüğü** yazılı — gerçek kesim zamanı hiçbir
yerde saklanmıyor. (Faz 1.3'ün asıl işi bu.)

### 2.1 Makro / oran

| Metrik | Kaynak API | Çözünürlük | Dönüşüm | Fail-mode (bugün) | Render |
|---|---|---|---|---|---|
| DXY | yfinance `DX-Y.NYB` | günlük kapanış | son 2 kapanış → % değişim | **`0.0`** (dict ön-dolgusu) | Macro Scoreboard |
| VIX | yfinance `^VIX` | günlük | son 2 kapanış → % | **`0.0`** | Macro Scoreboard |
| 10Y UST | yfinance `^TNX` | günlük | seviye + % değişim | **`0.0`** | Macro Scoreboard |
| 2Y UST | FRED `DGS2` | günlük | seviye + **% değişim** | **`0.0`** | (sadece 2s10s'e girdi) |
| **2s10s spread** | türetilmiş | — | `10Y − 2Y` (seviye, % cinsinden) | `0.0` | Macro Scoreboard — **T3** |
| HY OAS | FRED `BAMLH0A0HYM2` | günlük | son − 6 gün önce, ×100 → bps | **`0.0`** | Macro Scoreboard |
| **MOVE** | yfinance `^MOVE` | günlük | son 2 kapanış → % | **`0.0`** | Macro Scoreboard — **T1** |
| Copper/Gold | yfinance `HG=F` / `GC=F` | günlük | `(Cu/Au)×1000`, 6-gün w/w % | anahtar hiç yazılmaz → `None` | Macro Scoreboard — **T4** |
| 10Y reel getiri | FRED `DFII10` | günlük | seviye + 1h bps | anahtar yok → tile gizlenir | Macro Scoreboard |
| 10Y breakeven | FRED `T10YIE` | günlük | seviye + 1h bps | anahtar yok → tile gizlenir | Macro Scoreboard |
| M2 | FRED `M2SL` | aylık | ÷1000 → $T, MoM % | `0.0` | (scoreboard payload'ı) |
| NFCI | FRED `NFCI` | **haftalık** | seviye + 1h değişim + 3y seri | `None` → bölüm gizlenir | Likidite |
| Fed Net Likidite | FRED `WALCL`, `WTREGEN` + NY Fed RRP | **haftalık** | `WALCL − WTREGEN − RRP`, 3y | `None` → grafik gizlenir | Likidite |
| Global likidite | FRED `WALCL` | haftalık | seviye + 1h/1a % | `None` | (payload) |
| Enflasyon patikası | FRED `CPIAUCSL`, `CPILFESL`, `PCEPILFE` | **aylık** | `pct_change(12)` → YoY | `None` → grafik gizlenir | Macro Scoreboard — **T7** |
| Ekonomik takvim | ForexFactory `ff_calendar_thisweek.json` | olay bazlı | USD/EUR + High/Medium filtre, surprise guard, ilk 15 | eski snapshot'a düşer, `source_date` damgalanır | What's Next — **T7** |
| Fed pricing | FRED `FEDTARMD` + Kalshi `KXFEDDECISION` | olay bazlı | sonraki FOMC + medyan dot + cut-odds | kısmi dict; illikitse cut-odds gizlenir | Takvim şeridi |

### 2.2 Hisse / emtia

| Metrik | Kaynak | Çözünürlük | Dönüşüm | Fail-mode | Render |
|---|---|---|---|---|---|
| Mag 7 (7 hisse) | yfinance | günlük | fiyat + % | `results` kısmi | Equities |
| S&P 500 sektörleri (11 XL*) | yfinance | günlük | fiyat + % | `results` kısmi | Sektör ızgarası |
| Emtia (Au, Ag, Cu, NG, Cocoa, Coffee, Brent) | yfinance | günlük | fiyat + % | `results` kısmi | Commodities |
| BIST 100 / USD/TRY | yfinance `XU100.IS`, `USDTRY=X` | günlük | + türetilmiş `BIST/$` | `results` kısmi; `bist_usd` None ise `—` | Türkiye Masası |
| YTD karşılaştırma | yfinance BTC/NDX/GOLD | günlük | 1 Oca'dan itibaren % | `[]` | YTD grafiği |
| Korelasyon matrisi | yfinance ×5 | günlük | 30g getiri korelasyonu, 5×5 | `None` → bölüm gizlenir | Korelasyon |
| Sparkline'lar | yfinance (cache) | günlük | son 7 kapanış | eksik ticker atlanır | Tablolar |

### 2.3 Kripto

| Metrik | Kaynak | Çözünürlük | Dönüşüm | Fail-mode | Render |
|---|---|---|---|---|---|
| Watchlist (16 varlık) | CoinGecko `/coins/markets` | anlık | fiyat, 1s/24s/7g % | Binance `/ticker/24hr`'a düşer (mcap yok, 7g yok) | Watchlist (mcap top-10) |
| Piyasa geneli | CoinGecko `/global` | anlık | total/total3/dominance | **hepsi `None`** ✅ | Header/payload |
| Fear & Greed | alternative.me | günlük | seviye + sınıf | **`{'value': 50}` uyduruyor** ⚠️ | Gauge + rejim oyu |
| **BTC spot (döngü)** | yfinance `BTC-USD` 5y | **günlük kapanış** | son kapanış | `None` | Döngü paneli — **T8** |
| Mayer / 200WMA / drawdown | yfinance `BTC-USD` 5y | günlük | 200g SMA, 200h MA, ATH | `None` → bölüm gizlenir | Döngü paneli |
| Aylık heatmap | yfinance `BTC-USD` 5y | aylık | ay sonu % | `None` hücre | Döngü paneli |
| Funding (BTC/ETH/SOL) | **Kraken Futures** `/tickers` | anlık | 8s eşdeğerine normalize | kısmi dict | Pozisyonlanma |
| Open Interest | Kraken Futures | anlık | + snapshot'tan w/w delta | `oi_chg_7d=None` → değişim gizlenir | Pozisyonlanma |
| **Futures basis** | Binance spot + `dapi` delivery | anlık | yıllıklandırılmış prim | **`None`** → `—` basılır | Term Structure — **T2** |
| Coinbase premium | Binance klines + Coinbase candles | 1g ×180 | `(CB−BIN)/BIN` %; işaretten sinyal | boş dict | Premium kartı |
| BTC ETF akışı (haftalık) | Farside scrape (`all-data`) | günlük→**W-SUN** | resample sum; ilk+cari hafta atılır | `[]` → bölüm gizlenir | ETF |
| BTC ETF kümülatif | aynı | günlük | cumsum, 120 noktaya seyreltilir | `[]` | ETF |
| ETH ETF akışı | Farside `ethereum-etf-flow-all-data` | günlük→W-SUN | resample sum | `None` → satır gizlenir | ETF |
| Stablecoin arzı | DefiLlama `stablecoincharts` | günlük→haftalık | USDT/USDC pay % | `None` → bölüm gizlenir | Stablecoin |
| Stablecoin anlık | CoinGecko | anlık | USDT+USDC mcap | dict | (payload) |
| ETH/BTC | Binance `ETHBTC` | anlık + 30g | oran + 24s/7g % | `None` → kart gizlenir | Rotasyon |
| Sektör rotasyonu | türetilmiş (`crypto_prices`) | — | kategori 7g ortalaması | **`0.0`** ⚠️ | Rotasyon |
| Kazananlar/kaybedenler | türetilmiş | — | 7g sıralaması ilk/son 5 | `0.0` varsayılan | W&L grafiği |
| Hype radar | CoinGecko `/search/trending` | anlık | ilk 7 | `[]` → bölüm gizlenir | Hype Radar |
| Opsiyon (max pain, P/C, DVOL, 25Δ RR, büyük vadeler) | Deribit v2 | anlık | aşağıda | **`None`** (hepsi birden) | Pozisyonlanma — **T5, T6** |
| Haberler | Finnhub `/news?category=general` | anlık | whitelist+blacklist+skor, max 5 | boş liste → bölüm gizlenir | Stories |

---

## 3. Türetilmiş etiketler — hesaplanan mı, hardcode mu?

| Etiket | Nerede | Durum |
|---|---|---|
| **"büyüme sinyali" / "growth signal"** | `render/weekly.py:225` | 🔴 **HARDCODE.** `{cg_chg:+.2f}% · {STR['growth_signal']}` — oranın yönü ne olursa olsun aynı metin basılıyor. Düşüşte de "büyüme sinyali" der. **T4'ün tam kaynağı.** |
| "ABD satış baskısı" / "ABD alım baskısı" | `render/components.py:940-951` | 🟢 Hesaplanıyor — `current > 0` işaretinden. Doğru. |
| Max pain (vade başına) | `data_fetcher.py:1757-1775` | 🟢 Hesaplanıyor — her strike için toplam acı, minimum seçiliyor. |
| `max_pain_price` (çeyreklik) | `data_fetcher.py` | 🟡 Hesaplanıyor **ama weekly'de hiç render edilmiyor**; sadece payload'da. **T5'in kaynağı.** |
| Futures basis `sentiment` | `data_fetcher.py:420-425` | 🟡 Eşiklerden hesaplanıyor (>12 "Strong Bullish" vb.) ama **hiçbir yerde render edilmiyor** — sadece LLM görüyor. |
| Rejim (RISK_ON/OFF/NEUTRAL) | `regime.py` | 🟢 Deterministik 6-göstergeli oy, ölü bant + min 3 gösterge kuralı. Modelden önce hesaplanıyor, modele girdi olarak veriliyor. |
| F&G sınıfı ("Korku" vb.) | alternative.me | 🟢 Yayıncıdan geliyor, TR'ye map ediliyor. |
| NFCI ipucu ("sıkı/gevşek") | `i18n.py` statik metin | 🟢 Sabit açıklama, veri iddiası yok. |
| Renk sınıfları (`up`/`down`) | `_fmt_change` | 🟢 İşaretten. `|val| < 0.005` ise nötr "● 0.00%". |
| HY OAS renk yönü | `weekly.py:174` | 🟢 Ters çevrilmiş (spread artışı = `down`), doğru. |
| Reel getiri renk yönü | `weekly.py:202` | 🟢 Ters çevrilmiş, doğru. |

---

## 4. LLM çağrıları

### Weekly'de **tek bir** LLM çağrısı var.

| # | Çağrı | Model | max_tokens | Girdi | Ürettiği metin |
|---|---|---|---|---|---|
| 1 | `ContentEditorAgent.analyze(edition='weekly')` | `config/llm.py` → `gpt-5.6-luna`, reasoning `none` | 10 000 (kesilirse ×1.75 = 17 500, tek retry) | `regime` + `news_inputs` (max 5 başlık+özet) + **`_prepare_data_summary(data)`** | Aşağıdaki 14 alanın **TR ve EN kopyası** |

Çıktı alanları (dil başına):
`regime_line`, `overview`, `themes[3]{title,description}`, ve `notes` altında
`liquidity_note`, `inflation_note`, `stablecoin_note`, `etf_note`,
`rotation_note`, `cycle_note`, `correlation_note`, `futures_note`,
`week_plan_note`, `news_note`, artı haber başına `insights[]`.

`ResearchDeskAgent` **sadece daily'de** koşuyor (`main.py:658`) — weekly kapsam dışı.

### Modelin gördüğü girdi (bu redesign'ın merkezindeki sorun)

`_prepare_data_summary` (`agents.py:471`) şunları **çıkarıyor**: `tr`, `en`,
`ai_summary`, `news_commentaries`, legacy notlar, `weekly_themes`, ve weekly'de
ek olarak `etf_flows` + `etf_history_data` (haftalık toplamlarla çelişmesin diye).
`_trim_for_prompt` uzun serileri kısaltıyor (`prompt_budget.py`).

**Geri kalan her şey ham olarak modele gidiyor.** Yani model, bültende
**render edilmeyen** alanları da okuyor ve alıntılıyor:

| Payload'da var, weekly render'ında YOK | Sonuç |
|---|---|
| `options_data.put_call_ratio` | **T6** — "put/call 0,575" notta çıkıyor, raporda karşılığı yok |
| `options_data.max_pain_price` (çeyreklik) | **T5** — not 70.000$ derken tablo 65.000$ gösteriyor (ikisi de "gerçek", farklı vade) |
| `options_data.dvol_index`, `open_interest_btc` | aynı risk |
| `crypto_futures_basis.sentiment` / `.description` | aynı risk |
| `macro_scoreboard.M2`, `M2_chg` | aynı risk |
| `crypto_prices` (16 varlık — tablo 10 gösteriyor) | aynı risk |
| `btc_cycle_metrics.spot` **ve** `crypto_prices[BTC]` | **T8** — iki farklı BTC fiyatı |

Bu, Faz 2.5'in "Pass 2'ye ham veri dump'ı verme" kuralının neden doğru
olduğunun kanıtı: sayı denetimi (`validate_ai_numbers`) bu vakaların
**hiçbirini yakalayamaz**, çünkü sayılar payload'da gerçekten var — sadece
sayfada yok.

### Mevcut LLM denetim katmanı

`validators.validate_ai_numbers` (`validators.py:201`):
- Havuz: payload'daki **tüm** sayılar (AI anahtarları hariç), 4 ondalığa yuvarlanmış
- Metinden regex ile yüzdeleri çeker (TR `%4,68` ve EN `4.68%` biçimlerinin ikisi de)
- Tolerans **mutlak 0.02** — göreli bant bilerek reddedilmiş (yorumda gerekçesi var)
- Eşleşmeyen sayıda: `overview` → boşaltılır + kalite kapısı kırmızıya döner; `notes` → gizlenir; `insights[i]` → `""` (uzunluk korunur); `themes[i]` → düşürülür

Sınırı: **sadece yüzde** işaretli sayıları denetliyor. `$70,000`, `865M`,
`0.575` gibi çıplak sayılar denetim dışı. T5 ve T6 bu yüzden geçti.

### Maliyet

`config/llm.py` → `gpt-5.6-luna`, $0.20/$1.20 per Mtok. Log `logs/cost.jsonl`
+ `fetch_report.json.ai_calls`. Tek çağrı eşiği $0.40 (uyarı).

⚠️ **Faz 2.5 çelişkisi:** brief `gpt-5.6-terra` (varsayılan) + `gpt-5.6-sol`
(tek çağrı) istiyor. Kod bugün **`gpt-5.6-luna`** kullanıyor ve bu 8 Ağustos'ta
bilinçli bir maliyet kararıydı (`04c472f`, aylık $8.41 → ~$0.23). Terra/Sol'e
geçiş bu kararı geri alır. Ayrıca brief "~40 bölüm çağrısı" varsayıyor;
weekly'de bugün **1 çağrı** var — Pass 1'e geçmek çağrı sayısını 1 → ~12'ye
çıkarır. Bu, Faz 2.5'e başlamadan önce senin onayını gerektiren bir kalem
(§7'de soru olarak duruyor).

---

## 5. T1–T9 — kök neden konumları

Her biri kodda tek tek doğrulandı; 8 Ağustos artefaktında da görüldü.

| # | Hata | Kök neden | Dosya:satır |
|---|---|---|---|
| **T1** | MOVE = 0.0 | `results` dict'i `0.0` ile ön-doldurulmuş; fetch hata verirse sentinel kalıyor ve `_val()` onu geçerli float sayıp basıyor | `data_fetcher.py:605-614`, `render/weekly.py:164-166` |
| **T2** | Basis = `—` | Binance `dapi` GitHub runner'da 451 döndü → `spot_res` liste değil dict → `string indices` hatası → fonksiyon `None`, render `—` | `data_fetcher.py:395-435`, `render/weekly.py:693-694` |
| **T3** | 2s10s seviye = değişim | `2s10s_spread` bir **seviye** (10Y−2Y) ama render onu `_fmt_change()`'e veriyor; aynı sayı hem büyük hem küçük satırda | `data_fetcher.py:597`, `render/weekly.py:191-192` |
| **T4** | "büyüme sinyali" sabit | Etiket string tablosundan sabit çekiliyor, `cg_chg` işareti hiç okunmuyor | `render/weekly.py:225` |
| **T5** | max pain 70k vs tablo 65k | Model `max_pain_price` (çeyreklik) görüyor, tablo `large_expirations[].max_pain` (en yakın vade) basıyor | `data_fetcher.py:1800-1805` vs `render/weekly.py:751` |
| **T6** | put/call notta, raporda yok | `put_call_ratio` payload'da var, weekly render'ında hiç kullanılmıyor (sadece `render/daily.py:465`) | `render/weekly.py` (eksik) |
| **T7** | CPI 3.5% vs 3.73% | İki ayrı kaynak + iki ayrı vintage: takvim ForexFactory'nin BLS manşetini, grafik FRED `CPIAUCSL`'den hesaplanan YoY'u gösteriyor. Ayrıca `CPIAUCSL` **mevsimsellikten arındırılmış**; BLS manşet YoY ise NSA (`CPIAUCNS`) serisinden yayınlanır — bu iki sayı tanım gereği eşit olamaz | `data_fetcher.py:2005-2047` vs `973-1160` |
| **T8** | BTC iki fiyat | Watchlist CoinGecko anlık fiyatı, döngü paneli yfinance `BTC-USD` **günlük kapanışı**. Artefaktta $64,959 vs $64,972 | `data_fetcher.py:153` vs `2050` |
| **T9** | "2Y faizi %1,67 yükselirken" | 2Y `_chg` bir **oransal % değişim** (`(son−önceki)/önceki×100`), bps değil; model bunu seviye/bps sanıp cümleye koyuyor. Aynı hata 10Y, VIX, DXY, MOVE için de var | `data_fetcher.py:583`, `563` |

### Envanterin ortaya çıkardığı, brief'te olmayan iki bulgu

**A. Fear & Greed fetch hatası 50 uyduruyor.** `get_fear_and_greed_index`
(`data_fetcher.py:305,308`) hata durumunda `{'value': 50, 'classification':
'Neutral'}` döndürüyor. Bunun üç sonucu var: (1) gauge ölçülmüş gibi 50
basıyor, (2) `regime.py` bu 50'yi gerçek bir nötr oy sayıyor, (3) kalite kapısı
`if not ... .get('value')` kontrolü 50'yi truthy bulduğu için **geçiyor**.
Yani API tamamen ölse bile rapor yeşil koşar. Faz 1.1'in `zero_is_valid` /
`None` kuralı buraya da uygulanmalı — bu bir "0.0 fallback"tan daha sinsi,
çünkü uydurulan değer makul görünüyor.

**B. `calculate_crypto_sector_rotation` boş sektöre `0.0` yazıyor.**
`main.py:186` — bir kategoride hiç fiyat yoksa "ortalama getiri %0.00"
basılıyor. Ölçülmüş bir düz hafta ile veri yokluğu ayırt edilemiyor.

---

## 6. Faz 1 için hazır olan / eksik olan altyapı

| Gereksinim | Durum |
|---|---|
| `MetricSpec` benzeri bir yapı | ❌ Yok. `validate_and_sanitize` 6 metriği elle, gömülü aralıklarla kontrol ediyor |
| `valid_range` | 🟡 6 metrikte var (funding, basis, cb premium, dvol, p/c, 10Y/2Y), 40+ metrikte yok |
| `max_staleness_hours` | ❌ Hiç yok — hiçbir değerin yaşı bilinmiyor |
| `zero_is_valid` | ❌ Yok — ve `0.0` sentinel'leri bu yüzden geçiyor |
| `unit` | ❌ Yok — T3 ve T9'un kökü tam olarak bu |
| N/A render'ı | 🟡 Kısmi: `_val()`, `_fmt_change()`, `_fmt_price()` `None`'da `—` basıyor. Brief `N/A` + gri + tooltip istiyor, `—` istemiyor |
| WARN log + build özeti | 🟡 `fetch_report.json` var ama sadece reddedilenleri yazıyor; `build_report.json` yok |
| Blocklist | ❌ Yok. `maybe()` sadece `None`/`'null'`/boş string'i eliyor |
| Tek `as_of` | ❌ Yok. Header `datetime.now()` basıyor (`components.py:395`) |
| Test altyapısı | ✅ `tests.py` `unittest`, LLM çağrısı yok; T1–T9 buraya girer |
| Weekly snapshot | ❌ Yazılmıyor (Faz 3.2 için gerekli) |

---

## 7. Faz 1'e geçmeden önce senin kararını bekleyen 4 kalem

1. **Türkiye Masası** — brief "karar için bana sor" diyor. Bugün 3 metrik var
   (BIST 100, USD/TRY, BIST $-bazlı). CBRT politika faizi + TR 10Y + CDS + TÜFE
   eklemek **yeni veri kaynağı** demek, ki brief bunu açıkça kapsam dışı
   bırakıyor. Yani seçenekler pratikte: bölümü sil, ya da olduğu gibi bırak.
2. **Model tier'ı** — Terra/Sol'e geçiş 8 Ağustos'taki Luna maliyet kararını
   geri alır ve weekly çağrı sayısını 1 → ~12'ye çıkarır. Onayın gerekiyor.
3. **T7'nin doğru çözümü** — "tek kaynak, tek vintage" için iki yol var:
   (a) takvimin CPI satırını FRED'den besle, (b) grafiği `CPIAUCNS`'e geçirip
   BLS manşetiyle hizala. (b) daha doğru ama grafiğin geçmişi değişir.
4. **`—` mi `N/A` mi** — brief "asla `—`" diyor ama `—` şu an kodda 12 yerde
   bilinçli "veri yok" göstergesi. Hepsini `N/A`'ya çevirmek geniş ama mekanik
   bir değişiklik; onaylıyorsan Faz 1.1'de tek seferde yapılır.

---

*Faz 0 sonu. Kod değişikliği yapılmadı, API çağrısı gönderilmedi.*
