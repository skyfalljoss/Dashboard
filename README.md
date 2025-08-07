# Finance Portfolio Dashboard

A real-time portfolio management dashboard that displays stock data from yfinance with live updates, search functionality, and portfolio management features.

## Features

### Real-Time Stock Data
- **Live Price Updates**: Stock prices update every 30 seconds using yfinance
- **Visual Indicators**: Live data is marked with animated indicators
- **Real-time Search**: Search for stocks with live price data
- **Portfolio Tracking**: Real-time updates for holdings and performance

### Search & Add Functionality
- **Stock Search**: Search for stocks by symbol or company name
- **Live Data**: Search results show current prices and daily changes
- **Add to Portfolio**: Click "Add" to purchase stocks and add to holdings
- **Debounced Search**: Search is optimized with 500ms debouncing

### Portfolio Management
- **Holdings Table**: View current holdings with real-time prices
- **Buy/Sell Modals**: Interactive modals for buying and selling stocks
- **Performance Tracking**: Real-time gain/loss calculations
- **Asset Allocation**: Visual breakdown of portfolio composition

## Technical Implementation

### Frontend (JavaScript)
- **Real-time Updates**: Automatic refresh every 30 seconds
- **Visual Feedback**: CSS animations for live data indicators
- **Search Optimization**: Debounced search to reduce API calls
- **Modal System**: Interactive buy/sell modals with validation

### Backend (Python/Flask)
- **yfinance Integration**: Real-time stock data fetching
- **Search API**: Stock symbol search with live price enrichment
- **Real-time Endpoints**: Dedicated endpoints for live data updates
- **Error Handling**: Robust error handling for API failures

### Key Files
- `frontend/scripts.js`: Main JavaScript logic for real-time updates
- `frontend/style.css`: CSS for live data indicators and animations
- `backend/app/routes/search.py`: Stock search with yfinance integration
- `backend/app/routes/holdings.py`: Real-time holdings data endpoint
- `backend/app/utils/yfinance_helper.py`: yfinance data fetching utilities

## Usage

1. **Search for Stocks**: Type in the search box to find stocks
2. **View Live Data**: Real-time prices are marked with animated indicators
3. **Add to Portfolio**: Click "Add" button to purchase stocks
4. **Monitor Holdings**: View your portfolio with live price updates
5. **Sell Stocks**: Use the "Sell" button to sell holdings

## Real-Time Features

- **30-second Updates**: Automatic refresh of all stock data
- **Visual Indicators**: Green pulsing dots for live data
- **Price Highlighting**: Current prices are highlighted with live indicators
- **Update Feedback**: Visual feedback when data is being updated

## API Endpoints

- `GET /api/search?q=<query>`: Search for stocks with live data
- `GET /api/holdings`: Get current portfolio holdings
- `GET /api/holdings/realtime?symbols=<symbols>`: Get real-time price data
- `POST /api/stock/add`: Add stocks to portfolio
- `POST /api/stock/sell`: Sell stocks from portfolio 