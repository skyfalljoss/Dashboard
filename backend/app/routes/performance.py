from flask import Blueprint, jsonify
import pandas as pd
from ..models import Holding, db
from ..utils.yfinance_helper import fetch_historical_data
import yfinance as yf

performance_bp = Blueprint('performance', __name__)

@performance_bp.route('/performance', methods=['GET'])
def get_performance():
    """
    Calculates the historical performance of the portfolio over the last 12 months
    based on the current holdings.
    """
    # 1. Get all current holdings from the database
    holdings = Holding.query.all()
    if not holdings:
        # If there are no stocks held, return empty data for the chart
        return jsonify({'labels': [], 'values': []})

    symbols = [h.symbol for h in holdings]
    shares_map = {h.symbol: h.shares for h in holdings}

    # 2. Define the time period for the historical data (past 12 months)
    
    try:
        # 3. Fetch historical daily closing prices for all held stocks at once
        hist_data = fetch_historical_data(symbols,"1y")
        if hist_data is None:
             # fetch_historical_data logs the error
            return jsonify({'error': 'Failed to fetch performance data from provider'}), 500
    except Exception as e:
        print(f"Unexpected error in performance endpoint: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

    # If only one stock is held, yfinance returns a pandas Series.
    # We convert it to a DataFrame for consistent processing.
    
    # if isinstance(hist_data, pd.Series):
    #     hist_data = hist_data.to_frame(name=symbols[0])

    # 4. Calculate the portfolio's value over time
    # Forward-fill missing values (for weekends/holidays) then resample to get the last price of each month
    monthly_data = hist_data.ffill().resample('M').last()
    
    portfolio_values = []
    for date, prices in monthly_data.iterrows():
        monthly_total = 0
        for symbol, shares in shares_map.items():
            # Multiply the number of shares by the stock's price for that month
            if symbol in prices and pd.notna(prices[symbol]):
                 monthly_total += shares * prices[symbol]
        portfolio_values.append(round(monthly_total, 2))

    # 5. Format the data for the frontend chart
    performance_data = {
        'labels': monthly_data.index.strftime('%b %Y').tolist(), # Format as 'Jan 2023'
        'values': portfolio_values
    }
    return jsonify(performance_data)


# def get_performance():
#     """
#     Calculates the historical performance of the portfolio with robust error handling.
#     """
#     holdings = Holding.query.all()
#     if not holdings:
#         return jsonify({'labels': [], 'values': []})

#     symbols = [h.symbol for h in holdings]
#     shares_map = {h.symbol: h.shares for h in holdings}

#     end_date = datetime.now()
#     start_date = end_date - timedelta(days=365)
    
#     print(f"Fetching performance data for symbols: {symbols}")

#     try:
#         # Download historical data from yfinance
#         hist_data_full = yf.download(symbols, start=start_date, end=end_date)
        
#         if hist_data_full.empty:
#             print("Warning: yfinance returned an empty DataFrame.")
#             return jsonify({'labels': [], 'values': []})
        
#         # Correctly access the 'Close' prices, handling single vs. multi-symbol responses
#         hist_data = hist_data_full.get('Close')
#         if hist_data is None:
#              print("Warning: 'Close' column not found in yfinance data.")
#              return jsonify({'labels': [], 'values': []})

#     except Exception as e:
#         print(f"Error during yfinance download: {e}")
#         return jsonify({'error': 'Failed to fetch performance data from the provider.'}), 500

#     if isinstance(hist_data, pd.Series):
#         hist_data = hist_data.to_frame(name=symbols[0])
    
#     if hist_data.empty:
#         print("Warning: No 'Close' price data was found after processing.")
#         return jsonify({'labels': [], 'values': []})

#     monthly_data = hist_data.ffill().resample('M').last()
    
#     portfolio_values = []
#     for date, prices in monthly_data.iterrows():
#         monthly_total = 0
#         for symbol, shares in shares_map.items():
#             if symbol in prices and pd.notna(prices[symbol]):
#                  monthly_total += shares * prices[symbol]
#         portfolio_values.append(round(monthly_total, 2))

#     performance_data = {
#         'labels': monthly_data.index.strftime('%b %Y').tolist(),
#         'values': portfolio_values
#     }
#     return jsonify(performance_data)
