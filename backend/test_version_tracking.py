# test_version_tracking.py
import logging
from pymongo import MongoClient
from enhanced_adaptive_learning import enhanced_adaptive_manager
import yfinance as yf

logging.basicConfig(level=logging.INFO)

def test_version_tracking():
    print("🧪 TESTING MODEL VERSION TRACKING")
    print("=" * 50)
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client['stock_forecast_db']
    
    # Check all collections
    collections = db.list_collection_names()
    print("📁 Database collections:")
    for coll in collections:
        count = db[coll].count_documents({})
        print(f"  {coll}: {count} records")
    
    # Test model versions
    print(f"\n🔍 Model Version Analysis")
    versions = list(db.model_versions.find().sort('created_at', -1))
    print(f"Total model versions: {len(versions)}")
    
    if versions:
        # Group by symbol and model type
        from collections import defaultdict
        symbol_stats = defaultdict(lambda: defaultdict(int))
        
        for version in versions:
            symbol = version.get('symbol', 'unknown')
            model_type = version.get('model_type', 'unknown')
            symbol_stats[symbol][model_type] += 1
        
        print("\n📊 Version statistics by symbol:")
        for symbol, types in symbol_stats.items():
            print(f"  {symbol}:")
            for model_type, count in types.items():
                print(f"    {model_type}: {count} versions")
        
        # Show latest versions
        print(f"\n🆕 Latest 5 model versions:")
        for i, version in enumerate(versions[:5]):
            print(f"  {i+1}. {version['version_id']}")
            print(f"     Symbol: {version.get('symbol', 'N/A')}")
            print(f"     Type: {version.get('model_type', 'N/A')}")
            print(f"     Created: {version.get('created_at', 'N/A')}")
            print(f"     Active: {version.get('is_active', 'N/A')}")
    
    # Test performance history
    print(f"\n📈 Performance History Analysis")
    performance_data = list(db.model_performance_history.find().sort('timestamp', -1).limit(10))
    print(f"Latest performance records: {len(performance_data)}")
    
    if performance_data:
        print("Sample performance metrics:")
        for i, perf in enumerate(performance_data[:3]):
            print(f"  Record {i+1}:")
            print(f"    Symbol: {perf.get('symbol', 'N/A')}")
            print(f"    Model: {perf.get('model_type', 'N/A')}")
            metrics = perf.get('metrics', {})
            print(f"    RMSE: {metrics.get('rmse', 'N/A')}")
            print(f"    MAE: {metrics.get('mae', 'N/A')}")
            print(f"    Bias: {metrics.get('bias', 'N/A')}")
    
    # Test getting specific performance history
    print(f"\n🔎 Specific symbol performance:")
    test_symbols = ['AAPL', 'GOOGL', 'MSFT']
    for symbol in test_symbols:
        for model_type in ['lstm', 'arima', 'rolling_window']:
            history = enhanced_adaptive_manager.get_performance_history(symbol, model_type, days=30)
            if history:
                print(f"  {symbol} {model_type}: {len(history)} records")
    
    print("🎯 VERSION TRACKING TEST COMPLETED")

if __name__ == "__main__":
    test_version_tracking()