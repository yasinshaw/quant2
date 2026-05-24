'use client';

import { useRef, useCallback, useEffect } from 'react';
import { createChart, CandlestickSeries, UTCTimestamp, IChartApi } from 'lightweight-charts';

export default function TestChartPage() {
  const chartRef = useRef<IChartApi | null>(null);

  const setContainerRef = useCallback((node: HTMLDivElement | null) => {
    if (node && !chartRef.current) {
      const chart = createChart(node, {
        width: node.clientWidth || 800,
        height: 400,
        layout: {
          background: { color: 'transparent' },
          textColor: '#64748b',
        },
        grid: {
          vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
          horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
        },
        crosshair: { mode: 1 },
        rightPriceScale: {
          borderColor: 'rgba(148, 163, 184, 0.2)',
        },
        timeScale: {
          borderColor: 'rgba(148, 163, 184, 0.2)',
          timeVisible: true,
          secondsVisible: false,
        },
      });

      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderDownColor: '#ef4444',
        borderUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        wickUpColor: '#22c55e',
      });

      // Add sample data
      const data = [
        { time: 1776398400 as UTCTimestamp, open: 2324, high: 2341, low: 2315, close: 2333 },
        { time: 1776412800 as UTCTimestamp, open: 2333, high: 2377, low: 2332, close: 2353 },
        { time: 1776427200 as UTCTimestamp, open: 2353, high: 2447, low: 2347, close: 2430 },
        { time: 1776441600 as UTCTimestamp, open: 2430, high: 2450, low: 2420, close: 2440 },
        { time: 1776456000 as UTCTimestamp, open: 2440, high: 2460, low: 2430, close: 2450 },
      ];

      series.setData(data);
      chart.timeScale().fitContent();
      chartRef.current = chart;

      const handleResize = () => {
        chart.applyOptions({ width: node.clientWidth });
      };
      window.addEventListener('resize', handleResize);

      (chart as any)._cleanup = () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
        chartRef.current = null;
      };
    }
  }, []);

  useEffect(() => {
    return () => {
      if (chartRef.current && (chartRef.current as any)._cleanup) {
        (chartRef.current as any)._cleanup();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Test Chart</h1>
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
          <div ref={setContainerRef} style={{ height: '400px' }} />
        </div>
      </div>
    </div>
  );
}
