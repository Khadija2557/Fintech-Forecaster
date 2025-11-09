# adaptive_learning.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from db import db

logger = logging.getLogger(__name__)

class AdaptiveLearningManager:
    def __init__(self):
        self.model_versions_coll = db['model_versions']
        self.performance_history_coll = db['model_performance_history']
    
    def store_model_version(self, model_type, model_params, performance_metrics, training_data_info):
        """Store a new version of a model"""
        version_data = {
            'model_type': model_type,
            'model_params': model_params,
            'performance_metrics': performance_metrics,
            'training_data_range': training_data_info,
            'created_at': datetime.now().isoformat(),
            'version_id': f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        self.model_versions_coll.insert_one(version_data)
        return version_data['version_id']
    
    def get_latest_model_info(self, model_type):
        """Get the latest model version info"""
        latest_model = self.model_versions_coll.find_one(
            {'model_type': model_type},
            sort=[('created_at', -1)]
        )
        return latest_model
    
    def log_prediction_accuracy(self, symbol, model_type, predictions, actuals, timestamp):
        """Log prediction accuracy for continuous evaluation"""
        if len(predictions) != len(actuals):
            logger.warning("Predictions and actuals length mismatch")
            return
        
        # Calculate metrics
        errors = np.array(actuals) - np.array(predictions)
        mae = np.mean(np.abs(errors))
        rmse = np.sqrt(np.mean(errors**2))
        mape = np.mean(np.abs(errors / np.array(actuals))) * 100
        
        performance_data = {
            'symbol': symbol,
            'model_type': model_type,
            'timestamp': timestamp,
            'metrics': {
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape)
            },
            'predictions': [float(p) for p in predictions],
            'actuals': [float(a) for a in actuals],
            'created_at': datetime.now().isoformat()
        }
        
        self.performance_history_coll.insert_one(performance_data)
        return performance_data['metrics']
    
    def should_retrain_model(self, model_type, symbol, lookback_days=30):
        """Determine if a model should be retrained based on recent performance"""
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        recent_performance = list(self.performance_history_coll.find({
            'model_type': model_type,
            'symbol': symbol,
            'timestamp': {'$gte': cutoff_date.isoformat()}
        }).sort('timestamp', 1))
        
        if len(recent_performance) < 10:  # Not enough data
            return False
        
        # Check if error metrics are trending upward
        recent_errors = [p['metrics']['rmse'] for p in recent_performance[-10:]]
        if len(recent_errors) < 2:
            return False
        
        # Simple trend detection
        error_trend = np.polyfit(range(len(recent_errors)), recent_errors, 1)[0]
        return error_trend > 0.1  # Retrain if errors are increasing

# Global instance
adaptive_manager = AdaptiveLearningManager()