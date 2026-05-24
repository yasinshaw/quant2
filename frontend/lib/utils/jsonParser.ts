/**
 * JSON Parser for optimization results import/export
 */

export interface ImportRow {
  rank: number;
  parameters: Record<string, string | number>;
  pnl?: number;
  pnl_pct?: number;
  total_trades?: number;
  win_rate?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  composite_score?: number;
  is_best?: boolean;
  score?: number;
  total_return?: number;
  profit_factor?: number;
}

export interface ParsedImport {
  rows: ImportRow[];
  parameterNames: string[];
  metadata?: {
    job_id?: number;
    strategy_name?: string;
    exported_at?: string;
  };
}

export interface ExportData {
  job_id?: number;
  strategy_name?: string;
  exported_at: string;
  results: Array<{
    rank: number;
    parameters: Record<string, any>;
    pnl?: number;
    pnl_pct?: number;
    total_trades?: number;
    win_rate?: number;
    sharpe_ratio?: number;
    max_drawdown?: number;
    composite_score?: number;
    is_best?: boolean;
    score?: number;
    total_return?: number;
    profit_factor?: number;
  }>;
}

export interface ParamsExportData {
  strategy_name: string;
  exported_at: string;
  parameters: Record<string, any>;
}

/**
 * Parse JSON content exported from optimization results or params export
 */
export function parseImportJSON(jsonContent: string): ParsedImport {
  let data: any;

  try {
    data = JSON.parse(jsonContent);
  } catch {
    throw new Error('Invalid JSON file');
  }

  // Params-only export format: { strategy_name, exported_at, parameters }
  if (data.parameters && !data.results) {
    return {
      rows: [{
        rank: 1,
        parameters: data.parameters,
        is_best: true,
      }],
      parameterNames: Object.keys(data.parameters),
      metadata: {
        strategy_name: data.strategy_name,
        exported_at: data.exported_at,
      },
    };
  }

  // Optimization results export format: { job_id, strategy_name, exported_at, results }
  if (Array.isArray(data.results)) {
    const rows: ImportRow[] = data.results.map((r: any, idx: number) => ({
      rank: r.rank ?? idx + 1,
      parameters: r.parameters ?? {},
      pnl: r.pnl,
      pnl_pct: r.pnl_pct,
      total_trades: r.total_trades,
      win_rate: r.win_rate,
      sharpe_ratio: r.sharpe_ratio,
      max_drawdown: r.max_drawdown,
      composite_score: r.composite_score,
      is_best: r.is_best ?? false,
      score: r.score,
      total_return: r.total_return,
      profit_factor: r.profit_factor,
    }));

    const paramNames = data.results[0]?.parameters
      ? Object.keys(data.results[0].parameters)
      : [];

    return {
      rows,
      parameterNames: paramNames,
      metadata: {
        job_id: data.job_id,
        strategy_name: data.strategy_name,
        exported_at: data.exported_at,
      },
    };
  }

  throw new Error('Unrecognized JSON format');
}

/**
 * Get the best row from parsed import (is_best === true or first row)
 */
export function getBestRow(parsed: ParsedImport): ImportRow | null {
  const bestRow = parsed.rows.find(row => row.is_best === true);
  if (bestRow) {
    return bestRow;
  }

  return parsed.rows[0] || null;
}
