# app/routes/holdings.py
from flask import Blueprint, jsonify, request
from ..db_init import Holding, db
from ..utils.yfinance_helper import fetch_stock_info

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

        for holding in holdings_query:
            # Ensure the associated stock relationship exists before proceeding
            if not holding.stock:
                print(f"Skipping holding with symbol {holding.symbol} as it has no associated stock entry.")
                continue

            try:
                # Fetch fresh, real-time data for each holding
                realtime_info = fetch_stock_info(holding.symbol)
                
                if realtime_info and realtime_info.get('current_price') is not None:
                    current_price = realtime_info['current_price']
                    # Optionally, update the price in the database as well
                    holding.stock.current_price = current_price
                else:
                    # If the real-time fetch fails, fall back to the last stored price
                    print(f"Could not fetch real-time price for {holding.symbol}. Using stored price.")
                    current_price = holding.stock.current_price

                holdings_list.append({
                    'symbol': holding.symbol,
                    'name': holding.stock.name,
                    'shares': holding.shares,
                    'avgPrice': holding.avg_price,
                    'currentPrice': current_price
                })

            except Exception as e:
                # If an error occurs for one stock, log it and continue with the others
                print(f"Error processing holding for {holding.symbol}: {e}")
                continue
        
        # Commit any price updates to the database
        db.session.commit()
        
        return jsonify(holdings_list)

    except Exception as e:
        db.session.rollback()
        print(f"A critical error occurred while fetching holdings: {e}")
        return jsonify({"error": "Could not retrieve holdings due to a server error."}), 500