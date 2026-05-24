from sqlalchemy import Column, String, DateTime, JSON, Boolean, Float, Index
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class OptimizationJob(BaseModel):
    __tablename__ = 'optimization_jobs'

    # Existing fields
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    interval = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    parameter_ranges = Column(JSON, nullable=False)
    optimization_method = Column(String, default='grid', nullable=False)  # 'grid', 'genetic'
    status = Column(String, nullable=False)
    completed_at = Column(DateTime)

    # NEW: Scoring configuration
    scoring_weights = Column(JSON)  # Custom weights for composite scoring

    # NEW: Out-of-sample testing
    test_start_time = Column(DateTime)  # Test period start
    test_end_time = Column(DateTime)    # Test period end
    enable_out_of_sample = Column(Boolean, default=False)

    # NEW: Stability analysis
    enable_stability_analysis = Column(Boolean, default=True)
    stability_score = Column(Float)     # Stability score (0-1)
    stability_variance = Column(Float)  # Performance variance
    is_stable = Column(Boolean)         # Stability assessment

    # Relationships
    results = relationship("OptimizationResult", back_populates="optimization_job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_optimization_status', 'status'),
    )
