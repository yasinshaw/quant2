#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monitor V5 Bayesian Optimization Progress"""
import requests
import time

job_id = 109
API_URL = "http://localhost:8000/api/v1/backtest/jobs"

print("=" * 80)
print(f"V5 OPTIMIZATION PROGRESS MONITOR (Job ID: {job_id})")
print("=" * 80)
print("")

while True:
    response = requests.get(f"{API_URL}/{job_id}")
    if response.status_code == 200:
        job = response.json()
        status = job.get('status', 'unknown')

        print(f"\r[{time.strftime('%H:%M:%S')}] Status: {status:<15} ", end='', flush=True)

        if status == 'completed':
            print("\n✓ Optimization completed!")
            print(f"  Result: {job.get('result', {})}")
            break
        elif status == 'failed':
            print(f"\n✗ Optimization failed!")
            print(f"  Error: {job.get('error', 'Unknown error')}")
            break
        elif status == 'running':
            # 检查进度
            trials_completed = job.get('trials_completed', 0)
            total_trials = job.get('total_trials', 200)
            print(f"Progress: {trials_completed}/{total_trials} trials", end='', flush=True)
        else:
            print(f"Status: {status}")

    else:
        print(f"\rError checking status: {response.status_code}", end='', flush=True)

    time.sleep(5)  # 每5秒检查一次
