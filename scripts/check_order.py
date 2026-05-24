#!/usr/bin/env python3
"""Check OKX order status by order ID."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.live.okx_client import OKXClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: python check_order.py <order_id>")
        sys.exit(1)

    order_id = sys.argv[1]
    print(f"Checking order: {order_id}")

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
        # First check open orders
        print("\n=== Fetching open orders ===")
        open_orders = await client.fetch_open_orders()
        print(f"Found {len(open_orders)} open orders")
        for order in open_orders:
            print(f"  - ID: {order.get('id')}")
            print(f"    Type: {order.get('type')}")
            print(f"    Side: {order.get('side')}")
            print(f"    Amount: {order.get('amount')}")
            print(f"    Status: {order.get('status')}")
            print(f"    Stop Price: {order.get('stopPrice', 'N/A')}")
            info = order.get('info', {})
            if 'posSide' in info:
                print(f"    PosSide: {info['posSide']}")
            print()

        # Then try to fetch specific order
        print(f"\n=== Fetching order {order_id} ===")
        order = await client.fetch_order(order_id)
        print(f"Order found:")
        print(f"  ID: {order.get('id')}")
        print(f"  Type: {order.get('type')}")
        print(f"  Side: {order.get('side')}")
        print(f"  Amount: {order.get('amount')}")
        print(f"  Filled: {order.get('filled')}")
        print(f"  Remaining: {order.get('remaining')}")
        print(f"  Status: {order.get('status')}")
        print(f"  Stop Price: {order.get('stopPrice', 'N/A')}")
        info = order.get('info', {})
        if 'posSide' in info:
            print(f"  PosSide: {info['posSide']}")
        if 'trigger' in info:
            print(f"  Trigger: {info['trigger']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
