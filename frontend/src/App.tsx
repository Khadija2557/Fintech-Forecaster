import { useEffect, useState } from 'react';
import { TrendingUp, Sparkles, BarChart3, Wallet } from 'lucide-react';
import { 
  Instrument, 
  HistoricalPrice, 
  ForecastingModel, 
  Forecast, 
  fetchInstruments, 
  fetchHistoricalData, 
  fetchModels, 
  generateForecast
} from './lib/mongodb';
import InstrumentSelector from './components/InstrumentSelector';
import ForecastHorizonSelector from './components/ForecastHorizonSelector';
import ModelPerformance from './components/ModelPerformance';
import EnhancedCandlestickChart from './components/EnhancedCandlestickChart';
import PortfolioDashboard from './components/PortfolioDashboard';

function App() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [models, setModels] = useState<ForecastingModel[]>([]);
  const [selectedInstrument, setSelectedInstrument] = useState<Instrument | null>(null);
  const [selectedHorizon, setSelectedHorizon] = useState<number>(24);
  const [selectedModel, setSelectedModel] = useState<ForecastingModel | null>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalPrice[]>([]);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [activeTab, setActiveTab] = useState<'forecasting' | 'portfolio'>('forecasting');
  const [loading, setLoading] = useState(true);
  const [generatingForecast, setGeneratingForecast] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedInstrument) {
      loadHistoricalData();
    }
  }, [selectedInstrument]);

  const loadInitialData = async () => {
    try {
      const [instrumentsData, modelsData] = await Promise.all([
        fetchInstruments(), 
        fetchModels()
      ]);
      setInstruments(instrumentsData);
      if (instrumentsData.length > 0) setSelectedInstrument(instrumentsData[0]);
      setModels(modelsData);
      if (modelsData.length > 0) setSelectedModel(modelsData[0]);
    } catch (error) {
      console.error('Error loading initial data:', error);
      // Set mock data if API fails
      setInstruments([
        { id: '1', symbol: 'AAPL', name: 'Apple Inc.', type: 'stock', exchange: 'NASDAQ', created_at: new Date().toISOString() },
        { id: '2', symbol: 'GOOGL', name: 'Alphabet Inc.', type: 'stock', exchange: 'NASDAQ', created_at: new Date().toISOString() },
        { id: '3', symbol: 'MSFT', name: 'Microsoft Corporation', type: 'stock', exchange: 'NASDAQ', created_at: new Date().toISOString() },
        { id: '4', symbol: 'TSLA', name: 'Tesla Inc.', type: 'stock', exchange: 'NASDAQ', created_at: new Date().toISOString() },
        { id: '5', symbol: 'BTC-USD', name: 'Bitcoin USD', type: 'crypto', exchange: 'CRYPTO', created_at: new Date().toISOString() },
        { id: '6', symbol: 'ETH-USD', name: 'Ethereum USD', type: 'crypto', exchange: 'CRYPTO', created_at: new Date().toISOString() },
        { id: '7', symbol: 'EURUSD=X', name: 'Euro/US Dollar', type: 'forex', exchange: 'FOREX', created_at: new Date().toISOString() }
      ]);
      setModels([
        { 
          id: '1', 
          name: 'ARIMA', 
          type: 'traditional', 
          description: 'AutoRegressive Integrated Moving Average',
          hyperparameters: {},
          performance_metrics: { rmse: 2.5, mae: 1.8, mape: 1.2 },
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        { 
          id: '2', 
          name: 'LSTM', 
          type: 'neural', 
          description: 'Long Short-Term Memory Neural Network',
          hyperparameters: {},
          performance_metrics: { rmse: 1.8, mae: 1.3, mape: 0.9 },
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ]);
      setSelectedInstrument({
        id: '1', symbol: 'AAPL', name: 'Apple Inc.', type: 'stock', exchange: 'NASDAQ', created_at: new Date().toISOString()
      });
      setSelectedModel({
        id: '1', 
        name: 'ARIMA', 
        type: 'traditional', 
        description: 'AutoRegressive Integrated Moving Average',
        hyperparameters: {},
        performance_metrics: { rmse: 2.5, mae: 1.8, mape: 1.2 },
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  const loadHistoricalData = async () => {
    if (!selectedInstrument) return;
    try {
      const data = await fetchHistoricalData(selectedInstrument.symbol);
      setHistoricalData(data);
    } catch (error) {
      console.error('Error loading historical data:', error);
      // Set mock historical data if API fails
      const mockData: HistoricalPrice[] = Array.from({ length: 50 }, (_, i) => ({
        id: `mock-${i}`,
        instrument_id: selectedInstrument.id,
        timestamp: new Date(Date.now() - (50 - i) * 24 * 60 * 60 * 1000).toISOString(),
        open: 150 + Math.random() * 10,
        high: 155 + Math.random() * 10,
        low: 148 + Math.random() * 10,
        close: 152 + Math.random() * 10,
        volume: 1000000 + Math.random() * 5000000,
        created_at: new Date().toISOString()
      }));
      setHistoricalData(mockData);
    }
  };

  const handleGenerateForecast = async () => {
    if (!selectedInstrument || !selectedModel || historicalData.length === 0) return;
    setGeneratingForecast(true);
    try {
      const forecastsData = await generateForecast(
        selectedInstrument.symbol, 
        selectedHorizon, 
        selectedModel.id
      );
      setForecasts(forecastsData);
    } catch (error) {
      console.error('Error generating forecast:', error);
      // Set mock forecast data if API fails
      const mockForecasts: Forecast[] = Array.from({ length: selectedHorizon }, (_, i) => ({
        id: `forecast-${i}`,
        instrument_id: selectedInstrument.id,
        model_id: selectedModel.id,
        forecast_timestamp: new Date().toISOString(),
        target_timestamp: new Date(Date.now() + (i + 1) * 60 * 60 * 1000).toISOString(),
        horizon_hours: selectedHorizon,
        predicted_price: historicalData[historicalData.length - 1].close + (Math.random() - 0.5) * 10,
        confidence_lower: historicalData[historicalData.length - 1].close + (Math.random() - 0.5) * 8,
        confidence_upper: historicalData[historicalData.length - 1].close + (Math.random() - 0.5) * 12,
        actual_price: null,
        created_at: new Date().toISOString()
      }));
      setForecasts(mockForecasts);
    } finally {
      setGeneratingForecast(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400 text-lg">Loading forecasting engine...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-cyan-900/20 via-transparent to-transparent"></div>
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-purple-900/20 via-transparent to-transparent"></div>

      <div className="relative">
        <header className="border-b border-slate-800/50 bg-slate-950/30 backdrop-blur-xl">
          <div className="container mx-auto px-6 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <TrendingUp className="w-8 h-8 text-cyan-400" />
                  <Sparkles className="w-4 h-4 text-purple-400 absolute -top-1 -right-1 animate-pulse" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400">
                    FinTech Forecaster
                  </h1>
                  <p className="text-sm text-slate-400">AI-Powered Market Prediction & Portfolio Management</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-green-400" />
                <span className="text-sm text-slate-400">Real-time Analysis</span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex space-x-1 mt-6">
              <button
                onClick={() => setActiveTab('forecasting')}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  activeTab === 'forecasting'
                    ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Forecasting
                </div>
              </button>
              <button
                onClick={() => setActiveTab('portfolio')}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  activeTab === 'portfolio'
                    ? 'bg-green-500 text-white shadow-lg shadow-green-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Wallet className="w-4 h-4" />
                  Portfolio Management
                </div>
              </button>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-6 py-8">
          {activeTab === 'forecasting' ? (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-1 space-y-6">
                <div className="bg-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-800/50 shadow-xl">
                  <InstrumentSelector
                    instruments={instruments}
                    selectedInstrument={selectedInstrument}
                    onSelect={setSelectedInstrument}
                  />
                </div>

                <div className="bg-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-800/50 shadow-xl">
                  <ForecastHorizonSelector
                    selectedHorizon={selectedHorizon}
                    onSelect={setSelectedHorizon}
                  />
                </div>

                <div className="bg-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-800/50 shadow-xl">
                  <ModelPerformance
                    models={models}
                    selectedModel={selectedModel}
                    onSelect={setSelectedModel}
                  />
                </div>
              </div>

              <div className="lg:col-span-3 space-y-6">
                <div className="bg-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-800/50 shadow-xl">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h2 className="text-2xl font-bold text-white mb-1">
                        {selectedInstrument?.symbol || 'Select Instrument'}
                      </h2>
                      <p className="text-slate-400">
                        {selectedInstrument?.name || 'Choose an instrument to view forecasts'}
                      </p>
                    </div>
                    <button
                      onClick={handleGenerateForecast}
                      disabled={!selectedInstrument || !selectedModel || generatingForecast}
                      className={`
                        px-6 py-3 rounded-lg font-semibold transition-all duration-200 flex items-center gap-2
                        ${!selectedInstrument || !selectedModel || generatingForecast
                          ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                          : 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:from-cyan-600 hover:to-blue-600 shadow-lg shadow-cyan-500/20'
                        }
                      `}
                    >
                      {generatingForecast ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></div>
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          Generate Forecast
                        </>
                      )}
                    </button>
                  </div>

                  {historicalData.length > 0 ? (
                    <div className="bg-slate-800/30 rounded-lg p-6 border border-slate-700/50">
                      <EnhancedCandlestickChart
                        data={historicalData}
                        forecasts={forecasts}
                        predictionErrors={[]} // You can fetch real prediction errors from backend later
                      />
                    </div>
                  ) : (
                    <div className="bg-slate-800/30 rounded-lg p-12 border border-slate-700/50 text-center">
                      <BarChart3 className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                      <p className="text-slate-400 text-lg">No historical data available</p>
                      <p className="text-slate-500 text-sm mt-2">Select an instrument to view charts</p>
                    </div>
                  )}
                </div>

                {forecasts.length > 0 && (
                  <div className="bg-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-800/50 shadow-xl">
                    <h3 className="text-xl font-bold text-white mb-4">Forecast Summary</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-lg p-4 border border-cyan-500/20">
                        <div className="text-sm text-slate-400 mb-1">Model Used</div>
                        <div className="text-lg font-semibold text-white">{selectedModel?.name}</div>
                        <div className="text-xs text-slate-500 capitalize mt-1">{selectedModel?.type}</div>
                      </div>
                      <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-lg p-4 border border-purple-500/20">
                        <div className="text-sm text-slate-400 mb-1">Forecast Horizon</div>
                        <div className="text-lg font-semibold text-white">{selectedHorizon} Hours</div>
                        <div className="text-xs text-slate-500 mt-1">{forecasts.length} data points</div>
                      </div>
                      <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-lg p-4 border border-green-500/20">
                        <div className="text-sm text-slate-400 mb-1">Expected Price</div>
                        <div className="text-lg font-semibold text-white">
                          ${forecasts[forecasts.length - 1]?.predicted_price.toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          At {new Date(forecasts[forecasts.length - 1]?.target_timestamp).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    
                    {/* Enhanced Forecast Details */}
                    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-slate-800/30 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-slate-300 mb-2">Confidence Interval</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Lower Bound:</span>
                            <span className="text-red-400">
                              ${forecasts[0]?.confidence_lower?.toFixed(2) || 'N/A'}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Upper Bound:</span>
                            <span className="text-green-400">
                              ${forecasts[0]?.confidence_upper?.toFixed(2) || 'N/A'}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="bg-slate-800/30 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-slate-300 mb-2">Forecast Range</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Start:</span>
                            <span className="text-slate-300">
                              {new Date(forecasts[0]?.target_timestamp).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-slate-400">End:</span>
                            <span className="text-slate-300">
                              {new Date(forecasts[forecasts.length - 1]?.target_timestamp).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <PortfolioDashboard 
              forecasts={forecasts}
              selectedInstrument={selectedInstrument?.symbol || null}
            />
          )}
        </main>

        <footer className="border-t border-slate-800/50 bg-slate-950/30 backdrop-blur-xl mt-12">
          <div className="container mx-auto px-6 py-6">
            <div className="text-center text-slate-500 text-sm">
              <p>Powered by Advanced ML Models: ARIMA, LSTM, GRU & Hybrid Ensembles</p>
              <p className="mt-2">© 2025 FinTech Forecaster - AI-Driven Financial Intelligence & Portfolio Management</p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;