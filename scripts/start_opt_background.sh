#!/bin/bash
# Start optimization in background and monitor

echo "Starting Bayesian optimization..."
echo "This will take 30-60 minutes."
echo ""

# Start optimization request in background
curl -X POST http://localhost:8000/api/v1/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "Trend Pullback V6",
    "symbol": "ETHUSDT",
    "interval": "1h",
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "optimization_method": "bayesian",
    "n_trials": 50,
    "enable_stability_analysis": true,
    "parameter_ranges": {
      "ema_fast": {"min": 8, "max": 16},
      "ema_slow": {"min": 22, "max": 32},
      "pullback_threshold": {"min": 35, "max": 42},
      "atr_stop_mult": {"min": 1.2, "max": 2.2},
      "adx_threshold": {"min": 15.0, "max": 22.0},
      "risk_pct": {"min": 1.0, "max": 2.0}
    },
    "fixed_parameters": {
      "rsi_period": 14,
      "rsi_exit_long": 70,
      "rsi_exit_short": 30,
      "atr_period": 14,
      "vol_scale_threshold": 1.5,
      "cb_max_losses": 3
    }
  }' > /tmp/optimization_response.json 2>&1 &

CURL_PID=$!

# Wait a bit for the request to complete
sleep 10

# Check if response was received
if [ -f /tmp/optimization_response.json ]; then
  echo "Optimization response:"
  cat /tmp/optimization_response.json | python3 -m json.tool 2>/dev/null || cat /tmp/optimization_response.json
fi

# Monitor progress
echo ""
echo "Monitoring optimization progress..."
echo "Press Ctrl+C to stop monitoring (optimization will continue)"
echo ""

while true; do
  sleep 30
  echo "[$(date '+%H:%M:%S')] Checking progress..."
  python3 scripts/check_optimization.py 2>/dev/null | grep -E "Job ID|Status|Results:" | head -10
  echo ""
done
