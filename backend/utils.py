import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

def fetch_data_from_yfinance(symbol, start_date, end_date, interval='1d'):
    """
    Fetch OHLCV data from Yahoo Finance with enhanced error handling and fallbacks.
    """
    try:
        logger.info(f"📥 Fetching data for {symbol} from {start_date} to {end_date} (interval: {interval})")
        
        # Clean symbol
        symbol = symbol.upper().strip()
        
        # Try multiple interval options if the requested one fails
        intervals_to_try = [interval, '1d', '1h'] if interval != '1d' else ['1d', '1h']
        
        for interval_try in intervals_to_try:
            try:
                logger.info(f"🔄 Trying interval: {interval_try}")
                
                # Download data
                df = yf.download(
                    symbol, 
                    start=start_date, 
                    end=end_date, 
                    interval=interval_try,
                    progress=False,
                    auto_adjust=True
                )
                
                if not df.empty:
                    logger.info(f"✅ Successfully fetched {len(df)} rows with interval {interval_try}")
                    
                    # Ensure we have the required columns
                    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    if all(col in df.columns for col in required_columns):
                        return df
                    else:
                        logger.warning(f"⚠️ Missing some columns in data. Available: {df.columns.tolist()}")
                        # Try to create missing columns from available data
                        if 'Close' in df.columns:
                            if 'Open' not in df.columns:
                                df['Open'] = df['Close']
                            if 'High' not in df.columns:
                                df['High'] = df['Close']
                            if 'Low' not in df.columns:
                                df['Low'] = df['Close']
                            if 'Volume' not in df.columns:
                                df['Volume'] = 0
                            return df
                
            except Exception as e:
                logger.warning(f"❌ Failed with interval {interval_try}: {str(e)}")
                continue
        
        # If all intervals failed, try direct Ticker method
        logger.info("🔄 Trying direct Ticker method...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')
            if not df.empty:
                logger.info(f"✅ Direct Ticker method successful: {len(df)} rows")
                return df
        except Exception as e:
            logger.warning(f"❌ Direct Ticker method failed: {str(e)}")
        
        logger.error(f"❌ All data fetch methods failed for {symbol}")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching data for {symbol}: {str(e)}")
        return pd.DataFrame()

def fetch_stock_data(symbol, period='1mo', interval='1d'):
    """
    Alternative method to fetch stock data with different parameters.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            logger.warning(f"No data found for {symbol} with period {period}")
            return pd.DataFrame()
            
        logger.info(f"Fetched {len(data)} rows for {symbol}")
        return data
        
    except Exception as e:
        logger.error(f"Error in fetch_stock_data for {symbol}: {str(e)}")
        return pd.DataFrame()

def generate_candlestick_chart(historical_df, future_dates=None, predictions=None, title='Stock Price with Forecast'):
    """
    Generate Plotly candlestick chart with optional forecast overlay.
    """
    try:
        fig = go.Figure()

        # Ensure we have a DataFrame and required columns
        if historical_df is None or historical_df.empty:
            logger.warning("No historical data provided for chart generation")
            return "<div>No data available for chart</div>"

        # Check for required columns
        required_columns = ['Open', 'High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in historical_df.columns]
        if missing_columns:
            logger.warning(f"Missing columns for candlestick: {missing_columns}")
            # Create a simple line chart instead
            if 'Close' in historical_df.columns:
                fig.add_trace(go.Scatter(
                    x=historical_df.index,
                    y=historical_df['Close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='blue')
                ))
            else:
                return "<div>Insufficient data for chart</div>"
        else:
            # Historical candlestick
            fig.add_trace(go.Candlestick(
                x=historical_df.index,
                open=historical_df['Open'],
                high=historical_df['High'],
                low=historical_df['Low'],
                close=historical_df['Close'],
                name='Historical'
            ))

        # Add forecast if provided
        if future_dates is not None and predictions is not None:
            if len(future_dates) == len(predictions):
                fig.add_trace(go.Scatter(
                    x=future_dates,
                    y=predictions,
                    mode='lines+markers',
                    name='Forecast',
                    line=dict(color='red', dash='dot'),
                    marker=dict(size=4)
                ))
            else:
                logger.warning("Forecast dates and predictions length mismatch")

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Price',
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            height=500,
            showlegend=True
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')
        
    except Exception as e:
        logger.error(f"Error generating candlestick chart: {str(e)}")
        return f"<div>Error generating chart: {str(e)}</div>"

def generate_forecast_chart(historical_data, forecast_data, title='Price Forecast'):
    """
    Generate a comprehensive chart with historical data and forecasts.
    """
    try:
        fig = go.Figure()

        # Add historical data
        if 'Close' in historical_data.columns:
            fig.add_trace(go.Scatter(
                x=historical_data.index,
                y=historical_data['Close'],
                mode='lines',
                name='Historical Close',
                line=dict(color='#1f77b4', width=2)
            ))

        # Add forecast data
        if forecast_data and len(forecast_data) > 0:
            # Extract dates and predictions from forecast data
            if isinstance(forecast_data, pd.DataFrame):
                forecast_dates = forecast_data.index
                predictions = forecast_data['predicted_price'] if 'predicted_price' in forecast_data.columns else forecast_data.iloc[:, 0]
            else:
                # Assume it's a list of dictionaries
                forecast_dates = [pd.to_datetime(f['target_timestamp']) for f in forecast_data]
                predictions = [f['predicted_price'] for f in forecast_data]

            fig.add_trace(go.Scatter(
                x=forecast_dates,
                y=predictions,
                mode='lines+markers',
                name='Forecast',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                marker=dict(size=4)
            ))

            # Add confidence intervals if available
            if isinstance(forecast_data, list) and all('confidence_lower' in f and 'confidence_upper' in f for f in forecast_data):
                lower_bounds = [f['confidence_lower'] for f in forecast_data]
                upper_bounds = [f['confidence_upper'] for f in forecast_data]
                
                fig.add_trace(go.Scatter(
                    x=forecast_dates + forecast_dates[::-1],
                    y=upper_bounds + lower_bounds[::-1],
                    fill='toself',
                    fillcolor='rgba(255, 127, 14, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Confidence Interval'
                ))

        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Price',
            template='plotly_dark',
            height=500,
            showlegend=True
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')
        
    except Exception as e:
        logger.error(f"Error generating forecast chart: {str(e)}")
        return f"<div>Error generating forecast chart: {str(e)}</div>"

def calculate_metrics(actual, predicted):
    """
    Compute RMSE, MAE, MAPE with enhanced error handling.
    """
    try:
        # Convert to numpy arrays and handle None values
        actual = np.array(actual, dtype=float)
        predicted = np.array(predicted, dtype=float)
        
        # Remove any NaN or Inf values
        mask = np.isfinite(actual) & np.isfinite(predicted)
        actual_clean = actual[mask]
        predicted_clean = predicted[mask]
        
        if len(actual_clean) == 0 or len(predicted_clean) == 0:
            logger.warning("No valid data for metric calculation")
            return {'RMSE': None, 'MAE': None, 'MAPE': None}
        
        if len(actual_clean) != len(predicted_clean):
            min_len = min(len(actual_clean), len(predicted_clean))
            actual_clean = actual_clean[:min_len]
            predicted_clean = predicted_clean[:min_len]
        
        # Calculate metrics
        rmse = np.sqrt(mean_squared_error(actual_clean, predicted_clean))
        mae = mean_absolute_error(actual_clean, predicted_clean)
        
        # Calculate MAPE carefully (handle zero actual values)
        with np.errstate(divide='ignore', invalid='ignore'):
            percentage_errors = np.abs((actual_clean - predicted_clean) / actual_clean)
            percentage_errors = percentage_clean[np.isfinite(percentage_errors)]
            mape = np.mean(percentage_errors) * 100 if len(percentage_errors) > 0 else None
        
        metrics = {
            'RMSE': round(rmse, 4),
            'MAE': round(mae, 4),
            'MAPE': round(mape, 2) if mape is not None else None,
            'samples_used': len(actual_clean)
        }
        
        logger.info(f"Calculated metrics: RMSE={metrics['RMSE']}, MAE={metrics['MAE']}, MAPE={metrics['MAPE']}")
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        return {'RMSE': None, 'MAE': None, 'MAPE': None, 'error': str(e)}

def prepare_forecast_data(historical_series, horizon, last_date=None):
    """
    Prepare data structures for forecasting.
    """
    try:
        if last_date is None:
            last_date = datetime.now()
        
        # Generate future dates
        if isinstance(historical_series, pd.Series) and hasattr(historical_series.index, 'freq'):
            # Use the frequency of the historical data
            future_dates = pd.date_range(
                start=historical_series.index[-1] + pd.Timedelta(hours=1),
                periods=horizon,
                freq=historical_series.index.freq or 'H'
            )
        else:
            # Default to hourly frequency
            future_dates = pd.date_range(
                start=last_date + timedelta(hours=1),
                periods=horizon,
                freq='H'
            )
        
        return future_dates
        
    except Exception as e:
        logger.error(f"Error preparing forecast data: {str(e)}")
        # Return default future dates
        return pd.date_range(
            start=datetime.now() + timedelta(hours=1),
            periods=horizon,
            freq='H'
        )

def validate_symbol(symbol):
    """
    Validate if a symbol exists and is accessible on Yahoo Finance.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Check if we have basic info
        if info and 'regularMarketPrice' in info:
            return True
            
        # Try to get historical data as fallback
        data = ticker.history(period='1d')
        return not data.empty
        
    except Exception as e:
        logger.warning(f"Symbol validation failed for {symbol}: {str(e)}")
        return False

def get_symbol_info(symbol):
    """
    Get basic information about a symbol.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            'symbol': symbol,
            'name': info.get('longName', info.get('shortName', symbol)),
            'currency': info.get('currency', 'USD'),
            'exchange': info.get('exchange', 'Unknown'),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'market_cap': info.get('marketCap'),
            'current_price': info.get('regularMarketPrice')
        }
    except Exception as e:
        logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
        return {
            'symbol': symbol,
            'name': symbol,
            'currency': 'USD',
            'exchange': 'Unknown',
            'error': str(e)
        }