#!/usr/bin/env python3
"""Check OKX order history for details."""
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
    print("=== Checking Order History ===\n")

    proxy = settings.https_proxy
    base_url = "https://www.okx.com"
    api_key = settings.okx_api_key
    secret_key = settings.okx_secret_key
    passphrase = settings.okx_passphrase

    try:
        async with aiohttp.ClientSession() as session:
            # Get detailed order history
            timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
            path = '/api/v5/trade/orders-history?instType=SWAP&limit=20'
            sign = sign_request(timestamp, 'GET', path, '', secret_key)

            headers = {
                "OK-ACCESS-KEY": api_key,
                "OK-ACCESS-SIGN": sign,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": passphrase,
                "Content-Type": "application/json",
            }

            kwargs = {"headers": headers, "proxy": proxy} if proxy else {"headers": headers}

            async with session.get(base_url + path, **kwargs) as resp:
                data = await resp.json()
                print(f"Response Code: {data.get('code')}")
                print(f"Response Msg: {data.get('msg')}")

                orders = data.get('data', [])
                print(f"\nFound {len(orders)} orders\n")

                for i, order in enumerate(orders, 1):
                    ord_id = order.get('ordId', 'N/A')
                    algo_id = order.get('algoId', 'N/A')
                    inst_id = order.get('instId')
                    state = order.get('state')
                    side = order.get('side')
                    pos_side = order.get('posSide')
                    ord_type = order.get('ordType')
                    avg_px = order.get('avgPx')
                    fill_sz = order.get('fillSz')
                    create_time = order.get('cTime')

                    print(f"{i}. Order ID: {ord_id}")
                    print(f"   Algo ID: {algo_id}")
                    print(f"   Instrument: {inst_id}")
                    print(f"   Type: {ord_type}")
                    print(f"   Side: {side} / PosSide: {pos_side}")
                    print(f"   State: {state}")
                    print(f"   Avg Price: {avg_px}")
                    print(f"   Filled: {fill_sz}")
                    print(f"   Created: {datetime.fromtimestamp(int(create_time)/1000) if create_time else 'N/A'}")

                    if algo_id == '3476991260479623168' or ord_id == '3476991260479623168':
                        print("\n   ***!!! THIS IS THE TARGET ORDER !!!***")
                        print(f"   Full data:\n")
                        for k, v in order.items():
                            print(f"   {k}: {v}")

                    print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
