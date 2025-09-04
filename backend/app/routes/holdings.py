# app/routes/holdings.py
from flask import Blueprint, jsonify, request
from ..db_init import Holding, db
from ..utils.yfinance_helper import fetch_stock_info, fetch_historical_data

import yfinance as yf

holdings_bp = Blueprint('holdings', __name__)

@holdings_bp.route('/holdings', methods=['GET'])
def get_holdings():
    """
    Retrieves all current stock holdings and updates them with
    the latest real-time price from yfinance in a single call.
    """
    try:
        holdings_query = Holding.query.all()
        holdings_list = []

        # --- BATCH DATA FETCHING ---
        # 1. Get all symbols from holdings
        symbols = [h.symbol for h in holdings_query if h.stock]
        
        if not symbols:
            return jsonify([])

        # 2. Fetch all data using the rate-limited helper function
        realtime_data_map = {}
        try:
            # Use the rate-limited helper instead of direct yf.download
            data = fetch_historical_data(symbols, period="2d")
            if data is not None and not data.empty:
                # Create a map of current prices and changes
                for symbol in symbols:
                    try:
                        if symbol in data.columns:
                            current_price = data[symbol].iloc[-1]
                            prev_close = data[symbol].iloc[-2] if len(data) > 1 else current_price
                            change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0
                            
                            realtime_data_map[symbol] = {
                                'current_price': current_price,
                                'change_percent': change
                            }
                    except Exception as e:
                        print(f"Error processing data for {symbol}: {e}")
                        continue
        except Exception as e:
            print(f"Error fetching batch data: {e}")
            realtime_data_map = {}

        # 3. Process each holding with fallback to stored data
        for holding in holdings_query:
            # Ensure the associated stock relationship exists before proceeding
            if not holding.stock:
                print(f"Skipping holding with symbol {holding.symbol} as it has no associated stock entry.")
                continue

            try:
                # Try to get real-time data first
                realtime_info = realtime_data_map.get(holding.symbol)
                
                if realtime_info and realtime_info.get('current_price') is not None:
                    current_price = realtime_info['current_price']
                    # Update the price in the database
                    holding.stock.current_price = current_price
                    print(f"Updated {holding.symbol} with real-time price: {current_price}")
                else:
                    # Fallback to stored price if real-time fetch failed
                    current_price = holding.stock.current_price
                    print(f"Using stored price for {holding.symbol}: {current_price}")

                holdings_list.append({
                    'symbol': holding.symbol,
                    'name': holding.stock.name,
                    'shares': holding.shares,
                    'avgPrice': holding.avg_price,
                    'currentPrice': current_price,
                })

            except Exception as e:
                # If an error occurs for one stock, log it and continue with the others
                print(f"Error processing holding for {holding.symbol}: {e}")
                # Still add the holding with stored data
                holdings_list.append({
                    'symbol': holding.symbol,
                    'name': holding.stock.name,
                    'shares': holding.shares,
                    'avgPrice': holding.avg_price,
                    'currentPrice': holding.stock.current_price,
                })
                continue
        
        # Commit any price updates to the database
        db.session.commit()
        
        return jsonify(holdings_list)

    except Exception as e:
        db.session.rollback()
        print(f"A critical error occurred while fetching holdings: {e}")
        return jsonify({"error": "Could not retrieve holdings due to a server error."}), 500