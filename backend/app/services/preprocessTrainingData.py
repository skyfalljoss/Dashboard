import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler

def download_data(ticker):
    """
    Downloads historical stock data from Yahoo Finance.
    """
    return yf.download(ticker, start='2015-01-01', end=pd.to_datetime('today').strftime('%Y-%m-%d'))

def preprocess_data(data):
    """
    Preprocesses the data for the LSTM model, including scaling and creating sequences.
    """
    # Use the 'Close' price for prediction
    data = data.filter(['Close'])
    dataset = data.values
    
    # Scale the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(dataset)
    
    # Create training data (95% of the data)
    training_data_len = int(np.ceil(len(dataset) * .95))
    train_data = scaled_data[0:int(training_data_len), :]
    
    # Split the data into x_train and y_train data sets
    x_train = []
    y_train = []
    
    for i in range(60, len(train_data)):
        x_train.append(train_data[i-60:i, 0])
        y_train.append(train_data[i, 0])
        
    # Convert to numpy arrays and reshape
    x_train, y_train = np.array(x_train), np.array(y_train)
    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
    
    return x_train, y_train, scaler
