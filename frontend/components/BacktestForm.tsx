'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { strategiesApi } from '@/lib/api/strategies';
import { dataApi, Dataset } from '@/lib/api/data';
import { backtestApi, BacktestRequest, BacktestResult } from '@/lib/api/backtest';
import ParameterInput from './ParameterInput';
import { DatePicker } from './DatePicker';
import { toast } from '@/lib/toast';
import JSONImportModal from './JSONImportModal';
import { parseImportJSON, getBestRow } from '@/lib/utils/jsonParser';
import { validateParameters } from '@/lib/utils/parameterValidator';
import DatasetSelector from './DatasetSelector';

interface BacktestFormProps {
  onResult?: (result: BacktestResult) => void;
}

export default function BacktestForm({ onResult }: BacktestFormProps) {
  const [strategy, setStrategy] = useState<string>('');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [interval, setInterval] = useState('1h');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [initialCash, setInitialCash] = useState(100000);
  const [parameters, setParameters] = useState<Record<string, any>>({});

  // Dataset states
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
  const [selectedDatasetData, setSelectedDatasetData] = useState<Dataset | null>(null);

  // JSON Import states
  const [showImportModal, setShowImportModal] = useState(false);
  const [importData, setImportData] = useState<any>(null);
  const [validation, setValidation] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const defaultParams: Record<string, any> = {};
      Object.entries(selectedStrategyDetails.data.parameters).forEach(([key, param]) => {
        // Skip metadata keys (prefixed with _)
        if (key.startsWith('_')) return;
        defaultParams[key] = param.default;
      });
      setParameters(defaultParams);
    }
  }, [selectedStrategyDetails.data]);

  const runBacktestMutation = useMutation({
    mutationFn: (request: BacktestRequest) => backtestApi.run(request),
    onSuccess: (data) => {
      toast.success('Backtest completed successfully');
      if (onResult) {
        onResult(data);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to run backtest');
    },
  });

  const handleParameterChange = (name: string, value: any) => {
    setParameters((prev) => ({ ...prev, [name]: value }));
  };

  // JSON Import handler
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file type
    if (!file.name.endsWith('.json')) {
      toast.error('Please select a JSON file');
      return;
    }

    try {
      const content = await file.text();
      const parsed = parseImportJSON(content);
      const bestRow = getBestRow(parsed);

      if (!bestRow) {
        toast.error('No valid data found in JSON file');
        return;
      }

      // Validate parameters
      if (!selectedStrategyDetails.data?.parameters) {
        toast.error('Please select a strategy first');
        return;
      }

      const validationResult = validateParameters(
        bestRow,
        selectedStrategyDetails.data.parameters,
        false  // Use lenient mode for import
      );

      setImportData(bestRow);
      setValidation(validationResult);
      setShowImportModal(true);
    } catch (error: any) {
      toast.error(error.message || 'Failed to parse JSON file');
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleImportConfirm = () => {
    if (validation?.valid && validation?.parsedParameters) {
      setParameters(validation.parsedParameters);
      toast.success('Parameters imported successfully');
    }
    setShowImportModal(false);
    setImportData(null);
    setValidation(null);
  };

  const handleImportCancel = () => {
    setShowImportModal(false);
    setImportData(null);
    setValidation(null);
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedDataset) {
      toast.error('Please select a dataset');
      return;
    }

    if (!startTime || !endTime) {
      toast.error('Please select both start and end dates');
      return;
    }

    const start = new Date(startTime);
    const end = new Date(endTime);

    if (start >= end) {
      toast.error('Start date must be before end date');
      return;
    }

    // Format datetime without timezone conversion
    // This ensures the backend interprets the datetime as local time
    const formatDateTime = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
    };

    runBacktestMutation.mutate({
      strategy_name: strategy,
      dataset_id: selectedDataset,
      start_time: formatDateTime(start),
      end_time: formatDateTime(end),
      parameters,
      initial_cash: initialCash,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 space-y-6 border border-slate-200 dark:border-slate-700">

      <div>
        <label htmlFor="strategy" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Strategy
        </label>
        <select
          id="strategy"
          value={strategy}
          onChange={(e) => {
            setStrategy(e.target.value);
            setParameters({});
          }}
          required
          disabled={strategiesLoading}
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed transition-colors"
        >
          <option value="">Select a strategy</option>
          {strategies?.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name} (v{s.version})
            </option>
          ))}
        </select>
        {selectedStrategyDetails.data?.description && (
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
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
          setStartTime(dataset.start_time.split('T')[0]);
          setEndTime(dataset.end_time.split('T')[0]);
        }}
        disabled={strategiesLoading || runBacktestMutation.isPending}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="relative">
          <label htmlFor="symbol" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Symbol
          </label>
          <div className="relative">
            <input
              id="symbol"
              type="text"
              value={symbol}
              readOnly
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 pl-10 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-not-allowed"
            />
            <svg className="absolute left-3 top-3 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        </div>

        <div className="relative">
          <label htmlFor="interval" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Interval
          </label>
          <div className="relative">
            <input
              id="interval"
              type="text"
              value={interval}
              readOnly
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 pl-10 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-not-allowed"
            />
            <svg className="absolute left-3 top-3 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DatePicker
          id="startTime"
          label="Start Date"
          value={startTime}
          onChange={setStartTime}
          required
          maxDate={endTime || new Date().toISOString().split('T')[0]}
        />

        <DatePicker
          id="endTime"
          label="End Date"
          value={endTime}
          onChange={setEndTime}
          required
          minDate={startTime}
          maxDate={new Date().toISOString().split('T')[0]}
        />
      </div>

      {/* Dataset range warning */}
      {selectedDatasetData && (
        <div className={`text-xs mb-2 ${
          startTime < selectedDatasetData.start_time.split('T')[0] ||
          endTime > selectedDatasetData.end_time.split('T')[0]
            ? 'text-orange-600 dark:text-orange-400'
            : 'text-slate-500 dark:text-slate-400'
        }`}>
          {startTime < selectedDatasetData.start_time.split('T')[0] ||
           endTime > selectedDatasetData.end_time.split('T')[0]
            ? '⚠️ Time range outside dataset bounds (will be clipped)'
            : `Dataset range: ${selectedDatasetData.start_time.split('T')[0]} ~ ${selectedDatasetData.end_time.split('T')[0]}`
          }
        </div>
      )}

      <div>
        <label htmlFor="initialCash" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
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
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
        />
      </div>

      {selectedStrategyDetails.data?.parameters && Object.keys(selectedStrategyDetails.data.parameters).length > 0 && (
        <div className="border-t border-slate-200 dark:border-slate-700 pt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-heading font-semibold text-slate-900 dark:text-slate-100">
              Strategy Parameters
            </h3>
            <button
              type="button"
              onClick={triggerFileInput}
              className="flex items-center px-3 py-1.5 text-sm font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
              title="Import parameters from JSON file"
            >
              <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Import from JSON
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(selectedStrategyDetails.data.parameters).filter(([name]) => !name.startsWith('_')).map(([name, param]) => (
              <ParameterInput
                key={name}
                name={name}
                param={param as any}
                value={parameters[name]}
                onChange={handleParameterChange}
              />
            ))}
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={!strategy || !selectedDataset || runBacktestMutation.isPending}
        className="w-full bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white py-3 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-all duration-200 shadow-sm hover:shadow-md disabled:shadow-sm"
      >
        {runBacktestMutation.isPending ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Running Backtest...
          </span>
        ) : (
          'Run Backtest'
        )}
      </button>

      {/* JSON Import Modal */}
      <JSONImportModal
        isOpen={showImportModal}
        importRow={importData}
        validation={validation}
        onConfirm={handleImportConfirm}
        onCancel={handleImportCancel}
      />
    </form>
  );
}
