from flask import request, jsonify, Blueprint
from app.services.predictionModel import get_or_train_model, make_prediction

predict_bp = Blueprint('predict', __name__)

# @predict.route('/')
# def home():
#     """
#     Renders the main page.
#     """
#     return render_template('index.html')

@predict_bp.route('/predict', methods=['POST'])
def predict():
    """
    Handles the prediction request.
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    
    if not tickers:
        return jsonify({'error': 'No tickers provided'}), 400
        
    predictions = {}
    
    for ticker in tickers:
        try:
            model, scaler = get_or_train_model(ticker)
            prediction = make_prediction(ticker, model, scaler)
            predictions[ticker] = float(prediction) # Ensure it's JSON serializable
        except Exception as e:
            predictions[ticker] = f"Error processing {ticker}: {str(e)}"
            
    return jsonify(predictions)