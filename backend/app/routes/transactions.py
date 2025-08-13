# app/routes/transactions.py
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from ..db_init import Stock, Holding, Transaction, db, Portfolio
from datetime import datetime
from ..utils.yfinance_helper import fetch_stock_info

transactions_bp = Blueprint('transactions', __name__)

def _calculate_live_summary():
    """
    Helper function to calculate the portfolio summary using real-time data.
    This ensures the returned data is always fresh after a transaction.
    """
    portfolio = Portfolio.query.first()
    if not portfolio:
        # This case should ideally be handled upon app initialization
        return {
            'totalPortfolioValue': 0, 'totalGainLoss': 0,
            'cashBalance': 0, 'totalHoldings': 0
        }

    holdings = Holding.query.all()
    total_stock_value = 0
    total_cost_basis = 0

    for holding in holdings:
        if not holding.stock:
            continue
        
        current_price = holding.stock.current_price # Default to stored price
        try:
            # Fetch fresh price from yfinance
            info = fetch_stock_info(holding.symbol)
            if info and info.get('current_price') is not None:
                current_price = info['current_price']
                # Also update the DB for consistency on next non-realtime load
                holding.stock.current_price = current_price
        except Exception as e:
            print(f"Could not fetch real-time price for {holding.symbol} during summary calc. Using stored price. Error: {e}")

        total_stock_value += holding.shares * current_price
        total_cost_basis += holding.shares * holding.avg_price

    # Commit any price updates that were fetched
    db.session.commit()

    total_portfolio_value = total_stock_value + portfolio.cash_balance
    total_gain_loss = total_stock_value - total_cost_basis

    return {
        'totalPortfolioValue': total_portfolio_value,
        'totalGainLoss': total_gain_loss,
        'cashBalance': portfolio.cash_balance,
        'totalHoldings': len(holdings)
    }

@transactions_bp.route('/stock/add', methods=['POST'])
def add_stock():
    """
    Adds a stock to the portfolio.
    If the stock already exists in holdings, increases the share count.
    Otherwise, creates a new holding.
    Records the transaction.
    """
    data = request.get_json()
    symbol = data.get('symbol')
    shares = data.get('shares')

    if not symbol or not shares:
        return jsonify({'error': 'Stock symbol/Shares is required'}), 400

    try:
        shares_to_add = int(shares)
        if shares_to_add <= 0:
            return jsonify({'error': 'Shares must be a positive number.'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid number of shares.'}), 400

    # 1. Always fetch the latest data from the external API first
    info = fetch_stock_info(symbol)
    
    # Validate data received from API
    if not info:
        print(f"Failed to fetch data for {symbol} from API.")
        return jsonify({'error': f'Could not retrieve data for stock symbol {symbol} from the market data provider (API fetch failed).'}), 404

    curr_price = info.get('current_price')
    name = info.get('name', f"Unknown Company ({symbol})") # Provide fallback name

    if curr_price is None: # Use 'is None' for explicit check
        print(f"Current price is missing for {symbol} from API data.")
        return jsonify({'error': f'Current price is unavailable for stock symbol {symbol} from the market data provider.'}), 404


    # 2. Check if the stock exists in our database
    stock_to_add = Stock.query.get(symbol)
    
    # --- Corrected Logic for Upsert ---
    try:
        if stock_to_add:
            # --- Update existing stock ---
            print(f"Stock {symbol} found locally. Updating with fresh data from API.")
            
            # Calculate change_percent BEFORE updating current_price
            old_price = stock_to_add.current_price
            # Avoid division by zero
            if old_price and old_price != 0:
                 change_percent = ((curr_price - old_price) / old_price) * 100
            else:
                 change_percent = 0.0 # Or handle as appropriate if old_price is 0/None

            # Update the stock record with fresh data
            stock_to_add.name = name # Update name as well, in case it changed?
            stock_to_add.current_price = curr_price
            # Assuming change_percent is a float field in your model
            stock_to_add.change_percent = change_percent 
            # e.g., stock_to_add.last_updated = datetime.utcnow() 
            print(f"Updated {symbol}: Price {old_price} -> {curr_price}, Change: {change_percent:.2f}%")
            
        else:
            # --- Create a new stock record ---
            print(f"Stock {symbol} not found locally. Creating new record from API data.")
            
            # For a new stock, there's no previous price to compare for change_percent.
            # We can set it to 0 or omit it. Let's set it to 0.0.
            # Alternatively, if change_percent isn't required on creation, don't set it here.
            new_change_percent = 0.0 

            stock_to_add = Stock(
                symbol=symbol,
                name=name,
                current_price=curr_price,
                change_percent=new_change_percent # Set to 0 for new stocks
                # Add other fields if needed, e.g., last_updated
            )
            db.session.add(stock_to_add)
            print(f"Created new stock record for {symbol} at price {curr_price}")
        
        # Flush to ensure the Stock object is tracked for the rest of the transaction
        db.session.flush() 
    except Exception as fetch_or_create_error:
        # Handle potential errors during the fetch/process/creation step
        db.session.rollback() # Rollback in case of error during upsert
        print(f"Error processing/updating/creating stock {symbol} from API data: {fetch_or_create_error}")
        # Check if it's a specific data issue or a general error
        if "division by zero" in str(fetch_or_create_error).lower():
            return jsonify({'error': f'Calculation error (e.g., division by zero) for stock {symbol}. Data might be inconsistent.'}), 500
        else:
            return jsonify({'error': f'An error occurred while processing data for stock {symbol}.'}), 500
    # --- End Corrected Logic for Upsert ---       

    try:
        portfolio = Portfolio.query.first()
        if not portfolio:
            return jsonify({'error': 'Portfolio not found.'}), 404
        # 2. Check for existing holding
       
        transaction_price = stock_to_add.current_price # Use current price for transaction
        transaction_cost = shares_to_add * transaction_price

        if transaction_cost > portfolio.cash_balance:
            return jsonify({'error': 'Insufficient cash balance.'}), 400
        
        
        # 3. Check for existing holding
        existing_holding = Holding.query.filter_by(symbol=symbol).first()
        if existing_holding:
            # 3a. Update existing holding
            old_shares = existing_holding.shares
            old_avg_price = existing_holding.avg_price

            new_shares = old_shares + shares_to_add
            # Recalculate average price: (Total Cost Old + Total Cost New) / New Total Shares
            new_total_cost = (old_shares * old_avg_price) + (shares_to_add * transaction_price)
            new_avg_price = new_total_cost / new_shares if new_shares > 0 else 0

            existing_holding.shares = new_shares
            existing_holding.avg_price = new_avg_price

            message = f'Successfully added {shares_to_add} more shares of {symbol} to your portfolio.'
        else:
            # 3b. Create new holding
            # Example: Buy at current price (could be modified to use a different price)
            new_holding = Holding(
                symbol=symbol,
                shares=shares_to_add,
                avg_price=transaction_price # Initial avg price is the buy price
                
            )
            db.session.add(new_holding)
            message = f'Successfully added {shares_to_add} shares of {symbol} to your portfolio.'

        # 4. Record the transaction
        transaction_record = Transaction(
            symbol=symbol,
            transaction_type='BUY',
            shares=shares_to_add,
            price=transaction_price,
            amount=shares_to_add * transaction_price,
            txn_date=datetime.utcnow()
        )

        db.session.add(transaction_record)
        new_summary = _calculate_live_summary()

        portfolio.cash_balance -= transaction_cost

        db.session.commit()
        return jsonify({
            'message': message,
            'summary': new_summary
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error adding stock {symbol}: {e}")
        return jsonify({'error': 'A database error occurred while adding the stock.'}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error adding stock {symbol}: {e}")
        return jsonify({'error': 'An unexpected error occurred while adding the stock.'}), 500


@transactions_bp.route('/stock/sell', methods=['POST'])
def sell_stock():
    """
    Sells all shares of a stock from the portfolio.
    Records the transaction.
    """
    print("sell")
    data = request.get_json()
    symbol = data.get('symbol')
    shares = data.get('shares')

    if not symbol or not shares:
        return jsonify({'error': 'Stock symbol/Shares is required','':''}), 400

    try:
        shares_to_sell = int(shares)
        if shares_to_sell <= 0:
            return jsonify({'error': 'Shares must be a positive number.','':''}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid number of shares.','':''}), 400
    try:
        # 1. Find the holding to sell
        holding_to_sell = Holding.query.filter_by(symbol=symbol).first()
        if not holding_to_sell:
            return jsonify({'error': 'Holding not found in portfolio','':''}), 404

        portfolio = Portfolio.query.first()
        if not portfolio:
            return jsonify({'error': 'Portfolio not found.','':''}), 404

        if shares_to_sell > holding_to_sell.shares:
            return jsonify({'error': 'Insufficient shares to sell.','':''}), 400
    
        
        # shares_sold = holding_to_sell.shares

        stock_info = fetch_stock_info(symbol)
        if not stock_info:  
            return jsonify({'error': f'Could not retrieve data for stock symbol {symbol} from the market data provider.'}), 404
        # Use the current price from the fetched stock info
        if 'current_price' not in stock_info:   
            return jsonify({'error': f'Current price is unavailable for stock symbol {symbol} from the market data provider.'}), 404.
        # Ensure current_price is available
        if stock_info['current_price'] is None:
            return jsonify({'error': f'Current price is unavailable for stock symbol {symbol} from the market data provider.'}), 404
        # Use the current price for the transaction
        holding_to_sell.stock.current_price = stock_info['current_price']
        transaction_price = holding_to_sell.stock.current_price # Use current price for transaction

        transaction_cost = shares_to_sell * transaction_price

        # 2. Record the transaction *before* deleting the holding
        transaction_record = Transaction(
            symbol=symbol,
            transaction_type='SELL',
            shares=shares_to_sell,
            price=transaction_price,
            amount=shares_to_sell * transaction_price,
            txn_date=datetime.utcnow()
        )

        
        db.session.add(transaction_record)

        # 3. Delete the holding (sell all shares)
        if shares_to_sell == holding_to_sell.shares:
            db.session.delete(holding_to_sell)

        else:
            holding_to_sell.shares -= shares_to_sell
        portfolio.cash_balance += transaction_cost
        # 4. Commit changes
        db.session.commit()

        new_summary = _calculate_live_summary()
        print(f"DEBUG: Calculated new_summary: {new_summary}") 
        message= f'Successfully sold all {shares_to_sell} shares of {symbol}.'
        print(f"DEBUG: Preparing response message: {message}, summary: {new_summary}")
        response_data = {
            'message': message,
            'summary': new_summary
        }
        print(response_data)
        
        return jsonify({
            'message': f'Successfully sold all {shares_to_sell} shares of {symbol}.',
            'summary':new_summary
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error selling stock {symbol}: {e}")
        return jsonify({'error': 'A database error occurred while selling the stock.','':''}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error selling stock {symbol}: {e}")
        return jsonify({'error': 'An unexpected error occurred while selling the stock.','':''}), 500

# Optional: Endpoint to get transaction history
@transactions_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Retrieves the list of recent transactions."""
    # Simple retrieval, could be paginated or filtered
    transactions = Transaction.query.order_by(Transaction.symbol.desc()).all()
    transaction_list = []
    for t in transactions:
         transaction_list.append({
            'id': t.id,
            'symbol': t.symbol,
            'type': t.transaction_type,
            'shares': t.shares,
            'price': t.price,
            'amount': t.amount,
            'txn_date': t.txn_date
        })
    return jsonify(transaction_list)





