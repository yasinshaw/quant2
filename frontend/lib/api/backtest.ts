import api from '../api';

export interface BacktestRequest {
  strategy_name: string;
  dataset_id: number;
  start_time?: string;
  end_time?: string;
  parameters: Record<string, any>;
  initial_cash?: number;
}

export interface BacktestResult {
  id: number;
  backtest_job_id: number;
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  initial_cash: number;
  final_value: number;
  total_return: number;
  total_trades: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  status?: string;
  created_at?: string;
}

export interface BacktestJob {
  id: number;
  strategy_name: string;
  symbol: string;
  interval: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface BacktestJobsResponse {
  jobs: BacktestJob[];
  count: number;
}

export interface Trade {
  trade_no: number;
  entry_time: string;
  exit_time: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  exit_price: number;
  size: number;
  pnl: number;
  commission: number;
}

export interface Dataset {
  id: number;
  name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  candle_count: number;
}

export interface BacktestReport {
  summary: {
    total_return: number;
    final_value: number;
    total_trades: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown: number;
    profit_factor: number;
    avg_trade: number;
    avg_winning_trade: number;
    avg_losing_trade: number;
  };
  monthly_returns: Record<string, number>;
  trade_analysis: {
    trades: Trade[];
    long_trades: number;
    short_trades: number;
    avg_hold_time: number;
    best_trade: number;
    worst_trade: number;
  };
  equity_curve: Array<{ time: string; value: number }>;
  strategy_name: string;
  parameters: Record<string, any>;
  dataset?: Dataset | null;
  backtest_start_time?: string;
  backtest_end_time?: string;
}

export interface MonteCarloResult {
  num_simulations: number;
  equity_curves: number[][];
  final_returns: number[];
  max_drawdowns: number[];
  median_return: number;
  p5_return: number;
  p95_return: number;
  median_max_drawdown: number;
  p95_max_drawdown: number;
  ruin_probability: number;
  original_return: number;
  original_max_drawdown: number;
}

export const backtestApi = {
  run: async (request: BacktestRequest): Promise<BacktestResult> => {
    const response = await api.post<BacktestResult>('/api/v1/backtest/run', request);
    return response.data;
  },

  getJobs: async (): Promise<BacktestJob[]> => {
    const response = await api.get<BacktestJobsResponse>('/api/v1/backtest/jobs');
    return response.data.jobs;
  },

  getJob: async (id: number): Promise<BacktestJob> => {
    const response = await api.get<BacktestJob>(`/api/v1/backtest/jobs/${id}`);
    return response.data;
  },

  getReport: async (resultId: number): Promise<BacktestReport> => {
    const response = await api.get<BacktestReport>(`/api/v1/backtest/results/${resultId}/report`);
    return response.data;
  },

  getReportByJob: async (jobId: number): Promise<BacktestReport> => {
    const response = await api.get<BacktestReport>(`/api/v1/backtest/jobs/${jobId}/report`);
    return response.data;
  },

  runMonteCarlo: async (jobId: number, numSimulations: number = 1000): Promise<MonteCarloResult> => {
    const response = await api.post<MonteCarloResult>(
      `/api/v1/backtest/jobs/${jobId}/monte-carlo`,
      { num_simulations: numSimulations }
    );
    return response.data;
  },
};
