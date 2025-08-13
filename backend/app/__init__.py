from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # --- Configuration ---
    app.config.from_object('config.Config')
    # --- End Configuration ---

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from .routes.routes import main as main_blueprint
    from .routes.performance import performance_bp
    from .routes.allocation import allocation_bp
    from .routes.holdings import holdings_bp
    from .routes.search import search_bp
    from .routes.transactions import transactions_bp
    from .routes.predict import predict_bp

    # Register each blueprint with a URL prefix.
    app.register_blueprint(main_blueprint, url_prefix='/api')
    app.register_blueprint(holdings_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(transactions_bp, url_prefix='/api')
    app.register_blueprint(performance_bp, url_prefix='/api')
    app.register_blueprint(allocation_bp, url_prefix='/api')
    app.register_blueprint(predict_bp, url_prefix='/api')

    return app