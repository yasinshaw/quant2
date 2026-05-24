#!/usr/bin/env python3
"""
Test position sizing calculation with correct contract unit conversion.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from live.strategy import VolSqueezeSignalGenerator
from config import settings

print("=== Position Sizing Test ===")
print()

# Load strategy from config (should use optimized parameters)
strategy = VolSqueezeSignalGenerator.from_config(settings)

print("Strategy Parameters:")
print(f"  leverage: {strategy.p.leverage}x")
print(f"  position_pct: {strategy.p.position_pct}")
print(f"  risk_pct: {strategy.p.risk_pct}%")
print(f"  dd_throttle_start: {strategy.p.dd_throttle_start}%")
print(f"  dd_throttle_max: {strategy.p.dd_throttle_max}%")
print()

# Simulate the previous trade scenario
equity = 100.0
entry_price = 2372.06
stop_price = 2288.47
throttle = 1.0  # No DD
squeeze_bonus = 1.0  # No squeeze

print("Trade Scenario:")
print(f"  Account equity: {equity} USDT")
print(f"  Entry price: {entry_price}")
print(f"  Stop price: {stop_price}")
print(f"  Throttle: {throttle}")
print(f"  Squeeze bonus: {squeeze_bonus}")
print()

# Calculate position size
size = strategy._calc_position_size(equity, entry_price, stop_price, throttle, squeeze_bonus)

print("=== Position Sizing Calculation ===")
print(f"Final position size: {size:.6f} ETH")
print()

# Convert to OKX contracts
CONTRACT_SIZE = 0.1  # ETH per contract
contracts = size / CONTRACT_SIZE
print(f"OKX contracts: {contracts:.4f} contracts (0.1 ETH/contract)")
print()

# Calculate margin
margin = size * entry_price / strategy.p.leverage
print(f"Required margin: {margin:.2f} USDT")
print()

# Calculate risk
risk_per_unit = abs(entry_price - stop_price)
risk = size * risk_per_unit
risk_pct = risk / equity * 100
print(f"Stop loss risk: {risk:.2f} USDT ({risk_pct:.2f}% of equity)")
print()

# Compare with actual previous trade
print("=== Comparison with Previous Trade ===")
print("Previous (WRONG unit):")
print(f"  Strategy calculated: 0.1059 ETH")
print(f"  Sent to OKX: 0.1059 contracts (treated as contracts!)")
print(f"  Actual filled: 0.1 contracts = 0.01 ETH")
print(f"  Margin: ~5.9 USDT")
print(f"  Risk: ~0.84 USDT (0.84%)")
print()

print("After FIX:")
print(f"  Strategy calculates: {size:.6f} ETH")
print(f"  Convert to contracts: {contracts:.4f} contracts")
print(f"  Expected margin: {margin:.2f} USDT")
print(f"  Expected risk: {risk:.2f} USDT ({risk_pct:.2f}%)")
print()

print("=== Summary ===")
if abs(size - 0.0359) < 0.001:
    print("✓ Position sizing is CORRECT! (~0.036 ETH)")
    print(f"✓ Expected margin: {margin:.0f} USDT (not {margin/4:.0f} USDT)")
    print(f"✓ Expected risk: {risk:.1f}% (not {risk/3:.1f}%)")
else:
    print("✗ Position sizing may still have issues")
