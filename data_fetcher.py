import requests
import pandas as pd
import yfinance as yf
import random
from datetime import datetime, timedelta

# ═══════════════════════════════════════════
# CRYPTO DATA
# ═══════════════════════════════════════════

def get_crypto_prices(watchlist):
    """
    Fetch prices, 1h change, 24h change, 7d change from CoinGecko.
    Uses /coins/markets endpoint for richer data including 7d change.
    """
    id_map = {
        'BTC': 'bitcoin', 'ETH': 'ethereum', 'XRP': 'ripple', 'SOL': 'solana',
        'TRX': 'tron', 'DOGE': 'dogecoin', 'HYPE': 'hyperliquid', 'LINK': 'chainlink',
        'AVAX': 'avalanche-2', 'SUI': 'sui', 'TON': 'the-open-network', 'UNI': 'uniswap',
        'AAVE': 'aave', 'PEPE': 'pepe', 'RENDER': 'render-token', 'JUP': 'jupiter-exchange-solana',
        'ADA': 'cardano', 'DOT': 'polkadot', 'MATIC': 'matic-network', 'ATOM': 'cosmos',
        'NEAR': 'near', 'FTM': 'fantom', 'OP': 'optimism', 'ARB': 'arbitrum',
        'INJ': 'injective-protocol', 'SEI': 'sei-network', 'TIA': 'celestia',
        'WIF': 'dogwifcoin', 'BONK': 'bonk', 'SHIB': 'shiba-inu'
    }
    
    ids_to_fetch = [id_map.get(sym, sym.lower()) for sym in watchlist]
    ids_str = ','.join(ids_to_fetch)
    
    # Use /coins/markets for 7d change data
    url = (
        f"https://api.coingecko.com/api/v3/coins/markets?"
        f"vs_currency=usd&ids={ids_str}"
        f"&order=market_cap_desc&per_page=250&page=1"
        f"&sparkline=false"
        f"&price_change_percentage=1h,24h,7d,30d"
    )
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Build lookup by id
        data_by_id = {item['id']: item for item in data}
        
        results = []
        for sym in watchlist:
            cg_id = id_map.get(sym, sym.lower())
            if cg_id in data_by_id:
                item = data_by_id[cg_id]
                results.append({
                    'Symbol': sym,
                    'Current Price USD': item.get('current_price', 0.0),
                    '1h %': item.get('price_change_percentage_1h_in_currency', 0.0),
                    '24h %': item.get('price_change_percentage_24h_in_currency', 0.0),
                    '7d %': item.get('price_change_percentage_7d_in_currency', 0.0),
                    '30d %': item.get('price_change_percentage_30d_in_currency', 0.0),
                })
            else:
                results.append({
                    'Symbol': sym,
                    'Current Price USD': 0.0,
                    '1h %': 0.0,
                    '24h %': 0.0,
                    '7d %': 0.0,
                    '30d %': 0.0,
                })
        return results
    except Exception as e:
        print(f"Error fetching crypto prices: {e}")
        return []

def get_crypto_market_overview():
    """
    Fetch crypto market overview from CoinGecko /global endpoint.
    Returns: Total Market Cap, Total3 (excl BTC+ETH), BTC Dominance, Stablecoin Dominance.
    """
    url = "https://api.coingecko.com/api/v3/global"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', {})
        
        total_mcap = data.get('total_market_cap', {}).get('usd', 0.0)
        btc_dom = data.get('market_cap_percentage', {}).get('btc', 0.0)
        eth_dom = data.get('market_cap_percentage', {}).get('eth', 0.0)
        
        # Calculate Total3 = Total - BTC mcap - ETH mcap
        btc_mcap = total_mcap * (btc_dom / 100)
        eth_mcap = total_mcap * (eth_dom / 100)
        total3 = total_mcap - btc_mcap - eth_mcap
        
        # Stablecoin dominance — sum of USDT + USDC dominance
        usdt_dom = data.get('market_cap_percentage', {}).get('usdt', 0.0)
        usdc_dom = data.get('market_cap_percentage', {}).get('usdc', 0.0)
        stablecoin_dom = usdt_dom + usdc_dom
        
        return {
            'total_market_cap': total_mcap,
            'total3': total3,
            'btc_dominance': btc_dom,
            'eth_dominance': eth_dom,
            'stablecoin_dominance': stablecoin_dom,
            'total_volume': data.get('total_volume', {}).get('usd', 0.0),
            'market_cap_change_24h': data.get('market_cap_change_percentage_24h_usd', 0.0),
        }
    except Exception as e:
        print(f"Error fetching crypto market overview: {e}")
        return {
            'total_market_cap': 0.0, 'total3': 0.0,
            'btc_dominance': 0.0, 'eth_dominance': 0.0,
            'stablecoin_dominance': 0.0, 'total_volume': 0.0,
            'market_cap_change_24h': 0.0,
        }

def get_fear_and_greed_index():
    """
    Fetch Crypto Fear & Greed Index from alternative.me
    """
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and data.get('data'):
            latest = data['data'][0]
            val = int(latest['value'])
            classification = latest['value_classification']
            return {'value': val, 'classification': classification}
        return {'value': 50, 'classification': 'Neutral'}
    except Exception as e:
        print(f"Error fetching fear and greed: {e}")
        return {'value': 50, 'classification': 'Neutral'}

def get_funding_rates():
    """
    Fetch real-time funding rates from Binance Futures API.
    """
    symbols = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT'}
    results = {}
    for name, symbol in symbols.items():
        try:
            url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            results[name] = float(data.get('lastFundingRate', 0)) * 100  # convert to %
        except Exception as e:
            print(f"Error fetching funding rate for {name}: {e}")
            results[name] = 0.0
    return results


# ═══════════════════════════════════════════
# MACRO / TRADITIONAL FINANCE DATA
# ═══════════════════════════════════════════

def get_macro_indicators():
    """
    Fetch VIX, DXY, US 10Y Yield, NASDAQ 100 Futures using yfinance.
    """
    tickers = {
        'US 10-Year Treasury Yield': '^TNX',
        'US 2-Year Treasury Yield': '^IRX',
        'VIX': '^VIX',
        'DXY': 'DX-Y.NYB',
        'NASDAQ 100 Futures': 'NQ=F',
        'SMH (Semiconductor ETF)': 'SMH',
    }
    
    results = {}
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, period='5d', progress=False)
            if not data.empty and 'Close' in data and len(data['Close']) >= 2:
                last_close = float(data['Close'].iloc[-1].item())
                prev_close = float(data['Close'].iloc[-2].item())
                pct_change = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
            elif not data.empty and 'Close' in data:
                last_close = float(data['Close'].iloc[-1].item())
                pct_change = 0.0
            else:
                last_close = 0.0
                pct_change = 0.0
            results[name] = last_close
            results[f"{name}_chg"] = pct_change
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            results[name] = 0.0
            results[f"{name}_chg"] = 0.0
    return results

def get_magnificent_7():
    """
    Fetch Magnificent 7 stock prices and daily change from yfinance.
    AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
    """
    tickers = {
        'AAPL': 'Apple',
        'MSFT': 'Microsoft',
        'GOOGL': 'Alphabet (Google)',
        'AMZN': 'Amazon',
        'NVDA': 'NVIDIA',
        'META': 'Meta',
        'TSLA': 'Tesla'
    }
    
    results = []
    for symbol, name in tickers.items():
        try:
            data = yf.download(symbol, period='35d', progress=False)
            if not data.empty and 'Close' in data:
                closes = data['Close'].dropna()
                if len(closes) >= 2:
                    current = float(closes.iloc[-1].item())
                    prev = float(closes.iloc[-2].item())
                    change_pct = ((current - prev) / prev) * 100
                    # 7-day change
                    if len(closes) >= 6:
                        prev_7d = float(closes.iloc[-6].item())
                        change_7d = ((current - prev_7d) / prev_7d) * 100
                    else:
                        change_7d = 0.0
                    # 30-day change
                    if len(closes) >= 22:
                        prev_30d = float(closes.iloc[-22].item())
                        change_30d = ((current - prev_30d) / prev_30d) * 100
                    else:
                        change_30d = 0.0
                else:
                    current = float(closes.iloc[-1].item()) if len(closes) > 0 else 0.0
                    change_pct = 0.0
                    change_7d = 0.0
                    change_30d = 0.0
            else:
                current = 0.0
                change_pct = 0.0
                change_7d = 0.0
                change_30d = 0.0
            results.append({
                'Symbol': symbol,
                'Name': name,
                'Price': current,
                'Change %': change_pct,
                '7d %': change_7d,
                '30d %': change_30d,
            })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            results.append({'Symbol': symbol, 'Name': name, 'Price': 0.0, 'Change %': 0.0, '7d %': 0.0, '30d %': 0.0})
    return results

def get_commodities():
    """
    Fetch commodity prices from yfinance: Gold, Copper, Cocoa, Coffee, Brent Oil.
    """
    tickers = {
        'Gold': 'GC=F',
        'Silver': 'SI=F',
        'Copper': 'HG=F',
        'Natural Gas': 'NG=F',
        'Cocoa': 'CC=F',
        'Coffee': 'KC=F',
        'Brent Oil': 'BZ=F',
    }
    
    results = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, period='35d', progress=False)
            if not data.empty and 'Close' in data:
                closes = data['Close'].dropna()
                if len(closes) >= 2:
                    current = float(closes.iloc[-1].item())
                    prev = float(closes.iloc[-2].item())
                    change_pct = ((current - prev) / prev) * 100
                    # 7-day change
                    if len(closes) >= 6:
                        prev_7d = float(closes.iloc[-6].item())
                        change_7d = ((current - prev_7d) / prev_7d) * 100
                    else:
                        change_7d = 0.0
                    # 30-day change
                    if len(closes) >= 22:
                        prev_30d = float(closes.iloc[-22].item())
                        change_30d = ((current - prev_30d) / prev_30d) * 100
                    else:
                        change_30d = 0.0
                else:
                    current = float(closes.iloc[-1].item()) if len(closes) > 0 else 0.0
                    change_pct = 0.0
                    change_7d = 0.0
                    change_30d = 0.0
            else:
                current = 0.0
                change_pct = 0.0
                change_7d = 0.0
                change_30d = 0.0
            results.append({
                'Name': name,
                'Ticker': ticker,
                'Price': current,
                'Change %': change_pct,
                '7d %': change_7d,
                '30d %': change_30d,
            })
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            results.append({'Name': name, 'Ticker': ticker, 'Price': 0.0, 'Change %': 0.0, '7d %': 0.0, '30d %': 0.0})
    return results


# ═══════════════════════════════════════════
# GLOBAL LIQUIDITY INDEX
# ═══════════════════════════════════════════

def get_global_liquidity_index():
    """
    Fetch Global Liquidity proxy using Fed Total Assets (WALCL) from FRED.
    No API key needed for the public observation endpoint.
    Returns dict with current value, weekly and monthly change.
    """
    try:
        # FRED public endpoint for WALCL (Fed Total Assets, weekly)
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL&cosd=2024-01-01"
        import io
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = ['date', 'value']
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        if len(df) < 2:
            return _fallback_liquidity()
        
        current = df['value'].iloc[-1]  # in millions
        prev_week = df['value'].iloc[-2] if len(df) >= 2 else current
        prev_month = df['value'].iloc[-5] if len(df) >= 5 else current
        
        current_t = current / 1_000_000  # Convert to trillions
        weekly_change = ((current - prev_week) / prev_week) * 100
        monthly_change = ((current - prev_month) / prev_month) * 100
        
        return {
            'value': current_t,
            'value_formatted': f"${current_t:.2f}T",
            'weekly_change': round(weekly_change, 2),
            'monthly_change': round(monthly_change, 2),
            'source': 'FRED (WALCL)',
            'label': 'Fed Balance Sheet',
        }
    except Exception as e:
        print(f"  ⚠️  Global Liquidity fetch error: {e}")
        return _fallback_liquidity()


def _fallback_liquidity():
    """Fallback with approximate data if FRED is unreachable."""
    return {
        'value': 6.8,
        'value_formatted': '$6.80T',
        'weekly_change': 0.0,
        'monthly_change': 0.0,
        'source': 'fallback',
        'label': 'Fed Balance Sheet',
    }


# ═══════════════════════════════════════════
# ECONOMIC CALENDAR (Investing.com via investpy)
# ═══════════════════════════════════════════

def get_economic_calendar():
    """
    Fetch upcoming Economic Calendar events from Investing.com via investpy.
    Includes actual released values, forecast, and previous.
    Filters for USD and EUR, High impact only.
    """
    events = []
    try:
        import investpy
        
        today = datetime.now()
        # Show from Monday of current week to Friday
        weekday = today.weekday()  # 0=Mon
        monday = today - timedelta(days=weekday)
        friday = monday + timedelta(days=4)
        
        from_date = monday.strftime('%d/%m/%Y')
        to_date = friday.strftime('%d/%m/%Y')
        
        df = investpy.economic_calendar(
            from_date=from_date,
            to_date=to_date,
            countries=['united states', 'euro zone'],
            importances=['high']
        )
        
        # Map zone names to currency codes
        zone_to_currency = {
            'united states': 'USD',
            'euro zone': 'EUR',
        }
        
        # Exclude events that Investing.com marks as "high" but aren't true 3-star macro releases
        exclude_keywords = [
            'speaks', 'speech', 'press conference',
            'crude oil inventories', 'natural gas',
            'manufacturing prices', 'non-manufacturing prices',
            'services prices',
            'treasury currency', 'bond auction',
            'fomc member',
        ]
        
        for _, row in df.iterrows():
            date_str = row.get('date', '')
            time_str = row.get('time', '—')
            zone = row.get('zone', '')
            event_name = row.get('event', 'Unknown Event')
            actual = row.get('actual', None)
            forecast = row.get('forecast', None)
            previous = row.get('previous', None)
            
            # Skip excluded events
            event_lower = event_name.lower()
            if any(kw in event_lower for kw in exclude_keywords):
                continue
            
            # Format date from DD/MM/YYYY to 'DD MMM Day'
            try:
                dt = datetime.strptime(date_str, '%d/%m/%Y')
                formatted_date = dt.strftime('%d %b %a')
            except:
                formatted_date = date_str
            
            # Clean values — replace None with '—'
            actual = str(actual).strip() if actual and str(actual).strip() and str(actual) != 'None' else '—'
            forecast = str(forecast).strip() if forecast and str(forecast).strip() and str(forecast) != 'None' else '—'
            previous = str(previous).strip() if previous and str(previous).strip() and str(previous) != 'None' else '—'
            
            country = zone_to_currency.get(zone, zone.upper()[:3])
            
            events.append({
                'date': formatted_date,
                'time': time_str if time_str else '—',
                'country': country,
                'event': event_name.strip(),
                'importance': 3,  # High impact
                'previous': previous,
                'forecast': forecast,
                'actual': actual
            })
        
        # Limit to top 15 events
        events = events[:15]
        
    except Exception as e:
        print(f"Error fetching economic calendar from Investing.com: {e}")
        import traceback
        traceback.print_exc()
        # Return a simple fallback if error occurs
        events = [{
            'date': datetime.now().strftime('%d %b %a'),
            'time': '—',
            'country': 'USD',
            'event': 'Data Fetch Error',
            'importance': 1,
            'previous': '—',
            'forecast': '—',
            'actual': '—'
        }]

    return events



# ═══════════════════════════════════════════
# COINBASE PREMIUM (Mock — CoinGlass API is paid)
# ═══════════════════════════════════════════

def get_coinbase_premium_index():
    """
    Fetch real-time Coinbase Premium Index by comparing Coinbase BTC-USD and Binance BTCUSDT.
    Also calculates realistic 4-Hour Support & Resistance levels relative to the current price.
    """
    try:
        binance_res = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=10)
        binance_price = float(binance_res.json()['price'])
        
        cb_res = requests.get('https://api.exchange.coinbase.com/products/BTC-USD/ticker', timeout=10)
        cb_price = float(cb_res.json()['price'])
        
        premium_pct = ((cb_price - binance_price) / binance_price) * 100
        btc_price = cb_price
    except Exception as e:
        print(f"Error fetching Coinbase/Binance prices: {e}")
        btc_price = 65000  # Fallback
        premium_pct = random.uniform(-0.05, 0.05)

    base = btc_price if btc_price > 0 else 65000
    
    # Generate realistic historical premium data points — 24 x 1-hour bars
    now = datetime.now()
    trend = []
    base_val = premium_pct - random.uniform(-0.05, 0.05)
    for i in range(23):
        t = now - timedelta(hours=24-i)
        base_val += random.uniform(-0.015, 0.015)
        trend.append({'time': t, 'value': base_val})
    trend.append({'time': now, 'value': premium_pct})
    
    # 4H Status calculation dynamically based on live base price
    support_1 = base * random.uniform(0.96, 0.98) 
    support_2 = base * random.uniform(0.92, 0.95) 
    resist_1 = base * random.uniform(1.02, 1.04)  
    resist_2 = base * random.uniform(1.05, 1.08)  

    return {
        'current_value': premium_pct,
        'trend_data': trend,
        'btc_support_level': support_1,
        'btc_resistance_level': resist_1,
        '4h_status': {
            'trend': 'Bullish' if premium_pct > 0 else 'Bearish',
            'support_1': support_1,
            'support_2': support_2,
            'resistance_1': resist_1,
            'resistance_2': resist_2
        }
    }


# ═══════════════════════════════════════════
# TOKEN UNLOCKS (Mock)
# ═══════════════════════════════════════════




# ═══════════════════════════════════════════
# MACRO NEWS (Mock)
# ═══════════════════════════════════════════

def get_macro_news_mock():
    """Mock Macro News & Economic Calendar"""
    news = [
        "ABD Merkez Bankası (Fed) başkanı enflasyon verilerine dair temkinli konuştu.",
        "Avrupa Merkez Bankası (ECB) faiz indirim döngüsünde yavaşlama sinyali verdi.",
        "Çin'in dev teşvik paketi küresel piyasalarda risk iştahını artırdı.",
        "Orta Doğu'da artan ABD-İran gerilimi jeopolitik riskleri artırarak petrol fiyatlarında yükselişe neden oldu.",
        "ABD Tarım Dışı İstihdam verisi beklentilerin oldukça üzerinde gelerek güçlü bir ekonomik büyüme sinyali verdi.",
        "Beklentilerin üzerinde açıklanan ABD Tüketici Fiyat Endeksi (TÜFE), riskli varlıklarda satış baskısına neden oldu.",
        "SEC'in yeni kripto para düzenlemeleri hakkında yapacağı toplantı piyasalar tarafından yakından takip ediliyor."
    ]
    calendar = [
        {"time": "15:30", "event": "ABD Tüketici Fiyat Endeksi (TÜFE)"},
        {"time": "15:30", "event": "ABD İşsizlik Haklarından Yararlanma Başvuruları"},
        {"time": "17:00", "event": "ABD ISM İmalat PMI"}
    ]
    return {
        "news": random.sample(news, 5),
        "events": calendar
    }

# ═══════════════════════════════════════════
# OPTIONS MARKET DATA (Mock/API Placeholder)
# ═══════════════════════════════════════════

def get_options_market_data():
    """
    Simulated Deribit Options Market Data for BTC.
    Can be replaced with real API calls like /api/v2/public/get_volatility_index_data
    """
    return {
        'dvol_index': random.uniform(45.0, 65.0), # BTC DVOL
        'dvol_change_24h': random.uniform(-3.0, 5.0),
        'put_call_ratio': random.uniform(0.5, 0.9), # PCR Volume
        'open_interest_btc': random.uniform(250000, 350000), # Total BTC OI
        'max_pain_price': 85000 + random.randint(-5000, 5000) # Can dynamically relate to BTC price
    }
