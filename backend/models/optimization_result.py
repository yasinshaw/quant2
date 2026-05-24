from sqlalchemy import Column, Integer, Float, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class OptimizationResult(BaseModel):
    __tablename__ = 'optimization_results'

    optimization_job_id = Column(Integer, ForeignKey('optimization_jobs.id', ondelete='CASCADE'), nullable=False)
    parameters = Column(JSON, nullable=False)  # Best parameters
    score = Column(Float, nullable=False)  # Score (e.g., Sharpe ratio)
    backtest_result_id = Column(Integer, ForeignKey('backtest_results.id'))

    # Existing backtest metrics
    total_return = Column(Float)  # Total return as decimal (e.g., 0.15 for 15%)
    sharpe_ratio = Column(Float)  # Sharpe ratio
    max_drawdown = Column(Float)  # Maximum drawdown as decimal (e.g., 0.10 for 10%)
    win_rate = Column(Float)  # Win rate as decimal (e.g., 0.65 for 65%)
    profit_factor = Column(Float)  # Profit factor
    total_trades = Column(Integer)  # Total number of trades
    final_value = Column(Float)  # Final portfolio value
    initial_cash = Column(Float)  # Initial cash

    # NEW: Composite score (used for Bayesian optimization)
    composite_score = Column(Float)

    # NEW: Out-of-sample flag
    is_out_of_sample = Column(Boolean, default=False)

    # NEW: Stability neighbor data (for analysis)
    stability_neighbors = Column(JSON)

    # Relationships
    optimization_job = relationship("OptimizationJob", back_populates="results")
    backtest_result = relationship("BacktestResult")
