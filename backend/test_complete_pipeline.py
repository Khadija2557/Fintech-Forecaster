# test_complete_pipeline.py
import logging
import yfinance as yf
import time
from enhanced_adaptive_learning import enhanced_adaptive_manager
from continuous_monitoring import monitoring_system

logging.basicConfig(level=logging.INFO)

def test_complete_pipeline():
    print("🧪 TESTING COMPLETE ADAPTIVE LEARNING PIPELINE")
    print("=" * 50)
    
    test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    
    pipeline_results = {}
    
    for symbol in test_symbols:
        print(f"\n🚀 PROCESSING {symbol}")
        symbol_results = {}
        
        # Step 1: Data Acquisition
        print("  1. 📊 Data acquisition...")
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='4mo')['Close']
        symbol_results['data_points'] = len(data)
        print(f"     Data points: {len(data)}")
        
        # Step 2: Adaptive Forecasting
        print("  2. 🔮 Adaptive forecasting...")
        start_time = time.time()
        forecast, model_used = enhanced_adaptive_manager.adaptive_forecast(symbol, data, 24, use_ensemble=True)
        forecast_time = time.time() - start_time
        
        symbol_results['forecast_model'] = model_used
        symbol_results['forecast_points'] = len(forecast)
        symbol_results['forecast_time'] = forecast_time
        
        print(f"     Model used: {model_used}")
        print(f"     Forecast points: {len(forecast)}")
        print(f"     Time taken: {forecast_time:.2f}s")
        
        # Step 3: Model Version Check
        print("  3. 📁 Model version check...")
        latest_model = enhanced_adaptive_manager.get_latest_model_info(symbol, 'lstm')
        if latest_model:
            symbol_results['latest_model'] = latest_model['version_id']
            print(f"     Latest model: {latest_model['version_id']}")
        else:
            symbol_results['latest_model'] = None
            print("     No model found")
        
        # Step 4: Performance Tracking
        print("  4. 📈 Performance tracking...")
        performance_data = enhanced_adaptive_manager.get_performance_history(symbol, 'lstm', days=7)
        symbol_results['performance_records'] = len(performance_data)
        print(f"     Performance records: {len(performance_data)}")
        
        # Step 5: Monitoring Integration
        print("  5. 🔍 Monitoring integration...")
        if len(data) > 10 and len(forecast) > 5:
            # Simulate some prediction accuracy logging
            recent_actual = data[-5:].values
            recent_forecast = forecast[:5]
            
            monitoring_system.log_prediction_metrics(
                symbol, 'adaptive_ensemble', recent_forecast, recent_actual, 
                "2024-01-01T00:00:00"  # Mock timestamp
            )
            print("     Monitoring data logged")
        
        pipeline_results[symbol] = symbol_results
        time.sleep(1)  # Avoid rate limiting
    
    # Summary Report
    print(f"\n📊 PIPELINE SUMMARY REPORT")
    print("=" * 40)
    
    total_forecasts = sum(r['forecast_points'] for r in pipeline_results.values())
    total_time = sum(r['forecast_time'] for r in pipeline_results.values())
    
    print(f"Symbols processed: {len(pipeline_results)}")
    print(f"Total forecasts generated: {total_forecasts}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average time per symbol: {total_time/len(pipeline_results):.2f}s")
    
    print(f"\n📈 Model Usage Distribution:")
    model_counts = {}
    for results in pipeline_results.values():
        model = results['forecast_model']
        model_counts[model] = model_counts.get(model, 0) + 1
    
    for model, count in model_counts.items():
        print(f"  {model}: {count} symbols")
    
    print(f"\n✅ COMPLETE PIPELINE TEST FINISHED")

if __name__ == "__main__":
    test_complete_pipeline()