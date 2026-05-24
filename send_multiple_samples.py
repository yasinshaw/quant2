#!/usr/bin/env python3
"""Send multiple sample Feishu notifications."""
import asyncio
import sys
sys.path.insert(0, '/Users/yasin/code/quant2')

from backend.live.notifier import notify_trade, notify_error, notify_status


async def send_all_sample_notifications():
    """Send sample notifications of all types."""
    print("\n📱 Sending sample Feishu notifications...")
    print("=" * 60)

    # 1. 开仓通知
    print("\n1️⃣ Sending OPEN LONG notification...")
    await notify_trade(
        "OPEN LONG",
        "ETH/USDT:USDT",
        0.5,
        3100.0,
        3050.0,
        "KC breakout + volume spike + ADX confirmed (SAMPLE)"
    )
    await asyncio.sleep(1)

    # 2. 止损设置通知
    print("\n2️⃣ Sending STOP LOSS SET notification...")
    await notify_trade(
        "STOP LOSS SET",
        "ETH/USDT:USDT",
        0.5,
        3100.0,
        3050.0,
        "OKX Stop Order ID: stop_abc123... (SAMPLE)"
    )
    await asyncio.sleep(1)

    # 3. 止损更新通知
    print("\n3️⃣ Sending STOP LOSS UPDATED notification...")
    await notify_trade(
        "STOP LOSS UPDATED",
        "ETH/USDT:USDT",
        0.5,
        0,
        3070.0,
        "Trailing stop: 3050.00 → 3070.00 (+0.66%) (SAMPLE)"
    )
    await asyncio.sleep(1)

    # 4. 平仓通知
    print("\n4️⃣ Sending CLOSE LONG notification...")
    await notify_trade(
        "CLOSE LONG",
        "ETH/USDT:USDT",
        0.5,
        3150.0,
        0,
        "Chandelier trailing stop hit (SAMPLE)"
    )
    await asyncio.sleep(1)

    # 5. 错误通知
    print("\n5️⃣ Sending ERROR notification...")
    await notify_error(
        "Stop Order Failed",
        "Entry succeeded but stop order failed: Insufficient margin (SAMPLE)"
    )
    await asyncio.sleep(1)

    # 6. 状态通知
    print("\n6️⃣ Sending STATUS notification...")
    await notify_status(
        "Started",
        "Symbol: ETH/USDT:USDT\nTimeframe: 4h\nLeverage: 3x (SAMPLE)"
    )

    print("\n" + "=" * 60)
    print("✅ All 6 sample notifications sent!")
    print("=" * 60)

    print("\n📋 Summary of sent cards:")
    print("  1. 🟢 OPEN LONG - 绿色卡片")
    print("  2. 🛡️ STOP LOSS SET - 橙色卡片")
    print("  3. 📈 STOP LOSS UPDATED - 橙色卡片")
    print("  4. 🔵 CLOSE LONG - 橙色卡片")
    print("  5. ⚠️ ERROR - 红色卡片")
    print("  6. 🚀 STATUS - 绿色卡片")

    print("\n💡 Check your Feishu group now to see all cards!")
    print("\n📝 Note: These are SAMPLE notifications with '(SAMPLE)' marker")


if __name__ == "__main__":
    asyncio.run(send_all_sample_notifications())
