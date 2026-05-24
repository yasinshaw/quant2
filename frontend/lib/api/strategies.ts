import api from '../api';

export interface StrategyParameter {
  type: string;
  description?: string;
  default?: any;
  min?: number;
  max?: number;
  choices?: string[];
  required?: boolean;
}

export interface Strategy {
  name: string;
  version: string;
  description: string;
  is_hidden?: boolean;
  parameters?: Record<string, StrategyParameter>;
}

export interface StrategiesListResponse {
  strategies: Strategy[];
  count: number;
}

export interface RefreshResponse {
  message: string;
  count: number;
}

export const strategiesApi = {
  list: async (showHidden = false): Promise<Strategy[]> => {
    const response = await api.get<StrategiesListResponse>('/api/v1/strategies', {
      params: showHidden ? { show_hidden: true } : {},
    });
    return response.data.strategies;
  },

  refresh: async (): Promise<RefreshResponse> => {
    const response = await api.post<RefreshResponse>('/api/v1/strategies/refresh');
    return response.data;
  },

  get: async (name: string): Promise<Strategy> => {
    const response = await api.get<Strategy>(`/api/v1/strategies/${encodeURIComponent(name)}`);
    return response.data;
  },

  hide: async (name: string): Promise<void> => {
    await api.post(`/api/v1/strategies/${encodeURIComponent(name)}/hide`);
  },

  show: async (name: string): Promise<void> => {
    await api.post(`/api/v1/strategies/${encodeURIComponent(name)}/show`);
  },
};
