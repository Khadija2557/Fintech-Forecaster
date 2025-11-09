# models.py
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from utils import calculate_metrics
import logging

logger = logging.getLogger(__name__)

def forecast_arima(series, steps):
    """
    Forecast using ARIMA (AutoRegressive Integrated Moving Average).
    Order (5,1,0) as a simple default; tune in production.
    """
    try:
        model = ARIMA(series, order=(5,1,0))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
        return forecast
    except Exception as e:
        logger.error(f"ARIMA forecast error: {e}")
        # Return simple forecast as fallback
        last_value = series.iloc[-1]
        return np.array([last_value] * steps)

def forecast_lstm(series, steps, time_steps=24):
    """
    Forecast using LSTM. Scales data, trains on sequences.
    """
    try:
        data = series.values.reshape(-1, 1)
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(data)

        # Create sequences
        X, y = [], []
        for i in range(len(scaled_data) - time_steps):
            X.append(scaled_data[i:i+time_steps, 0])
            y.append(scaled_data[i+time_steps, 0])
        X, y = np.array(X), np.array(y)
        X = X.reshape((X.shape[0], X.shape[1], 1))

        # Build model
        model = Sequential()
        model.add(LSTM(50, return_sequences=True, input_shape=(time_steps, 1)))
        model.add(LSTM(50))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X, y, epochs=10, batch_size=32, verbose=0)

        # Forecast
        inputs = scaled_data[-time_steps:].reshape(1, time_steps, 1)
        predictions = []
        for _ in range(steps):
            pred = model.predict(inputs, verbose=0)
            predictions.append(pred[0,0])
            inputs = np.append(inputs[:,1:,:], pred.reshape(1,1,1), axis=1)
        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1,1)).flatten()

        return predictions
        
    except Exception as e:
        logger.error(f"LSTM forecast error: {e}")
        # Fallback to simple forecast
        last_value = series.iloc[-1]
        return np.array([last_value] * steps)

def ensemble_forecast(pred1, pred2):
    """
    Simple ensemble: average of two predictions.
    """
    return (pred1 + pred2) / 2