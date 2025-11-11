# test_retraining.py
import logging
import yfinance as yf
from datetime import datetime, timedelta
from enhanced_adaptive_learning import enhanced_adaptive_manager

logging.basicConfig(level=logging.INFO)

def test_performance_retraining():
    print("🧪 TESTING PERFORMANCE-BASED RETRAINING")
    print("=" * 50)
    
    symbols = ['AAPL', 'TSLA', 'NVDA']
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}")
        
        # Get data
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='3mo')['Close']
        print(f"Data points: {len(data)}")
        
        # Ensure we have a model first
        print("🔄 Creating initial model...")
        forecast, model_used = enhanced_adaptive_manager.adaptive_forecast(symbol, data, 12)
        print(f"Initial forecast: {model_used}")
        
        # Test 1: Check retraining need
        print("🔍 Checking if retraining is needed...")
        needs_retrain = enhanced_adaptive_manager.check_retraining_needed(symbol, 'lstm')
        print(f"Retraining needed: {needs_retrain}")
        
        # Test 2: Force scheduled retraining
        print("🔄 Testing scheduled retraining...")
        scheduled_result = enhanced_adaptive_manager.scheduled_retraining(
            symbol, data, 'lstm', retrain_interval=0  # Force retrain
        )
        
        if scheduled_result:
            print(f"✅ Scheduled retraining triggered!")
            print(f"New version: {scheduled_result}")
            
            # Verify new model exists
            import os
            model_path = f"saved_models/{scheduled_result}.h5"
            if os.path.exists(model_path):
                print(f"✅ New model file created")
            else:
                print(f"❌ New model file not found")
        else:
            print("ℹ️ Scheduled retraining not triggered")
        
        # Test 3: Manual retraining
        print("🔄 Testing manual retraining...")
        manual_result = enhanced_adaptive_manager.retrain_model(symbol, data, 'lstm')
        if manual_result:
            print(f"✅ Manual retraining successful: {manual_result}")
        else:
            print("❌ Manual retraining failed")
    
    print("🎯 RETRAINING TEST COMPLETED")

if __name__ == "__main__":
    test_performance_retraining()