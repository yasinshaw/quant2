'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import BacktestForm from '@/components/BacktestForm';
import { BacktestResult } from '@/lib/api/backtest';
import { formatDate } from '@/lib/utils/dateFormat';

export default function BacktestPage() {
  const router = useRouter();
  const [result, setResult] = useState<BacktestResult | null>(null);

  const handleResult = (backtestResult: BacktestResult) => {
    setResult(backtestResult);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Run Backtest</h1>
          <p className="text-gray-600 mt-2">
            Configure and run backtests for your trading strategies
          </p>
        </div>

        <BacktestForm onResult={handleResult} />

        {result && (
          <div className="mt-8 bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Backtest Results</h2>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-500">
                  ID: {result.id}
                </span>
                <button
                  onClick={() => router.push(`/results/${result.backtest_job_id}`)}
                  className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors duration-200 shadow-sm hover:shadow-md"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  View Details
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Total Return</p>
                <p className={`text-2xl font-bold ${(result.total_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(result.total_return ?? 0) >= 0 ? '+' : ''}{(result.total_return ?? 0).toFixed(2)}%
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Total Trades</p>
                <p className="text-2xl font-bold text-gray-900">{result.total_trades ?? 0}</p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Win Rate</p>
                <p className="text-2xl font-bold text-gray-900">{(result.win_rate ?? 0).toFixed(1)}%</p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Sharpe Ratio</p>
                <p className="text-2xl font-bold text-gray-900">{(result.sharpe_ratio ?? 0).toFixed(2)}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Initial Cash</p>
                <p className="text-lg font-semibold text-gray-900">
                  ${(result.initial_cash ?? 0).toLocaleString()}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Final Value</p>
                <p className="text-lg font-semibold text-gray-900">
                  ${(result.final_value ?? 0).toLocaleString()}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Max Drawdown</p>
                <p className="text-lg font-semibold text-red-600">
                  -{(result.max_drawdown ?? 0).toFixed(2)}%
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Profit Factor</p>
                <p className="text-lg font-semibold text-gray-900">
                  {(result.profit_factor ?? 0).toFixed(2)}
                </p>
              </div>
            </div>

            <div className="border-t pt-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Configuration</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Strategy:</span>
                  <p className="font-medium text-gray-900">{result.strategy_name}</p>
                </div>
                <div>
                  <span className="text-gray-600">Symbol:</span>
                  <p className="font-medium text-gray-900">{result.symbol}</p>
                </div>
                <div>
                  <span className="text-gray-600">Interval:</span>
                  <p className="font-medium text-gray-900">{result.interval}</p>
                </div>
                <div>
                  <span className="text-gray-600">Start Time:</span>
                  <p className="font-medium text-gray-900">
                    {formatDate(result.start_time)}
                  </p>
                </div>
                <div>
                  <span className="text-gray-600">End Time:</span>
                  <p className="font-medium text-gray-900">
                    {formatDate(result.end_time)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
