'use client';

import { useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { backtestApi } from '@/lib/api/backtest';
import { historyApi } from '@/lib/api/history';
import EquityCurve from '@/components/EquityCurve';
import MonthlyReturns from '@/components/MonthlyReturns';
import TradeTable from '@/components/TradeTable';
import ConfigurationSection from '@/components/ConfigurationSection';
import CandlestickChart, { type CandlestickChartHandle } from '@/components/CandlestickChart';
import MonteCarloSimulation from '@/components/MonteCarloSimulation';

export default function ResultsPage({ params }: { params: { id: string } }) {
  const jobId = parseInt(params.id);
  const chartRef = useRef<CandlestickChartHandle>(null);
  const queryClient = useQueryClient();

  const {
    data: report,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['backtest-report', jobId],
    queryFn: () => backtestApi.getReportByJob(jobId),
  });

  const [isFavorite, setIsFavorite] = useState<boolean | null>(null);

  const { data: favoriteStatus } = useQuery({
    queryKey: ['job-favorite', jobId],
    queryFn: async () => {
      const res = await fetch(`http://localhost:8000/api/v1/backtest/jobs/${jobId}`);
      const data = await res.json();
      return data.job?.is_favorite ?? false;
    },
    staleTime: 30000,
  });

  const currentFavorite = isFavorite ?? favoriteStatus ?? false;

  const toggleFavoriteMutation = useMutation({
    mutationFn: () => historyApi.toggleBacktestFavorite(jobId),
    onMutate: () => {
      setIsFavorite((prev) => (prev === null ? !currentFavorite : !prev));
    },
    onSuccess: (data) => {
      setIsFavorite(data.is_favorite);
      queryClient.invalidateQueries({ queryKey: ['job-favorite', jobId] });
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
    },
    onError: () => {
      setIsFavorite(null);
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-10 bg-gray-200 rounded w-1/4 mb-8"></div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="bg-white rounded-lg shadow-md p-6">
                  <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded w-3/4"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Report</h2>
            <p className="text-red-600">
              {error instanceof Error ? error.message : 'An unexpected error occurred'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-gray-600">No report data available</p>
        </div>
      </div>
    );
  }

  const {
    summary,
    monthly_returns,
    trade_analysis,
    equity_curve,
    strategy_name,
    parameters,
    dataset,
    backtest_start_time,
    backtest_end_time,
  } = report;

  const metrics = [
    {
      label: 'Total Return',
      value: `${summary.total_return >= 0 ? '+' : ''}${(summary.total_return * 100).toFixed(2)}%`,
      color: summary.total_return >= 0 ? 'text-green-600' : 'text-red-600',
    },
    {
      label: 'Final Value',
      value: `$${summary.final_value.toLocaleString()}`,
      color: 'text-gray-900',
    },
    {
      label: 'Sharpe Ratio',
      value: summary.sharpe_ratio.toFixed(2),
      color: 'text-blue-600',
    },
    {
      label: 'Max Drawdown',
      value: `-${(summary.max_drawdown * 100).toFixed(2)}%`,
      color: 'text-red-600',
    },
    {
      label: 'Win Rate',
      value: `${(summary.win_rate * 100).toFixed(1)}%`,
      color: 'text-gray-900',
    },
    {
      label: 'Profit Factor',
      value: summary.profit_factor.toFixed(2),
      color: 'text-gray-900',
    },
    {
      label: 'Total Trades',
      value: summary.total_trades.toString(),
      color: 'text-gray-900',
    },
    {
      label: 'Avg Trade',
      value: `${summary.avg_trade >= 0 ? '+' : ''}$${summary.avg_trade.toFixed(2)}`,
      color: summary.avg_trade >= 0 ? 'text-green-600' : 'text-red-600',
    },
  ];

  const analysisMetrics = [
    {
      label: 'Long Trades',
      value: trade_analysis.long_trades,
      color: 'text-green-600',
    },
    {
      label: 'Short Trades',
      value: trade_analysis.short_trades,
      color: 'text-red-600',
    },
    {
      label: 'Avg Hold Time',
      value: `${trade_analysis.avg_hold_time.toFixed(1)}h`,
      color: 'text-gray-900',
    },
    {
      label: 'Best Trade',
      value: `+$${trade_analysis.best_trade.toFixed(2)}`,
      color: 'text-green-600',
    },
    {
      label: 'Worst Trade',
      value: `-$${Math.abs(trade_analysis.worst_trade).toFixed(2)}`,
      color: 'text-red-600',
    },
    {
      label: 'Avg Winning',
      value: `+$${summary.avg_winning_trade.toFixed(2)}`,
      color: 'text-green-600',
    },
    {
      label: 'Avg Losing',
      value: `-$${Math.abs(summary.avg_losing_trade).toFixed(2)}`,
      color: 'text-red-600',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Backtest Results</h1>
          <button
            onClick={() => toggleFavoriteMutation.mutate()}
            disabled={toggleFavoriteMutation.isPending}
            className={`p-2 rounded-lg transition-colors ${
              currentFavorite
                ? 'bg-amber-100 text-amber-500 hover:bg-amber-200'
                : 'text-gray-300 hover:bg-gray-100 hover:text-gray-400'
            }`}
            title={currentFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-7 w-7"
              viewBox="0 0 24 24"
              fill={currentFavorite ? 'currentColor' : 'none'}
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </button>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {metrics.map((metric, index) => (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <p className="text-sm text-gray-600 mb-1">{metric.label}</p>
              <p className={`text-2xl font-bold ${metric.color}`}>{metric.value}</p>
            </div>
          ))}
        </div>

        {/* Additional Analysis */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Trade Analysis Summary</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {analysisMetrics.map((metric, index) => (
              <div key={index}>
                <p className="text-xs text-gray-600 mb-1">{metric.label}</p>
                <p className={`text-lg font-semibold ${metric.color}`}>{metric.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* NEW: Configuration Section */}
        <ConfigurationSection
          strategyName={strategy_name}
          parameters={parameters}
          dataset={dataset}
          backtestStartTime={backtest_start_time}
          backtestEndTime={backtest_end_time}
        />

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <EquityCurve data={equity_curve} />
          <MonthlyReturns data={monthly_returns} />
        </div>

        {/* Candlestick Chart with Trade Markers */}
        <CandlestickChart ref={chartRef} trades={trade_analysis.trades} dataset={dataset ?? null} initialCash={summary.final_value / (1 + summary.total_return)} />

        {/* Monte Carlo Simulation */}
        <div className="mb-8">
          <MonteCarloSimulation
            jobId={jobId}
            initialCash={summary.final_value / (1 + summary.total_return)}
          />
        </div>

        {/* Trade Table */}
        <TradeTable
          trades={trade_analysis.trades}
          initialCash={summary.final_value / (1 + summary.total_return)}
          onTradeClick={(trade) => chartRef.current?.scrollToTrade(trade)}
        />
      </div>
    </div>
  );
}
