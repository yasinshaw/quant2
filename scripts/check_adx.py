#!/usr/bin/env python3
import json
import pandas as pd
import numpy as np
from datetime import datetime

# 计算 ADX
def calculate_adx(high, low, close, period=12):
    # 计算 True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # 计算 +DM 和 -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    # 平滑
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr.rolling(period).mean())
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr.rolling(period).mean())

    # 计算 DX 和 ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()

    return adx, plus_di, minus_di

# 获取数据
import requests
response = requests.get('http://localhost:8000/api/v1/live/klines?timeframe=4h&limit=100')
data = response.json()

# 转换为 DataFrame
df = pd.DataFrame(data['data'])
df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']

# 计算 ADX
adx, plus_di, minus_di = calculate_adx(df['high'], df['low'], df['close'], 12)

# 显示最新的 ADX 值
latest_adx = adx.iloc[-1]
latest_plus_di = plus_di.iloc[-1]
latest_minus_di = minus_di.iloc[-1]

print("=== ADX 趋势指标 (周期=12) ===")
print(f"当前 ADX: {latest_adx:.2f}")
print(f"+DI (上升方向): {latest_plus_di:.2f}")
print(f"-DI (下降方向): {latest_minus_di:.2f}")
print()
print("=== 趋势判断 ===")
if latest_adx < 20:
    trend = "弱趋势/震荡"
elif latest_adx < 25:
    trend = "中等趋势"
else:
    trend = "强趋势"

print(f"趋势强度: {trend}")
print()
print(f"策略阈值要求: ADX > 24")
print(f"是否满足做多: {'✅ 是' if latest_adx > 24 else '❌ 否 (ADX不够)'}")
print()
print("=== 最近10根K线的ADX变化 ===")
for i in range(-10, 0):
    adx_val = adx.iloc[i]
    dt = datetime.fromtimestamp(df['time'].iloc[i])
    print(f"{dt.strftime('%m-%d %H:%M')} | ADX: {adx_val:.2f} | +DI: {plus_di.iloc[i]:.2f} | -DI: {minus_di.iloc[i]:.2f}")

# 检查 +DI 和 -DI 的关系
print()
print("=== 趋势方向判断 ===")
if latest_plus_di > latest_minus_di:
    direction = "上升趋势"
else:
    direction = "下降趋势"
print(f"方向: {direction} (+DI vs -DI: {latest_plus_di:.2f} vs {latest_minus_di:.2f})")
