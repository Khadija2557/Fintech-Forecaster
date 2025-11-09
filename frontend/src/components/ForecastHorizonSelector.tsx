import { Clock } from 'lucide-react';

interface ForecastHorizonSelectorProps {
  selectedHorizon: number;
  onSelect: (hours: number) => void;
}

const horizons = [
  { hours: 1, label: '1 Hour' },
  { hours: 3, label: '3 Hours' },
  { hours: 24, label: '24 Hours' },
  { hours: 72, label: '72 Hours' }
];

export default function ForecastHorizonSelector({
  selectedHorizon,
  onSelect
}: ForecastHorizonSelectorProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500 flex items-center gap-2">
        <Clock className="w-5 h-5 text-purple-400" />
        Forecast Horizon
      </h3>

      <div className="grid grid-cols-2 gap-3">
        {horizons.map(({ hours, label }) => (
          <button
            key={hours}
            onClick={() => onSelect(hours)}
            className={`
              px-4 py-3 rounded-lg transition-all duration-200 font-medium
              ${selectedHorizon === hours
                ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 border-2 border-purple-400/50 text-white shadow-lg shadow-purple-500/20'
                : 'bg-slate-800/50 border-2 border-slate-700/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800/70'
              }
            `}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
