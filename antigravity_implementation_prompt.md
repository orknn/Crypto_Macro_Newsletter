# nocashflow Bülten Pipeline — Tam Yeniden Yapılandırma Spec'i (v1.0)

> **Hedef repo:** `orknn/Crypto_Macro_Newsletter`
> **Rol:** Kıdemli Python/data engineer olarak çalış. Aşağıdaki spec'i fazlara sadık kalarak, her fazın sonunda çalışır durumda commit'leyerek uygula.
> **Referans tasarımlar:** `design_reference/daily_pulse_demo.html` ve `design_reference/weekly_deepdive_demo.html` — bu iki dosya görsel ve yapısal **tek doğruluk kaynağıdır** (single source of truth). CSS token'ları, bölüm sıralaması, SVG grafik stilleri ve not blokları birebir bu dosyalardan alınacak. (Not: Bu dosyaları repoya `design_reference/` klasörüne ben koyacağım; yoksa benden iste.)

---

## 0 · MUTLAK KURALLAR (her fazda geçerli)

1. **ASLA veri simüle etme.** `random.*` ile üretilen, hardcode edilen veya tahmin edilen hiçbir değer bültene giremez. Bir veri kaynağı başarısız olursa ilgili bölüm/kart **tamamen gizlenir** (`None` → renderer bölümü atlar). "Yaklaşık değer", "son bilinen değer" gibi fallback'ler de yasak — tek istisna: aynı koşudaki bir önceki başarılı snapshot'tan okuma ve bunun bültende `(önceki kapanış)` etiketiyle işaretlenmesi.
2. **Sır yönetimi:** API anahtarları ve e-posta adresleri asla koda yazılmaz. Sadece `os.environ` üzerinden okunur, GitHub Actions'ta `secrets.*` ile beslenir.
3. Her fazın sonunda `python main.py --edition daily --dry-run` hatasız çalışmalı (dry-run: e-posta göndermez, web push yapmaz, sadece HTML üretir).
4. Mevcut çalışan davranışı bozan bir refactor yapacaksan önce ilgili testi yaz, sonra refactor et.
5. Kod yorumları ve commit mesajları İngilizce; bülten içeriği Türkçe (mevcut dil korunur).

---

## FAZ 1 — Veri Bütünlüğü ve Güvenlik Acil Düzeltmeleri

### 1.1 Sahte veri temizliği (`data_fetcher.py`)

| Konum | Sorun | Çözüm |
|---|---|---|
| `get_etf_flows()` | Farside response parse edilmiyor; IBIT/FBTC akışları `random.uniform()` ile üretiliyor | Bkz. §2.4 gerçek parse. Faz 1'de geçici çözüm: parse yoksa `None` dön, bölüm gizlensin |
| Options bloğu | `max_pain_price = 85000 + random.randint(-2000, 2000)` ve `dvol_change_24h` random jitter | Max pain: Deribit `get_book_summary_by_currency(currency=BTC, kind=option)` çıktısından, en yakın **çeyrek vade** için strike bazında `sum(call_OI*max(0,S-K) + put_OI*max(0,K-S))`'yi minimize eden K. DVOL 24h değişimi: `public/get_volatility_index_data` (resolution=3600, son 24 nokta) ilk/son farkı |
| Coinbase Premium fallback | API hatasında random walk üretiyor | Fallback'i sil; hata → `None` → bölüm gizlenir |
| Takvim fallback'i | `forecast='1.0%'` gibi hardcode değerler | Fallback takviminde forecast/previous alanları boş (`—`) gösterilir, asla sayı uydurulmaz |
| PMI | FRED `NAPM` serisi kaldırılmış, `ISM/NMI` geçersiz ID → her gün hardcode 49.5 basılıyor | PMI'ı scoreboard'dan **tamamen çıkar**. (İleride ForexFactory takviminden ISM actual'ı yakalanırsa geri eklenebilir — şimdilik kapsam dışı) |
| 2Y tahvil | `'US 2-Year Treasury Yield': '^IRX'` — ^IRX 13 haftalık T-bill'dir, 2Y değil | FRED `DGS2` serisine geç (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2`). 2s10s spread = DGS10 − DGS2 olarak yeniden hesapla |
| Kraken funding | `fundingRatePrediction` saatlik; Binance 8h ile karşılaştırılamaz, yanıltıcı | Saatlik oranı ×8 ile **8h-eşdeğerine** normalize et; UI etiketine "(8h eşd.)" ekle. `oi_chg_24h` hesaplanamıyorsa alanı kaldır |

### 1.2 Workflow secret bug'ı (`.github/workflows/daily_bulletin.yml`)
- Workflow env'de `OPENAI_API_KEY` tanımlı, ancak `agents.py` `ANTHROPIC_API_KEY` okuyor → AI agent'lar CI'da sessizce hiç çalışmıyor.
- Düzelt: `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` ekle, OPENAI satırını sil.
- `agents.py`'de anahtar yoksa **sessiz atlama yerine** log'a açık WARNING yaz ve bülten başlığının altına görünmez HTML yorumu ekle: `<!-- AI sections skipped: no API key -->`.

### 1.3 Abone listesi ve e-posta uyumluluğu (`email_sender.py`)
- `SUBSCRIBERS` listesindeki kişisel e-postaları koddan sil.
- Geçiş çözümü: `SUBSCRIBERS` env değişkeni (virgülle ayrılmış, GitHub Secret). Hedef çözüm: **Resend Audiences + Broadcasts** API'sine geç (`audiences` endpoint'i ile liste yönetimi, broadcast ile gönderim — unsubscribe otomatik yönetilir).
- Her e-postaya `List-Unsubscribe` ve `List-Unsubscribe-Post` header'ları ekle (Resend `headers` parametresi).
- E-posta gövdesi: PDF eki yerine kısa özet + "Bülteni web'de oku" CTA linki (siteye push edilen HTML'e). PDF üretimi web arşivi için devam edebilir ama eke konmaz.
- **Git geçmişi temizliği YAPMA** (force-push riski) — bunun yerine README'ye not düş; geçmiş temizliğini repo sahibi manuel yapacak.

### 1.4 Ölü kod ve bağımlılıklar
- Sil: `charting.py` (main'den import edilmiyor), `design_preview.html`, `design_preview_generator.py` (edition mimarisiyle gereksizleşiyor).
- `requirements.txt`'ten çıkar: `investpy`, `schedule`, `matplotlib`, `numpy` (kullanım kalmadıysa). Tüm bağımlılıkları sürüm pinle (`package==x.y.z`).
- Haber görsellerinin **base64 gömülmesini kaldır** — `<img src="{url}">` olarak doğrudan kaynak URL kullan, `loading="lazy"` ekle. (Faz 2'de Finnhub'a geçince zaten URL gelecek.)
- README'yi gerçek mimariye göre yeniden yaz (Resend, mevcut dosyalar, kurulum, secrets listesi).
- `ExperienceDesignerAgent`'ı günlük akıştan çıkar (token israfı); kodu sil ya da `--design-review` flag'i arkasına al.

**Faz 1 kabul kriteri:** Repo'da `grep -rn "random\." --include="*.py"` çıktısında veri üreten tek satır kalmamalı; `daily` dry-run'da ETF/options bölümleri ya gerçek veriyle ya da hiç görünmemeli.

---

## FAZ 2 — Veri Kaynağı Değişiklikleri ve Eklemeleri

### 2.1 Haberler: Cointelegraph RSS → Finnhub
- Endpoint: `GET https://finnhub.io/api/v1/news?category={general|crypto}&token=$FINNHUB_API_KEY`
- Günlük bülten: `general`'dan 1 + `crypto`'dan 2 başlık (en güncel, `headline` dedupe). Haftalık: her kategoriden 3'er, hafta içinden.
- Dönen alanlar: `headline, summary, source, url, image, datetime`. Görsel: URL olarak kullan (base64 yok).
- AI Insight üretimi mevcut agent akışında kalır; prompt'a haber `summary`'si beslenir.
- Rate limit: ücretsiz tier 60 çağrı/dk — sorun değil, retry'lı tek çağrı yeterli.
- Cointelegraph RSS kodunu **fallback** olarak tut (Finnhub down ise), ama görselsiz.

### 2.2 FRED ek serileri (anahtar gerekmez, `fredgraph.csv?id=` pattern'i mevcut)
| Seri | Kullanım |
|---|---|
| `DGS2` | Gerçek 2Y yield; 2s10s spread |
| `WALCL` (mevcut) + `WTREGEN` + `RRPONTSYD` | **Net Liquidity = WALCL − WTREGEN − RRPONTSYD**. Haftalık bültenin hero grafiği; 3 yıllık seri çek, haftalık frekansa indir |
| `M2SL` (mevcut) | Seviye değil **YoY % değişim** olarak hesapla; 5 yıllık seri |
| `CPIAUCSL`, `CPILFESL`, `PCEPILFE` | Enflasyon Patikası grafiği: üçünün YoY %'si, 5 yıl |
| `BAMLH0A0HYM2` | HY OAS (kredi spread) — Macro Scoreboard kartı, w/w bp değişimi |

### 2.3 Yeni kaynaklar
- **DefiLlama (ücretsiz, anahtarsız):**
  - `GET https://stablecoins.llama.fi/stablecoincharts/all` → toplam stablecoin mcap tarihsel serisi (3 yıl) + `GET /stablecoins?includePrices=true` → USDT/USDC güncel mcap → pay savaşı grafiği için iki seri türet (peggedUSD kırılımı tarihsel endpoint'lerde mevcut; USDT id=1, USDC id=2: `/stablecoincharts/all?stablecoin={id}`).
  - Token unlocks: `https://api.llama.fi/api/emissions` listesi ağırsa, haftalıkta sadece watchlist token'ları (SUI, ARB, JUP vb.) için `https://api.llama.fi/emission/{protocol}` çek; önümüzdeki 7 günün unlock'larını $ değeriyle tablola. Endpoint şemasını koddan önce `curl` ile doğrula; uymuyorsa bölümü gizle (uydurma yok).
- **MOVE endeksi:** yfinance `^MOVE` (kapanış + w/w). Veri gelmezse kartı gizle.
- **CoinGecko categories:** `GET /api/v3/coins/categories` → `market_cap_change_24h` yerine 7d için kategori sayfası yoksa: kategori başına temsilci sepet (L1: ETH/SOL/AVAX, DeFi: UNI/AAVE/LINK, AI: RNDR/TAO/FET, Meme: DOGE/PEPE/SHIB, Privacy: ZEC/XMR, RWA: ONDO/LINK) tanımla ve 7d ortalamasını watchlist verisinden hesapla — bu yöntem deterministik ve API'siz, tercih edilen budur.
- **Farside ETF parse (gerçek):** `cloudscraper` ile `https://farside.co.uk/btc/` çek, `pandas.read_html` ile tabloyu al; son satır = bugünün akışları, kolon başlıklarından IBIT/FBTC/GBTC/Total eşle. 10 günlük seri için son 10 satır. Parse başarısızsa bölüm gizlenir. `pandas` zaten dependency; `lxml` ekle.

### 2.4 yfinance batch refactor
- ~30 tekil `yf.download` çağrısını grupla: tek `yf.download(tickers=[...], period='35d', interval='1d', group_by='ticker', threads=True)` (genel varlıklar) + haftalık için `period='2y'` ikinci batch (YTD/uzun seriler).
- Sparkline'lar için her ticker'ın son 8 kapanışını snapshot'a yaz.

### 2.5 Snapshot katmanı (yeni: `snapshots/`)
- Her **günlük** koşu, tüm ham çekilen veriyi `snapshots/YYYY-MM-DD.json` olarak repoya commit eder (workflow'daki mevcut push adımına eklenir).
- **Haftalık** koşu: haftalık değişimleri, 7g ortalama funding'i, ETF haftalık toplamlarını ve kazanan/kaybeden sıralamasını mümkün olduğunca son 7 snapshot'tan türetir; eksik gün varsa API'den tamamlar.
- Şema: düz JSON, en üst seviyede `{"date", "tickers": {...}, "crypto": {...}, "macro": {...}, "derivatives": {...}, "etf": {...}, "news": [...]}`. Şemayı `schemas/snapshot.schema.json` olarak yaz ve koşu sonunda doğrula.

**Faz 2 kabul kriteri:** Dry-run çıktısındaki her sayı, log'da kaynağı ve timestamp'iyle izlenebilir olmalı (`fetch_report.json`: hangi kaynak başarılı/başarısız/süre).

---

## FAZ 3 — Edition Mimarisi ve Yeni Şablonlar

### 3.1 Dosya yapısı
```
main.py                      # --edition daily|weekly --dry-run --no-email --no-push
config/editions.py           # edition başına: bölüm listesi, başlık, accent, no sayacı
data_fetcher.py              # ortak (Faz 2 sonrası hali)
render/
  tokens.py                  # renk+font token'ları (referans HTML'lerdeki :root birebir)
  svg.py                     # sparkline, bar_chart, line_chart, hbar_rows,
                             # momentum_bar, month_heatmap, corr_matrix
  components.py              # header, ticker, regime_strip, section, card grid,
                             # asset_table, calendar_table, story, block_divider, footer
  daily.py                   # günlük bölüm sıralaması (aşağıda)
  weekly.py                  # haftalık bölüm sıralaması (aşağıda)
agents.py                    # edition'a özel promptlar (aşağıda)
email_sender.py              # Resend broadcast
snapshots/                   # Faz 2
design_reference/            # onaylı iki demo HTML (dokunma, sadece referans)
.github/workflows/daily.yml  # mevcut cron (05:45 UTC, hafta içi+sonu)
.github/workflows/weekly.yml # Pazar 16:00 UTC
```

### 3.2 Bölüm sıralaması — **referans HTML'lerle birebir aynı olacak**

**DAILY (sıra kesin):** header → regime strip (genel piyasa dili) → ticker 8'li (NASDAQ, DXY, GOLD, 10Y, VIX, BRENT, BTC, ETH; her birinde 7g sparkline) → Market Overview (AI; makro önce, kripto sonda) → Bugünün Takvimi (bugün+yarın) → Equities & Commodities (Mag7 + Commodities tabloları, momentum bar 24s) → **KRİPTO MASASI ayraç** → Key Metrics (mcap, BTC.D, F&G) → Derivatives Desk (funding 8h-eşd., OI, 3M basis, DVOL, PCR, max pain + Coinbase Premium 24h bar grafiği) → Spot BTC ETF Flows (3 kart + 10g bar) → Crypto Watchlist (16 coin, 1s/24s/7g + momentum) → Top Stories (3; makro haber ilk sırada) → footer.

**WEEKLY (sıra kesin):** header → Haftanın Üç Teması (sıra: jeopolitik/makro → likidite → kripto) → Likidite Rejimi (Net Liquidity 3y + kartlar + M2 YoY 5y) → Macro Scoreboard (DXY, 10Y, 2s10s, HY OAS, MOVE, VIX) + Enflasyon Patikası 5y (CPI/Core/PCE + %2 hedef çizgisi) → Equities & Commodities (7g/30g/YTD + momentum 7g) → S&P 500 Sektör Haritası → BTC vs NDX vs GOLD YTD → Türkiye Masası (BIST, USD/TRY, $ bazlı BIST) → **KRİPTO MASASI ayraç** → Stablecoin Supply (toplam 3y + USDT vs USDC pay savaşı 3y) → ETF Haftalık Net Akış (bar + 3 kart) → Kazananlar/Kaybedenler (5+5 yatay bar) → Crypto Watchlist (7g/30g/YTD/ATH↓ + momentum) → Kripto Sektör Rotasyonu → Döngü Paneli (Mayer Multiple, 200WMA mesafesi, zirveden uzaklık + aylık getiri heatmap'i 2024-2026) → Korelasyon Matrisi (BTC/NDX/GOLD/DXY/10Y, 30g rolling, günlük getiriler — `pandas.corr` ile gerçekten hesapla) → Vadeli Yapı & Konumlanma (funding 7g ort., 1M/3M basis, DVOL ort., 25Δ risk reversal, OI w/w + büyük opsiyon vadeleri tablosu) → Önümüzdeki Hafta (takvim + token unlocks + hafta planı notu) → footer.

Hesaplama notları:
- Mayer Multiple = spot / 200 günlük SMA; 200WMA = haftalık kapanışların 200'lük SMA'sı (yeterli geçmiş yoksa günlük×7 yaklaşımı kullanma — CoinGecko `market_chart?days=max` ile gerçek seri çek).
- Aylık heatmap: BTC aylık kapanış getirileri, son 3 takvim yılı; içinde bulunulan ay `*` ile işaretli.
- 25Δ risk reversal: Deribit book summary'den en yakın aylık vadede 25-delta call IV − 25-delta put IV (delta'sı 0.25'e en yakın strike'lar); hesaplanamıyorsa kartı gizle.

### 3.3 AI agent promptları (`agents.py`)
- Tek model çağrısı/edition (mevcut iki ayrı agent'ı birleştir, maliyet düşer). Model: `claude-sonnet-4-5` yerine repo'da hangisi tanımlıysa onu koru; `max_tokens` 1500.
- **Daily prompt:** snapshot JSON'unu ver; çıktı: (a) regime kelimesi `RISK-ON|NEUTRAL|RISK-OFF` + tek cümle, (b) 4-5 cümlelik Market Overview (makro→kripto sırası), (c) 3 haber için 1'er cümle AI Insight. Çıktıyı **katı JSON** iste, parse et; parse hatasında bölümler gizlenir, asla yarım metin basılmaz.
- **Weekly prompt:** son 7 snapshot özeti + haftalık türetilmiş metrikler; çıktı: 3 tema (başlık ≤2 kelime + 2-3 cümle), her ana bölüm için 1-2 cümlelik "not" metni (likidite, enflasyon, stablecoin, ETF, rotasyon, döngü, korelasyon, vadeli yapı, hafta planı). Aynı katı JSON kuralı.
- Promptlara talimat ekle: "Sana verilen sayılar dışında hiçbir sayı kullanma."

### 3.4 Workflow'lar
- `daily.yml`: mevcut cron korunur; adımlar: checkout → setup-python (pip cache) → install → `python main.py --edition daily` → snapshot+HTML commit/push → Resend broadcast. `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`, `RESEND_API_KEY` secrets.
- `weekly.yml`: `cron: '0 16 * * 0'` (Pazar 16:00 UTC); aynı adımlar `--edition weekly`.
- Web push hedefi: site reposuna `bulletins/daily/YYYY-MM-DD.html` ve `bulletins/weekly/YYYY-Www.html` olarak **tarihli arşiv** + `latest` kopyası.

### 3.5 E-posta uyumluluğu
- Web HTML zengin kalır (SVG + flex). E-posta gövdesi ayrı, sade şablondur: logo, tarih, regime satırı, AI overview metni, 3-4 ana metrik **tablo-bazlı** satır, "Web'de oku" butonu, unsubscribe. SVG ve flex e-posta gövdesinde kullanılmaz.

**Faz 3 kabul kriteri:** (1) `--edition daily` ve `--edition weekly` dry-run çıktıları, `design_reference/` dosyalarıyla yan yana açıldığında bölüm sırası ve görsel dil birebir eşleşmeli (veriler farklı olacak, yapı aynı). (2) Mobil (390px) ekran görüntüsünde ticker 2 kolon, tablolar taşmasız. (3) Tüm koşu uçtan uca <5 dk.

---

## TEST PLANI
1. `pytest` ile: snapshot şema doğrulaması, net liquidity hesabı (bilinen 3 FRED değeriyle), Mayer Multiple, max pain (sentetik küçük opsiyon kitabıyla), funding normalizasyonu, AI JSON parser (bozuk çıktı senaryosu dahil).
2. Her fetch fonksiyonu için "API down" senaryosu: bölümün HTML'de hiç görünmediğini assert et.
3. CI'da PR başına `--dry-run` smoke test workflow'u ekle (`pull_request` trigger).

## GEREKLİ SECRETS (repo sahibi ekleyecek)
`ANTHROPIC_API_KEY` · `FINNHUB_API_KEY` · `RESEND_API_KEY` · `WEBSITE_PUSH_TOKEN` (fine-grained, sadece site reposu contents yetkisi) · geçiş dönemi için `SUBSCRIBERS`

## YAPMA LİSTESİ
- Veri uydurma/simülasyon yok (Kural 1).
- Git geçmişine force-push yok.
- Referans HTML'lerin tasarım token'larını "iyileştirme" yok — birebir uygula.
- Yeni ücretli API ekleme yok; tüm kaynaklar ücretsiz tier.
- Kapsam dışı: aylık edition, premium abonelik, site tarafı değişiklikleri.
