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
        'VIX': '^VIX',
        'DXY': 'DX-Y.NYB',
        'NASDAQ 100 Futures': 'NQ=F'
    }
    
    results = {}
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, period='5d', progress=False)
            if not data.empty and 'Close' in data:
                last_close = float(data['Close'].iloc[-1].item())
            else:
                last_close = 0.0
            results[name] = last_close
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            results[name] = 0.0
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
# ECONOMIC CALENDAR (Mock — will integrate real API later)
# ═══════════════════════════════════════════

def get_economic_calendar():
    """
    Mock weekly economic calendar with 3-star (high importance) events.
    Will integrate with tradingeconomics or similar API later.
    """
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    
    events = [
        {
            'date': (monday + timedelta(days=0)).strftime('%d %b %a'),
            'time': '15:30',
            'country': 'US',
            'event': 'Core PCE Price Index (MoM)',
            'importance': 3,
            'previous': '0.3%',
            'forecast': '0.3%',
        },
        {
            'date': (monday + timedelta(days=1)).strftime('%d %b %a'),
            'time': '15:30',
            'country': 'US',
            'event': 'Non-Farm Payrolls',
            'importance': 3,
            'previous': '256K',
            'forecast': '170K',
        },
        {
            'date': (monday + timedelta(days=1)).strftime('%d %b %a'),
            'time': '15:30',
            'country': 'US',
            'event': 'Unemployment Rate',
            'importance': 3,
            'previous': '4.0%',
            'forecast': '4.0%',
        },
        {
            'date': (monday + timedelta(days=2)).strftime('%d %b %a'),
            'time': '14:15',
            'country': 'EU',
            'event': 'ECB Interest Rate Decision',
            'importance': 3,
            'previous': '2.90%',
            'forecast': '2.65%',
        },
        {
            'date': (monday + timedelta(days=3)).strftime('%d %b %a'),
            'time': '15:30',
            'country': 'US',
            'event': 'CPI (YoY)',
            'importance': 3,
            'previous': '3.0%',
            'forecast': '2.9%',
        },
        {
            'date': (monday + timedelta(days=3)).strftime('%d %b %a'),
            'time': '17:00',
            'country': 'US',
            'event': 'ISM Manufacturing PMI',
            'importance': 3,
            'previous': '49.3',
            'forecast': '49.5',
        },
        {
            'date': (monday + timedelta(days=4)).strftime('%d %b %a'),
            'time': '15:30',
            'country': 'US',
            'event': 'Initial Jobless Claims',
            'importance': 3,
            'previous': '219K',
            'forecast': '220K',
        },
    ]
    return events


# ═══════════════════════════════════════════
# ETF FLOWS (Mock — will integrate Farside/CoinGlass later)
# ═══════════════════════════════════════════

def get_crypto_etf_flows():
    """
    Mock crypto ETF inflows/outflows data — detailed per-asset breakdown.
    """
    flows = [
        {'asset': 'Bitcoin ETFs', 'ticker': 'IBIT/FBTC/GBTC', 'flow_m': random.uniform(-100, 400), 'type': 'BTC'},
        {'asset': 'Ethereum ETFs', 'ticker': 'ETHA/ETHE', 'flow_m': random.uniform(-80, 150), 'type': 'ETH'},
        {'asset': 'Solana ETFs', 'ticker': 'SOLQ', 'flow_m': random.uniform(-20, 50), 'type': 'SOL'},
    ]
    
    # Individual ETF breakdown
    btc_etfs = [
        {'name': 'IBIT (BlackRock)', 'flow_m': random.uniform(50, 300)},
        {'name': 'FBTC (Fidelity)', 'flow_m': random.uniform(10, 150)},
        {'name': 'GBTC (Grayscale)', 'flow_m': random.uniform(-200, -20)},
        {'name': 'ARKB (Ark/21Shares)', 'flow_m': random.uniform(-30, 80)},
    ]
    eth_etfs = [
        {'name': 'ETHA (BlackRock)', 'flow_m': random.uniform(10, 80)},
        {'name': 'ETHE (Grayscale)', 'flow_m': random.uniform(-60, -5)},
    ]
    
    total_inflow = sum(f['flow_m'] for f in btc_etfs + eth_etfs if f['flow_m'] > 0)
    total_outflow = sum(f['flow_m'] for f in btc_etfs + eth_etfs if f['flow_m'] < 0)
    
    return {
        'summary': flows,
        'btc_etfs': btc_etfs,
        'eth_etfs': eth_etfs,
        'total_net_inflow': total_inflow,
        'total_net_outflow': total_outflow,
        'net_flow': total_inflow + total_outflow,
    }


# ═══════════════════════════════════════════
# COINBASE PREMIUM (Mock — CoinGlass API is paid)
# ═══════════════════════════════════════════

def get_coinbase_premium_mock():
    """Mock 1-hour trend for Coinbase Premium Index"""
    base_val = random.uniform(-0.05, 0.1)
    trend = []
    now = datetime.now()
    for i in range(60):
        t = now - timedelta(minutes=60-i)
        base_val += random.uniform(-0.01, 0.01)
        trend.append({'time': t, 'value': base_val})
        
    return {
        'trend_data': trend,
        'current_value': base_val,
        'btc_support_level': 85000 + random.randint(-2000, 2000),
        'btc_resistance_level': 95000 + random.randint(-2000, 2000)
    }


# ═══════════════════════════════════════════
# TOKEN UNLOCKS (Mock)
# ═══════════════════════════════════════════

def get_token_unlocks_mock(watchlist):
    """Mock upcoming Token Unlocks & Burns"""
    unlocks = []
    selected = random.sample(watchlist, min(3, len(watchlist)))
    for sym in selected:
        amount_m = random.uniform(10, 200)
        days = random.randint(1, 14)
        unlocks.append({
            'symbol': sym,
            'event': 'token unlock' if random.random() > 0.3 else 'token burn',
            'amount_usd_m': amount_m,
            'date': (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        })
    return unlocks


# ═══════════════════════════════════════════
# MACRO NEWS (Mock)
# ═══════════════════════════════════════════

def get_macro_news_mock():
    """Mock Macro News & Economic Calendar"""
    news = [
        "ABD Merkez Bankası (Fed) başkanı enflasyon verilerine dair temkinli konuştu.",
        "Avrupa Merkez Bankası (ECB) faiz indirim döngüsünde yavaşlama sinyali verdi.",
        "Çin'in dev teşvik paketi küresel piyasalarda risk iştahını artırdı."
    ]
    calendar = [
        {"time": "15:30", "event": "ABD Tüketici Fiyat Endeksi (TÜFE)"},
        {"time": "15:30", "event": "ABD İşsizlik Haklarından Yararlanma Başvuruları"},
        {"time": "17:00", "event": "ABD ISM İmalat PMI"}
    ]
    return {
        "news": random.sample(news, 2),
        "events": calendar
    }
