import numpy as np
import pandas as pd
import yfinance as yf
import time
import random
from sklearn.preprocessing import MinMaxScaler

def download_data(ticker):
    """
    Downloads historical stock data from Yahoo Finance with rate limiting.
    """
    try:
        # Add a delay to prevent rate limiting
        time.sleep(random.uniform(1, 3))
        return yf.download(ticker, start='2015-01-01', end=pd.to_datetime('today').strftime('%Y-%m-%d'), progress=False)
    except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")
        # If rate limited, wait longer and retry once
        if '429' in str(e):
            print(f"Rate limited for {ticker}, waiting 10 seconds before retry...")
            time.sleep(10)
            try:
                return yf.download(ticker, start='2015-01-01', end=pd.to_datetime('today').strftime('%Y-%m-%d'), progress=False)
            except Exception as retry_e:
                print(f"Retry failed for {ticker}: {retry_e}")
                return None
        return None

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
