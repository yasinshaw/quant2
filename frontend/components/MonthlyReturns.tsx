'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';

interface Props {
  data: Record<string, number>;
}

interface ChartData {
  month: string;
  return: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: { month: string } }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const returnValue = payload[0].value;
    return (
      <div className="bg-white dark:bg-slate-800 p-3 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl">
        <p className="text-sm text-slate-600 dark:text-slate-400">
          <span className="font-semibold text-slate-900 dark:text-slate-100">Month:</span> {payload[0].payload.month}
        </p>
        <p
          className={`text-sm font-semibold ${
            returnValue >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
          }`}
        >
          P&L: {returnValue >= 0 ? '+' : ''}${Math.abs(returnValue).toFixed(2)}
        </p>
      </div>
    );
  }
  return null;
};

export default function MonthlyReturns({ data }: Props) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
        <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">Monthly Returns</h3>
        <p className="text-slate-500 dark:text-slate-400 text-center py-12">No data available</p>
      </div>
    );
  }

  const chartData: ChartData[] = Object.entries(data)
    .map(([month, returnValue]) => ({
      month,
      return: returnValue,
    }))
    .sort((a, b) => a.month.localeCompare(b.month));

  const minValue = Math.min(...chartData.map((d) => d.return));
  const maxValue = Math.max(...chartData.map((d) => d.return));

  // Calculate Y-axis domain with proper padding
  const yMin = minValue >= 0 ? 0 : Math.floor(minValue * 1.1);
  const yMax = maxValue <= 0 ? 0 : Math.ceil(maxValue * 1.1);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
      <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">Monthly Returns</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: '#475569' }}
            stroke="#94a3b8"
            className="dark:stroke-slate-600"
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 12, fill: '#475569' }}
            stroke="#94a3b8"
            className="dark:stroke-slate-600"
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="return" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.return >= 0 ? '#10b981' : '#ef4444'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
