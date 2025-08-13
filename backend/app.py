from app import create_app, db
from app.db_init import Portfolio
        
app = create_app()

def seed_database():
    """
    Clears all existing data and initializes the database with a clean slate.
    - Drops all tables.
    - Creates all tables.
    - Sets an initial portfolio cash balance of $100,000.
    """
    with app.app_context():
        print("Resetting database to a clean state...")
        

        # Check if a portfolio already exists
        if Portfolio.query.first() is None:
            # Initialize the portfolio with a starting cash balance
            initial_portfolio = Portfolio(cash_balance=100000.0)
            db.session.add(initial_portfolio)
            db.session.commit()
            print("Database has been reset. Initial cash balance set to $100,000.")
        else:
            print("Database already has a portfolio. Skipping initial cash setup.")

if __name__ == '__main__':
    with app.app_context():
        # db.drop_all()
        # db.create_all()
        seed_database()
   
    app.run(debug=True, port=5001)