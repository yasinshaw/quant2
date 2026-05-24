import api from '../api';

/**
 * Query parameters for history endpoints
 */
export interface HistoryQueryParams {
  strategy_name?: string;
  symbol?: string;
  status?: string;
  is_favorite?: boolean;
  sort_by?: 'created_at' | 'total_return' | 'sharpe_ratio' | 'best_score';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

/**
 * Generic paginated response type
 */
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: T[];
}

/**
 * Backtest history item
 */
export interface BacktestHistoryItem {
  job_id: number;
  result_id?: number;  // Result ID if job is completed
  strategy_name: string;
  symbol: string;
  interval: string;
  status: string;
  is_favorite: boolean;
  created_at: string;
  completed_at?: string;
  start_time: string;
  end_time: string;
  initial_cash: number;
  final_value?: number;
  total_return?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  profit_factor?: number;
  total_trades?: number;
}

/**
 * Optimization history item
 */
export interface OptimizationHistoryItem {
  job_id: number;
  strategy_name: string;
  symbol: string;
  interval: string;
  status: string;
  created_at: string;
  completed_at?: string;
  start_time: string;
  end_time: string;
  optimization_method: string;
  total_combinations?: number;
  best_parameters?: Record<string, any>;
  best_score?: number;
  best_total_return?: number;
}

/**
 * Delete response
 */
export interface DeleteResponse {
  success: boolean;
  message: string;
}

/**
 * History API client
 */
export const historyApi = {
  /**
   * Get backtest history with filtering, sorting, and pagination
   */
  getBacktestHistory: async (
    params: HistoryQueryParams
  ): Promise<PaginatedResponse<BacktestHistoryItem>> => {
    const response = await api.get<PaginatedResponse<BacktestHistoryItem>>(
      '/api/v1/backtest/history',
      { params }
    );
    return response.data;
  },

  /**
   * Delete a backtest job
   */
  deleteBacktestJob: async (jobId: number): Promise<void> => {
    await api.delete<DeleteResponse>(`/api/v1/backtest/jobs/${jobId}`);
  },

  /**
   * Toggle favorite status for a backtest job
   */
  toggleBacktestFavorite: async (
    jobId: number
  ): Promise<{ job_id: number; is_favorite: boolean }> => {
    const response = await api.patch<{ job_id: number; is_favorite: boolean }>(
      `/api/v1/backtest/jobs/${jobId}/favorite`
    );
    return response.data;
  },

  /**
   * Get optimization history with filtering, sorting, and pagination
   */
  getOptimizationHistory: async (
    params: HistoryQueryParams
  ): Promise<PaginatedResponse<OptimizationHistoryItem>> => {
    const response = await api.get<PaginatedResponse<OptimizationHistoryItem>>(
      '/api/v1/backtest/optimization/history',
      { params }
    );
    return response.data;
  },

  /**
   * Delete an optimization job
   */
  deleteOptimizationJob: async (jobId: number): Promise<void> => {
    await api.delete<DeleteResponse>(`/api/v1/backtest/optimization/jobs/${jobId}`);
  },
};
