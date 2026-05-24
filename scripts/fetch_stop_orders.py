#!/usr/bin/env python3
"""Fetch OKX stop orders using ccxt with correct parameters."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.live.okx_client import OKXClient


async def main():
    print("=== Fetching OKX Stop Orders ===\n")

    client = OKXClient(
        api_key=settings.okx_api_key,
        secret_key=settings.okx_secret_key,
        passphrase=settings.okx_passphrase,
        symbol=settings.okx_symbol,
        leverage=settings.okx_leverage,
        margin_mode=settings.okx_margin_mode,
        proxy=settings.https_proxy,
    )

    try:
        # 1. Try fetch_open_orders with trigger=True
        print("1. Fetching with trigger=True...")
        try:
            orders = await client._exchange.fetch_open_orders(
                settings.okx_symbol,
                params={'trigger': True}
            )
            print(f"   Found {len(orders)} trigger orders")
            for order in orders:
                oid = order.get('id')
                print(f"\n   Order ID: {oid}")
                print(f"   Type: {order.get('type')}")
                print(f"   Side: {order.get('side')}")
                print(f"   Amount: {order.get('amount')}")
                print(f"   Status: {order.get('status')}")
                print(f"   Stop Price: {order.get('stopPrice', 'N/A')}")

                if oid == '3476991260479623168':
                    print("\n   *** THIS IS THE TARGET ORDER ***")
                    print(f"   Full order: {order}")
        except Exception as e:
            print(f"   Failed: {e}")

        # 2. Try with stop=True
        print("\n2. Fetching with stop=True...")
        try:
            orders = await client._exchange.fetch_open_orders(
                settings.okx_symbol,
                params={'stop': True}
            )
            print(f"   Found {len(orders)} stop orders")
            for order in orders:
                oid = order.get('id')
                print(f"   Order ID: {oid}")
                if oid == '3476991260479623168':
                    print(f"\n   *** TARGET ORDER FOUND ***")
                    print(f"   {order}")
        except Exception as e:
            print(f"   Failed: {e}")

        # 3. Try with ordType='conditional'
        print("\n3. Fetching with ordType='conditional'...")
        try:
            orders = await client._exchange.fetch_open_orders(
                settings.okx_symbol,
                params={'ordType': 'conditional'}
            )
            print(f"   Found {len(orders)} conditional orders")
            for order in orders:
                oid = order.get('id')
                print(f"   Order ID: {oid}")
                if oid == '3476991260479623168':
                    print(f"\n   *** TARGET ORDER FOUND ***")
                    print(f"   {order}")
        except Exception as e:
            print(f"   Failed: {e}")

        # 4. Try direct private API call
        print("\n4. Fetching via privateGetTradeOrdersAlgoPending...")
        try:
            result = await client._exchange.private_get_trade_orders_algo_pending({
                'instType': 'SWAP',
                'instId': 'ETH-USDT-SWAP',
            })
            print(f"   Response: {result}")
            orders = result.get('data', [])
            print(f"   Found {len(orders)} algo orders")
            for order in orders:
                algo_id = order.get('algoId')
                print(f"   Algo ID: {algo_id}")
                if algo_id == '3476991260479623168':
                    print(f"\n   *** TARGET ORDER FOUND ***")
                    print(f"   {order}")
        except Exception as e:
            print(f"   Failed: {e}")
            import traceback
            traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
