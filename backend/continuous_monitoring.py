# continuous_monitoring.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from db import db
import asyncio
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class ContinuousMonitoringSystem:
    def __init__(self):
        self.metrics_coll = db['prediction_metrics']
        self.performance_alerts_coll = db['performance_alerts']
        self.setup_collections()
    
    def setup_collections(self):
        """Ensure collections have proper indexes"""
        try:
            # Create indexes for efficient querying
            self.metrics_coll.create_index([("symbol", 1), ("timestamp", -1)])
            self.metrics_coll.create_index([("model_type", 1), ("timestamp", -1)])
            self.metrics_coll.create_index([("timestamp", 1)])
            
            self.performance_alerts_coll.create_index([("symbol", 1), ("created_at", -1)])
            self.performance_alerts_coll.create_index([("is_resolved", 1)])
            
            logger.info("Continuous monitoring collections setup completed")
        except Exception as e:
            logger.error(f"Error setting up monitoring collections: {str(e)}")

    def calculate_comprehensive_metrics(self, predictions: List[float], actuals: List[float]) -> Dict:
        """Calculate comprehensive error metrics"""
        try:
            if len(predictions) != len(actuals) or len(predictions) == 0:
                return {}
            
            predictions = np.array(predictions, dtype=float)
            actuals = np.array(actuals, dtype=float)
            
            # Remove any NaN values
            mask = ~(np.isnan(predictions) | np.isnan(actuals))
            predictions = predictions[mask]
            actuals = actuals[mask]
            
            if len(predictions) == 0:
                return {}
            
            errors = actuals - predictions
            absolute_errors = np.abs(errors)
            percentage_errors = np.abs(errors / actuals) * 100
            
            # Basic metrics
            metrics = {
                'mae': float(np.mean(absolute_errors)),
                'rmse': float(np.sqrt(np.mean(errors ** 2))),
                'mape': float(np.mean(percentage_errors)),
                'bias': float(np.mean(errors)),  # Systematic bias
                'std_error': float(np.std(errors)),
                'max_error': float(np.max(absolute_errors)),
                'min_error': float(np.min(absolute_errors)),
                'error_range': float(np.max(absolute_errors) - np.min(absolute_errors))
            }
            
            # Additional statistical metrics
            metrics.update({
                'median_absolute_error': float(np.median(absolute_errors)),
                'r_squared': self.calculate_r_squared(actuals, predictions),
                'direction_accuracy': self.calculate_direction_accuracy(actuals, predictions),
                'theils_u': self.calculate_theils_u(actuals, predictions)
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}

    def calculate_r_squared(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate R-squared metric"""
        try:
            ss_res = np.sum((actuals - predictions) ** 2)
            ss_tot = np.sum((actuals - np.mean(actuals)) ** 2)
            return float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0.0
        except:
            return 0.0

    def calculate_direction_accuracy(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate direction prediction accuracy"""
        try:
            if len(actuals) < 2:
                return 0.0
            
            actual_directions = np.sign(np.diff(actuals))
            predicted_directions = np.sign(np.diff(predictions))
            
            # Remove points where direction is neutral (0)
            mask = (actual_directions != 0) & (predicted_directions != 0)
            if np.sum(mask) == 0:
                return 0.0
            
            correct_directions = np.sum(actual_directions[mask] == predicted_directions[mask])
            return float(correct_directions / np.sum(mask))
        except:
            return 0.0

    def calculate_theils_u(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate Theil's U statistic"""
        try:
            if len(actuals) < 2:
                return 1.0  # Worst possible value
            
            actual_changes = np.diff(actuals)
            predicted_changes = np.diff(predictions)
            
            mse_forecast = np.mean((actual_changes - predicted_changes) ** 2)
            mse_naive = np.mean(actual_changes ** 2)
            
            return float(np.sqrt(mse_forecast / mse_naive)) if mse_naive != 0 else 1.0
        except:
            return 1.0

    def log_prediction_metrics(self, symbol: str, model_type: str, 
                             predictions: List[float], actuals: List[float],
                             forecast_timestamp: str) -> bool:
        """Log comprehensive prediction metrics for continuous evaluation"""
        try:
            metrics = self.calculate_comprehensive_metrics(predictions, actuals)
            
            if not metrics:
                return False
            
            metric_record = {
                'symbol': symbol,
                'model_type': model_type,
                'timestamp': datetime.now().isoformat(),
                'forecast_timestamp': forecast_timestamp,
                'metrics': metrics,
                'sample_size': len(predictions),
                'predictions': [float(p) for p in predictions],
                'actuals': [float(a) for a in actuals],
                'created_at': datetime.now().isoformat()
            }
            
            # Store in database
            self.metrics_coll.insert_one(metric_record)
            
            # Check for performance alerts
            self.check_performance_alerts(symbol, model_type, metrics)
            
            logger.info(f"Metrics logged for {symbol} ({model_type}): MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging prediction metrics: {str(e)}")
            return False

    def check_performance_alerts(self, symbol: str, model_type: str, metrics: Dict):
        """Check if performance metrics trigger any alerts"""
        try:
            alerts = []
            
            # RMSE alert threshold
            if metrics['rmse'] > 10.0:  # Adjust threshold as needed
                alerts.append({
                    'type': 'high_rmse',
                    'message': f'High RMSE ({metrics["rmse"]:.2f}) detected for {symbol}',
                    'severity': 'warning',
                    'threshold': 10.0,
                    'actual_value': metrics['rmse']
                })
            
            # MAPE alert threshold
            if metrics['mape'] > 15.0:  # 15% error threshold
                alerts.append({
                    'type': 'high_mape',
                    'message': f'High MAPE ({metrics["mape"]:.1f}%) detected for {symbol}',
                    'severity': 'warning',
                    'threshold': 15.0,
                    'actual_value': metrics['mape']
                })
            
            # Bias alert
            if abs(metrics['bias']) > 5.0:  # Significant systematic bias
                alerts.append({
                    'type': 'high_bias',
                    'message': f'Significant bias ({metrics["bias"]:.2f}) detected for {symbol}',
                    'severity': 'warning',
                    'threshold': 5.0,
                    'actual_value': metrics['bias']
                })
            
            # Store alerts
            for alert in alerts:
                alert_record = {
                    'symbol': symbol,
                    'model_type': model_type,
                    'alert_type': alert['type'],
                    'message': alert['message'],
                    'severity': alert['severity'],
                    'threshold': alert['threshold'],
                    'actual_value': alert['actual_value'],
                    'timestamp': datetime.now().isoformat(),
                    'is_resolved': False,
                    'created_at': datetime.now().isoformat()
                }
                self.performance_alerts_coll.insert_one(alert_record)
                logger.warning(f"Performance alert: {alert['message']}")
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {str(e)}")

    def get_metrics_history(self, symbol: str, model_type: str = None, 
                          days: int = 30) -> List[Dict]:
        """Get metrics history for a symbol and optional model type"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = {
                'symbol': symbol,
                'timestamp': {'$gte': cutoff_date.isoformat()}
            }
            
            if model_type:
                query['model_type'] = model_type
            
            metrics = list(self.metrics_coll.find(
                query, 
                {'_id': 0}
            ).sort('timestamp', 1))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics history: {str(e)}")
            return []

    def get_performance_summary(self, symbol: str, days: int = 30) -> Dict:
        """Get performance summary across all models for a symbol"""
        try:
            metrics_history = self.get_metrics_history(symbol, days=days)
            
            if not metrics_history:
                return {}
            
            # Group by model type
            model_metrics = {}
            for metric in metrics_history:
                model_type = metric['model_type']
                if model_type not in model_metrics:
                    model_metrics[model_type] = []
                model_metrics[model_type].append(metric)
            
            # Calculate summary statistics
            summary = {}
            for model_type, metrics_list in model_metrics.items():
                recent_metrics = metrics_list[-1]['metrics'] if metrics_list else {}
                summary[model_type] = {
                    'recent_metrics': recent_metrics,
                    'total_evaluations': len(metrics_list),
                    'last_evaluation': metrics_list[-1]['timestamp'] if metrics_list else None,
                    'trend': self.calculate_performance_trend(metrics_list)
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}

    def calculate_performance_trend(self, metrics_list: List[Dict]) -> str:
        """Calculate performance trend (improving/stable/degrading)"""
        try:
            if len(metrics_list) < 5:
                return "insufficient_data"
            
            # Use last 10 evaluations for trend analysis
            recent_metrics = metrics_list[-10:]
            rmse_values = [m['metrics']['rmse'] for m in recent_metrics]
            
            # Calculate trend using linear regression
            x = np.arange(len(rmse_values))
            slope = np.polyfit(x, rmse_values, 1)[0]
            
            if slope < -0.01:  # RMSE decreasing
                return "improving"
            elif slope > 0.01:  # RMSE increasing
                return "degrading"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"Error calculating performance trend: {str(e)}")
            return "unknown"

    def get_active_alerts(self, symbol: str = None, severity: str = None) -> List[Dict]:
        """Get active performance alerts"""
        try:
            query = {'is_resolved': False}
            if symbol:
                query['symbol'] = symbol
            if severity:
                query['severity'] = severity
            
            alerts = list(self.performance_alerts_coll.find(
                query, 
                {'_id': 0}
            ).sort('timestamp', -1))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {str(e)}")
            return []

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        try:
            result = self.performance_alerts_coll.update_one(
                {'_id': alert_id},
                {'$set': {'is_resolved': True, 'resolved_at': datetime.now().isoformat()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            return False

# Global instance
monitoring_system = ContinuousMonitoringSystem()