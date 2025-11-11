import requests
import json
import time

def test_adaptive_system():
    print("🧪 Testing Adaptive Learning System...")
    
    # Test 1: Generate forecast using adaptive system
    print("1. Testing adaptive forecast...")
    try:
        response = requests.post(
            "http://localhost:5000/forecast",
            json={
                "symbol": "AAPL",
                "horizon": 24,
                "model_id": "ensemble"
            }
        )
        if response.status_code == 200:
            forecasts = response.json()
            print(f"✅ Forecast generated: {len(forecasts)} points")
        else:
            print(f"❌ Forecast failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Forecast error: {e}")
    
    # Test 2: Check if models are being saved
    print("2. Checking saved models...")
    import os
    if os.path.exists('saved_models'):
        models = [f for f in os.listdir('saved_models') if f.endswith('.h5')]
        print(f"✅ Saved models: {len(models)} .h5 files")
        for model in models[:3]:  # Show first 3
            print(f"   - {model}")
    else:
        print("❌ saved_models directory not found")
    
    # Test 3: Check database records
    print("3. Checking database records...")
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017/')
    db = client['stock_forecast_db']
    
    versions = db.model_versions.count_documents({})
    performance = db.model_performance_history.count_documents({})
    
    print(f"✅ Model versions: {versions}")
    print(f"✅ Performance records: {performance}")

if __name__ == "__main__":
    test_adaptive_system()