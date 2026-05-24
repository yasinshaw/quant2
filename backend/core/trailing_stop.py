"""
Trailing Stop Manager

Multi-level profit locking mechanism using trailing stops.
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StopLevel:
    """Stop level configuration"""
    trigger_atr: float   # Trigger condition (profit ATR multiple)
    stop_distance: float # Stop distance (ATR multiple, negative means above entry price)
    description: str     # Description


class TrailingStopManager:
    """
    Trailing Stop Manager

    Implements multi-level profit locking mechanism:
    1. Initial stop: ATR × 1.0
    2. Break even: Profit > ATR × 1.5, move stop to entry price
    3. Lock 50%: Profit > ATR × 3.0, move stop to entry price + 1.5×ATR
    4. Lock 75%: Profit > ATR × 4.0, move stop to entry price + 3.0×ATR
    5. Lock 90%: Profit > ATR × 5.0, move stop to entry price + 4.5×ATR
    """

    # Default stop levels (sorted by trigger condition ascending)
    DEFAULT_STOP_LEVELS = [
        StopLevel(
            trigger_atr=0,
            stop_distance=1.0,
            description='Initial stop'
        ),
        StopLevel(
            trigger_atr=1.5,
            stop_distance=0,
            description='Break even'
        ),
        StopLevel(
            trigger_atr=3.0,
            stop_distance=-1.5,
            description='Lock 50% profit'
        ),
        StopLevel(
            trigger_atr=4.0,
            stop_distance=-3.0,
            description='Lock 75% profit'
        ),
        StopLevel(
            trigger_atr=5.0,
            stop_distance=-4.5,
            description='Lock 90% profit'
        ),
    ]

    # Stop levels (sorted by trigger condition ascending) - backward compatibility
    STOP_LEVELS = DEFAULT_STOP_LEVELS

    def __init__(self, custom_levels: List[Tuple[float, float]] = None):
        """
        Initialize trailing stop manager

        Args:
            custom_levels: Custom stop levels in format: [(trigger_atr, stop_distance), ...]
                         trigger_atr: Trigger condition (profit ATR multiple)
                         stop_distance: Stop distance (ATR multiple, negative means above entry price)
        """
        if custom_levels:
            # Convert custom levels to StopLevel objects
            self.STOP_LEVELS = [
                StopLevel(
                    trigger_atr=level[0],
                    stop_distance=level[1],
                    description=f'Custom level {i}'
                )
                for i, level in enumerate(custom_levels)
            ]
        else:
            # Use default levels
            self.STOP_LEVELS = self.DEFAULT_STOP_LEVELS.copy()

    def calculate_stop(
        self,
        current_price: float,
        entry_price: float,
        current_stop: Optional[float],
        atr: float,
        is_long: bool
    ) -> Optional[float]:
        """
        Calculate trailing stop price

        Args:
            current_price: Current price
            entry_price: Entry price
            current_stop: Current stop price (None means just opened position)
            atr: ATR value
            is_long: Whether it's a long position

        Returns:
            New stop price
        """
        # Calculate current profit (in ATR multiples)
        if is_long:
            profit_atr = (current_price - entry_price) / atr
        else:
            profit_atr = (entry_price - current_price) / atr

        # Calculate new stop price
        new_stop = current_stop if current_stop is not None else None

        for level in self.STOP_LEVELS:
            if profit_atr >= level.trigger_atr:
                # Calculate stop price for this level
                if is_long:
                    # Long: stop is below entry price
                    candidate_stop = entry_price - level.stop_distance * atr
                else:
                    # Short: stop is above entry price
                    candidate_stop = entry_price + level.stop_distance * atr

                # Stop can only move in favorable direction
                if new_stop is None:
                    new_stop = candidate_stop
                elif is_long and candidate_stop > new_stop:
                    # Long: stop can only move up
                    new_stop = candidate_stop
                elif not is_long and candidate_stop < new_stop:
                    # Short: stop can only move down
                    new_stop = candidate_stop

        return new_stop
