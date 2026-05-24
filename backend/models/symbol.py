from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Symbol(BaseModel):
    __tablename__ = 'symbols'

    name = Column(String, unique=True, nullable=False)  # 'BTCUSDT'
    base_currency = Column(String, nullable=False)       # 'BTC'
    quote_currency = Column(String, nullable=False)      # 'USDT'
    enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    candles = relationship("Candle", back_populates="symbol", cascade="all, delete-orphan")
