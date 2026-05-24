import api from '../api';

export interface DownloadRequest {
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  dataset_name?: string;
}

export interface DownloadResponse {
  symbol: string;
  interval: string;
  count: number;
  status: 'downloaded' | 'already_exists' | 'error';
  message?: string;
}

export interface DataStatus {
  symbol: string;
  interval: string;
  count: number;
  available: boolean;
  message?: string;
}

export interface SymbolsResponse {
  symbols: string[];
}

export interface DownloadedInterval {
  interval: string;
  count: number;
  start_time: string;
  end_time: string;
}

export interface DownloadedDataItem {
  symbol: string;
  intervals: DownloadedInterval[];
}

export interface DeleteResponse {
  symbol: string;
  interval: string;
  deleted_count: number;
  message: string;
}

export interface Dataset {
  id: number;
  name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  candle_count: number;
  created_at: string;
}

export interface DatasetRenameRequest {
  name: string;
}

export interface DatasetDeleteResponse {
  dataset_id: number;
  deleted_count: number;
  message: string;
}

export interface ClearHistoryResponse {
  backtest_jobs: number;
  backtest_results: number;
  trades: number;
  optimization_jobs: number;
  optimization_results: number;
  total_deleted: number;
  message: string;
}

export const dataApi = {
  getSymbols: async (): Promise<string[]> => {
    const response = await api.get<SymbolsResponse>('/api/v1/data/symbols');
    return response.data.symbols;
  },

  download: async (request: DownloadRequest): Promise<DownloadResponse> => {
    const response = await api.post<DownloadResponse>('/api/v1/data/download', request);
    return response.data;
  },

  getStatus: async (symbol: string, interval: string): Promise<DataStatus> => {
    const response = await api.get<DataStatus>(`/api/v1/data/status/${symbol}/${interval}`);
    return response.data;
  },

  getCandles: async (
    symbol: string,
    interval: string,
    startTime: string,
    endTime: string
  ): Promise<any[]> => {
    const response = await api.get('/api/v1/data/candles', {
      params: {
        symbol,
        interval,
        start_time: startTime,
        end_time: endTime,
      },
    });
    return response.data.candles || response.data;
  },

  getDownloadedData: async (): Promise<DownloadedDataItem[]> => {
    const response = await api.get<{ data: DownloadedDataItem[] }>(
      '/api/v1/data/downloaded'
    );
    return response.data.data;
  },

  deleteData: async (symbol: string, interval: string): Promise<DeleteResponse> => {
    const response = await api.delete<DeleteResponse>(
      `/api/v1/data/${symbol}/${interval}`
    );
    return response.data;
  },

  getDatasets: async (): Promise<Dataset[]> => {
    const response = await api.get<{ datasets: Dataset[] }>(
      '/api/v1/data/datasets'
    );
    return response.data.datasets;
  },

  renameDataset: async (datasetId: number, name: string): Promise<{ id: number; name: string }> => {
    const response = await api.put<{ id: number; name: string }>(
      `/api/v1/data/datasets/${datasetId}/rename`,
      { name }
    );
    return response.data;
  },

  deleteDataset: async (datasetId: number): Promise<DatasetDeleteResponse> => {
    const response = await api.delete<DatasetDeleteResponse>(
      `/api/v1/data/datasets/${datasetId}`
    );
    return response.data;
  },

  clearAllHistory: async (): Promise<ClearHistoryResponse> => {
    const response = await api.delete<ClearHistoryResponse>(
      '/api/v1/data/history/all'
    );
    return response.data;
  },
};
