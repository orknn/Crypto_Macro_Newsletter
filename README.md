# 📊 Daily Crypto & Macro Newsletter

Otomatik günlük finans bülteni — Crypto, makro veriler, grafikler ve AI analiz.

**Orkun Biçen** tarafından geliştirilmiştir.

---

## 🚀 Özellikler

- 📈 **Crypto Watchlist**: BTC, ETH, SOL ve 13+ altcoin fiyat/değişim tablosu
- 🌍 **Makro Göstergeler**: VIX, DXY, US 10Y, NASDAQ Futures
- 🏢 **Magnificent 7**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
- 🛢️ **Emtialar**: Altın, Gümüş, Bakır, Petrol, Kahve, Kakao
- 📊 **Grafikler**: Fear & Greed gauge, Coinbase Premium bar chart, makro bar chart
- 💰 **ETF Flows**: Bitcoin & Ethereum ETF giriş/çıkışları
- 🔓 **Token Unlocks**: Yaklaşan token açılım ve yakımları
- 📰 **Makro Haberler**: AI destekli piyasa analizi
- 📧 **Otomatik E-posta**: Her sabah Gmail üzerinden bülten gönderimi

---

## 📁 Proje Yapısı

```
Crypto_Macro_Newsletter/
├── main.py                 # Ana pipeline: veri çekme → HTML → PDF → e-posta
├── data_fetcher.py         # API'lerden veri çekimi (CoinGecko, yfinance, Binance)
├── html_generator.py       # Premium HTML bülten şablonu
├── charting.py             # Matplotlib ile grafik üretimi
├── email_sender.py         # Gmail SMTP ile e-posta gönderimi
├── pdf_generator.py        # PDF oluşturma (eski versiyon)
├── requirements.txt        # Python bağımlılıkları
├── Roboto-Bold.ttf         # Font dosyası
├── Roboto-Regular.ttf      # Font dosyası
└── .github/
    └── workflows/
        └── daily_newsletter.yml  # GitHub Actions cron job
```

---

## 🖥️ Yerel Kurulum

```bash
# 1. Repo'yu klonla
git clone https://github.com/KULLANICI_ADI/Crypto_Macro_Newsletter.git
cd Crypto_Macro_Newsletter

# 2. Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Playwright Chromium yükle (PDF için)
python -m playwright install chromium

# 5. Bülteni oluştur
python main.py

# 6. E-posta ile gönder (opsiyonel)
SEND_EMAIL=true EMAIL_FROM="ornek@gmail.com" EMAIL_PASSWORD="xxxx" EMAIL_TO="alici@gmail.com" python main.py
```

---

## ☁️ GitHub Actions (Otomatik Günlük Çalışma)

Bu repo, GitHub Actions ile her sabah **08:00 (Türkiye saati)** otomatik çalışır.

### GitHub Secrets Ayarlama

GitHub repo sayfasında: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Adı | Değer |
|---|---|
| `EMAIL_FROM` | Gmail adresin (ör: `ornek@gmail.com`) |
| `EMAIL_PASSWORD` | Gmail App Password (aşağıya bak) |
| `EMAIL_TO` | Alıcı e-posta (ör: `alici@gmail.com`) |

### 📱 Gmail App Password Oluşturma

1. [Google Hesap Güvenliği](https://myaccount.google.com/security) sayfasına git
2. **2 Adımlı Doğrulama** açık olmalı (değilse önce aç)
3. [App Passwords](https://myaccount.google.com/apppasswords) sayfasına git
4. **App name** olarak `Newsletter` yaz
5. **Create** butonuna tıkla
6. 16 haneli şifreyi kopyala — bu `EMAIL_PASSWORD` olacak

> ⚠️ **Önemli**: Normal Gmail şifreni kullanma, App Password oluştur!

### Manual Tetikleme

GitHub repo sayfasında: **Actions → Daily Newsletter → Run workflow**

---

## 🔧 Teknolojiler

| Teknoloji | Kullanım |
|---|---|
| Python 3.11 | Ana dil |
| CoinGecko API | Crypto fiyatları |
| yfinance | Hisse, emtia, makro verileri |
| Binance API | Funding rate verileri |
| alternative.me | Fear & Greed Index |
| Matplotlib | Grafik üretimi |
| Playwright | HTML → PDF dönüşümü |
| GitHub Actions | Otomatik zamanlama |
| Gmail SMTP | E-posta gönderimi |

---

## 📜 Lisans

Kişisel kullanım için geliştirilmiştir.
