#!/usr/bin/env python3
"""Check optimization status"""
import sqlite3
import json
from datetime import datetime

DB_PATH = "data/quant.db"

print("Checking recent optimization jobs...")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get recent optimization jobs
cursor.execute("""
    SELECT id, strategy_name, symbol, interval, status,
           start_time, end_time, optimization_method
    FROM optimization_jobs
    WHERE strategy_name LIKE '%V6%'
    ORDER BY created_at DESC
    LIMIT 5
""")

jobs = cursor.fetchall()

if not jobs:
    print("No V6 optimization jobs found yet.")
    print("Optimization may still be starting...")
else:
    for job in jobs:
        job_id, strategy, symbol, interval, status, start, end, method = job
        print(f"\nJob ID: {job_id}")
        print(f"Strategy: {strategy}")
        print(f"Symbol: {symbol} {interval}")
        print(f"Period: {start} → {end}")
        print(f"Method: {method}")
        print(f"Status: {status}")

        # Get results count
        cursor.execute("""
            SELECT COUNT(*) FROM optimization_results WHERE optimization_job_id = ?
        """, (job_id,))
        result_count = cursor.fetchone()[0]
        print(f"Results: {result_count} trials completed")

        if status == "completed":
            # Get best result
            cursor.execute("""
                SELECT parameters, composite_score, total_return, sharpe_ratio,
                       max_drawdown, total_trades
                FROM optimization_results
                WHERE optimization_job_id = ?
                ORDER BY composite_score DESC
                LIMIT 1
            """, (job_id,))
            best = cursor.fetchone()
            if best:
                params, score, ret, sharpe, dd, trades = best
                print(f"\n✓ Best Result:")
                print(f"  Score: {score:.4f}")
                print(f"  Return: {ret*100:.2f}%")
                print(f"  Sharpe: {sharpe:.2f}")
                print(f"  Max DD: {dd*100:.2f}%")
                print(f"  Trades: {trades}")
                print(f"  Params: {json.loads(params)}")

conn.close()
