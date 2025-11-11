# test_rolling_window.py
import logging
import yfinance as yf
from enhanced_adaptive_learning import enhanced_adaptive_manager

logging.basicConfig(level=logging.INFO)

def test_rolling_window_regression():
    print("🧪 TESTING ROLLING WINDOW REGRESSION")
    print("=" * 50)
    
    # Get sufficient data for rolling windows
    ticker = yf.Ticker('GOOGL')
    data = ticker.history(period='6mo')['Close']
    print(f"📊 Data for rolling windows: {len(data)} points")
    
    # Test different window sizes
    window_sizes = [50, 100]
    step_sizes = [5, 10]
    
    for window_size in window_sizes:
        for step_size in step_sizes:
            print(f"\n🔧 Testing window_size={window_size}, step_size={step_size}")
            
            # Test rolling window regression
            rolling_predictions = enhanced_adaptive_manager.rolling_window_regression(
                'GOOGL', data, window_size=window_size, step_size=step_size
            )
            
            if rolling_predictions:
                print(f"✅ Rolling window successful!")
                print(f"📈 Generated {len(rolling_predictions)} predictions")
                print(f"🔮 Latest 3 predictions: {[f'{x:.2f}' for x in rolling_predictions[-3:]]}")
                
                # Check if performance data was stored
                from pymongo import MongoClient
                client = MongoClient('mongodb://localhost:27017/')
                db = client['stock_forecast_db']
                
                performance_count = db.model_performance_history.count_documents({
                    'symbol': 'GOOGL', 
                    'model_type': 'rolling_window'
                })
                print(f"📊 Performance records stored: {performance_count}")
            else:
                print(f"❌ Rolling window failed for this configuration")
    
    print("🎯 ROLLING WINDOW TEST COMPLETED")

if __name__ == "__main__":
    test_rolling_window_regression()