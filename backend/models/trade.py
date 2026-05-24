from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Trade(BaseModel):
    __tablename__ = 'trades'

    backtest_job_id = Column(Integer, ForeignKey('backtest_jobs.id', ondelete='CASCADE'), nullable=False)
    order_id = Column(String)  # Backtrader order ID
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # 'BUY', 'SELL'
    entry_price = Column(Float, nullable=True)  # Entry price for position
    exit_price = Column(Float, nullable=True)  # Exit price when position closed
    price = Column(Float, nullable=False)  # Deprecated: use exit_price, kept for compatibility
    size = Column(Float, nullable=False)
    commission = Column(Float, default=0.0, nullable=False)
    pnl = Column(Float, nullable=True)  # Profit/loss for this trade
    timestamp = Column(DateTime, nullable=False)  # Exit time (deprecated name, kept for compatibility)
    entry_time = Column(DateTime, nullable=True)  # Entry time (new field)
    exit_time = Column(DateTime, nullable=True)   # Exit time (new field, more explicit than timestamp)

    # Relationships
    backtest_job = relationship("BacktestJob", back_populates="trades")

    # Indexes
    __table_args__ = (
        Index('idx_trades_backtest', 'backtest_job_id'),
    )
