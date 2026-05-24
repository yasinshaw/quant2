'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { optimizationApi } from '@/lib/api/optimization';
import { formatDateTime } from '@/lib/utils/dateFormat';

interface OptimizationResultDetail {
  id: number;
  parameters: Record<string, any>;
  score: number;
  total_return?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  profit_factor?: number;
  total_trades?: number;
  final_value?: number;
  initial_cash?: number;
}

interface OptimizationResultsResponse {
  job_id: number;
  job_details: {
    strategy_name: string;
    symbol: string;
    interval: string;
    start_time: string;
    end_time: string;
    status: string;
    optimization_method: string;
    created_at: string;
    completed_at?: string;
  };
  results: OptimizationResultDetail[];
  total_results: number;
}

export default function OptimizationResultsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const { data, isLoading, error } = useQuery({
    queryKey: ['optimization-results', jobId],
    queryFn: () => optimizationApi.getResults(parseInt(jobId)),
    enabled: !!jobId,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
        <p className="text-center text-slate-500 dark:text-slate-400 mt-4">Loading optimization results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-red-800 dark:text-red-400 mb-2">Error</h2>
          <p className="text-red-600 dark:text-red-500">Failed to load optimization results. Please try again.</p>
          <button
            onClick={() => router.push('/history')}
            className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Back to History
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { job_details, results, total_results } = data as OptimizationResultsResponse;

  const exportToJSON = () => {
    if (!results || results.length === 0) return;

    const sortedResults = [...results].sort((a, b) => b.score - a.score);
    const exportData = {
      job_id: parseInt(jobId),
      strategy_name: job_details.strategy_name,
      exported_at: new Date().toISOString(),
      results: sortedResults.map((r, idx) => ({
        rank: idx + 1,
        parameters: r.parameters,
        score: r.score,
        total_return: r.total_return,
        sharpe_ratio: r.sharpe_ratio,
        max_drawdown: r.max_drawdown,
        win_rate: r.win_rate,
        total_trades: r.total_trades,
        profit_factor: r.profit_factor,
      })),
    };

    const jsonContent = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    const date = new Date().toISOString().split('T')[0];
    link.setAttribute('href', url);
    link.setAttribute('download', `${date}_${job_details.strategy_name}_optimization_${jobId}.json`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push('/history')}
          className="text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 mb-4 transition-colors"
        >
          ← Back to History
        </button>
        <h1 className="text-3xl font-heading font-bold text-slate-900 dark:text-slate-100 mb-2">
          Optimization Results #{jobId}
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          {job_details.strategy_name} - {job_details.symbol} ({job_details.interval})
        </p>
      </div>

      {/* Job Details */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700 mb-6">
        <h2 className="text-xl font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">
          Job Details
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-slate-600 dark:text-slate-400">Status:</span>
            <span className={`ml-2 px-2 py-1 rounded text-xs font-medium capitalize ${
              job_details.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400' :
              job_details.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400' :
              'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-400'
            }`}>
              {job_details.status}
            </span>
          </div>
          <div>
            <span className="text-slate-600 dark:text-slate-400">Method:</span>
            <span className="ml-2 font-medium text-slate-900 dark:text-slate-100 capitalize">{job_details.optimization_method}</span>
          </div>
          <div>
            <span className="text-slate-600 dark:text-slate-400">Total Results:</span>
            <span className="ml-2 font-medium text-slate-900 dark:text-slate-100">{total_results}</span>
          </div>
          <div>
            <span className="text-slate-600 dark:text-slate-400">Completed:</span>
            <span className="ml-2 font-medium text-slate-900 dark:text-slate-100">
              {job_details.completed_at ? formatDateTime(job_details.completed_at) : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-xl font-heading font-bold text-slate-900 dark:text-slate-100">
            Parameter Combinations ({total_results})
          </h2>
          {results.length > 0 && (
            <button
              onClick={exportToJSON}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export JSON
            </button>
          )}
        </div>

        {results.length === 0 ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            No results available
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
              <thead className="bg-slate-50 dark:bg-slate-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Parameters
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Total Return
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Sharpe Ratio
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Max Drawdown
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
                {results.map((result, index) => (
                  <tr
                    key={result.id}
                    className={`hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${
                      index === 0 ? 'bg-emerald-50 dark:bg-emerald-900/10' : ''
                    }`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {index === 0 && (
                          <span className="text-lg mr-2">🏆</span>
                        )}
                        <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          #{index + 1}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-slate-900 dark:text-slate-100">
                        {Object.entries(result.parameters).map(([key, value]) => (
                          <div key={key} className="mb-1">
                            <span className="font-medium">{key}:</span>{' '}
                            <span className="text-slate-600 dark:text-slate-400">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {result.score.toFixed(4)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                      {result.total_return !== undefined && result.total_return !== null
                        ? `${(result.total_return * 100).toFixed(2)}%`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                      {result.sharpe_ratio !== undefined && result.sharpe_ratio !== null
                        ? result.sharpe_ratio.toFixed(2)
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                      {result.max_drawdown !== undefined && result.max_drawdown !== null
                        ? `-${(result.max_drawdown * 100).toFixed(2)}%`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
