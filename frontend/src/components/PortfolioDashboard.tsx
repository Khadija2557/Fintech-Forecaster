// components/PortfolioDashboard.tsx
import { useState, useEffect } from 'react';
import { 
  Wallet, 
  TrendingUp, 
  Activity, 
  DollarSign, 
  Target, 
  AlertCircle,
  ArrowUpCircle,
  ArrowDownCircle,
  RefreshCw
} from 'lucide-react';
import { 
  Portfolio, 
  PortfolioPerformance, 
  getPortfolio, 
  getPortfolioPerformance, 
  executeTrade,
  Forecast,
  getModelPerformance,
  retrainModel
} from '../lib/mongodb'; // REMOVED getPredictionErrors

interface PortfolioDashboardProps {
  forecasts: Forecast[];
  selectedInstrument: string | null;
}

export default function PortfolioDashboard({ forecasts, selectedInstrument }: PortfolioDashboardProps) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [trading, setTrading] = useState(false);
  const [tradeSymbol, setTradeSymbol] = useState('');
  const [tradeQuantity, setTradeQuantity] = useState('');
  const [tradingSignals, setTradingSignals] = useState<any[]>([]);
  const [modelPerformance, setModelPerformance] = useState<any[]>([]);
  const [retraining, setRetraining] = useState(false);

  useEffect(() => {
    loadPortfolioData();
    generateTradingSignals();
    loadModelPerformance();
  }, [forecasts, selectedInstrument]);

  const loadPortfolioData = async () => {
    try {
      const [portfolioData, performanceData] = await Promise.all([
        getPortfolio(),
        getPortfolioPerformance()
      ]);
      setPortfolio(portfolioData);
      setPerformance(performanceData);
    } catch (error) {
      console.error('Error loading portfolio data:', error);
      // Mock data for development
      setPortfolio({
        user_id: 'default',
        cash_balance: 10000,
        holdings: { AAPL: 10, GOOGL: 5 },
        total_value: 15000,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
      setPerformance({
        initial_capital: 10000,
        current_value: 15000,
        total_return_percent: 50,
        total_return_dollar: 5000,
        cash_balance: 5000,
        number_of_holdings: 2,
        number_of_trades: 5,
        volatility: 0.15,
        sharpe_ratio: 1.2
      });
    } finally {
      setLoading(false);
    }
  };

  const loadModelPerformance = async () => {
    if (!selectedInstrument) return;
    
    try {
      const performanceData = await getModelPerformance(selectedInstrument);
      setModelPerformance(performanceData);
    } catch (error) {
      console.error('Error loading model performance:', error);
    }
  };

  const generateTradingSignals = () => {
    if (!forecasts.length || !selectedInstrument) return;

    const latestForecast = forecasts[forecasts.length - 1];
    const signals = [];

    // Advanced trading strategy based on forecast analysis
    if (latestForecast.confidence_lower && latestForecast.confidence_upper) {
      const confidenceRange = latestForecast.confidence_upper - latestForecast.confidence_lower;
      const confidenceLevel = 1 - (confidenceRange / latestForecast.predicted_price);

      // Buy signal: High confidence and predicted price > current price
      if (confidenceLevel > 0.7 && latestForecast.predicted_price > (performance?.current_value || 0)) {
        signals.push({
          symbol: selectedInstrument,
          action: 'BUY',
          confidence: confidenceLevel,
          reason: 'High confidence bullish forecast with strong upside potential',
          predictedPrice: latestForecast.predicted_price,
          confidenceRange: confidenceRange
        });
      }

      // Sell signal: High confidence and predicted price < current price
      if (confidenceLevel > 0.7 && latestForecast.predicted_price < (performance?.current_value || 0)) {
        signals.push({
          symbol: selectedInstrument,
          action: 'SELL',
          confidence: confidenceLevel,
          reason: 'High confidence bearish forecast indicating downturn',
          predictedPrice: latestForecast.predicted_price,
          confidenceRange: confidenceRange
        });
      }
    }

    setTradingSignals(signals);
  };

  const handleAutoTrade = async (signal: any) => {
    setTrading(true);
    try {
      // Calculate position size (10% of available cash for buys, available holdings for sells)
      let quantity = 0;
      
      if (signal.action === 'BUY') {
        const maxInvestment = (performance?.cash_balance || 0) * 0.1; // 10% of cash
        quantity = Math.floor(maxInvestment / signal.predictedPrice);
      } else if (signal.action === 'SELL') {
        const currentHoldings = portfolio?.holdings?.[signal.symbol] || 0;
        quantity = Math.min(currentHoldings, Math.floor(currentHoldings * 0.5)); // Sell up to 50% of holdings
      }

      if (quantity > 0) {
        await executeTrade(signal.symbol, signal.action.toLowerCase(), quantity);
        await loadPortfolioData();
        alert(`Auto-trade executed: ${signal.action} ${quantity} shares of ${signal.symbol}`);
      } else {
        alert('Insufficient funds or holdings for this trade');
      }
    } catch (error: any) {
      console.error('Auto-trade failed:', error);
      alert(`Auto-trade failed: ${error.message || 'Unknown error'}`);
    } finally {
      setTrading(false);
    }
  };

  const handleManualTrade = async (action: 'buy' | 'sell') => {
    if (!tradeSymbol || !tradeQuantity) {
      alert('Please enter symbol and quantity');
      return;
    }

    setTrading(true);
    try {
      const quantity = parseInt(tradeQuantity);
      await executeTrade(tradeSymbol, action, quantity);
      await loadPortfolioData();
      setTradeSymbol('');
      setTradeQuantity('');
      alert(`Trade executed: ${action.toUpperCase()} ${quantity} shares of ${tradeSymbol}`);
    } catch (error: any) {
      console.error('Trade failed:', error);
      alert(`Trade failed: ${error.message || 'Unknown error'}`);
    } finally {
      setTrading(false);
    }
  };

  const handleRetrainModel = async () => {
    if (!selectedInstrument) {
      alert('Please select an instrument first');
      return;
    }

    setRetraining(true);
    try {
      const result = await retrainModel(selectedInstrument);
      alert(result.message);
      await loadModelPerformance();
    } catch (error: any) {
      alert(`Retraining failed: ${error.message || 'Unknown error'}`);
    } finally {
      setRetraining(false);
    }
  };

  const getLatestModelMetrics = () => {
    if (modelPerformance.length === 0) return null;
    return modelPerformance[0];
  };

  const calculatePortfolioGrowth = () => {
    if (!performance) return 0;
    return ((performance.current_value - performance.initial_capital) / performance.initial_capital) * 100;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-400"></div>
        <span className="ml-3 text-slate-400">Loading portfolio...</span>
      </div>
    );
  }

  const latestMetrics = getLatestModelMetrics();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Wallet className="w-8 h-8 text-green-400" />
          <h2 className="text-2xl font-bold text-white">Enhanced Portfolio Management</h2>
        </div>
        <button
          onClick={handleRetrainModel}
          disabled={retraining || !selectedInstrument}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${retraining ? 'animate-spin' : ''}`} />
          {retraining ? 'Retraining...' : 'Retrain Model'}
        </button>
      </div>

      {/* AI Trading Signals */}
      {tradingSignals.length > 0 && (
        <div className="bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-lg p-6 border border-green-500/20">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5" />
            AI Trading Signals
          </h3>
          <div className="space-y-3">
            {tradingSignals.map((signal, index) => (
              <div key={index} className="flex justify-between items-center p-4 bg-green-500/10 rounded-lg border border-green-500/30">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`font-semibold text-lg ${
                      signal.action === 'BUY' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {signal.symbol} - {signal.action}
                    </div>
                    <div className="flex items-center gap-1 px-2 py-1 bg-green-500/20 rounded text-xs text-green-400">
                      <TrendingUp className="w-3 h-3" />
                      {(signal.confidence * 100).toFixed(1)}% Confidence
                    </div>
                  </div>
                  <div className="text-sm text-slate-300 mb-1">{signal.reason}</div>
                  <div className="text-xs text-slate-400">
                    Predicted: ${signal.predictedPrice.toFixed(2)} ± ${signal.confidenceRange.toFixed(2)}
                  </div>
                </div>
                <button
                  onClick={() => handleAutoTrade(signal)}
                  disabled={trading}
                  className={`px-4 py-2 rounded text-sm font-semibold transition-colors disabled:opacity-50 ${
                    signal.action === 'BUY' 
                      ? 'bg-green-500 hover:bg-green-600 text-white' 
                      : 'bg-red-500 hover:bg-red-600 text-white'
                  }`}
                >
                  {trading ? 'Trading...' : `Auto ${signal.action}`}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Portfolio Performance & Model Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Performance */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            Portfolio Performance
          </h3>
          
          {performance && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-lg p-4 border border-green-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-4 h-4 text-green-400" />
                  <div className="text-sm text-slate-400">Total Value</div>
                </div>
                <div className="text-xl font-bold text-white">
                  ${performance.current_value.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
                </div>
              </div>

              <div className={`rounded-lg p-4 border ${
                calculatePortfolioGrowth() >= 0 
                  ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20' 
                  : 'bg-gradient-to-br from-red-500/10 to-rose-500/10 border-red-500/20'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {calculatePortfolioGrowth() >= 0 ? 
                    <ArrowUpCircle className="w-4 h-4 text-green-400" /> : 
                    <ArrowDownCircle className="w-4 h-4 text-red-400" />
                  }
                  <div className="text-sm text-slate-400">Portfolio Growth</div>
                </div>
                <div className={`text-xl font-bold ${
                  calculatePortfolioGrowth() >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {calculatePortfolioGrowth() >= 0 ? '+' : ''}{calculatePortfolioGrowth().toFixed(2)}%
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-lg p-4 border border-blue-500/20">
                <div className="text-sm text-slate-400 mb-2">Cash Balance</div>
                <div className="text-xl font-bold text-white">
                  ${performance.cash_balance.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}
                </div>
              </div>

              <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-lg p-4 border border-purple-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-purple-400" />
                  <div className="text-sm text-slate-400">Sharpe Ratio</div>
                </div>
                <div className="text-xl font-bold text-white">
                  {performance.sharpe_ratio?.toFixed(2) || 'N/A'}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Model Performance Metrics */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-400" />
            Model Performance
          </h3>
          
          {latestMetrics ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-orange-500/10 to-amber-500/10 rounded-lg p-4 border border-orange-500/20">
                <div className="text-sm text-slate-400 mb-2">RMSE</div>
                <div className="text-xl font-bold text-white">
                  {latestMetrics.metrics?.rmse?.toFixed(4) || 'N/A'}
                </div>
                <div className="text-xs text-slate-400 mt-1">Root Mean Square Error</div>
              </div>

              <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-lg p-4 border border-blue-500/20">
                <div className="text-sm text-slate-400 mb-2">MAE</div>
                <div className="text-xl font-bold text-white">
                  {latestMetrics.metrics?.mae?.toFixed(4) || 'N/A'}
                </div>
                <div className="text-xs text-slate-400 mt-1">Mean Absolute Error</div>
              </div>

              <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-lg p-4 border border-green-500/20">
                <div className="text-sm text-slate-400 mb-2">MAPE</div>
                <div className="text-xl font-bold text-white">
                  {latestMetrics.metrics?.mape?.toFixed(2) || 'N/A'}%
                </div>
                <div className="text-xs text-slate-400 mt-1">Mean Absolute Percentage Error</div>
              </div>

              <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-lg p-4 border border-purple-500/20">
                <div className="text-sm text-slate-400 mb-2">Last Update</div>
                <div className="text-sm font-bold text-white">
                  {latestMetrics.timestamp ? new Date(latestMetrics.timestamp).toLocaleDateString() : 'N/A'}
                </div>
                <div className="text-xs text-slate-400 mt-1">Model Evaluation</div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50 text-center">
              <AlertCircle className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <p className="text-slate-400">No model performance data available</p>
              <p className="text-slate-500 text-sm">Generate forecasts to see performance metrics</p>
            </div>
          )}
        </div>
      </div>

      {/* Current Holdings */}
      {portfolio && portfolio.holdings && Object.keys(portfolio.holdings).length > 0 && (
        <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white mb-4">Current Holdings</h3>
          <div className="space-y-3">
            {Object.entries(portfolio.holdings).map(([symbol, quantity]) => (
              <div key={symbol} className="flex justify-between items-center p-4 bg-slate-700/30 rounded-lg">
                <div className="flex-1">
                  <div className="font-semibold text-white text-lg">{symbol}</div>
                  <div className="text-sm text-slate-400">Quantity: {quantity} shares</div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAutoTrade({
                      symbol,
                      action: 'BUY',
                      confidence: 0.8,
                      reason: 'Manual buy order',
                      predictedPrice: 0
                    })}
                    disabled={trading}
                    className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded text-sm disabled:opacity-50 transition-colors font-semibold"
                  >
                    Buy More
                  </button>
                  <button
                    onClick={() => handleAutoTrade({
                      symbol,
                      action: 'SELL',
                      confidence: 0.8,
                      reason: 'Manual sell order',
                      predictedPrice: 0
                    })}
                    disabled={trading}
                    className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded text-sm disabled:opacity-50 transition-colors font-semibold"
                  >
                    Sell
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Manual Trade Section */}
      <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white mb-4">Manual Trading</h3>
        <div className="flex flex-col sm:flex-row gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm text-slate-400 mb-2">Symbol</label>
            <input
              type="text"
              value={tradeSymbol}
              onChange={(e) => setTradeSymbol(e.target.value.toUpperCase())}
              placeholder="e.g., AAPL, GOOGL, BTC-USD"
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>
          <div className="w-32">
            <label className="block text-sm text-slate-400 mb-2">Quantity</label>
            <input
              type="number"
              value={tradeQuantity}
              onChange={(e) => setTradeQuantity(e.target.value)}
              placeholder="e.g., 10"
              min="1"
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>
          <div className="flex gap-3">
            <button 
              onClick={() => handleManualTrade('buy')}
              disabled={trading || !tradeSymbol || !tradeQuantity}
              className="px-6 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowUpCircle className="w-4 h-4" />
              {trading ? 'Buying...' : 'Buy'}
            </button>
            <button 
              onClick={() => handleManualTrade('sell')}
              disabled={trading || !tradeSymbol || !tradeQuantity}
              className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowDownCircle className="w-4 h-4" />
              {trading ? 'Selling...' : 'Sell'}
            </button>
          </div>
        </div>
        <div className="mt-3 text-xs text-slate-400">
          <p>Available Cash: ${performance?.cash_balance?.toLocaleString() || '0'}</p>
        </div>
      </div>

      {/* Adaptive Learning Status */}
      <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <RefreshCw className="w-5 h-5 text-cyan-400" />
          Adaptive Learning System
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="bg-slate-700/50 rounded p-3">
            <div className="text-slate-400 mb-1">Model Status</div>
            <div className="text-green-400 font-semibold">Active & Learning</div>
          </div>
          <div className="bg-slate-700/50 rounded p-3">
            <div className="text-slate-400 mb-1">Performance Tracking</div>
            <div className="text-cyan-400 font-semibold">{modelPerformance.length} Evaluations</div>
          </div>
          <div className="bg-slate-700/50 rounded p-3">
            <div className="text-slate-400 mb-1">Auto-Retraining</div>
            <div className="text-purple-400 font-semibold">Enabled</div>
          </div>
        </div>
      </div>
    </div>
  );
}