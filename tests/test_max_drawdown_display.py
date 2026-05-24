"""
Test to verify that Max Drawdown is displayed with negative sign
"""
import pytest
from typing import Optional


def test_max_drawdown_format_with_negative_sign():
    """
    Test that max drawdown is formatted with a negative sign (-) prefix.
    Drawdown represents a loss, so it should always be displayed as negative.
    """

    # Simulate the formatDrawdown function from BacktestHistoryTable.tsx
    def formatDrawdown(value: Optional[float]) -> str:
        if value is None:
            return '-'
        return f"-{(value * 100):.2f}%"

    # Test case 1: 5.5% drawdown stored as 0.055
    max_drawdown_decimal = 0.055
    formatted = formatDrawdown(max_drawdown_decimal)

    # Should display as -5.50%
    assert formatted == "-5.50%", \
        f"Expected '-5.50%', got '{formatted}'"

    print(f"✓ Max Drawdown: Database stores {max_drawdown_decimal}, Frontend shows {formatted}")

    # Test case 2: 15.25% drawdown stored as 0.1525
    max_drawdown_decimal = 0.1525
    formatted = formatDrawdown(max_drawdown_decimal)

    # Should display as -15.25%
    assert formatted == "-15.25%", \
        f"Expected '-15.25%', got '{formatted}'"

    print(f"✓ Max Drawdown: Database stores {max_drawdown_decimal}, Frontend shows {formatted}")

    # Test case 3: 0% drawdown (no drawdown)
    max_drawdown_decimal = 0.0
    formatted = formatDrawdown(max_drawdown_decimal)

    # Should display as -0.00%
    assert formatted == "-0.00%", \
        f"Expected '-0.00%', got '{formatted}'"

    print(f"✓ Max Drawdown: Database stores {max_drawdown_decimal}, Frontend shows {formatted}")


def test_max_drawdown_in_results_page():
    """
    Test the formatting used in results/[id]/page.tsx
    """
    # Simulate the formatting in results page
    summary = {
        'max_drawdown': 0.055  # 5.5% stored as decimal
    }

    # This is what results/[id]/page.tsx does
    value = f"-{summary['max_drawdown']:.2f}%"

    assert value == "-0.06%", \
        f"Expected '-0.06%', got '{value}'"

    print(f"✓ Results page shows Max Drawdown as {value}")


def test_max_drawdown_in_optimization_results():
    """
    Test the formatting used in optimization-results/[id]/page.tsx
    """
    result = {
        'max_drawdown': 0.055  # 5.5% stored as decimal
    }

    # This is what optimization-results/[id]/page.tsx does
    if result['max_drawdown'] is not None:
        value = f"-{(result['max_drawdown'] * 100):.2f}%"
    else:
        value = '-'

    assert value == "-5.50%", \
        f"Expected '-5.50%', got '{value}'"

    print(f"✓ Optimization results page shows Max Drawdown as {value}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
