"""
Migration script to convert existing candles to dataset-based schema.
Creates one default dataset per unique symbol+interval combination.
"""
import logging
from datetime import datetime
from sqlalchemy import text
from backend.database import Database
from backend.config import settings

logger = logging.getLogger(__name__)


def migrate_existing_data():
    """
    Migrate existing candles to new dataset schema.
    Creates one default dataset per unique symbol+interval combination.
    Uses transaction for atomic rollback on failure.

    Returns:
        Number of datasets created
    """
    db = Database(settings.database_url)
    migrated_count = 0

    try:
        with db.engine.begin() as conn:  # Transaction
            # Get all distinct symbol + interval combinations
            combinations = db.get_all_symbol_interval_combinations()

            for symbol, interval in combinations:
                try:
                    # Get time range for this combination
                    time_range = db.get_time_range(symbol, interval)

                    # Get candle count that haven't been migrated yet (dataset_id = 0)
                    count_result = conn.execute(
                        text("""
                            SELECT COUNT(*) as count
                            FROM candles c
                            JOIN symbols s ON c.symbol_id = s.id
                            WHERE s.name = :symbol
                            AND c.interval = :interval
                            AND c.dataset_id = 0
                        """),
                        {"symbol": symbol, "interval": interval}
                    ).fetchone()
                    count = count_result[0]

                    # Skip if all candles already migrated
                    if count == 0:
                        logger.info(f"Skipping {symbol} {interval} - already migrated")
                        continue

                    # Create default dataset
                    now = datetime.now()
                    dataset_name = f"{symbol} {interval} Legacy Data"
                    dataset_result = conn.execute(
                        text("""
                            INSERT INTO datasets (name, symbol, interval, start_time, end_time, candle_count, created_at, updated_at)
                            VALUES (:name, :symbol, :interval, :start_time, :end_time, :count, :created_at, :updated_at)
                            RETURNING id
                        """),
                        {
                            "name": dataset_name,
                            "symbol": symbol,
                            "interval": interval,
                            "start_time": time_range.start,
                            "end_time": time_range.end,
                            "count": count,
                            "created_at": now,
                            "updated_at": now
                        }
                    )
                    dataset_id = dataset_result.fetchone()[0]

                    # Associate candles to dataset
                    conn.execute(
                        text("""
                            UPDATE candles
                            SET dataset_id = :dataset_id
                            WHERE symbol_id = (
                                SELECT id FROM symbols WHERE name = :symbol
                            )
                            AND interval = :interval
                        """),
                        {
                            "dataset_id": dataset_id,
                            "symbol": symbol,
                            "interval": interval
                        }
                    )

                    migrated_count += 1
                    logger.info(
                        f"Migrated {count} candles for {symbol} {interval} "
                        f"to dataset '{dataset_name}' (ID: {dataset_id})"
                    )

                except Exception as e:
                    logger.error(f"Failed to migrate {symbol} {interval}: {e}")
                    # Continue with next combination
                    continue

            logger.info(f"Migration complete: {migrated_count} datasets created")
            return migrated_count

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Transaction automatically rolls back
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting data migration...")
    count = migrate_existing_data()
    print(f"Migration completed successfully: {count} datasets created")
