import { Brain, TrendingUp, Activity } from 'lucide-react';
import { ForecastingModel } from '../lib/mongodb';

interface ModelPerformanceProps {
  models: ForecastingModel[];
  selectedModel: ForecastingModel | null;
  onSelect: (model: ForecastingModel) => void;
}

export default function ModelPerformance({
  models,
  selectedModel,
  onSelect
}: ModelPerformanceProps) {
  const getModelIcon = (type: string) => {
    switch (type) {
      case 'neural':
        return <Brain className="w-5 h-5 text-pink-400" />;
      case 'traditional':
        return <TrendingUp className="w-5 h-5 text-green-400" />;
      case 'ensemble':
        return <Activity className="w-5 h-5 text-purple-400" />;
      default:
        return <Brain className="w-5 h-5" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'neural':
        return 'from-pink-500/20 to-rose-500/20 border-pink-400/50';
      case 'traditional':
        return 'from-green-500/20 to-emerald-500/20 border-green-400/50';
      case 'ensemble':
        return 'from-purple-500/20 to-indigo-500/20 border-purple-400/50';
      default:
        return 'from-slate-500/20 to-slate-500/20 border-slate-400/50';
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">
        Forecasting Models
      </h3>

      <div className="grid gap-3">
        {models.map(model => (
          <button
            key={model.id}
            onClick={() => onSelect(model)}
            className={`
              w-full text-left p-4 rounded-lg transition-all duration-200
              ${selectedModel?.id === model.id
                ? `bg-gradient-to-r ${getTypeColor(model.type)} border-2 shadow-lg`
                : 'bg-slate-800/50 border-2 border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/70'
              }
            `}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                {getModelIcon(model.type)}
                <div>
                  <div className="font-semibold text-white">{model.name}</div>
                  <div className="text-xs text-slate-400 capitalize">{model.type}</div>
                </div>
              </div>
              {model.is_active && (
                <span className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded-full border border-green-500/30">
                  Active
                </span>
              )}
            </div>

            <div className="text-xs text-slate-400 mb-3 line-clamp-2">
              {model.description}
            </div>

            {model.performance_metrics && (
              <div className="grid grid-cols-3 gap-2">
                {model.performance_metrics.rmse && (
                  <div className="bg-slate-900/50 rounded px-2 py-1">
                    <div className="text-xs text-slate-500">RMSE</div>
                    <div className="text-sm font-semibold text-white">
                      {model.performance_metrics.rmse.toFixed(2)}
                    </div>
                  </div>
                )}
                {model.performance_metrics.mae && (
                  <div className="bg-slate-900/50 rounded px-2 py-1">
                    <div className="text-xs text-slate-500">MAE</div>
                    <div className="text-sm font-semibold text-white">
                      {model.performance_metrics.mae.toFixed(2)}
                    </div>
                  </div>
                )}
                {model.performance_metrics.mape && (
                  <div className="bg-slate-900/50 rounded px-2 py-1">
                    <div className="text-xs text-slate-500">MAPE</div>
                    <div className="text-sm font-semibold text-white">
                      {model.performance_metrics.mape.toFixed(2)}%
                    </div>
                  </div>
                )}
              </div>
            )}
          </button>
        ))}
      </div>

      <div className="mt-4 p-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
        <div className="text-xs text-slate-400 space-y-1">
          <div><span className="font-semibold text-slate-300">RMSE:</span> Root Mean Square Error (lower is better)</div>
          <div><span className="font-semibold text-slate-300">MAE:</span> Mean Absolute Error (lower is better)</div>
          <div><span className="font-semibold text-slate-300">MAPE:</span> Mean Absolute Percentage Error (lower is better)</div>
        </div>
      </div>
    </div>
  );
}
