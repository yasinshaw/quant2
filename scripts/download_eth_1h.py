#!/usr/bin/env python3
"""Download ETH 1h data from Binance"""
import requests
import time
import json

API_URL = "http://localhost:8000/api/v1/data/download"

payload = {
    "symbol": "ETHUSDT",
    "interval": "1h",
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2026-04-10T23:59:59"
}

print(f"Downloading ETH 1h data from {payload['start_time']} to {payload['end_time']}")
print("This may take a few minutes...")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=600)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Download successful!")
    print(f"  Dataset ID: {result.get('dataset_id')}")
    print(f"  Dataset Name: {result.get('dataset_name')}")
    print(f"  Candles: {result.get('count')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Time: {elapsed:.1f}s")
else:
    print(f"\n✗ Download failed!")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text}")
