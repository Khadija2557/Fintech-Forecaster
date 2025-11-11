// components/EnhancedCandlestickChart.tsx
import { useMemo } from 'react';
import { HistoricalPrice, Forecast } from '../lib/mongodb';

interface EnhancedCandlestickChartProps {
  data: HistoricalPrice[];
  forecasts: Forecast[];
  predictionErrors?: { timestamp: string; error: number; predicted: number; actual: number }[];
  showPredictionErrors?: boolean;
}

export default function EnhancedCandlestickChart({ 
  data, 
  forecasts,
  showPredictionErrors = false
}: EnhancedCandlestickChartProps) {
  
  const { minPrice, maxPrice, priceRange, visibleData, dateRange } = useMemo(() => {
    if (data.length === 0) return { 
      minPrice: 0, 
      maxPrice: 100, 
      priceRange: 100, 
      visibleData: [],
      dateRange: { min: new Date(), max: new Date() }
    };

    // Show only 30 historical points for better visibility
    const visibleData = data.slice(-30);
    
    const allPrices = [
      ...visibleData.flatMap(d => [d.low, d.high, d.close, d.open]),
      ...forecasts.map(f => f.predicted_price),
      ...forecasts.filter(f => f.confidence_lower).map(f => f.confidence_lower!),
      ...forecasts.filter(f => f.confidence_upper).map(f => f.confidence_upper!)
    ].filter(price => !isNaN(price) && isFinite(price));

    // Calculate date range for X-axis
    const historicalDates = visibleData.map(d => new Date(d.timestamp).getTime());
    const forecastDates = forecasts.map(f => new Date(f.target_timestamp).getTime());
    const allDates = [...historicalDates, ...forecastDates];
    
    const dateRange = {
      min: new Date(Math.min(...allDates)),
      max: new Date(Math.max(...allDates))
    };

    if (allPrices.length === 0) return { 
      minPrice: 0, 
      maxPrice: 100, 
      priceRange: 100, 
      visibleData,
      dateRange
    };

    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const range = max - min;
    const padding = range * 0.05;

    return {
      minPrice: min - padding,
      maxPrice: max + padding,
      priceRange: range + (padding * 2),
      visibleData,
      dateRange
    };
  }, [data, forecasts]);

  const chartHeight = 500;
  const chartWidth = Math.max(800, visibleData.length * 25); // Increased width for more candles
  const padding = { top: 20, right: 60, bottom: 60, left: 60 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const getY = (price: number) => {
    return innerHeight - ((price - minPrice) / priceRange) * innerHeight;
  };

  const getX = (timestamp: string | Date, isForecast: boolean = false) => {
    const date = new Date(timestamp);
    const totalTimeRange = dateRange.max.getTime() - dateRange.min.getTime();
    const timePosition = date.getTime() - dateRange.min.getTime();
    
    if (totalTimeRange === 0) return padding.left;
    
    const ratio = timePosition / totalTimeRange;
    return padding.left + (ratio * innerWidth);
  };

  // REDUCED SPACING: Increased candle width and reduced spacing
  const candleWidth = Math.max(8, Math.min(15, innerWidth / visibleData.length * 0.9));

  const formatPrice = (price: number) => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric'
    });
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  };

  // Generate date labels for X-axis - SIMPLIFIED
  const dateLabels = useMemo(() => {
    if (visibleData.length === 0) return [];
    
    const labels = [];
    
    // Only show key dates: first, middle, last historical
    labels.push({
      x: getX(visibleData[0].timestamp),
      date: new Date(visibleData[0].timestamp),
      isMajor: true,
      isForecast: false
    });
    
    // Middle historical point
    const middleIndex = Math.floor(visibleData.length / 2);
    labels.push({
      x: getX(visibleData[middleIndex].timestamp),
      date: new Date(visibleData[middleIndex].timestamp),
      isMajor: true,
      isForecast: false
    });
    
    // Last historical date
    labels.push({
      x: getX(visibleData[visibleData.length - 1].timestamp),
      date: new Date(visibleData[visibleData.length - 1].timestamp),
      isMajor: true,
      isForecast: false
    });
    
    // Forecast dates - only show first and last
    if (forecasts.length > 0) {
      labels.push({
        x: getX(forecasts[0].target_timestamp, true),
        date: new Date(forecasts[0].target_timestamp),
        isMajor: true,
        isForecast: true
      });
      
      if (forecasts.length > 1) {
        labels.push({
          x: getX(forecasts[forecasts.length - 1].target_timestamp, true),
          date: new Date(forecasts[forecasts.length - 1].target_timestamp),
          isMajor: true,
          isForecast: true
        });
      }
    }
    
    return labels;
  }, [visibleData, forecasts, dateRange]);

  // Filter forecasts to show only 3 key points: first, middle, and last
  const visibleForecasts = useMemo(() => {
    if (forecasts.length <= 3) return forecasts;
    
    const filtered = [forecasts[0]];
    
    // Add middle point
    const middleIndex = Math.floor(forecasts.length / 2);
    filtered.push(forecasts[middleIndex]);
    
    // Add last point
    filtered.push(forecasts[forecasts.length - 1]);
    
    return filtered;
  }, [forecasts]);

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

          {/* Forecast area gradient */}
          <linearGradient id="forecastArea" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.05" />
          </linearGradient>

          {/* Error gradients for monitoring dashboard */}
          {showPredictionErrors && (
            <>
              <linearGradient id="overpredictionGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#ec4899" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#ec4899" stopOpacity="0.3" />
              </linearGradient>
              <linearGradient id="underpredictionGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#fbbf24" stopOpacity="0.3" />
              </linearGradient>
            </>
          )}
        </defs>

        {/* X-Axis Line */}
        <line
          x1={padding.left}
          y1={chartHeight - padding.bottom}
          x2={chartWidth - padding.right}
          y2={chartHeight - padding.bottom}
          stroke="#475569"
          strokeWidth="2"
        />

        {/* Y-Axis Line */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={chartHeight - padding.bottom}
          stroke="#475569"
          strokeWidth="2"
        />

        {/* X-Axis Date Labels */}
        <g className="x-axis-dates">
          {dateLabels.map((label, index) => (
            <g key={`date-${index}`} transform={`translate(${label.x}, ${chartHeight - 25})`}>
              <text
                textAnchor="middle"
                className={`text-xs ${label.isForecast ? 'fill-cyan-400' : 'fill-slate-400'} font-medium`}
                fontSize="10"
              >
                {formatDate(label.date)}
              </text>
              <text
                y={15}
                textAnchor="middle"
                className={`text-xs ${label.isForecast ? 'fill-cyan-300' : 'fill-slate-500'}`}
                fontSize="9"
              >
                {formatTime(label.date)}
              </text>
            </g>
          ))}
        </g>

        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines and price labels */}
          {[0, 0.5, 1].map((ratio, i) => {
            const y = innerHeight * ratio;
            const price = maxPrice - (ratio * priceRange);
            return (
              <g key={`grid-line-${i}`}>
                <line
                  x1={0}
                  y1={y}
                  x2={innerWidth}
                  y2={y}
                  stroke="#475569"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                <text
                  x={-8}
                  y={y + 4}
                  textAnchor="end"
                  className="text-xs fill-slate-300 font-medium"
                  fontSize="10"
                >
                  ${formatPrice(price)}
                </text>
              </g>
            );
          })}

          {/* Timeline separator between historical and forecast */}
          {forecasts.length > 0 && (
            <g>
              <line
                x1={getX(visibleData[visibleData.length - 1].timestamp) - padding.left}
                y1={0}
                x2={getX(visibleData[visibleData.length - 1].timestamp) - padding.left}
                y2={innerHeight}
                stroke="#06b6d4"
                strokeWidth="2"
                strokeDasharray="4,4"
                opacity="0.7"
              />
            </g>
          )}

          {/* Candlestick Chart - REDUCED SPACING BETWEEN CANDLES */}
          {visibleData.map((candle, i) => {
            const x = getX(candle.timestamp) - padding.left;
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
                {/* Wick */}
                <line
                  x1={x}
                  y1={highY}
                  x2={x}
                  y2={lowY}
                  stroke={color}
                  strokeWidth="1.5"
                />
                {/* Body */}
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
          {visibleForecasts.length > 0 && (
            <>
              {/* Forecast area background */}
              <rect
                x={getX(visibleForecasts[0].target_timestamp, true) - padding.left}
                y={0}
                width={getX(visibleForecasts[visibleForecasts.length - 1].target_timestamp, true) - getX(visibleForecasts[0].target_timestamp, true)}
                height={innerHeight}
                fill="url(#forecastArea)"
              />

              {visibleForecasts.map((forecast, i) => {
                const x = getX(forecast.target_timestamp, true) - padding.left;
                const y = getY(forecast.predicted_price);

                return (
                  <g key={`forecast-${forecast.id || i}`}>
                    <circle
                      cx={x}
                      cy={y}
                      r="5"
                      fill="#06b6d4"
                      stroke="#0ea5e9"
                      strokeWidth="2"
                    />
                  </g>
                );
              })}

              {/* Forecast line */}
              <path
                d={`M ${getX(visibleData[visibleData.length - 1].timestamp) - padding.left} ${getY(visibleData[visibleData.length - 1].close)} ${visibleForecasts.map((f, i) => {
                  const x = getX(f.target_timestamp, true) - padding.left;
                  const y = getY(f.predicted_price);
                  return `L ${x} ${y}`;
                }).join(' ')}`}
                stroke="#06b6d4"
                strokeWidth="2"
                fill="none"
                strokeDasharray="4,4"
              />
            </>
          )}
        </g>

        {/* Legend - UPDATED TEXT */}
        <g transform={`translate(${padding.left}, ${padding.top - 10})`}>
          <rect x={0} y={0} width={10} height={10} fill="#10b981" />
          <text x={15} y={9} className="text-xs fill-slate-300" fontSize="9">Stocks Increasing</text>
          
          <rect x={110} y={0} width={10} height={10} fill="#ef4444" />
          <text x={125} y={9} className="text-xs fill-slate-300" fontSize="9">Stocks Decreasing</text>
          
          <circle cx={220} cy={5} r="4" fill="#06b6d4" />
          <text x={230} y={9} className="text-xs fill-slate-300" fontSize="9">Forecast</text>
          
          {/* Add error legend only for monitoring dashboard */}
          {showPredictionErrors && (
            <>
              <circle cx={290} cy={5} r="5" fill="#ec4899" />
              <text x={300} y={9} className="text-xs fill-slate-300" fontSize="9">Overprediction</text>
              
              <circle cx={385} cy={5} r="5" fill="#fbbf24" />
              <text x={395} y={9} className="text-xs fill-slate-300" fontSize="9">Underprediction</text>
            </>
          )}
        </g>

        {/* Forecast Summary */}
        {visibleForecasts.length > 0 && (
          <g transform={`translate(${padding.left + innerWidth - 200}, ${padding.top + 10})`}>
            <rect x={0} y={0} width={190} height={40} fill="#1f2937" opacity="0.9" rx="4" />
            <text x={8} y={12} className="text-xs fill-cyan-400 font-semibold" fontSize="9">
              Forecast Summary
            </text>
            <text x={8} y={25} className="text-xs fill-slate-300" fontSize="8">
              Start: ${visibleForecasts[0].predicted_price.toFixed(2)}
            </text>
            <text x={8} y={35} className="text-xs fill-slate-300" fontSize="8">
              End: ${visibleForecasts[visibleForecasts.length - 1].predicted_price.toFixed(2)}
            </text>
          </g>
        )}
      </svg>

      {/* Stats Cards */}
      {visibleForecasts.length > 0 && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="bg-cyan-500/10 rounded-lg p-4 border border-cyan-500/20">
            <div className="text-sm text-cyan-400 font-semibold">Start Price</div>
            <div className="text-lg font-bold text-white">
              ${visibleForecasts[0].predicted_price.toFixed(2)}
            </div>
          </div>
          <div className="bg-cyan-500/10 rounded-lg p-4 border border-cyan-500/20">
            <div className="text-sm text-cyan-400 font-semibold">End Price</div>
            <div className="text-lg font-bold text-white">
              ${visibleForecasts[visibleForecasts.length - 1].predicted_price.toFixed(2)}
            </div>
          </div>
          <div className="bg-cyan-500/10 rounded-lg p-4 border border-cyan-500/20">
            <div className="text-sm text-cyan-400 font-semibold">Change</div>
            <div className={`text-lg font-bold ${
              visibleForecasts[visibleForecasts.length - 1].predicted_price >= visibleForecasts[0].predicted_price 
                ? 'text-green-400' 
                : 'text-red-400'
            }`}>
              {((visibleForecasts[visibleForecasts.length - 1].predicted_price - visibleForecasts[0].predicted_price) / visibleForecasts[0].predicted_price * 100).toFixed(2)}%
            </div>
          </div>
          <div className="bg-cyan-500/10 rounded-lg p-4 border border-cyan-500/20">
            <div className="text-sm text-cyan-400 font-semibold">Points Shown</div>
            <div className="text-lg font-bold text-white">
              {visibleForecasts.length} of {forecasts.length}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}