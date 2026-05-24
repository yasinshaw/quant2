'use client';

import { useState, FormEvent } from 'react';
import { toast } from '@/lib/toast';
import { DatePicker } from './DatePicker';

interface DownloadFormProps {
  onDownload: (startTime: string, endTime: string, datasetName?: string) => void;
  isLoading: boolean;
  symbol?: string;
  interval?: string;
}

export default function DownloadForm({ onDownload, isLoading, symbol, interval }: DownloadFormProps) {
  // Set default dates (last 30 days)
  const getDefaultDate = (daysAgo: number) => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    return date.toISOString().split('T')[0]; // YYYY-MM-DD format
  };

  const [startDate, setStartDate] = useState(getDefaultDate(30));
  const [endDate, setEndDate] = useState(getDefaultDate(0));
  const [datasetName, setDatasetName] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    if (!startDate || !endDate) {
      toast.error('Please select both start and end dates');
      return;
    }

    if (new Date(startDate) >= new Date(endDate)) {
      toast.error('Start date must be before end date');
      return;
    }

    // Send datetime without timezone conversion
    // This ensures the backend interprets the dates as local time exactly as selected by user
    const startISO = startDate + 'T00:00:00';
    const endISO = endDate + 'T23:59:59';

    onDownload(startISO, endISO, datasetName || undefined);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
      <h2 className="text-xl font-heading font-semibold text-slate-900 dark:text-slate-100 mb-4">Download Historical Data</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Dataset Name Input */}
        <div>
          <label htmlFor="datasetName" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Dataset Name (Optional)
          </label>
          <input
            id="datasetName"
            type="text"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="Auto-generated if empty"
            className="w-full border border-slate-300 dark:border-slate-600 rounded-md px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {symbol && interval && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Default: {symbol} {interval} ({startDate} ~ {endDate})_[timestamp]
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <DatePicker
            id="start_date"
            label="Start Date"
            value={startDate}
            onChange={setStartDate}
            required
            maxDate={endDate || new Date().toISOString().split('T')[0]}
          />
          <DatePicker
            id="end_date"
            label="End Date"
            value={endDate}
            onChange={setEndDate}
            required
            minDate={startDate}
            maxDate={new Date().toISOString().split('T')[0]}
          />
        </div>

        <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-3">
          <p className="text-sm text-primary-700 dark:text-primary-400">
            <strong className="font-semibold">Tip:</strong> For large date ranges or small intervals, downloads may take several minutes.
            Start with smaller ranges (e.g., 1 month) for testing.
          </p>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white px-6 py-2.5 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-sm hover:shadow-md disabled:shadow-sm"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Downloading...
            </span>
          ) : (
            'Download Data'
          )}
        </button>
      </form>
    </div>
  );
}
