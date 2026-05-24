from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Dataset(BaseModel):
    """Dataset model - represents a collection of candles for a specific time range"""

    __tablename__ = 'datasets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)  # Not unique - allows duplicates
    symbol = Column(String(20), nullable=False)
    interval = Column(String(10), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    candle_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    candles = relationship("Candle", back_populates="dataset", cascade="all, delete-orphan")
    backtest_jobs = relationship("BacktestJob", back_populates="dataset")

    # Indexes for performance
    __table_args__ = (
        Index('idx_datasets_symbol_interval', 'symbol', 'interval'),
        Index('idx_datasets_created_at', 'created_at'),
        Index('idx_datasets_name', 'name'),
    )
