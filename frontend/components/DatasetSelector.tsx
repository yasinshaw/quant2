'use client';

import { useQuery } from '@tanstack/react-query';
import { dataApi, Dataset } from '@/lib/api/data';

interface DatasetSelectorProps {
  value: number | null;
  onChange: (datasetId: number, dataset: Dataset) => void;
  disabled?: boolean;
}

export default function DatasetSelector({ value, onChange, disabled }: DatasetSelectorProps) {
  const { data: datasets, isLoading, error } = useQuery({
    queryKey: ['datasets'],
    queryFn: dataApi.getDatasets,
    staleTime: 60000, // 1 minute
  });

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const datasetId = parseInt(e.target.value);
    const dataset = datasets?.find((d) => d.id === datasetId);
    if (dataset) {
      onChange(datasetId, dataset);
    }
  };

  if (isLoading) {
    return (
      <div>
        <label htmlFor="dataset" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Dataset
        </label>
        <div className="animate-pulse">
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <label htmlFor="dataset" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Dataset
        </label>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-sm text-red-800 dark:text-red-200">Failed to load datasets</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-red-600 dark:text-red-400 underline mt-1 hover:text-red-800 dark:hover:text-red-300 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!datasets || datasets.length === 0) {
    return (
      <div>
        <label htmlFor="dataset" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Dataset
        </label>
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <p className="text-sm text-amber-800 dark:text-amber-200 mb-2">
            No datasets available. Download data first.
          </p>
          <a
            href="/data"
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline transition-colors"
          >
            Go to Data Management →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor="dataset" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
        Dataset
      </label>
      <select
        id="dataset"
        value={value || ''}
        onChange={handleChange}
        disabled={disabled}
        className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed transition-colors"
      >
        <option value="">Select a dataset</option>
        {datasets.map((dataset) => (
          <option key={dataset.id} value={dataset.id}>
            {dataset.name} ({dataset.symbol} {dataset.interval}, {dataset.candle_count} candles)
          </option>
        ))}
      </select>
    </div>
  );
}
