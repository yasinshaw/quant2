"""Tests for database delete functionality"""
import pytest
from datetime import datetime
from backend.database import Database
from backend.models.candle import Candle
from backend.models.symbol import Symbol


class TestDatabaseDelete:
    def test_delete_candles_by_symbol_interval_success(self):
        """Test successful deletion of candles"""
        db = Database("sqlite:///:memory:")
        db.create_tables()

        # Insert test data
        with db.get_session() as session:
            # Create symbol first
            symbol_obj = Symbol(
                name="BTCUSDT",
                base_currency="BTC",
                quote_currency="USDT"
            )
            session.add(symbol_obj)
            session.flush()

            candle = Candle(
                symbol_id=symbol_obj.id,
                interval="1h",
                open_time=datetime(2024, 1, 1, 0, 0),
                close_time=datetime(2024, 1, 1, 1, 0),
                open_price=42000.0,
                high_price=42500.0,
                low_price=41800.0,
                close_price=42300.0,
                volume=100.5
            )
            session.add(candle)

        # Delete
        count = db.delete_candles_by_symbol_interval("BTCUSDT", "1h")
        assert count == 1

        # Verify deletion
        with db.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == "BTCUSDT"
            ).first()
            remaining = session.query(Candle).filter(
                Candle.symbol_id == symbol_obj.id,
                Candle.interval == "1h"
            ).count()
            assert remaining == 0

    def test_delete_candles_by_symbol_interval_not_found(self):
        """Test deletion when no data exists"""
        db = Database("sqlite:///:memory:")
        db.create_tables()

        count = db.delete_candles_by_symbol_interval("BTCUSDT", "1h")
        assert count == 0

    def test_delete_candles_preserves_other_intervals(self):
        """Test that deleting one interval doesn't affect others"""
        db = Database("sqlite:///:memory:")
        db.create_tables()

        # Insert candles for different intervals
        with db.get_session() as session:
            # Create symbol first
            symbol_obj = Symbol(
                name="BTCUSDT",
                base_currency="BTC",
                quote_currency="USDT"
            )
            session.add(symbol_obj)
            session.flush()

            for interval in ["1h", "4h"]:
                candle = Candle(
                    symbol_id=symbol_obj.id,
                    interval=interval,
                    open_time=datetime(2024, 1, 1, 0, 0),
                    close_time=datetime(2024, 1, 1, 1, 0),
                    open_price=42000.0,
                    high_price=42500.0,
                    low_price=41800.0,
                    close_price=42300.0,
                    volume=100.5
                )
                session.add(candle)

        # Delete only 1h
        count = db.delete_candles_by_symbol_interval("BTCUSDT", "1h")
        assert count == 1

        # Verify 4h still exists
        with db.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == "BTCUSDT"
            ).first()
            remaining = session.query(Candle).filter(
                Candle.symbol_id == symbol_obj.id,
                Candle.interval == "4h"
            ).count()
            assert remaining == 1
