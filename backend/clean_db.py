# In Dashboard/backend/cleanup_db.py

from app import create_app, db
from backend.app.db_init import Transaction, Portfolio, Stock, Holding 
from datetime import datetime

app = create_app()

def clear_database():
    """
    Drops all existing tables and creates new ones, initializing an empty portfolio.
    """
    db.drop_all()
    db.create_all()
    
    if Portfolio.query.first() is None:
        initial_portfolio = Portfolio(cash_balance=100000.0)
        db.session.add(initial_portfolio)
        db.session.commit()
        print("Database has been cleared. Initial cash balance set to $100,000.")
    else:
        print("Database has been cleared, but a portfolio already existed.")

if __name__ == '__main__':
    with app.app_context():
        print("Starting database reset without any seed data...")
        clear_database()
        print("Database has been successfully cleared.")