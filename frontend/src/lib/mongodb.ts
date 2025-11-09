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


// Add to your existing mongodb.ts
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

// Add API functions to mongodb.ts
export const createPortfolio = async (initialCapital = 10000): Promise<Portfolio> => {
  const res = await fetch('http://localhost:5000/portfolio/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initial_capital: initialCapital })
  });
  return res.json();
};

export const getPortfolio = async (): Promise<Portfolio> => {
  const res = await fetch('http://localhost:5000/portfolio/default');
  return res.json();
};

export const executeTrade = async (symbol: string, action: 'buy' | 'sell', quantity: number): Promise<any> => {
  const res = await fetch('http://localhost:5000/portfolio/trade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, action, quantity })
  });
  return res.json();
};

export const getPortfolioPerformance = async (): Promise<PortfolioPerformance> => {
  const res = await fetch('http://localhost:5000/portfolio/performance/default');
  return res.json();
};

export const fetchInstruments = async (): Promise<Instrument[]> => {
  const res = await fetch('http://localhost:5000/instruments');
  return res.json();
};



export const fetchHistoricalData = async (symbol: string): Promise<HistoricalPrice[]> => {
  const res = await fetch(`http://localhost:5000/historical-data/${symbol}`);
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

export const fetchModels = async (): Promise<ForecastingModel[]> => {
  const res = await fetch('http://localhost:5000/models');
  return res.json();
};

export const generateForecast = async (symbol: string, horizon: number, model: string): Promise<Forecast[]> => {
  const res = await fetch('http://localhost:5000/forecast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, horizon, model })
  });
  if (!res.ok) throw new Error('Failed to generate forecast');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
};

// Add to your existing mongodb.ts

// New API functions for enhanced features
export const getPredictionErrors = async (symbol: string): Promise<any[]> => {
  const res = await fetch(`http://localhost:5000/prediction/errors/${symbol}`);
  return res.json();
};

export const getModelPerformance = async (symbol: string): Promise<any[]> => {
  const res = await fetch(`http://localhost:5000/model/performance/${symbol}`);
  return res.json();
};

export const retrainModel = async (symbol: string, modelType: string = 'arima'): Promise<any> => {
  const res = await fetch('http://localhost:5000/model/retrain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, model_type: modelType })
  });
  return res.json();
};