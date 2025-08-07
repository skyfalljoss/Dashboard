import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
from flask import jsonify
from app.models import db, Stock, Holding

def get_portfolio_performance():
    """
    Calculates the historical performance of the portfolio with robust error handling.
    """
    holdings = Holding.query.all()
    if not holdings:
        return jsonify({'labels': [], 'values': []})

    symbols = [h.symbol for h in holdings]
    shares_map = {h.symbol: h.shares for h in holdings}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"Fetching performance data for symbols: {symbols}")

    try:
        # Download historical data from yfinance
        hist_data_full = yf.download(symbols, start=start_date, end=end_date)
        
        if hist_data_full.empty:
            print("Warning: yfinance returned an empty DataFrame.")
            return jsonify({'labels': [], 'values': []})
        
        # Correctly access the 'Close' prices, handling single vs. multi-symbol responses
        hist_data = hist_data_full.get('Close')
        if hist_data is None:
             print("Warning: 'Close' column not found in yfinance data.")
             return jsonify({'labels': [], 'values': []})

    except Exception as e:
        print(f"Error during yfinance download: {e}")
        return jsonify({'error': 'Failed to fetch performance data from the provider.'}), 500

    if isinstance(hist_data, pd.Series):
        hist_data = hist_data.to_frame(name=symbols[0])
    
    if hist_data.empty:
        print("Warning: No 'Close' price data was found after processing.")
        return jsonify({'labels': [], 'values': []})

    monthly_data = hist_data.ffill().resample('M').last()
    
    portfolio_values = []
    for date, prices in monthly_data.iterrows():
        monthly_total = 0
        for symbol, shares in shares_map.items():
            if symbol in prices and pd.notna(prices[symbol]):
                 monthly_total += shares * prices[symbol]
        portfolio_values.append(round(monthly_total, 2))

    performance_data = {
        'labels': monthly_data.index.strftime('%b %Y').tolist(),
        'values': portfolio_values
    }
    return jsonify(performance_data)


def get_portfolio_allocation():
    """Calculates the asset allocation of the portfolio."""
    holdings = Holding.query.all()
    stocks_value = sum(h.shares * h.stock.current_price for h in holdings if h.stock)
    cash_value = 12450.00 
    bonds_value = 28447.00 

    allocation_data = {
        'labels': ['Stocks', 'Bonds', 'Cash'],
        'values': [stocks_value, bonds_value, cash_value],
        'colors': ['#4285f4', '#6fa8f7', '#a3c4f9']
    }
    return jsonify(allocation_data)

def seed_database_with_data():
    """
    Drops all existing tables, creates new ones, and seeds them with
    initial data from Yahoo Finance.
    """
    db.drop_all()
    db.create_all()

    symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 
        'NFLX', 'CRM', 'ADBE', 'PYPL', 'INTC', 'AMD', 'ORCL', 'IBM'
    ]
    
    print("Fetching live stock data from Yahoo Finance...")
    
    for symbol in symbols:
        time.sleep(0.5) 
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            prev_close = info.get('previousClose')
            
            if current_price and prev_close:
                change = ((current_price - prev_close) / prev_close) * 100
                stock = Stock(
                    symbol=symbol,
                    name=info.get('longName', symbol),
                    current_price=current_price,
                    change_percent=change
                )
                db.session.add(stock)
                print(f"Successfully fetched data for {symbol}")
            else:
                print(f"Could not retrieve complete pricing data for {symbol}")
        except Exception as e:
            print(f"An error occurred fetching data for {symbol}: {e}")

    holdings_data = [
        {'symbol': 'AAPL', 'shares': 50, 'avgPrice': 150.00},
        {'symbol': 'MSFT', 'shares': 30, 'avgPrice': 280.00},
        {'symbol': 'GOOGL', 'shares': 25, 'avgPrice': 120.00},
        {'symbol': 'AMZN', 'shares': 40, 'avgPrice': 90.00},
        {'symbol': 'TSLA', 'shares': 20, 'avgPrice': 200.00},
    ]

    for h in holdings_data:
        holding = Holding(symbol=h['symbol'], shares=h['shares'], avg_price=h['avgPrice'])
        db.session.add(holding)

    db.session.commit()
    print("Database has been seeded.")

