from sqlalchemy import Column, String, Boolean
from backend.models.base import BaseModel


class HiddenStrategy(BaseModel):
    """Tracks strategies hidden from the UI"""
    __tablename__ = 'hidden_strategies'

    strategy_name = Column(String, unique=True, nullable=False, index=True)
    is_hidden = Column(Boolean, default=True, nullable=False)
