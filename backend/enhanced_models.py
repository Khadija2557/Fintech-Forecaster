# enhanced_models.py
# Add to the top of enhanced_models.py (after existing imports)
import os
import joblib
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from utils import calculate_metrics
import logging
from enhanced_adaptive_learning import enhanced_adaptive_manager

logger = logging.getLogger(__name__)

# In enhanced_adaptive_learning.py, update the adaptive_forecast method:

def adaptive_forecast_arima(self, symbol, data, horizon=24, use_ensemble=True):
    """Main adaptive forecasting method that combines all techniques"""
    try:
        # First, check if we need to retrain
        needs_retrain = self.check_retraining_needed(symbol, 'lstm')
        if needs_retrain and len(data) > 50:  # Only retrain if we have enough data
            logger.info(f"🔄 Auto-retraining triggered for {symbol}")
            self.retrain_model(symbol, data, 'lstm')
        
        forecasts = {}
        recent_performance = {}
        
        # Get recent performance for weight adjustment
        for model_type in ['arima', 'lstm', 'rolling_window']:
            perf_data = self.get_performance_history(symbol, model_type, days=7)
            if perf_data:
                recent_performance[model_type] = perf_data[-1]['metrics'] if perf_data else None
        
        # Generate forecasts using different methods
        if use_ensemble:
            # ARIMA forecast
            from enhanced_models import forecast_arima
            try:
                arima_forecast = forecast_arima(data, horizon)
                forecasts['arima'] = arima_forecast
                logger.info(f"✅ ARIMA forecast generated: {len(arima_forecast)} points")
            except Exception as e:
                logger.warning(f"❌ ARIMA forecast failed: {str(e)}")
                forecasts['arima'] = [data.iloc[-1]] * horizon
            
            # LSTM forecast  
            from enhanced_models import forecast_lstm
            try:
                lstm_forecast = forecast_lstm(data, horizon, symbol)
                forecasts['lstm'] = lstm_forecast
                logger.info(f"✅ LSTM forecast generated: {len(lstm_forecast)} points")
            except Exception as e:
                logger.warning(f"❌ LSTM forecast failed: {str(e)}")
                forecasts['lstm'] = [data.iloc[-1]] * horizon
            
            # Rolling window forecast
            try:
                rolling_forecast = self.rolling_window_regression(symbol, data)
                if rolling_forecast:
                    forecasts['rolling_window'] = rolling_forecast[-horizon:] if len(rolling_forecast) >= horizon else [data.iloc[-1]] * horizon
                    logger.info(f"✅ Rolling window forecast generated")
                else:
                    forecasts['rolling_window'] = [data.iloc[-1]] * horizon
            except Exception as e:
                logger.warning(f"❌ Rolling window forecast failed: {str(e)}")
                forecasts['rolling_window'] = [data.iloc[-1]] * horizon
            
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
            if recent_performance:
                best_model = min(recent_performance.items(), 
                               key=lambda x: x[1]['rmse'] if x[1] else float('inf'))
                if best_model[1]:
                    final_forecast = forecasts.get(best_model[0], [data.iloc[-1]] * horizon)
                    model_used = best_model[0]
                else:
                    # Fallback to ARIMA
                    from enhanced_models import forecast_arima
                    final_forecast = forecast_arima(data, horizon)
                    model_used = 'arima'
            else:
                # Fallback to ARIMA
                from enhanced_models import forecast_arima
                final_forecast = forecast_arima(data, horizon)
                model_used = 'arima'
        
        # Schedule retraining if needed
        self.scheduled_retraining(symbol, data)
        
        logger.info(f"✅ Adaptive forecast completed using {model_used}")
        return final_forecast, model_used
        
    except Exception as e:
        logger.error(f"❌ Error in adaptive forecast: {str(e)}")
        logger.error(traceback.format_exc())
        # Fallback to simple forecast
        return [data.iloc[-1]] * horizon, 'fallback'

def adaptive_forecast_lstm(series, steps, symbol=None, time_steps=24):
    """Enhanced LSTM with incremental learning support and robust model saving"""
    try:
        logger.info(f"🔄 Starting LSTM forecast for {symbol}, steps: {steps}, data points: {len(series)}")
        
        # Validate input data
        if len(series) < time_steps + 1:
            logger.warning(f"❌ Insufficient data for LSTM: {len(series)} points, need at least {time_steps + 1}")
            last_value = series.iloc[-1] if len(series) > 0 else 0
            return np.array([last_value] * steps)
        
        data = series.values.reshape(-1, 1)
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(data)

        # Check for existing model first
        existing_model_used = False
        if symbol:
            latest_model = enhanced_adaptive_manager.get_latest_model_info(symbol, 'lstm')
            if latest_model:
                try:
                    model_path = f"saved_models/{latest_model['version_id']}.h5"
                    scaler_path = f"saved_models/{latest_model['version_id']}_scaler.pkl"
                    
                    if os.path.exists(model_path) and os.path.exists(scaler_path):
                        logger.info(f"📁 Loading existing LSTM model: {latest_model['version_id']}")
                        model = load_model(model_path)
                        existing_scaler = joblib.load(scaler_path)
                        
                        # Use existing model for prediction
                        inputs = scaled_data[-time_steps:].reshape(1, time_steps, 1)
                        predictions = []
                        for _ in range(steps):
                            pred = model.predict(inputs, verbose=0)
                            predictions.append(pred[0,0])
                            inputs = np.append(inputs[:,1:,:], pred.reshape(1,1,1), axis=1)
                        
                        # Inverse transform using the loaded scaler
                        predictions = existing_scaler.inverse_transform(np.array(predictions).reshape(-1,1)).flatten()
                        
                        # Log performance for model evaluation
                        if len(series) > steps:
                            recent_actual = series[-steps:].values
                            try:
                                enhanced_adaptive_manager.log_prediction_accuracy(
                                    symbol, 'lstm', predictions, recent_actual,
                                    datetime.now().isoformat()
                                )
                                logger.info("✅ Performance logged for existing model")
                            except Exception as log_error:
                                logger.warning(f"⚠️ Could not log performance: {log_error}")
                        
                        existing_model_used = True
                        logger.info(f"✅ Existing LSTM model used successfully, predictions: {len(predictions)}")
                        return predictions
                        
                except Exception as e:
                    logger.warning(f"❌ Could not load existing LSTM model: {str(e)}")
                    # Continue to train new model

        # Train new model if no existing model or loading failed
        logger.info("🆕 Training new LSTM model...")
        
        # Prepare training data
        X, y = [], []
        for i in range(len(scaled_data) - time_steps):
            X.append(scaled_data[i:i+time_steps, 0])
            y.append(scaled_data[i+time_steps, 0])
        
        if len(X) == 0:
            raise ValueError(f"Insufficient data for LSTM training. Need at least {time_steps + 1} data points, got {len(series)}")
        
        X, y = np.array(X), np.array(y)
        X = X.reshape((X.shape[0], X.shape[1], 1))

        logger.info(f"📊 Training data prepared: X.shape={X.shape}, y.shape={y.shape}")

        # Build enhanced LSTM model
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(time_steps, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
        
        # Train with progress tracking
        logger.info("🎯 Training LSTM model...")
        history = model.fit(
            X, y, 
            epochs=20, 
            batch_size=32, 
            verbose=0, 
            validation_split=0.2,
            callbacks=[]
        )
        
        final_loss = history.history['loss'][-1]
        logger.info(f"✅ LSTM training completed. Final loss: {final_loss:.6f}")

        # Generate forecasts
        inputs = scaled_data[-time_steps:].reshape(1, time_steps, 1)
        predictions = []
        
        logger.info("🔮 Generating forecasts...")
        for i in range(steps):
            pred = model.predict(inputs, verbose=0)
            predictions.append(pred[0,0])
            # Update inputs for next prediction
            inputs = np.append(inputs[:,1:,:], pred.reshape(1,1,1), axis=1)
        
        # Convert predictions back to original scale
        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1,1)).flatten()
        logger.info(f"✅ Forecasts generated: {len(predictions)} points")

        # SAVE MODEL - CRITICAL SECTION WITH PROPER ERROR HANDLING
        if symbol:
            try:
                # Ensure saved_models directory exists
                os.makedirs("saved_models", exist_ok=True)
                
                # Generate unique version ID
                version_id = f"lstm_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                model_path = f"saved_models/{version_id}.h5"
                scaler_path = f"saved_models/{version_id}_scaler.pkl"
                
                logger.info(f"💾 Saving model to: {model_path}")
                
                # Save model and scaler
                model.save(model_path)
                joblib.dump(scaler, scaler_path)
                
                # Verify files were created
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    logger.info(f"✅ Model saved successfully: {model_path}")
                    logger.info(f"✅ Scaler saved successfully: {scaler_path}")
                    
                    # Calculate basic performance metrics for storage
                    if len(series) > steps:
                        recent_actual = series[-steps:].values
                        try:
                            mae = np.mean(np.abs(recent_actual - predictions))
                            rmse = np.sqrt(np.mean((recent_actual - predictions) ** 2))
                            performance_metrics = {'mae': float(mae), 'rmse': float(rmse)}
                        except:
                            performance_metrics = {'mae': 0.0, 'rmse': 0.0}
                    else:
                        performance_metrics = {'mae': 0.0, 'rmse': 0.0}
                    
                    # Store model version in database
                    try:
                        enhanced_adaptive_manager.store_model_version(
                            model_type='lstm',
                            model_params={
                                'time_steps': time_steps, 
                                'units': 50,
                                'epochs': 20,
                                'batch_size': 32,
                                'loss': float(final_loss)
                            },
                            performance_metrics=performance_metrics,
                            training_data_info={
                                'symbol': symbol, 
                                'data_points': len(series),
                                'training_samples': len(X),
                                'data_range': {
                                    'start': series.index[0].isoformat() if hasattr(series.index[0], 'isoformat') else str(series.index[0]),
                                    'end': series.index[-1].isoformat() if hasattr(series.index[-1], 'isoformat') else str(series.index[-1])
                                }
                            },
                            version_id=version_id
                        )
                        logger.info(f"✅ Model version stored in database: {version_id}")
                    except Exception as db_error:
                        logger.error(f"❌ Failed to store model version in database: {db_error}")
                
                else:
                    logger.error(f"❌ Model files not created properly: {model_path}")
                    
            except Exception as save_error:
                logger.error(f"❌ Error saving LSTM model: {str(save_error)}")
                logger.error(traceback.format_exc())
        
        # Log prediction accuracy for the new model
        if len(series) > steps and not existing_model_used:
            try:
                recent_actual = series[-steps:].values
                enhanced_adaptive_manager.log_prediction_accuracy(
                    symbol, 'lstm', predictions, recent_actual,
                    datetime.now().isoformat()
                )
                logger.info("✅ Performance logged for new model")
            except Exception as log_error:
                logger.warning(f"⚠️ Could not log performance for new model: {log_error}")

        logger.info(f"✅ LSTM forecast completed successfully. Returning {len(predictions)} predictions")
        return predictions
        
    except ValueError as ve:
        logger.error(f"❌ Data validation error in LSTM forecast: {ve}")
        last_value = series.iloc[-1] if len(series) > 0 else 0
        return np.array([last_value] * steps)
    except Exception as e:
        logger.error(f"❌ Unexpected error in adaptive LSTM forecast: {str(e)}")
        logger.error(traceback.format_exc())
        last_value = series.iloc[-1] if len(series) > 0 else 0
        return np.array([last_value] * steps)

def adaptive_ensemble_forecast(series, steps, symbol=None):
    """Enhanced ensemble with adaptive weighting"""
    try:
        # Get individual forecasts
        arima_pred = adaptive_forecast_arima(series, steps, symbol)
        lstm_pred = adaptive_forecast_lstm(series, steps, symbol)
        
        # Get recent performance for adaptive weighting
        recent_performance = {}
        for model_type in ['arima', 'lstm']:
            perf_data = enhanced_adaptive_manager.get_performance_history(symbol, model_type, days=7)
            if perf_data:
                recent_performance[model_type] = perf_data[-1]['metrics'] if perf_data else None
        
        # Calculate adaptive weights
        weights = enhanced_adaptive_manager.adaptive_ensemble_weights(symbol, recent_performance)
        
        # Apply weights
        weighted_forecast = []
        for i in range(steps):
            weighted_val = (arima_pred[i] * weights.get('arima', 0.5) + 
                          lstm_pred[i] * weights.get('lstm', 0.5))
            weighted_forecast.append(weighted_val)
        
        return np.array(weighted_forecast)
        
    except Exception as e:
        logger.error(f"Adaptive ensemble forecast error: {e}")
        # Fallback to simple average
        return (arima_pred + lstm_pred) / 2
    
    
# Add to the bottom of enhanced_models.py

def forecast_arima(series, steps):
    """Wrapper function for ARIMA forecasting used by adaptive system"""
    return adaptive_forecast_arima(series, steps)

def forecast_lstm(series, steps):
    """Wrapper function for LSTM forecasting used by adaptive system"""
    return adaptive_forecast_lstm(series, steps)

def ensemble_forecast(arima_pred, lstm_pred):
    """Simple ensemble averaging"""
    return (np.array(arima_pred) + np.array(lstm_pred)) / 2