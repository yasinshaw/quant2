from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class BacktestResult(BaseModel):
    __tablename__ = 'backtest_results'

    backtest_job_id = Column(Integer, ForeignKey('backtest_jobs.id', ondelete='CASCADE'), unique=True, nullable=False)
    total_return = Column(Float, nullable=False)
    annual_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float, nullable=False)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    initial_cash = Column(Float, nullable=False)
    final_value = Column(Float, nullable=False)

    # Relationships
    backtest_job = relationship("BacktestJob", back_populates="result")
