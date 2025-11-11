// components/MonitoringDashboard.tsx
import { useState, useEffect } from 'react';
import { 
  Activity, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  CheckCircle,
  XCircle,
  RefreshCw,
  BarChart3,
  Shield,
  Database,
  LineChart
} from 'lucide-react';
import { 
  getModelPerformance, 
  getPredictionErrors,
  getPerformanceAlerts,
  resolveAlert,
  getMetricsHistory,
  getModelPerformanceHistory,
  PerformanceAlert,
  PredictionError
} from '../lib/mongodb';

interface PerformanceMetrics {
  mae: number;
  rmse: number;
  mape: number;
  bias: number;
  std_error: number;
  direction_accuracy: number;
  r_squared: number;
}

interface ModelPerformanceData {
  recent_metrics?: PerformanceMetrics;
  total_evaluations?: number;
  trend?: 'improving' | 'stable' | 'degrading';
  last_evaluation?: string;
}

export default function MonitoringDashboard() {
  const [performanceData, setPerformanceData] = useState<Record<string, ModelPerformanceData>>({});
  const [predictionErrors, setPredictionErrors] = useState<PredictionError[]>([]);
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('AAPL');
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMonitoringData();
  }, [selectedSymbol, timeRange]);

  // In MonitoringDashboard.tsx - Update the loadMonitoringData function:

  const loadMonitoringData = async () => {
      setLoading(true);
      setError(null);
      try {
        console.log('Loading monitoring data for:', selectedSymbol);
        
        // Use Promise.allSettled to handle individual API failures gracefully
        const [performanceResult, errorsResult, alertResult, metricsResult] = await Promise.allSettled([
          getModelPerformance(selectedSymbol),
          getPredictionErrors(selectedSymbol),
          getPerformanceAlerts(),
          getMetricsHistory(selectedSymbol)
        ]);

        // Handle each result individually
        const performance = performanceResult.status === 'fulfilled' ? performanceResult.value : {};
        const errors = errorsResult.status === 'fulfilled' ? errorsResult.value : [];
        const alertData = alertResult.status === 'fulfilled' ? alertResult.value : [];
        const metrics = metricsResult.status === 'fulfilled' ? metricsResult.value : [];

        setPerformanceData(performance || {});
        setPredictionErrors(errors || []);
        setAlerts(alertData || []);
        setMetricsHistory(metrics || []);
        
        console.log('Monitoring data loaded successfully:', {
          performance: Object.keys(performance).length,
          errors: errors.length,
          alerts: alertData.length,
          metrics: metrics.length
        });

        // If all endpoints failed, show specific error
        if (performanceResult.status === 'rejected' && 
            errorsResult.status === 'rejected' && 
            alertResult.status === 'rejected') {
          setError('Backend services are unavailable. Please ensure the Flask server is running on port 5000.');
        }
        
      } catch (error) {
        console.error('Error loading monitoring data:', error);
        setError('Failed to load monitoring data. Please check if the backend is running on http://localhost:5000');
        
        // Set empty states
        setPerformanceData({});
        setPredictionErrors([]);
        setAlerts([]);
        setMetricsHistory([]);
      } finally {
        setLoading(false);
      }
    };

  const handleResolveAlert = async (alertId: string) => {
    try {
      await resolveAlert(alertId);
      setAlerts(alerts.filter(alert => alert.id !== alertId));
    } catch (error) {
      console.error('Error resolving alert:', error);
      setError('Failed to resolve alert');
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'degrading':
        return <TrendingDown className="w-4 h-4 text-red-400" />;
      default:
        return <BarChart3 className="w-4 h-4 text-blue-400" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'bg-red-500/20 border-red-500/50 text-red-400';
      case 'warning':
        return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400';
      default:
        return 'bg-blue-500/20 border-blue-500/50 text-blue-400';
    }
  };

  // NEW: Calculate comprehensive error statistics
  const calculateErrorStatistics = () => {
    if (predictionErrors.length === 0) return null;
    
    const totalErrors = predictionErrors.length;
    const avgError = predictionErrors.reduce((sum, e) => sum + Math.abs(e.error), 0) / totalErrors;
    const maxError = Math.max(...predictionErrors.map(e => Math.abs(e.error)));
    const stdDev = Math.sqrt(
      predictionErrors.reduce((sum, e) => sum + Math.pow(Math.abs(e.error) - avgError, 2), 0) / totalErrors
    );
    
    return { totalErrors, avgError, maxError, stdDev };
  };

  // NEW: Calculate MAE, RMSE, MAPE from prediction errors
  const calculateModelMetrics = () => {
    if (predictionErrors.length === 0) return null;
    
    const errors = predictionErrors.map(e => Math.abs(e.error));
    const actuals = predictionErrors.map(e => e.actual);
    
    // MAE (Mean Absolute Error)
    const mae = errors.reduce((sum, error) => sum + error, 0) / errors.length;
    
    // RMSE (Root Mean Square Error)
    const rmse = Math.sqrt(
      predictionErrors.reduce((sum, e) => sum + Math.pow(e.error, 2), 0) / predictionErrors.length
    );
    
    // MAPE (Mean Absolute Percentage Error)
    const mape = (predictionErrors.reduce((sum, e) => {
      if (e.actual !== 0) {
        return sum + (Math.abs(e.error) / Math.abs(e.actual));
      }
      return sum;
    }, 0) / predictionErrors.length) * 100;
    
    return { mae, rmse, mape };
  };

  const errorStats = calculateErrorStatistics();
  const modelMetrics = calculateModelMetrics();

  // NEW: Function to render the prediction accuracy chart
  const renderPredictionAccuracyChart = () => {
    if (predictionErrors.length === 0) {
      return (
        <div className="bg-slate-800/30 rounded-lg p-8 border border-slate-700/50 text-center">
          <LineChart className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-400 mb-2">No Prediction Data</h3>
          <p className="text-slate-500">Generate forecasts to see prediction accuracy visualization</p>
        </div>
      );
    }

    const chartData = predictionErrors.slice(-20); // Show last 20 errors for clarity
    const chartHeight = 300;
    const chartWidth = 800;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };

    const innerWidth = chartWidth - padding.left - padding.right;
    const innerHeight = chartHeight - padding.top - padding.bottom;

    // Calculate scales
    const allPrices = [...chartData.flatMap(d => [d.predicted, d.actual])];
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    const priceRange = maxPrice - minPrice;

    const getY = (price: number) => {
      return innerHeight - ((price - minPrice) / priceRange) * innerHeight;
    };

    const getX = (index: number) => {
      return (index / (chartData.length - 1)) * innerWidth;
    };

    return (
      <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <LineChart className="w-5 h-5 text-cyan-400" />
          Prediction Accuracy Visualization
        </h3>
        
        <div className="overflow-x-auto">
          <svg width={chartWidth} height={chartHeight} className="bg-slate-900/50 rounded">
            <defs>
              <linearGradient id="actualLine" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#fbbf24" stopOpacity="1" />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity="1" />
              </linearGradient>
              <linearGradient id="predictedLine" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#ec4899" stopOpacity="1" />
                <stop offset="100%" stopColor="#db2777" stopOpacity="1" />
              </linearGradient>
            </defs>

            <g transform={`translate(${padding.left}, ${padding.top})`}>
              {/* Grid lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                const y = innerHeight * ratio;
                const price = maxPrice - (ratio * priceRange);
                return (
                  <g key={`grid-${i}`}>
                    <line
                      x1={0}
                      y1={y}
                      x2={innerWidth}
                      y2={y}
                      stroke="#334155"
                      strokeWidth="1"
                      strokeDasharray="2,2"
                    />
                    <text
                      x={-5}
                      y={y + 4}
                      textAnchor="end"
                      className="text-xs fill-slate-400"
                      fontSize="10"
                    >
                      ${price.toFixed(2)}
                    </text>
                  </g>
                );
              })}

              {/* Actual prices line (YELLOW) */}
              <path
                d={`M ${chartData.map((point, i) => 
                  `${getX(i)} ${getY(point.actual)}`
                ).join(' L ')}`}
                stroke="url(#actualLine)"
                strokeWidth="3"
                fill="none"
                strokeLinecap="round"
              />

              {/* Predicted prices line (PINK) */}
              <path
                d={`M ${chartData.map((point, i) => 
                  `${getX(i)} ${getY(point.predicted)}`
                ).join(' L ')}`}
                stroke="url(#predictedLine)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="4,4"
                strokeLinecap="round"
              />

              {/* Error lines */}
              {chartData.map((point, i) => {
                const x = getX(i);
                const actualY = getY(point.actual);
                const predictedY = getY(point.predicted);
                
                return (
                  <g key={`error-${i}`}>
                    <line
                      x1={x}
                      y1={actualY}
                      x2={x}
                      y2={predictedY}
                      stroke="#ef4444"
                      strokeWidth="2"
                      opacity="0.6"
                    />
                    <circle
                      cx={x}
                      cy={actualY}
                      r="4"
                      fill="#fbbf24"
                    />
                    <circle
                      cx={x}
                      cy={predictedY}
                      r="3"
                      fill="#ec4899"
                    />
                  </g>
                );
              })}

              {/* X-axis labels */}
              {chartData.filter((_, i) => i % 5 === 0).map((point, i) => {
                const x = getX(i * 5);
                return (
                  <text
                    key={`label-${i}`}
                    x={x}
                    y={innerHeight + 20}
                    textAnchor="middle"
                    className="text-xs fill-slate-400"
                    fontSize="10"
                  >
                    {new Date(point.timestamp).toLocaleTimeString()}
                  </text>
                );
              })}
            </g>

            {/* Legend */}
            <g transform={`translate(${padding.left + innerWidth - 200}, ${padding.top + 10})`}>
              <rect x={0} y={0} width={190} height={60} fill="#1f2937" opacity="0.9" rx="4" />
              
              <line x1={10} y1={15} x2={30} y2={15} stroke="#fbbf24" strokeWidth="3" />
              <text x={35} y={18} className="text-xs fill-slate-300" fontSize="10">Actual Prices</text>
              
              <line x1={10} y1={35} x2={30} y2={35} stroke="#ec4899" strokeWidth="2" strokeDasharray="4,4" />
              <text x={35} y={38} className="text-xs fill-slate-300" fontSize="10">Predicted Prices</text>
              
              <line x1={10} y1={55} x2={30} y2={55} stroke="#ef4444" strokeWidth="2" />
              <text x={35} y={58} className="text-xs fill-slate-300" fontSize="10">Prediction Errors</text>
            </g>
          </svg>
        </div>

        {/* Error Statistics */}
        {errorStats && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-red-500/10 rounded-lg p-3 border border-red-500/20">
              <div className="text-sm text-red-400 font-semibold">Total Errors</div>
              <div className="text-lg text-white font-bold">{errorStats.totalErrors}</div>
            </div>
            <div className="bg-orange-500/10 rounded-lg p-3 border border-orange-500/20">
              <div className="text-sm text-orange-400 font-semibold">Avg Error</div>
              <div className="text-lg text-white font-bold">${errorStats.avgError.toFixed(2)}</div>
            </div>
            <div className="bg-yellow-500/10 rounded-lg p-3 border border-yellow-500/20">
              <div className="text-sm text-yellow-400 font-semibold">Max Error</div>
              <div className="text-lg text-white font-bold">${errorStats.maxError.toFixed(2)}</div>
            </div>
            <div className="bg-purple-500/10 rounded-lg p-3 border border-purple-500/20">
              <div className="text-sm text-purple-400 font-semibold">Std Dev</div>
              <div className="text-lg text-white font-bold">${errorStats.stdDev.toFixed(2)}</div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // NEW: Function to render model metrics cards
  const renderModelMetrics = () => {
    if (!modelMetrics) return null;

    return (
      <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-green-400" />
          Model Performance Metrics
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-lg p-4 border border-blue-500/20">
            <div className="text-sm text-slate-400 mb-2">MAE (Mean Absolute Error)</div>
            <div className="text-2xl font-bold text-white">{modelMetrics.mae.toFixed(4)}</div>
            <div className="text-xs text-slate-400 mt-1">Lower is better</div>
          </div>

          <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-lg p-4 border border-purple-500/20">
            <div className="text-sm text-slate-400 mb-2">RMSE (Root Mean Square Error)</div>
            <div className="text-2xl font-bold text-white">{modelMetrics.rmse.toFixed(4)}</div>
            <div className="text-xs text-slate-400 mt-1">Lower is better</div>
          </div>

          <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-lg p-4 border border-green-500/20">
            <div className="text-sm text-slate-400 mb-2">MAPE (Mean Absolute % Error)</div>
            <div className="text-2xl font-bold text-white">{modelMetrics.mape.toFixed(2)}%</div>
            <div className="text-xs text-slate-400 mt-1">Lower is better</div>
          </div>
        </div>

        <div className="mt-4 text-sm text-slate-400">
          <p>Based on {predictionErrors.length} prediction samples</p>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-400"></div>
        <span className="ml-3 text-slate-400">Loading monitoring data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity className="w-8 h-8 text-cyan-400" />
          <h2 className="text-2xl font-bold text-white">Continuous Monitoring Dashboard</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <label htmlFor="symbol-select" className="text-sm text-slate-400 mb-1">
              Instrument
            </label>
            <select
              id="symbol-select"
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
            >
              <option value="AAPL">AAPL</option>
              <option value="GOOGL">GOOGL</option>
              <option value="MSFT">MSFT</option>
              <option value="TSLA">TSLA</option>
              <option value="BTC-USD">BTC-USD</option>
              <option value="ETH-USD">ETH-USD</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label htmlFor="time-range-select" className="text-sm text-slate-400 mb-1">
              Time Range
            </label>
            <select
              id="time-range-select"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
          <button
            onClick={loadMonitoringData}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-white transition-colors mt-6"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* NEW: Prediction Accuracy Chart */}
      {renderPredictionAccuracyChart()}

      {/* NEW: Model Metrics */}
      {renderModelMetrics()}

      {/* Performance Alerts */}
      {alerts.filter(alert => !alert.is_resolved).length > 0 && (
        <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            Active Performance Alerts ({alerts.filter(alert => !alert.is_resolved).length})
          </h3>
          <div className="space-y-3">
            {alerts
              .filter(alert => !alert.is_resolved)
              .map(alert => (
              <div key={alert.id} className={`p-4 rounded-lg border ${getSeverityColor(alert.severity)}`}>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="font-semibold">{alert.symbol}</div>
                      <div className="text-sm opacity-75 capitalize">{alert.model_type}</div>
                      <div className="text-sm px-2 py-1 bg-slate-700/50 rounded capitalize">
                        {alert.alert_type.replace('_', ' ')}
                      </div>
                      <div className={`text-xs px-2 py-1 rounded ${
                        alert.severity === 'error' ? 'bg-red-500/20 text-red-400' :
                        alert.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {alert.severity}
                      </div>
                    </div>
                    <div className="text-sm mb-2">{alert.message}</div>
                    <div className="text-xs opacity-75">
                      Threshold: {alert.threshold} | Actual: {alert.actual_value.toFixed(2)} | 
                      Date: {new Date(alert.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={() => handleResolveAlert(alert.id)}
                    className="flex items-center gap-1 px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-sm text-white transition-colors"
                  >
                    <CheckCircle className="w-3 h-3" />
                    Resolve
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Data Message */}
      {predictionErrors.length === 0 && alerts.length === 0 && Object.keys(performanceData).length === 0 && (
        <div className="bg-slate-800/50 rounded-lg p-12 border border-slate-700/50 text-center">
          <Database className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-400 mb-2">No Monitoring Data Available</h3>
          <p className="text-slate-500 mb-4">Generate forecasts and wait for the monitoring system to collect data</p>
          <button
            onClick={loadMonitoringData}
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-white transition-colors"
          >
            Check Again
          </button>
        </div>
      )}
    </div>
  );
}