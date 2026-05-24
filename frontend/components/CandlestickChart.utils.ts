import type { CandlestickData, HistogramData, SeriesMarker, Time } from 'lightweight-charts';
import type { Trade } from '@/lib/api/backtest';

export interface ApiCandle {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function transformCandles(apiCandles: ApiCandle[]): CandlestickData<Time>[] {
  const deduped = deduplicateByTime(apiCandles);
  return deduped.map((c) => ({
    time: isoToTimestamp(c.open_time) as Time,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
}

export function transformVolume(apiCandles: ApiCandle[]): HistogramData<Time>[] {
  const deduped = deduplicateByTime(apiCandles);
  return deduped.map((c) => ({
    time: isoToTimestamp(c.open_time) as Time,
    value: c.volume,
    color: c.close >= c.open ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
  }));
}

function deduplicateByTime(candles: ApiCandle[]): ApiCandle[] {
  const map = new Map<number, ApiCandle>();
  for (const c of candles) {
    map.set(isoToTimestamp(c.open_time), c);
  }
  return [...map.values()].sort(
    (a, b) => isoToTimestamp(a.open_time) - isoToTimestamp(b.open_time)
  );
}

export function transformTradesToMarkers(trades: Trade[]): SeriesMarker<Time>[] {
  const markers: SeriesMarker<Time>[] = [];

  trades.forEach((trade) => {
    // Entry marker: green arrow up, below bar
    markers.push({
      time: isoToTimestamp(trade.entry_time) as Time,
      position: 'belowBar',
      color: '#26a69a',
      shape: 'arrowUp',
      text: `${trade.side}`,
      id: `trade-${trade.trade_no}-entry`,
    });

    // Exit marker: color by PnL, arrow down, above bar
    const profitable = trade.pnl >= 0;
    markers.push({
      time: isoToTimestamp(trade.exit_time) as Time,
      position: 'aboveBar',
      color: profitable ? '#26a69a' : '#ef5350',
      shape: 'arrowDown',
      text: `${profitable ? '+' : ''}${trade.pnl.toFixed(1)}`,
      id: `trade-${trade.trade_no}-exit`,
    });
  });

  // Sort by time ascending (required by lightweight-charts)
  markers.sort((a, b) => {
    const ta = typeof a.time === 'number' ? a.time : 0;
    const tb = typeof b.time === 'number' ? b.time : 0;
    return ta - tb;
  });

  return markers;
}

export function findTradeByMarkerId(markerId: string, trades: Trade[]): Trade | null {
  const match = markerId.match(/^trade-(\d+)-(entry|exit)$/);
  if (!match) return null;
  const tradeNo = parseInt(match[1], 10);
  return trades.find((t) => t.trade_no === tradeNo) ?? null;
}

function isoToTimestamp(isoString: string): number {
  return Math.floor(new Date(isoString).getTime() / 1000);
}
