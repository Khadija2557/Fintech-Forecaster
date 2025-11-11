# enhanced_adaptive_learning.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from db import db
import joblib
import os
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.linear_model import SGDRegressor
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class EnhancedAdaptiveLearningManager:
    def __init__(self):
        self.model_versions_coll = db['model_versions']
        self.performance_history_coll = db['model_performance_history']
        self.model_registry = {}
        self.models_dir = "saved_models"
        os.makedirs(self.models_dir, exist_ok=True)
        
    def train_lstm_from_scratch(self, symbol, data, horizon):
        """Train LSTM from scratch and return model, scaler, forecast"""
        try:
            if len(data) < 50:
                return None, None, [data.iloc[-1]] * horizon

            scaler = MinMaxScaler()
            scaled = scaler.fit_transform(data.values.reshape(-1, 1))
            
            time_steps = 24
            X, y = [], []
            for i in range(len(scaled) - time_steps):
                X.append(scaled[i:i+time_steps])
                y.append(scaled[i+time_steps])
            
            X = np.array(X)
            y = np.array(y)
            
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(time_steps, 1)),
                Dropout(0.2),
                LSTM(50),
                Dropout(0.2),
                Dense(1)
            ])
            model.compile(optimizer=Adam(0.001), loss='mse')
            model.fit(X, y, epochs=10, batch_size=32, verbose=0)
            
            # Predict
            last_seq = scaled[-time_steps:].reshape(1, time_steps, 1)
            preds = []
            current = last_seq.copy()
            for _ in range(horizon):
                pred = model.predict(current, verbose=0)[0, 0]
                preds.append(pred)
                current = np.roll(current, -1)
                current[0, -1, 0] = pred
            
            preds = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
            
            # ✅ FIX: SAVE THE MODEL TO FILESYSTEM
            version_id = f"lstm_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            model_path = f"{self.models_dir}/{version_id}.h5"
            scaler_path = f"{self.models_dir}/{version_id}_scaler.pkl"
            
            # Save model and scaler
            model.save(model_path)
            joblib.dump(scaler, scaler_path)
            
            # Store version info in database
            self.store_model_version(
                model_type='lstm',
                model_params={'time_steps': time_steps, 'units': 50},
                performance_metrics={'rmse': 0.0},  # Placeholder - would calculate actual metrics
                training_data_info={'symbol': symbol, 'data_points': len(data)},
                version_id=version_id
            )
            
            logger.info(f"✅ LSTM model trained and saved: {version_id}")
            
            return model, scaler, preds.tolist()
            
        except Exception as e:
            logger.error(f"LSTM training failed: {e}")
            return None, None, [data.iloc[-1]] * horizon

    def predict_with_lstm(self, model, scaler, data, horizon):
        """Predict using loaded LSTM"""
        try:
            # ✅ FIX: Compile model before prediction to fix metrics issue
            model.compile(optimizer=Adam(0.001), loss='mse')
            
            scaled = scaler.transform(data.values.reshape(-1, 1))
            time_steps = 24
            last_seq = scaled[-time_steps:].reshape(1, time_steps, 1)
            preds = []
            current = last_seq.copy()
            for _ in range(horizon):
                pred = model.predict(current, verbose=0)[0, 0]
                preds.append(pred)
                current = np.roll(current, -1)
                current[0, -1, 0] = pred
            return scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten().tolist()
        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            return [data.iloc[-1]] * horizon

    def incremental_lstm_update(self, symbol, new_data, model_version_id):
        """Update LSTM model incrementally with new data using fine-tuning"""
        try:
            # Get existing model
            model_info = self.model_versions_coll.find_one({'version_id': model_version_id})
            if not model_info:
                logger.error(f"Model version {model_version_id} not found")
                return False
                
            # Load model architecture and weights
            model_path = f"{self.models_dir}/{model_version_id}.h5"
            if not os.path.exists(model_path):
                logger.error(f"Model file {model_path} not found")
                return False
                
            model = load_model(model_path)
            scaler = joblib.load(f"{self.models_dir}/{model_version_id}_scaler.pkl")
            
            # Prepare new data for incremental training
            if isinstance(new_data, pd.Series):
                new_data_scaled = scaler.transform(new_data.values.reshape(-1, 1))
            else:
                new_data_scaled = scaler.transform(np.array(new_data).reshape(-1, 1))
            
            # Use smaller learning rate for fine-tuning
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
            
            # Create sequences from new data
            time_steps = model_info.get('time_steps', 24)
            X_new, y_new = [], []
            for i in range(len(new_data_scaled) - time_steps):
                X_new.append(new_data_scaled[i:i+time_steps, 0])
                y_new.append(new_data_scaled[i+time_steps, 0])
            
            if len(X_new) > 0:
                X_new = np.array(X_new).reshape(-1, time_steps, 1)
                y_new = np.array(y_new)
                
                # Fine-tune with fewer epochs
                model.fit(X_new, y_new, epochs=5, batch_size=16, verbose=0, validation_split=0.2)
                
                # Save updated model
                new_version_id = f"lstm_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                model.save(f"{self.models_dir}/{new_version_id}.h5")
                joblib.dump(scaler, f"{self.models_dir}/{new_version_id}_scaler.pkl")
                
                # Store version info
                self.store_model_version(
                    model_type='lstm',
                    model_params=model_info['model_params'],
                    performance_metrics=model_info['performance_metrics'],
                    training_data_info={'symbol': symbol, 'data_points': len(new_data)},
                    version_id=new_version_id
                )
                
                logger.info(f"LSTM model incrementally updated: {new_version_id}")
                return new_version_id
            
            return model_version_id
            
        except Exception as e:
            logger.error(f"Error in incremental LSTM update: {str(e)}")
            return False

    def rolling_window_regression(self, symbol, data, window_size=100, step_size=10):
        """Implement rolling window regression for continuous adaptation"""
        try:
            if len(data) < window_size:
                return None
                
            predictions = []
            actuals = []
            performance_history = []
            
            for i in range(0, len(data) - window_size, step_size):
                window_data = data[i:i + window_size]
                
                # ✅ FIX: Normalize the data to prevent huge predictions
                scaler = StandardScaler()
                window_scaled = scaler.fit_transform(window_data.values.reshape(-1, 1)).flatten()
                
                # Simple linear regression on the window
                X = np.arange(len(window_scaled)).reshape(-1, 1)
                y = window_scaled
                
                # Use SGD for online learning
                model = SGDRegressor(learning_rate='adaptive', eta0=0.01)
                model.fit(X, y)
                
                # Predict next step and scale back
                next_pred_scaled = model.predict([[len(window_scaled)]])[0]
                next_pred = scaler.inverse_transform([[next_pred_scaled]])[0][0]
                predictions.append(next_pred)
                
                # Store performance if we have actual value
                if i + window_size < len(data):
                    actual = data.iloc[i + window_size]
                    actuals.append(actual)
                    
                    # Calculate metrics
                    error = abs(actual - next_pred)
                    performance_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'window_end': data.index[i + window_size].isoformat() if hasattr(data.index, 'isoformat') else str(data.index[i + window_size]),
                        'error': error,
                        'prediction': next_pred,
                        'actual': actual
                    })
            
            # Store rolling window performance
            if performance_history:
                self.performance_history_coll.insert_many([
                    {**perf, 'symbol': symbol, 'model_type': 'rolling_window'} 
                    for perf in performance_history
                ])
            
            return predictions[-10:] if predictions else []  # Return last 10 predictions
            
        except Exception as e:
            logger.error(f"Error in rolling window regression: {str(e)}")
            return None

    def adaptive_ensemble_weights(self, symbol, recent_performance):
        """Dynamically adjust ensemble weights based on recent performance"""
        try:
            # Calculate weights based on inverse error (better performance = higher weight)
            errors = {}
            weights = {}
            
            for model_type, performance in recent_performance.items():
                if performance and 'rmse' in performance:
                    errors[model_type] = performance['rmse']
            
            if errors:
                total_inverse_error = sum(1/err for err in errors.values() if err > 0)
                for model_type, error in errors.items():
                    if error > 0:
                        weights[model_type] = (1/error) / total_inverse_error
                return weights
            return {'arima': 0.5, 'lstm': 0.5}  # Default weights
            
        except Exception as e:
            logger.error(f"Error calculating adaptive weights: {str(e)}")
            return {'arima': 0.5, 'lstm': 0.5}

    def sliding_context_transformer(self, symbol, data, context_size=50, prediction_steps=10):
        """Transformer-like approach with sliding context windows"""
        try:
            if len(data) < context_size:
                return None
                
            predictions = []
            
            for i in range(len(data) - context_size):
                context = data.iloc[i:i + context_size]
                
                # Simple attention-like mechanism: weight recent points more heavily
                weights = np.exp(np.linspace(0, 1, context_size))
                weights = weights / weights.sum()
                
                # Weighted prediction (simplified transformer)
                weighted_avg = np.sum(context.values * weights)
                
                # Add some trend component
                recent_trend = np.polyfit(range(10), context.values[-10:], 1)[0] if len(context) >= 10 else 0
                prediction = weighted_avg + recent_trend * prediction_steps
                
                predictions.append(prediction)
                
                # Store context window performance
                if i + context_size < len(data):
                    actual = data.iloc[i + context_size]
                    self.log_prediction_accuracy(
                        symbol, 'sliding_context', [prediction], [actual], 
                        datetime.now().isoformat()
                    )
            
            return predictions[-prediction_steps:] if predictions else []
            
        except Exception as e:
            logger.error(f"Error in sliding context transformer: {str(e)}")
            return None

    def scheduled_retraining(self, symbol, data, model_type='ensemble', retrain_interval=7):
        """Schedule model retraining based on time interval"""
        try:
            # Check when model was last trained
            latest_model = self.get_latest_model_info(symbol, model_type)
            
            if latest_model:
                last_trained = datetime.fromisoformat(latest_model['created_at'].replace('Z', '+00:00'))
                days_since_retrain = (datetime.now().replace(tzinfo=None) - last_trained.replace(tzinfo=None)).days
                
                if days_since_retrain >= retrain_interval:
                    logger.info(f"Scheduled retraining triggered for {symbol} ({model_type})")
                    return self.retrain_model(symbol, data, model_type)
            
            return latest_model['version_id'] if latest_model else None
            
        except Exception as e:
            logger.error(f"Error in scheduled retraining: {str(e)}")
            return None

    def retrain_model(self, symbol, data, model_type):
        """Complete model retraining with latest data"""
        try:
            if model_type == 'lstm':
                # Retrain LSTM with all available data
                # ✅ FIX: Import inside method to avoid circular imports
                from enhanced_models import forecast_lstm
                
                # Use a simple retraining approach
                time_steps = 24
                if len(data) > time_steps:
                    # Scale data
                    scaler = MinMaxScaler()
                    scaled_data = scaler.fit_transform(data.values.reshape(-1, 1))
                    
                    # Build sequences
                    X, y = [], []
                    for i in range(len(scaled_data) - time_steps):
                        X.append(scaled_data[i:i+time_steps, 0])
                        y.append(scaled_data[i+time_steps, 0])
                    
                    if len(X) > 0:
                        X = np.array(X).reshape(-1, time_steps, 1)
                        y = np.array(y)
                        
                        # Build and train model
                        model = Sequential([
                            LSTM(50, return_sequences=True, input_shape=(time_steps, 1)),
                            Dropout(0.2),
                            LSTM(50, return_sequences=False),
                            Dropout(0.2),
                            Dense(25),
                            Dense(1)
                        ])
                        
                        model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
                        model.fit(X, y, epochs=20, batch_size=32, verbose=0, validation_split=0.2)
                        
                        # Save model
                        version_id = f"lstm_retrained_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        model.save(f"{self.models_dir}/{version_id}.h5")
                        joblib.dump(scaler, f"{self.models_dir}/{version_id}_scaler.pkl")
                        
                        # Store version info
                        self.store_model_version(
                            model_type='lstm',
                            model_params={'time_steps': time_steps, 'units': 50},
                            performance_metrics={'rmse': 0.0, 'mae': 0.0},  # Would calculate actual metrics
                            training_data_info={'symbol': symbol, 'data_points': len(data)},
                            version_id=version_id
                        )
                        
                        return version_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error in model retraining: {str(e)}")
            return None

    def store_model_version(self, model_type, model_params, performance_metrics, training_data_info, version_id=None):
        """Store a new version of a model with enhanced tracking"""
        if version_id is None:
            version_id = f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        version_data = {
            'version_id': version_id,
            'model_type': model_type,
            'symbol': training_data_info['symbol'],
            'model_params': model_params,
            'performance_metrics': performance_metrics,
            'training_data_range': training_data_info,
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        # Deactivate previous versions for this symbol + type
        self.model_versions_coll.update_many(
            {'model_type': model_type, 'symbol': training_data_info['symbol']},
            {'$set': {'is_active': False}}
        )
        
        self.model_versions_coll.insert_one(version_data)
        return version_id

    def get_latest_model_info(self, symbol, model_type):
        """Get the latest active model version info for a symbol"""
        latest_model = self.model_versions_coll.find_one(
            {'model_type': model_type, 'symbol': symbol, 'is_active': True},
            sort=[('created_at', -1)]
        )
        return latest_model

    def log_prediction_accuracy(self, symbol, model_type, predictions, actuals, timestamp):
        """Enhanced prediction accuracy logging with trend analysis"""
        try:
            if len(predictions) != len(actuals) or len(predictions) == 0:
                return None
            
            # Calculate comprehensive metrics
            errors = np.array(actuals) - np.array(predictions)
            mae = np.mean(np.abs(errors))
            rmse = np.sqrt(np.mean(errors**2))
            mape = np.mean(np.abs(errors / np.array(actuals))) * 100 if all(a != 0 for a in actuals) else None
            
            # Trend analysis
            if len(errors) > 5:
                error_trend = np.polyfit(range(len(errors)), errors, 1)[0]  # Slope of error trend
            else:
                error_trend = 0
            
            performance_data = {
                'symbol': symbol,
                'model_type': model_type,
                'timestamp': timestamp,
                'metrics': {
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'mape': float(mape) if mape else None,
                    'error_trend': float(error_trend),
                    'bias': float(np.mean(errors))  # Systematic bias
                },
                'predictions': [float(p) for p in predictions],
                'actuals': [float(a) for a in actuals],
                'created_at': datetime.now().isoformat()
            }
            
            self.performance_history_coll.insert_one(performance_data)
            
            # Check if model needs retraining based on performance degradation
            self.check_retraining_needed(symbol, model_type)
            
            return performance_data['metrics']
            
        except Exception as e:
            logger.error(f"Error logging prediction accuracy: {str(e)}")
            return None

    def check_retraining_needed(self, symbol, model_type, lookback_days=30):
        """Determine if model needs retraining based on performance degradation"""
        try:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            
            recent_performance = list(self.performance_history_coll.find({
                'model_type': model_type,
                'symbol': symbol,
                'timestamp': {'$gte': cutoff_date.isoformat()}
            }).sort('timestamp', 1))
            
            if len(recent_performance) < 10:
                return False
            
            # Analyze performance trends
            recent_errors = [p.get('metrics', {}).get('rmse', 0) for p in recent_performance[-10:]]
            recent_bias = [p.get('metrics', {}).get('bias', 0) for p in recent_performance[-10:]]
            
            # Calculate trends
            error_trend = np.polyfit(range(len(recent_errors)), recent_errors, 1)[0]
            bias_trend = np.polyfit(range(len(recent_bias)), recent_bias, 1)[0]
            
            # Retrain if errors are increasing significantly or bias is growing
            needs_retrain = (error_trend > 0.1) or (abs(bias_trend) > 0.05)
            
            if needs_retrain:
                logger.info(f"Retraining needed for {symbol} {model_type}. Error trend: {error_trend:.3f}, Bias trend: {bias_trend:.3f}")
                
            return needs_retrain
            
        except Exception as e:
            logger.error(f"Error checking retraining need: {str(e)}")
            return False

    def get_performance_history(self, symbol, model_type, days=30):
        """Get performance history for analysis and visualization"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            performance_data = list(self.performance_history_coll.find({
                'symbol': symbol,
                'model_type': model_type,
                'timestamp': {'$gte': cutoff_date.isoformat()}
            }).sort('timestamp', 1))
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Error getting performance history: {str(e)}")
            return []

    def adaptive_forecast(self, symbol, data, horizon=24, use_ensemble=True):
        """Main adaptive forecasting method that combines all techniques"""
        try:
            forecasts = {}
            recent_performance = {}
            
            # ✅ FIX: Get recent performance with proper error handling
            for model_type in ['arima', 'lstm', 'rolling_window']:
                perf_data = self.get_performance_history(symbol, model_type, days=7)
                if perf_data and len(perf_data) > 0:
                    # ✅ FIX: Check if 'metrics' exists before accessing
                    recent_performance[model_type] = perf_data[-1].get('metrics', None)
                else:
                    recent_performance[model_type] = None
            
            # Generate forecasts using different methods
            if use_ensemble:
                # ✅ FIX: ARIMA forecast with proper import
                try:
                    # Import ARIMA forecasting function
                    from enhanced_models import forecast_arima
                    arima_forecast = forecast_arima(data, horizon)
                    forecasts['arima'] = arima_forecast
                    logger.info(f"✅ ARIMA forecast generated: {len(arima_forecast)} points")
                except Exception as e:
                    logger.warning(f"ARIMA forecast failed: {str(e)}")
                    forecasts['arima'] = [data.iloc[-1]] * horizon
                
                # LSTM forecast
                lstm_forecast = None
                latest_lstm = self.get_latest_model_info(symbol, 'lstm')

                if latest_lstm and os.path.exists(f"{self.models_dir}/{latest_lstm['version_id']}.h5"):
                    # Load existing model
                    try:
                        model = load_model(f"{self.models_dir}/{latest_lstm['version_id']}.h5")
                        scaler = joblib.load(f"{self.models_dir}/{latest_lstm['version_id']}_scaler.pkl")
                        lstm_forecast = self.predict_with_lstm(model, scaler, data, horizon)
                        logger.info(f"Using existing LSTM model: {latest_lstm['version_id']}")
                    except Exception as e:
                        logger.warning(f"Failed to load LSTM model: {e}")
                else:
                    # TRAIN FROM SCRATCH
                    logger.info(f"NO LSTM MODEL FOR {symbol} → TRAINING FROM SCRATCH")
                    model, scaler, lstm_forecast = self.train_lstm_from_scratch(symbol, data, horizon)
                    if model:
                        version_id = f"lstm_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        model.save(f"{self.models_dir}/{version_id}.h5")
                        joblib.dump(scaler, f"{self.models_dir}/{version_id}_scaler.pkl")
                        
                        self.store_model_version(
                            model_type='lstm',
                            model_params={'time_steps': 24, 'units': 50},
                            performance_metrics={'rmse': 0.0},
                            training_data_info={'symbol': symbol, 'data_points': len(data)},
                            version_id=version_id
                        )
                        logger.info(f"SAVED NEW LSTM MODEL: {version_id}")

                forecasts['lstm'] = lstm_forecast or [data.iloc[-1]] * horizon
                
                # Rolling window forecast
                rolling_forecast = self.rolling_window_regression(symbol, data)
                if rolling_forecast:
                    forecasts['rolling_window'] = rolling_forecast[-horizon:] if len(rolling_forecast) >= horizon else [data.iloc[-1]] * horizon
                
                # Adaptive ensemble
                weights = self.adaptive_ensemble_weights(symbol, recent_performance)
                logger.info(f"📊 Ensemble weights: {weights}")
                
                # Combine forecasts
                ensemble_forecast = []
                for i in range(horizon):
                    weighted_sum = 0
                    total_weight = 0
                    
                    for model_type, weight in weights.items():
                        if model_type in forecasts and i < len(forecasts[model_type]):
                            weighted_sum += forecasts[model_type][i] * weight
                            total_weight += weight
                    
                    if total_weight > 0:
                        ensemble_forecast.append(weighted_sum / total_weight)
                    else:
                        ensemble_forecast.append(data.iloc[-1])
                
                final_forecast = ensemble_forecast
                model_used = 'adaptive_ensemble'
                
            else:
                # Use single best performing model
                best_model = min(recent_performance.items(), 
                               key=lambda x: x[1].get('rmse', float('inf')) if x[1] else float('inf'))
                if best_model[1]:
                    final_forecast = forecasts.get(best_model[0], [data.iloc[-1]] * horizon)
                    model_used = best_model[0]
                else:
                    # Fallback to ARIMA
                    try:
                        from enhanced_models import forecast_arima
                        final_forecast = forecast_arima(data, horizon)
                        model_used = 'arima'
                    except:
                        final_forecast = [data.iloc[-1]] * horizon
                        model_used = 'fallback'
            
            # Schedule retraining if needed
            self.scheduled_retraining(symbol, data)
            
            return final_forecast, model_used
            
        except Exception as e:
            logger.error(f"Error in adaptive forecast: {str(e)}")
            # Fallback to simple forecast
            return [data.iloc[-1]] * horizon, 'fallback'

# Global instance
enhanced_adaptive_manager = EnhancedAdaptiveLearningManager()