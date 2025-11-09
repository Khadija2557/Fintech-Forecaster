import { TrendingUp, Bitcoin, DollarSign } from 'lucide-react';
import { Instrument } from '../lib/mongodb';

interface InstrumentSelectorProps {
  instruments: Instrument[];
  selectedInstrument: Instrument | null;
  onSelect: (instrument: Instrument) => void;
}

export default function InstrumentSelector({
  instruments,
  selectedInstrument,
  onSelect
}: InstrumentSelectorProps) {
  const getIcon = (type: string) => {
    switch (type) {
      case 'stock':
        return <TrendingUp className="w-5 h-5" />;
      case 'crypto':
        return <Bitcoin className="w-5 h-5" />;
      case 'forex':
        return <DollarSign className="w-5 h-5" />;
      default:
        return <TrendingUp className="w-5 h-5" />;
    }
  };

  const groupedInstruments = instruments.reduce((acc, instrument) => {
    if (!acc[instrument.type]) {
      acc[instrument.type] = [];
    }
    acc[instrument.type].push(instrument);
    return acc;
  }, {} as Record<string, Instrument[]>);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
        Select Instrument
      </h3>

      {Object.entries(groupedInstruments).map(([type, items]) => (
        <div key={type} className="space-y-2">
          <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider flex items-center gap-2">
            {getIcon(type)}
            {type}
          </h4>
          <div className="grid gap-2">
            {items.map(instrument => (
              <button
                key={instrument.id}
                onClick={() => onSelect(instrument)}
                className={`
                  w-full text-left px-4 py-3 rounded-lg transition-all duration-200
                  ${selectedInstrument?.id === instrument.id
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border-2 border-cyan-400/50 shadow-lg shadow-cyan-500/20'
                    : 'bg-slate-800/50 border-2 border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/70'
                  }
                `}
              >
                <div className="flex justify-between items-center">
                  <div>
                    <div className="font-semibold text-white">{instrument.symbol}</div>
                    <div className="text-sm text-slate-400">{instrument.name}</div>
                  </div>
                  <div className="text-xs text-slate-500">{instrument.exchange}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
