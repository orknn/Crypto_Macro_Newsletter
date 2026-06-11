# render/i18n.py
from datetime import datetime

STR = {
    # Sections
    "section_calendar": {"tr": "Bugünün Takvimi", "en": "Today's Calendar"},
    "section_calendar_weekly": {"tr": "Önümüzdeki Hafta", "en": "Next Week"},
    "section_equities_commodities": {"tr": "Hisseler & Emtialar", "en": "Equities & Commodities"},
    "section_sp500_sectors": {"tr": "S&P 500 Sektörleri", "en": "S&P 500 Sectors"},
    "section_crypto_desk": {"tr": "Kripto Masası", "en": "Crypto Desk"},
    "section_derivatives_desk": {"tr": "Vadeli İşlem Masası", "en": "Derivatives Desk"},
    "section_etf_flows": {"tr": "Spot Bitcoin ETF Akışları", "en": "Spot Bitcoin ETF Flows"},
    "section_watchlist": {"tr": "Kripto İzleme Listesi", "en": "Crypto Watchlist"},
    "section_stories": {"tr": "Öne Çıkan Haberler", "en": "Top Stories"},
    "section_themes": {"tr": "Haftanın Üç Teması", "en": "Three Themes of the Week"},
    "section_liquidity": {"tr": "Likidite Rejimi", "en": "Liquidity Regime"},
    "section_macro_scoreboard": {"tr": "Makro Skor Tahtası", "en": "Macro Scoreboard"},
    "section_stablecoin": {"tr": "Stablecoin Arzı & Payı", "en": "Stablecoin Supply & Share"},
    "section_winners_losers": {"tr": "Haftanın Kazananları & Kaybedenleri", "en": "Winners & Losers of the Week"},
    "section_rotation": {"tr": "Kripto Sektör Rotasyonu", "en": "Crypto Sector Rotation"},
    "section_cycle": {"tr": "Bitcoin Döngü Paneli", "en": "Bitcoin Cycle Panel"},
    "section_correlation": {"tr": "Korelasyon Matrisi", "en": "Correlation Matrix"},
    "section_positioning": {"tr": "Vadeli Yapı & Konumlanma", "en": "Futures Term Structure & Positioning"},
    "section_large_expirations": {"tr": "Büyük Opsiyon Vadeleri", "en": "Large Options Expirations"},
    "section_turkey_desk": {"tr": "Türkiye Masası", "en": "Turkey Desk"},

    # Columns
    "col_date": {"tr": "Tarih", "en": "Date"},
    "col_time": {"tr": "Saat", "en": "Time"},
    "col_event": {"tr": "Gelişme", "en": "Event"},
    "col_country": {"tr": "Ülke", "en": "Country"},
    "col_prev": {"tr": "Önceki", "en": "Prev"},
    "col_cons": {"tr": "Beklenti", "en": "Cons"},
    "col_actual": {"tr": "Açıklanan", "en": "Actual"},
    "col_asset": {"tr": "Varlık", "en": "Asset"},
    "col_price": {"tr": "Fiyat", "en": "Price"},
    "col_1h": {"tr": "1s", "en": "1H"},
    "col_24h": {"tr": "24s", "en": "24H"},
    "col_7d": {"tr": "7g", "en": "7D"},
    "col_30d": {"tr": "30g", "en": "30D"},
    "col_ytd": {"tr": "YTD", "en": "YTD"},
    "col_trend": {"tr": "Trend", "en": "Trend"},
    "col_expiry_date": {"tr": "Vade Tarihi", "en": "Expiry Date"},
    "col_total_notional": {"tr": "Toplam Değer", "en": "Total Notional"},
    "col_max_pain_strike": {"tr": "Maksimum Acı Strike", "en": "Max Pain Strike"},
    "col_sector": {"tr": "Sektör", "en": "Sector Category"},
    "col_7d_avg_return": {"tr": "7g Ortalama Getiri", "en": "7D Basket Avg Return"},

    # Card Labels
    "card_vix": {"tr": "VIX ENDEKSİ", "en": "VIX INDEX"},
    "card_dxy": {"tr": "DOLAR ENDEKSİ (DXY)", "en": "DOLLAR INDEX (DXY)"},
    "card_spread": {"tr": "2s10s MAKAS", "en": "2s10s SPREAD"},
    "card_fng": {"tr": "KORKU & AÇGÖZLÜLÜK", "en": "FEAR & GREED"},
    "card_dominance": {"tr": "BTC DOMİNASYON", "en": "BTC DOMINANCE"},
    "card_mcap": {"tr": "TOPLAM KRİPTO MCAP", "en": "TOTAL MARKET CAP"},
    "card_10y_yield": {"tr": "ABD 10 Yıllık Tahvil", "en": "US 10Y Yield"},
    "card_hy_spread": {"tr": "Yüksek Getirili Kredi Makası", "en": "HY Credit Spread"},
    "card_move": {"tr": "MOVE Endeksi", "en": "MOVE Index"},
    "card_vix_index": {"tr": "VIX Endeksi", "en": "VIX Index"},
    "card_inflation_path": {"tr": "ABD Enflasyon Patikası", "en": "US Inflation Path"},
    "card_net_liquidity": {"tr": "Fed Net Likiditesi", "en": "Fed Net Liquidity"},
    "card_stablecoin_mcap": {"tr": "Stablecoin Toplam Değeri", "en": "Stablecoin Market Cap"},
    "card_mayer_multiple": {"tr": "Mayer Multiple", "en": "Mayer Multiple"},
    "card_200wma_distance": {"tr": "200WMA Mesafe", "en": "200WMA Distance"},
    "card_drawdown": {"tr": "ATH'den Düşüş", "en": "Drawdown from ATH"},
    "card_spot_price": {"tr": "BTC Spot Fiyat", "en": "BTC Spot Price"},
    "card_support": {"tr": "Destek Seviyesi", "en": "Support Level"},
    "card_resistance": {"tr": "Direnç Seviyesi", "en": "Resistance Level"},
    "card_risk_reversal": {"tr": "25Δ Risk Reversal (Aylık)", "en": "25Δ Risk Reversal (Monthly)"},
    "card_max_pain": {"tr": "BTC Max Pain (Çeyreklik)", "en": "BTC Max Pain (Quarterly)"},
    "card_dvol": {"tr": "Deribit DVOL Endeksi", "en": "Deribit DVOL Index"},
    "card_pcr": {"tr": "Options Put/Call Oranı", "en": "Options Put/Call Ratio"},
    "card_etf_flows_title": {"tr": "Spot ETF Günlük Net Akış", "en": "ETF Daily Net Flows"},
    "card_etf_weekly_title": {"tr": "Spot ETF Haftalık Net Akış", "en": "ETF Weekly Net Flows"},
    "card_weekly_total": {"tr": "Haftalık Toplam", "en": "Weekly Total"},
    "card_daily_total": {"tr": "Toplam Akış", "en": "Total Flow"},
    "card_etf_history_title": {"tr": "Spot ETF Akış Geçmişi (Son 10 Gün)", "en": "Spot ETF Flows History (Last 10 Days)"},
    "card_etf_weekly_history_title": {"tr": "Spot ETF Haftalık Net Akış Geçmişi ($ Milyon)", "en": "Bitcoin Spot ETF Weekly Net Flows ($ Millions)"},

    # Signals
    "signal_neutral": {"tr": "● Nötr", "en": "● Neutral"},
    "signal_buying_active": {"tr": "▲ ABD kurumsal alım baskısı aktif", "en": "▲ US buying pressure active"},
    "signal_selling_active": {"tr": "▼ ABD satış baskısı", "en": "▼ US selling pressure"},
    "reading_guide": {"tr": "Okuma Kılavuzu", "en": "Reading Guide"},
    "reading_guide_text": {
        "tr": "Pozitif değerler ABD kurumsal alım baskısını gösterir. Sürekli pozitif premium BTC için yükseliş sinyalidir.",
        "en": "Positive values indicate US institutional buying pressure. Sustained positive premium is a bullish signal for BTC."
    },
    "analyst_note": {"tr": "Analist Notu", "en": "Analyst Note"},
    "outlook_strategy": {"tr": "Haftalık Görünüm & Strateji", "en": "Weekly Outlook & Strategy"},
    
    # Footers
    "bulletin_desc": {"tr": "NOCASHFLOW bültenidir.", "en": "NOCASHFLOW bulletin."},
    "view_on_web": {"tr": "Web'de oku", "en": "Read on Web"},
    "unsubscribe": {"tr": "Abonelikten çık", "en": "Unsubscribe"},
    "language_pref": {"tr": "Dil Tercihi", "en": "Language"},
    "footer_copyright": {"tr": "Tüm hakları saklıdır.", "en": "All rights reserved."},
    "disclaimer": {
        "tr": "Bu belge yalnızca bilgilendirme amaçlıdır ve finansal, yatırım veya hukuki tavsiye niteliği taşımaz. Tüm yatırım kararları risk içerir.",
        "en": "This document is for informational purposes only and does not constitute financial, investment, or legal advice. All investment decisions carry risks."
    },

    # Email Subjects
    "email_subject_daily": {"tr": "Günlük Finans Bülteni - {date}", "en": "Daily Financial Bulletin - {date}"},
    "email_subject_weekly": {"tr": "Haftalık Stratejik Analiz - {date}", "en": "Weekly Deep Dive Bulletin - {date}"},
    
    # Fallback and Labels
    "no_events": {"tr": "Planlanmış gelişme yok", "en": "No scheduled events"},
    "no_asset_data": {"tr": "Varlık verisi mevcut değil", "en": "No asset data available"},
    "no_stories": {"tr": "Bugün derlenmiş haber yok", "en": "No stories compiled today"}
}

def format_bulletin_date(dt, lang):
    """
    Format date object according to language specs.
    TR: 11 Haziran 2026, Perşembe
    EN: Thu, Jun 11 2026
    """
    months_tr = {
        1: "Haziran", 2: "Haziran", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }
    # Wait, 1 is Ocak, 2 is Şubat! Let's write them correctly:
    months_tr = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }
    days_tr = {
        0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
    }
    
    if lang == 'tr':
        day_name = days_tr[dt.weekday()]
        month_name = months_tr[dt.month]
        return f"{dt.day} {month_name} {dt.year}, {day_name}"
    else:
        day_name = dt.strftime("%a")
        month_name = dt.strftime("%b")
        return f"{day_name}, {month_name} {dt.day} {dt.year}"
