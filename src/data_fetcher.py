"""Stock data fetcher - uses yfinance (primary) with Alpha Vantage fallback."""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"


def resolve_symbol(symbol: str) -> str:
    """Intelligently resolve symbol using Yahoo Finance search if no exchange suffix is provided."""
    # If user already provided an explicit suffix (like .NS, .BO, .L)
    if "." in symbol:
        return symbol.upper()
        
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        quotes = data.get('quotes', [])
        if quotes:
            # 1. Filter for Equities only first (prioritize stocks over ETFs)
            equities = [q for q in quotes if q.get('quoteType') == 'EQUITY']
            
            # 2. Look for an exact ticker match (e.g., if user typed SBIN, look for SBIN.NS or SBIN.BO)
            best_match = None
            for q in equities:
                q_symbol = q.get('symbol', '').upper()
                if q_symbol == symbol.upper() or q_symbol.startswith(f"{symbol.upper()}."):
                    # Favor National Stock Exchange (.NS) if available
                    if q_symbol.endswith('.NS'):
                        return q_symbol
                    if best_match is None:
                        best_match = q_symbol
            
            if best_match:
                return best_match

            # 3. Fallback to first Equity found
            if equities:
                return equities[0].get('symbol').upper()
                
            # 4. Final fallback to any ETF or result
            for q in quotes:
                if q.get('quoteType') in ('EQUITY', 'ETF'):
                    return q.get('symbol').upper()
            
    except Exception as e:
        print(f"Symbol search failed: {e}")
        
    # If search fails or returns nothing, just return the original symbol
    return symbol.upper()

def get_daily_data(symbol: str, output_size: str = "compact") -> dict:
    """Fetch daily OHLCV data for a stock using yfinance.

    yfinance provides more reliable data with 20+ years of history.
    Falls back to Alpha Vantage if yfinance fails.
    """
    try:
        import yfinance as yf
        import requests
        
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        ticker = yf.Ticker(symbol, session=session)
        hist = ticker.history(period="2y")
        if hist.empty:
            raise ValueError(f"No data returned for {symbol}")

        # Convert to Alpha Vantage format for compatibility
        result = {}
        for idx, row in hist.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            result[date_str] = {
                "1. open": row["Open"],
                "2. high": row["High"],
                "3. low": row["Low"],
                "4. close": row["Close"],
                "5. volume": row["Volume"],
            }
        return result
    except Exception as e:
        print(f"yfinance failed ({e}), falling back to Alpha Vantage...")
        return _get_av_daily_data(symbol, output_size)


def _get_av_daily_data(symbol: str, output_size: str = "compact") -> dict:
    """Fetch daily data from Alpha Vantage (fallback)."""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": output_size,
        "apikey": API_KEY,
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if "Time Series (Daily)" not in data:
        raise ValueError(f"Invalid symbol or API error: {data}")

    return data["Time Series (Daily)"]


def get_company_info(symbol: str) -> dict:
    """Fetch company profile and fundamental data using yfinance."""
    try:
        import yfinance as yf
        import requests
        
        # Use a session with a custom User-Agent to avoid being blocked by Yahoo
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        ticker = yf.Ticker(symbol, session=session)
        info = ticker.info

        # Helper to handle None values
        def safe_get(key, default="N/A"):
            val = info.get(key)
            return default if val is None else val

        # Map yfinance info to our expected format
        # Try shortName, then longName, then symbol
        name = info.get("shortName") or info.get("longName") or symbol
        
        return {
            "Symbol": symbol,
            "Name": name,
            "Description": safe_get("longBusinessSummary"),
            "Sector": safe_get("sector"),
            "Industry": safe_get("industry"),
            "PERatio": safe_get("trailingPE") or safe_get("forwardPE"),
            "PEGRatio": safe_get("pegRatio"),
            "PriceToBookRatio": safe_get("priceToBook"),
            "ProfitMargin": safe_get("profitMargins", 0),
            "OperatingMarginTTM": safe_get("operatingMargins", 0),
            "ReturnOnEquityTTM": safe_get("returnOnEquity", 0),
            "QuarterlyRevenueGrowthYOY": safe_get("revenueGrowth", 0),
            "QuarterlyEarningsGrowthYOY": safe_get("earningsGrowth", 0),
            "DebtToEquity": safe_get("debtToEquity"),
            "CurrentRatio": safe_get("currentRatio"),
            "MarketCapitalization": safe_get("marketCap"),
            "52WeekHigh": safe_get("fiftyTwoWeekHigh"),
            "52WeekLow": safe_get("fiftyTwoWeekLow"),
            "DividendYield": safe_get("dividendYield"),
            "Beta": safe_get("beta"),
        }
    except Exception as e:
        print(f"yfinance company info failed ({e}), trying Alpha Vantage...")
        return _get_av_company_info(symbol)


def _get_av_company_info(symbol: str) -> dict:
    """Fetch company info from Alpha Vantage (fallback)."""
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": API_KEY,
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_income_statement(symbol: str) -> dict:
    """Fetch annual income statement using yfinance primarily."""
    try:
        import yfinance as yf
        import requests
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        ticker = yf.Ticker(symbol, session=session)
        stmt = ticker.income_stmt
        
        if stmt.empty:
            raise ValueError("No income statement found")
            
        # Convert yfinance format to a simplified dict for our analyzer
        # We just need the most recent year's data
        latest = stmt.iloc[:, 0]
        return {
            "annualReports": [{
                "totalRevenue": latest.get("Total Revenue", 0),
                "netIncome": latest.get("Net Income", 0)
            }]
        }
    except Exception as e:
        print(f"yfinance income stmt failed ({e}), falling back to Alpha Vantage...")
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
            "apikey": API_KEY,
        }
        response = requests.get(BASE_URL, params=params)
        return response.json()


def get_quote(symbol: str) -> dict:
    """Fetch real-time quote using yfinance primarily."""
    try:
        import yfinance as yf
        import requests
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        ticker = yf.Ticker(symbol, session=session)
        info = ticker.info
        
        # Map yfinance info to Alpha Vantage Global Quote format
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        prev_close = info.get("previousClose") or price
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
        
        return {
            "01. symbol": symbol,
            "05. price": price,
            "09. change": change,
            "10. change percent": f"{change_pct:.2f}%"
        }
    except Exception as e:
        print(f"yfinance quote failed ({e}), falling back to Alpha Vantage...")
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": API_KEY,
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        return data.get("Global Quote", {})


def parse_to_dataframe(daily_data: dict) -> "pd.DataFrame":
    """Convert API response to pandas DataFrame."""
    import pandas as pd

    df = pd.DataFrame.from_dict(daily_data, orient="index")
    df.index = pd.to_datetime(df.index)
    # Convert to numeric, coercing errors to NaN, then drop any rows with missing values
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna()
    df.columns = ["open", "high", "low", "close", "volume"]
    return df.sort_index()
