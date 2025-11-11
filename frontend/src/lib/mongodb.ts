export interface Instrument {
  id: string;
  symbol: string;
  name: string;
  type: 'stock' | 'crypto' | 'forex';
  exchange: string;
  created_at: string;
}

export interface HistoricalPrice {
  id: string;
  instrument_id: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  created_at: string;
}

export interface ForecastingModel {
  id: string;
  name: string;
  type: 'traditional' | 'neural' | 'ensemble';
  description: string;
  hyperparameters: Record<string, any>;
  performance_metrics: {
    rmse?: number;
    mae?: number;
    mape?: number;
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Forecast {
  id: string;
  instrument_id: string;
  model_id: string;
  forecast_timestamp: string;
  target_timestamp: string;
  horizon_hours: number;
  predicted_price: number;
  confidence_lower: number | null;
  confidence_upper: number | null;
  actual_price: number | null;
  created_at: string;
}

export interface Portfolio {
  user_id: string;
  cash_balance: number;
  holdings: Record<string, number>;
  total_value: number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioTransaction {
  id: string;
  portfolio_id: string;
  symbol: string;
  action: 'buy' | 'sell';
  quantity: number;
  price: number;
  total_amount: number;
  timestamp: string;
  created_at: string;
}

export interface PortfolioPerformance {
  initial_capital: number;
  current_value: number;
  total_return_percent: number;
  total_return_dollar: number;
  cash_balance: number;
  number_of_holdings: number;
  number_of_trades: number;
  volatility?: number;
  sharpe_ratio?: number;
}

// Prediction Error Interface
// Add this interface to mongodb.ts
export interface PredictionError {
  id?: string;
  timestamp: string;
  predicted: number;
  actual: number;
  error: number;
  symbol?: string;
  model_type?: string;
  // Add these fields to match backend response
  matchedIndex?: number;
  isReasonableMatch?: boolean;
  normalizedError?: number;
}

// Performance Metrics Interface
export interface PerformanceMetrics {
  mae: number;
  rmse: number;
  mape: number;
  bias: number;
  std_error: number;
  direction_accuracy: number;
  r_squared: number;
  max_error?: number;
  min_error?: number;
}

// Performance Alert Interface
export interface PerformanceAlert {
  id: string;
  symbol: string;
  model_type: string;
  alert_type: string;
  message: string;
  severity: 'warning' | 'error' | 'info';
  threshold: number;
  actual_value: number;
  timestamp: string;
  is_resolved: boolean;
  created_at: string;
}

// ========== PORTFOLIO API FUNCTIONS ==========

export const createPortfolio = async (initialCapital = 10000): Promise<Portfolio> => {
  const res = await fetch('http://localhost:5000/portfolio/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initial_capital: initialCapital })
  });
  if (!res.ok) throw new Error('Failed to create portfolio');
  return res.json();
};

export const getPortfolio = async (user_id: string = 'default'): Promise<Portfolio> => {
  const res = await fetch(`http://localhost:5000/portfolio/${user_id}`);
  if (!res.ok) throw new Error('Failed to fetch portfolio');
  return res.json();
};

export const executeTrade = async (
  symbol: string, 
  action: 'buy' | 'sell', 
  quantity: number, 
  user_id: string = 'default'
): Promise<any> => {
  const res = await fetch('http://localhost:5000/portfolio/trade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, action, quantity, user_id })
  });
  if (!res.ok) throw new Error('Failed to execute trade');
  return res.json();
};

export const getPortfolioPerformance = async (user_id: string = 'default'): Promise<PortfolioPerformance> => {
  const res = await fetch(`http://localhost:5000/portfolio/performance/${user_id}`);
  if (!res.ok) throw new Error('Failed to fetch portfolio performance');
  return res.json();
};

// ========== FORECASTING API FUNCTIONS ==========

export const fetchInstruments = async (): Promise<Instrument[]> => {
  const res = await fetch('http://localhost:5000/instruments');
  if (!res.ok) throw new Error('Failed to fetch instruments');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export const fetchHistoricalData = async (symbol: string): Promise<HistoricalPrice[]> => {
  const res = await fetch(`http://localhost:5000/historical-data/${symbol}`);
  if (!res.ok) throw new Error('Failed to fetch historical data');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export const fetchModels = async (): Promise<ForecastingModel[]> => {
  const res = await fetch('http://localhost:5000/models');
  if (!res.ok) throw new Error('Failed to fetch models');
  return res.json();
};

export const generateForecast = async (
  symbol: string, 
  horizon: number, 
  model: string
): Promise<Forecast[]> => {
  const res = await fetch('http://localhost:5000/forecast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, horizon, model })
  });
  if (!res.ok) throw new Error('Failed to generate forecast');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

// ========== ADAPTIVE LEARNING API FUNCTIONS ==========

export const retrainModel = async (
  symbol: string, 
  modelType: string = 'ensemble'
): Promise<any> => {
  const res = await fetch('http://localhost:5000/model/retrain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, model_type: modelType })
  });
  if (!res.ok) throw new Error('Failed to retrain model');
  return res.json();
};

export const incrementalModelUpdate = async (
  symbol: string, 
  modelType: string = 'lstm'
): Promise<any> => {
  const res = await fetch('http://localhost:5000/model/incremental-update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, model_type: modelType })
  });
  if (!res.ok) throw new Error('Failed to perform incremental update');
  return res.json();
};

export const getModelVersions = async (symbol: string): Promise<any[]> => {
  const res = await fetch(`http://localhost:5000/model/versions/${symbol}`);
  if (!res.ok) throw new Error('Failed to fetch model versions');
  return res.json();
};

export const adaptiveForecast = async (
  symbol: string, 
  horizon: number = 24
): Promise<any> => {
  const res = await fetch('http://localhost:5000/model/adaptive-forecast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, horizon })
  });
  if (!res.ok) throw new Error('Failed to generate adaptive forecast');
  return res.json();
};

// ========== MONITORING & PERFORMANCE API FUNCTIONS ==========


export const getPredictionErrors = async (symbol: string): Promise<PredictionError[]> => {
  try {
    const res = await fetch(`http://localhost:5000/monitoring/errors/${symbol}`);
    if (!res.ok) {
      console.warn('No prediction errors found or endpoint not available');
      return [];
    }
    const data = await res.json();
    
    // Transform the data to match frontend expectations
    const formattedErrors = Array.isArray(data) ? data.map(error => ({
      timestamp: error.timestamp,
      predicted: error.predicted || error.predicted_price,
      actual: error.actual || error.actual_price,
      error: error.error || (error.actual - error.predicted),
      symbol: error.symbol || symbol,
      model_type: error.model_type
    })) : [];
    
    console.log(`Loaded ${formattedErrors.length} prediction errors for ${symbol}`);
    return formattedErrors;
  } catch (error) {
    console.error('Error fetching prediction errors:', error);
    return [];
  }
};

export const getModelPerformance = async (symbol: string): Promise<any> => {
  const res = await fetch(`http://localhost:5000/monitoring/performance/${symbol}`);
  if (!res.ok) throw new Error('Failed to fetch model performance');
  return res.json();
};

export const getPerformanceAlerts = async (): Promise<PerformanceAlert[]> => {
  const res = await fetch('http://localhost:5000/monitoring/alerts');
  if (!res.ok) throw new Error('Failed to fetch performance alerts');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export const resolveAlert = async (alertId: string): Promise<any> => {
  const res = await fetch(`http://localhost:5000/monitoring/alerts/${alertId}/resolve`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to resolve alert');
  return res.json();
};

export const getMetricsHistory = async (
  symbol: string, 
  modelType?: string
): Promise<any[]> => {
  const url = modelType 
    ? `http://localhost:5000/monitoring/metrics/${symbol}?model_type=${modelType}`
    : `http://localhost:5000/monitoring/metrics/${symbol}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch metrics history');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export const getModelPerformanceHistory = async (symbol: string): Promise<any> => {
  const res = await fetch(`http://localhost:5000/model/performance-history/${symbol}`);
  if (!res.ok) throw new Error('Failed to fetch model performance history');
  return res.json();
};

// ========== HEALTH CHECK ==========



export const healthCheck = async (): Promise<boolean> => {
  try {
    const res = await fetch('http://localhost:5000/health');
    return res.ok;
  } catch (error) {
    return false;
  }
};