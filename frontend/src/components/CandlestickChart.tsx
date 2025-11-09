import { useMemo } from 'react';
import { HistoricalPrice, Forecast } from '../lib/mongodb';

interface CandlestickChartProps {
  data: HistoricalPrice[];
  forecasts: Forecast[];
  selectedHorizon: number;
}

export default function CandlestickChart({ data, forecasts, selectedHorizon }: CandlestickChartProps) {
  const { minPrice, maxPrice, priceRange } = useMemo(() => {
    if (data.length === 0) return { minPrice: 0, maxPrice: 100, priceRange: 100 };

    const allPrices = [
      ...data.flatMap(d => [d.low, d.high]),
      ...forecasts.map(f => f.predicted_price),
      ...forecasts.filter(f => f.confidence_lower).map(f => f.confidence_lower!),
      ...forecasts.filter(f => f.confidence_upper).map(f => f.confidence_upper!)
    ];

    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const range = max - min;
    const padding = range * 0.1;

    return {
      minPrice: min - padding,
      maxPrice: max + padding,
      priceRange: range + (padding * 2)
    };
  }, [data, forecasts]);

  const chartHeight = 400;
  const chartWidth = 800;
  const padding = { top: 20, right: 80, bottom: 40, left: 60 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const getY = (price: number) => {
    return innerHeight - ((price - minPrice) / priceRange) * innerHeight;
  };

  const candleWidth = Math.max(2, Math.min(12, innerWidth / data.length - 2));

  const formatPrice = (price: number) => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const visibleData = data.slice(-100);
  const dataPointWidth = innerWidth / visibleData.length;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width={chartWidth}
        height={chartHeight}
        className="bg-gradient-to-br from-slate-900/50 to-slate-800/50 rounded-lg"
      >
        <defs>
          <linearGradient id="forecastGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.05" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        <g transform={`translate(${padding.left}, ${padding.top})`}>
          <line
            x1={0}
            y1={innerHeight}
            x2={innerWidth}
            y2={innerHeight}
            stroke="#475569"
            strokeWidth="1"
          />
          <line
            x1={0}
            y1={0}
            x2={0}
            y2={innerHeight}
            stroke="#475569"
            strokeWidth="1"
          />

          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
            const y = innerHeight * ratio;
            const price = maxPrice - (ratio * priceRange);
            return (
              <g key={`grid-line-${i}`}> {/* Added key */}
                <line
                  x1={0}
                  y1={y}
                  x2={innerWidth}
                  y2={y}
                  stroke="#334155"
                  strokeWidth="1"
                  strokeDasharray="4,4"
                  opacity="0.3"
                />
                <text
                  x={-10}
                  y={y + 4}
                  textAnchor="end"
                  className="text-xs fill-slate-400"
                  fontSize="11"
                >
                  ${formatPrice(price)}
                </text>
              </g>
            );
          })}

          {visibleData.map((candle, i) => {
            const x = i * dataPointWidth + dataPointWidth / 2;
            const isGreen = candle.close >= candle.open;
            const color = isGreen ? '#10b981' : '#ef4444';

            const openY = getY(candle.open);
            const closeY = getY(candle.close);
            const highY = getY(candle.high);
            const lowY = getY(candle.low);
            const bodyHeight = Math.abs(closeY - openY);
            const bodyY = Math.min(openY, closeY);

            return (
              <g key={`candle-${candle.id || i}`}> {/* Added key with fallback */}
                <line
                  x1={x}
                  y1={highY}
                  x2={x}
                  y2={lowY}
                  stroke={color}
                  strokeWidth="1"
                />
                <rect
                  x={x - candleWidth / 2}
                  y={bodyY}
                  width={candleWidth}
                  height={Math.max(bodyHeight, 1)}
                  fill={color}
                  opacity="0.9"
                />
              </g>
            );
          })}

          {forecasts.length > 0 && (
            <>
              {forecasts.map((forecast, i) => {
                const x = innerWidth + (i + 1) * 20;
                const y = getY(forecast.predicted_price);

                return (
                  <g key={`forecast-${forecast.id || i}`}> {/* Added key with fallback */}
                    {forecast.confidence_lower && forecast.confidence_upper && (
                      <line
                        x1={x}
                        y1={getY(forecast.confidence_lower)}
                        x2={x}
                        y2={getY(forecast.confidence_upper)}
                        stroke="#06b6d4"
                        strokeWidth="2"
                        opacity="0.3"
                      />
                    )}
                    <circle
                      cx={x}
                      cy={y}
                      r="4"
                      fill="#06b6d4"
                      filter="url(#glow)"
                    />
                  </g>
                );
              })}

              <path
                d={`M ${innerWidth} ${getY(visibleData[visibleData.length - 1].close)} ${forecasts.map((f, i) => {
                  const x = innerWidth + (i + 1) * 20;
                  const y = getY(f.predicted_price);
                  return `L ${x} ${y}`;
                }).join(' ')}`}
                stroke="#06b6d4"
                strokeWidth="2"
                fill="none"
                strokeDasharray="4,4"
                key="forecast-path" // Added key
              />

              <text
                x={innerWidth + 10}
                y={-5}
                className="text-xs fill-cyan-400 font-semibold"
                fontSize="11"
                key="forecast-label" // Added key
              >
                Forecast →
              </text>
            </>
          )}

          {[0, Math.floor(visibleData.length / 2), visibleData.length - 1].map(i => {
            if (i >= visibleData.length) return null;
            const x = i * dataPointWidth + dataPointWidth / 2;
            const candle = visibleData[i];
            return (
              <text
                key={`xaxis-label-${i}`} // Added key
                x={x}
                y={innerHeight + 20}
                textAnchor="middle"
                className="text-xs fill-slate-400"
                fontSize="10"
              >
                {formatDate(candle.timestamp)}
              </text>
            );
          })}
        </g>
      </svg>

      <div className="mt-4 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-emerald-500 rounded"></div>
          <span className="text-slate-300">BUY signal</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span className="text-slate-300">SELL signal</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-cyan-400 rounded"></div>
          <span className="text-slate-300">Forecast</span>
        </div>
      </div>
    </div>
  );
}