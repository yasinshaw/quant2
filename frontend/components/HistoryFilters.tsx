'use client';

import { HistoryQueryParams } from '@/lib/api/history';

interface HistoryFiltersProps {
  filters: HistoryQueryParams;
  onFilterChange: (filters: HistoryQueryParams) => void;
  onClear: () => void;
  strategies?: string[];
  symbols?: string[];
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Created At' },
  { value: 'total_return', label: 'Return' },
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
];

export default function HistoryFilters({
  filters,
  onFilterChange,
  onClear,
  strategies = [],
  symbols = [],
}: HistoryFiltersProps) {
  const hasActiveFilters =
    filters.strategy_name || filters.symbol || filters.status || filters.is_favorite;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-4 border border-slate-200 dark:border-slate-700">
      <div className="flex flex-wrap gap-3 items-end">
        {/* Strategy Filter */}
        <div className="min-w-[140px] flex-1">
          <label
            htmlFor="filter-strategy"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
          >
            Strategy
          </label>
          <select
            id="filter-strategy"
            value={filters.strategy_name || ''}
            onChange={(e) =>
              onFilterChange({ ...filters, strategy_name: e.target.value || undefined })
            }
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          >
            <option value="">All Strategies</option>
            {strategies.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Symbol Filter */}
        <div className="min-w-[140px] flex-1">
          <label
            htmlFor="filter-symbol"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
          >
            Symbol
          </label>
          <select
            id="filter-symbol"
            value={filters.symbol || ''}
            onChange={(e) =>
              onFilterChange({ ...filters, symbol: e.target.value || undefined })
            }
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          >
            <option value="">All Symbols</option>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div className="min-w-[140px] flex-1">
          <label
            htmlFor="filter-status"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
          >
            Status
          </label>
          <select
            id="filter-status"
            value={filters.status || ''}
            onChange={(e) =>
              onFilterChange({ ...filters, status: e.target.value || undefined })
            }
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Sort By */}
        <div className="min-w-[130px]">
          <label
            htmlFor="filter-sort"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
          >
            Sort By
          </label>
          <select
            id="filter-sort"
            value={filters.sort_by || 'created_at'}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                sort_by: (e.target.value || 'created_at') as HistoryQueryParams['sort_by'],
              })
            }
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Sort Order Toggle */}
        <button
          type="button"
          onClick={() =>
            onFilterChange({
              ...filters,
              sort_order: filters.sort_order === 'desc' ? 'asc' : 'desc',
            })
          }
          className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent flex items-center justify-center gap-1.5"
        >
          {filters.sort_order === 'desc' ? (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              Desc
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
              </svg>
              Asc
            </>
          )}
        </button>

        {/* Favorites Toggle */}
        <button
          type="button"
          onClick={() =>
            onFilterChange({
              ...filters,
              is_favorite: filters.is_favorite ? undefined : true,
            })
          }
          className={`px-3 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent flex items-center justify-center gap-1.5 ${
            filters.is_favorite
              ? 'bg-amber-100 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-400'
              : 'border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill={filters.is_favorite ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          Favorites
        </button>

        {/* Clear Button */}
        <button
          type="button"
          onClick={onClear}
          disabled={!hasActiveFilters}
          className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
