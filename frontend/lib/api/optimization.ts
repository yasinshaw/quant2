import api from '../api';

// Parameter range types
export interface ParameterRange {
  type?: 'int' | 'float' | 'choice';
  min?: number;
  max?: number;
  options?: any[];
  values?: any[];  // For grid search
}

export interface OptimizationRequest {
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  parameter_ranges: Record<string, any[] | ParameterRange>;
  fixed_parameters?: Record<string, any>;
  initial_cash?: number;

  // NEW: Optimization method
  optimization_method?: 'grid' | 'bayesian';

  // NEW: Bayesian optimization settings
  n_trials?: number;

  // NEW: Composite scoring
  scoring_weights?: ScoringWeights;

  // NEW: Out-of-sample testing
  enable_out_of_sample?: boolean;
  test_start_time?: string;
  test_end_time?: string;

  // NEW: Stability analysis
  enable_stability_analysis?: boolean;
}

export interface OptimizationResult {
  id: number;
  job_id: number;
  parameters: Record<string, any>;
  pnl: number;
  pnl_pct: number;
  total_trades: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  is_best?: boolean;
  composite_score?: number;  // NEW
}

export interface OptimizationResponse {
  job_id: number;
  total_combinations?: number;
  results?: OptimizationResult[];
  best_result: OptimizationResult;

  // NEW: Stability metrics
  stability_metrics?: StabilityReport;
}

export interface OptimizationResultDetail {
  id: number;
  parameters: Record<string, any>;
  score: number;
  composite_score?: number;  // NEW
  is_out_of_sample?: boolean;  // NEW
  backtest_result_id?: number;
  backtest_result?: {
    final_value?: number;
    total_return?: number;
    sharpe_ratio?: number;
    max_drawdown?: number;
    win_rate?: number;
    profit_factor?: number;
    total_trades?: number;
  };
}

export interface OptimizationResultsResponse {
  job_id: number;
  job_details: {
    strategy_name: string;
    symbol: string;
    interval: string;
    start_time: string;
    end_time: string;
    status: string;
    optimization_method: string;
    created_at: string;
    completed_at?: string;

    // NEW: Job configuration
    enable_stability_analysis?: boolean;
    enable_out_of_sample?: boolean;
  };
  results: OptimizationResultDetail[];
  total_results: number;
}

// NEW: Scoring weights interface
export interface ScoringWeights {
  sharpe_ratio: number;
  total_return: number;
  max_drawdown: number;
  win_rate: number;
  calmar_ratio?: number;
}

// NEW: Scoring weights response
export interface ScoringWeightsResponse {
  weights: ScoringWeights;
  description: Record<string, string>;
  note: string;
}

// NEW: Stability report
export interface StabilityNeighbor {
  parameters: Record<string, any>;
  score: number;
  pnl_pct?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
}

export interface StabilityReport {
  job_id: number;
  stability_score: number | null;
  variance: number | null;
  is_stable: boolean;
  enable_stability_analysis: boolean;
  neighbors?: StabilityNeighbor[];
  optimal_parameters?: Record<string, any>;
  optimal_score?: number;
}

export const optimizationApi = {
  run: async (request: OptimizationRequest): Promise<OptimizationResponse> => {
    const response = await api.post<OptimizationResponse>('/api/v1/backtest/optimize', request);
    return response.data;
  },

  getJobs: async () => {
    const response = await api.get('/api/v1/backtest/jobs');
    return response.data;
  },

  getResults: async (jobId: number): Promise<OptimizationResultsResponse> => {
    const response = await api.get<OptimizationResultsResponse>(
      `/api/v1/backtest/optimization/jobs/${jobId}/results`
    );
    return response.data;
  },

  // NEW: Get stability report
  getStability: async (jobId: number): Promise<StabilityReport> => {
    const response = await api.get<StabilityReport>(
      `/api/v1/backtest/optimization/jobs/${jobId}/stability`
    );
    return response.data;
  },

  // NEW: Get default scoring weights
  getScoringWeights: async (): Promise<ScoringWeightsResponse> => {
    const response = await api.get<ScoringWeightsResponse>(
      '/api/v1/backtest/optimization/scoring-weights'
    );
    return response.data;
  },
};

