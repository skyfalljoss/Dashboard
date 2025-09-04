from flask import Blueprint, jsonify, request
from app.db_init import db, Stock, Holding, Portfolio
from app.services.portfolioPerformance import get_portfolio_performance, get_portfolio_allocation
from ..utils.yfinance_helper import fetch_stock_info, fetch_historical_data, get_api_status, reset_api_status

# A Blueprint is Flask's way of organizing a group of related routes.
main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def root():
    """Root endpoint to test if server is running."""
    return jsonify({'message': 'Finance Portfolio Dashboard API is running!'})


def _calculate_live_summary():
    """Helper function to calculate the portfolio summary using real-time data."""
    portfolio = Portfolio.query.first()
    if not portfolio:
        portfolio = Portfolio(cash_balance=100000)
        db.session.add(portfolio)
        db.session.commit()
    holdings = Holding.query.all()
    total_stock_value = 0
    total_cost_basis = 0
    for holding in holdings:
        if not holding.stock: continue
        current_price = holding.stock.current_price
        try:
            info = fetch_stock_info(holding.symbol)
            if info and info.get('current_price') is not None:
                current_price = info['current_price']
        except Exception: pass
        total_stock_value += holding.shares * current_price
        total_cost_basis += holding.shares * holding.avg_price
    total_portfolio_value = total_stock_value + portfolio.cash_balance
    total_gain_loss = total_stock_value - total_cost_basis
    return {
        'totalPortfolioValue': total_portfolio_value,
        'totalGainLoss': total_gain_loss,
        'cashBalance': portfolio.cash_balance,
        'totalHoldings': len(holdings)
    }



# --- Dashboard Read-Only Endpoints ---

@main.route('/summary', methods=['GET'])
def summary():
    """Calculates and returns the current portfolio summary."""
    try:
        portfolio = Portfolio.query.first()
        if not portfolio:
            return jsonify({"error": "No portfolio found."}), 404

        holdings = Holding.query.all()
        if not holdings:
            return jsonify({
                'totalPortfolioValue': portfolio.cash_balance,
                'totalGainLoss': 0,
                'cashBalance': portfolio.cash_balance,
                'totalHoldings': 0
            })

        # Get all symbols for batch processing
        symbols = [h.symbol for h in holdings if h.stock]
        
        # Fetch all prices in a single batch call instead of individual calls
        realtime_prices = {}
        try:
            if symbols:
                # Use batch download to get all prices at once
                data = fetch_historical_data(symbols, period="1d")
                if data is not None and not data.empty:
                    for symbol in symbols:
                        if symbol in data.columns:
                            realtime_prices[symbol] = data[symbol].iloc[-1]
        except Exception as e:
            print(f"Error fetching batch prices for summary: {e}")
            # Continue with stored prices if batch fetch fails

        total_stock_value = 0
        total_cost_basis = 0

        for holding in holdings:
            # Ensure the holding has a valid stock relationship
            if not holding.stock:
                continue

            # Use real-time price if available, otherwise fall back to stored price
            try:
                current_price = realtime_prices.get(holding.symbol, holding.stock.current_price)
            except Exception:
                # If yfinance fails for a symbol, fall back to the last stored price
                current_price = holding.stock.current_price

            total_stock_value += holding.shares * current_price
            total_cost_basis += holding.shares * holding.avg_price

        # The true total portfolio value is the sum of all stocks at their
        # current market price, plus the available cash.
        total_portfolio_value = total_stock_value + portfolio.cash_balance
        total_gain_loss = total_stock_value - total_cost_basis
        
        return jsonify({
            'totalPortfolioValue': total_portfolio_value,
            'totalGainLoss': total_gain_loss,
            'cashBalance': portfolio.cash_balance,
            'totalHoldings': len(holdings)
        })

    except Exception as e:
        print(f"Error calculating summary: {e}")
        return jsonify({"error": "Could not calculate portfolio summary."}), 500



@main.route('/performance', methods=['GET'])
def performance():
    """Endpoint to get historical portfolio performance."""
    return get_portfolio_performance()

@main.route('/allocation', methods=['GET'])
def allocation():
    """Endpoint to get current portfolio asset allocation."""
    return get_portfolio_allocation()

# Search route is handled by the search blueprint
# @main.route('/search', methods=['GET'])
# def search_stocks():
#     """Endpoint to get the list of all searchable stocks."""
#     # Import the search function from the search blueprint
#     from .search import search_stocks as search_stocks_func
#     return search_stocks_func()


# --- CRUD Operations for Holdings ---

# CREATE a new holding
@main.route('/holding/create', methods=['POST'])
def create_holding():
    """Creates a new stock holding in the portfolio."""
    data = request.get_json()
    symbol = data.get('symbol')
    shares = data.get('shares')
    avg_price = data.get('avg_price')

    if not all([symbol, shares, avg_price]):
        return jsonify({'error': 'Missing data. Symbol, shares, and avg_price are required.'}), 400

    if Holding.query.filter_by(symbol=symbol).first():
        return jsonify({'error': f'A holding for {symbol} already exists. Use the update endpoint instead.'}), 409

    if not Stock.query.get(symbol):
        return jsonify({'error': f'Stock symbol {symbol} not found in the database.'}), 404

    new_holding = Holding(symbol=symbol, shares=float(shares), avg_price=float(avg_price))
    db.session.add(new_holding)
    db.session.commit()
    
    return jsonify({'message': f'Successfully created holding for {symbol}.'}), 201

# READ all holdings
@main.route('/holdings', methods=['GET'])
def get_holdings():
    """Reads and returns all current stock holdings."""
    holdings_query = Holding.query.all()
    holdings_list = []
    for holding in holdings_query:
        if holding.stock:
            holdings_list.append({
                'id': holding.id, # Crucial for Update and Delete operations on the frontend
                'symbol': holding.symbol,
                'name': holding.stock.name,
                'shares': holding.shares,
                'avgPrice': holding.avg_price,
                'currentPrice': holding.stock.current_price
            })
    return jsonify(holdings_list)

# UPDATE an existing holding
@main.route('/holding/update/<int:holding_id>', methods=['PUT'])
def update_holding(holding_id):
    """Updates the shares or average price of an existing holding."""
    # get_or_404 is a handy shortcut that returns a 404 error if the ID is not found.
    holding = Holding.query.get_or_404(holding_id)
    data = request.get_json()

    if 'shares' in data:
        holding.shares = float(data['shares'])
    if 'avg_price' in data:
        holding.avg_price = float(data['avg_price'])

    db.session.commit()
    return jsonify({'message': f'Successfully updated holding for {holding.symbol}.'})

# DELETE a holding
@main.route('/holding/delete/<int:holding_id>', methods=['DELETE'])
def delete_holding(holding_id):
    """Deletes a stock holding from the portfolio."""
    holding = Holding.query.get_or_404(holding_id)
    symbol = holding.symbol # Get the symbol for the confirmation message
    db.session.delete(holding)
    db.session.commit()
    return jsonify({'message': f'Successfully deleted holding for {symbol}.'})

@main.route('/status', methods=['GET'])
def api_status():
    """Get the current status of the API rate limiting and Yahoo Finance health"""
    return jsonify(get_api_status())

@main.route('/status/reset', methods=['POST'])
def reset_api_status():
    """Manually reset the API status and clear cache"""
    reset_api_status()
    return jsonify({'message': 'API status reset successfully'})

@main.route('/test-yahoo', methods=['GET'])
def test_yahoo():
    """Test Yahoo Finance connectivity"""
    from ..utils.yfinance_helper import check_yahoo_health
    is_healthy = check_yahoo_health()
    return jsonify({
        'yahoo_finance_working': is_healthy,
        'message': 'Yahoo Finance is working' if is_healthy else 'Yahoo Finance is not responding'
    })

