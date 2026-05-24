'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { strategiesApi } from '@/lib/api/strategies';
import { dataApi, Dataset } from '@/lib/api/data';
import { OptimizationRequest, ScoringWeights, ParameterRange } from '@/lib/api/optimization';
import { SimpleDatePicker } from './DatePicker';
import { toast } from '@/lib/toast';
import DatasetSelector from './DatasetSelector';

interface ParameterConfig {
  optimize: boolean;
  fixedValue?: number;
  range?: {
    min: number;
    max: number;
    step: number;
  };
  strategyDefaultValue: number;
}

interface Props {
  onSubmit: (request: OptimizationRequest) => void;
  isLoading: boolean;
}

function ToggleSwitch({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
        checked ? 'bg-blue-600' : 'bg-gray-200'
      }`}
      aria-pressed={checked}
      aria-label={label}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition duration-200 ease-in-out ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

export default function OptimizationForm({ onSubmit, isLoading }: Props) {
  const [strategy, setStrategy] = useState('');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [interval, setInterval] = useState('1h');

  // Dataset states
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
  const [selectedDatasetData, setSelectedDatasetData] = useState<Dataset | null>(null);

  // 设置默认的日期值（格式：YYYY-MM-DD）
  // 时间将默认为开始00:00，结束23:59
  const getDefaultStartDate = () => {
    const now = new Date();
    now.setDate(now.getDate() - 30); // 默认30天前
    return now.toISOString().slice(0, 10);
  };

  const getDefaultEndDate = () => {
    const now = new Date();
    return now.toISOString().slice(0, 10);
  };

  const [startDate, setStartDate] = useState(getDefaultStartDate());
  const [endDate, setEndDate] = useState(getDefaultEndDate());

  // Helper to combine date and time for API
  const toDateTime = (dateStr: string, isEnd: boolean = false) => {
    const date = new Date(dateStr);
    if (isEnd) {
      date.setHours(23, 59, 0, 0);
    } else {
      date.setHours(0, 0, 0, 0);
    }
    // Format datetime without timezone conversion
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  // For compatibility, create computed startTime/endTime
  const startTime = toDateTime(startDate);
  const endTime = toDateTime(endDate, true);
  const [initialCash, setInitialCash] = useState(100000);
  const [parameterConfigs, setParameterConfigs] = useState<Record<string, ParameterConfig>>({});

  // NEW: Optimization method and advanced settings
  const [optimizationMethod, setOptimizationMethod] = useState<'grid' | 'bayesian'>('bayesian');
  const [nTrials, setNTrials] = useState(100);
  const [customScoring, setCustomScoring] = useState(false);
  const [scoringWeights, setScoringWeights] = useState<ScoringWeights>({
    sharpe_ratio: 0.3,
    total_return: 0.15,
    max_drawdown: -0.2,
    win_rate: 0.05,
    calmar_ratio: 0.3,
  });

  // NEW: Out-of-sample testing
  const [enableOutOfSample, setEnableOutOfSample] = useState(false);
  const [testStartDate, setTestStartDate] = useState('');
  const [testEndDate, setTestEndDate] = useState('');

  // Helper to convert test dates to datetime format
  const toTestDateTime = (dateStr: string, isEnd: boolean = false) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isEnd) {
      date.setHours(23, 59, 0, 0);
    } else {
      date.setHours(0, 0, 0, 0);
    }
    return date.toISOString().slice(0, 16);
  };

  // Computed values for compatibility
  const testStartTime = toTestDateTime(testStartDate);
  const testEndTime = toTestDateTime(testEndDate, true);

  // NEW: Stability analysis
  const [enableStabilityAnalysis, setEnableStabilityAnalysis] = useState(true);

  const { data: strategies, isLoading: strategiesLoading } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategiesApi.list(),
  });

  const selectedStrategyDetails = useQuery({
    queryKey: ['strategy', strategy],
    queryFn: () => strategiesApi.get(strategy),
    enabled: !!strategy,
  });

  useEffect(() => {
    if (selectedStrategyDetails.data?.parameters) {
      const configs: Record<string, ParameterConfig> = {};
      Object.entries(selectedStrategyDetails.data.parameters).forEach(([key, param]) => {
        if (param.type === 'int' || param.type === 'float') {
          // Default: ALL parameters are optimized
          const defaultValue = param.default ?? (param.type === 'int' ? 1 : 0.1);
          configs[key] = {
            optimize: true,
            range: {
              min: param.min ?? defaultValue * 0.5,
              max: param.max ?? defaultValue * 2,
              step: param.type === 'int' ? 1 : 0.1
            },
            strategyDefaultValue: defaultValue,
          };
        }
      });
      setParameterConfigs(configs);
    }
  }, [selectedStrategyDetails.data]);

  // Update test time range when training range changes
  useEffect(() => {
    if (enableOutOfSample && startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      const duration = end.getTime() - start.getTime();

      // Set test period to start after training period
      const testStart = new Date(end.getTime() + 1); // Start 1ms after training ends
      const testEnd = new Date(testStart.getTime() + duration); // Same duration as training

      setTestStartDate(testStart.toISOString().slice(0, 10));
      setTestEndDate(testEnd.toISOString().slice(0, 10));
    }
  }, [enableOutOfSample, startTime, endTime]);

  const totalCombinations = useMemo(() => {
    if (optimizationMethod === 'bayesian') {
      return nTrials;
    }
    return Object.values(parameterConfigs)
      .filter(config => config.optimize)
      .reduce((total, config) => {
        if (!config.range || config.range.step <= 0) return total;
        const count = Math.floor((config.range.max - config.range.min) / config.range.step) + 1;
        return total * Math.max(0, count);
      }, 1);
  }, [parameterConfigs, optimizationMethod, nTrials]);

  // Calculate optimization states for toggle buttons
  const allParamsOptimized = useMemo(() => {
    return Object.values(parameterConfigs).every(config => config.optimize);
  }, [parameterConfigs]);

  const noParamsOptimized = useMemo(() => {
    return Object.values(parameterConfigs).every(config => !config.optimize);
  }, [parameterConfigs]);

  // Enable optimization for all parameters
  const handleEnableAll = () => {
    setParameterConfigs(prev => {
      const updated = { ...prev };
      Object.keys(updated).forEach(key => {
        updated[key] = {
          ...updated[key],
          optimize: true,
          // Initialize range if not exists
          range: updated[key].range || {
            min: updated[key].strategyDefaultValue * 0.5,
            max: updated[key].strategyDefaultValue * 2,
            step: typeof updated[key].strategyDefaultValue === 'number' &&
                  Number.isInteger(updated[key].strategyDefaultValue) ? 1 : 0.1
          }
        };
      });
      return updated;
    });
  };

  // Disable optimization for all parameters
  const handleDisableAll = () => {
    setParameterConfigs(prev => {
      const updated = { ...prev };
      Object.keys(updated).forEach(key => {
        updated[key] = {
          ...updated[key],
          optimize: false
        };
      });
      return updated;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedDataset) {
      toast.error('Please select a dataset');
      return;
    }

    if (!startDate || !endDate) {
      toast.error('Please select both start and end dates');
      return;
    }

    const start = new Date(startDate);
    const end = new Date(endDate);

    if (start >= end) {
      toast.error('Start date must be before end date');
      return;
    }

    // Check if at least one parameter is optimized
    const hasOptimizedParams = Object.values(parameterConfigs).some(config => config.optimize);
    if (!hasOptimizedParams) {
      toast.error('Please enable at least one parameter for optimization');
      return;
    }

    // Build parameter_ranges based on optimization method
    let parameter_ranges: Record<string, any[] | ParameterRange> = {};
    const fixed_parameters: Record<string, any> = {};

    Object.entries(parameterConfigs).forEach(([name, config]) => {
      if (config.optimize) {
        if (optimizationMethod === 'bayesian') {
          // For Bayesian: use continuous range
          parameter_ranges[name] = {
            type: typeof config.strategyDefaultValue === 'number' && Number.isInteger(config.strategyDefaultValue) ? 'int' : 'float',
            min: config.range?.min ?? config.strategyDefaultValue * 0.5,
            max: config.range?.max ?? config.strategyDefaultValue * 2
          };
        } else {
          // For Grid: use discrete values
          if (!config.range) return;
          const values: number[] = [];
          for (let v = config.range.min; v <= config.range.max; v += config.range.step) {
            values.push(Number(v.toFixed(2)));
          }
          parameter_ranges[name] = values;
        }
      } else {
        // Use fixed value
        if (config.fixedValue !== undefined) {
          fixed_parameters[name] = config.fixedValue;
        }
      }
    });

    if (optimizationMethod === 'grid' && totalCombinations > 1000) {
      toast.error(`Too many combinations (${totalCombinations}). Please reduce parameter ranges or use Bayesian optimization.`);
      return;
    }

    // Format datetime without timezone conversion
    const formatDateTime = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
    };

    // Build optimization request
    const request: OptimizationRequest = {
      strategy_name: strategy,
      symbol,
      interval,
      start_time: formatDateTime(start),
      end_time: formatDateTime(end),
      parameter_ranges,
      fixed_parameters,
      initial_cash: initialCash,
      optimization_method: optimizationMethod,
      n_trials: optimizationMethod === 'bayesian' ? nTrials : undefined,
      enable_stability_analysis: enableStabilityAnalysis
    };

    // Add optional fields
    if (customScoring) {
      request.scoring_weights = scoringWeights;
    }

    if (enableOutOfSample && testStartTime && testEndTime) {
      request.enable_out_of_sample = true;
      request.test_start_time = formatDateTime(new Date(testStartTime));
      request.test_end_time = formatDateTime(new Date(testEndTime));
    }

    onSubmit(request);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 space-y-6">

      <div>
        <label htmlFor="strategy" className="block text-sm font-medium text-gray-700 mb-2">
          Strategy
        </label>
        <select
          id="strategy"
          value={strategy}
          onChange={(e) => {
            setStrategy(e.target.value);
            setParameterConfigs({});
          }}
          required
          disabled={strategiesLoading}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          <option value="">Select a strategy</option>
          {strategies?.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name} (v{s.version})
            </option>
          ))}
        </select>
        {selectedStrategyDetails.data?.description && (
          <p className="text-sm text-gray-600 mt-2">
            {selectedStrategyDetails.data.description}
          </p>
        )}
      </div>

      {/* Dataset Selector */}
      <DatasetSelector
        value={selectedDataset}
        onChange={(datasetId, dataset) => {
          setSelectedDataset(datasetId);
          setSelectedDatasetData(dataset);
          setSymbol(dataset.symbol);
          setInterval(dataset.interval);
          setStartDate(dataset.start_time.split('T')[0]);
          setEndDate(dataset.end_time.split('T')[0]);
        }}
        disabled={strategiesLoading || isLoading}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="relative">
          <label htmlFor="symbol" className="block text-sm font-medium text-gray-700 mb-2">
            Symbol
          </label>
          <div className="relative">
            <input
              id="symbol"
              type="text"
              value={symbol}
              readOnly
              className="w-full border border-gray-300 rounded-md px-3 py-2 pl-10 bg-gray-50 text-gray-700 cursor-not-allowed"
            />
            <svg className="absolute left-3 top-3 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        </div>

        <div className="relative">
          <label htmlFor="interval" className="block text-sm font-medium text-gray-700 mb-2">
            Interval
          </label>
          <div className="relative">
            <input
              id="interval"
              type="text"
              value={interval}
              readOnly
              className="w-full border border-gray-300 rounded-md px-3 py-2 pl-10 bg-gray-50 text-gray-700 cursor-not-allowed"
            />
            <svg className="absolute left-3 top-3 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SimpleDatePicker
          id="startTime"
          label="Start Date"
          value={startDate}
          onChange={setStartDate}
          required
          maxDate={endDate || new Date().toISOString().split('T')[0]}
        />

        <SimpleDatePicker
          id="endTime"
          label="End Date"
          value={endDate}
          onChange={setEndDate}
          required
          minDate={startDate}
          maxDate={new Date().toISOString().split('T')[0]}
        />
      </div>

      {/* Dataset range warning */}
      {selectedDatasetData && (
        <div className={`text-xs mb-2 ${
          startDate < selectedDatasetData.start_time.split('T')[0] ||
          endDate > selectedDatasetData.end_time.split('T')[0]
            ? 'text-orange-600'
            : 'text-gray-500'
        }`}>
          {startDate < selectedDatasetData.start_time.split('T')[0] ||
           endDate > selectedDatasetData.end_time.split('T')[0]
            ? '⚠️ Time range outside dataset bounds (will be clipped)'
            : `Dataset range: ${selectedDatasetData.start_time.split('T')[0]} ~ ${selectedDatasetData.end_time.split('T')[0]}`
          }
        </div>
      )}

      <div>
        <label htmlFor="initialCash" className="block text-sm font-medium text-gray-700 mb-2">
          Initial Cash ($)
        </label>
        <input
          id="initialCash"
          type="number"
          value={initialCash}
          onChange={(e) => {
            const value = parseFloat(e.target.value);
            if (!isNaN(value)) {
              setInitialCash(value);
            }
          }}
          min="1000"
          step="1000"
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* NEW: Advanced Optimization Settings */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Advanced Settings</h3>

        {/* Optimization Method */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Optimization Method
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setOptimizationMethod('grid')}
              className={`p-4 rounded-lg border-2 transition-colors ${
                optimizationMethod === 'grid'
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <div className="font-semibold">Grid Search</div>
              <div className="text-xs text-gray-600 mt-1">
                Test all combinations
              </div>
            </button>
            <button
              type="button"
              onClick={() => setOptimizationMethod('bayesian')}
              className={`p-4 rounded-lg border-2 transition-colors ${
                optimizationMethod === 'bayesian'
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <div className="font-semibold">Bayesian Optimization</div>
              <div className="text-xs text-gray-600 mt-1">
                Smart parameter search (requires Optuna)
              </div>
            </button>
          </div>
        </div>

        {/* Bayesian: Number of Trials */}
        {optimizationMethod === 'bayesian' && (
          <div className="mb-4">
            <label htmlFor="nTrials" className="block text-sm font-medium text-gray-700 mb-2">
              Number of Trials
            </label>
            <input
              id="nTrials"
              type="number"
              value={nTrials}
              onChange={(e) => setNTrials(parseInt(e.target.value) || 100)}
              min="10"
              max="1000"
              step="10"
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              More trials = better results but slower
            </p>
          </div>
        )}

        {/* Custom Scoring Weights */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Custom Scoring Weights
            </label>
            <ToggleSwitch
              checked={customScoring}
              onChange={setCustomScoring}
              label="Toggle custom scoring weights"
            />
          </div>

          {customScoring && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Sharpe Ratio (weight)</label>
                <input
                  type="number"
                  step="0.1"
                  value={scoringWeights.sharpe_ratio}
                  onChange={(e) => setScoringWeights({ ...scoringWeights, sharpe_ratio: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Total Return (weight)</label>
                <input
                  type="number"
                  step="0.1"
                  value={scoringWeights.total_return}
                  onChange={(e) => setScoringWeights({ ...scoringWeights, total_return: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Max Drawdown (negative weight)</label>
                <input
                  type="number"
                  step="0.1"
                  value={scoringWeights.max_drawdown}
                  onChange={(e) => setScoringWeights({ ...scoringWeights, max_drawdown: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Win Rate (weight)</label>
                <input
                  type="number"
                  step="0.1"
                  value={scoringWeights.win_rate}
                  onChange={(e) => setScoringWeights({ ...scoringWeights, win_rate: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Calmar Ratio (weight)</label>
                <input
                  type="number"
                  step="0.1"
                  value={scoringWeights.calmar_ratio ?? 0}
                  onChange={(e) => setScoringWeights({ ...scoringWeights, calmar_ratio: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <p className="text-xs text-gray-500">
                Weights should sum to approximately 1.0 (ignoring negative signs)
              </p>
            </div>
          )}
        </div>

        {/* Out-of-Sample Testing */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Out-of-Sample Testing
              </label>
              <p className="text-xs text-gray-500">
                Validate parameters on unseen data to detect overfitting
              </p>
            </div>
            <ToggleSwitch
              checked={enableOutOfSample}
              onChange={setEnableOutOfSample}
              label="Toggle out-of-sample testing"
            />
          </div>

          {enableOutOfSample && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SimpleDatePicker
                  id="testStartTime"
                  label="Test Start Date"
                  value={testStartDate}
                  onChange={setTestStartDate}
                  maxDate={testEndDate || new Date().toISOString().split('T')[0]}
                />

                <SimpleDatePicker
                  id="testEndTime"
                  label="Test End Date"
                  value={testEndDate}
                  onChange={setTestEndDate}
                  minDate={testStartDate}
                  maxDate={new Date().toISOString().split('T')[0]}
                />
              </div>
            </div>
          )}
        </div>

        {/* Stability Analysis */}
        <div className="flex items-center justify-between">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Stability Analysis
            </label>
            <p className="text-xs text-gray-500">
              Test parameter robustness to detect overfitting
            </p>
          </div>
          <ToggleSwitch
            checked={enableStabilityAnalysis}
            onChange={setEnableStabilityAnalysis}
            label="Toggle stability analysis"
          />
        </div>
      </div>

      {Object.keys(parameterConfigs).length > 0 && (
        <div className="border-t pt-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Parameters</h3>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-600">
                {optimizationMethod === 'bayesian' ? (
                  <span>Trials: <span className="font-bold text-blue-600">{totalCombinations}</span></span>
                ) : (
                  <span>Combinations: <span className="font-bold text-blue-600">{totalCombinations}</span></span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleEnableAll}
                  disabled={allParamsOptimized}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  全部开启
                </button>
                <button
                  type="button"
                  onClick={handleDisableAll}
                  disabled={noParamsOptimized}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  全部关闭
                </button>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            {Object.entries(parameterConfigs).map(([name, config]) => (
              <div key={name} className="bg-gray-50 rounded-lg p-4" data-testid="parameter-config">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-gray-800">{name}</h4>
                  <ToggleSwitch
                    checked={config.optimize}
                    onChange={(checked) => {
                      setParameterConfigs((prev) => ({
                        ...prev,
                        [name]: {
                          ...prev[name],
                          optimize: checked,
                          // Initialize range if enabling optimization
                          range: checked ? (prev[name].range || {
                            min: prev[name].strategyDefaultValue * 0.5,
                            max: prev[name].strategyDefaultValue * 2,
                            step: typeof prev[name].strategyDefaultValue === 'number' &&
                                  Number.isInteger(prev[name].strategyDefaultValue) ? 1 : 0.1
                          }) : undefined
                        }
                      }));
                    }}
                    label={`Toggle optimization for ${name}`}
                  />
                </div>

                {config.optimize ? (
                  // Optimized: Show Min/Max/Step inputs
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Min</label>
                      <input
                        type="number"
                        value={config.range?.min ?? ''}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          if (!isNaN(value)) {
                            setParameterConfigs((prev) => ({
                              ...prev,
                              [name]: {
                                ...prev[name],
                                range: { ...prev[name].range!, min: value }
                              }
                            }));
                          }
                        }}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Max</label>
                      <input
                        type="number"
                        value={config.range?.max ?? ''}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          if (!isNaN(value)) {
                            setParameterConfigs((prev) => ({
                              ...prev,
                              [name]: {
                                ...prev[name],
                                range: { ...prev[name].range!, max: value }
                              }
                            }));
                          }
                        }}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    {optimizationMethod === 'grid' && (
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Step</label>
                        <input
                          type="number"
                          step="0.01"
                          value={config.range?.step ?? ''}
                          onChange={(e) => {
                            const value = parseFloat(e.target.value);
                            if (!isNaN(value)) {
                              setParameterConfigs((prev) => ({
                                ...prev,
                                [name]: {
                                  ...prev[name],
                                  range: { ...prev[name].range!, step: value }
                                }
                              }));
                            }
                          }}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  // Fixed: Show single value input with hint
                  <div>
                    <input
                      type="number"
                      value={config.fixedValue ?? ''}
                      onChange={(e) => {
                        const value = parseFloat(e.target.value);
                        if (!isNaN(value)) {
                          setParameterConfigs((prev) => ({
                            ...prev,
                            [name]: {
                              ...prev[name],
                              fixedValue: value
                            }
                          }));
                        }
                      }}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Strategy default: {config.strategyDefaultValue}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedStrategyDetails.data && Object.keys(parameterConfigs).length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-md">
          This strategy has no numeric parameters available for optimization.
        </div>
      )}

      <button
        type="submit"
        disabled={!strategy || !selectedDataset || isLoading || Object.keys(parameterConfigs).length === 0}
        className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors duration-200"
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Running Optimization...
          </span>
        ) : (
          `Run Optimization (${optimizationMethod === 'bayesian' ? `${nTrials} trials` : `${totalCombinations} combinations`})`
        )}
      </button>
    </form>
  );
}
