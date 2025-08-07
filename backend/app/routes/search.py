# Dashboard/backend/app/routes/search.py
from flask import Blueprint, jsonify, request
from ..utils.yfinance_helper import fetch_stock_info

search_bp = Blueprint('search', __name__)

# Popular stocks to display by default
POPULAR_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
    'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'ADBE'
]

@search_bp.route('/search', methods=['GET'])
def search_stocks():
    """
    Searches for stocks using yfinance directly or returns popular stocks.
    """
    query = request.args.get('q', '').strip().upper()

    # If no query, return popular stocks
    if not query:
        return get_popular_stocks()

    # Otherwise, search using yfinance
    return search_with_yfinance(query)

def get_popular_stocks():
    """
    Returns popular stocks with live data from yfinance.
    """
    popular_results = []
    for symbol in POPULAR_STOCKS:
        try:
            stock_info = fetch_stock_info(symbol)
            if stock_info and stock_info.get('current_price') is not None:
                change_percent = stock_info.get('change_percent', 0)
                change_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"

                popular_results.append({
                    'symbol': symbol,
                    'name': stock_info.get('name', symbol),
                    'price': stock_info['current_price'],
                    'change': change_str
                })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            continue
    return jsonify(popular_results)

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