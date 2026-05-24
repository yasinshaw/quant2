'use client';

import { Strategy, StrategyParameter } from '@/lib/api/strategies';

interface Props {
  strategy: Strategy | null;
  onClose: () => void;
}

function formatParameterType(param: StrategyParameter): string {
  let type = param.type;
  if (param.choices) {
    type += ` [${param.choices.join(', ')}]`;
  }
  if (param.required) {
    type += ' (required)';
  }
  return type;
}

function formatDefaultValue(param: StrategyParameter): string {
  if (param.default === undefined || param.default === null) {
    return 'None';
  }
  if (typeof param.default === 'object') {
    return JSON.stringify(param.default);
  }
  return String(param.default);
}

export default function StrategyDetailModal({ strategy, onClose }: Props) {
  if (!strategy) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-600 hover:text-gray-900 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 transition-colors"
          aria-label="Close"
        >
          ×
        </button>

        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{strategy.name}</h2>
          <p className="text-sm text-gray-600">
            <span className="font-semibold">Version:</span> {strategy.version}
          </p>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
          <p className="text-gray-700">{strategy.description}</p>
        </div>

        {strategy.parameters && Object.keys(strategy.parameters).length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Parameters ({Object.keys(strategy.parameters).length})
            </h3>
            <div className="space-y-4">
              {Object.entries(strategy.parameters).map(([name, param]) => (
                <div
                  key={name}
                  className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-semibold text-gray-900">{name}</h4>
                    <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                      {formatParameterType(param)}
                    </span>
                  </div>

                  {param.description && (
                    <p className="text-sm text-gray-600 mb-2">{param.description}</p>
                  )}

                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-600 font-medium">Default:</span>{' '}
                      <span className="text-gray-900">{formatDefaultValue(param)}</span>
                    </div>
                    {param.min !== undefined && (
                      <div>
                        <span className="text-gray-600 font-medium">Min:</span>{' '}
                        <span className="text-gray-900">{param.min}</span>
                      </div>
                    )}
                    {param.max !== undefined && (
                      <div>
                        <span className="text-gray-600 font-medium">Max:</span>{' '}
                        <span className="text-gray-900">{param.max}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!strategy.parameters || Object.keys(strategy.parameters).length === 0 ? (
          <div className="text-gray-600 text-center py-4 bg-gray-50 rounded-lg">
            No parameters defined for this strategy.
          </div>
        ) : null}
      </div>
    </div>
  );
}
