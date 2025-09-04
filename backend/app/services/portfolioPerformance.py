import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from flask import jsonify
from app.db_init import db, Stock, Holding, Transaction, Portfolio
from app.utils.yfinance_helper import fetch_historical_data

def get_portfolio_performance():   
    """
    Calculates the historical performance of the portfolio with robust error handling.
    """
    try:
        transactions = Transaction.query.order_by(Transaction.txn_date.asc()).all()
        portfolio = Portfolio.query.first()
        current_cash  = portfolio.cash_balance if portfolio else 0
        print(f"Initial cash balance: {current_cash}")
        
        if not transactions:
            return jsonify({'labels': [], 'values': []})

        symbols = list(set(t.symbol for t in transactions))
        
        start_date = transactions[0].txn_date
        end_date = datetime.now()

        
        cash_at_period_start = current_cash 
        # Add this check to handle future-dated transactions
        if start_date > end_date:
            print("First transaction is in the future. Returning empty performance data.")
            return jsonify({'labels': [], 'values': []})
        
        for t in transactions:
            if t.txn_date >= start_date:
                if t.transaction_type == 'BUY':
                    cash_at_period_start += t.amount
                elif t.transaction_type == 'SELL':
                    cash_at_period_start -= t.amount

        initial_cash = cash_at_period_start
        print(f"Cash at period start ({start_date.date()}): {initial_cash}")

        # Use the rate-limited helper function instead of direct yf.download
        hist_data = fetch_historical_data(symbols, period='1y')
        if hist_data is None:
            return jsonify({'labels': [], 'values': []})
            
        if isinstance(hist_data, pd.Series):
            hist_data = hist_data.to_frame(name=symbols[0])

        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        portfolio_values = []
        
        for date in dates:
            cash_balance = initial_cash
            holdings_on_date = {}
            print("" + "_" * 40)
            for t in transactions:
                if t.txn_date.date() <= date.date():
                    if t.transaction_type == 'BUY':
                        holdings_on_date[t.symbol] = holdings_on_date.get(t.symbol, 0) + t.shares
                        cash_balance -= t.amount
                    elif t.transaction_type == 'SELL':
                        holdings_on_date[t.symbol] = holdings_on_date.get(t.symbol, 0) - t.shares
                        cash_balance += t.amount
            
            total_value = cash_balance
            print(f'Date: {date}, Cash: {cash_balance}, Holdings: {holdings_on_date}')
            for symbol, shares in holdings_on_date.items():
                if shares > 0 and symbol in hist_data.columns:
                    try:
                        price_on_date = hist_data.loc[hist_data.index.asof(date), symbol]
                        print(f'  {symbol}: {shares} shares at {price_on_date} each')
                        if pd.notna(price_on_date):
                            total_value += shares * price_on_date
                            print(f'  {symbol}: {shares} shares at {price_on_date} each, Total: {shares * price_on_date}')
                    except KeyError:
                        continue
            portfolio_values.append(round(total_value, 2))

        daily_labels = [d.strftime('%b %d, %Y') for d in dates]
        print("" + "-" * 40)
        print(portfolio_values)
        if not portfolio_values:
            return jsonify({'labels': [], 'values': []})
        
        # Format the data for the frontend chart
        if len(daily_labels) > 12:
            daily_labels = daily_labels[::len(daily_labels) // 12]
            portfolio_values = portfolio_values[::len(portfolio_values) // 12]  
        elif len(daily_labels) < 12:
            daily_labels = daily_labels + [daily_labels[-1]] * (12 - len(daily_labels))
            portfolio_values = portfolio_values + [portfolio_values[-1]] * (12 - len(portfolio_values))
        elif len(daily_labels) == 12:
            daily_labels = daily_labels[:12]
            portfolio_values = portfolio_values[:12]
        if len(daily_labels) != len(portfolio_values):
            print("Warning: Mismatch in daily labels and portfolio values length.")
        if len(daily_labels) == 0 or len(portfolio_values) == 0:
            return jsonify({'labels': [], 'values': []})
        
        performance_data = {
            'labels': daily_labels,
            'values': portfolio_values
        }
        return jsonify(performance_data)

    except Exception as e:
        print(f"Error calculating historical performance: {e}")
        return jsonify({'error': 'Failed to calculate historical performance.'}), 500


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
    
    # Use batch download with proper delays instead of individual calls
    try:
        # Download all symbols at once with a single API call
        hist_data = yf.download(symbols, period="1d", progress=False)
        if not hist_data.empty:
            for symbol in symbols:
                try:
                    if symbol in hist_data['Close'].columns:
                        current_price = hist_data['Close'][symbol].iloc[-1]
                        prev_close = hist_data['Close'][symbol].iloc[-1]  # Same as current for 1d period
                        
                        if current_price and prev_close:
                            change = 0  # No change for 1-day period
                            stock = Stock(
                                symbol=symbol,
                                name=symbol,  # Will be updated later if needed
                                current_price=current_price,
                                change_percent=change
                            )
                            db.session.add(stock)
                            print(f"Successfully fetched data for {symbol}")
                        else:
                            print(f"Could not retrieve complete pricing data for {symbol}")
                except Exception as e:
                    print(f"An error occurred processing data for {symbol}: {e}")
    except Exception as e:
        print(f"Error in batch download: {e}")
        # Fallback to individual calls with longer delays
        for symbol in symbols:
            time.sleep(2)  # Increased delay to 2 seconds
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

