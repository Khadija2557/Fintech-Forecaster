# test_sliding_context.py
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from enhanced_adaptive_learning import enhanced_adaptive_manager

logging.basicConfig(level=logging.INFO)

def test_sliding_context_transformer():
    print("🧪 TESTING SLIDING CONTEXT TRANSFORMER")
    print("=" * 50)
    
    # Test 1: Real stock data
    print("📊 Test 1: Real stock data")
    ticker = yf.Ticker('AAPL')
    real_data = ticker.history(period='4mo')['Close']
    print(f"Real data points: {len(real_data)}")
    
    context_predictions = enhanced_adaptive_manager.sliding_context_transformer(
        'AAPL', real_data, context_size=30, prediction_steps=10
    )
    
    if context_predictions:
        print(f"✅ Real data test successful!")
        print(f"🔮 Generated {len(context_predictions)} predictions")
        print(f"Predictions: {[f'{x:.2f}' for x in context_predictions]}")
    else:
        print("❌ Real data test failed")
    
    # Test 2: Synthetic trend data
    print("\n📈 Test 2: Synthetic trend data")
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    
    # Create different trend patterns
    trend_patterns = [
        ('Upward Trend', np.arange(100) * 0.5 + np.random.randn(100) * 2),
        ('Downward Trend', -np.arange(100) * 0.3 + np.random.randn(100) * 2),
        ('Volatile', np.cumsum(np.random.randn(100)) + 100)
    ]
    
    for pattern_name, pattern_data in trend_patterns:
        print(f"\n🔧 Testing {pattern_name}")
        series = pd.Series(pattern_data, index=dates)
        
        predictions = enhanced_adaptive_manager.sliding_context_transformer(
            f'TEST_{pattern_name}', series, context_size=20, prediction_steps=5
        )
        
        if predictions:
            print(f"✅ {pattern_name} test successful!")
            print(f"📈 Generated {len(predictions)} predictions")
            if len(predictions) > 0:
                actual_trend = np.mean(np.diff(series.values[-10:]))
                predicted_trend = np.mean(np.diff(predictions))
                print(f"📊 Actual trend: {actual_trend:.3f}, Predicted trend: {predicted_trend:.3f}")
        else:
            print(f"❌ {pattern_name} test failed")
    
    # Test 3: Different context sizes
    print("\n🎛️ Test 3: Different context sizes")
    test_data = yf.Ticker('MSFT').history(period='3mo')['Close']
    
    context_sizes = [20, 40, 60]
    for context_size in context_sizes:
        print(f"\n🔧 Testing context_size={context_size}")
        predictions = enhanced_adaptive_manager.sliding_context_transformer(
            'MSFT', test_data, context_size=context_size, prediction_steps=8
        )
        
        if predictions:
            print(f"✅ Context size {context_size} successful")
            print(f"📈 Predictions: {len(predictions)}")
        else:
            print(f"❌ Context size {context_size} failed")
    
    print("🎯 SLIDING CONTEXT TEST COMPLETED")

if __name__ == "__main__":
    test_sliding_context_transformer()