'use client';

import { useState, useMemo } from 'react';
import { Trade } from '@/lib/api/backtest';
import { formatDateTime } from '@/lib/utils/dateFormat';

interface YearlyStats {
  year: string;
  trades: number;
  wins: number;
  losses: number;
  winRate: number;
  pnl: number;
  grossProfit: number;
  grossLoss: number;
  profitFactor: number;
  avgTrade: number;
  bestTrade: number;
  worstTrade: number;
  annualizedReturn: number;
}

interface Props {
  trades: Trade[];
  initialCash?: number;
  onTradeClick?: (trade: Trade) => void;
}

type SortField = 'entry_time' | 'exit_time' | 'side' | 'entry_price' | 'exit_price' | 'size' | 'pnl' | 'commission';
type SortOrder = 'asc' | 'desc';

export default function TradeTable({ trades, initialCash, onTradeClick }: Props) {
  const [sortField, setSortField] = useState<SortField>('entry_time');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const yearlyStats = useMemo((): YearlyStats[] => {
    const yearMap: Record<string, Trade[]> = {};
    for (const trade of trades) {
      const year = new Date(trade.entry_time).getFullYear().toString();
      if (!yearMap[year]) yearMap[year] = [];
      yearMap[year].push(trade);
    }

    const startBalance = initialCash ?? 0;
    let cumulPnl = 0;

    const years = Object.entries(yearMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([year, yearTrades]): YearlyStats => {
        const wins = yearTrades.filter((t: Trade) => t.pnl > 0);
        const losses = yearTrades.filter((t: Trade) => t.pnl <= 0);
        const grossProfit = wins.reduce((s: number, t: Trade) => s + t.pnl, 0);
        const grossLoss = Math.abs(losses.reduce((s: number, t: Trade) => s + t.pnl, 0));
        const pnl = yearTrades.reduce((s: number, t: Trade) => s + t.pnl, 0);
        const yearStartBal = startBalance + cumulPnl;
        cumulPnl += pnl;

        return {
          year,
          trades: yearTrades.length,
          wins: wins.length,
          losses: losses.length,
          winRate: yearTrades.length > 0 ? wins.length / yearTrades.length : 0,
          pnl,
          grossProfit,
          grossLoss,
          profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
          avgTrade: yearTrades.length > 0 ? pnl / yearTrades.length : 0,
          bestTrade: Math.max(...yearTrades.map((t: Trade) => t.pnl)),
          worstTrade: Math.min(...yearTrades.map((t: Trade) => t.pnl)),
          annualizedReturn: yearStartBal > 0 ? pnl / yearStartBal : 0,
        };
      });

    // Add total row
    const totalPnl = trades.reduce((s, t) => s + t.pnl, 0);
    const allWins = trades.filter((t) => t.pnl > 0);
    const allLosses = trades.filter((t) => t.pnl <= 0);
    const totalGP = allWins.reduce((s, t) => s + t.pnl, 0);
    const totalGL = Math.abs(allLosses.reduce((s, t) => s + t.pnl, 0));
    const finalBalance = startBalance + totalPnl;

    // Compute total years span from first entry to last exit
    const sortedByExit = [...trades].sort(
      (a, b) => new Date(a.exit_time).getTime() - new Date(b.exit_time).getTime()
    );
    const totalYears = sortedByExit.length >= 2
      ? (new Date(sortedByExit[sortedByExit.length - 1].exit_time).getTime() -
         new Date(sortedByExit[0].entry_time).getTime()) / (365.25 * 24 * 3600 * 1000)
      : 1;

    years.push({
      year: 'Total',
      trades: trades.length,
      wins: allWins.length,
      losses: allLosses.length,
      winRate: trades.length > 0 ? allWins.length / trades.length : 0,
      pnl: totalPnl,
      grossProfit: totalGP,
      grossLoss: totalGL,
      profitFactor: totalGL > 0 ? totalGP / totalGL : totalGP > 0 ? Infinity : 0,
      avgTrade: trades.length > 0 ? totalPnl / trades.length : 0,
      bestTrade: Math.max(...trades.map((t: Trade) => t.pnl)),
      worstTrade: Math.min(...trades.map((t: Trade) => t.pnl)),
      annualizedReturn: startBalance > 0
        ? Math.pow(finalBalance / startBalance, 1 / Math.max(totalYears, 0.01)) - 1
        : 0,
    });

    return years;
  }, [trades, initialCash]);

  // Compute running balance for each trade (sorted by exit_time asc)
  const tradeBalances = useMemo((): Map<string, number> => {
    const balances = new Map<string, number>();
    if (!initialCash) return balances;

    const sorted = [...trades].sort(
      (a, b) => new Date(a.exit_time).getTime() - new Date(b.exit_time).getTime()
    );
    let balance = initialCash;
    for (const t of sorted) {
      balances.set(t.exit_time, balance);
      balance += t.pnl;
    }
    return balances;
  }, [trades, initialCash]);

  const sortedTrades = useMemo(() => {
    const sorted = [...trades].sort((a, b) => {
      let aValue: string | number = a[sortField];
      let bValue: string | number = b[sortField];

      if (sortField === 'entry_time' || sortField === 'exit_time') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
    return sorted;
  }, [trades, sortField, sortOrder]);

  const totalPages = Math.ceil(sortedTrades.length / itemsPerPage);
  const paginatedTrades = sortedTrades.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const exportToCSV = () => {
    const headers = [
      'Trade#',
      'Entry Time',
      'Exit Time',
      'Side',
      'Entry Price',
      'Exit Price',
      'Size',
      'PnL',
      'Commission',
    ];
    const rows = trades.map((trade) => [
      trade.trade_no.toString(),
      trade.entry_time,
      trade.exit_time,
      trade.side,
      trade.entry_price.toString(),
      trade.exit_price.toString(),
      trade.size.toString(),
      trade.pnl.toString(),
      trade.commission.toString(),
    ]);

    const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'trades.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (field !== sortField) return <span className="text-slate-300 dark:text-slate-600 ml-1">↕</span>;
    return <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
  };

  if (!trades || trades.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
        <h3 className="text-lg font-heading font-bold mb-4 text-slate-900 dark:text-slate-100">Trade Analysis</h3>
        <p className="text-slate-500 dark:text-slate-400 text-center py-12">No trades available</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-700">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-heading font-bold text-slate-900 dark:text-slate-100">Trade Analysis</h3>
        <button
          onClick={exportToCSV}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white rounded-lg transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md"
        >
          Export CSV
        </button>
      </div>

      {/* Yearly Breakdown */}
      {yearlyStats.length > 1 && (
        <div className="mb-6 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700 text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900/50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Year</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Trades</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Wins</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Losses</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Win Rate</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">PnL</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Ann. Return</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Profit Factor</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Avg Trade</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Best</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Worst</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {yearlyStats.map((stat) => {
                const isTotal = stat.year === 'Total';
                return (
                  <tr
                    key={stat.year}
                    className={isTotal ? 'bg-slate-100 dark:bg-slate-700/50 font-semibold' : 'hover:bg-slate-50 dark:hover:bg-slate-700/30'}
                  >
                    <td className="px-3 py-2 whitespace-nowrap text-slate-900 dark:text-slate-100">
                      {stat.year}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-slate-900 dark:text-slate-100">{stat.trades}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-emerald-600 dark:text-emerald-400">{stat.wins}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-red-600 dark:text-red-400">{stat.losses}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-slate-900 dark:text-slate-100">{(stat.winRate * 100).toFixed(1)}%</td>
                    <td className={`px-3 py-2 whitespace-nowrap text-right ${stat.pnl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {stat.pnl >= 0 ? '+' : ''}${stat.pnl.toFixed(2)}
                    </td>
                    <td className={`px-3 py-2 whitespace-nowrap text-right font-medium ${stat.annualizedReturn >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {stat.annualizedReturn >= 0 ? '+' : ''}{(stat.annualizedReturn * 100).toFixed(2)}%
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-slate-900 dark:text-slate-100">
                      {stat.profitFactor === Infinity ? '∞' : stat.profitFactor.toFixed(2)}
                    </td>
                    <td className={`px-3 py-2 whitespace-nowrap text-right ${stat.avgTrade >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {stat.avgTrade >= 0 ? '+' : ''}${stat.avgTrade.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-emerald-600 dark:text-emerald-400">+${stat.bestTrade.toFixed(2)}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-right text-red-600 dark:text-red-400">${stat.worstTrade.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
          <thead className="bg-slate-50 dark:bg-slate-900/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Trade#
              </th>
              <th
                onClick={() => handleSort('entry_time')}
                className="px-4 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Entry Time <SortIcon field="entry_time" />
              </th>
              <th
                onClick={() => handleSort('exit_time')}
                className="px-4 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Exit Time <SortIcon field="exit_time" />
              </th>
              <th
                onClick={() => handleSort('side')}
                className="px-4 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Side <SortIcon field="side" />
              </th>
              <th
                onClick={() => handleSort('entry_price')}
                className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Entry Price <SortIcon field="entry_price" />
              </th>
              <th
                onClick={() => handleSort('exit_price')}
                className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Exit Price <SortIcon field="exit_price" />
              </th>
              <th
                onClick={() => handleSort('size')}
                className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Size <SortIcon field="size" />
              </th>
              <th
                onClick={() => handleSort('pnl')}
                className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                PnL <SortIcon field="pnl" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Pos %</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">Bal %</th>
              <th
                onClick={() => handleSort('commission')}
                className="px-4 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Commission <SortIcon field="commission" />
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
            {paginatedTrades.map((trade) => (
              <tr
                key={trade.trade_no}
                className={`hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors${onTradeClick ? ' cursor-pointer' : ''}`}
                onClick={() => onTradeClick?.(trade)}
              >
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                  #{trade.trade_no}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                  {formatDateTime(trade.entry_time)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                  {formatDateTime(trade.exit_time)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      trade.side === 'BUY'
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                    }`}
                  >
                    {trade.side}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100 text-right">
                  ${trade.entry_price.toLocaleString()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100 text-right">
                  ${trade.exit_price.toLocaleString()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100 text-right">
                  {trade.size}
                </td>
                <td
                  className={`px-4 py-3 whitespace-nowrap text-sm text-right font-semibold ${
                    trade.pnl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                </td>
                <td
                  className={`px-4 py-3 whitespace-nowrap text-sm text-right ${
                    trade.pnl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {(() => {
                    const posCost = trade.entry_price * trade.size;
                    if (posCost === 0) return '-';
                    const pct = (trade.pnl / posCost) * 100;
                    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
                  })()}
                </td>
                <td
                  className={`px-4 py-3 whitespace-nowrap text-sm text-right ${
                    trade.pnl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {(() => {
                    const bal = tradeBalances.get(trade.exit_time);
                    if (!bal || bal === 0) return '-';
                    const pct = (trade.pnl / bal) * 100;
                    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
                  })()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100 text-right">
                  ${trade.commission.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
            {Math.min(currentPage * itemsPerPage, sortedTrades.length)} of {sortedTrades.length}{' '}
            trades
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
