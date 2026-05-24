"""
Observers package for Backtrader observers

This package contains custom Backtrader observers for tracking
backtest execution and results.
"""
from backend.observers.trade_recorder import TradeRecorder

__all__ = ['TradeRecorder']
