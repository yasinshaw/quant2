'use client';

import { ValidationResult } from '@/lib/utils/parameterValidator';
import { ImportRow } from '@/lib/utils/jsonParser';

interface Props {
  isOpen: boolean;
  importRow: ImportRow | null;
  validation: ValidationResult | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function JSONImportModal({
  isOpen,
  importRow,
  validation,
  onConfirm,
  onCancel,
}: Props) {
  if (!isOpen || !importRow || !validation) {
    return null;
  }

  const hasErrors = validation.errors.length > 0;
  const hasWarnings = validation.warnings.length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Import Parameters from JSON
          </h2>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {/* Status Message */}
          <div className={`rounded-lg p-4 ${
            hasErrors
              ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              : hasWarnings
              ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
              : 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
          }`}>
            <div className="flex items-start">
              <span className="text-2xl mr-3">
                {hasErrors ? '❌' : hasWarnings ? '⚠️' : '✅'}
              </span>
              <div>
                <p className={`font-semibold ${
                  hasErrors
                    ? 'text-red-800 dark:text-red-400'
                    : hasWarnings
                    ? 'text-yellow-800 dark:text-yellow-400'
                    : 'text-green-800 dark:text-green-400'
                }`}>
                  {hasErrors
                    ? `Validation Failed (${validation.errors.length} error${validation.errors.length > 1 ? 's' : ''})`
                    : hasWarnings
                    ? `Validation Passed with Warnings (${validation.warnings.length} warning${validation.warnings.length > 1 ? 's' : ''})`
                    : 'All Parameters Validated Successfully'}
                </p>
              </div>
            </div>
          </div>

          {/* Performance Metrics (if available) */}
          {(importRow.pnl !== undefined ||
            importRow.pnl_pct !== undefined ||
            importRow.sharpe_ratio !== undefined ||
            importRow.win_rate !== undefined) && (
            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Performance Metrics
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {importRow.pnl_pct !== undefined && (
                  <div>
                    <span className="text-slate-600 dark:text-slate-400">PnL %:</span>
                    <span className={`ml-2 font-semibold ${importRow.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {importRow.pnl_pct >= 0 ? '+' : ''}{(importRow.pnl_pct * 100).toFixed(2)}%
                    </span>
                  </div>
                )}
                {importRow.sharpe_ratio !== undefined && (
                  <div>
                    <span className="text-slate-600 dark:text-slate-400">Sharpe:</span>
                    <span className="ml-2 font-semibold text-slate-900 dark:text-slate-100">
                      {importRow.sharpe_ratio.toFixed(2)}
                    </span>
                  </div>
                )}
                {importRow.win_rate !== undefined && (
                  <div>
                    <span className="text-slate-600 dark:text-slate-400">Win Rate:</span>
                    <span className="ml-2 font-semibold text-slate-900 dark:text-slate-100">
                      {(importRow.win_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                {importRow.max_drawdown !== undefined && (
                  <div>
                    <span className="text-slate-600 dark:text-slate-400">Max DD:</span>
                    <span className="ml-2 font-semibold text-red-600">
                      -{(importRow.max_drawdown * 100).toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Parameters to Import */}
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
              Parameters to Import
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(importRow.parameters).map(([key, value]) => {
                const hasError = validation.errors.some(e => e.parameter === key);
                const hasWarning = validation.warnings.some(w => w.parameter === key);

                return (
                  <div
                    key={key}
                    className={`bg-white dark:bg-slate-800 rounded px-3 py-2 border ${
                      hasError
                        ? 'border-red-300 dark:border-red-700'
                        : hasWarning
                        ? 'border-yellow-300 dark:border-yellow-700'
                        : 'border-slate-200 dark:border-slate-700'
                    }`}
                  >
                    <p className="text-xs text-slate-600 dark:text-slate-400">{key}</p>
                    <p className={`text-sm font-semibold ${
                      hasError
                        ? 'text-red-600 dark:text-red-400'
                        : hasWarning
                        ? 'text-yellow-600 dark:text-yellow-400'
                        : 'text-slate-900 dark:text-slate-100'
                    }`}>
                      {String(value)}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Validation Details */}
          {(hasErrors || hasWarnings) && (
            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Validation Details
              </h3>
              <div className="space-y-2 text-sm">
                {validation.errors.map((error, idx) => (
                  <div key={idx} className="flex items-start text-red-700 dark:text-red-400">
                    <span className="mr-2">•</span>
                    <span>
                      <strong>{error.parameter}:</strong> {error.message}
                    </span>
                  </div>
                ))}
                {validation.warnings.map((warning, idx) => (
                  <div key={idx} className="flex items-start text-yellow-700 dark:text-yellow-400">
                    <span className="mr-2">•</span>
                    <span>
                      <strong>{warning.parameter}:</strong> {warning.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 px-6 py-4 flex justify-end space-x-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          {!hasErrors && (
            <button
              type="button"
              onClick={onConfirm}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white rounded-lg transition-colors font-medium"
            >
              Import Parameters
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
