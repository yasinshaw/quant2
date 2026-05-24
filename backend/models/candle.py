from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Candle(BaseModel):
    __tablename__ = 'candles'

    symbol_id = Column(Integer, ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False)
    interval = Column(String, nullable=False)  # '1m', '5m', '1h', '1d'
    open_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime, nullable=False)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Dataset relationship
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True)
    dataset = relationship("Dataset", back_populates="candles")

    # Relationships
    symbol = relationship("Symbol", back_populates="candles")

    # Indexes
    __table_args__ = (
        Index('idx_candles_lookup', 'symbol_id', 'interval', 'open_time', unique=True),
        Index('idx_candles_dataset_time', 'dataset_id', 'open_time'),
    )
