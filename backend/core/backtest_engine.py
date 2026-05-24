"""
Backtest Engine

Core component that executes backtests by:
1. Loading historical K-line data from database
2. Configuring and running Backtrader backtests
3. Recording trade details using TradeRecorder observer
4. Calculating performance metrics
5. Saving results to database
"""
import backtrader as bt
from typing import Dict, Any, Type, List
from datetime import datetime
import pandas as pd
import logging

from backend.core.strategy_base import StrategyBase
from backend.core.maker_taker_comm import MakerTakerCommInfo
from backend.database import Database
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade
from backend.observers.trade_recorder import TradeRecorder

logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎 - Backtest Engine

    Executes backtests using Backtrader framework with integrated
    database persistence and trade recording.

    Example:
        >>> db = Database('sqlite:///quant.db')
        >>> engine = BacktestEngine(db)
        >>> result = await engine.run(
        ...     strategy_class=MyStrategy,
        ...     dataset_id=1,
        ...     start_time=datetime(2024, 1, 1),
        ...     end_time=datetime(2024, 1, 31),
        ...     parameters={'period': 20},
        ...     initial_cash=100000.0
        ... )
    """

    def __init__(self, db: Database):
        """Initialize backtest engine

        Args:
            db: Database instance for loading data and saving results
        """
        self.db = db

    async def run(
        self,
        strategy_class: Type[StrategyBase],
        dataset_id: int,
        start_time: datetime = None,
        end_time: datetime = None,
        parameters: Dict[str, Any] = None,
        initial_cash: float = 100000.0,
        commission: float = None,
        maker_rate: float = 0.0002,
        taker_rate: float = 0.0005,
        job_id: int = None
    ) -> Dict[str, Any]:
        """
        Run backtest on specified dataset.

        Args:
            strategy_class: Strategy class to test
            dataset_id: ID of dataset to use
            start_time: Optional start time override (clipped to dataset bounds)
            end_time: Optional end time override (clipped to dataset bounds)
            parameters: Strategy parameters
            initial_cash: Initial capital
            commission: Legacy single commission rate (deprecated, use maker_rate/taker_rate)
            maker_rate: Maker (limit order) commission rate (default 0.0002 = 0.02%)
            taker_rate: Taker (market order) commission rate (default 0.0005 = 0.05%)
            job_id: Optional job ID for saving results

        Returns:
            Dict with backtest results
        """
        # Default parameters if not provided
        if parameters is None:
            parameters = {}

        # Fetch dataset metadata
        dataset = self.db.get_dataset(dataset_id)

        # Use dataset time range if not specified
        if start_time is None:
            start_time = dataset.start_time
        if end_time is None:
            end_time = dataset.end_time

        # Validate and clip time range to dataset bounds
        if start_time < dataset.start_time:
            logger.warning(f"Start time {start_time} before dataset start {dataset.start_time}, clipping")
            start_time = dataset.start_time
        if end_time > dataset.end_time:
            logger.warning(f"End time {end_time} after dataset end {dataset.end_time}, clipping")
            end_time = dataset.end_time

        if start_time >= end_time:
            raise ValueError(
                f"Invalid time range: start_time {start_time} >= end_time {end_time}"
            )

        logger.info(
            f"Starting backtest: {strategy_class.strategy_name} "
            f"on dataset '{dataset.name}' ({dataset.symbol} {dataset.interval}) "
            f"from {start_time} to {end_time}"
        )

        # Query candles by dataset_id AND time range
        candles = self.db.get_candles_by_dataset(
            dataset_id=dataset_id,
            start_time=start_time,
            end_time=end_time
        )

        if not candles:
            raise ValueError(
                f"No candles found for dataset {dataset_id} "
                f"in time range {start_time} ~ {end_time}"
            )

        logger.info(f"Running backtest with {len(candles)} candles from dataset '{dataset.name}'")

        # 2. Validate data sufficiency for strategy
        self._validate_data_sufficiency(strategy_class, parameters, len(candles))

        # 3. Create Backtrader data feed
        data = self._create_data_feed(candles)

        # 4. Configure Cerebro engine
        cerebro = bt.Cerebro(
            oldsync=True,  # Use oldsync to avoid array index issues
            tradehistory=True  # Enable trade history to get size information
        )
        cerebro.adddata(data)
        # Filter out metadata keys (prefixed with _) that are not strategy params
        clean_params = {k: v for k, v in parameters.items() if not k.startswith('_')}
        cerebro.addstrategy(strategy_class, **clean_params)
        cerebro.broker.setcash(initial_cash)
        # Use MakerTakerCommInfo for separate maker/taker rates
        if commission is not None:
            # Legacy mode: single rate → use as both maker and taker
            comminfo = MakerTakerCommInfo(maker_rate=commission, taker_rate=commission)
        else:
            comminfo = MakerTakerCommInfo(maker_rate=maker_rate, taker_rate=taker_rate)
        cerebro.broker.addcommissioninfo(comminfo)

        # 5. Add trade recorder observer
        trade_recorder = cerebro.addobserver(TradeRecorder)

        # 5.5 Add analyzers for Sharpe Ratio and Max Drawdown
        # Configure SharpeRatio for proper calculation
        # Use Days timeframe with annualization for intraday data
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio,
            _name='sharpe',
            timeframe=bt.TimeFrame.Days,
            annualize=True,
            riskfreerate=0.0  # Use 0% risk-free rate for crypto
        )
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        # 6. Execute backtest
        logger.info("Running backtest...")
        initial_value = cerebro.broker.getvalue()
        results = cerebro.run(runonce=False)  # Disable runonce mode to avoid array issues
        final_value = cerebro.broker.getvalue()

        logger.info(
            f"Backtest completed: Initial {initial_value:.2f} -> "
            f"Final {final_value:.2f}"
        )

        # 7. Extract results
        pnl = final_value - initial_cash
        pnl_pct = (pnl / initial_cash) * 100

        # Get strategy instance (first result)
        strategy = results[0]

        # Get recorded trades from TradeRecorder observer
        # The observer is attached to the strategy
        trades = []
        for observer in strategy.observers:
            if isinstance(observer, TradeRecorder):
                trades = observer.trades
                break

        # Calculate additional metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        # Calculate profit factor
        gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Extract Sharpe Ratio from analyzer
        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0)
        if sharpe_ratio is None:
            sharpe_ratio = 0.0
            logger.warning("Sharpe ratio analysis returned None, using 0.0")

        # Extract Max Drawdown from analyzer
        drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
        if max_drawdown is None:
            max_drawdown = 0.0
            logger.warning("Max drawdown analysis returned None, using 0.0")

        logger.info(f"Calculated metrics - Sharpe Ratio: {sharpe_ratio:.2f}, Max Drawdown: {max_drawdown:.2f}%")

        result = {
            'final_value': final_value,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'total_return': pnl_pct,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'initial_cash': initial_cash,
            'trades': trades,
            'backtest_start_time': start_time.isoformat(),
            'backtest_end_time': end_time.isoformat(),
            'dataset': {
                'id': dataset.id,
                'name': dataset.name,
                'symbol': dataset.symbol,
                'interval': dataset.interval,
                'start_time': dataset.start_time.isoformat(),
                'end_time': dataset.end_time.isoformat(),
                'candle_count': dataset.candle_count
            }
        }

        logger.info(
            f"Backtest results: PnL={pnl:.2f} ({pnl_pct:.2f}%), "
            f"Trades={total_trades}, WinRate={win_rate:.1f}%"
        )

        return result

    def _validate_data_sufficiency(
        self,
        strategy_class: Type[StrategyBase],
        parameters: Dict[str, Any],
        available_bars: int
    ):
        """
        Validate that available data is sufficient for strategy

        Args:
            strategy_class: Strategy class
            parameters: Strategy parameters dict
            available_bars: Number of available candles

        Raises:
            ValueError: If data is insufficient for strategy
        """
        # Get strategy parameter definitions
        param_defs = strategy_class.get_parameters()

        # Merge provided parameters with defaults
        merged_params = {}
        for param_name, param_def in param_defs.items():
            # Skip metadata keys (prefixed with _)
            if param_name.startswith('_'):
                continue
            if not isinstance(param_def, dict):
                continue
            if param_name in parameters:
                merged_params[param_name] = parameters[param_name]
            else:
                merged_params[param_name] = param_def.get('default')

        # Calculate minimum bars needed based on strategy type
        min_bars_needed = self._calculate_min_bars_needed(
            strategy_class.strategy_name,
            merged_params
        )

        # Check if we have enough data
        if available_bars < min_bars_needed:
            error_msg = (
                f"Insufficient data for strategy '{strategy_class.strategy_name}'. "
                f"Need at least {min_bars_needed} bars but only {available_bars} available. "
                f"Strategy parameters: {merged_params}. "
                f"Please download more historical data or adjust strategy parameters."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"Data sufficiency validated: {available_bars} bars available, "
            f"{min_bars_needed} bars needed"
        )

    def _calculate_min_bars_needed(
        self,
        strategy_name: str,
        params: Dict[str, Any]
    ) -> int:
        """
        Calculate minimum bars needed for a strategy

        Args:
            strategy_name: Strategy name
            params: Strategy parameters

        Returns:
            Minimum number of bars needed
        """
        # Strategy-specific minimum bar calculations
        if 'MACD' in strategy_name:
            # MACD needs slow_period + signal_period
            slow_period = params.get('slow_period', 26)
            signal_period = params.get('signal_period', 9)
            return slow_period + signal_period

        elif 'Double MA' in strategy_name or 'DoubleMA' in strategy_name:
            # Double MA needs slow_period
            slow_period = params.get('slow_period', 20)
            return slow_period

        elif 'RSI' in strategy_name:
            # RSI needs rsi_period
            rsi_period = params.get('rsi_period', 14)
            return rsi_period

        else:
            # Default: assume need at least 20 bars for any indicator
            logger.warning(
                f"Unknown strategy '{strategy_name}', using default minimum bars: 20"
            )
            return 20

    def _create_data_feed(self, candles: List) -> bt.feeds.PandasData:
        """
        Convert database candles to Backtrader data feed

        Args:
            candles: List of Candle model objects from database

        Returns:
            bt.feeds.PandasData: Backtrader data feed

        Raises:
            ValueError: If candles list is empty
        """
        if not candles:
            raise ValueError("Cannot create data feed from empty candles list")

        # Convert to pandas DataFrame
        df = pd.DataFrame([
            {
                'datetime': c.open_time,
                'open': c.open_price,
                'high': c.high_price,
                'low': c.low_price,
                'close': c.close_price,
                'volume': c.volume
            }
            for c in candles
        ])

        # Set datetime as index
        df.set_index('datetime', inplace=True)

        # Create PandasData feed
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # Use index as datetime
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1  # No open interest data
        )

        return data

    async def run_with_job(
        self,
        job_id: int,
        strategy_class: Type[StrategyBase],
        dataset_id: int,
        start_time: datetime = None,
        end_time: datetime = None,
        parameters: Dict[str, Any] = None,
        initial_cash: float = 100000.0,
        commission: float = None,
        maker_rate: float = 0.0002,
        taker_rate: float = 0.0005
    ) -> Dict[str, Any]:
        """
        Execute backtest and save results to database

        Async method that runs the backtest and saves results to database.

        Args:
            job_id: BacktestJob ID in database
            strategy_class: Strategy class
            dataset_id: Dataset ID to use
            start_time: Optional start time override
            end_time: Optional end time override
            parameters: Strategy parameters dict
            initial_cash: Initial portfolio cash
            commission: Commission rate

        Returns:
            Dict containing backtest results with database IDs

        Raises:
            ValueError: If no data found or backtest fails
        """
        # Run async backtest
        result = await self.run(
            strategy_class=strategy_class,
            dataset_id=dataset_id,
            start_time=start_time,
            end_time=end_time,
            parameters=parameters,
            initial_cash=initial_cash,
            commission=commission,
            maker_rate=maker_rate,
            taker_rate=taker_rate,
            job_id=job_id
        )

        # Save results to database
        backtest_result_id = self._save_results(
            job_id=job_id,
            result=result,
            initial_cash=initial_cash
        )

        result['backtest_result_id'] = backtest_result_id
        return result

    def _save_results(
        self,
        job_id: int,
        result: Dict[str, Any],
        initial_cash: float
    ) -> int:
        """
        Save backtest results and trades to database

        Args:
            job_id: BacktestJob ID
            result: Backtest result dict
            initial_cash: Initial cash amount

        Returns:
            int: BacktestResult ID
        """
        # Get symbol from dataset info in result
        symbol = result['dataset']['symbol']

        # Calculate additional metrics
        trades = result['trades']
        final_value = result['final_value']

        # Calculate win rate
        winning_trades = [t for t in trades if t['pnl'] > 0]
        total_trades = len(trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        # Calculate profit factor
        gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Use metrics from backtest result (calculated by analyzers)
        max_drawdown = result.get('max_drawdown', 0.0)
        sharpe_ratio = result.get('sharpe_ratio')

        # Calculate annual return (simplified - would need time period calculation)
        annual_return = None  # TODO: Calculate based on time period

        # Create BacktestResult
        backtest_result = BacktestResult(
            backtest_job_id=job_id,
            total_return=result['pnl_pct'] / 100,  # Convert to decimal (1.367% -> 0.01367)
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown / 100 if max_drawdown else 0.0,  # Convert to decimal
            win_rate=win_rate / 100 if win_rate else 0.0,  # Convert to decimal
            profit_factor=profit_factor,
            total_trades=total_trades,
            initial_cash=initial_cash,
            final_value=final_value
        )

        # Create Trade records
        trade_records = []
        for trade_data in trades:
            trade = Trade(
                backtest_job_id=job_id,
                order_id=None,  # Backtrader doesn't expose order IDs easily
                symbol=symbol,
                side=trade_data['side'],
                entry_price=trade_data.get('entry_price'),
                exit_price=trade_data.get('exit_price'),
                price=trade_data.get('exit_price'),  # Use exit price as the execution price (deprecated, kept for compatibility)
                size=trade_data['size'],
                commission=trade_data['commission'],
                pnl=trade_data.get('pnl'),
                timestamp=datetime.fromisoformat(trade_data['exit_time']),  # Keep for backward compatibility
                entry_time=datetime.fromisoformat(trade_data['entry_time']),  # New field
                exit_time=datetime.fromisoformat(trade_data['exit_time'])    # New field
            )
            trade_records.append(trade)

        # Save to database
        result_id = self.db.save_backtest_result(backtest_result, trade_records)
        logger.info(f"Saved backtest results to database: result_id={result_id}")

        return result_id
