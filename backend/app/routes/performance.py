from flask import Blueprint
from ..services.portfolioPerformance import get_portfolio_performance

performance_bp = Blueprint('performance', __name__)

@performance_bp.route('/performance', methods=['GET'])
def get_performance():
    return get_portfolio_performance()