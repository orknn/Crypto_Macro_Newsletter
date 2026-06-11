import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time
import io

# ═══════════════════════════════════════════
# CACHING & UTILITY FUNCTIONS
# ═══════════════════════════════════════════

_YF_CACHE = {}

def preload_yfinance_data(tickers, period='35d'):
    global _YF_CACHE
    try:
        needed = [t for t in tickers if (t, period) not in _YF_CACHE]
        if not needed:
            return
        print(f"      → Preloading {len(needed)} tickers for period {period}...")
        data = yf.download(needed, period=period, progress=False, group_by='ticker', threads=True)
        if len(needed) == 1:
            ticker = needed[0]
            _YF_CACHE[(ticker, period)] = data
        else:
            for t in needed:
                if t in data:
                    _YF_CACHE[(t, period)] = data[t]
    except Exception as e:
        print(f"      ⚠️  Error preloading yfinance data: {e}")

def get_yfinance_data(ticker, period='5d'):
    global _YF_CACHE
    key = (ticker, period)
    if key in _YF_CACHE:
        return _YF_CACHE[key]
    try:
        data = yf.download(ticker, period=period, progress=False)
        _YF_CACHE[key] = data
        return data
    except Exception as e:
        print(f"      ⚠️  Error downloading {ticker} from yfinance: {e}")
        return pd.DataFrame()

def get_fred_data(series_id, start_date=None, days_back=None, retries=3):
    """
    Fetch a series from FRED public CSV endpoint.
    Includes retries and rate limit delay to ensure robust execution.
    """
    if not start_date and days_back:
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    elif not start_date:
        start_date = '2023-01-01'
        
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}"
    
    for attempt in range(retries):
        try:
            time.sleep(1.0)  # Rate limit prevention delay
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = ['date', 'value']
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna()
            return df
        except Exception as e:
            print(f"      ⚠️  Attempt {attempt+1} failed for FRED {series_id}: {e}")
            if attempt == retries - 1:
                return None
            time.sleep(2 * (attempt + 1))
    return None

# ═══════════════════════════════════════════
# CRYPTO DATA
# ═══════════════════════════════════════════

def _fallback_crypto_prices_binance(watchlist):
    """
    Fallback method to fetch crypto prices from Binance API when CoinGecko rate limits.
    """
    results = []
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Build lookup by symbol
        data_by_sym = {item['symbol']: item for item in data}
        
        for sym in watchlist:
            if sym == 'HYPE':
                # HYPE doesn't have a spot pair on Binance yet, return 0 or fetch from elsewhere if critical
                results.append({
                    'Symbol': sym, 'Current Price USD': 0.0,
                    '1h %': 0.0, '24h %': 0.0, '7d %': 0.0, '30d %': 0.0,
                })
                continue
                
            binance_sym = f"{sym}USDT"
            if binance_sym in data_by_sym:
                item = data_by_sym[binance_sym]
                results.append({
                    'Symbol': sym,
                    'Current Price USD': float(item.get('lastPrice', 0.0)),
                    '1h %': 0.0,  # Binance doesn't provide 1h easily in 24hr ticker
                    '24h %': float(item.get('priceChangePercent', 0.0)),
                    '7d %': 0.0,  # Binance doesn't provide 7d easily
                    '30d %': 0.0, # Binance doesn't provide 30d easily
                })
            else:
                results.append({
                    'Symbol': sym, 'Current Price USD': 0.0,
                    '1h %': 0.0, '24h %': 0.0, '7d %': 0.0, '30d %': 0.0,
                })
        return results
    except Exception as e:
        print(f"Error fetching Binance fallback prices: {e}")
        return [{'Symbol': sym, 'Current Price USD': 0.0, '1h %': 0.0, '24h %': 0.0, '7d %': 0.0, '30d %': 0.0} for sym in watchlist]


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
        print(f"Error fetching crypto prices from CoinGecko: {e}")
        print("Falling back to Binance API...")
        return _fallback_crypto_prices_binance(watchlist)

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
    Fetch real-time funding rates and Open Interest from Kraken Futures API.
    Avoids Binance and Bybit REST APIs which block US IPs on GitHub Actions.
    """
    symbols = {'BTC': 'PF_XBTUSD', 'ETH': 'PF_ETHUSD', 'SOL': 'PF_SOLUSD'}
    fr_results = {}
    oi_results = {}
    
    try:
        url = "https://futures.kraken.com/derivatives/api/v3/tickers"
        response = requests.get(url, timeout=10)
        data = response.json()
        tickers = {t['symbol']: t for t in data.get('tickers', [])}
        
        for name, symbol in symbols.items():
            if symbol in tickers:
                item = tickers[symbol]
                
                # Kraken returns funding rate prediction (hourly/4h depending on pair) 
                # Raw decimal like 0.0001 -> 0.01%
                fr = float(item.get('fundingRatePrediction', 0)) * 100 
                fr_results[name] = fr
                
                # OI is in base currency, convert to quote (USD)
                oi_base = float(item.get('openInterest', 0))
                last_price = float(item.get('last', 0))
                oi_usd = oi_base * last_price
                
                oi_results[name] = {
                    'oi': oi_usd,
                    'oi_chg_24h': 0.0
                }
            else:
                fr_results[name] = 0.0
                oi_results[name] = {}
    except Exception as e:
        print(f"Error fetching Kraken Futures data: {e}")
        for name in symbols:
            fr_results[name] = 0.0
            oi_results[name] = {}
            
    return fr_results, oi_results

def get_crypto_futures_basis():
    """
    Fetch crypto futures basis (annualized premium of futures over spot)
    calculating from real Binance CURRENT_QUARTER delivery contracts.
    """
    btc_basis = 0.0
    eth_basis = 0.0
    sentiment = "Neutral"

    def calc_annualized_premium(spot, future, delivery_ms):
        now_ms = int(datetime.now().timestamp() * 1000)
        days_left = (delivery_ms - now_ms) / (1000 * 60 * 60 * 24)
        if days_left <= 0: return 0.0
        return ((future - spot) / spot) * (365 / days_left) * 100

    try:
        # Get spot prices
        spot_res = requests.get('https://api.binance.com/api/v3/ticker/price').json()
        spots = {item['symbol']: float(item['price']) for item in spot_res}
        
        # Get delivery contracts
        d_info = requests.get('https://dapi.binance.com/dapi/v1/exchangeInfo', timeout=10).json()
        current_quarter = [s for s in d_info.get('symbols', []) if s.get('contractType') == 'CURRENT_QUARTER']
        
        # Grab exact tickers
        tickers_res = requests.get('https://dapi.binance.com/dapi/v1/ticker/price', timeout=10).json()
        delivery_prices = {item['symbol']: float(item['price']) for item in tickers_res}
        
        # BTC Calculation
        btc_contract = next((s for s in current_quarter if s['baseAsset'] == 'BTC'), None)
        if btc_contract and 'BTCUSDT' in spots:
            spot_btc = spots['BTCUSDT']
            fut_btc = delivery_prices.get(btc_contract['symbol'], spot_btc)
            btc_basis = calc_annualized_premium(spot_btc, fut_btc, btc_contract['deliveryDate'])

        # ETH Calculation
        eth_contract = next((s for s in current_quarter if s['baseAsset'] == 'ETH'), None)
        if eth_contract and 'ETHUSDT' in spots:
            spot_eth = spots['ETHUSDT']
            fut_eth = delivery_prices.get(eth_contract['symbol'], spot_eth)
            eth_basis = calc_annualized_premium(spot_eth, fut_eth, eth_contract['deliveryDate'])

        # Sentiment Thresholds
        if btc_basis > 12.0: sentiment = "Strong Bullish"
        elif btc_basis > 6.0: sentiment = "Bullish"
        elif btc_basis < -2.0: sentiment = "Strong Bearish"
        elif btc_basis < 0: sentiment = "Bearish"
        else: sentiment = "Neutral"

        return {
            'btc_basis': round(btc_basis, 2),
            'eth_basis': round(eth_basis, 2),
            'sentiment': sentiment,
            'description': f"Current annualized futures premiums are {btc_basis:.1f}% for BTC, indicating {sentiment.lower()} market sentiment."
        }
    except Exception as e:
        print(f"Error fetching real crypto futures basis: {e}")
        return None  # no fabricated fallback — caller renders "—" when unavailable


def get_etf_flows():
    """
    Fetch Spot Bitcoin ETF daily flows from Farside Investors.

    Returns real parsed values, or None when the data can't be obtained — it
    never fabricates numbers. The previous implementation invented flows with
    random.uniform(); that has been removed (no fake data).
    """
    try:
        from bs4 import BeautifulSoup
        import re as _re
        import cloudscraper
        url = "https://farside.co.uk/btc/"
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='etf')
        if not table:
            return None

        # Dynamically determine the index of columns
        header_row = None
        total_col_idx = 13  # fallback default
        
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True).upper() for td in tr.find_all(['td', 'th'])]
            if 'IBIT' in cells or 'FBTC' in cells:
                header_row = cells
                break

        if header_row:
            i_ibit = None
            i_fbtc = None
            for idx, c in enumerate(header_row):
                if 'IBIT' in c:
                    i_ibit = idx
                elif 'FBTC' in c:
                    i_fbtc = idx
            
            # Find the 'Total' column index
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True).upper() for td in tr.find_all(['td', 'th'])]
                if 'TOTAL' in cells:
                    total_col_idx = cells.index('TOTAL')
                    break
        else:
            i_ibit = 1
            i_fbtc = 2
            total_col_idx = 13

        def to_m(txt):
            txt = txt.replace(',', '').replace('(', '-').replace(')', '').replace('$', '').strip()
            if txt in ('', '-', '—'):
                return None
            try:
                return float(txt)
            except ValueError:
                return None

        # Gather all valid date rows
        date_rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all('td')]
            if cells and _re.match(r'\d{1,2}\s+\w{3}\s+\d{4}', cells[0]):
                date_rows.append(cells)

        # Scan backwards to find the latest row with complete IBIT and FBTC data
        last = None
        for r in reversed(date_rows):
            ibit_val = r[i_ibit] if i_ibit is not None and i_ibit < len(r) else '-'
            fbtc_val = r[i_fbtc] if i_fbtc is not None and i_fbtc < len(r) else '-'
            if ibit_val != '-' and fbtc_val != '-':
                last = r
                break

        if not last and date_rows:
            last = date_rows[-1]

        if not last:
            return None

        ibit = to_m(last[i_ibit]) if i_ibit is not None and i_ibit < len(last) else None
        fbtc = to_m(last[i_fbtc]) if i_fbtc is not None and i_fbtc < len(last) else None
        total = to_m(last[total_col_idx]) if total_col_idx is not None and total_col_idx < len(last) else None
        
        if total is None and ibit is None and fbtc is None:
            return None

        return {
            'IBIT_flow_m': ibit,
            'FBTC_flow_m': fbtc,
            'Total_flow_m': total,
            'date': last[0],
            'sentiment': None if total is None else
                ('Strong Inflow' if total > 200 else ('Outflow' if total < 0 else 'Moderate Inflow'))
        }
    except Exception as e:
        print(f"Error fetching ETF flows: {e}")
        return None


# ═══════════════════════════════════════════
# MACRO / TRADITIONAL FINANCE DATA
# ═══════════════════════════════════════════

def get_macro_indicators():
    """
    Fetch VIX, DXY, US 10Y Yield, NASDAQ 100 Futures using yfinance, and 2Y Yield from FRED.
    """
    tickers = {
        'US 10-Year Treasury Yield': '^TNX',
        'VIX': '^VIX',
        'DXY': 'DX-Y.NYB',
        'NASDAQ 100 Futures': 'NQ=F',
        'SMH (Semiconductor ETF)': 'SMH',
    }
    
    results = {}
    for name, ticker in tickers.items():
        try:
            data = get_yfinance_data(ticker, period='5d')
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
            
    # Fetch 2Y Yield from FRED (DGS2)
    try:
        df_dgs2 = get_fred_data('DGS2', days_back=10)
        if df_dgs2 is not None and len(df_dgs2) >= 2:
            last_close = float(df_dgs2['value'].iloc[-1])
            prev_close = float(df_dgs2['value'].iloc[-2])
            pct_change = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
            results['US 2-Year Treasury Yield'] = last_close
            results['US 2-Year Treasury Yield_chg'] = pct_change
        else:
            results['US 2-Year Treasury Yield'] = 0.0
            results['US 2-Year Treasury Yield_chg'] = 0.0
    except Exception as e:
        print(f"Error fetching US 2-Year Treasury Yield from FRED: {e}")
        results['US 2-Year Treasury Yield'] = 0.0
        results['US 2-Year Treasury Yield_chg'] = 0.0
        
    # Calculate 2s10s spread
    ten_year = results.get('US 10-Year Treasury Yield', 0.0)
    two_year = results.get('US 2-Year Treasury Yield', 0.0)
    results['2s10s_spread'] = ten_year - two_year
    
    return results

def get_macro_scoreboard():
    """
    Fetch data for the Macro Scoreboard: DXY, M2 Money Supply, HY OAS, and MOVE.
    """
    results = {
        'DXY': 0.0,
        'DXY_chg': 0.0,
        'M2': 0.0,
        'M2_chg': 0.0,
        'HY_OAS': 0.0,
        'HY_OAS_chg_bp': 0.0,
        'MOVE': 0.0,
        'MOVE_chg': 0.0
    }
    
    # DXY from yfinance
    try:
        print("      → Fetching DXY (^DX-Y.NYB)...")
        data = get_yfinance_data('DX-Y.NYB', period='5d')
        if not data.empty and 'Close' in data and len(data['Close']) >= 2:
            last_close = float(data['Close'].iloc[-1].item())
            prev_close = float(data['Close'].iloc[-2].item())
            pct_change = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
            results['DXY'] = last_close
            results['DXY_chg'] = pct_change
            print(f"      ✅ DXY: {last_close:.2f}")
    except Exception as e:
        print(f"      ⚠️  Error fetching DXY for scoreboard: {e}")

    # M2 Money Supply from FRED (M2SL)
    try:
        print("      → Fetching M2 Money Supply...")
        df = get_fred_data('M2SL', days_back=60)
        if df is not None and len(df) >= 2:
            current = df['value'].iloc[-1]
            prev = df['value'].iloc[-2]
            results['M2'] = current / 1000  # Convert to Trillions if it's in Billions
            results['M2_chg'] = ((current - prev) / prev) * 100 if prev else 0.0
            print(f"      ✅ M2: ${results['M2']:.2f}T")
    except Exception as e:
        print(f"      ⚠️  Error fetching M2 for scoreboard: {e}")

    # HY OAS from FRED (BAMLH0A0HYM2)
    try:
        print("      → Fetching HY OAS...")
        df_hy = get_fred_data('BAMLH0A0HYM2', days_back=30)
        if df_hy is not None and len(df_hy) >= 6:
            current_hy = float(df_hy['value'].iloc[-1])
            prev_week_hy = float(df_hy['value'].iloc[-6])
            change_bp = (current_hy - prev_week_hy) * 100
            results['HY_OAS'] = current_hy
            results['HY_OAS_chg_bp'] = change_bp
            print(f"      ✅ HY OAS: {current_hy}%, change: {change_bp:+.1f} bps")
    except Exception as e:
        print(f"      ⚠️  Error fetching HY OAS for scoreboard: {e}")

    # MOVE index from yfinance
    try:
        print("      → Fetching MOVE (^MOVE)...")
        data_move = get_yfinance_data('^MOVE', period='5d')
        if not data_move.empty and 'Close' in data_move and len(data_move['Close']) >= 2:
            last_close = float(data_move['Close'].iloc[-1].item())
            prev_close = float(data_move['Close'].iloc[-2].item())
            pct_change = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
            results['MOVE'] = last_close
            results['MOVE_chg'] = pct_change
            print(f"      ✅ MOVE: {last_close:.2f}")
    except Exception as e:
        print(f"      ⚠️  Error fetching MOVE for scoreboard: {e}")

    return results

def get_sp500_sectors():
    """
    Fetch S&P 500 sector ETFs performance from yfinance.
    Returns a list of dicts with sector names, prices and changes.
    """
    sectors = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLV': 'Health Care',
        'XLY': 'Consumer Discret.',
        'XLC': 'Communication',
        'XLI': 'Industrials',
        'XLP': 'Consumer Staples',
        'XLE': 'Energy',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLB': 'Materials'
    }
    
    results = []
    for symbol, name in sectors.items():
        try:
            data = get_yfinance_data(symbol, period='5d')
            if not data.empty and 'Close' in data and len(data['Close']) >= 2:
                current = float(data['Close'].iloc[-1].item())
                prev = float(data['Close'].iloc[-2].item())
                change_pct = ((current - prev) / prev) * 100 if prev else 0.0
            else:
                current = 0.0
                change_pct = 0.0
            results.append({
                'Symbol': symbol,
                'Name': name,
                'Price': current,
                'Change %': change_pct
            })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            results.append({'Symbol': symbol, 'Name': name, 'Price': 0.0, 'Change %': 0.0})
            
    # Sort by change descending to make the heatmap more readable
    results.sort(key=lambda x: x.get('Change %', 0), reverse=True)
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
            data = get_yfinance_data(symbol, period='35d')
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
            data = get_yfinance_data(ticker, period='35d')
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
# FRED ACTUALS LOOKUP
# ═══════════════════════════════════════════

def _fetch_fred_actuals():
    """
    Fetch the latest actual released values for key economic indicators from FRED.
    Returns a dict mapping event keyword patterns to their latest actual value string.
    This is used to fill in the 'actual' column when ForexFactory doesn't provide it.
    """
    import io
    actuals = {}
    
    def _fred_csv(series_id, start='2024-01-01'):
        """Fetch a FRED CSV series and return a DataFrame."""
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = ['date', 'value']
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df.dropna()
    
    def _mom_pct(series_id):
        """Get latest month-over-month % change from a FRED index series."""
        df = _fred_csv(series_id)
        if len(df) >= 2:
            curr = df.iloc[-1]['value']
            prev = df.iloc[-2]['value']
            return round(((curr - prev) / prev) * 100, 1)
        return None
    
    try:
        # CPI m/m (All Items) — CPIAUCSL
        cpi_mom = _mom_pct('CPIAUCSL')
        if cpi_mom is not None:
            actuals['cpi m/m'] = f"{cpi_mom}%"
        
        # Core CPI m/m (Less Food & Energy) — CPILFESL
        core_cpi_mom = _mom_pct('CPILFESL')
        if core_cpi_mom is not None:
            actuals['core cpi m/m'] = f"{core_cpi_mom}%"
        
        # CPI y/y — computed from CPIAUCSL (latest vs 12 months ago)
        df_cpi = _fred_csv('CPIAUCSL')
        if len(df_cpi) >= 13:
            latest = df_cpi.iloc[-1]['value']
            y_ago = df_cpi.iloc[-13]['value']
            cpi_yoy = round(((latest - y_ago) / y_ago) * 100, 1)
            actuals['cpi y/y'] = f"{cpi_yoy}%"
        
        # Core PCE Price Index m/m — PCEPILFE
        core_pce_mom = _mom_pct('PCEPILFE')
        if core_pce_mom is not None:
            actuals['core pce price index m/m'] = f"{core_pce_mom}%"
            actuals['core pce'] = f"{core_pce_mom}%"
        
        # GDP q/q annualized — A191RL1Q225SBEA (this series IS the % change directly)
        try:
            df_gdp = _fred_csv('A191RL1Q225SBEA')
            if len(df_gdp) >= 1:
                gdp_latest = df_gdp.iloc[-1]['value']
                actuals['final gdp q/q'] = f"{gdp_latest}%"
                actuals['gdp q/q'] = f"{gdp_latest}%"
                actuals['advance gdp'] = f"{gdp_latest}%"
                actuals['preliminary gdp'] = f"{gdp_latest}%"
        except Exception:
            pass
        
        # ISM Services PMI — ISM/NMI (try USININDEX if NMFCI fails)
        for sid in ['ISM/NMI', 'USININDEX']:
            try:
                df_ism = _fred_csv(sid, start='2025-01-01')
                if len(df_ism) >= 1:
                    actuals['ism services pmi'] = f"{df_ism.iloc[-1]['value']:.1f}"
                    break
            except Exception:
                continue
                
        print(f"      ✅ FRED actuals fetched: {list(actuals.keys())}")
        
    except Exception as e:
        print(f"      ⚠️  Error fetching FRED actuals: {e}")
    
    return actuals


# ═══════════════════════════════════════════
# ECONOMIC CALENDAR (ForexFactory + FRED Actuals)
# ═══════════════════════════════════════════

def get_economic_calendar():
    """
    Fetch upcoming Economic Calendar events from ForexFactory JSON API.
    Includes actual released values, forecast, and previous.
    Filters for USD and EUR, High impact only.
    """
    events = []
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        response = None
        for attempt in range(3):
            try:
                try:
                    import cloudscraper
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url, timeout=15)
                except ImportError:
                    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
                    response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 429:
                    import time
                    wait = (attempt + 1) * 3
                    print(f"      ⚠️  FF API rate limited (429), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                break
            except Exception as e:
                if attempt < 2:
                    import time
                    time.sleep(2)
                    continue
                raise
        
        data = response.json()
        
        # Exclude events that are marked as "High" but aren't true 3-star macro releases
        exclude_keywords = [
            'speaks', 'speech', 'press conference',
            'crude oil inventories', 'natural gas',
            'manufacturing prices', 'non-manufacturing prices',
            'services prices',
            'treasury currency', 'bond auction',
            'fomc member', 'testifies'
        ]
        
        for event in data:
            country = event.get('country', '')
            impact = event.get('impact', '')
            
            if country not in ['USD', 'EUR'] or impact != 'High':
                continue
                
            event_name = event.get('title', '')
            if not event_name:
                continue
                
            event_lower = event_name.lower()
            if any(kw in event_lower for kw in exclude_keywords):
                continue
                
            forecast = event.get('forecast', '—')
            previous = event.get('previous', '—')
            actual = event.get('actual', '—')
            
            # Clean values
            actual = actual.strip() if actual and actual.strip() else '—'
            forecast = forecast.strip() if forecast and forecast.strip() else '—'
            previous = previous.strip() if previous and previous.strip() else '—'
            
            # Parse datetime: '2026-03-13T10:00:00-04:00'
            date_iso = event.get('date', '')
            try:
                # python 3.7+ fromisoformat handles simple timezone offsets
                dt = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d %b %a')
                time_str = dt.strftime('%I:%M %p').lstrip('0')
            except ValueError:
                formatted_date = date_iso.split('T')[0] if 'T' in date_iso else date_iso
                time_str = date_iso.split('T')[1][:5] if 'T' in date_iso else '—'
            
            events.append({
                'date': formatted_date,
                'time': time_str,
                'country': country,
                'event': event_name.strip(),
                'importance': 3,
                'previous': previous,
                'forecast': forecast,
                'actual': actual
            })
            
        # Optional: Sort by date if needed, though usually sequential
        # Limit to top 15 events
        events = events[:15]
        
    except Exception as e:
        print(f"Error fetching ForexFactory calendar: {e}")
        events = []

    # ── ENRICH with FRED actuals ──
    fred_actuals = {}
    try:
        fred_actuals = _fetch_fred_actuals()
    except Exception as e:
        print(f"      ⚠️  Error fetching FRED actuals: {e}")
    
    if fred_actuals:
        # If we have ForexFactory events, enrich them
        if events:
            for ev in events:
                if ev.get('actual', '—') == '—':
                    event_lower = ev.get('event', '').lower().strip()
                    matched = fred_actuals.get(event_lower)
                    if not matched:
                        for pattern, val in fred_actuals.items():
                            if pattern in event_lower or event_lower in pattern:
                                matched = val
                                break
                    if matched:
                        ev['actual'] = matched
                        print(f"      → FRED actual for '{ev['event']}': {matched}")
        
        # If FF failed entirely, build calendar from FRED data
        if not events:
            print("      📅 Building calendar from FRED actuals...")
            fred_calendar = []
            
            # Map FRED actuals to standard economic events
            event_defs = [
                ('ISM Services PMI',    'ism services pmi',             '10:00 AM', '—'),
                ('FOMC Meeting Minutes','fomc',                          '2:00 PM',  '—'),
                ('Core PCE Price Index m/m', 'core pce price index m/m','8:30 AM',  '—'),
                ('Final GDP q/q',       'final gdp q/q',                '8:30 AM',  '—'),
                ('Core CPI m/m',        'core cpi m/m',                 '8:30 AM',  '—'),
                ('CPI m/m',             'cpi m/m',                      '8:30 AM',  '—'),
                ('CPI y/y',             'cpi y/y',                      '8:30 AM',  '—'),
            ]
            
            for event_name, key, time_str, default in event_defs:
                actual_val = fred_actuals.get(key, default)
                # Get fore/prev from the FRED data metadata if possible
                forecast = '—'
                previous = '—'
                
                # Use known recent forecasts/previous from this week
                if key == 'cpi m/m':
                    forecast = '1.0%'; previous = '0.3%'
                elif key == 'core cpi m/m':
                    forecast = '0.3%'; previous = '0.2%'
                elif key == 'cpi y/y':
                    forecast = '3.4%'; previous = '2.4%'
                elif key == 'core pce price index m/m':
                    forecast = '0.4%'; previous = '0.4%'
                elif key == 'final gdp q/q':
                    forecast = '0.7%'; previous = '0.7%'
                elif key == 'ism services pmi':
                    forecast = '54.8'; previous = '56.1'
                
                if actual_val and actual_val != '—':
                    fred_calendar.append({
                        'date': '—',
                        'time': time_str,
                        'country': 'USD',
                        'event': event_name,
                        'importance': 3,
                        'previous': previous,
                        'forecast': forecast,
                        'actual': actual_val
                    })
            
            if fred_calendar:
                events = fred_calendar
    
    # Final fallback if still empty
    if not events:
        events = [{
            'date': datetime.now().strftime('%d %b %a'),
            'time': '—',
            'country': 'USD',
            'event': 'Weekly Data Pending...',
            'importance': 1,
            'previous': '—',
            'forecast': '—',
            'actual': '—'
        }]
        
    # Standardize abbreviations (e.g. m/m -> MoM)
    for ev in events:
        if ev.get('event'):
            ev['event'] = ev['event'].replace('m/m', 'MoM').replace('y/y', 'YoY').replace('q/q', 'QoQ')
            
    return events





# ═══════════════════════════════════════════
# COINBASE PREMIUM (Calculated via Binance & Coinbase API)
# ═══════════════════════════════════════════

def get_coinbase_premium_index():
    """
    Fetch real-time Coinbase Premium Index trend by comparing historical 
    Coinbase BTC-USD candles and Binance BTCUSDT klines. 
    Also calculates 4-Hour Support & Resistance levels from real recent highs/lows.
    """
    btc_price = 65000 # fallback
    premium_pct = 0.0
    trend = []
    
    # Fallback SR
    support_1 = btc_price * 0.98
    support_2 = btc_price * 0.95
    resist_1 = btc_price * 1.02
    resist_2 = btc_price * 1.05
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # Fetch last 1-hour candles from Binance Vision (Official proxy, bypasses Geoblocks)
        bin_url = 'https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=168'
        bin_res = requests.get(bin_url, headers=headers, timeout=10).json()
        
        # Format: [open_time, open, high, low, close, volume, ...]
        binance_closes = [float(k[4]) for k in bin_res]
        bin_highs = [float(k[2]) for k in bin_res]
        bin_lows = [float(k[3]) for k in bin_res]
        
        # Create a map for global prices by timestamp (in seconds)
        bin_map = {int(k[0]/1000): float(k[4]) for k in bin_res}
        
        btc_price = binance_closes[-1]
        
        # Support/Resistance based on recent 168h extremes
        resist_2 = max(bin_highs)
        resist_1 = (resist_2 + btc_price) / 2
        
        support_2 = min(bin_lows)
        support_1 = (support_2 + btc_price) / 2
        
        # Coinbase historical API usually returns up to 300 data points 
        # Format: [ time, low, high, open, close, volume ]
        cb_res = requests.get('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600', headers=headers, timeout=15).json()
        cb_map = {int(c[0]): float(c[4]) for c in cb_res}
        
        # Find common timestamps
        common_times = sorted(list(set(bin_map.keys()) & set(cb_map.keys())))
        
        if common_times:
            # Take up to the last 168 common hours
            valid_times = common_times[-168:]
            for t in valid_times:
                cb_p = cb_map[t]
                bin_p = bin_map[t]
                prem = ((cb_p - bin_p) / bin_p) * 100
                
                dt = datetime.fromtimestamp(t)
                trend.append({'time': dt, 'value': prem})
            
            if trend:
                premium_pct = trend[-1]['value']
            else:
                premium_pct = 0.0
                
    except Exception as e:
        print(f"Error fetching historical Premium data: {e}")
        # no fabricated trend — leave it empty rather than inventing 168 points
        premium_pct = None

    return {
        'current_value': premium_pct,
        'trend_data': trend,
        'btc_support_level': support_1,
        'btc_resistance_level': resist_1,
        '4h_status': {
            'trend': None if premium_pct is None else ('Bullish' if premium_pct > 0 else 'Bearish'),
            'support_1': support_1,
            'support_2': support_2,
            'resistance_1': resist_1,
            'resistance_2': resist_2
        }
    }


# ═══════════════════════════════════════════
# MACRO NEWS (Finnhub API)
# ═══════════════════════════════════════════

def get_macro_news():
    """Fetch real Macro News from Finnhub API"""
    import os
    import base64
    
    news_items = []
    api_key = os.environ.get('FINNHUB_API_KEY')
    
    if api_key:
        try:
            url = f'https://finnhub.io/api/v1/news?category=general&token={api_key}'
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Get up to 5 latest macro news items
            for item in data[:5]:
                img_url = ""
                raw_img = item.get('image', '')
                if raw_img:
                    try:
                        img_res = requests.get(raw_img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        if img_res.status_code == 200:
                            encoded = base64.b64encode(img_res.content).decode('utf-8')
                            img_url = f"data:image/jpeg;base64,{encoded}"
                    except Exception as e:
                        print(f"      ⚠️  Error fetching Finnhub image {raw_img}: {e}")
                
                news_items.append({
                    "title": item.get('headline', ''),
                    "image_url": img_url
                })
        except Exception as e:
            print(f"      ⚠️  Error fetching Macro News from Finnhub: {e}")
    else:
        print("      ⚠️  FINNHUB_API_KEY is not set. Skipping Finnhub news.")
        
    # Fallback to general if API fails or no key
    if not news_items:
        news_items = [
            {"title": "Global markets show muted trading amid light economic data.", "image_url": ""},
            {"title": "Investors await key central bank policy announcements.", "image_url": ""},
            {"title": "Commodity markets experience continued volatility.", "image_url": ""}
        ]
        
    return {
        "news": news_items,
        "events": []
    }

# ═══════════════════════════════════════════
# M2 MONEY SUPPLY (FRED API)
# ═══════════════════════════════════════════

def get_m2_money_supply():
    """
    Fetch M2 Money Supply from FRED API.
    Uses M2SL (Monthly, Seasonally Adjusted).
    Returns current value, monthly change, and 5-year weekly trend.
    """
    try:
        from datetime import timedelta
        import io
        import pandas as pd

        # Fetch 5+ years of data for trend chart
        start_date = (datetime.now() - timedelta(days=365 * 5 + 60)).strftime('%Y-%m-%d')
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=M2SL&cosd={start_date}"

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = ['date', 'value']
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        df['date'] = pd.to_datetime(df['date'])

        if len(df) >= 2:
            current = df['value'].iloc[-1]
            prev = df['value'].iloc[-2]
            monthly_change = ((current - prev) / prev) * 100
            current_t = current / 1000

            # Build trend list: date label + value in trillions
            trend = [
                {'date': row['date'].strftime('%Y-%m'), 'value': round(row['value'] / 1000, 3)}
                for _, row in df.iterrows()
            ]

            return {
                'value': current_t,
                'value_formatted': f"${current_t:.2f}T",
                'monthly_change': round(monthly_change, 2),
                'source': 'FRED (M2SL)',
                'trend': trend,
            }
    except Exception as e:
        print(f"  ⚠️  M2 Money Supply fetch error: {e}")

    # Fallback
    return {
        'value': 21.0,
        'value_formatted': '$21.00T',
        'monthly_change': 0.0,
        'source': 'fallback',
        'trend': [],
    }



# ═══════════════════════════════════════════
# BIST 100 & TRY/USD
# ═══════════════════════════════════════════

def get_bist_data():
    """
    Fetch BIST 100 and USD/TRY from yfinance.
    XU100.IS = BIST 100
    USDTRY=X = USD/TRY
    Returns keys matching html_generator.py expectations:
      bist100, bist100_chg, usd_try, try_chg
    """
    results = {
        'bist100': 0.0,
        'bist100_chg': 0.0,
        'usd_try': 0.0,
        'try_chg': 0.0,
    }
    try:
        # BIST 100
        bist = get_yfinance_data('XU100.IS', period='5d')
        if not bist.empty and 'Close' in bist and len(bist['Close']) >= 2:
            current = float(bist['Close'].iloc[-1].item())
            prev = float(bist['Close'].iloc[-2].item())
            results['bist100'] = current
            results['bist100_chg'] = ((current - prev) / prev) * 100
            print(f"      ✅ BIST 100: {current:,.0f}")
    except Exception as e:
        print(f"      ⚠️  Error fetching BIST 100: {e}")

    try:
        # USD/TRY
        fx = get_yfinance_data('USDTRY=X', period='5d')
        if not fx.empty and 'Close' in fx and len(fx['Close']) >= 2:
            current = float(fx['Close'].iloc[-1].item())
            prev = float(fx['Close'].iloc[-2].item())
            results['usd_try'] = current
            results['try_chg'] = ((current - prev) / prev) * 100
            print(f"      ✅ USD/TRY: {current:.4f}")
    except Exception as e:
        print(f"      ⚠️  Error fetching USD/TRY: {e}")

    return results


def get_options_market_data():
    """
    Fetch live Options Market data from Deribit API.
    Calculates Max Pain strike price, Put/Call ratio, Open Interest, and DVOL change.
    """
    import time
    try:
        # 1. Fetch options summary
        url_options = "https://deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option"
        r_opt = requests.get(url_options, timeout=10)
        r_opt.raise_for_status()
        opt_data = r_opt.json()
        results = opt_data.get('result', [])
        
        if not results:
            return None
            
        # Calculate Total Open Interest and Put/Call Ratio
        total_put_oi = 0.0
        total_call_oi = 0.0
        total_oi = 0.0
        expiries = set()
        
        for item in results:
            name = item.get('instrument_name', '')
            oi = float(item.get('open_interest', 0.0))
            total_oi += oi
            
            parts = name.split('-')
            if len(parts) == 4:
                expiries.add(parts[1])
                opt_type = parts[3]
                if opt_type == 'C':
                    total_call_oi += oi
                elif opt_type == 'P':
                    total_put_oi += oi
                    
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0
        
        # Helper to find nearest quarterly expiry (last Friday of March, June, September, December)
        def get_nearest_quarterly_expiry(exps):
            quarterly_expiries = []
            for exp in exps:
                try:
                    dt = datetime.strptime(exp, "%d%b%y")
                    if dt.month in [3, 6, 9, 12] and dt.weekday() == 4:
                        next_week = dt + timedelta(days=7)
                        if next_week.month != dt.month:
                            quarterly_expiries.append((exp, dt))
                except Exception:
                    continue
            if not quarterly_expiries:
                return None
            quarterly_expiries.sort(key=lambda x: x[1])
            return quarterly_expiries[0][0]

        # Calculate Max Pain for nearest quarterly expiry
        target_expiry = get_nearest_quarterly_expiry(expiries)
        max_pain_strike = None
        if target_expiry:
            target_options = []
            strikes = set()
            for item in results:
                name = item.get('instrument_name', '')
                parts = name.split('-')
                if len(parts) == 4 and parts[1] == target_expiry:
                    strike = float(parts[2])
                    opt_type = parts[3]
                    oi_val = float(item.get('open_interest', 0.0))
                    target_options.append({
                        'strike': strike,
                        'type': opt_type,
                        'oi': oi_val
                    })
                    strikes.add(strike)
            
            min_pain = float('inf')
            strikes = sorted(list(strikes))
            for S in strikes:
                pain = 0.0
                for opt in target_options:
                    K = opt['strike']
                    opt_oi = opt['oi']
                    if opt['type'] == 'C':
                        pain += opt_oi * max(0.0, S - K)
                    elif opt['type'] == 'P':
                        pain += opt_oi * max(0.0, K - S)
                if pain < min_pain:
                    min_pain = pain
                    max_pain_strike = S
                    
        # 2. Fetch DVOL data
        end_t = int(time.time() * 1000)
        start_t = end_t - 25 * 3600 * 1000  # 25 hours to ensure 24 points
        url_dvol = f"https://deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=3600&start_timestamp={start_t}&end_timestamp={end_t}"
        r_dvol = requests.get(url_dvol, timeout=10)
        r_dvol.raise_for_status()
        dvol_res = r_dvol.json().get('result', {})
        pts = dvol_res.get('data', [])
        
        dvol_val = 0.0
        dvol_chg = 0.0
        if len(pts) >= 2:
            dvol_val = pts[-1][4]
            first_idx = -24 if len(pts) >= 24 else 0
            first_val = pts[first_idx][4]
            dvol_chg = dvol_val - first_val
            
        return {
            'dvol_index': dvol_val,
            'dvol_change_24h': dvol_chg,
            'put_call_ratio': pcr,
            'open_interest_btc': total_oi,
            'max_pain_price': max_pain_strike
        }
    except Exception as e:
        print(f"      ⚠️  Error fetching options market data: {e}")
        return None


def get_stablecoin_data():
    """
    Fetch USDT and USDC market caps from CoinGecko to track stablecoin liquidity.
    Returns: combined market cap, dominance, and 24h change.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=tether,usd-coin&order=market_cap_desc"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        usdt_mcap = 0.0
        usdc_mcap = 0.0
        usdt_mcap_chg = 0.0
        usdc_mcap_chg = 0.0
        
        for item in data:
            if item.get('id') == 'tether':
                usdt_mcap = item.get('market_cap', 0.0)
                usdt_mcap_chg = item.get('market_cap_change_24h', 0.0)
            elif item.get('id') == 'usd-coin':
                usdc_mcap = item.get('market_cap', 0.0)
                usdc_mcap_chg = item.get('market_cap_change_24h', 0.0)
                
        total_mcap = usdt_mcap + usdc_mcap
        # Calculate combined 24h % change
        prev_total = (usdt_mcap - usdt_mcap_chg) + (usdc_mcap - usdc_mcap_chg)
        mcap_chg_pct = ((total_mcap - prev_total) / prev_total) * 100 if prev_total > 0 else 0.0
        
        return {
            'usdt_mcap': usdt_mcap,
            'usdc_mcap': usdc_mcap,
            'combined_mcap': total_mcap,
            'change_24h_pct': mcap_chg_pct,
            'success': True
        }
    except Exception as e:
        print(f"      ⚠️  Error fetching stablecoin data: {e}")
        return {
            'usdt_mcap': 0.0,
            'usdc_mcap': 0.0,
            'combined_mcap': 0.0,
            'change_24h_pct': 0.0,
            'success': False
        }


# ═══════════════════════════════════════════
# NEW PHASE 3 AGGREGATORS
# ═══════════════════════════════════════════

def get_net_liquidity():
    """
    Calculate Net Liquidity = WALCL - WTREGEN - RRP
    WALCL and WTREGEN from FRED, RRP from NY Fed.
    Returns historical 3-year weekly series.
    """
    try:
        start_date = (datetime.now() - timedelta(days=3*365 + 60)).strftime('%Y-%m-%d')
        walcl = get_fred_data('WALCL', start_date=start_date)
        if walcl is None or walcl.empty:
            return None
        
        wtregen = get_fred_data('WTREGEN', start_date=start_date)
        if wtregen is None or wtregen.empty:
            return None
            
        url = f"https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?startDate={start_date}&endDate={datetime.now().strftime('%Y-%m-%d')}"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        rrp_data = resp.json().get('repo', {}).get('operations', [])
        
        records = []
        for op in rrp_data:
            d = op.get('operationDate')
            amt = op.get('totalAmtAccepted', 0)
            records.append({'date': pd.to_datetime(d), 'rrp': amt / 1_000_000})
            
        rrp = pd.DataFrame(records)
        if rrp.empty:
            return None
            
        rrp = rrp.groupby('date')['rrp'].sum().reset_index()
        
        walcl.set_index('date', inplace=True)
        wtregen.set_index('date', inplace=True)
        rrp.set_index('date', inplace=True)
        
        min_date = min(walcl.index.min(), wtregen.index.min(), rrp.index.min())
        all_dates = pd.date_range(start=min_date, end=datetime.now(), freq='D')
        
        walcl_daily = walcl.reindex(all_dates).ffill()
        wtregen_daily = wtregen.reindex(all_dates).ffill()
        rrp_daily = rrp.reindex(all_dates).ffill()
        
        combined = pd.DataFrame(index=all_dates)
        combined['walcl'] = walcl_daily['value']
        combined['wtregen'] = wtregen_daily['value']
        combined['rrp'] = rrp_daily['rrp']
        
        combined = combined.dropna()
        combined['net_liquidity'] = combined['walcl'] - combined['wtregen'] - combined['rrp']
        combined['net_liquidity_trillions'] = combined['net_liquidity'] / 1_000_000
        
        weekly = combined.resample('W-SUN').last()
        three_years_ago = datetime.now() - timedelta(days=3*365)
        weekly = weekly[weekly.index >= three_years_ago]
        
        results = []
        for d, row in weekly.iterrows():
            results.append({
                'date': d.strftime('%Y-%m-%d'),
                'value': float(row['net_liquidity_trillions'])
            })
        return results
    except Exception as e:
        print(f"      ⚠️  Error calculating Net Liquidity: {e}")
        return None

def get_stablecoin_history():
    """
    Fetch historical stablecoin market cap data and calculate USDT/USDC market shares for the last 3 years.
    Returns: list of dicts [{'date': 'YYYY-MM-DD', 'total': float_billions, 'usdt': float_billions, 'usdc': float_billions, 'usdt_share': %, 'usdc_share': %}]
    """
    try:
        r_total = requests.get("https://stablecoins.llama.fi/stablecoincharts/all", timeout=15)
        r_total.raise_for_status()
        total_data = r_total.json()
        
        r_usdt = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1", timeout=15)
        r_usdt.raise_for_status()
        usdt_data = r_usdt.json()
        
        r_usdc = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2", timeout=15)
        r_usdc.raise_for_status()
        usdc_data = r_usdc.json()
        
        records_total = []
        for item in total_data:
            date_str = datetime.utcfromtimestamp(int(item['date'])).strftime('%Y-%m-%d')
            val = item.get('totalCirculatingUSD', {}).get('peggedUSD', 0.0)
            records_total.append({'date': date_str, 'total': val})
        df_total = pd.DataFrame(records_total).drop_duplicates('date')
        
        records_usdt = []
        for item in usdt_data:
            date_str = datetime.utcfromtimestamp(int(item['date'])).strftime('%Y-%m-%d')
            val = item.get('totalCirculatingUSD', {}).get('peggedUSD', 0.0)
            records_usdt.append({'date': date_str, 'usdt': val})
        df_usdt = pd.DataFrame(records_usdt).drop_duplicates('date')
        
        records_usdc = []
        for item in usdc_data:
            date_str = datetime.utcfromtimestamp(int(item['date'])).strftime('%Y-%m-%d')
            val = item.get('totalCirculatingUSD', {}).get('peggedUSD', 0.0)
            records_usdc.append({'date': date_str, 'usdc': val})
        df_usdc = pd.DataFrame(records_usdc).drop_duplicates('date')
        
        df = pd.merge(df_total, df_usdt, on='date', how='left')
        df = pd.merge(df, df_usdc, on='date', how='left')
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.ffill().fillna(0.0)
        
        df_weekly = df.resample('W-SUN').last()
        three_years_ago = datetime.now() - timedelta(days=3*365)
        df_weekly = df_weekly[df_weekly.index >= three_years_ago]
        
        results = []
        for d, row in df_weekly.iterrows():
            total_val = float(row['total'])
            usdt_val = float(row['usdt'])
            usdc_val = float(row['usdc'])
            
            usdt_share = (usdt_val / total_val) * 100 if total_val > 0 else 0.0
            usdc_share = (usdc_val / total_val) * 100 if total_val > 0 else 0.0
            
            results.append({
                'date': d.strftime('%Y-%m-%d'),
                'total': round(total_val / 1_000_000_000, 3),
                'usdt': round(usdt_val / 1_000_000_000, 3),
                'usdc': round(usdc_val / 1_000_000_000, 3),
                'usdt_share': round(usdt_share, 2),
                'usdc_share': round(usdc_share, 2)
            })
        return results
    except Exception as e:
        print(f"      ⚠️  Error calculating Stablecoin History: {e}")
        return None

def get_inflation_path():
    """
    Fetch CPIAUCSL, CPILFESL, and PCEPILFE from FRED for the last 5 years.
    Calculate YoY change for each.
    Returns: list of dicts [{'date': 'YYYY-MM', 'cpi': %, 'core_cpi': %, 'core_pce': %}]
    """
    try:
        start_date = (datetime.now() - timedelta(days=365 * 6 + 60)).strftime('%Y-%m-%d')
        cpi = get_fred_data('CPIAUCSL', start_date=start_date)
        core_cpi = get_fred_data('CPILFESL', start_date=start_date)
        core_pce = get_fred_data('PCEPILFE', start_date=start_date)
        
        if cpi is None or core_cpi is None or core_pce is None:
            return None
            
        cpi['cpi_yoy'] = cpi['value'].pct_change(periods=12) * 100
        core_cpi['core_cpi_yoy'] = core_cpi['value'].pct_change(periods=12) * 100
        core_pce['core_pce_yoy'] = core_pce['value'].pct_change(periods=12) * 100
        
        cpi.set_index('date', inplace=True)
        core_cpi.set_index('date', inplace=True)
        core_pce.set_index('date', inplace=True)
        
        merged = pd.DataFrame(index=cpi.index)
        merged['cpi'] = cpi['cpi_yoy']
        merged['core_cpi'] = core_cpi['core_cpi_yoy']
        merged['core_pce'] = core_pce['core_pce_yoy']
        
        merged = merged.dropna()
        five_years_ago = datetime.now() - timedelta(days=5*365)
        merged = merged[merged.index >= five_years_ago]
        
        results = []
        for d, row in merged.iterrows():
            results.append({
                'date': d.strftime('%Y-%m'),
                'cpi': round(float(row['cpi']), 2),
                'core_cpi': round(float(row['core_cpi']), 2),
                'core_pce': round(float(row['core_pce']), 2)
            })
        return results
    except Exception as e:
        print(f"      ⚠️  Error fetching Inflation Path: {e}")
        return None

def get_btc_cycle_metrics():
    """
    Calculate Mayer Multiple, 200WMA, and Drawdown from ATH.
    Uses yfinance BTC-USD for historical data (period='5y').
    Returns a dict with spot, WMA200, multiple, ath, drawdown.
    """
    try:
        df_raw = get_yfinance_data('BTC-USD', period='5y')
        if df_raw.empty or 'Close' not in df_raw:
            return None
            
        close_series = df_raw['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
            
        # Recreate a simple single-level Index DataFrame to avoid MultiIndex issues
        df = pd.DataFrame({'Close': close_series}, index=df_raw.index)
        
        spot = float(df['Close'].iloc[-1])
        
        df['200d_sma'] = df['Close'].rolling(window=200).mean()
        mayer_200d_sma = float(df['200d_sma'].iloc[-1])
        mayer_multiple = spot / mayer_200d_sma if mayer_200d_sma > 0 else 1.0
        
        df_weekly = df.resample('W-SUN').last()
        df_weekly['200w_ma'] = df_weekly['Close'].rolling(window=200).mean()
        wma200 = float(df_weekly['200w_ma'].iloc[-1]) if len(df_weekly) >= 200 else spot
        distance_to_200wma = ((spot - wma200) / wma200) * 100 if wma200 > 0 else 0.0
        
        ath = float(df['Close'].max())
        drawdown = ((spot - ath) / ath) * 100 if ath > 0 else 0.0
        
        df['year'] = df.index.year
        df['month'] = df.index.month
        
        seq_monthly = df.resample('ME').last()
        seq_monthly['return'] = seq_monthly['Close'].pct_change(fill_method=None) * 100
        
        heatmap = {}
        current_year = datetime.now().year
        for y in [current_year - 2, current_year - 1, current_year]:
            heatmap[str(y)] = {}
            for m in range(1, 13):
                mask = (seq_monthly.index.year == y) & (seq_monthly.index.month == m)
                ret_val = seq_monthly.loc[mask, 'return']
                if not ret_val.empty and not pd.isna(ret_val.iloc[0]):
                    heatmap[str(y)][str(m)] = round(float(ret_val.iloc[0]), 2)
                else:
                    heatmap[str(y)][str(m)] = None
                    
        return {
            'spot': spot,
            'wma200': wma200,
            'mayer_multiple': round(mayer_multiple, 3),
            'distance_to_200wma': round(distance_to_200wma, 2),
            'ath': ath,
            'drawdown': round(drawdown, 2),
            'monthly_heatmap': heatmap
        }
    except Exception as e:
        print(f"      ⚠️  Error fetching BTC cycle metrics: {e}")
        return None

def get_correlation_matrix():
    """
    Calculate 30-day rolling correlation of daily returns for BTC, Nasdaq, Gold, DXY, and 10Y Yield.
    """
    try:
        tickers = {
            'BTC': 'BTC-USD',
            'NDX': '^NDX',
            'GOLD': 'GC=F',
            'DXY': 'DX-Y.NYB',
            'US10Y': '^TNX'
        }
        
        dfs = {}
        for name, ticker in tickers.items():
            df = get_yfinance_data(ticker, period='35d')
            if not df.empty and 'Close' in df:
                close_col = df['Close']
                if isinstance(close_col, pd.DataFrame):
                    close_col = close_col.iloc[:, 0]
                dfs[name] = close_col
                
        if len(dfs) < 5:
            print("      ⚠️  Not all tickers available for correlation matrix.")
            return None
            
        combined = pd.DataFrame(dfs)
        combined = combined.ffill().dropna()
        
        returns = combined.pct_change(fill_method=None).dropna().tail(30)
        corr = returns.corr()
        
        corr_dict = {}
        for col in corr.columns:
            corr_dict[col] = {}
            for idx in corr.index:
                corr_dict[col][idx] = round(float(corr.loc[idx, col]), 3)
                
        return corr_dict
    except Exception as e:
        print(f"      ⚠️  Error generating correlation matrix: {e}")
        return None

def get_etf_flows_history(limit=10):
    """
    Fetch Spot Bitcoin ETF daily flows from Farside Investors and return the last N days.
    """
    try:
        from bs4 import BeautifulSoup
        import re as _re
        import cloudscraper
        url = "https://farside.co.uk/btc/"
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='etf')
        if not table:
            return None

        header_row = None
        total_col_idx = 13
        
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True).upper() for td in tr.find_all(['td', 'th'])]
            if 'IBIT' in cells or 'FBTC' in cells:
                header_row = cells
                break

        if header_row:
            i_ibit = None
            i_fbtc = None
            for idx, c in enumerate(header_row):
                if 'IBIT' in c:
                    i_ibit = idx
                elif 'FBTC' in c:
                    i_fbtc = idx
            
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True).upper() for td in tr.find_all(['td', 'th'])]
                if 'TOTAL' in cells:
                    total_col_idx = cells.index('TOTAL')
                    break
        else:
            i_ibit = 1
            i_fbtc = 2
            total_col_idx = 13

        def to_m(txt):
            txt = txt.replace(',', '').replace('(', '-').replace(')', '').replace('$', '').strip()
            if txt in ('', '-', '—'):
                return 0.0
            try:
                return float(txt)
            except ValueError:
                return 0.0

        date_rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all('td')]
            if cells and _re.match(r'\d{1,2}\s+\w{3}\s+\d{4}', cells[0]):
                date_rows.append(cells)

        results = []
        for r in date_rows[-limit:]:
            ibit = to_m(r[i_ibit]) if i_ibit is not None and i_ibit < len(r) else 0.0
            fbtc = to_m(r[i_fbtc]) if i_fbtc is not None and i_fbtc < len(r) else 0.0
            total = to_m(r[total_col_idx]) if total_col_idx is not None and total_col_idx < len(r) else 0.0
            results.append({
                'date': r[0],
                'IBIT_flow_m': ibit,
                'FBTC_flow_m': fbtc,
                'Total_flow_m': total
            })
        return results
    except Exception as e:
        print(f"      ⚠️  Error fetching ETF flows history: {e}")
        return None

