# Dashboard/backend/app/routes/search.py
from flask import Blueprint, jsonify, request
from ..utils.yfinance_helper import fetch_stock_info, fetch_historical_data
from ..db_init import Holding
import yfinance as yf
import pandas as pd

ALPHA_VANTAGE_API_KEY = 'HWWZLX4BAWS7ID80'
# 5D620U1VSLBYFJV3
search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
def search_stocks():
    """
    Searches for stocks using yfinance directly or returns popular stocks.
    """
    query = request.args.get('q', '').strip().upper()

    # If no query, return popular stocks
    if not query:
        return get_user_holdings()

    # Otherwise, search using yfinance
    return search_with_yfinance(query)
    # return search_with_alpha_vantage(query) 

def get_user_holdings():
    """
    Returns the user's current holdings with live data from yfinance.
    """
    holdings = Holding.query.all()
    if not holdings:
        return jsonify([])

    symbols = [holding.symbol for holding in holdings]
    
    try:
        # Use the rate-limited helper function instead of direct yf.download
        data = fetch_historical_data(symbols, period="2d")
        if data is None or data.empty:
            return jsonify([])

        holdings_results = []
        for holding in holdings:
            try:
                symbol = holding.symbol
                if symbol in data.columns:
                    current_price = data[symbol].iloc[-1]
                    prev_close = data[symbol].iloc[-2] if len(data) > 1 else current_price
                    
                    if prev_close != 0:
                        change_percent = ((current_price - prev_close) / prev_close) * 100
                        change_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"
                    else:
                        change_str = "0.00%"

                    holdings_results.append({
                        'symbol': symbol,
                        'name': holding.stock.name if holding.stock else symbol,
                        'price': current_price,
                        'change': change_str
                    })
            except Exception as e:
                print(f"Error processing data for {holding.symbol}: {e}")
                continue
                
        return jsonify(holdings_results)
    except Exception as e:
        print(f"Error fetching batch data: {e}")
        return jsonify([])

def search_with_yfinance(query):
    """
    Search for stocks using yfinance directly.
    """
    try:
        stock_info = fetch_stock_info(query)
        if stock_info and stock_info.get('current_price') is not None:
            change_percent = stock_info.get('change_percent', 0)
            change_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"

            return jsonify([{
                'symbol': stock_info['symbol'],
                'name': stock_info.get('name', query),
                'price': stock_info['current_price'],
                'change': change_str
            }])
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error in yfinance search: {e}")
        return jsonify([])
    
# def search_with_alpha_vantage(query):
#     """
#     Searches for stocks using the Alpha Vantage API and enriches with yfinance data.
#     """
#     url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={ALPHA_VANTAGE_API_KEY}"
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         data = response.json()

#         best_matches = data.get('bestMatches', [])
#         if not best_matches:
#             return jsonify([])

#         search_results = []
#         for match in best_matches:
#             symbol = match.get('1. symbol')
#             # Filter out non-US markets for relevance, if desired
#             if symbol and '.' not in symbol:
#                 try:
#                     # Fetch live info to ensure price/change is current
#                     stock_info = fetch_stock_info(symbol)
#                     if stock_info and stock_info.get('current_price') is not None:
#                         change_percent = stock_info.get('change_percent', 0)
#                         change_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"

#                         search_results.append({
#                             'symbol': stock_info['symbol'],
#                             'name': stock_info.get('name', match.get('2. name')),
#                             'price': stock_info['current_price'],
#                             'change': change_str
#                         })
#                 except Exception as e:
#                     print(f"Error fetching live data for matched stock {symbol}: {e}")
#                     continue
        
#         return jsonify(search_results)

#     except requests.exceptions.RequestException as e:
#         print(f"Error calling Alpha Vantage API: {e}")
#         return jsonify({"error": "Failed to connect to the stock search service."}), 500
#     except Exception as e:
#         print(f"An error occurred during search: {e}")
#         return jsonify({"error": "An unexpected error occurred during search."}), 500
    

def search_with_alpha_vantage(query):
    """
    Searches for stocks using the Alpha Vantage API and enriches with yfinance data.
    """
    # FIX: Use the API key from your app's configuration, not a hardcoded one
    api_key = ALPHA_VANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        best_matches = data.get('bestMatches', [])
        if not best_matches:
            return jsonify([])

        search_results = []
        for match in best_matches:
            symbol = match.get('1. symbol')
            if symbol and '.' not in symbol:
                try:
                    stock_info = fetch_stock_info(symbol)
                    if stock_info and stock_info.get('current_price') is not None:
                        change_percent = stock_info.get('change_percent', 0)
                        change_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"
                        search_results.append({
                            'symbol': stock_info['symbol'],
                            'name': stock_info.get('name', match.get('2. name')),
                            'price': stock_info['current_price'],
                            'change': change_str
                        })
                    else:
                        search_results.append({
                            'symbol': symbol,
                            'name': match.get('2. name'),
                            'price': 'N/A',
                            'change': 'N/A'
                        })
                except Exception as e:
                    print(f"Error fetching live data for matched stock {symbol}: {e}")
                    search_results.append({
                        'symbol': symbol,
                        'name': match.get('2. name'),
                        'price': 'N/A',
                        'change': 'N/A'
                    })
                    continue
        
        return jsonify(search_results)

    except requests.exceptions.RequestException as e:
        print(f"Error calling Alpha Vantage API: {e}")
        return jsonify({"error": "Failed to connect to the stock search service."}), 500
    except Exception as e:
        print(f"An error occurred during search: {e}")
        return jsonify({"error": "An unexpected error occurred during search."}), 500