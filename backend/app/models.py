from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from . import db

# db = SQLAlchemy()

class Stock(db.Model):
    __tablename__ = 'stocks'
    symbol = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    change_percent = db.Column(db.Float, nullable=False)
    # last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    holdings = db.relationship('Holding', back_populates='stock')
    transactions = db.relationship('Transaction', back_populates='stock')


class Holding(db.Model):
    __tablename__ = 'holdings'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), db.ForeignKey('stocks.symbol'), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    avg_price = db.Column(db.Float, nullable=False)

    stock = db.relationship('Stock', back_populates='holdings')


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), db.ForeignKey('stocks.symbol'), nullable=False)
    transaction_type = db.Column(db.Enum('BUY', 'SELL'), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False) # Total cash value of transaction
    txn_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    stock = db.relationship('Stock', back_populates='transactions')

class Portfolio(db.Model):
    """A simple table to hold portfolio-wide state, like cash balance."""
    __tablename__ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True)
    cash_balance = db.Column(db.Float, nullable=False, default=0.0)
