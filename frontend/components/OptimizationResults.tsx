'use client';

import { useState } from 'react';
import { OptimizationResponse, StabilityReport } from '@/lib/api/optimization';

interface Props {
  result: OptimizationResponse;
  stabilityReport?: StabilityReport;
  strategyName?: string;
}

type SortField = 'pnl_pct' | 'sharpe_ratio' | 'total_trades' | 'max_drawdown' | 'win_rate' | 'composite_score';
type SortOrder = 'asc' | 'desc';

export default function OptimizationResults({ result, stabilityReport, strategyName }: Props) {
  const [sortField, setSortField] = useState<SortField>('pnl_pct');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [showStability, setShowStability] = useState(false);

  const sortedResults = [...(result.results || [])].sort((a, b) => {
    // Prioritize composite_score if available
    const aScore = a.composite_score ?? a[sortField] ?? 0;
    const bScore = b.composite_score ?? b[sortField] ?? 0;
    return sortOrder === 'desc' ? bScore - aScore : aScore - bScore;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const exportToJSON = () => {
    if (!result.results || result.results.length === 0) return;

    const exportData = {
      job_id: result.job_id,
      strategy_name: strategyName || 'strategy',
      exported_at: new Date().toISOString(),
      results: sortedResults.map((r, idx) => ({
        rank: idx + 1,
        parameters: r.parameters,
        pnl: r.pnl,
        pnl_pct: r.pnl_pct,
        total_trades: r.total_trades,
        win_rate: r.win_rate,
        sharpe_ratio: r.sharpe_ratio,
        max_drawdown: r.max_drawdown,
        composite_score: r.composite_score,
        is_best: r.is_best,
      })),
    };

    const jsonContent = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    const date = new Date().toISOString().split('T')[0];
    const strategy = strategyName || 'strategy';
    link.setAttribute('download', `${date}_${strategy}_optimization_${result.job_id}.json`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <span className="text-gray-400 ml-1">⇅</span>;
    }
    return <span className="ml-1">{sortOrder === 'desc' ? '↓' : '↑'}</span>;
  };

  const getStabilityBadge = (score: number | null, isStable: boolean) => {
    if (score === null) {
      return <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-xs">Not Analyzed</span>;
    }
    if (isStable) {
      return <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Stable ({score.toFixed(2)})</span>;
    }
    return <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">Unstable ({score.toFixed(2)})</span>;
  };

  return (
    <div className="mt-8 space-y-6">
      {/* NEW: Stability Analysis Summary */}
      {stabilityReport && (
        <div className="bg-white rounded-lg shadow-md p-6 border-2 border-blue-500">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <span className="text-blue-500 mr-2">📊</span>
              Stability Analysis
            </h2>
            <button
              onClick={() => setShowStability(!showStability)}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              {showStability ? 'Hide Details' : 'Show Details'}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Stability Score</p>
              <p className="text-2xl font-bold text-gray-900">
                {stabilityReport.stability_score !== null ? stabilityReport.stability_score.toFixed(2) : 'N/A'}
              </p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Variance</p>
              <p className="text-2xl font-bold text-gray-900">
                {stabilityReport.variance !== null ? stabilityReport.variance.toFixed(4) : 'N/A'}
              </p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Assessment</p>
              <div className="text-2xl font-bold">
                {getStabilityBadge(stabilityReport.stability_score, stabilityReport.is_stable)}
              </div>
            </div>
          </div>

          {showStability && stabilityReport.neighbors && stabilityReport.neighbors.length > 0 && (
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Neighbor Parameter Tests</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Parameters</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">PnL %</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sharpe</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Max DD</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {stabilityReport.neighbors.map((neighbor, idx) => (
                      <tr key={idx}>
                        <td className="px-3 py-2 text-sm text-gray-900">
                          {Object.entries(neighbor.parameters).map(([k, v]) => `${k}=${v}`).join(', ')}
                        </td>
                        <td className="px-3 py-2 text-sm font-semibold text-gray-900">
                          {neighbor.score.toFixed(3)}
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-900">
                          {neighbor.pnl_pct?.toFixed(2) || 'N/A'}%
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-900">
                          {neighbor.sharpe_ratio?.toFixed(2) || 'N/A'}
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-900">
                          {neighbor.max_drawdown !== undefined && neighbor.max_drawdown !== null ? `${(neighbor.max_drawdown * 100).toFixed(2)}%` : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Best Result Summary */}
      <div className="bg-white rounded-lg shadow-md p-6 border-2 border-green-500">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 flex items-center">
            <span className="text-green-500 mr-2">★</span>
            Best Result
          </h2>
          <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
            Optimal Parameters
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">PnL</p>
            <p className={`text-2xl font-bold ${result.best_result.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ${result.best_result.pnl.toFixed(2)}
            </p>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">PnL %</p>
            <p className={`text-2xl font-bold ${result.best_result.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {result.best_result.pnl_pct >= 0 ? '+' : ''}{(result.best_result.pnl_pct * 100).toFixed(2)}%
            </p>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Total Trades</p>
            <p className="text-2xl font-bold text-gray-900">{result.best_result.total_trades}</p>
          </div>

          {/* NEW: Composite Score Display */}
          {result.best_result.composite_score !== undefined ? (
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Composite Score</p>
              <p className="text-2xl font-bold text-blue-600">
                {result.best_result.composite_score.toFixed(3)}
              </p>
            </div>
          ) : (
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Sharpe Ratio</p>
              <p className="text-2xl font-bold text-gray-900">
                {result.best_result.sharpe_ratio?.toFixed(2) || 'N/A'}
              </p>
            </div>
          )}
        </div>

        <div className="border-t pt-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Best Parameters</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(result.best_result.parameters).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded px-3 py-2">
                <p className="text-xs text-gray-600">{key}</p>
                <p className="text-sm font-semibold text-gray-900">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* All Results Table */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            All Parameter Combinations
          </h2>
          <button
            onClick={exportToJSON}
            disabled={!result.results || result.results.length === 0}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Export JSON
          </button>
        </div>

        {result.total_combinations && (
          <div className="mb-4 text-sm text-gray-600">
            Total combinations tested: <span className="font-semibold">{result.total_combinations}</span>
          </div>
        )}

        {result.results && result.results.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rank
                  </th>
                  {Object.keys(result.results[0]?.parameters || {}).map((paramName) => (
                    <th
                      key={paramName}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {paramName}
                    </th>
                  ))}
                  <th
                    onClick={() => handleSort('pnl_pct')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    PnL % <SortIcon field="pnl_pct" />
                  </th>
                  <th
                    onClick={() => handleSort('pnl_pct')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    PnL ($) <SortIcon field="pnl_pct" />
                  </th>
                  <th
                    onClick={() => handleSort('total_trades')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Trades <SortIcon field="total_trades" />
                  </th>
                  <th
                    onClick={() => handleSort('win_rate')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Win Rate <SortIcon field="win_rate" />
                  </th>
                  <th
                    onClick={() => handleSort('sharpe_ratio')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Sharpe <SortIcon field="sharpe_ratio" />
                  </th>
                  <th
                    onClick={() => handleSort('max_drawdown')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Max DD <SortIcon field="max_drawdown" />
                  </th>
                  {/* NEW: Composite Score Column */}
                  {result.results.some(r => r.composite_score !== undefined) && (
                    <th
                      onClick={() => handleSort('composite_score')}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Composite <SortIcon field="composite_score" />
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedResults.map((r, idx) => (
                  <tr
                    key={r.id}
                    className={r.is_best ? 'bg-green-50 hover:bg-green-100' : 'hover:bg-gray-50'}
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      {idx + 1}
                      {r.is_best && <span className="ml-1 text-green-600">★</span>}
                    </td>
                    {Object.values(r.parameters).map((value, i) => (
                      <td key={i} className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {String(value)}
                      </td>
                    ))}
                    <td className={`px-4 py-3 whitespace-nowrap text-sm font-semibold ${r.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {r.pnl_pct >= 0 ? '+' : ''}{(r.pnl_pct * 100).toFixed(2)}%
                    </td>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm font-semibold ${r.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ${r.pnl.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {r.total_trades}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {r.win_rate !== undefined && r.win_rate !== null ? `${(r.win_rate * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {r.sharpe_ratio?.toFixed(2) || 'N/A'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-red-600">
                      {r.max_drawdown !== undefined && r.max_drawdown !== null ? `-${(r.max_drawdown * 100).toFixed(2)}%` : 'N/A'}
                    </td>
                    {/* NEW: Composite Score Cell */}
                    {result.results?.some(res => res.composite_score !== undefined) && (
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-semibold text-blue-600">
                        {r.composite_score !== undefined ? r.composite_score.toFixed(3) : 'N/A'}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No results available
          </div>
        )}
      </div>
    </div>
  );
}
