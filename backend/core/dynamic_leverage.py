"""
Dynamic Leverage Manager

Adjusts leverage based on account PnL status to protect capital during losses
and amplify returns during profits.
"""
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class LeverageTier:
    """Leverage tier configuration"""
    threshold: float  # PnL threshold (negative = loss, positive = profit)
    leverage: float   # Leverage multiplier
    description: str  # Description


class DynamicLeverageManager:
    """
    Dynamic Leverage Manager

    Dynamically adjusts leverage based on account PnL:
    - Lower leverage when losing to protect capital
    - Increase leverage when profitable to amplify returns
    """

    # Default leverage tiers (sorted by threshold ascending)
    DEFAULT_LEVERAGE_TIERS = [
        LeverageTier(
            threshold=-0.15,
            leverage=1.5,
            description='Severe loss, significantly reduce leverage to protect capital'
        ),
        LeverageTier(
            threshold=-0.10,
            leverage=2.0,
            description='Loss, reduce leverage'
        ),
        LeverageTier(
            threshold=0.10,
            leverage=3.0,
            description='Normal leverage'
        ),
        LeverageTier(
            threshold=0.20,
            leverage=3.5,
            description='Profit, moderately increase leverage'
        ),
        LeverageTier(
            threshold=float('inf'),
            leverage=4.0,
            description='High profit, further increase leverage'
        ),
    ]

    # Leverage limits
    MAX_LEVERAGE = 4.0
    MIN_LEVERAGE = 1.5

    def __init__(self, initial_cash: float = 10000, leverage_tiers: List[Tuple[float, float]] = None):
        """
        Initialize leverage manager

        Args:
            initial_cash: Initial capital
            leverage_tiers: Custom leverage tiers in format [(threshold, leverage), ...]
                          If None, uses default configuration
        """
        self.initial_cash = initial_cash

        # Process custom leverage tiers
        if leverage_tiers is not None:
            # Convert simplified format to LeverageTier objects
            self.leverage_tiers = []
            for i, (threshold, leverage) in enumerate(leverage_tiers):
                description = f'Custom tier {i+1}: {threshold:.2f} -> {leverage}x'
                self.leverage_tiers.append(
                    LeverageTier(threshold=threshold, leverage=leverage, description=description)
                )
        else:
            self.leverage_tiers = self.DEFAULT_LEVERAGE_TIERS

    def calculate_account_state(self, broker_value: float, initial_cash: float = None) -> float:
        """
        Calculate account PnL percentage

        Args:
            broker_value: Current account value
            initial_cash: Initial capital (defaults to self.initial_cash)

        Returns:
            PnL percentage
        """
        if initial_cash is None:
            initial_cash = self.initial_cash

        if initial_cash <= 0:
            raise ValueError(f"initial_cash must be positive, got {initial_cash}")

        if broker_value < 0:
            raise ValueError(f"broker_value cannot be negative, got {broker_value}")

        pnl_pct = (broker_value - initial_cash) / initial_cash
        return pnl_pct

    def get_leverage(self, account_pnl_pct: float) -> float:
        """
        Return leverage multiplier based on account PnL percentage

        Args:
            account_pnl_pct: Account PnL percentage

        Returns:
            Leverage multiplier
        """
        # Iterate through leverage tiers to find the first matching tier
        for tier in self.leverage_tiers:
            if account_pnl_pct <= tier.threshold:
                return tier.leverage

        # If none match, return the last tier's leverage
        return self.leverage_tiers[-1].leverage if self.leverage_tiers else 3.0

    def get_leverage_for_value(self, account_value: float) -> float:
        """
        Convenience method to get leverage based on account value

        Args:
            account_value: Current account value

        Returns:
            Leverage multiplier
        """
        pnl_pct = self.calculate_account_state(account_value, self.initial_cash)
        return self.get_leverage(pnl_pct)

    def get_tier_description(self, account_value: float) -> str:
        """
        Get current tier description

        Args:
            account_value: Current account value

        Returns:
            Tier description
        """
        pnl_pct = self.calculate_account_state(account_value, self.initial_cash)

        # Iterate through leverage tiers to find the first matching tier
        for tier in self.leverage_tiers:
            if pnl_pct <= tier.threshold:
                return tier.description

        # If none match, return the last tier's description
        return self.leverage_tiers[-1].description if self.leverage_tiers else 'Unknown'
