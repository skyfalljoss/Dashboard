import yfinance as yf
import json

def test_api(symbol):
    try:
        stock = yf.Ticker(symbol.upper())
        info = stock.info
        return {
            'symbol': symbol.upper(),
            'name': info.get('longName', 'N/A'),
            'current_price': info.get('currentPrice', 'N/A')
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    result = test_api("MSFT")
    print(json.dumps(result, indent=2))