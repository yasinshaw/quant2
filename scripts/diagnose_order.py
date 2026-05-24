#!/usr/bin/env python3
"""Comprehensive OKX order and account diagnosis."""
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


async def okx_request(session, method: str, request_path: str, body: str = "", proxy: str = ""):
    """Make signed OKX API request."""
    base_url = "https://www.okx.com"
    api_key = settings.okx_api_key
    secret_key = settings.okx_secret_key
    passphrase = settings.okx_passphrase

    timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    sign = sign_request(timestamp, method, request_path, body, secret_key)

    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }

    url = base_url + request_path
    kwargs = {"headers": headers, "proxy": proxy} if proxy else {"headers": headers}

    async with session.request(method, url, **kwargs) as resp:
        return await resp.json()


async def main():
    print("=== OKX Account & Order Diagnosis ===\n")

    proxy = settings.https_proxy

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Check account configuration
            print("1. Checking account config...")
            try:
                result = await okx_request(session, 'GET', '/api/v5/account/config', proxy=proxy)
                if result.get('code') == '0':
                    data = result.get('data', [])
                    if data:
                        config = data[0]
                        print(f"   Account Level: {config.get('acctLv')}")
                        print(f"   Position Mode: {config.get('posMode')}")
                        print(f"   Auto Loan: {config.get('autoLoan')}")
                else:
                    print(f"   Error: {result}")
            except Exception as e:
                print(f"   Failed: {e}")

            # 2. Check ALL algo orders (without instrument filter)
            print("\n2. Checking ALL algo orders (no filter)...")
            try:
                result = await okx_request(session, 'GET', '/api/v5/trade/order-algo-pending?instType=SWAP', proxy=proxy)
                if result.get('code') == '0':
                    orders = result.get('data', [])
                    print(f"   Found {len(orders)} algo orders")

                    for order in orders:
                        algo_id = order.get('algoId')
                        inst_id = order.get('instId')
                        print(f"\n   ┌─ Order: {algo_id}")
                        print(f"   │  Instrument: {inst_id}")
                        print(f"   │  Type: {order.get('algoType')}")
                        print(f"   │  Side: {order.get('side')}")
                        print(f"   │  PosSide: {order.get('posSide')}")
                        print(f"   │  Size: {order.get('sz')}")
                        print(f"   │  Trigger: {order.get('triggerPx')}")
                        print(f"   │  State: {order.get('state')}")

                        if algo_id == '3476991260479623168':
                            print(f"   │  *** THIS IS THE TARGET ORDER ***")
                else:
                    print(f"   API Error: {result}")
            except Exception as e:
                print(f"   Failed: {e}")
                import traceback
                traceback.print_exc()

            # 3. Check algo orders history for our specific order
            print("\n3. Checking algo order history...")
            try:
                result = await okx_request(session, 'GET', '/api/v5/trade/order-algo-history?instType=SWAP', proxy=proxy)
                if result.get('code') == '0':
                    orders = result.get('data', [])
                    print(f"   Found {len(orders)} historical orders")

                    for order in orders:
                        if order.get('algoId') == '3476991260479623168':
                            print(f"\n   *** TARGET ORDER FOUND IN HISTORY ***")
                            print(f"   Algo ID: {order.get('algoId')}")
                            print(f"   Type: {order.get('algoType')}")
                            print(f"   State: {order.get('state')}")
                            print(f"   Trigger Px: {order.get('triggerPx')}")
                            print(f"   Actual Trigger: {order.get('actualTriggerPx')}")
                            print(f"   Avg Px: {order.get('avgPx')}")
                            print(f"   Fee: {order.get('fee')}")
                            print(f"   Create Time: {order.get('cTime')}")
                            print(f"   Update Time: {order.get('uTime')}")
                else:
                    print(f"   API Error: {result}")
            except Exception as e:
                print(f"   Failed: {e}")

            # 4. Check positions to understand context
            print("\n4. Checking current positions...")
            try:
                result = await okx_request(session, 'GET', '/api/v5/account/positions?instType=SWAP', proxy=proxy)
                if result.get('code') == '0':
                    positions = result.get('data', [])
                    print(f"   Found {len(positions)} positions")

                    for pos in positions:
                        if float(pos.get('pos', 0)) != 0:
                            print(f"\n   {pos.get('instId')}:")
                            print(f"   PosSide: {pos.get('posSide')}")
                            print(f"   Size: {pos.get('pos')}")
                            print(f"   AvgPx: {pos.get('avgPx')}")
                            print(f"   Unrealized PnL: {pos.get('upl')}")
                else:
                    print(f"   API Error: {result}")
            except Exception as e:
                print(f"   Failed: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
