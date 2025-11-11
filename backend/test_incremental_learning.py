# test_incremental_learning.py
import os
import logging
import yfinance as yf
import pandas as pd
from enhanced_adaptive_learning import enhanced_adaptive_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_incremental_learning():
    print("🧪 TESTING INCREMENTAL LEARNING")
    print("=" * 50)
    
    # Get initial data
    ticker = yf.Ticker('AAPL')
    initial_data = ticker.history(period='3mo')['Close']
    print(f"📊 Initial data: {len(initial_data)} points")
    
    # Generate first forecast (creates initial model)
    print("🔄 Creating initial model...")
    forecast1, model1 = enhanced_adaptive_manager.adaptive_forecast('AAPL', initial_data, 12)
    print(f"✅ Initial forecast completed using: {model1}")
    
    # Get newer data for incremental update
    new_data = ticker.history(period='1mo')['Close']
    print(f"📈 New data for incremental update: {len(new_data)} points")
    
    # Get latest model info for incremental update
    latest_model = enhanced_adaptive_manager.get_latest_model_info('AAPL', 'lstm')
    if latest_model:
        print(f"🔍 Latest model version: {latest_model['version_id']}")
        
        # Test incremental update
        print("🔄 Testing incremental LSTM update...")
        new_version = enhanced_adaptive_manager.incremental_lstm_update('AAPL', new_data, latest_model['version_id'])
        
        if new_version:
            print(f"✅ Incremental update successful!")
            print(f"📁 New version: {new_version}")
            
            # Verify new model file exists
            new_model_path = f"saved_models/{new_version}.h5"
            if os.path.exists(new_model_path):
                print(f"✅ New model file created: {new_model_path}")
            else:
                print(f"❌ New model file not found")
                
            # Check database for new version
            from pymongo import MongoClient
            client = MongoClient('mongodb://localhost:27017/')
            db = client['stock_forecast_db']
            new_version_record = db.model_versions.find_one({'version_id': new_version})
            if new_version_record:
                print(f"✅ New version recorded in database")
            else:
                print(f"❌ New version not found in database")
        else:
            print("❌ Incremental update failed")
    else:
        print("❌ No existing model found for incremental update")
    
    print("🎯 INCREMENTAL LEARNING TEST COMPLETED")

if __name__ == "__main__":
    test_incremental_learning()