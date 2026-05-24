#!/usr/bin/env python3
"""
测试时区修复是否有效

运行方式：
  python scripts/test_timezone_fix.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from backend.database import Database
from backend.config import settings


def test_downloaded_data_range():
    """检查下载的数据时间范围是否正确"""

    db = Database(settings.database_url)

    # 获取ETH 4h在2026年的数据
    candles = db.get_candles(
        symbol="ETHUSDT",
        interval="4h",
        start_time="2026-01-01T00:00:00",
        end_time="2026-04-07T23:59:59"
    )

    if not candles:
        print("❌ 没有找到2026年的数据！")
        print("   请先下载数据：")
        print("   curl -X POST http://localhost:8000/api/v1/data/download \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{")
        print('       "symbol": "ETHUSDT",')
        print('       "interval": "4h",')
        print('       "start_time": "2026-01-01T00:00:00",')
        print('       "end_time": "2026-04-07T23:59:59",')
        print('       "force_download": true')
        print("     }'")
        return False

    # 检查时间范围
    first_candle = candles[0]
    last_candle = candles[-1]

    # open_time已经是datetime对象
    first_time = first_candle.open_time
    last_time = last_candle.open_time

    print(f"✅ 找到 {len(candles)} 条K线数据")
    print(f"   第一条: {first_time}")
    print(f"   最后一条: {last_time}")

    # 验证开始时间是否正确
    expected_start = datetime(2026, 1, 1, 0, 0, 0)
    if first_time.replace(tzinfo=None) == expected_start:
        print(f"✅ 开始时间正确: {first_time}")
    else:
        print(f"❌ 开始时间错误！")
        print(f"   期望: {expected_start}")
        print(f"   实际: {first_time}")
        return False

    # 验证结束时间是否在合理范围内
    expected_end_min = datetime(2026, 4, 7, 0, 0, 0)
    expected_end_max = datetime(2026, 4, 7, 23, 59, 59)

    if expected_end_min <= last_time.replace(tzinfo=None) <= expected_end_max:
        print(f"✅ 结束时间正确: {last_time}")
    else:
        print(f"❌ 结束时间错误！")
        print(f"   期望范围: {expected_end_min} ~ {expected_end_max}")
        print(f"   实际: {last_time}")
        return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("时区修复验证测试")
    print("=" * 60)
    print()

    success = test_downloaded_data_range()

    print()
    print("=" * 60)
    if success:
        print("✅ 所有测试通过！时区修复有效。")
    else:
        print("❌ 测试失败！请检查修复是否正确应用。")
    print("=" * 60)

    sys.exit(0 if success else 1)
