import os
import logging
import shutil
from enhanced_adaptive_learning import enhanced_adaptive_manager
import yfinance as yf
from pymongo import MongoClient

logging.basicConfig(level=logging.DEBUG)

print('=== TESTING FIXED MODEL SAVING ===')

# Clear any existing models to force training from scratch
if os.path.exists('saved_models'):
    shutil.rmtree('saved_models')
os.makedirs('saved_models', exist_ok=True)

# Get data
ticker = yf.Ticker('AAPL')
data = ticker.history(period='3mo')['Close']
print(f'Data loaded: {len(data)} points')

# This should now trigger model training AND saving
print('Calling adaptive_forecast (should train and save new model)...')
forecast, model_used = enhanced_adaptive_manager.adaptive_forecast('AAPL', data, 24, use_ensemble=True)
print(f'Forecast completed using: {model_used}')

# Check if files were created
model_files = [f for f in os.listdir('saved_models') if f.endswith('.h5')]
scaler_files = [f for f in os.listdir('saved_models') if f.endswith('.pkl')]

print(f'Models created: {len(model_files)}')
print(f'Scalers created: {len(scaler_files)}')

if model_files:
    print('Latest model files:')
    for f in model_files[-3:]:
        print(f'  - {f}')

# Check database
client = MongoClient('mongodb://localhost:27017/')
db = client['stock_forecast_db']
model_versions = db.model_versions.count_documents({})
print(f'Model versions in DB: {model_versions}')
