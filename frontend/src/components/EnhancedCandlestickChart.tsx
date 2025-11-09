// components/EnhancedCandlestickChart.tsx
import { useMemo } from 'react';
import { HistoricalPrice, Forecast } from '../lib/mongodb';

interface EnhancedCandlestickChartProps {
  data: HistoricalPrice[];
  forecasts: Forecast[];
  predictionErrors?: { timestamp: string; error: number }[];
}

export default function EnhancedCandlestickChart({ 
  data, 
  forecasts, 
  predictionErrors = []
}: EnhancedCandlestickChartProps) {
  
  const { minPrice, maxPrice, priceRange, errorData } = useMemo(() => {
    if (data.length === 0) return { minPrice: 0, maxPrice: 100, priceRange: 100, errorData: [] };

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

    // Prepare error data for visualization
    const errorData = predictionErrors.map(error => ({
      ...error,
      normalizedError: Math.min(Math.abs(error.error) / range * 100, 50) // Cap at 50% of chart height
    }));

    return {
      minPrice: min - padding,
      maxPrice: max + padding,
      priceRange: range + (padding * 2),
      errorData
    };
  }, [data, forecasts, predictionErrors]);

  const chartHeight = 500;
  const chartWidth = 800;
  const padding = { top: 20, right: 80, bottom: 60, left: 60 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const getY = (price: number) => {
    return innerHeight - ((price - minPrice) / priceRange) * innerHeight;
  };

  const candleWidth = Math.max(2, Math.min(12, innerWidth / data.length - 2));
  const visibleData = data.slice(-50); // Show last 50 points
  const dataPointWidth = innerWidth / visibleData.length;

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
          <linearGradient id="errorGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.05" />
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
          {/* Grid lines and price labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
            const y = innerHeight * ratio;
            const price = maxPrice - (ratio * priceRange);
            return (
              <g key={`grid-line-${i}`}>
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

          {/* Error Overlays */}
          {errorData.map((error, i) => {
            const dataIndex = visibleData.findIndex(d => 
              new Date(d.timestamp).toDateString() === new Date(error.timestamp).toDateString()
            );
            if (dataIndex === -1) return null;
            
            const x = dataIndex * dataPointWidth + dataPointWidth / 2;
            const errorHeight = (error.normalizedError / 100) * innerHeight;
            const errorY = innerHeight - errorHeight;
            
            return (
              <g key={`error-${i}`}>
                <rect
                  x={x - candleWidth}
                  y={errorY}
                  width={candleWidth * 2}
                  height={errorHeight}
                  fill="url(#errorGradient)"
                  opacity="0.6"
                />
                <line
                  x1={x}
                  y1={errorY}
                  x2={x}
                  y2={innerHeight}
                  stroke="#ef4444"
                  strokeWidth="2"
                  opacity="0.8"
                />
              </g>
            );
          })}

          {/* Candlestick Chart */}
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
              <g key={`candle-${candle.id || i}`}>
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

          {/* Forecast Visualization */}
          {forecasts.length > 0 && (
            <>
              {forecasts.map((forecast, i) => {
                const x = innerWidth + (i + 1) * 20;
                const y = getY(forecast.predicted_price);

                return (
                  <g key={`forecast-${forecast.id || i}`}>
                    {forecast.confidence_lower && forecast.confidence_upper && (
                      <rect
                        x={x - 8}
                        y={getY(forecast.confidence_upper)}
                        width={16}
                        height={getY(forecast.confidence_lower) - getY(forecast.confidence_upper)}
                        fill="url(#forecastGradient)"
                        opacity="0.5"
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
              />

              <text
                x={innerWidth + 10}
                y={-5}
                className="text-xs fill-cyan-400 font-semibold"
                fontSize="11"
              >
                Forecast →
              </text>
            </>
          )}

          {/* X-axis labels */}
          {[0, Math.floor(visibleData.length / 2), visibleData.length - 1].map(i => {
            if (i >= visibleData.length) return null;
            const x = i * dataPointWidth + dataPointWidth / 2;
            const candle = visibleData[i];
            return (
              <text
                key={`xaxis-label-${i}`}
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

        {/* Legend */}
        <g transform={`translate(${padding.left}, ${chartHeight - 30})`}>
          <rect x={0} y={0} width={12} height={12} fill="#10b981" />
          <text x={15} y={10} className="text-xs fill-slate-300" fontSize="10">Bullish</text>
          
          <rect x={80} y={0} width={12} height={12} fill="#ef4444" />
          <text x={95} y={10} className="text-xs fill-slate-300" fontSize="10">Bearish</text>
          
          <rect x={160} y={0} width={12} height={12} fill="#06b6d4" />
          <text x={175} y={10} className="text-xs fill-slate-300" fontSize="10">Forecast</text>
          
          <rect x={240} y={0} width={12} height={12} fill="url(#errorGradient)" />
          <text x={255} y={10} className="text-xs fill-slate-300" fontSize="10">Prediction Error</text>
        </g>
      </svg>
    </div>
  );
}