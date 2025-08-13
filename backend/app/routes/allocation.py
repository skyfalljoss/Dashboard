# app/routes/allocation.py
from flask import Blueprint, jsonify
from ..db_init import Holding, db

allocation_bp = Blueprint('allocation', __name__)

# --- Asset Allocation Endpoint ---
# Note: Cash and Bonds values are static placeholders as in the original example.
# In a full application, these might come from the database or other sources.
STATIC_CASH_VALUE = 12450.00
STATIC_BONDS_VALUE = 28447.00

@allocation_bp.route('/allocation', methods=['GET'])
def get_allocation():
    """
    Calculates the current asset allocation of the portfolio.
    Includes Stocks (based on current holdings), Bonds, and Cash.
    """
    # 1. Calculate total value of stock holdings
    holdings = Holding.query.all()
    stocks_value = sum(h.shares * h.stock.current_price for h in holdings if h.stock)

    # 2. Prepare allocation data
    allocation_data = {
        'labels': ['Stocks', 'Bonds', 'Cash'],
        'values': [stocks_value, STATIC_BONDS_VALUE, STATIC_CASH_VALUE],
        'colors': ['#4285f4', '#6fa8f7', '#a3c4f9']
    }
    return jsonify(allocation_data)
