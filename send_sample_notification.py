#!/usr/bin/env python3
"""Send a sample Feishu notification card."""
import asyncio
import sys
sys.path.insert(0, '/Users/yasin/code/quant2')

from backend.live.notifier import notify_trade


async def send_sample_notification():
    """Send a sample trading notification."""
    print("\n📱 Sending sample Feishu notification...")
    print("=" * 60)

    # 发送一个开仓通知示例
    await notify_trade(
        "OPEN LONG",
        "ETH/USDT:USDT",
        0.5,
        3100.0,
        3050.0,
        "KC breakout + volume spike + ADX confirmed (TEST)"
    )

    print("\n✅ Notification sent!")
    print("=" * 60)
    print("\n📋 Expected card content:")
    print("-" * 60)
    print("🟢 **OPEN LONG**")
    print("**Symbol:** ETH/USDT:USDT")
    print("**Size:** 0.5000")
    print("**Price:** 3100.00 USDT")
    print("**Stop Loss:** 3050.00")
    print("**Reason:** KC breakout + volume spike + ADX confirmed (TEST)")
    print("-" * 60)

    print("\n💡 Please check your Feishu group to see the actual card!")


if __name__ == "__main__":
    asyncio.run(send_sample_notification())
