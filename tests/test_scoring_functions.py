"""
Unit tests for scoring functions
"""

import pytest
from backend.core.scoring_functions import calculate_composite_score, DEFAULT_WEIGHTS


def test_calculate_composite_score_with_defaults():
    """Test composite score calculation with default weights"""
    result = {
        'pnl_pct': 50.0,  # 50% return
        'sharpe_ratio': 2.0,
        'max_drawdown': 10.0,  # 10% drawdown
        'win_rate': 60.0  # 60% win rate
    }

    score = calculate_composite_score(result)

    # Score should be between 0 and 1
    assert 0 <= score <= 1
    # With good metrics, score should be decent (>0.5)
    assert score > 0.5


def test_calculate_composite_score_with_custom_weights():
    """Test with custom weights overriding defaults"""
    result = {
        'pnl_pct': 20.0,
        'sharpe_ratio': 1.0,
        'max_drawdown': 20.0,
        'win_rate': 55.0
    }

    custom_weights = {
        'sharpe_ratio': 1.0,  # Only care about Sharpe
        'total_return': 0.0,
        'max_drawdown': 0.0,
        'win_rate': 0.0
    }

    score = calculate_composite_score(result, weights=custom_weights)

    # Score should only depend on Sharpe ratio
    # sharpe_ratio = 1.0, normalized = 1.0 / 3.0 = 0.333
    expected_approx = 1.0 / 3.0  # Normalized Sharpe
    assert abs(score - expected_approx) < 0.1


def test_calculate_composite_score_handles_missing_metrics():
    """Test graceful handling of missing metrics"""
    result = {
        'pnl_pct': 10.0
        # Missing other metrics
    }

    score = calculate_composite_score(result)

    # Should not crash, return a valid score
    assert 0 <= score <= 1


def test_calculate_composite_score_negative_return():
    """Test with negative returns"""
    result = {
        'pnl_pct': -10.0,
        'sharpe_ratio': -0.5,
        'max_drawdown': 25.0,
        'win_rate': 40.0
    }

    score = calculate_composite_score(result)

    # Poor performance should give low score
    assert score < 0.3
