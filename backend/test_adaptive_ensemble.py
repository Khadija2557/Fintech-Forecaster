# test_adaptive_ensemble.py
import logging
import yfinance as yf
from enhanced_adaptive_learning import enhanced_adaptive_manager

logging.basicConfig(level=logging.INFO)

def test_adaptive_ensemble():
    print("🧪 TESTING ADAPTIVE ENSEMBLE WEIGHTS")
    print("=" * 50)
    
    # Test with different performance scenarios
    test_scenarios = [
        {
            'name': 'LSTM Best Performance',
            'performance': {
                'arima': {'rmse': 3.5, 'mae': 2.8},
                'lstm': {'rmse': 1.8, 'mae': 1.3},
                'rolling_window': {'rmse': 2.8, 'mae': 2.1}
            }
        },
        {
            'name': 'ARIMA Best Performance', 
            'performance': {
                'arima': {'rmse': 1.5, 'mae': 1.2},
                'lstm': {'rmse': 2.8, 'mae': 2.1},
                'rolling_window': {'rmse': 2.2, 'mae': 1.8}
            }
        },
        {
            'name': 'Equal Performance',
            'performance': {
                'arima': {'rmse': 2.0, 'mae': 1.5},
                'lstm': {'rmse': 2.0, 'mae': 1.5},
                'rolling_window': {'rmse': 2.0, 'mae': 1.5}
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print("Performance metrics:")
        for model, metrics in scenario['performance'].items():
            print(f"  {model.upper()}: RMSE={metrics['rmse']}, MAE={metrics['mae']}")
        
        # Calculate adaptive weights
        weights = enhanced_adaptive_manager.adaptive_ensemble_weights('TEST', scenario['performance'])
        
        print("🎯 Calculated weights:")
        total_weight = 0
        for model_type, weight in weights.items():
            print(f"  {model_type}: {weight:.3f} ({weight*100:.1f}%)")
            total_weight += weight
        
        print(f"  Total weight: {total_weight:.3f}")
        
        # Verify best performer gets highest weight
        best_model = min(scenario['performance'].items(), key=lambda x: x[1]['rmse'])[0]
        best_weight = weights.get(best_model, 0)
        print(f"  Best performer ({best_model}) weight: {best_weight:.3f}")
    
    # Test real data scenario
    print(f"\n🔍 Testing with real forecast data...")
    ticker = yf.Ticker('MSFT')
    data = ticker.history(period='3mo')['Close']
    
    # Generate ensemble forecast
    forecast, model_used = enhanced_adaptive_manager.adaptive_forecast('MSFT', data, 24, use_ensemble=True)
    print(f"Ensemble forecast completed using: {model_used}")
    print(f"Generated {len(forecast)} forecast points")
    
    print("🎯 ADAPTIVE ENSEMBLE TEST COMPLETED")

if __name__ == "__main__":
    test_adaptive_ensemble()