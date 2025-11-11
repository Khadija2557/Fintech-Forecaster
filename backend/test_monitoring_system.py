# test_monitoring_system.py
import logging
import numpy as np
from continuous_monitoring import monitoring_system
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)

def test_monitoring_system():
    print("🧪 TESTING MONITORING SYSTEM")
    print("=" * 50)
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client['stock_forecast_db']
    
    # Test 1: Comprehensive Metrics Calculation
    print("1. 📊 Testing metrics calculation...")
    
    test_cases = [
        {
            'name': 'Perfect Prediction',
            'predictions': [100, 102, 105, 103, 107],
            'actuals': [100, 102, 105, 103, 107]
        },
        {
            'name': 'Small Errors', 
            'predictions': [100, 102, 105, 103, 107],
            'actuals': [101, 101, 106, 104, 108]
        },
        {
            'name': 'Large Errors',
            'predictions': [100, 102, 105, 103, 107],
            'actuals': [95, 108, 98, 110, 102]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔧 {test_case['name']}")
        metrics = monitoring_system.calculate_comprehensive_metrics(
            test_case['predictions'], test_case['actuals']
        )
        
        print("   Metrics:")
        for metric, value in metrics.items():
            if value is not None:
                print(f"     {metric}: {value:.4f}")
    
    # Test 2: Performance Alerts
    print(f"\n2. 🚨 Testing alert system...")
    
    alert_scenarios = [
        {
            'symbol': 'TEST_HIGH_ERROR',
            'model_type': 'lstm',
            'metrics': {'rmse': 15.5, 'mape': 18.2, 'bias': 6.8}
        },
        {
            'symbol': 'TEST_MODERATE_ERROR', 
            'model_type': 'arima',
            'metrics': {'rmse': 8.2, 'mape': 12.5, 'bias': 2.1}
        },
        {
            'symbol': 'TEST_LOW_ERROR',
            'model_type': 'ensemble',
            'metrics': {'rmse': 2.1, 'mape': 3.8, 'bias': 0.5}
        }
    ]
    
    for scenario in alert_scenarios:
        print(f"\n🔍 Testing {scenario['symbol']}...")
        monitoring_system.check_performance_alerts(
            scenario['symbol'], scenario['model_type'], scenario['metrics']
        )
    
    # Test 3: Alert Management
    print(f"\n3. 📋 Testing alert management...")
    
    # Get active alerts
    active_alerts = monitoring_system.get_active_alerts()
    print(f"Active alerts: {len(active_alerts)}")
    
    if active_alerts:
        print("Sample alerts:")
        for i, alert in enumerate(active_alerts[:3]):
            print(f"  {i+1}. {alert['symbol']} - {alert['alert_type']}")
            print(f"     Message: {alert['message']}")
            print(f"     Severity: {alert['severity']}")
            
            # Test resolving alerts
            if i == 0:  # Resolve first alert
                success = monitoring_system.resolve_alert(alert['id'])
                print(f"     Resolved: {success}")
    
    # Test 4: Metrics History
    print(f"\n4. 📈 Testing metrics history...")
    
    test_symbols = ['AAPL', 'GOOGL']
    for symbol in test_symbols:
        metrics_history = monitoring_system.get_metrics_history(symbol, days=7)
        print(f"{symbol} metrics history: {len(metrics_history)} records")
    
    # Test 5: Performance Summary
    print(f"\n5. 📊 Testing performance summary...")
    
    for symbol in test_symbols:
        performance_summary = monitoring_system.get_performance_summary(symbol, days=30)
        if performance_summary:
            print(f"{symbol} performance summary:")
            for model_type, data in performance_summary.items():
                print(f"  {model_type}: {data.get('total_evaluations', 0)} evaluations")
                print(f"    Trend: {data.get('trend', 'unknown')}")
    
    print("🎯 MONITORING SYSTEM TEST COMPLETED")

if __name__ == "__main__":
    test_monitoring_system()