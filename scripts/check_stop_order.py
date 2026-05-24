#!/usr/bin/env python3
"""Check OKX stop/algorithm orders using direct API call."""
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


async def main():
    print("Checking OKX stop/algo orders via direct API...")

    base_url = "https://www.okx.com"
    api_key = settings.okx_api_key
    secret_key = settings.okx_secret_key
    passphrase = settings.okx_passphrase

    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }

    proxy = settings.https_proxy

    try:
        async with aiohttp.ClientSession() as session:
            # Check pending stop/algo orders
            print("\n=== Fetching pending STOP/ALGO orders ===")
            timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
            request_path = '/api/v5/trade/order-algo-pending?instType=SWAP&instId=ETH-USDT-SWAP'
            sign = sign_request(timestamp, 'GET', request_path, '', secret_key)

            headers["OK-ACCESS-SIGN"] = sign
            headers["OK-ACCESS-TIMESTAMP"] = timestamp

            kwargs = {"headers": headers, "proxy": proxy} if proxy else {"headers": headers}
            async with session.get(base_url + request_path, **kwargs) as resp:
                data = await resp.json()
                print(f"Response code: {data.get('code')}")
                print(f"Response msg: {data.get('msg')}")

                orders = data.get("data", [])
                print(f"Found {len(orders)} pending algo orders")

                for order in orders:
                    algo_id = order.get('algoId')
                    print(f"\n  Algo ID: {algo_id}")
                    print(f"  Type: {order.get('algoType')}")
                    print(f"  Side: {order.get('side')}")
                    print(f"  Pos Side: {order.get('posSide')}")
                    print(f"  Size: {order.get('sz')}")
                    print(f"  Trigger Price: {order.get('triggerPx')}")
                    print(f"  Status: {order.get('state')}")
                    print(f"  Create Time: {order.get('cTime')}")

                    if algo_id == '3476991260479623168':
                        print("\n  *** THIS IS THE TARGET ORDER ***")

            # Check algo order history
            print("\n=== Fetching algo order history ===")
            timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
            request_path = '/api/v5/trade/order-algo-history?instType=SWAP&instId=ETH-USDT-SWAP'
            sign = sign_request(timestamp, 'GET', request_path, '', secret_key)

            headers["OK-ACCESS-SIGN"] = sign
            headers["OK-ACCESS-TIMESTAMP"] = timestamp

            kwargs = {"headers": headers, "proxy": proxy} if proxy else {"headers": headers}
            async with session.get(base_url + request_path, **kwargs) as resp:
                data = await resp.json()
                history = data.get("data", [])
                print(f"Found {len(history)} historical algo orders")

                for order in history:
                    if order.get('algoId') == '3476991260479623168':
                        print(f"\n  *** TARGET ORDER FOUND IN HISTORY ***")
                        print(f"  Algo ID: {order.get('algoId')}")
                        print(f"  Type: {order.get('algoType')}")
                        print(f"  Status: {order.get('state')}")
                        print(f"  Trigger Price: {order.get('triggerPx')}")
                        print(f"  Actual Trigger: {order.get('actualTriggerPx', 'N/A')}")
                        print(f"  Create Time: {order.get('cTime')}")
                        print(f"  Update Time: {order.get('uTime')}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
