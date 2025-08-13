import os
import numpy as np
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf
from preprocessTrainingData import download_data, preprocess_data

def create_model(input_shape):
    """
    Creates and compiles an LSTM model.
    """
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=25))
    model.add(Dense(units=1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def get_or_train_model(ticker):
    """
    Loads a pre-trained model if it exists, otherwise trains a new one.
    """
    model_file = f'{ticker}_lstm_model.h5'
    
    if os.path.exists(model_file):
        model = load_model(model_file)
        # We still need the scaler from the original data
        data = download_data(ticker)
        _, _, scaler = preprocess_data(data)
    else:
        data = download_data(ticker)
        x_train, y_train, scaler = preprocess_data(data)
        
        model = create_model(input_shape=(x_train.shape[1], 1))
        model.fit(x_train, y_train, batch_size=1, epochs=1)
        model.save(model_file)
        
    return model, scaler

def make_prediction(ticker, model, scaler):
    """
    Makes a prediction for the next day's closing price.
    """
    # Get the last 60 days of closing price data
    data = yf.download(ticker, period="2mo")
    data = data.filter(['Close'])
    last_60_days = data[-60:].values
    last_60_days_scaled = scaler.transform(last_60_days)
    
    # Create a data structure for prediction
    X_test = []
    X_test.append(last_60_days_scaled)
    X_test = np.array(X_test)
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
    
    # Get the predicted scaled price and inverse the scaling
    pred_price = model.predict(X_test)
    pred_price = scaler.inverse_transform(pred_price)
    
    return pred_price[0][0]
