#!/usr/bin/env python3
"""Cancel the orphaned stop order 3476991260479623168."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.live.okx_client import OKXClient


async def main():
    print("=== Cancelling Orphaned Stop Order ===\n")

    client = OKXClient(
        api_key=settings.okx_api_key,
        secret_key=settings.okx_secret_key,
        passphrase=settings.okx_passphrase,
        symbol=settings.okx_symbol,
        proxy=settings.https_proxy,
    )

    try:
        order_id = "3476991260479623168"

        print(f"Cancelling stop order: {order_id}")

        result = await client.cancel_order(order_id, stop_order=True)

        print(f"\n✅ Cancel result: {result}")
        print(f"Status: {result.get('status', 'unknown')}")

    except Exception as e:
        print(f"\n❌ Failed to cancel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
