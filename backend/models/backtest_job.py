from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class BacktestJob(BaseModel):
    __tablename__ = 'backtest_jobs'

    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    interval = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True, default=None)
    parameters = Column(JSON, nullable=False)
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    completed_at = Column(DateTime)
    is_favorite = Column(Boolean, nullable=False, default=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="backtest_jobs")
    trades = relationship("Trade", back_populates="backtest_job", cascade="all, delete-orphan")
    result = relationship("BacktestResult", uselist=False, back_populates="backtest_job", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_backtest_status', 'status'),
        Index('idx_backtest_strategy_name', 'strategy_name'),
        Index('idx_backtest_symbol', 'symbol'),
        Index('idx_backtest_created_at', 'created_at'),
        # Composite index for common queries
        Index('idx_backtest_strategy_created', 'strategy_name', 'created_at'),
    )
