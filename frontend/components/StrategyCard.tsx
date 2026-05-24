'use client';

import { Strategy } from '@/lib/api/strategies';

interface Props {
  strategy: Strategy;
  showHidden: boolean;
  onViewDetails: (strategy: Strategy) => void;
  onToggleVisibility: (strategy: Strategy) => void;
  isToggling: boolean;
}

export default function StrategyCard({ strategy, showHidden, onViewDetails, onToggleVisibility, isToggling }: Props) {
  const isHidden = strategy.is_hidden ?? false;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-all duration-200 border flex flex-col h-full ${isHidden ? 'border-amber-300 dark:border-amber-600 opacity-60' : 'border-slate-200 dark:border-slate-700'}`}>
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <h3 className="text-xl font-heading font-bold text-slate-900 dark:text-slate-100 mb-2">
            {strategy.name}
            {isHidden && (
              <span className="ml-2 text-xs font-medium bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded-full">
                Hidden
              </span>
            )}
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            <span className="font-semibold">Version:</span> {strategy.version}
          </p>
        </div>
        {showHidden && (
          <button
            onClick={() => onToggleVisibility(strategy)}
            disabled={isToggling}
            title={isHidden ? 'Show strategy' : 'Hide strategy'}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 shrink-0"
          >
            {isHidden ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            )}
          </button>
        )}
      </div>

      <p className="text-slate-700 dark:text-slate-300 mb-4 line-clamp-3 font-body flex-grow">{strategy.description}</p>

      {strategy.parameters && (
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          <span className="font-semibold">{Object.keys(strategy.parameters).length}</span> parameters
        </p>
      )}

      <div className="mt-auto pt-4 flex gap-2">
        <button
          onClick={() => onViewDetails(strategy)}
          className="flex-1 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white px-4 py-2 rounded-lg transition-all duration-200 font-medium shadow-sm hover:shadow-md"
        >
          View Details
        </button>
        {!showHidden && (
          <button
            onClick={() => onToggleVisibility(strategy)}
            disabled={isToggling}
            title="Hide strategy"
            className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
