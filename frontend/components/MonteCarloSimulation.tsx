'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Cell, ReferenceLine,
} from 'recharts';
import { backtestApi, MonteCarloResult } from '@/lib/api/backtest';

interface Props {
  jobId: number;
  initialCash: number;
}

function computePercentileCurves(equityCurves: number[][], percentiles: number[]) {
  if (!equityCurves.length) return {};
  const numPoints = equityCurves[0].length;
  const result: Record<string, number[]> = {};

  for (const p of percentiles) {
    const key = `p${p}`;
    result[key] = [];
    for (let i = 0; i < numPoints; i++) {
      const values = equityCurves.map(c => c[i]).sort((a, b) => a - b);
      const idx = Math.floor(values.length * p / 100);
      result[key].push(values[Math.min(idx, values.length - 1)]);
    }
  }

  return result;
}

function buildHistogramData(returns: number[], originalReturn: number) {
  if (!returns.length) return [];
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const binCount = 30;
  const binWidth = (max - min) / binCount || 1;

  const bins = Array.from({ length: binCount }, (_, i) => ({
    range: (min + i * binWidth + binWidth / 2),
    count: 0,
    isOriginal: false,
  }));

  for (const r of returns) {
    const idx = Math.min(Math.floor((r - min) / binWidth), binCount - 1);
    bins[idx].count++;
  }

  let closestIdx = 0;
  let closestDist = Infinity;
  bins.forEach((b, i) => {
    const dist = Math.abs(b.range - originalReturn);
    if (dist < closestDist) {
      closestDist = dist;
      closestIdx = i;
    }
  });
  bins[closestIdx].isOriginal = true;

  return bins;
}

export default function MonteCarloSimulation({ jobId, initialCash }: Props) {
  const [numSimulations, setNumSimulations] = useState(1000);
  const [result, setResult] = useState<MonteCarloResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => backtestApi.runMonteCarlo(jobId, numSimulations),
    onSuccess: (data) => setResult(data),
  });

  const handleRun = () => {
    setResult(null);
    mutation.mutate();
  };

  const pctFormat = (v: number) => `${(v * 100).toFixed(1)}%`;
  const moneyFormat = (v: number) => `$${(v / 1000).toFixed(0)}K`;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md border border-slate-200 dark:border-slate-700">
      {/* Header + Controls */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-heading font-bold text-slate-900 dark:text-slate-100">
            Monte Carlo Simulation
          </h3>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              <span>Simulations:</span>
              <input
                type="range"
                min={100}
                max={10000}
                step={100}
                value={numSimulations}
                onChange={(e) => setNumSimulations(Number(e.target.value))}
                className="w-32"
              />
              <span className="font-mono text-slate-900 dark:text-slate-100 w-16 text-right">
                {numSimulations.toLocaleString()}
              </span>
            </label>
            <button
              onClick={handleRun}
              disabled={mutation.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {mutation.isPending ? 'Running...' : 'Run Simulation'}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {mutation.isError && (
        <div className="p-4 mx-6 mt-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
          Failed to run simulation. Please try again.
        </div>
      )}

      {/* Loading */}
      {mutation.isPending && (
        <div className="p-12 text-center text-slate-500 dark:text-slate-400">
          Running {numSimulations.toLocaleString()} simulations...
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="p-6 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Median Return"
              value={pctFormat(result.median_return)}
              sub={`P5: ${pctFormat(result.p5_return)} / P95: ${pctFormat(result.p95_return)}`}
            />
            <StatCard
              label="95th Pctl Drawdown"
              value={pctFormat(result.p95_max_drawdown)}
              sub={`Median: ${pctFormat(result.median_max_drawdown)}`}
              valueColor={result.p95_max_drawdown > 0.25 ? 'text-red-600 dark:text-red-400' : undefined}
            />
            <StatCard
              label="Ruin Probability"
              value={pctFormat(result.ruin_probability)}
              sub={`Equity < ${moneyFormat(initialCash * 0.5)}`}
              valueColor={result.ruin_probability > 0.05 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}
            />
            <StatCard
              label="Original vs Median"
              value={pctFormat(result.original_return)}
              sub={`Median: ${pctFormat(result.median_return)}`}
              valueColor={result.original_return >= result.median_return ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Equity Curve Distribution
              </h4>
              <FanChart result={result} initialCash={initialCash} />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Max Drawdown Distribution
              </h4>
              <ReturnHistogram result={result} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, sub, valueColor }: {
  label: string; value: string; sub: string; valueColor?: string;
}) {
  return (
    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
      <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</p>
      <p className={`text-xl font-bold mt-1 ${valueColor ?? 'text-slate-900 dark:text-slate-100'}`}>{value}</p>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{sub}</p>
    </div>
  );
}

function FanChart({ result }: { result: MonteCarloResult; initialCash: number }) {
  const percentiles = computePercentileCurves(result.equity_curves, [5, 25, 50, 75, 95]);
  const numPoints = result.equity_curves[0]?.length ?? 0;
  const data = Array.from({ length: numPoints }, (_, i) => ({
    index: i + 1,
    p5: percentiles.p5?.[i],
    p25: percentiles.p25?.[i],
    p50: percentiles.p50?.[i],
    p75: percentiles.p75?.[i],
    p95: percentiles.p95?.[i],
  }));

  const allValues = data.flatMap(d => [d.p5, d.p95].filter((v): v is number => v !== undefined));
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const domain = [Math.floor(minVal * 0.95), Math.ceil(maxVal * 1.05)];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
        <XAxis dataKey="index" tick={{ fontSize: 11, fill: '#475569' }} stroke="#94a3b8" />
        <YAxis domain={domain} tick={{ fontSize: 11, fill: '#475569' }} stroke="#94a3b8"
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`} />
        <Tooltip formatter={(v: number) => `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
        <Line type="monotone" dataKey="p5" stroke="#93c5fd" strokeWidth={1} dot={false} name="P5" />
        <Line type="monotone" dataKey="p25" stroke="#60a5fa" strokeWidth={1} dot={false} name="P25" />
        <Line type="monotone" dataKey="p50" stroke="#3b82f6" strokeWidth={2} dot={false} name="P50 (Median)" />
        <Line type="monotone" dataKey="p75" stroke="#60a5fa" strokeWidth={1} dot={false} name="P75" />
        <Line type="monotone" dataKey="p95" stroke="#93c5fd" strokeWidth={1} dot={false} name="P95" />
      </LineChart>
    </ResponsiveContainer>
  );
}

function ReturnHistogram({ result }: { result: MonteCarloResult }) {
  // Show max drawdown distribution (shuffle changes drawdowns, not returns)
  const bins = buildHistogramData(result.max_drawdowns, result.original_max_drawdown);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={bins}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
        <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#475569' }} stroke="#94a3b8"
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis tick={{ fontSize: 11, fill: '#475569' }} stroke="#94a3b8" />
        <Tooltip formatter={(v: number) => v} labelFormatter={(l: number) => `Max Drawdown: ${(l * 100).toFixed(1)}%`} />
        <Bar dataKey="count">
          {bins.map((entry, idx) => (
            <Cell
              key={idx}
              fill={entry.isOriginal ? '#f59e0b' : entry.range > 0.20 ? '#ef4444' : '#3b82f6'}
              opacity={entry.isOriginal ? 1 : 0.6}
            />
          ))}
        </Bar>
        <ReferenceLine x={result.original_max_drawdown} stroke="#f59e0b" strokeWidth={2} label="Original" />
      </BarChart>
    </ResponsiveContainer>
  );
}
