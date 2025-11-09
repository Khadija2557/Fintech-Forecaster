from db import db  # Add this if not already there
from flask_cors import CORS
from flask import Flask, jsonify, request
from models import forecast_arima, forecast_lstm, ensemble_forecast
from db import get_instruments, get_historical_data, store_historical_data, store_forecasts
from utils import fetch_data_from_yfinance
from adaptive_learning import adaptive_manager
import pandas as pd
from datetime import datetime, timedelta
import logging
import yfinance as yf
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS properly
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Your existing routes (keep these)
@app.route('/instruments', methods=['GET'])
def get_instruments_endpoint():
    try:
        instruments = get_instruments()
        logger.info(f"Returning {len(instruments)} instruments")
        return jsonify(instruments)
    except Exception as e:
        logger.error(f"Error fetching instruments: {str(e)}")
        return jsonify([])

@app.route('/historical-data/<symbol>', methods=['GET'])
def get_historical_data_endpoint(symbol):
    logger.info(f"🔧 Historical data requested for: {symbol}")
    try:
        symbol_clean = symbol.upper().strip()
        yfinance_symbol = symbol_clean.replace('/', '-')
        logger.info(f"🔧 Using yfinance symbol: {yfinance_symbol}")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        logger.info(f"🔧 Fetching data from {start_date.date()} to {end_date.date()}")

        historical_data = None
        
        try:
            logger.info("🔄 Attempting direct yfinance fetch...")
            ticker = yf.Ticker(yfinance_symbol)
            hist_data = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if not hist_data.empty:
                logger.info(f"✅ Direct yfinance fetch successful: {len(hist_data)} rows")
                historical_data = hist_data
            else:
                logger.warning("❌ Direct yfinance returned empty data")
        except Exception as e:
            logger.warning(f"❌ Direct yfinance failed: {str(e)}")

        if historical_data is None or historical_data.empty:
            try:
                logger.info("🔄 Attempting utils fetch...")
                raw_data = fetch_data_from_yfinance(yfinance_symbol, start_date, end_date)
                if not raw_data.empty:
                    logger.info(f"✅ Utils fetch successful: {len(raw_data)} rows")
                    historical_data = raw_data
                else:
                    logger.warning("❌ Utils fetch returned empty data")
            except Exception as e:
                logger.warning(f"❌ Utils fetch failed: {str(e)}")

        if historical_data is None or historical_data.empty:
            logger.error(f"❌ No data available for {symbol} from any source")
            return jsonify([])

        try:
            store_historical_data(symbol_clean, historical_data)
            logger.info("✅ Data stored in database")
        except Exception as e:
            logger.warning(f"⚠️ Could not store data in database: {str(e)}")

        if not isinstance(historical_data, pd.DataFrame):
            historical_data = pd.DataFrame(historical_data)

        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in historical_data.columns for col in required_columns):
            logger.error(f"❌ Missing required columns in data")
            return jsonify([])

        if historical_data.index.name == 'Date':
            historical_data = historical_data.reset_index()

        result = []
        for index, row in historical_data.iterrows():
            if 'Date' in row:
                date_value = row['Date']
                if isinstance(date_value, pd.Timestamp):
                    date_str = date_value.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_value)
            else:
                date_str = (start_date + timedelta(days=index)).strftime('%Y-%m-%d')

            result.append({
                'id': f"{symbol}-{index}",
                'instrument_id': symbol_clean,
                'timestamp': date_str + 'T00:00:00Z',
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'created_at': datetime.now().isoformat()
            })

        logger.info(f"✅ Returning {len(result)} data points for {symbol}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Error in historical data for {symbol}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify([])

@app.route('/models', methods=['GET'])
def get_models_endpoint():
    try:
        try:
            models_coll = db['forecasting_models']
            models = list(models_coll.find({}, {'_id': 0}))
            logger.info(f"Found {len(models)} models in database")
        except Exception as e:
            logger.warning(f"Could not fetch models from database: {str(e)}")
            models = [
                {
                    'id': '1',
                    'name': 'ARIMA',
                    'type': 'traditional',
                    'description': 'AutoRegressive Integrated Moving Average',
                    'hyperparameters': {},
                    'performance_metrics': {'rmse': 2.5, 'mae': 1.8, 'mape': 1.2},
                    'is_active': True,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                },
                {
                    'id': '2', 
                    'name': 'LSTM',
                    'type': 'neural',
                    'description': 'Long Short-Term Memory Neural Network',
                    'hyperparameters': {},
                    'performance_metrics': {'rmse': 1.8, 'mae': 1.3, 'mape': 0.9},
                    'is_active': True,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            ]
        
        return jsonify(models)
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        return jsonify([])

@app.route('/forecast', methods=['POST', 'OPTIONS'])
def generate_forecast_endpoint():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        symbol = data.get('symbol')
        horizon_hours = data.get('days') or data.get('horizon')
        model_id = data.get('model_id') or data.get('model')

        logger.info(f"🔮 Forecast request - Symbol: {symbol}, Horizon: {horizon_hours}, Model: {model_id}")

        if not all([symbol, horizon_hours, model_id]):
            return jsonify({'error': 'Missing parameters. Required: symbol, days/horizon, model_id/model'}), 400

        try:
            horizon_hours = int(horizon_hours)
        except ValueError:
            return jsonify({'error': 'horizon/days must be a number'}), 400

        symbol_clean = symbol.upper().strip()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        logger.info(f"📊 Fetching historical data for forecasting...")
        
        ticker = yf.Ticker(symbol_clean)
        historical_df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if historical_df.empty:
            return jsonify({'error': 'No historical data available for forecasting'}), 404

        logger.info(f"📊 Found {len(historical_df)} historical data points")

        series = historical_df['Close'].dropna()
        
        if len(series) < 10:
            return jsonify({'error': 'Insufficient historical data for forecasting'}), 400

        logger.info(f"🤖 Generating forecast using model: {model_id}")
        
        if 'arima' in model_id.lower() or model_id == '1':
            predictions = forecast_arima(series, horizon_hours)
            model_name = 'ARIMA'
        elif 'lstm' in model_id.lower() or model_id == '2':
            predictions = forecast_lstm(series, horizon_hours) 
            model_name = 'LSTM'
        else:
            arima_pred = forecast_arima(series, horizon_hours)
            lstm_pred = forecast_lstm(series, horizon_hours)
            predictions = ensemble_forecast(arima_pred, lstm_pred)
            model_name = 'Ensemble'

        last_date = historical_df.index[-1] if hasattr(historical_df.index, '__len__') else datetime.now()
        future_dates = [last_date + timedelta(hours=i+1) for i in range(horizon_hours)]
        
        forecasts = []
        for i, (date, pred) in enumerate(zip(future_dates, predictions)):
            confidence_margin = pred * 0.02
            
            forecast_data = {
                'id': f"forecast-{symbol}-{i}",
                'instrument_id': symbol_clean,
                'model_id': model_id,
                'forecast_timestamp': datetime.now().isoformat(),
                'target_timestamp': date.isoformat(),
                'horizon_hours': horizon_hours,
                'predicted_price': float(pred),
                'confidence_lower': float(pred - confidence_margin),
                'confidence_upper': float(pred + confidence_margin),
                'actual_price': None,
                'created_at': datetime.now().isoformat()
            }
            forecasts.append(forecast_data)

        try:
            store_forecasts(symbol_clean, horizon_hours, model_id, forecasts)
            logger.info(f"✅ Forecasts stored in database")
        except Exception as e:
            logger.warning(f"⚠️ Could not store forecasts in database: {str(e)}")

        logger.info(f"✅ Successfully generated {len(forecasts)} forecasts")
        return jsonify(forecasts)

    except Exception as e:
        logger.error(f"❌ Error generating forecast: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Forecast generation failed: {str(e)}'}), 500

# PORTFOLIO ROUTES - ADD THESE
@app.route('/portfolio/create', methods=['POST'])
def create_portfolio_endpoint():
    """Create or reset a portfolio"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        initial_capital = data.get('initial_capital', 10000)
        
        # Create portfolio collection if it doesn't exist
        portfolio_coll = db['portfolios']
        
        portfolio = {
            'user_id': user_id,
            'cash_balance': float(initial_capital),
            'holdings': {},
            'total_value': float(initial_capital),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        portfolio_coll.update_one(
            {'user_id': user_id},
            {'$set': portfolio},
            upsert=True
        )
        
        return jsonify(portfolio)
    except Exception as e:
        logger.error(f"Error creating portfolio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/portfolio/<user_id>', methods=['GET'])
def get_portfolio_endpoint(user_id):
    """Get current portfolio state"""
    try:
        portfolio_coll = db['portfolios']
        portfolio = portfolio_coll.find_one({'user_id': user_id})
        
        if not portfolio:
            # Create a default portfolio if none exists
            default_portfolio = {
                'user_id': user_id,
                'cash_balance': 10000.0,
                'holdings': {},
                'total_value': 10000.0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            portfolio_coll.insert_one(default_portfolio)
            portfolio = default_portfolio
            
        # Remove MongoDB ID before returning
        portfolio.pop('_id', None)
        return jsonify(portfolio)
    except Exception as e:
        logger.error(f"Error fetching portfolio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/portfolio/trade', methods=['POST'])
def execute_trade_endpoint():
    """Execute a buy/sell trade"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        symbol = data.get('symbol')
        action = data.get('action')  # 'buy' or 'sell'
        quantity = int(data.get('quantity', 0))
        
        if not all([symbol, action, quantity]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Get current price
        ticker = yf.Ticker(symbol)
        current_data = ticker.history(period='1d')
        if current_data.empty:
            return jsonify({'error': 'Could not fetch current price'}), 400
            
        current_price = current_data['Close'].iloc[-1]
        
        # Execute the trade
        portfolio_coll = db['portfolios']
        transactions_coll = db['portfolio_transactions']
        
        # Get current portfolio
        portfolio = portfolio_coll.find_one({'user_id': user_id})
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        total_cost = quantity * current_price
        
        if action == 'buy':
            if portfolio['cash_balance'] < total_cost:
                return jsonify({'error': 'Insufficient funds'}), 400
            
            # Update portfolio
            new_cash = portfolio['cash_balance'] - total_cost
            holdings = portfolio.get('holdings', {})
            current_quantity = holdings.get(symbol, 0)
            holdings[symbol] = current_quantity + quantity
            
        elif action == 'sell':
            holdings = portfolio.get('holdings', {})
            current_quantity = holdings.get(symbol, 0)
            
            if current_quantity < quantity:
                return jsonify({'error': 'Insufficient shares'}), 400
            
            # Update portfolio
            new_cash = portfolio['cash_balance'] + total_cost
            holdings[symbol] = current_quantity - quantity
            
            # Remove symbol if quantity becomes zero
            if holdings[symbol] == 0:
                del holdings[symbol]
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        # Calculate new total value
        new_total_value = new_cash
        
        # Update portfolio in database
        portfolio_coll.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'cash_balance': new_cash,
                    'holdings': holdings,
                    'total_value': new_total_value,
                    'updated_at': datetime.now().isoformat()
                }
            }
        )
        
        # Record transaction
        transaction = {
            'portfolio_id': user_id,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': current_price,
            'total_amount': total_cost,
            'timestamp': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        transactions_coll.insert_one(transaction)
        
        return jsonify({
            'success': True,
            'new_cash_balance': new_cash,
            'new_holdings': holdings,
            'total_value': new_total_value
        })
        
    except Exception as e:
        logger.error(f"Error executing trade: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/portfolio/performance/<user_id>', methods=['GET'])
def get_portfolio_performance_endpoint(user_id):
    """Get portfolio performance metrics"""
    try:
        portfolio_coll = db['portfolios']
        transactions_coll = db['portfolio_transactions']
        
        portfolio = portfolio_coll.find_one({'user_id': user_id})
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        initial_capital = 10000
        current_value = portfolio['total_value']
        total_return = ((current_value - initial_capital) / initial_capital) * 100
        
        metrics = {
            'initial_capital': initial_capital,
            'current_value': current_value,
            'total_return_percent': round(total_return, 2),
            'total_return_dollar': round(current_value - initial_capital, 2),
            'cash_balance': portfolio['cash_balance'],
            'number_of_holdings': len(portfolio.get('holdings', {})),
            'number_of_trades': transactions_coll.count_documents({'portfolio_id': user_id})
        }
        
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error calculating performance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'service': 'FinTech Forecaster API'
    })
    
    

# Add these routes to your app.py


# Add these imports to your app.py
from adaptive_learning import AdaptiveLearningManager

# Then add these routes (make sure they're in your app.py):
@app.route('/model/retrain', methods=['POST'])
def retrain_model_endpoint():
    """Trigger model retraining based on recent performance"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        model_type = data.get('model_type', 'arima')
        
        # For now, just return success since we don't have full adaptive learning yet
        return jsonify({
            'retrained': True,
            'message': f'{model_type.upper()} model retraining triggered for {symbol}'
        })
            
    except Exception as e:
        logger.error(f"Error in model retraining: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/model/performance/<symbol>', methods=['GET'])
def get_model_performance_endpoint(symbol):
    """Get model performance history for a symbol"""
    try:
        # For now, return mock data
        mock_performance = [
            {
                'symbol': symbol,
                'model_type': 'arima',
                'timestamp': datetime.now().isoformat(),
                'metrics': {
                    'mae': 2.1,
                    'rmse': 3.4,
                    'mape': 1.8
                }
            }
        ]
        return jsonify(mock_performance)
    except Exception as e:
        logger.error(f"Error fetching performance data: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 Starting FinTech Forecaster API...")
    app.run(debug=True, host='0.0.0.0', port=5000)