"""
Backtest API Endpoints

REST API endpoints for running backtests and parameter optimizations.
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
import bisect
import logging

from backend.database import Database
from backend.core.backtest_engine import BacktestEngine
from backend.core.optimizer import GridSearchOptimizer
from backend.core.bayesian_optimizer import BayesianOptimizer
from backend.core.stability_analyzer import StabilityAnalyzer
from backend.core.monte_carlo import MonteCarloSimulator
from backend.core.scoring_functions import DEFAULT_WEIGHTS
from backend.core.report_generator import ReportGenerator
from backend.core.strategy_loader import StrategyLoader
from backend.models.backtest_job import BacktestJob
from backend.models.optimization_job import OptimizationJob
from backend.config import settings
from backend.api.data import parse_iso_datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backtest", tags=["Backtest"])

# Global instances
_db = Database(settings.database_url)
_engine = BacktestEngine(_db)
_optimizer = GridSearchOptimizer(_engine)
_report_generator = ReportGenerator()
_strategy_loader = StrategyLoader()


@router.post("/run")
async def run_backtest(request: dict) -> Dict[str, Any]:
    """
    Run a single backtest.

    Args:
        request: Backtest request with:
            - strategy_name: Name of strategy to run
            - dataset_id: Dataset ID to use
            - start_time: Optional start time override in ISO format
            - end_time: Optional end time override in ISO format
            - parameters: Strategy parameters (optional)
            - initial_cash: Initial cash amount (optional, default: 100000)

    Returns:
        Dict containing:
            - final_value: Final portfolio value
            - pnl: Absolute profit/loss
            - pnl_pct: Percentage profit/loss
            - trades: List of trades
            - dataset: Dataset information
            - backtest_job_id: Database job ID
            - id: Same as backtest_job_id (for compatibility)

    Raises:
        HTTPException: 400 if invalid request, 404 if strategy/dataset not found, 500 if backtest fails
    """
    # Validate required fields
    required_fields = ["strategy_name", "dataset_id"]
    for field in required_fields:
        if field not in request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )

    # Load strategy
    strategies = _strategy_loader.load_all()
    strategy_name = request["strategy_name"]

    if strategy_name not in strategies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_name}' not found"
        )

    strategy_class = strategies[strategy_name]

    # Get dataset_id
    dataset_id = request["dataset_id"]

    # Validate dataset exists
    try:
        dataset = _db.get_dataset(dataset_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    # Parse optional datetime overrides
    start_dt = None
    end_dt = None
    if "start_time" in request:
        try:
            start_dt = parse_iso_datetime(request["start_time"])
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_time format: {e}"
            )

    if "end_time" in request:
        try:
            end_dt = parse_iso_datetime(request["end_time"])
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_time format: {e}"
            )

    # Get parameters
    parameters = request.get("parameters", {})
    initial_cash = request.get("initial_cash", settings.default_initial_cash)
    commission = request.get("commission", None)
    maker_rate = request.get("maker_rate", 0.0002)
    taker_rate = request.get("taker_rate", 0.0005)

    # Create backtest job
    from backend.models.backtest_job import BacktestJob
    job = BacktestJob(
        strategy_name=strategy_name,
        symbol=dataset.symbol,
        interval=dataset.interval,
        start_time=start_dt if start_dt else dataset.start_time,
        end_time=end_dt if end_dt else dataset.end_time,
        dataset_id=dataset_id,
        parameters=parameters,
        status="pending"
    )

    job_id = _db.create_backtest_job(job)
    logger.info(f"Created backtest job {job_id}")

    # Update job status to running
    _db.update_backtest_job_status(job_id, "running")

    # Run backtest
    try:
        result = await _engine.run_with_job(
            job_id=job_id,
            strategy_class=strategy_class,
            dataset_id=dataset_id,
            start_time=start_dt,
            end_time=end_dt,
            parameters=parameters,
            initial_cash=initial_cash,
            commission=commission,
            maker_rate=maker_rate,
            taker_rate=taker_rate
        )

        # Generate complete report
        from backend.models.backtest_result import BacktestResult
        from backend.models.trade import Trade

        # Create BacktestResult object for report generation
        # IMPORTANT: Convert percentage values to decimals for storage
        backtest_result = BacktestResult(
            backtest_job_id=job_id,
            total_return=result['pnl_pct'] / 100,  # Convert to decimal
            annual_return=None,
            sharpe_ratio=result.get('sharpe_ratio'),
            max_drawdown=result.get('max_drawdown', 0.0) / 100 if result.get('max_drawdown') else 0.0,  # Convert to decimal
            win_rate=result.get('win_rate', 0.0) / 100 if result.get('win_rate') else 0.0,  # Convert to decimal
            profit_factor=result.get('profit_factor', 0.0),
            total_trades=len(result.get('trades', [])),
            initial_cash=initial_cash,
            final_value=result['final_value']
        )

        # Generate report
        # Convert trade dicts to Trade objects for report generation
        from datetime import datetime
        trade_objects = []
        for trade_data in result.get('trades', []):
            trade_obj = Trade(
                backtest_job_id=job_id,
                order_id=None,
                symbol=dataset.symbol,
                side=trade_data['side'],
                price=trade_data['exit_price'],
                size=trade_data['size'],
                commission=trade_data['commission'],
                timestamp=datetime.fromisoformat(trade_data['exit_time'])
            )
            # Add pnl as an attribute (not a database field)
            trade_obj.pnl = trade_data['pnl']
            trade_objects.append(trade_obj)

        report = _report_generator.generate_report(backtest_result, trade_objects, start_dt if start_dt else dataset.start_time)

        # Merge result with report
        complete_result = {
            **result,
            **report,
            'id': result.get('backtest_result_id', job_id),  # Use backtest_result_id from result or fallback to job_id
            'backtest_job_id': job_id,  # Include job_id for reference
            'strategy_name': strategy_name,
            'start_time': (start_dt if start_dt else dataset.start_time).isoformat(),
            'end_time': (end_dt if end_dt else dataset.end_time).isoformat(),
        }

        logger.info(
            f"Backtest completed: {strategy_name} on {dataset.symbol} "
            f"PnL={result['pnl']:.2f} ({result['pnl_pct']:.2f}%), Job ID={job_id}"
        )

        # Update job status to completed
        _db.update_backtest_job_status(job_id, "completed", completed_at=datetime.now())

        return complete_result
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        _db.update_backtest_job_status(job_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}"
        )


@router.post("/optimize")
async def optimize_parameters(request: dict) -> Dict[str, Any]:
    """
    Run parameter optimization using grid search or Bayesian optimization.

    Args:
        request: Optimization request with:
            - strategy_name: Name of strategy to optimize
            - symbol: Trading pair
            - interval: K-line interval
            - start_time: Start time in ISO format
            - end_time: End time in ISO format
            - parameter_ranges: Dict of parameter names to value lists (grid) or ranges (Bayesian)
            - fixed_parameters: (optional) Dict of parameter names to fixed values
            - initial_cash: Initial cash (optional)
            - optimization_method: Optimization method (optional, default: 'grid', options: 'grid', 'bayesian')
            - n_trials: Number of trials for Bayesian optimization (optional, default: 100)
            - scoring_weights: (optional) Custom weights for composite scoring
            - enable_out_of_sample: (optional) Enable out-of-sample testing (default: false)
            - test_start_time: (optional) Test period start for out-of-sample
            - test_end_time: (optional) Test period end for out-of-sample
            - enable_stability_analysis: (optional) Enable stability analysis (default: true)

    Returns:
        Dict containing:
            - parameters: Best parameter combination
            - backtest_result: Backtest result for best parameters
            - optimization_result: OptimizationResult database object
            - stability_metrics: (optional) Stability analysis results if enabled

    Raises:
        HTTPException: 400 if invalid request, 404 if strategy not found, 500 if optimization fails
    """
    # Validate required fields
    required_fields = ["strategy_name", "symbol", "interval", "start_time", "end_time", "parameter_ranges"]
    for field in required_fields:
        if field not in request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )

    # Load strategy
    strategies = _strategy_loader.load_all()
    strategy_name = request["strategy_name"]

    if strategy_name not in strategies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_name}' not found"
        )

    strategy_class = strategies[strategy_name]

    # Parse datetime
    try:
        start_dt = parse_iso_datetime(request["start_time"])
        end_dt = parse_iso_datetime(request["end_time"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}"
        )

    # Get parameters
    initial_cash = request.get("initial_cash", settings.default_initial_cash)
    parameter_ranges = request["parameter_ranges"]
    fixed_parameters = request.get("fixed_parameters", {})
    optimization_method = request.get("optimization_method", "grid")

    # NEW: Parse optional optimization settings
    n_trials = request.get("n_trials", 100)
    scoring_weights = request.get("scoring_weights", None)  # Use defaults if None
    enable_out_of_sample = request.get("enable_out_of_sample", False)
    test_start_time = None
    test_end_time = None

    if enable_out_of_sample:
        if "test_start_time" in request:
            try:
                test_start_time = parse_iso_datetime(request["test_start_time"])
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid test_start_time format: {e}"
                )
        if "test_end_time" in request:
            try:
                test_end_time = parse_iso_datetime(request["test_end_time"])
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid test_end_time format: {e}"
                )

    enable_stability_analysis = request.get("enable_stability_analysis", True)

    # Create optimization job with new fields
    job = OptimizationJob(
        strategy_name=strategy_name,
        symbol=request["symbol"],
        interval=request["interval"],
        start_time=start_dt,
        end_time=end_dt,
        parameter_ranges=parameter_ranges,
        optimization_method=optimization_method,
        status="pending",
        scoring_weights=scoring_weights,
        test_start_time=test_start_time,
        test_end_time=test_end_time,
        enable_out_of_sample=enable_out_of_sample,
        enable_stability_analysis=enable_stability_analysis
    )

    job_id = _db.create_optimization_job(job)
    logger.info(f"Created optimization job {job_id} with method {optimization_method}")

    # Update job status to running
    _db.update_optimization_job_status(job_id, "running")

    # Run optimization
    try:
        # Select optimizer based on method
        if optimization_method == "bayesian":
            # Use Bayesian optimizer
            try:
                bayesian_optimizer = BayesianOptimizer(_engine)
                result = await bayesian_optimizer.optimize(
                    strategy_class=strategy_class,
                    symbol=request["symbol"],
                    interval=request["interval"],
                    start_time=start_dt.isoformat(),
                    end_time=end_dt.isoformat(),
                    parameter_ranges=parameter_ranges,
                    optimization_job_id=job_id,
                    n_trials=n_trials,
                    scoring_weights=scoring_weights,
                    fixed_parameters=fixed_parameters
                )
            except ImportError as e:
                # Optuna not installed
                logger.error(f"Bayesian optimization failed: {e}")
                _db.update_optimization_job_status(job_id, "failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bayesian optimization requires Optuna. Install with: pip install optuna>=3.5.0"
                )
        else:
            # Use grid search optimizer (default)
            result = await _optimizer.optimize(
                strategy_class=strategy_class,
                symbol=request["symbol"],
                interval=request["interval"],
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                parameter_ranges=parameter_ranges,
                optimization_job_id=job_id,
                fixed_parameters=fixed_parameters
            )

        # Run stability analysis if enabled
        stability_metrics = None
        if enable_stability_analysis and optimization_method in ["grid", "bayesian"]:
            try:
                stability_analyzer = StabilityAnalyzer(_engine)
                stability_metrics = await stability_analyzer.analyze_stability(
                    strategy_class=strategy_class,
                    optimal_params=result['best_result']['parameters'],
                    parameter_ranges=parameter_ranges,
                    symbol=request["symbol"],
                    interval=request["interval"],
                    start_time=start_dt,
                    end_time=end_dt,
                    optimization_job_id=job_id,
                    variation_pct=0.10,
                    samples_per_param=3
                )

                # Add stability metrics to result
                result['stability_metrics'] = stability_metrics

                logger.info(
                    f"Stability analysis completed: score={stability_metrics['stability_score']:.2f}, "
                    f"stable={stability_metrics['is_stable']}"
                )
            except Exception as e:
                logger.warning(f"Stability analysis failed (non-critical): {e}")

        logger.info(
            f"Optimization completed: {result.get('total_combinations', 'N/A')} combinations tested, "
            f"best parameters: {result['best_result']['parameters']} "
            f"with PnL={result['best_result']['pnl']:.2f} ({result['best_result']['pnl_pct']:.2f}%)"
        )

        # Update optimization job status to completed
        _db.update_optimization_job_status(job_id, "completed", completed_at=datetime.now())

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        _db.update_optimization_job_status(job_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    List backtest jobs.

    Args:
        status: Optional filter by job status ('pending', 'running', 'completed', 'failed')

    Returns:
        Dict containing:
            - jobs: List of jobs with basic info
    """
    jobs = _db.get_backtest_jobs_by_status(status=status)

    return {
        "jobs": [
            {
                "id": job.id,
                "strategy_name": job.strategy_name,
                "symbol": job.symbol,
                "status": job.status,
                "created_at": job.created_at.isoformat()
            }
            for job in jobs
        ]
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: int) -> Dict[str, Any]:
    """
    Get job status and results.

    Args:
        job_id: Job ID to retrieve

    Returns:
        Dict containing:
            - job: Job details with status
            - result: Backtest result if job is completed (optional)

    Raises:
        HTTPException: 404 if job not found
    """
    job = _db.get_backtest_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Include result if completed
    result_data = None
    if job.status == "completed":
        result = _db.get_backtest_result_by_job_id(job_id)
        if result:
            result_data = {
                "total_return": result.total_return,
                "annual_return": result.annual_return,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "total_trades": result.total_trades,
                "initial_cash": result.initial_cash,
                "final_value": result.final_value
            }

    return {
        "job": {
            "id": job.id,
            "strategy_name": job.strategy_name,
            "symbol": job.symbol,
            "interval": job.interval,
            "status": job.status,
            "is_favorite": job.is_favorite,
            "created_at": job.created_at.isoformat()
        },
        "result": result_data
    }


def _generate_report_for_result(result, result_id: int) -> Dict[str, Any]:
    """Generate a full backtest report from a BacktestResult object."""
    trades = _db.get_trades(result.backtest_job_id)
    job = _db.get_backtest_job(result.backtest_job_id)
    start_time = job.start_time if job else None

    report = _report_generator.generate_report(result, trades, start_time)

    if job:
        report['strategy_name'] = job.strategy_name
        report['parameters'] = job.parameters if job.parameters else {}
        report['backtest_start_time'] = job.start_time.isoformat() if job.start_time else None
        report['backtest_end_time'] = job.end_time.isoformat() if job.end_time else None
    else:
        logger.warning(f"BacktestJob {result.backtest_job_id} not found for result {result_id}")
        report['strategy_name'] = "Unknown"
        report['parameters'] = {}

    # Add dataset info
    if job and job.dataset_id:
        try:
            dataset = _db.get_dataset(job.dataset_id)
            report['dataset'] = {
                'id': dataset.id,
                'name': dataset.name,
                'symbol': dataset.symbol,
                'interval': dataset.interval,
                'start_time': dataset.start_time.isoformat(),
                'end_time': dataset.end_time.isoformat(),
                'candle_count': dataset.candle_count,
            }
        except Exception:
            report['dataset'] = None
    else:
        report['dataset'] = None

    # Add buy-and-hold benchmark to equity curve
    _add_benchmark_to_equity_curve(report, _db, job)

    logger.info(f"Generated report for result {result_id} with {len(trades)} trades")
    return report


def _add_benchmark_to_equity_curve(
    report: Dict[str, Any],
    db: Database,
    job: Any
) -> None:
    """Add buy-and-hold benchmark values to equity curve data points."""
    equity_curve = report.get('equity_curve', [])
    if not equity_curve or not job or not job.dataset_id:
        return

    try:
        dataset = db.get_dataset(job.dataset_id)
    except Exception:
        return

    if not dataset:
        return

    # Fetch candles covering the equity curve time range
    start_time = datetime.fromisoformat(equity_curve[0]['time'])
    end_time = datetime.fromisoformat(equity_curve[-1]['time'])
    candles = db.get_candles_by_dataset(dataset.id, start_time, end_time)

    if not candles:
        return

    # Build sorted candle timestamps and close prices
    candle_data = sorted([(c.open_time, c.close_price) for c in candles])
    candle_times = [c[0] for c in candle_data]
    candle_closes = [c[1] for c in candle_data]
    first_close = candle_closes[0]
    initial_cash = report['summary']['initial_cash']

    # For each equity curve point, find the candle at or before that time
    for point in equity_curve:
        point_time = datetime.fromisoformat(point['time'])
        idx = bisect.bisect_right(candle_times, point_time) - 1
        if idx >= 0:
            close = candle_closes[idx]
            point['benchmark'] = initial_cash * (close / first_close)


@router.get("/jobs/{job_id}/report")
async def get_report_by_job(job_id: int) -> Dict[str, Any]:
    """
    Get detailed backtest report by job ID.

    Args:
        job_id: BacktestJob ID

    Returns:
        Full backtest report (same format as /results/{result_id}/report)

    Raises:
        HTTPException: 404 if job or result not found
    """
    job = _db.get_backtest_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    result = _db.get_backtest_result_by_job_id(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result found for job {job_id}"
        )

    return _generate_report_for_result(result, result.id)


@router.post("/jobs/{job_id}/monte-carlo")
async def run_monte_carlo(job_id: int, request: dict) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a backtest job.

    Shuffles trade order N times to assess strategy robustness.

    Args:
        job_id: BacktestJob ID
        request: { num_simulations: int (100-10000, default 1000) }

    Returns:
        MonteCarloResult with distribution statistics.
    """
    num_simulations = request.get("num_simulations", 1000)
    if not isinstance(num_simulations, int) or num_simulations < 100 or num_simulations > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="num_simulations must be an integer between 100 and 10000"
        )

    # Fetch job
    job = _db.get_backtest_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed (status: {job.status})"
        )

    # Fetch result
    result = _db.get_backtest_result_by_job_id(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result found for job {job_id}"
        )

    # Fetch trades and extract PnL
    trades = _db.get_trades(job_id)
    pnl_list = [t.pnl for t in trades if hasattr(t, 'pnl') and t.pnl is not None]

    if len(pnl_list) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient trades for Monte Carlo simulation: {len(pnl_list)} (minimum 10)"
        )

    if len(pnl_list) < len(trades):
        logger.warning(
            f"Filtered {len(trades) - len(pnl_list)} trades with None pnl for job {job_id}"
        )

    # Run simulation
    try:
        mc_result = MonteCarloSimulator.simulate(
            trades_pnl=pnl_list,
            initial_cash=float(result.initial_cash),
            original_return=float(result.total_return),
            original_max_drawdown=float(result.max_drawdown),
            num_simulations=num_simulations,
        )
    except Exception as e:
        logger.error(f"Monte Carlo simulation failed for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )

    logger.info(
        f"Monte Carlo simulation completed for job {job_id}: "
        f"{num_simulations} simulations, median_return={mc_result.median_return:.4f}, "
        f"p95_dd={mc_result.p95_max_drawdown:.4f}, ruin_prob={mc_result.ruin_probability:.4f}"
    )

    return {
        "num_simulations": mc_result.num_simulations,
        "equity_curves": mc_result.equity_curves,
        "final_returns": mc_result.final_returns,
        "max_drawdowns": mc_result.max_drawdowns,
        "median_return": mc_result.median_return,
        "p5_return": mc_result.p5_return,
        "p95_return": mc_result.p95_return,
        "median_max_drawdown": mc_result.median_max_drawdown,
        "p95_max_drawdown": mc_result.p95_max_drawdown,
        "ruin_probability": mc_result.ruin_probability,
        "original_return": mc_result.original_return,
        "original_max_drawdown": mc_result.original_max_drawdown,
    }


@router.get("/results/{result_id}/report")
async def get_report(result_id: int) -> Dict[str, Any]:
    """
    Get detailed backtest report.

    Args:
        result_id: BacktestResult ID to generate report for

    Returns:
        Dict containing:
            - summary: Performance metrics summary
            - monthly_returns: Monthly returns breakdown
            - trade_analysis: Per-trade analysis with statistics
            - equity_curve: Equity curve data
            - strategy_name: Strategy used for backtest
            - parameters: Strategy parameters used

    Raises:
        HTTPException: 404 if result not found
    """
    result = _db.get_backtest_result_by_id(result_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found"
        )

    return _generate_report_for_result(result, result_id)


@router.patch("/jobs/{job_id}/favorite")
async def toggle_favorite(job_id: int) -> Dict[str, Any]:
    """Toggle favorite status for a backtest job."""
    try:
        is_favorite = _db.toggle_backtest_favorite(job_id)
        return {"job_id": job_id, "is_favorite": is_favorite}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/history")
async def get_backtest_history(
    strategy_name: Optional[str] = Query(None, description="Filter by strategy name"),
    symbol: Optional[str] = Query(None, description="Filter by trading pair"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter by job status"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    sort_by: str = Query("created_at", description="Sort field (created_at, total_return, sharpe_ratio)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)")
) -> Dict[str, Any]:
    """
    Get backtest history with filtering, sorting, and pagination.

    Args:
        strategy_name: Filter by strategy name (optional)
        symbol: Filter by trading pair (optional)
        job_status: Filter by job status (optional, query param: status)
        sort_by: Sort field ('created_at', 'total_return', 'sharpe_ratio')
        sort_order: Sort order ('asc' or 'desc')
        page: Page number (1-based)
        page_size: Number of items per page (1-100)

    Returns:
        Dict containing:
            - total: Total number of items
            - page: Current page number
            - page_size: Items per page
            - total_pages: Total number of pages
            - items: List of backtest jobs with results

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        result = _db.get_backtest_history(
            strategy_name=strategy_name,
            symbol=symbol,
            status=job_status,
            is_favorite=is_favorite,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )

        # Convert datetime objects to ISO format
        for item in result['items']:
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
            if item.get('completed_at'):
                item['completed_at'] = item['completed_at'].isoformat()
            if item.get('start_time'):
                item['start_time'] = item['start_time'].isoformat()
            if item.get('end_time'):
                item['end_time'] = item['end_time'].isoformat()

        logger.info(f"Retrieved backtest history: {len(result['items'])} items on page {page}")
        return result
    except Exception as e:
        logger.error(f"Failed to get backtest history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.delete("/jobs/{job_id}")
async def delete_backtest_job(job_id: int) -> Dict[str, Any]:
    """
    Delete a backtest job.

    Args:
        job_id: Job ID to delete

    Returns:
        Dict containing:
            - success: True
            - message: Success message

    Raises:
        HTTPException: 400 if job is running, 404 if job not found
    """
    try:
        _db.delete_backtest_job(job_id)
        logger.info(f"Deleted backtest job {job_id}")
        return {
            "success": True,
            "message": f"Backtest job {job_id} deleted successfully"
        }
    except ValueError as e:
        error_msg = str(e)
        if "running" in error_msg.lower():
            logger.warning(f"Attempted to delete running job {job_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.warning(f"Backtest job {job_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
    except Exception as e:
        logger.error(f"Failed to delete backtest job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.get("/optimization/history")
async def get_optimization_history(
    strategy_name: Optional[str] = Query(None, description="Filter by strategy name"),
    symbol: Optional[str] = Query(None, description="Filter by trading pair"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter by job status"),
    sort_by: str = Query("created_at", description="Sort field (created_at, best_score)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)")
) -> Dict[str, Any]:
    """
    Get optimization history with filtering, sorting, and pagination.

    Args:
        strategy_name: Filter by strategy name (optional)
        symbol: Filter by trading pair (optional)
        job_status: Filter by job status (optional, query param: status)
        sort_by: Sort field ('created_at', 'best_score')
        sort_order: Sort order ('asc' or 'desc')
        page: Page number (1-based)
        page_size: Number of items per page (1-100)

    Returns:
        Dict containing:
            - total: Total number of items
            - page: Current page number
            - page_size: Items per page
            - total_pages: Total number of pages
            - items: List of optimization jobs with best results

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        result = _db.get_optimization_history(
            strategy_name=strategy_name,
            symbol=symbol,
            status=job_status,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )

        # Convert datetime objects to ISO format
        for item in result['items']:
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
            if item.get('completed_at'):
                item['completed_at'] = item['completed_at'].isoformat()
            if item.get('start_time'):
                item['start_time'] = item['start_time'].isoformat()
            if item.get('end_time'):
                item['end_time'] = item['end_time'].isoformat()

        logger.info(f"Retrieved optimization history: {len(result['items'])} items on page {page}")
        return result
    except Exception as e:
        logger.error(f"Failed to get optimization history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.get("/optimization/jobs/{job_id}/results")
async def get_optimization_job_results(job_id: int) -> Dict[str, Any]:
    """
    Get all optimization results for a specific job.

    Args:
        job_id: Optimization job ID

    Returns:
        Dict containing:
            - job_id: Job ID
            - job_details: Job information
            - results: List of optimization results sorted by score (descending)
            - total_results: Total number of results

    Raises:
        HTTPException: 404 if job not found, 500 if database error occurs
    """
    try:
        # Get optimization results with backtest details in one query
        from backend.models.optimization_result import OptimizationResult

        with _db.get_session() as session:
            # Get job
            job = session.query(OptimizationJob).filter(
                OptimizationJob.id == job_id
            ).first()

            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Optimization job {job_id} not found"
                )

            # Get results with joined backtest data
            results = session.query(OptimizationResult).filter(
                OptimizationResult.optimization_job_id == job_id
            ).all()

            # Convert to dict format
            results_data = []
            for result in results:
                result_dict = {
                    'id': result.id,
                    'parameters': result.parameters,
                    'score': result.score,
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate,
                    'profit_factor': result.profit_factor,
                    'total_trades': result.total_trades,
                    'final_value': result.final_value,
                    'initial_cash': result.initial_cash
                }

                results_data.append(result_dict)

            # Sort by score descending
            results_data.sort(key=lambda x: x['score'], reverse=True)

            return {
                'job_id': job_id,
                'job_details': {
                    'strategy_name': job.strategy_name,
                    'symbol': job.symbol,
                    'interval': job.interval,
                    'start_time': job.start_time.isoformat(),
                    'end_time': job.end_time.isoformat(),
                    'status': job.status,
                    'optimization_method': job.optimization_method,
                    'created_at': job.created_at.isoformat(),
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None
                },
                'results': results_data,
                'total_results': len(results_data)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization job results: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.delete("/optimization/jobs/{job_id}")
async def delete_optimization_job(job_id: int) -> Dict[str, Any]:
    """
    Delete an optimization job.

    Args:
        job_id: Job ID to delete

    Returns:
        Dict containing:
            - success: True
            - message: Success message

    Raises:
        HTTPException: 400 if job is running, 404 if job not found
    """
    try:
        _db.delete_optimization_job(job_id)
        logger.info(f"Deleted optimization job {job_id}")
        return {
            "success": True,
            "message": f"Optimization job {job_id} deleted successfully"
        }
    except ValueError as e:
        error_msg = str(e)
        if "running" in error_msg.lower():
            logger.warning(f"Attempted to delete running optimization job {job_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.warning(f"Optimization job {job_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
    except Exception as e:
        logger.error(f"Failed to delete optimization job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.get("/optimization/jobs/{job_id}/stability")
async def get_optimization_stability(job_id: int) -> Dict[str, Any]:
    """
    Get stability analysis report for an optimization job.

    Args:
        job_id: Optimization job ID

    Returns:
        Dict containing:
            - job_id: Job ID
            - stability_score: Stability score (0-1, higher is more stable)
            - variance: Performance variance across neighbors
            - is_stable: Whether parameters are considered stable
            - neighbors: (optional) List of neighbor test results with parameters and scores

    Raises:
        HTTPException: 404 if job not found, 500 if database error occurs
    """
    try:
        from backend.models.optimization_job import OptimizationJob
        from backend.models.optimization_result import OptimizationResult

        with _db.get_session() as session:
            # Get job
            job = session.query(OptimizationJob).filter(
                OptimizationJob.id == job_id
            ).first()

            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Optimization job {job_id} not found"
                )

            # Get best result with neighbor data
            best_result = session.query(OptimizationResult).filter(
                OptimizationResult.optimization_job_id == job_id
            ).order_by(OptimizationResult.score.desc()).first()

            stability_data = {
                'job_id': job_id,
                'stability_score': job.stability_score,
                'variance': job.stability_variance,
                'is_stable': job.is_stable if job.is_stable is not None else False,
                'enable_stability_analysis': job.enable_stability_analysis
            }

            # Include neighbor data if available
            if best_result and best_result.stability_neighbors:
                stability_data['neighbors'] = best_result.stability_neighbors
                stability_data['optimal_parameters'] = best_result.parameters
                stability_data['optimal_score'] = best_result.score

            logger.info(f"Retrieved stability report for job {job_id}")
            return stability_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stability report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.get("/optimization/scoring-weights")
async def get_default_scoring_weights() -> Dict[str, Any]:
    """
    Get default scoring weights for composite scoring.

    Returns:
        Dict containing:
            - weights: Default weight configuration for composite scoring
            - description: Explanation of each weight component

    The default weights are:
        - sharpe_ratio: 0.4 (40% weight)
        - total_return: 0.3 (30% weight)
        - max_drawdown: -0.2 (20% negative weight - lower drawdown is better)
        - win_rate: 0.1 (10% weight)
    """
    return {
        "weights": DEFAULT_WEIGHTS.copy(),
        "description": {
            "sharpe_ratio": "Risk-adjusted return metric (40% weight). Higher values indicate better risk-adjusted performance.",
            "total_return": "Total return percentage (30% weight). Measures overall profitability.",
            "max_drawdown": "Maximum drawdown percentage (-20% weight). Negative because lower drawdown is better.",
            "win_rate": "Win rate percentage (10% weight). Percentage of profitable trades."
        },
        "note": "Weights can be customized by providing 'scoring_weights' in the optimize request. Weights must sum to approximately 1.0 (ignoring sign for negative weights)."
    }

