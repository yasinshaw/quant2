#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 Bayesian Optimization - Calmar Priority on 4h Data"""
import requests
import time
import json

API_URL = "http://localhost:8000/api/v1/backtest/optimize"

# Calmar-focused scoring weights
scoring_weights = {
    "sharpe": 0.20,
    "calmar": 0.40,        # HIGHEST PRIORITY
    "max_drawdown": -0.25, # HEAVILY PENALIZE DRAWDOWN
    "profit_factor": 0.10,
    "win_rate": 0.00,      # IGNORE WIN RATE
    "trade_frequency": 0.05
}

# ETH 4h数据集时间分割
# 总时间: 2020-01-01 → 2026-04-10 (约6.3年)
# 训练期70%: 2020-01-01 → 2024-05-20 (约4.4年)
# 验证期30%: 2024-05-21 → 2026-04-10 (约1.9年)

payload = {
    "strategy_name": "Trend Pullback V5",
    "symbol": "ETHUSDT",
    "interval": "4h",
    "start_time": "2020-01-01T00:00:00",  # 训练期开始
    "end_time": "2024-05-20T23:59:59",    # 训练期结束（70%）
    "optimization_method": "bayesian",
    "n_trials": 200,  # 更多trial因为参数空间较大
    "parameter_ranges": {
        # 核心参数（基于V5成功配置的附近搜索）
        "ema_fast": [18, 30],
        "ema_slow": [70, 100],
        "rsi_period": [14, 21],
        "pullback_threshold": [35, 45],
        "rsi_exit_long": [65, 75],
        "rsi_exit_short": [23, 33],
        "atr_stop_mult": [1.2, 2.0],
        "risk_pct": [1.0, 2.0],

        # DD Control参数
        "adx_threshold": [15, 25],
        "vol_scale_threshold": [1.3, 1.7],
        "vol_scale_factor": [0.4, 0.6],
        "cb_max_losses": [2, 4],
        "cb_cooldown": [4, 8],
        "macro_ema_period": [180, 220],
        "dd_throttle_start": [8.0, 12.0],
        "dd_throttle_max": [18.0, 25.0],
    },
    "fixed_parameters": {
        # 固定不优化的参数
        "atr_period": 15,
        "atr_ma_period": 50,
        "max_leverage": 1.5,
        "use_adx_filter": True,
        "use_macro_filter": True,
    },
    "enable_stability_analysis": True,
    "scoring_weights": scoring_weights,
}

print("=" * 80)
print("V5 BAYESIAN OPTIMIZATION - CALMAR PRIORITY (4h Data)")
print("=" * 80)
print("Dataset: ETHUSDT 4h (2020-2026, 6 years)")
print("Training: 2020-01-01 → 2024-05-20 (70%, ~4.4 years)")
print("Validation: 2024-05-21 → 2026-04-10 (30%, ~1.9 years)")
print("")
print("Optimization Target:")
print("  - Calmar Ratio: 40% (PRIMARY)")
print("  - Max Drawdown: -25% (HEAVY PENALTY)")
print("  - Sharpe Ratio: 20%")
print("  - Profit Factor: 10%")
print("  - Trade Frequency: 5%")
print("  - Win Rate: 0% (IGNORED)")
print("")
print(f"Parameter ranges: {len(payload['parameter_ranges'])} optimized")
print(f"Fixed parameters: {len(payload['fixed_parameters'])}")
print("")
print("=" * 80)
print("Starting Bayesian optimization (200 trials)...")
print("This will take 15-30 minutes...")
print("=" * 80)
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=7200)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    job_id = result.get('job_id')
    print(f"✓ Optimization job started: {job_id}")
    print(f"  Response time: {elapsed:.1f}s")
    print("")
    print("Optimization is running in the background.")
    print("")
    print("Monitor progress:")
    print(f"  curl http://localhost:8000/api/v1/backtest/jobs/{job_id}")
    print("")
    print("Get results when complete:")
    print(f"  curl http://localhost:8000/api/v1/backtest/optimization/jobs/{job_id}/results")
else:
    print(f"✗ Failed to start optimization:")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text}")
