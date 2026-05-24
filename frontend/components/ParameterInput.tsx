'use client';

import { StrategyParameter } from '@/lib/api/strategies';

interface Props {
  name: string;
  param: StrategyParameter;
  value: any;
  onChange: (name: string, value: any) => void;
}

export default function ParameterInput({ name, param, value, onChange }: Props) {
  const inputId = `param-${name}`;

  switch (param.type) {
    case 'int':
      return (
        <div>
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
            {name} {param.description && <span className="text-gray-500">({param.description})</span>}
          </label>
          <input
            id={inputId}
            type="number"
            value={value ?? param.default ?? ''}
            onChange={(e) => {
              const parsed = parseInt(e.target.value);
              if (!isNaN(parsed)) {
                onChange(name, parsed);
              }
            }}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {(param.min !== undefined || param.max !== undefined) && (
            <p className="text-xs text-gray-500 mt-1">
              Suggested range: {param.min !== undefined ? param.min : '−∞'} to {param.max !== undefined ? param.max : '∞'}
            </p>
          )}
        </div>
      );

    case 'float':
      return (
        <div>
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
            {name} {param.description && <span className="text-gray-500">({param.description})</span>}
          </label>
          <input
            id={inputId}
            type="number"
            step="0.01"
            value={value ?? param.default ?? ''}
            onChange={(e) => {
              const parsed = parseFloat(e.target.value);
              if (!isNaN(parsed)) {
                onChange(name, parsed);
              }
            }}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {(param.min !== undefined || param.max !== undefined) && (
            <p className="text-xs text-gray-500 mt-1">
              Suggested range: {param.min !== undefined ? param.min : '−∞'} to {param.max !== undefined ? param.max : '∞'}
            </p>
          )}
        </div>
      );

    case 'bool':
      return (
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              id={inputId}
              type="checkbox"
              checked={value ?? param.default ?? false}
              onChange={(e) => onChange(name, e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="ml-3 text-sm">
            <label htmlFor={inputId} className="font-medium text-gray-700">
              {name}
            </label>
            {param.description && (
              <p className="text-gray-500">{param.description}</p>
            )}
          </div>
        </div>
      );

    case 'str':
      if (param.choices && param.choices.length > 0) {
        return (
          <div>
            <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
              {name} {param.description && <span className="text-gray-500">({param.description})</span>}
            </label>
            <select
              id={inputId}
              value={value ?? param.default ?? ''}
              onChange={(e) => onChange(name, e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {param.choices.map((choice) => (
                <option key={choice} value={choice}>
                  {choice}
                </option>
              ))}
            </select>
          </div>
        );
      }
      return (
        <div>
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
            {name} {param.description && <span className="text-gray-500">({param.description})</span>}
          </label>
          <input
            id={inputId}
            type="text"
            value={value ?? param.default ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      );

    default:
      return (
        <div>
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
            {name} {param.description && <span className="text-gray-500">({param.description})</span>}
          </label>
          <input
            id={inputId}
            type="text"
            value={value ?? param.default ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      );
  }
}
