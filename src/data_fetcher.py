"""Stock data fetcher - uses yfinance (primary) with Alpha Vantage fallback."""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"


def get_daily_data(symbol: str, output_size: str = "compact") -> dict:
    """Fetch daily OHLCV data for a stock using yfinance.

    yfinance provides more reliable data with 20+ years of history.
    Falls back to Alpha Vantage if yfinance fails.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max")
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
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Map yfinance info to our expected format
        return {
            "Symbol": symbol,
            "Name": info.get("shortName", "N/A"),
            "Description": info.get("longBusinessSummary", "N/A"),
            "Sector": info.get("sector", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "PERatio": info.get("trailingPE", "N/A"),
            "PEGRatio": info.get("pegRatio", "N/A"),
            "PriceToBookRatio": info.get("priceToBook", "N/A"),
            "ProfitMargin": info.get("profitMargins", 0),
            "OperatingMarginTTM": info.get("operatingMargins", 0),
            "ReturnOnEquityTTM": info.get("returnOnEquity", 0),
            "QuarterlyRevenueGrowthYOY": info.get("revenueGrowth", 0),
            "QuarterlyEarningsGrowthYOY": info.get("earningsGrowth", 0),
            "DebtToEquity": info.get("debtToEquity", "N/A"),
            "CurrentRatio": info.get("currentRatio", "N/A"),
            "MarketCapitalization": info.get("marketCap", "N/A"),
            "52WeekHigh": info.get("fiftyTwoWeekHigh", "N/A"),
            "52WeekLow": info.get("fiftyTwoWeekLow", "N/A"),
            "DividendYield": info.get("dividendYield", "N/A"),
            "Beta": info.get("beta", "N/A"),
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
    """Fetch annual income statement."""
    params = {
        "function": "INCOME_STATEMENT",
        "symbol": symbol,
        "apikey": API_KEY,
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_quote(symbol: str) -> dict:
    """Fetch real-time quote."""
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY,
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("Global Quote", {})


def parse_to_dataframe(daily_data: dict) -> "pd.DataFrame":
    """Convert API response to pandas DataFrame."""
    import pandas as pd

    df = pd.DataFrame.from_dict(daily_data, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.astype(float)
    df.columns = ["open", "high", "low", "close", "volume"]
    return df.sort_index()
