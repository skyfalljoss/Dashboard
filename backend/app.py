from app import create_app, db
from app.models import Portfolio, Stock, Holding, Transaction
from app.utils.yfinance_helper import fetch_stock_info
import requests
import pandas as pd
import io
from app.services import seed_database_with_data

ALPHA_VANTAGE_API_KEY = 'HWWZLX4BAWS7ID80'
        
app = create_app()

def create_stock_data():
    with app.app_context():
    # Create a new Stock object (in memory)
        new_stock = Stock(symbol='GOOG', name='Alphabet Inc.', current_price=150.0, change_percent=1.2)

        # Tell SQLAlchemy to add it to the session (staging area)
        db.session.add(new_stock)

        # Commit the session to write changes to the database file
        db.session.commit()


def get_stock_symbols():
    url = f"https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
    # Make the API request
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # The response content is a CSV. We use io.StringIO to treat the text as a file
        # and read it directly into a pandas DataFrame.
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))

        # Filter the DataFrame to show only active stocks
        active_stocks = df[df['status'] == 'Active'].head(20)   

        # Display the first 5 active stocks
        print("--- Top 5 Active Stocks ---")
        print(active_stocks.head(20))

        # Display the total count of active stocks found
        print(f"\n✅ Found {len(active_stocks)} active stock symbols.")
        return active_stocks['symbol'].tolist()
        

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return []

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def seed_database():
    with app.app_context():
        # db.drop_all()
        # Check if the database is already seeded
        if Stock.query.first() is not None:
            print("Database already seeded. Skipping.")
            return
        # Create tables if they don't exist
        db.create_all()

        print("Seeding database...")
        # --- End Decision Point ---

        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'CRM', 'ADBE', 'SOFI','F','AAL', 'GRAB', 'INTC']

        symbols.extend(get_stock_symbols())
        symbols = list(set(symbols))
        print("------------------symbols----------------")
        print(symbols)
        stocks_added = 0
        
        for symbol in symbols:
            try:
                print(f"Fetching data for {symbol}...")
                info = fetch_stock_info(symbol)
                # Check if info was fetched successfully
                print("check info")
                print(info)
                if info and info.get('current_price') is not None:
                    stock = Stock(
                        symbol=info['symbol'],
                        name=info['name'],
                        current_price=info['current_price'],
                        change_percent=info['change_percent']
                        # last_updated will use the default=datetime.utcnow
                    )
                    db.session.add(stock)
                    print(f" Successfully queued {symbol} for addition.")
                    stocks_added += 1
                else:
                    print(f"  Warning: Incomplete data for {symbol}. Skipping.")

            except Exception as e:
                # Catch errors specifically related to fetching or processing this stock
                print(f"  Error processing {symbol}: {e}. Skipping.")


        print(f"Queued {stocks_added} stocks for seeding.")

        holdings_data = [
            {'id': 1, 'symbol': 'AAPL', 'shares': 50, 'avg_price': 150.00},
            {'id': 2, 'symbol': 'MSFT', 'shares': 30, 'avg_price': 280.00},
            {'id': 3, 'symbol': 'GOOGL', 'shares': 25, 'avg_price': 120.00},
            {'id': 4, 'symbol': 'AMZN', 'shares': 40, 'avg_price': 90.00},
            {'id': 5, 'symbol': 'TSLA', 'shares': 20, 'avg_price': 200.00},
            {'id': 6, 'symbol': 'SOFI', 'shares': 20, 'avg_price': 22.00},
        ]
        holdings_added = 0
        for h_data in holdings_data:
            try:
                # Optional: Check if the symbol exists in the stocks table first?
                # stock_exists = Stock.query.get(h_data['symbol'])
                # if not stock_exists:
                #     print(f"Warning: Stock {h_data['symbol']} not found in stocks table. Skipping holding.")
                #     continue

                holding = Holding(id=h_data['id'], symbol=h_data['symbol'], shares=h_data['shares'], avg_price=h_data['avg_price'])
                print("-----------------HOLDING---------------")
                print(holding.avg_price)  
                print(holding.symbol)  
                db.session.add(holding)
                print(f"Queued holding for {h_data['symbol']}.")
                holdings_added += 1
            except Exception as e:
                print(f"Error adding holding for {h_data.get('symbol', 'UNKNOWN')}: {e}")

        print(f"Queued {holdings_added} holdings for seeding.")

        portfolio_data = Portfolio(
            cash_balance = 50000
        )
        db.session.add(portfolio_data)

        try:
            print("Committing changes to database...")
            db.session.commit()
            print("Database seeded successfully.")
        except Exception as e:
            db.session.rollback() # Important: Rollback if commit fails
            print(f"Error committing to database: {e}")
            print("Database seeding failed.")
        
        

# def seed_holdings():
#     with app.app_context():
#         holdings_data = [
#             {'id': 1, 'symbol': 'AAPL', 'shares': 50, 'avg_price': 150.00},
#             {'id': 2, 'symbol': 'MSFT', 'shares': 30, 'avg_price': 280.00},
#             {'id': 3, 'symbol': 'GOOGL', 'shares': 25, 'avg_price': 120.00},
#         ]   
#         print("-----------------HOLDINGS111---------------")
#         holdings_added = 0
#         for h_data in holdings_data:
#             try:
#                 holding = Holding(id=h_data['id'], symbol=h_data['symbol'], shares=h_data['shares'], avg_price=h_data['avg_price'])
#                 print("-----------------HOLDINGS222---------------")
#                 print(holding)
#                 db.session.add(holding)
#                 holdings_added += 1 
#             except Exception as e:
#                 print(f"Error adding holding for {h_data.get('symbol', 'UNKNOWN')}: {e}")
#         print(f"Queued {holdings_added} holdings for seeding.")
#         db.session.commit()
#         print("Database seeded successfully.")

if __name__ == '__main__':
    with app.app_context():
        # db.drop_all()
        # db.create_all()
        seed_database()
   
    app.run(debug=True, port=5001)