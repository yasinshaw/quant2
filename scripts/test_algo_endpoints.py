#!/usr/bin/env python3
"""Test different OKX API endpoints to find the correct one."""
import asyncio
import sys
import hmac
import base64
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
import aiohttp


def sign_request(timestamp: str, method: str, request_path: str, body: str, secret_key: str) -> str:
    """Generate OKX API signature."""
    message = timestamp + method + request_path + body
    mac = hmac.new(
        bytes(secret_key, encoding='utf8'),
        bytes(message, encoding='utf-8'),
        digestmod='sha256'
    )
    return base64.b64encode(mac.digest()).decode()


async def test_endpoint(session, endpoint_name: str, path: str, proxy: str = ""):
    """Test an OKX API endpoint."""
    base_url = "https://www.okx.com"
    api_key = settings.okx_api_key
    secret_key = settings.okx_secret_key
    passphrase = settings.okx_passphrase

    timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    sign = sign_request(timestamp, 'GET', path, '', secret_key)

    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }

    url = base_url + path
    kwargs = {"headers": headers, "proxy": proxy} if proxy else {"headers": headers}

    try:
        async with session.get(url, **kwargs) as resp:
            data = await resp.json()
            code = data.get('code', resp.status)
            msg = data.get('msg', '')
            data_count = len(data.get('data', []))

            print(f"  [{code}] {endpoint_name}")
            print(f"      Path: {path}")
            print(f"      Count: {data_count} orders")
            if data_count > 0:
                for order in data.get('data', [])[:3]:  # Show first 3
                    print(f"        - {order.get('algoId', order.get('ordId', 'N/A'))}: {order.get('state', 'N/A')}")
            print()

            return data
    except Exception as e:
        print(f"  [ERR] {endpoint_name}: {e}\n")
        return None


async def main():
    print("=== Testing OKX Order Endpoints ===\n")

    proxy = settings.https_proxy

    try:
        async with aiohttp.ClientSession() as session:
            # Test different endpoints
            endpoints = [
                ("Algo Pending (SWAP only)", "/api/v5/trade/order-algo-pending?instType=SWAP"),
                ("Algo Pending (ALL)", "/api/v5/trade/order-algo-pending"),
                ("Algo History (SWAP)", "/api/v5/trade/order-algo-history?instType=SWAP"),
                ("Algo History (ALL)", "/api/v5/trade/order-algo-history"),
                ("Order Pending (SWAP)", "/api/v5/trade/orders-pending?instType=SWAP"),
                ("Order Pending (ALL)", "/api/v5/trade/orders-pending"),
                ("Order History (SWAP)", "/api/v5/trade/orders-history?instType=SWAP"),
                ("Order History (ALL)", "/api/v5/trade/orders-history"),
            ]

            for name, path in endpoints:
                result = await test_endpoint(session, name, path, proxy)

                # Check if our target order appears
                if result and result.get('data'):
                    for order in result.get('data', []):
                        oid = order.get('algoId') or order.get('ordId')
                        if oid == '3476991260479623168':
                            print(f"\n  ***!!! TARGET ORDER FOUND in {name} !!!***")
                            print(f"  {order}\n")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
