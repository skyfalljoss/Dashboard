import yfinance as yf
import pandas as pd


def fetch_stock_info(symbol):
    """
    Fetch real-time stock information using yfinance.
    Returns a dictionary with stock data or None if failed.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get current price from multiple possible sources
        current_price = (info.get('currentPrice') or 
                        info.get('regularMarketPrice') or 
                        info.get('previousClose'))
        
        prev_close = info.get('previousClose')
        
        # Calculate change percentage
        if current_price and prev_close and prev_close != 0:
            change_percent = ((current_price - prev_close) / prev_close) * 100
        else:
            change_percent = 0
        
        # Validate that we have essential data
        if not current_price:
            print(f"No price data available for {symbol}")
            return None
            
        return {
            'symbol': symbol.upper(),
            'name': info.get('longName', symbol),
            'current_price': current_price,
            'previous_close': prev_close,
            'change_percent': round(change_percent, 2),
            'currency': info.get('currency', 'USD'),
            'market_cap': info.get('marketCap', 0)
        }
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None

def fetch_historical_data(symbols, period='1y'):
    """
    Fetch historical data for given symbols.
    """
    try:
        hist_data = yf.download(symbols, period=period, auto_adjust=True)['Close']
        if isinstance(hist_data, pd.Series):
            hist_data = hist_data.to_frame(name=symbols[0])
        return hist_data.ffill()
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return None

