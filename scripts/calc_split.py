#!/usr/bin/env python3
"""Calculate 70/30 time split for dataset"""
from datetime import datetime, timedelta

start = datetime(2022, 1, 1)
end = datetime(2026, 4, 10)

total_days = (end - start).days
training_days = int(total_days * 0.70)
validation_days = total_days - training_days

training_end = start + timedelta(days=training_days)

print(f"Total Range: {start.date()} → {end.date()} ({total_days} days)")
print(f"\n70/30 Split:")
print(f"Training:   {start.date()} → {training_end.date()} ({training_days} days, 70%)")
print(f"Validation: {training_end.date()} → {end.date()} ({validation_days} days, 30%)")
