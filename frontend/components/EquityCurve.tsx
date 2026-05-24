'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';

interface DataPoint {
  time: string;
  value: number;
  benchmark?: number;
}

interface Props {
  data: DataPoint[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string; payload: DataPoint }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const hasBenchmark = data.benchmark !== undefined && data.benchmark !== null;
    const diff = hasBenchmark ? data.value - data.benchmark! : null;
    const diffPct = hasBenchmark && data.benchmark! !== 0
      ? ((data.value - data.benchmark!) / data.benchmark!) * 100
      : null;

    return (
      <div className="bg-white dark:bg-slate-800 p-3 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl min-w-[180px]">
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
          <span className="font-semibold text-slate-900 dark:text-slate-100">Date:</span> {data.time.split('T')[0]}
        </p>
        <p className="text-sm text-blue-600 dark:text-blue-400">
          <span className="font-semibold">Strategy:</span> ${data.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </p>
        {hasBenchmark && (
          <>
            <p className="text-sm text-amber-600 dark:text-amber-400">
              <span className="font-semibold">Buy & Hold:</span> ${data.benchmark!.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
            {diff !== null && (
              <p className={`text-sm font-semibold mt-1 pt-1 border-t border-slate-200 dark:border-slate-600 ${
                diff >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}>
                Diff: {diff >= 0 ? '+' : ''}${diff.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                {diffPct !== null && ` (${diffPct >= 0 ? '+' : ''}${diffPct.toFixed(1)}%)`}
              </p>
            )}
          </>
        )}
      </div>
    );
  }
  return null;
};

export default function EquityCurve({ data }: Props) {
  const hasBenchmark = data.some((d) => d.benchmark !== undefined && d.benchmark !== null);

  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
        <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">Equity Curve</h3>
        <p className="text-slate-500 dark:text-slate-400 text-center py-12">No data available</p>
      </div>
    );
  }

  const allValues = data.flatMap((d) =>
    hasBenchmark && d.benchmark !== undefined ? [d.value, d.benchmark] : [d.value]
  );
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const domain = [Math.floor(minValue * 0.95), Math.ceil(maxValue * 1.05)];

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
      <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">Equity Curve</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 12, fill: '#475569' }}
            stroke="#94a3b8"
            className="dark:stroke-slate-600"
            tickFormatter={(value: string) => value.split('T')[0]}
          />
          <YAxis
            domain={domain}
            tick={{ fontSize: 12, fill: '#475569' }}
            stroke="#94a3b8"
            className="dark:stroke-slate-600"
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            name="Strategy"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 6, fill: '#3b82f6', stroke: '#fff', strokeWidth: 2 }}
          />
          {hasBenchmark && (
            <Line
              type="monotone"
              dataKey="benchmark"
              name="Buy & Hold"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              activeDot={{ r: 5, fill: '#f59e0b', stroke: '#fff', strokeWidth: 2 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
