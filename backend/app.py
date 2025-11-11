# ADD THIS AT THE TOP OF app.py (after other imports)
from bson import ObjectId
from datetime import datetime
import json

# ADD THIS CLASS ANYWHERE BEFORE app = Flask(__name__)
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

import os
from db import db  # Add this if not already there
from flask_cors import CORS
from flask import Flask, jsonify, request
from enhanced_models import adaptive_forecast_arima, adaptive_forecast_lstm, adaptive_ensemble_forecast
from db import get_instruments, get_historical_data, store_historical_data, store_forecasts
from utils import fetch_data_from_yfinance
from enhanced_adaptive_learning import enhanced_adaptive_manager
from continuous_monitoring import monitoring_system
import pandas as pd
from datetime import datetime, timedelta
import logging
import yfinance as yf
import traceback
import time
import threading
import logging

# In app.py, add this after the imports and before the routes
import os



# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Create necessary directories on startup
os.makedirs("saved_models", exist_ok=True)
logger.info("✅ saved_models directory created/verified")

app = Flask(__name__)
# ADD THIS LINE AFTER app = Flask(__name__)
app.json_encoder = JSONEncoder

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

        # 🚀 AUTOMATIC ADAPTIVE LEARNING TRIGGERS - ADD THIS SECTION
        try:
            if historical_data is not None and not historical_data.empty:
                logger.info(f"🔄 Checking adaptive learning triggers for {symbol_clean}")
                
                if len(historical_data) > 30:  # Only if we have sufficient data
                    close_prices = historical_data['Close'] if 'Close' in historical_data.columns else historical_data['close']
                    
                    # Convert to pandas Series if needed
                    if isinstance(close_prices, pd.Series):
                        price_series = close_prices
                    else:
                        price_series = pd.Series(close_prices.values, index=historical_data.index)
                    
                    logger.info(f"📊 Price series prepared: {len(price_series)} points")
                    
                    # 1. INCREMENTAL UPDATE TRIGGER
                    latest_model = enhanced_adaptive_manager.get_latest_model_info(symbol_clean, 'lstm')
                    if latest_model:
                        # Use recent data for incremental learning (last 5-7 days)
                        recent_data = price_series.tail(7)
                        if len(recent_data) >= 5:
                            logger.info(f"🔄 Triggering incremental LSTM update for {symbol_clean}")
                            try:
                                new_version = enhanced_adaptive_manager.incremental_lstm_update(
                                    symbol_clean, recent_data, latest_model['version_id']
                                )
                                if new_version:
                                    logger.info(f"✅ Incremental update successful: {new_version}")
                                else:
                                    logger.warning("⚠️ Incremental update returned no new version")
                            except Exception as inc_error:
                                logger.warning(f"⚠️ Incremental update failed: {inc_error}")
                    
                    # 2. SCHEDULED RETRAINING TRIGGER
                    logger.info(f"🔄 Checking scheduled retraining for {symbol_clean}")
                    try:
                        retrain_result = enhanced_adaptive_manager.scheduled_retraining(symbol_clean, price_series)
                        if retrain_result:
                            logger.info(f"✅ Scheduled retraining triggered: {retrain_result}")
                    except Exception as retrain_error:
                        logger.warning(f"⚠️ Scheduled retraining check failed: {retrain_error}")
                    
                    # 3. ROLLING WINDOW REGRESSION UPDATE
                    logger.info(f"🔄 Updating rolling window regression for {symbol_clean}")
                    try:
                        rolling_predictions = enhanced_adaptive_manager.rolling_window_regression(symbol_clean, price_series)
                        if rolling_predictions:
                            logger.info(f"✅ Rolling window updated: {len(rolling_predictions)} predictions")
                    except Exception as rolling_error:
                        logger.warning(f"⚠️ Rolling window update failed: {rolling_error}")
                    
                    # 4. PERFORMANCE DEGRADATION CHECK
                    logger.info(f"🔄 Checking for performance degradation for {symbol_clean}")
                    try:
                        needs_retrain = enhanced_adaptive_manager.check_retraining_needed(symbol_clean, 'lstm')
                        if needs_retrain:
                            logger.warning(f"🚨 Performance degradation detected for {symbol_clean}, retraining recommended")
                            # Auto-trigger retraining if severe degradation
                            if len(price_series) > 100:  # Only if we have enough data
                                enhanced_adaptive_manager.retrain_model(symbol_clean, price_series, 'lstm')
                                logger.info(f"✅ Auto-retraining completed for {symbol_clean}")
                    except Exception as perf_error:
                        logger.warning(f"⚠️ Performance check failed: {perf_error}")
                    
                    logger.info(f"✅ All adaptive learning triggers completed for {symbol_clean}")
                else:
                    logger.info(f"⏸️ Insufficient data for adaptive learning: {len(historical_data)} points")
                    
        except Exception as adaptive_error:
            logger.error(f"❌ Adaptive learning triggers failed: {adaptive_error}")
            logger.error(traceback.format_exc())
        # END OF ADAPTIVE LEARNING TRIGGERS

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

        # WITH THIS:
        logger.info(f"🤖 Generating adaptive forecast using model: {model_id}")

        # Use adaptive learning system for all forecasts
        if 'arima' in model_id.lower() or model_id == '1':
            predictions, model_used = enhanced_adaptive_manager.adaptive_forecast(
                symbol_clean, series, horizon_hours, use_ensemble=False
            )
            model_name = 'ARIMA'
        elif 'lstm' in model_id.lower() or model_id == '2':
            predictions, model_used = enhanced_adaptive_manager.adaptive_forecast(
                symbol_clean, series, horizon_hours, use_ensemble=False
            )
            model_name = 'LSTM'
        else:
            predictions, model_used = enhanced_adaptive_manager.adaptive_forecast(
                symbol_clean, series, horizon_hours, use_ensemble=True
            )
            model_name = 'Ensemble'

        logger.info(f"✅ Adaptive forecast generated using: {model_used}")

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
            logger.info(f"Forecasts stored in database")
        except Exception as e:
            logger.warning(f"Could not store forecasts in database: {str(e)}")
            # CONTINUE — don't fail the API

        logger.info(f"Successfully generated {len(forecasts)} forecasts")

        # forecasts is CLEAN → no ObjectId
        return jsonify(forecasts)  # ← NOW SAFE

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

# ADAPTIVE LEARNING ROUTES
@app.route('/model/adaptive-forecast', methods=['POST'])
def adaptive_forecast_endpoint():
    """Generate forecast using adaptive learning system"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        horizon = data.get('horizon', 24)
        
        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400

        # Fetch historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        ticker = yf.Ticker(symbol)
        historical_df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if historical_df.empty:
            return jsonify({'error': 'No historical data available'}), 404

        series = historical_df['Close'].dropna()
        
        # Use adaptive forecasting
        forecast, model_used = enhanced_adaptive_manager.adaptive_forecast(
            symbol, series, horizon, use_ensemble=True
        )
        
        # Prepare forecast results
        last_date = historical_df.index[-1]
        future_dates = [last_date + timedelta(hours=i+1) for i in range(horizon)]
        
        forecasts = []
        for i, (date, pred) in enumerate(zip(future_dates, forecast)):
            confidence_margin = pred * 0.02
            
            forecast_data = {
                'id': f"adaptive-{symbol}-{i}",
                'instrument_id': symbol,
                'model_id': f"adaptive_{model_used}",
                'forecast_timestamp': datetime.now().isoformat(),
                'target_timestamp': date.isoformat(),
                'horizon_hours': horizon,
                'predicted_price': float(pred),
                'confidence_lower': float(pred - confidence_margin),
                'confidence_upper': float(pred + confidence_margin),
                'actual_price': None,
                'created_at': datetime.now().isoformat()
            }
            forecasts.append(forecast_data)

        # Store forecasts
        store_forecasts(symbol, horizon, f"adaptive_{model_used}", forecasts)

        return jsonify({
            'forecasts': forecasts,
            'model_used': model_used,
            'adaptive_system': True
        })

    except Exception as e:
        logger.error(f"Error in adaptive forecast: {str(e)}")
        return jsonify({'error': f'Adaptive forecast failed: {str(e)}'}), 500

@app.route('/model/performance-history/<symbol>', methods=['GET'])  # CHANGED NAME
def get_model_performance_history_endpoint(symbol):  # CHANGED NAME
    """Get comprehensive model performance history"""
    try:
        performance_data = {}
        
        for model_type in ['arima', 'lstm', 'rolling_window', 'sliding_context']:
            performance_data[model_type] = enhanced_adaptive_manager.get_performance_history(
                symbol, model_type, days=30
            )
        
        return jsonify(performance_data)
        
    except Exception as e:
        logger.error(f"Error fetching performance data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/model/versions/<symbol>', methods=['GET'])
def get_model_versions_endpoint(symbol):
    """Get all model versions for a symbol"""
    try:
        versions = list(db['model_versions'].find(
            {'training_data_range.symbol': symbol},
            {'_id': 0}
        ).sort('created_at', -1))
        
        return jsonify(versions)
        
    except Exception as e:
        logger.error(f"Error fetching model versions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/model/retrain', methods=['POST'])
def retrain_model_endpoint():
    """Trigger model retraining with enhanced adaptive learning"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        model_type = data.get('model_type', 'ensemble')
        
        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400

        # Fetch latest data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        ticker = yf.Ticker(symbol)
        historical_df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if historical_df.empty:
            return jsonify({'error': 'No historical data available'}), 404

        series = historical_df['Close'].dropna()
        
        # Perform retraining
        if model_type == 'lstm':
            version_id = enhanced_adaptive_manager.retrain_model(symbol, series, 'lstm')
        elif model_type == 'adaptive':
            # Use adaptive ensemble retraining
            forecast, model_used = enhanced_adaptive_manager.adaptive_forecast(
                symbol, series, 24, use_ensemble=True
            )
            version_id = f"adaptive_ensemble_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            # Complete retraining of all models
            enhanced_adaptive_manager.retrain_model(symbol, series, 'lstm')
            version_id = f"full_retrain_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return jsonify({
            'retrained': True,
            'message': f'{model_type.upper()} model retraining completed for {symbol}',
            'version_id': version_id,
            'timestamp': datetime.now().isoformat()
        })
            
    except Exception as e:
        logger.error(f"Error in model retraining: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/model/incremental-update', methods=['POST'])
def incremental_update_endpoint():
    """Trigger incremental model update with new data"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        model_type = data.get('model_type', 'lstm')
        
        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400

        # Fetch very recent data for incremental learning
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Only last 7 days
        
        ticker = yf.Ticker(symbol)
        recent_df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if recent_df.empty:
            return jsonify({'error': 'No recent data available'}), 404

        series = recent_df['Close'].dropna()
        
        # Get latest model version
        latest_model = enhanced_adaptive_manager.get_latest_model_info(symbol, model_type)
        
        if not latest_model:
            return jsonify({'error': f'No existing {model_type} model found for incremental update'}), 404
        
        # Perform incremental update
        if model_type == 'lstm':
            new_version_id = enhanced_adaptive_manager.incremental_lstm_update(
                symbol, series, latest_model['version_id']
            )
            
            if new_version_id:
                return jsonify({
                    'updated': True,
                    'message': f'LSTM model incrementally updated for {symbol}',
                    'old_version': latest_model['version_id'],
                    'new_version': new_version_id
                })
            else:
                return jsonify({'error': 'Incremental update failed'}), 500
        
        return jsonify({'error': f'Incremental update not supported for {model_type}'}), 400
            
    except Exception as e:
        logger.error(f"Error in incremental update: {str(e)}")
        return jsonify({'error': str(e)}), 500

# MONITORING ROUTES
@app.route('/monitoring/errors/<symbol>', methods=['GET'])
def get_prediction_errors_endpoint(symbol):
    """Get prediction errors for a symbol"""
    try:
        errors_coll = db['prediction_metrics']
        
        # Get recent prediction errors
        cutoff_date = datetime.now() - timedelta(days=30)
        errors = list(errors_coll.find({
            'symbol': symbol,
            'timestamp': {'$gte': cutoff_date.isoformat()}
        }, {'_id': 0}).sort('timestamp', -1).limit(100))
        
        # Format errors for frontend
        formatted_errors = []
        for error in errors:
            if 'predictions' in error and 'actuals' in error:
                for pred, actual in zip(error['predictions'], error['actuals']):
                    formatted_errors.append({
                        'timestamp': error['timestamp'],
                        'predicted': pred,
                        'actual': actual,
                        'error': actual - pred
                    })
        
        return jsonify(formatted_errors)
        
    except Exception as e:
        logger.error(f"Error getting prediction errors: {str(e)}")
        return jsonify([])

@app.route('/monitoring/performance/<symbol>', methods=['GET'])
def get_monitoring_performance_endpoint(symbol):  # CHANGED NAME
    """Get comprehensive model performance for a symbol"""
    try:
        performance_summary = monitoring_system.get_performance_summary(symbol)
        return jsonify(performance_summary)
        
    except Exception as e:
        logger.error(f"Error getting model performance: {str(e)}")
        return jsonify({})

@app.route('/monitoring/alerts', methods=['GET'])
def get_performance_alerts_endpoint():
    """Get active performance alerts"""
    try:
        alerts = monitoring_system.get_active_alerts()
        
        # Convert ObjectId to string for JSON serialization
        for alert in alerts:
            alert['id'] = str(alert['_id'])
            del alert['_id']
            
        return jsonify(alerts)
        
    except Exception as e:
        logger.error(f"Error getting performance alerts: {str(e)}")
        return jsonify([])

@app.route('/monitoring/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_alert_endpoint(alert_id):
    """Mark an alert as resolved"""
    try:
        success = monitoring_system.resolve_alert(alert_id)
        
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/monitoring/metrics/<symbol>', methods=['GET'])
def get_metrics_history_endpoint(symbol):
    """Get metrics history for a symbol"""
    try:
        model_type = request.args.get('model_type')
        
        metrics = monitoring_system.get_metrics_history(symbol, model_type)
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting metrics history: {str(e)}")
        return jsonify([])

# Background task for continuous evaluation
def background_continuous_evaluation():
    """Background task to continuously evaluate predictions"""
    while True:
        try:
            # This would typically check for new ground-truth data
            # and evaluate recent predictions
            time.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in continuous evaluation: {str(e)}")
            time.sleep(300)  # Wait 5 minutes on error

# Start background thread (add this after app routes)
eval_thread = threading.Thread(target=background_continuous_evaluation, daemon=True)
eval_thread.start()

if __name__ == '__main__':
    logger.info("🚀 Starting FinTech Forecaster API...")
    app.run(debug=True, host='0.0.0.0', port=5000)