'use client';

import React, { useState } from 'react';
import { formatDisplayDate } from '@/lib/utils/dateFormat';

interface Dataset {
  id: number;
  name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  candle_count: number;
}

interface ConfigurationSectionProps {
  strategyName: string;
  parameters: Record<string, any>;
  dataset?: Dataset | null;
  backtestStartTime?: string;
  backtestEndTime?: string;
}

/**
 * Displays the strategy configuration used for a backtest.
 * Shows the strategy name, dataset information, and all parameters with their values.
 */
export default function ConfigurationSection({
  strategyName,
  parameters,
  dataset,
  backtestStartTime,
  backtestEndTime
}: ConfigurationSectionProps) {
  const [paramsCollapsed, setParamsCollapsed] = useState(true);

  const displayName = strategyName || 'N/A';

  // Format parameter values for display
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) {
      return 'N/A';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">Configuration</h2>
        <button
          onClick={() => {
            const exportData = {
              strategy_name: strategyName || 'strategy',
              exported_at: new Date().toISOString(),
              parameters,
            };
            const jsonContent = JSON.stringify(exportData, null, 2);
            const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${strategyName || 'strategy'}_params_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export Params
        </button>
      </div>

      {/* Strategy and Dataset Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        {/* Strategy Name */}
        <div>
          <p className="text-sm text-gray-600 mb-1">Strategy</p>
          <p className="text-lg font-semibold text-blue-600">
            {displayName}
          </p>
        </div>

        {/* Dataset Information */}
        {dataset ? (
          <>
            <div>
              <p className="text-sm text-gray-600 mb-1">Dataset</p>
              <p className="text-base font-medium text-gray-900">
                {dataset.name}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Backtest Period</p>
              <p className="text-base font-medium text-gray-900">
                {backtestStartTime && backtestEndTime
                  ? `${formatDisplayDate(backtestStartTime)} ~ ${formatDisplayDate(backtestEndTime)}`
                  : `${formatDisplayDate(dataset.start_time)} ~ ${formatDisplayDate(dataset.end_time)}`}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Dataset Range</p>
              <p className="text-base font-medium text-gray-500">
                {formatDisplayDate(dataset.start_time)} ~ {formatDisplayDate(dataset.end_time)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Data Points</p>
              <p className="text-base font-medium text-gray-900">
                {dataset.candle_count.toLocaleString()} candles
              </p>
            </div>
          </>
        ) : (
          <div className="md:col-span-3">
            <p className="text-sm text-gray-500">No dataset information available</p>
          </div>
        )}
      </div>

      {/* Parameters */}
      {parameters && Object.keys(parameters).length > 0 && (
        <div className="border-t border-gray-200 pt-4">
          <button
            type="button"
            onClick={() => setParamsCollapsed(v => !v)}
            className="flex items-center justify-between w-full group"
          >
            <p className="text-sm text-gray-600">
              Strategy Parameters
              <span className="text-xs text-gray-400 ml-1.5">
                {Object.keys(parameters).length} params
              </span>
            </p>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${!paramsCollapsed ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {!paramsCollapsed && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
              {Object.entries(parameters).map(([key, value]) => (
                <div key={key} className="bg-gray-50 rounded p-3">
                  <p className="text-xs text-gray-500">{key}</p>
                  <p className="text-sm font-medium text-gray-900">
                    {formatValue(value)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
