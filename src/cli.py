"""Command Line Interface for Quant Bot."""

import sys
from datetime import datetime
from . import data_fetcher
from . import analyzer


def format_currency(value: str | float) -> str:
    """Format value as currency."""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percent(value: str | float) -> str:
    """Format value as percentage."""
    try:
        return f"{float(value) * 100:.2f}%" if float(value) < 1 else f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def analyze_stock(symbol: str):
    """Run full analysis on a stock."""
    symbol = symbol.upper()
    print(f"\n{'=' * 60}")
    print(f"  QUANT BOT ANALYSIS: {symbol}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    # Fetch data
    print("[1/5] Fetching market data...")
    try:
        daily_data = data_fetcher.get_daily_data(symbol)
        company_info = data_fetcher.get_company_info(symbol)
        quote = data_fetcher.get_quote(symbol)
    except Exception as e:
        print(f"  ERROR: Failed to fetch data - {e}")
        print("  Make sure you have a valid Alpha Vantage API key in .env file")
        return

    df = data_fetcher.parse_to_dataframe(daily_data)
    print(f"  Loaded {len(df)} days of historical data")

    # Company Overview
    print(f"\n{'-' * 60}")
    print("  COMPANY OVERVIEW")
    print(f"{'-' * 60}")
    print(f"  Name: {company_info.get('Name', 'N/A')}")
    print(f"  Sector: {company_info.get('Sector', 'N/A')}")
    print(f"  Industry: {company_info.get('Industry', 'N/A')}")
    print(f"  Market Cap: {format_currency(company_info.get('MarketCapitalization', 0))}")
    print(f"  Current Price: {format_currency(quote.get('05. price', 0))}")

    # Technical Analysis
    print(f"\n{'-' * 60}")
    print("  TECHNICAL ANALYSIS")
    print(f"{'-' * 60}")

    df = analyzer.add_technical_indicators(df)
    latest = df.iloc[-1]

    print(f"\n  Moving Averages:")
    print(f"    SMA(20):  ${latest['sma_20']:.2f}  |  Price vs SMA: {'ABOVE' if latest['close'] > latest['sma_20'] else 'BELOW'}")
    print(f"    SMA(50):  ${latest['sma_50']:.2f}  |  Price vs SMA: {'ABOVE' if latest['close'] > latest['sma_50'] else 'BELOW'}")
    print(f"    SMA(200): ${latest['sma_200']:.2f} |  Price vs SMA: {'ABOVE' if latest['close'] > latest['sma_200'] else 'BELOW'}")

    print(f"\n  Momentum Indicators:")
    print(f"    RSI(14):     {latest['rsi']:.2f}  {'[OVERBOUGHT]' if latest['rsi'] > 70 else '[OVERSOLD]' if latest['rsi'] < 30 else '[NEUTRAL]'}")
    print(f"    MACD:        {latest['macd']:.4f}  |  Signal: {latest['macd_signal']:.4f}  |  Hist: {latest['macd_hist']:.4f}")
    print(f"    Stochastic:  K={latest['stoch_k']:.2f}  D={latest['stoch_d']:.2f}")

    print(f"\n  Volatility:")
    print(f"    ATR(14):     ${latest['atr']:.2f}")
    print(f"    Bollinger:   Upper ${latest['bb_upper']:.2f} | Middle ${latest['bb_middle']:.2f} | Lower ${latest['bb_lower']:.2f}")
    print(f"    BB Position: {latest['bb_pct'] * 100:.1f}% (0%=lower band, 100%=upper band)")

    # Generate Signals
    print(f"\n{'-' * 60}")
    print("  TRADING SIGNALS")
    print(f"{'-' * 60}")

    signals = analyzer.generate_signals(df)

    for category, signal_list in signals.items():
        if signal_list:
            print(f"\n  [{category.upper()}]")
            for signal_type, description in signal_list:
                icon = "[+]" if "BUY" in signal_type or "BULLISH" in signal_type else "[-]" if "SELL" in signal_type or "BEARISH" in signal_type else "[~]"
                print(f"    {icon} {signal_type}: {description}")

    if not any(signals.values()):
        print("\n  No strong signals detected - market in consolidation")

    # Fundamental Analysis
    print(f"\n{'-' * 60}")
    print("  FUNDAMENTAL ANALYSIS")
    print(f"{'-' * 60}")

    fundamental_analysis = analyzer.analyze_fundamentals(company_info, {})

    print(f"\n  Valuation:")
    print(f"    P/E Ratio:    {company_info.get('PERatio', 'N/A')}")
    print(f"    PEG Ratio:    {company_info.get('PEGRatio', 'N/A')}")
    print(f"    P/B Ratio:    {company_info.get('PriceToBookRatio', 'N/A')}")
    for assessment in fundamental_analysis["valuation"]["assessment"]:
        print(f"    [+] {assessment}")

    print(f"\n  Profitability:")
    print(f"    Profit Margin:  {format_percent(company_info.get('ProfitMargin', 0))}")
    print(f"    Operating Marg: {format_percent(company_info.get('OperatingMarginTTM', 0))}")
    print(f"    ROE:            {format_percent(company_info.get('ReturnOnEquityTTM', 0))}")
    for assessment in fundamental_analysis["profitability"]["assessment"]:
        print(f"    [+] {assessment}")

    print(f"\n  Growth (YoY):")
    print(f"    Revenue Growth:  {format_percent(company_info.get('QuarterlyRevenueGrowthYOY', 0))}")
    print(f"    Earnings Growth: {format_percent(company_info.get('QuarterlyEarningsGrowthYOY', 0))}")
    for assessment in fundamental_analysis["growth"]["assessment"]:
        print(f"    [+] {assessment}")

    print(f"\n  Financial Health:")
    print(f"    Debt/Equity:  {company_info.get('DebtToEquity', 'N/A')}")
    print(f"    Current Ratio: {company_info.get('CurrentRatio', 'N/A')}")
    for assessment in fundamental_analysis["financial_health"]["assessment"]:
        print(f"    [+] {assessment}")

    # ML Prediction
    print(f"\n{'-' * 60}")
    print("  ML PRICE PREDICTION")
    print(f"{'-' * 60}")

    model, metrics = analyzer.train_price_predictor(df)

    if model is None:
        print(f"\n  [!] ML Model not trained: {metrics.get('error', 'Unknown error')}")
        print(f"      Note: Free tier Alpha Vantage only provides 100 days of data.")
        print(f"      For ML predictions, you need 200+ days of historical data.")
        prediction = {"direction": "UNKNOWN", "confidence": "N/A", "predicted_return": 0}
    else:
        prediction = analyzer.predict_next_day(model, df)
        print(f"\n  Model Performance:")
        print(f"    R² Score: {metrics['r2']:.4f}")
        print(f"    MSE:      {metrics['mse']:.6f}")
        print(f"\n  Top Feature Importances:")
        for feature, importance in metrics["importance"].head(5).items():
            print(f"    {feature}: {importance:.4f}")

        print(f"\n  Next Day Prediction:")
        print(f"    Direction:  {prediction['direction']}")
        print(f"    Confidence: {prediction['confidence']}")
        print(f"    Expected Return: {prediction['predicted_return'] * 100:.2f}%")

    # Overall Recommendation
    print(f"\n{'=' * 60}")
    print("  OVERALL RECOMMENDATION")
    print(f"{'=' * 60}")

    recommendation = analyzer.generate_overall_recommendation(
        signals,
        fundamental_analysis,
        prediction
    )

    print(f"\n  *** {recommendation['recommendation']} ***")
    print(f"  Composite Score: {recommendation['score']:.1f}")
    print(f"\n  Key Reasons:")
    for i, reason in enumerate(recommendation["reasons"][:7], 1):
        print(f"    {i}. {reason}")

    # Entry/Exit Points
    print(f"\n{'-' * 60}")
    print("  SUGGESTED ENTRY/EXIT POINTS")
    print(f"{'-' * 60}")

    current_price = latest["close"]
    atr = latest["atr"]

    print(f"\n  Current Price: ${current_price:.2f}")
    print(f"  ATR (14-day):  ${atr:.2f}")

    print(f"\n  Entry Zones (if buying):")
    print(f"    Aggressive:  ${current_price * 0.98:.2f}  (-2%)")
    print(f"    Conservative: ${latest['sma_20']:.2f}  (at SMA20)")
    print(f"    Deep Value:   ${latest['sma_50']:.2f}  (at SMA50)")

    print(f"\n  Take Profit Targets:")
    print(f"    Target 1:  ${current_price * 1.05:.2f}  (+5%)")
    print(f"    Target 2:  ${current_price * 1.10:.2f}  (+10%)")
    print(f"    Target 3:  ${current_price * 1.15:.2f}  (+15%)")

    print(f"\n  Stop Loss Levels:")
    print(f"    Tight:     ${current_price * 0.95:.2f}  (-5%)")
    print(f"    Standard:  ${current_price * 0.90:.2f}  (-10%)")
    print(f"    Wide (ATR): ${current_price - (2 * atr):.2f}  (-2 ATR)")

    print(f"\n{'=' * 60}")
    print("  DISCLAIMER: This is for educational purposes only.")
    print("  Not financial advice. Always do your own research.")
    print(f"{'=' * 60}\n")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("\n  Quant Bot - Stock Analysis System")
        print("  ─────────────────────────────────")
        print(f"  Usage: python -m src.cli <SYMBOL>")
        print(f"  Example: python -m src.cli AAPL")
        print(f"           python -m src.cli TSLA")
        print()
        return

    symbol = sys.argv[1]
    analyze_stock(symbol)


if __name__ == "__main__":
    main()
