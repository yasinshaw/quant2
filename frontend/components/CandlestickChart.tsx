'use client';

import {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  createSeriesMarkers,
  type IChartApi,
  type Time,
} from 'lightweight-charts';
import { dataApi } from '@/lib/api/data';
import type { Trade } from '@/lib/api/backtest';
import {
  transformCandles,
  transformVolume,
  transformTradesToMarkers,
  findTradeByMarkerId,
  type ApiCandle,
} from './CandlestickChart.utils';

interface ChartDataset {
  id: number;
  name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
}

interface Props {
  trades: Trade[];
  dataset: ChartDataset | null;
  initialCash?: number;
}

export interface CandlestickChartHandle {
  scrollToTrade: (trade: Trade) => void;
}

function formatDuration(hours: number): string {
  if (hours < 24) return `${hours.toFixed(0)}h`;
  const days = Math.floor(hours / 24);
  const remainHours = Math.round(hours % 24);
  return remainHours > 0 ? `${days}d ${remainHours}h` : `${days}d`;
}

function TradePopup({
  trade,
  balance,
  position,
  onClose,
}: {
  trade: Trade;
  balance?: number;
  position: { x: number; y: number };
  onClose: () => void;
}) {
  const profitable = trade.pnl >= 0;
  const posCost = trade.entry_price * trade.size;
  const posPct = posCost > 0 ? (trade.pnl / posCost) * 100 : undefined;
  const balPct = balance && balance > 0 ? (trade.pnl / balance) * 100 : undefined;

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="absolute z-50 bg-white rounded-lg shadow-xl border border-gray-200 p-4 w-72"
        style={{ left: position.x, top: position.y }}
      >
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500">#{trade.trade_no}</span>
            <span
              className={`text-sm font-bold px-2 py-0.5 rounded ${
                trade.side === 'BUY'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              {trade.side}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            &times;
          </button>
        </div>
        <div className="space-y-1.5 text-sm">
          <Row label="Entry" value={`$${trade.entry_price.toFixed(2)}`} />
          <Row label="Exit" value={`$${trade.exit_price.toFixed(2)}`} />
          <Row label="Size" value={trade.size.toFixed(4)} />
          <Row
            label="PnL"
            value={`${profitable ? '+' : ''}$${trade.pnl.toFixed(2)}`}
            className={profitable ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}
          />
          {posPct !== undefined && (
            <Row
              label="Pos %"
              value={`${posPct >= 0 ? '+' : ''}${posPct.toFixed(2)}%`}
              className={profitable ? 'text-green-600' : 'text-red-600'}
            />
          )}
          {balPct !== undefined && (
            <Row
              label="Bal %"
              value={`${balPct >= 0 ? '+' : ''}${balPct.toFixed(2)}%`}
              className={profitable ? 'text-green-600' : 'text-red-600'}
            />
          )}
          <Row
            label="Hold Time"
            value={formatDuration(
              (new Date(trade.exit_time).getTime() - new Date(trade.entry_time).getTime()) /
                3600000
            )}
          />
          <Row label="Commission" value={`$${trade.commission.toFixed(2)}`} />
        </div>
      </div>
    </>
  );
}

function Row({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className={className ?? 'text-gray-900'}>{value}</span>
    </div>
  );
}

const CandlestickChart = forwardRef<CandlestickChartHandle, Props>(function CandlestickChart(
  { trades, dataset, initialCash },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  // Keep markers primitive alive to prevent GC removing markers from chart
  const seriesMarkersRef = useRef<any>(null);

  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [popupPosition, setPopupPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Compute running balance at each trade (by exit_time) for BAL% calculation
  const tradeBalances = useMemo((): Map<number, number> => {
    const balances = new Map<number, number>();
    if (!initialCash) return balances;
    const sorted = [...trades].sort(
      (a, b) => new Date(a.exit_time).getTime() - new Date(b.exit_time).getTime()
    );
    let balance = initialCash;
    for (const t of sorted) {
      balances.set(t.trade_no, balance);
      balance += t.pnl;
    }
    return balances;
  }, [trades, initialCash]);

  // Fetch candles if dataset is available
  const { data: candles } = useQuery({
    queryKey: ['candles', dataset?.symbol, dataset?.interval, dataset?.start_time, dataset?.end_time],
    queryFn: () =>
      dataApi.getCandles(dataset!.symbol, dataset!.interval, dataset!.start_time, dataset!.end_time),
    enabled: !!dataset,
    staleTime: 5 * 60 * 1000,
  });

  const candleData = useMemo(() => transformCandles((candles ?? []) as ApiCandle[]), [candles]);
  const volumeData = useMemo(() => transformVolume((candles ?? []) as ApiCandle[]), [candles]);
  const markers = useMemo(() => transformTradesToMarkers(trades), [trades]);

  // Expose scrollToTrade to parent
  useImperativeHandle(ref, () => ({
    scrollToTrade(trade: Trade) {
      const chart = chartRef.current;
      if (!chart) return;

      // Scroll page to chart
      wrapperRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Set visible range around the trade
      const entrySec = Math.floor(new Date(trade.entry_time).getTime() / 1000);
      const exitSec = Math.floor(new Date(trade.exit_time).getTime() / 1000);

      // Add padding: 15% of trade duration on each side, minimum 6 hours
      const duration = exitSec - entrySec;
      const padding = Math.max(Math.floor(duration * 0.15), 6 * 3600);

      chart.timeScale().setVisibleRange({
        from: (entrySec - padding) as Time,
        to: (exitSec + padding) as Time,
      });

      // Show trade popup
      setSelectedTrade(trade);
      setPopupPosition({ x: 16, y: 16 });
    },
  }));

  // Detect dark mode
  const isDark = useCallback(() => {
    if (typeof document === 'undefined') return false;
    return document.documentElement.classList.contains('dark');
  }, []);

  const getThemeColors = useCallback(
    (dark: boolean) => ({
      background: dark ? '#1a1a2e' : '#ffffff',
      textColor: dark ? '#d1d5db' : '#333333',
      gridColor: dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
      borderColor: dark ? '#374151' : '#e5e7eb',
    }),
    []
  );

  useEffect(() => {
    if (!containerRef.current || candleData.length === 0) return;

    const dark = isDark();
    const colors = getThemeColors(dark);
    const container = containerRef.current;

    const chart = createChart(container, {
      layout: {
        background: { color: colors.background },
        textColor: colors.textColor,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: colors.borderColor },
      timeScale: {
        borderColor: colors.borderColor,
        timeVisible: true,
        secondsVisible: false,
      },
      autoSize: true,
    });

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    candleSeries.setData(candleData);

    // Volume series (overlay bottom 25%)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.75, bottom: 0 },
    });
    volumeSeries.setData(volumeData);

    // Trade markers — keep reference alive to prevent GC
    if (markers.length > 0) {
      seriesMarkersRef.current = createSeriesMarkers(candleSeries, markers);
    }

    // Click handler for markers
    chart.subscribeClick((param) => {
      if (param.hoveredObjectId && typeof param.hoveredObjectId === 'string' && param.point) {
        const trade = findTradeByMarkerId(param.hoveredObjectId, trades);
        if (trade && containerRef.current) {
          const rect = containerRef.current.getBoundingClientRect();
          const x = Math.min(param.point.x, rect.width - 300);
          const y = param.point.y > rect.height / 2 ? param.point.y - 250 : param.point.y + 10;
          setPopupPosition({ x, y });
          setSelectedTrade(trade);
          return;
        }
      }
      setSelectedTrade(null);
    });

    chart.timeScale().fitContent();
    chartRef.current = chart;

    // Dark mode observer
    const observer = new MutationObserver(() => {
      const d = isDark();
      const c = getThemeColors(d);
      chart.applyOptions({
        layout: {
          background: { color: c.background },
          textColor: c.textColor,
        },
        grid: {
          vertLines: { color: c.gridColor },
          horzLines: { color: c.gridColor },
        },
        rightPriceScale: { borderColor: c.borderColor },
        timeScale: { borderColor: c.borderColor },
      });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesMarkersRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candleData, volumeData, markers]);

  if (!dataset) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Price Chart</h2>
        <p className="text-gray-500 text-sm">
          Candlestick chart unavailable — no dataset information linked to this backtest.
        </p>
      </div>
    );
  }

  if (candleData.length === 0 && candles === undefined) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Price Chart</h2>
        <div className="animate-pulse h-96 bg-gray-100 rounded" />
      </div>
    );
  }

  return (
    <div ref={wrapperRef} className="bg-white rounded-xl shadow-md p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">
          Price Chart
          <span className="text-sm font-normal text-gray-500 ml-2">
            {dataset.symbol} {dataset.interval}
          </span>
        </h2>
        <button
          onClick={() => {
            chartRef.current?.timeScale().fitContent();
            setSelectedTrade(null);
          }}
          className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          Fit All
        </button>
      </div>
      <div className="relative">
        <div ref={containerRef} className="w-full" style={{ height: 500 }} />
        {selectedTrade && (
          <TradePopup
            trade={selectedTrade}
            balance={tradeBalances.get(selectedTrade.trade_no)}
            position={popupPosition}
            onClose={() => setSelectedTrade(null)}
          />
        )}
      </div>
      <p className="text-xs text-gray-400 mt-2 text-right">
        Click trade markers to view details. Scroll to zoom, drag to pan.
      </p>
    </div>
  );
});

export default CandlestickChart;
