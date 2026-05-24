'use client';

import { BacktestHistoryItem } from '@/lib/api/history';
import { formatDate, formatDateTime } from '@/lib/utils/dateFormat';

interface Props {
  data: BacktestHistoryItem[];
  onDelete: (jobId: number) => void;
  onView: (jobId: number) => void;
  onToggleFavorite: (jobId: number) => void;
}

function formatPercent(value: number | undefined): string {
  if (value === undefined) return '-';
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

function formatDrawdown(value: number | undefined): string {
  if (value === undefined) return '-';
  return `-${(value * 100).toFixed(2)}%`;
}

function getStatusBadge(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400';
    case 'failed':
      return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400';
    case 'running':
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400';
    case 'pending':
    default:
      return 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-400';
  }
}

export default function BacktestHistoryTable({ data, onDelete, onView, onToggleFavorite }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
        <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">
          Backtest History
        </h3>
        <p className="text-slate-500 dark:text-slate-400 text-center py-12">
          No backtest history available
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
      <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">
        Backtest History
      </h3>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
          <thead className="bg-slate-50 dark:bg-slate-900/50">
            <tr>
              <th className="px-3 py-3 text-center text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                <span title="Favorite">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                </span>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                ID
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Strategy
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Market / Period
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-3 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Return
              </th>
              <th className="px-3 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Sharpe
              </th>
              <th className="px-3 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Drawdown
              </th>
              <th className="px-3 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Trades
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Created
              </th>
              <th className="px-3 py-3 text-center text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
            {data.map((item, index) => (
              <tr
                key={item.job_id}
                className={`hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${
                  index % 2 === 1 ? 'bg-slate-50/50 dark:bg-slate-900/20' : ''
                }`}
              >
                <td className="px-3 py-3 whitespace-nowrap text-sm text-center">
                  <button
                    onClick={() => onToggleFavorite(item.job_id)}
                    className="p-1 rounded transition-colors hover:bg-slate-100 dark:hover:bg-slate-700"
                    title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className={`h-5 w-5 transition-colors ${
                        item.is_favorite
                          ? 'text-amber-400'
                          : 'text-slate-300 dark:text-slate-600'
                      }`}
                      viewBox="0 0 24 24"
                      fill={item.is_favorite ? 'currentColor' : 'none'}
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                  </button>
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400 font-mono">
                  #{item.job_id}
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                  {item.strategy_name}
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                  <div>{item.symbol} / {item.interval}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {formatDate(item.start_time)} ~ {formatDate(item.end_time)}
                  </div>
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium capitalize ${getStatusBadge(
                      item.status
                    )}`}
                  >
                    {item.status}
                  </span>
                </td>
                <td
                  className={`px-3 py-3 whitespace-nowrap text-sm text-right font-semibold ${
                    item.total_return === undefined
                      ? 'text-slate-500 dark:text-slate-400'
                      : item.total_return >= 0
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatPercent(item.total_return)}
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100 text-right">
                  {item.sharpe_ratio != null ? item.sharpe_ratio.toFixed(2) : '-'}
                </td>
                <td
                  className={`px-3 py-3 whitespace-nowrap text-sm text-right ${
                    item.max_drawdown === undefined
                      ? 'text-slate-500 dark:text-slate-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatDrawdown(item.max_drawdown)}
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100 text-right">
                  {item.total_trades ?? '-'}
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                  {formatDateTime(item.created_at)}
                </td>
                <td className="px-3 py-3 whitespace-nowrap text-sm text-center">
                  <div className="flex items-center justify-center gap-1">
                    <button
                      onClick={() => onView(item.job_id)}
                      disabled={item.status.toLowerCase() !== 'completed'}
                      className="p-1.5 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title={item.status.toLowerCase() !== 'completed' ? 'Results not available yet' : 'View results'}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => onDelete(item.job_id)}
                      disabled={item.status.toLowerCase() === 'running'}
                      className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title={
                        item.status.toLowerCase() === 'running'
                          ? 'Cannot delete running job'
                          : 'Delete this backtest'
                      }
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
