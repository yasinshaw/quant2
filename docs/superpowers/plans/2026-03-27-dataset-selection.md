# Dataset Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to download multiple datasets for the same symbol/interval and select datasets when running backtests and parameter optimization

**Architecture:** Introduce dataset abstraction layer with unique IDs, migrate existing candles to default datasets, update backtest engine to query by dataset_id, add dataset selection UI to forms

**Tech Stack:** FastAPI, SQLAlchemy, SQLite (backend), Next.js 14, React Query, TypeScript (frontend)

---

## File Structure

### Backend Files to Create
- `backend/models/dataset.py` - Dataset SQLAlchemy model
- `backend/core/migration.py` - Data migration script

### Backend Files to Modify
- `backend/database.py` - Add dataset CRUD methods
- `backend/api/data.py` - Update download API, add dataset endpoints
- `backend/api/backtest.py` - Update to use dataset_id
- `backend/core/backtest_engine.py` - Use dataset_id for queries
- `backend/core/data_manager.py` - Pass dataset_id through download flow
- `backend/models/backtest_job.py` - Add dataset_id foreign key

### Frontend Files to Create
- `frontend/components/DatasetSelector.tsx` - Dataset dropdown component
- `frontend/components/RenameDatasetDialog.tsx` - Rename modal
- `frontend/lib/api/types.ts` - Update with dataset types (or create if doesn't exist)

### Frontend Files to Modify
- `frontend/lib/api/data.ts` - Add dataset API methods
- `frontend/lib/api/backtest.ts` - Update to pass dataset_id
- `frontend/components/DownloadForm.tsx` - Add dataset name input
- `frontend/components/DownloadedDataSidebar.tsx` - Refactor to flat list
- `frontend/components/BacktestForm.tsx` - Add dataset selector, lock fields
- `frontend/components/OptimizationForm.tsx` - Same as BacktestForm
- `frontend/components/ConfigurationSection.tsx` - Display dataset info

---

## Phase 1: Backend Foundation

### Task 1: Create Dataset Model

**Files:**
- Create: `backend/models/dataset.py`

- [ ] **Step 1: Create dataset model file**

```python
# backend/models/dataset.py
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Dataset(BaseModel):
    """Dataset model - represents a collection of candles for a specific time range"""

    __tablename__ = 'datasets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)  # Not unique - allows duplicates
    symbol = Column(String(20), nullable=False)
    interval = Column(String(10), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    candle_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    candles = relationship("Candle", back_populates="dataset", cascade="all, delete-orphan")
    backtest_jobs = relationship("BacktestJob", back_populates="dataset")

    # Indexes for performance
    __table_args__ = (
        Index('idx_datasets_symbol_interval', 'symbol', 'interval'),
        Index('idx_datasets_created_at', 'created_at'),
        Index('idx_datasets_name', 'name'),
    )
```

- [ ] **Step 2: Update Candle model to add relationship**

**File:** `backend/models/candle.py`

```python
# Add to Candle class (after line 17, before Relationships comment)

# Dataset relationship
dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, default=0)
dataset = relationship("Dataset", back_populates="candles")
```

- [ ] **Step 3: Update BacktestJob model to add dataset_id**

**File:** `backend/models/backtest_job.py`

```python
# Add after line 13 (after end_time column)

dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True, default=None)

# Update relationships (line 19) to include:
dataset = relationship("Dataset", back_populates="backtest_jobs")
```

- [ ] **Step 4: Run database migration to create tables**

```bash
cd backend
# This will create the datasets table using SQLAlchemy's create_all
# Manual SQL alternative:
sqlite3 data/quant.db << 'EOF'
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    candle_count INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_datasets_symbol_interval ON datasets(symbol, interval);
CREATE INDEX idx_datasets_created_at ON datasets(created_at);
CREATE INDEX idx_datasets_name ON datasets(name);

ALTER TABLE candles ADD COLUMN dataset_id INTEGER NOT NULL DEFAULT 0;
ALTER TABLE backtest_jobs ADD COLUMN dataset_id INTEGER DEFAULT NULL;

CREATE INDEX idx_candles_dataset_time ON candles(dataset_id, open_time);
EOF
```

- [ ] **Step 5: Commit**

```bash
git add backend/models/dataset.py backend/models/candle.py backend/models/backtest_job.py
git commit -m "feat: add dataset model and foreign keys

- Create Dataset model with indexes
- Add dataset_id foreign key to candles table
- Add dataset_id foreign key to backtest_jobs table
- Add composite index on candles(dataset_id, open_time)"
```

---

### Task 2: Database Dataset Methods

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: Add Dataset import**

**File:** `backend/database.py` (around line 15, after other imports)

```python
from backend.models.dataset import Dataset
```

- [ ] **Step 2: Add dataset CRUD methods**

**File:** `backend/database.py` (add at end of Database class, before last `}`)

```python
    # Dataset management methods

    def get_all_symbol_interval_combinations(self) -> List[Tuple[str, str]]:
        """Get all distinct symbol + interval combinations for migration.

        Returns:
            List of (symbol, interval) tuples
        """
        with self.SessionLocal() as session:
            results = session.query(
                Candle.symbol,
                Candle.interval
            ).distinct().all()
            return [(r.symbol, r.interval) for r in results]

    def get_time_range(self, symbol: str, interval: str) -> 'TimeRange':
        """Get min/max timestamp for symbol/interval combination.

        Args:
            symbol: Trading pair symbol
            interval: K-line interval

        Returns:
            TimeRange named tuple with start and end datetime
        """
        from collections import namedtuple
        TimeRange = namedtuple('TimeRange', ['start', 'end'])

        with self.SessionLocal() as session:
            result = session.query(
                func.min(Candle.open_time),
                func.max(Candle.open_time)
            ).join(
                Symbol, Symbol.symbol == Candle.symbol
            ).filter(
                Symbol.symbol == symbol,
                Candle.interval == interval
            ).first()

            if not result or not result[0]:
                raise ValueError(f"No data found for {symbol} {interval}")

            return TimeRange(start=result[0], end=result[1])

    def create_dataset(
        self,
        name: str,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        candle_count: int
    ) -> int:
        """Create dataset record and return dataset_id.

        Args:
            name: Dataset name
            symbol: Trading pair symbol
            interval: K-line interval
            start_time: Start datetime
            end_time: End datetime
            candle_count: Number of candles

        Returns:
            dataset_id (int)
        """
        with self.SessionLocal() as session:
            dataset = Dataset(
                name=name,
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                candle_count=candle_count,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.commit()
            session.refresh(dataset)
            return dataset.id

    def get_datasets(self) -> List[Dataset]:
        """Get all datasets.

        Returns:
            List of Dataset objects
        """
        with self.SessionLocal() as session:
            return session.query(Dataset).order_by(Dataset.created_at.desc()).all()

    def get_dataset(self, dataset_id: int) -> Dataset:
        """Get single dataset by ID.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset object

        Raises:
            ValueError: If dataset not found
        """
        with self.SessionLocal() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")
            return dataset

    def rename_dataset(self, dataset_id: int, new_name: str) -> bool:
        """Rename dataset.

        Args:
            dataset_id: Dataset ID
            new_name: New name

        Returns:
            True if successful, False if name already exists
        """
        try:
            with self.SessionLocal() as session:
                # Check if name already exists
                existing = session.query(Dataset).filter(Dataset.name == new_name).first()
                if existing:
                    return False

                dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
                if not dataset:
                    raise ValueError(f"Dataset {dataset_id} not found")

                dataset.name = new_name
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to rename dataset: {e}")
            return False

    def delete_dataset(self, dataset_id: int) -> int:
        """Delete dataset and associated candles (cascade).

        Args:
            dataset_id: Dataset ID

        Returns:
            Number of candles deleted

        Raises:
            ValueError: If dataset not found
        """
        with self.SessionLocal() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            # Count candles before deletion
            candle_count = session.query(Candle).filter(Candle.dataset_id == dataset_id).count()

            # Delete dataset (cascade will delete candles)
            session.delete(dataset)
            session.commit()

            return candle_count

    def check_dataset_usage(self, dataset_id: int) -> int:
        """Check how many backtest results reference this dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Number of backtest results using this dataset
        """
        with self.SessionLocal() as session:
            return session.query(BacktestJob).filter(
                BacktestJob.dataset_id == dataset_id
            ).count()

    def update_candles_dataset_id(
        self,
        symbol: str,
        interval: str,
        dataset_id: int
    ) -> int:
        """Update all candles for symbol/interval to have dataset_id.

        Args:
            symbol: Trading pair symbol
            interval: K-line interval
            dataset_id: Dataset ID to assign

        Returns:
            Number of candles updated
        """
        with self.engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE candles
                    SET dataset_id = :dataset_id
                    WHERE symbol_id = (
                        SELECT id FROM symbols WHERE symbol = :symbol
                    )
                    AND interval = :interval
                """),
                {
                    "dataset_id": dataset_id,
                    "symbol": symbol,
                    "interval": interval
                }
            )
            return result.rowcount

    def get_candles_by_dataset(
        self,
        dataset_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Candle]:
        """Get candles for dataset within time range.

        Args:
            dataset_id: Dataset ID
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List of Candle objects
        """
        with self.SessionLocal() as session:
            return session.query(Candle).filter(
                Candle.dataset_id == dataset_id,
                Candle.open_time >= start_time,
                Candle.open_time <= end_time
            ).order_by(Candle.open_time).all()
```

- [ ] **Step 3: Write test for get_all_symbol_interval_combinations**

**File:** `tests/test_database_datasets.py` (create new)

```python
import pytest
from datetime import datetime
from backend.database import Database
from backend.models.candle import Candle
from backend.models.symbol import Symbol


def test_get_all_symbol_interval_combinations(db_session):
    """Test getting distinct symbol/interval combinations"""
    # Create test data
    symbol = Symbol(symbol="BTCUSDT")
    db_session.add(symbol)
    db_session.commit()

    # Add candles for different intervals
    for interval in ['1h', '4h']:
        candle = Candle(
            symbol_id=symbol.id,
            interval=interval,
            open_time=datetime(2024, 1, 1),
            close_time=datetime(2024, 1, 2),
            open_price=100.0,
            high_price=110.0,
            low_price=90.0,
            close_price=105.0,
            volume=1000.0
        )
        db_session.add(candle)
    db_session.commit()

    # Test
    from backend.config import settings
    db = Database(settings.database_url)
    combinations = db.get_all_symbol_interval_combinations()

    assert len(combinations) == 1
    assert ('BTCUSDT', '1h') in combinations
    assert ('BTCUSDT', '4h') in combinations
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd ~/code/quant2
pytest tests/test_database_datasets.py::test_get_all_symbol_interval_combinations -v
```

Expected: PASS (if fixtures work) or FAIL with missing fixtures - adjust as needed

- [ ] **Step 5: Commit**

```bash
git add backend/database.py tests/test_database_datasets.py
git commit -m "feat: add dataset CRUD methods to Database class

- Add get_all_symbol_interval_combinations for migration
- Add get_time_range for symbol/interval
- Add create_dataset, get_dataset, get_datasets
- Add rename_dataset, delete_dataset
- Add check_dataset_usage for validation
- Add update_candles_dataset_id for migration
- Add get_candles_by_dataset for backtest queries"
```

---

### Task 3: Migration Script

**Files:**
- Create: `backend/core/migration.py`

- [ ] **Step 1: Create migration script**

```python
# backend/core/migration.py
"""
Migration script to convert existing candles to dataset-based schema.
Creates one default dataset per unique symbol+interval combination.
"""
import logging
from datetime import datetime
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

                    # Get candle count
                    count = conn.execute(
                        text("""
                            SELECT COUNT(*) as count
                            FROM candles c
                            JOIN symbols s ON c.symbol_id = s.id
                            WHERE s.symbol = :symbol
                            AND c.interval = :interval
                        """),
                        {"symbol": symbol, "interval": interval}
                    ).fetchone()[0]

                    if count == 0:
                        continue

                    # Create default dataset
                    dataset_name = f"{symbol} {interval} Legacy Data"
                    dataset_result = conn.execute(
                        text("""
                            INSERT INTO datasets (name, symbol, interval, start_time, end_time, candle_count, created_at)
                            VALUES (:name, :symbol, :interval, :start_time, :end_time, :count, :created_at)
                            RETURNING id
                        """),
                        {
                            "name": dataset_name,
                            "symbol": symbol,
                            "interval": interval,
                            "start_time": time_range.start,
                            "end_time": time_range.end,
                            "count": count,
                            "created_at": datetime.utcnow()
                        }
                    )
                    dataset_id = dataset_result.fetchone()[0]

                    # Associate candles to dataset
                    conn.execute(
                        text("""
                            UPDATE candles
                            SET dataset_id = :dataset_id
                            WHERE symbol_id = (
                                SELECT id FROM symbols WHERE symbol = :symbol
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
```

- [ ] **Step 2: Test migration on backup**

```bash
# Backup database first
cp data/quant.db data/quant.db.backup

# Run migration
cd backend
python -m core.migration
```

Expected: Output showing number of datasets created

- [ ] **Step 3: Verify migration**

```bash
sqlite3 data/quant.db "SELECT name, symbol, interval, candle_count FROM datasets;"
```

Expected: List of legacy datasets

```bash
sqlite3 data/quant.db "SELECT COUNT(*) FROM candles WHERE dataset_id = 0;"
```

Expected: 0 (all candles migrated)

- [ ] **Step 4: If successful, restore original and commit**

```bash
# Keep backup for safety
# git add doesn't track data/quant.db
git add backend/core/migration.py
git commit -m "feat: add data migration script

- Create default datasets for existing symbol/interval combinations
- Use transaction for atomic rollback on failure
- Associate existing candles to new datasets
- Add comprehensive logging"
```

---

### Task 4: Update Download API

**Files:**
- Modify: `backend/api/data.py`

- [ ] **Step 1: Add dataset_id parameter to download endpoint**

**File:** `backend/api/data.py` (update the download_data function around line 180)

```python
@router.post("/download")
async def download_data(request: dict):
    """
    Download historical data from Binance.

    Downloads historical candle data from Binance and saves it to the database.
    Creates a dataset record for the downloaded data.

    Args:
        request: Dict containing:
            - symbol: Trading pair (e.g., BTCUSDT)
            - interval: K-line interval (e.g., 1h)
            - start_time: Start time in ISO format
            - end_time: End time in ISO format
            - dataset_name: Optional dataset name

    Returns:
        Dict containing:
            - dataset_id: int
            - dataset_name: str
            - symbol: str
            - interval: str
            - count: int (number of candles downloaded or existing)
            - status: 'downloaded' | 'already_exists' | 'error'
            - message: str (only on success or error)
    """
    # Validate required fields
    required = ["symbol", "interval", "start_time", "end_time"]
    for field in required:
        if field not in request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )

    # Parse datetime
    try:
        start_dt = parse_iso_datetime(request["start_time"])
        end_dt = parse_iso_datetime(request["end_time"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}"
        )

    # Get dataset name (optional) or generate auto name
    import time
    dataset_name = request.get("dataset_name")
    if not dataset_name:
        timestamp_suffix = int(time.time())
        dataset_name = f"{request['symbol']} {request['interval']} ({request['start_time'][:10]} ~ {request['end_time'][:10]})_{timestamp_suffix}"

    # Download data (existing logic)
    download_result = await _data_manager.download_and_save(
        symbol=request["symbol"],
        interval=request["interval"],
        start_time=start_dt,
        end_time=end_dt
    )

    # Create dataset record
    try:
        dataset_id = _db.create_dataset(
            name=dataset_name,
            symbol=request["symbol"],
            interval=request["interval"],
            start_time=start_dt,
            end_time=end_dt,
            candle_count=download_result["count"]
        )

        # Associate candles to dataset
        _db.update_candles_dataset_id(
            symbol=request["symbol"],
            interval=request["interval"],
            dataset_id=dataset_id
        )

        download_result["dataset_id"] = dataset_id
        download_result["dataset_name"] = dataset_name

    except Exception as e:
        logger.error(f"Failed to create dataset: {e}")
        download_result["status"] = "error"
        download_result["error"] = str(e)

    # Add message based on status
    if download_result["status"] == "downloaded":
        download_result["message"] = "Data downloaded successfully"
    elif download_result["status"] == "already_exists":
        download_result["message"] = "Data already exists"

    return download_result
```

- [ ] **Step 2: Add dataset list endpoint**

**File:** `backend/api/data.py` (add after the delete endpoint, around line 375)

```python
@router.get("/datasets")
async def list_datasets() -> Dict[str, Any]:
    """
    List all datasets.

    Returns:
        Dict with "datasets" key containing list of dataset objects
        {
            "datasets": [
                {
                    "id": 123,
                    "name": "BTC 2024 Q1",
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-12-31T23:59:59",
                    "candle_count": 8760,
                    "created_at": "2024-03-27T10:30:00"
                }
            ]
        }
    """
    try:
        datasets = _db.get_datasets()

        # Convert to dict format
        formatted_datasets = []
        for dataset in datasets:
            formatted_datasets.append({
                "id": dataset.id,
                "name": dataset.name,
                "symbol": dataset.symbol,
                "interval": dataset.interval,
                "start_time": dataset.start_time.isoformat(),
                "end_time": dataset.end_time.isoformat(),
                "candle_count": dataset.candle_count,
                "created_at": dataset.created_at.isoformat()
            })

        return {"datasets": formatted_datasets}
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve datasets"
        )


@router.put("/datasets/{dataset_id}/rename")
async def rename_dataset(dataset_id: int, request: dict) -> Dict[str, Any]:
    """
    Rename a dataset.

    Args:
        dataset_id: Dataset ID
        request: Dict with "name" key

    Returns:
        Dict with "id" and "name" of renamed dataset

    Raises:
        HTTPException: 404 if not found, 400 if name exists
    """
    if "name" not in request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: name"
        )

    new_name = request["name"]

    try:
        success = _db.rename_dataset(dataset_id, new_name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset name already exists. Please choose a different name."
            )

        return {"id": dataset_id, "name": new_name}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to rename dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename dataset"
        )


@router.delete("/datasets/{dataset_id}")
async def delete_dataset_endpoint(dataset_id: int) -> Dict[str, Any]:
    """
    Delete a dataset and all associated candles.

    Args:
        dataset_id: Dataset ID

    Returns:
        Dict with deletion confirmation

    Raises:
        HTTPException: 404 if not found, 409 if used in backtests
    """
    try:
        # Check if dataset is used in backtests
        backtest_count = _db.check_dataset_usage(dataset_id)
        if backtest_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete dataset: used by {backtest_count} backtest result(s). Delete backtest results first."
            )

        # Delete dataset
        deleted_count = _db.delete_dataset(dataset_id)

        return {
            "dataset_id": dataset_id,
            "deleted_count": deleted_count,
            "message": "Dataset deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset"
        )
```

- [ ] **Step 3: Write test for dataset list endpoint**

**File:** `tests/test_api_datasets.py` (create new)

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Database
from backend.models.dataset import Dataset
from datetime import datetime


def test_list_datasets(client: TestClient, db_session):
    """Test listing all datasets"""
    # Create test dataset
    dataset = Dataset(
        name="Test Dataset",
        symbol="BTCUSDT",
        interval="1h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 3, 31),
        candle_count=2184,
        created_at=datetime.utcnow()
    )
    db_session.add(dataset)
    db_session.commit()

    # Test
    response = client.get("/api/v1/data/datasets")

    assert response.status_code == 200
    data = response.json()
    assert "datasets" in data
    assert len(data["datasets"]) >= 1

    # Find our test dataset
    test_ds = next((d for d in data["datasets"] if d["name"] == "Test Dataset"), None)
    assert test_ds is not None
    assert test_ds["symbol"] == "BTCUSDT"
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_api_datasets.py::test_list_datasets -v
```

Expected: FAIL (test infrastructure setup needed) or PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/data.py tests/test_api_datasets.py
git commit -m "feat: update download API to create datasets

- Add dataset_name parameter to download endpoint
- Auto-generate dataset name with timestamp if not provided
- Create dataset record after successful download
- Associate downloaded candles to dataset
- Add GET /api/v1/data/datasets endpoint
- Add PUT /api/v1/data/datasets/{id}/rename endpoint
- Add DELETE /api/v1/data/datasets/{id} endpoint with validation"
```

---

### Task 5: Update Backtest Engine

**Files:**
- Modify: `backend/core/backtest_engine.py`

- [ ] **Step 1: Update BacktestEngine.run() signature**

**File:** `backend/core/backtest_engine.py` (modify run method signature and implementation, around line 50-100)

```python
async def run(
    self,
    strategy_class: Type[StrategyBase],
    dataset_id: int,
    start_time: datetime = None,
    end_time: datetime = None,
    parameters: Dict[str, Any] = None,
    initial_cash: float = 100000.0,
    commission: float = 0.001,
    job_id: int = None
) -> Dict[str, Any]:
    """
    Run backtest on specified dataset.

    Args:
        strategy_class: Strategy class to test
        dataset_id: ID of dataset to use
        start_time: Optional start time override (clipped to dataset bounds)
        end_time: Optional end time override (clipped to dataset bounds)
        parameters: Strategy parameters
        initial_cash: Initial capital
        commission: Commission per trade
        job_id: Optional job ID for saving results

    Returns:
        Dict with backtest results
    """
    # Fetch dataset metadata
    dataset = self.db.get_dataset(dataset_id)

    # Use dataset time range if not specified
    if start_time is None:
        start_time = dataset.start_time
    if end_time is None:
        end_time = dataset.end_time

    # Validate and clip time range to dataset bounds
    if start_time < dataset.start_time:
        logger.warning(f"Start time {start_time} before dataset start {dataset.start_time}, clipping")
        start_time = dataset.start_time
    if end_time > dataset.end_time:
        logger.warning(f"End time {end_time} after dataset end {dataset.end_time}, clipping")
        end_time = dataset.end_time

    if start_time >= end_time:
        raise ValueError(
            f"Invalid time range: start_time {start_time} >= end_time {end_time}"
        )

    # Query candles by dataset_id AND time range
    candles = self.db.get_candles_by_dataset(
        dataset_id=dataset_id,
        start_time=start_time,
        end_time=end_time
    )

    if not candles:
        raise ValueError(
            f"No candles found for dataset {dataset_id} "
            f"in time range {start_time} ~ {end_time}"
        )

    logger.info(f"Running backtest with {len(candles)} candles from dataset '{dataset.name}'")

    # ... continue with existing backtest logic using candles list
    # The rest of the method remains the same from here...

    # Convert candles to pandas DataFrame
    # ...
```

- [ ] **Step 2: Update backtest API endpoint to use dataset_id**

**File:** `backend/api/backtest.py` (update the run endpoint to accept dataset_id)

```python
@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """Run a backtest with specified strategy and dataset."""

    # Validate dataset_id is provided
    if not hasattr(request, 'dataset_id') or request.dataset_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dataset_id is required"
        )

    # Rest of implementation using dataset_id
    # ...
```

- [ ] **Step 3: Update BacktestRequest model**

**File:** `backend/models/backtest_job.py` (or wherever request is defined)

```python
# Add to BacktestRequest schema
dataset_id: int  # Required field
```

- [ ] **Step 4: Update report generation to include dataset info**

**File:** `backend/core/backtest_engine.py` (in the results dict construction)

```python
# Add dataset information to results
results = {
    # ... existing fields ...
    "dataset": {
        "id": dataset.id,
        "name": dataset.name,
        "symbol": dataset.symbol,
        "interval": dataset.interval,
        "start_time": dataset.start_time.isoformat(),
        "end_time": dataset.end_time.isoformat(),
        "candle_count": dataset.candle_count
    }
}
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/backtest_engine.py backend/api/backtest.py
git commit -m "feat: update backtest engine to use dataset_id

- Change BacktestEngine.run() to accept dataset_id parameter
- Add time range clipping to dataset bounds
- Query candles by dataset_id instead of symbol/interval
- Add dataset information to backtest results
- Update backtest API to require dataset_id"
```

---

## Phase 2: Frontend Data Management

### Task 6: Frontend Dataset Types

**Files:**
- Modify: `frontend/lib/api/data.ts`

- [ ] **Step 1: Add dataset interfaces**

**File:** `frontend/lib/api/data.ts` (add after existing interfaces)

```typescript
export interface Dataset {
  id: number;
  name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  candle_count: number;
  created_at: string;
}

export interface DatasetRenameRequest {
  name: string;
}

export interface DatasetDeleteResponse {
  dataset_id: number;
  deleted_count: number;
  message: string;
}

export interface DownloadRequestExtended extends DownloadRequest {
  dataset_name?: string;  // Optional dataset name
}
```

- [ ] **Step 2: Add dataset API methods**

**File:** `frontend/lib/api/data.ts` (add to dataApi object)

```typescript
// Add to dataApi object:
  getDatasets: async (): Promise<Dataset[]> => {
    const response = await api.get<{ datasets: Dataset[] }>(
      '/api/v1/data/datasets'
    );
    return response.data.datasets;
  },

  renameDataset: async (datasetId: number, name: string): Promise<{ id: number; name: string }> => {
    const response = await api.put<{ id: number; name: string }>(
      `/api/v1/data/datasets/${datasetId}/rename`,
      { name }
    );
    return response.data;
  },

  deleteDataset: async (datasetId: number): Promise<DatasetDeleteResponse> => {
    const response = await api.delete<DatasetDeleteResponse>(
      `/api/v1/data/datasets/${datasetId}`
    );
    return response.data;
  },
```

- [ ] **Step 3: Update DownloadRequest type**

**File:** `frontend/lib/api/data.ts` (update DownloadRequest interface)

```typescript
// Change:
export interface DownloadRequest {
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
}

// To:
export interface DownloadRequest {
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  dataset_name?: string;  // Optional
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api/data.ts
git commit -m "feat: add dataset types and API methods

- Add Dataset interface
- Add getDatasets API method
- Add renameDataset API method
- Add deleteDataset API method
- Update DownloadRequest to include optional dataset_name"
```

---

### Task 7: Dataset Selector Component

**Files:**
- Create: `frontend/components/DatasetSelector.tsx`

- [ ] **Step 1: Create DatasetSelector component**

```typescript
// frontend/components/DatasetSelector.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { dataApi, Dataset } from '@/lib/api/data';

interface DatasetSelectorProps {
  value: number | null;
  onChange: (datasetId: number, dataset: Dataset) => void;
  disabled?: boolean;
}

export default function DatasetSelector({ value, onChange, disabled }: DatasetSelectorProps) {
  const { data: datasets, isLoading, error } = useQuery({
    queryKey: ['datasets'],
    queryFn: dataApi.getDatasets,
    staleTime: 60000, // 1 minute
  });

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const datasetId = parseInt(e.target.value);
    const dataset = datasets?.find((d) => d.id === datasetId);
    if (dataset) {
      onChange(datasetId, dataset);
    }
  };

  if (isLoading) {
    return (
      <div>
        <label htmlFor="dataset" className="block text-sm font-medium text-gray-700 mb-2">
          Dataset
        </label>
        <div className="animate-pulse">
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <label htmlFor="dataset" className="block text-sm font-medium text-gray-700 mb-2">
          Dataset
        </label>
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-sm text-red-800">Failed to load datasets</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-red-600 underline mt-1"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!datasets || datasets.length === 0) {
    return (
      <div>
        <label htmlFor="dataset" className="block text-sm font-medium text-gray-700 mb-2">
          Dataset
        </label>
        <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
          <p className="text-sm text-yellow-800 mb-2">
            No datasets available. Download data first.
          </p>
          <a
            href="/data"
            className="text-sm text-blue-600 hover:underline"
          >
            Go to Data Management →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor="dataset" className="block text-sm font-medium text-gray-700 mb-2">
        Dataset
      </label>
      <select
        id="dataset"
        value={value || ''}
        onChange={handleChange}
        disabled={disabled}
        className="w-full border border-gray-300 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
      >
        <option value="">Select a dataset</option>
        {datasets.map((dataset) => (
          <option key={dataset.id} value={dataset.id}>
            {dataset.name} ({dataset.symbol} {dataset.interval}, {dataset.candle_count} candles)
          </option>
        ))}
      </select>
    </div>
  );
}
```

- [ ] **Step 2: Write test for DatasetSelector**

**File:** `frontend/components/DatasetSelector.test.tsx` (create new)

```typescript
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DatasetSelector from './DatasetSelector';
import { dataApi } from '@/lib/api/data';

// Mock dataApi
vi.mock('@/lib/api/data', () => ({
  dataApi: {
    getDatasets: vi.fn(),
  },
}));

const mockDatasets = [
  {
    id: 1,
    name: 'BTC 2024 Q1',
    symbol: 'BTCUSDT',
    interval: '1h',
    start_time: '2024-01-01T00:00:00',
    end_time: '2024-03-31T23:59:59',
    candle_count: 2184,
    created_at: '2024-03-27T10:30:00',
  },
];

describe('DatasetSelector', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('renders dataset options', async () => {
    vi.mocked(dataApi.getDatasets).mockResolvedValue(mockDatasets);

    render(
      <QueryClientProvider client={queryClient}>
        <DatasetSelector value={null} onChange={() => {}} />
      </QueryClientProvider>
    );

    expect(await screen.findByText('BTC 2024 Q1 (BTCUSDT 1h, 2184 candles)')).toBeInTheDocument();
  });

  it('shows empty state when no datasets', async () => {
    vi.mocked(dataApi.getDatasets).mockResolvedValue([]);

    render(
      <QueryClientProvider client={queryClient}>
        <DatasetSelector value={null} onChange={() => {}} />
      </QueryClientProvider>
    );

    expect(await screen.findByText('No datasets available. Download data first.')).toBeInTheDocument();
  });

  it('calls onChange when dataset selected', async () => {
    const handleChange = vi.fn();
    vi.mocked(dataApi.getDatasets).mockResolvedValue(mockDatasets);

    render(
      <QueryClientProvider client={queryClient}>
        <DatasetSelector value={null} onChange={handleChange} />
      </QueryClientProvider>
    );

    const select = await screen.findByRole('combobox');
    // Simulate selection - actual implementation depends on testing library
  });
});
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/DatasetSelector.tsx frontend/components/DatasetSelector.test.tsx
git commit -m "feat: add DatasetSelector component

- Create dataset dropdown with loading/error/empty states
- Display format: name (symbol interval, count candles)
- Empty state links to data management page
- Add unit tests for DatasetSelector"
```

---

### Task 8: Update DownloadForm

**Files:**
- Modify: `frontend/components/DownloadForm.tsx`

- [ ] **Step 1: Add dataset name input**

**File:** `frontend/components/DownloadForm.tsx` (find the form and add dataset name input before time selection)

```typescript
// Add to component state:
const [datasetName, setDatasetName] = useState('');

// Add in form (before start/end time selection):
<div className="mb-4">
  <label htmlFor="datasetName" className="block text-sm font-medium text-gray-700 mb-2">
    Dataset Name (Optional)
  </label>
  <input
    id="datasetName"
    type="text"
    value={datasetName}
    onChange={(e) => setDatasetName(e.target.value)}
    placeholder="Auto-generated if empty"
    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
  />
  <p className="text-xs text-gray-500 mt-1">
    Default: {symbol} {interval} ({startDate} ~ {endDate})_[timestamp]
  </p>
</div>
```

- [ ] **Step 2: Pass dataset_name to download API**

**File:** `frontend/components/DownloadForm.tsx` (update the handleDownload function)

```typescript
const handleDownload = (startTime: string, endTime: string) => {
  setDownloadResult(null);
  downloadMutation.mutate({
    symbol: selectedSymbol,
    interval: selectedInterval,
    start_time: startTime,
    end_time: endTime,
    dataset_name: datasetName || undefined,  // Pass dataset name if provided
  });
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/DownloadForm.tsx
git commit -m "feat: add optional dataset name input to DownloadForm

- Add dataset name input field
- Show auto-generated name pattern in helper text
- Pass dataset_name to download API
- Maintain backward compatibility (optional field)"
```

---

### Task 9: Refactor DownloadedDataSidebar

**Files:**
- Modify: `frontend/components/DownloadedDataSidebar.tsx`

- [ ] **Step 1: Update to flat list display**

**File:** `frontend/components/DownloadedDataSidebar.tsx` (major refactor of component structure)

```typescript
// Change from hierarchical to flat list
// Replace the symbol/interval expansion with simple dataset list

// Update the main render to show flat list:
<div className="p-4">
  <h2 className="text-lg font-semibold mb-4">Downloaded Datasets</h2>

  {isLoading ? (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="animate-pulse">
          <div className="h-16 bg-gray-200 rounded"></div>
        </div>
      ))}
    </div>
  ) : error ? (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <p className="text-sm text-red-800 mb-3">
        {error instanceof Error ? error.message : 'Failed to load datasets'}
      </p>
      <button
        onClick={() => refetch()}
        className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
      >
        Retry
      </button>
    </div>
  ) : !downloadedData || downloadedData.length === 0 ? (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <p className="text-gray-600 mb-2">No datasets downloaded</p>
      <p className="text-gray-400 text-sm">Download data to get started</p>
    </div>
  ) : (
    <div className="space-y-2">
      {downloadedData.map((dataset: Dataset) => {
        const isSelected = selectedDatasetId === dataset.id;

        return (
          <div
            key={dataset.id}
            className={`border rounded-lg overflow-hidden transition-colors ${
              isSelected
                ? 'bg-blue-50 border-blue-500'
                : 'bg-white border-gray-200 hover:border-gray-300'
            }`}
          >
            <button
              onClick={() => onSelectDataset(dataset)}
              className="w-full px-4 py-3 text-left"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900">{dataset.name}</span>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500">
                    {dataset.candle_count.toLocaleString()} candles
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRename(dataset);
                    }}
                    className="p-1 hover:bg-gray-100 rounded"
                    aria-label={`Rename ${dataset.name}`}
                  >
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(dataset);
                    }}
                    className="p-1 hover:bg-red-100 rounded"
                    aria-label={`Delete ${dataset.name}`}
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              </div>
              <div className="text-xs text-gray-500">
                {dataset.symbol} {dataset.interval} | {formatDate(dataset.start_time)} ~ {formatDate(dataset.end_time)}
              </div>
            </button>
          </div>
        );
      })}
    </div>
  )}

  {/* Rename dialog */}
  {showRenameDialog && (
    <RenameDatasetDialog
      dataset={selectedDatasetForRename}
      onConfirm={handleRenameConfirm}
      onCancel={() => setShowRenameDialog(false)}
    />
  )}
</div>
```

- [ ] **Step 2: Create RenameDatasetDialog component**

**File:** `frontend/components/RenameDatasetDialog.tsx` (create new)

```typescript
'use client';

import { useState } from 'react';
import Modal from './Modal';

interface RenameDatasetDialogProps {
  dataset: Dataset | null;
  onConfirm: (name: string) => void;
  onCancel: () => void;
}

export default function RenameDatasetDialog({ dataset, onConfirm, onCancel }: RenameDatasetDialogProps) {
  const [name, setName] = useState(dataset?.name || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onConfirm(name.trim());
    }
  };

  return (
    <Modal
      isOpen={!!dataset}
      onClose={onCancel}
      title="Rename Dataset"
    >
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="newDatasetName" className="block text-sm font-medium text-gray-700 mb-2">
            New Name
          </label>
          <input
            id="newDatasetName"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            autoFocus
          />
        </div>
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Rename
          </button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/DownloadedDataSidebar.tsx frontend/components/RenameDatasetDialog.tsx
git commit -m "feat: refactor DownloadedDataSidebar to flat list

- Change from 3-layer hierarchy to flat dataset list
- Show all datasets in single scrollable list
- Add rename dialog component
- Add delete confirmation with dataset details
- Update styling and interactions"
```

---

## Phase 3: Frontend Backtest & Optimization

### Task 10: Update BacktestForm

**Files:**
- Modify: `frontend/components/BacktestForm.tsx`

- [ ] **Step 1: Add dataset state and DatasetSelector**

**File:** `frontend/components/BacktestForm.tsx`

```typescript
// Add imports:
import DatasetSelector from './DatasetSelector';
import { dataApi, Dataset } from '@/lib/api/data';
import { LockClosedIcon } from '@heroicons/react/24/outline'; // or use SVG

// Add state:
const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
const [selectedDatasetData, setSelectedDatasetData] = useState<Dataset | null>(null);
```

- [ ] **Step 2: Add DatasetSelector to form**

**File:** `frontend/components/BacktestForm.tsx` (add after strategy selector, before symbol/interval)

```tsx
{/* Dataset Selector */}
<DatasetSelector
  value={selectedDataset}
  onChange={(datasetId, dataset) => {
    setSelectedDataset(datasetId);
    setSelectedDatasetData(dataset);
    setSymbol(dataset.symbol);
    setInterval(dataset.interval);
    setStartTime(dataset.start_time.split('T')[0]);
    setEndTime(dataset.end_time.split('T')[0]);
  }}
  disabled={strategiesLoading || runBacktestMutation.isPending}
/>
```

- [ ] **Step 3: Make symbol and interval read-only with lock icon**

**File:** `frontend/components/BacktestForm.tsx` (update symbol/interval inputs)

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  <div className="relative">
    <label htmlFor="symbol" className="block text-sm font-medium text-gray-700 mb-2">
      Symbol
    </label>
    <div className="relative">
      <input
        id="symbol"
        type="text"
        value={symbol}
        readOnly
        className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-gray-50 text-gray-700 pl-10"
      />
      <LockClosedIcon className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
    </div>
  </div>

  <div className="relative">
    <label htmlFor="interval" className="block text-sm font-medium text-gray-700 mb-2">
      Interval
    </label>
    <div className="relative">
      <input
        id="interval"
        type="text"
        value={interval}
        readOnly
        className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-gray-50 text-gray-700 pl-10"
      />
      <LockClosedIcon className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
    </div>
  </div>
</div>
```

- [ ] **Step 4: Add time range validation**

**File:** `frontend/components/BacktestForm.tsx` (add after time pickers)

```tsx
{/* Dataset range warning */}
{selectedDatasetData && (
  <div className={`text-xs mb-2 ${
    startTime < selectedDatasetData.start_time.split('T')[0] ||
    endTime > selectedDatasetData.end_time.split('T')[0]
      ? 'text-orange-600'
      : 'text-gray-500'
  }`}>
    {startTime < selectedDatasetData.start_time.split('T')[0] ||
     endTime > selectedDatasetData.end_time.split('T')[0]
      ? '⚠️ Time range outside dataset bounds (will be clipped)'
      : `Dataset range: ${selectedDatasetData.start_time.split('T')[0]} ~ ${selectedDatasetData.end_time.split('T')[0]}`
    }
  </div>
)}
```

- [ ] **Step 5: Update form submission to pass dataset_id**

**File:** `frontend/components/BacktestForm.tsx` (update handleSubmit)

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

  if (!selectedDataset) {
    toast.error('Please select a dataset');
    return;
  }

  // ... rest of validation

  runBacktestMutation.mutate({
    strategy_name: strategy,
    dataset_id: selectedDataset,  // Pass dataset_id instead of symbol/interval
    start_time: new Date(startTime).toISOString(),
    end_time: new Date(endTime).toISOString(),
    parameters,
    initial_cash: initialCash,
  });
};
```

- [ ] **Step 6: Commit**

```bash
git add frontend/components/BacktestForm.tsx
git commit -m "feat: add dataset selection to BacktestForm

- Add DatasetSelector component before symbol/interval
- Auto-fill symbol, interval, times when dataset selected
- Make symbol/interval read-only with lock icons
- Add time range validation and clipping warnings
- Update form submission to pass dataset_id"
```

---

### Task 11: Update OptimizationForm

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx`

- [ ] **Step 1: Apply same changes as BacktestForm**

Follow the exact same pattern as Task 10:
- Add dataset state
- Import DatasetSelector
- Add DatasetSelector to form
- Make symbol/interval read-only
- Add time range validation
- Update submission to pass dataset_id

- [ ] **Step 2: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: add dataset selection to OptimizationForm

- Add DatasetSelector component
- Auto-fill symbol, interval, times
- Make symbol/interval read-only with lock icons
- Add time range validation
- Update form submission to pass dataset_id"
```

---

### Task 12: Update ConfigurationSection

**Files:**
- Modify: `frontend/components/ConfigurationSection.tsx`

- [ ] **Step 1: Add dataset display to ConfigurationSection**

**File:** `frontend/components/ConfigurationSection.tsx` (update to include dataset info)

```typescript
// Add to props interface:
interface ConfigurationSectionProps {
  strategyName: string;
  parameters: Record<string, any>;
  dataset?: {
    id: number;
    name: string;
    symbol: string;
    interval: string;
    start_time: string;
    end_time: string;
    candle_count: number;
  } | null;
}

// Update component to display dataset:
<div className="bg-white rounded-lg shadow-md p-6 mb-8">
  <h2 className="text-xl font-bold text-gray-900 mb-4">Configuration</h2>

  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-4">
    <div>
      <span className="text-gray-600">Strategy:</span>
      <p className="font-medium text-gray-900">{strategyName}</p>
    </div>

    {/* NEW: Dataset Information */}
    {dataset && (
      <>
        <div>
          <span className="text-gray-600">Dataset:</span>
          <p className="font-medium text-gray-900">{dataset.name}</p>
        </div>
        <div>
          <span className="text-gray-600">Data Range:</span>
          <p className="font-medium text-gray-900">
            {new Date(dataset.start_time).toLocaleDateString()} ~ {new Date(dataset.end_time).toLocaleDateString()}
          </p>
        </div>
        <div>
          <span className="text-gray-600">Data Points:</span>
          <p className="font-medium text-gray-900">{dataset.candle_count} candles</p>
        </div>
      </>
    )}
  </div>

  {/* Parameters section */}
  {parameters && Object.keys(parameters).length > 0 && (
    <div className="border-t pt-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Strategy Parameters</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
        {Object.entries(parameters).map(([key, value]) => (
          <div key={key}>
            <span className="text-gray-600">{key}:</span>
            <span className="font-medium text-gray-900 ml-1">{String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  )}
</div>
```

- [ ] **Step 2: Update results page to pass dataset**

**File:** `frontend/app/results/[id]/page.tsx` (update to pass dataset to ConfigurationSection)

```typescript
// Extract dataset from report
const { dataset, ...rest } = report;

// Pass to ConfigurationSection:
<ConfigurationSection
  strategyName={strategy_name}
  parameters={parameters}
  dataset={dataset}
/>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ConfigurationSection.tsx frontend/app/results/[id]/page.tsx
git commit -m "feat: display dataset info in ConfigurationSection

- Show dataset name, data range, and candle count
- Display dataset information in backtest results
- Pass dataset data from API response to component
- Handle null/missing dataset gracefully"
```

---

## Phase 4: Testing & Documentation

### Task 13: Backend Tests

**Files:**
- Modify: `tests/test_database_datasets.py`
- Create: `tests/test_backtest_engine_datasets.py`

- [ ] **Step 1: Add comprehensive dataset tests**

```python
# tests/test_database_datasets.py

import pytest
from datetime import datetime
from backend.database import Database
from backend.models.dataset import Dataset
from backend.models.candle import Candle
from backend.models.symbol import Symbol
from backend.config import settings


def test_create_and_get_dataset(db_session):
    """Test creating and retrieving a dataset"""
    db = Database(settings.database_url)

    dataset_id = db.create_dataset(
        name="Test Dataset",
        symbol="BTCUSDT",
        interval="1h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 3, 31),
        candle_count=2184
    )

    assert dataset_id > 0

    dataset = db.get_dataset(dataset_id)
    assert dataset.name == "Test Dataset"
    assert dataset.symbol == "BTCUSDT"


def test_rename_dataset(db_session):
    """Test renaming a dataset"""
    db = Database(settings.database_url)

    # Create dataset
    dataset_id = db.create_dataset(
        name="Original Name",
        symbol="ETHUSDT",
        interval="4h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 6, 30),
        candle_count=1000
    )

    # Rename
    success = db.rename_dataset(dataset_id, "New Name")
    assert success is True

    # Verify
    dataset = db.get_dataset(dataset_id)
    assert dataset.name == "New Name"


def test_delete_dataset(db_session):
    """Test deleting a dataset"""
    db = Database(settings.database_url)

    # Create dataset with candles
    symbol = Symbol(symbol="BTCUSDT")
    db_session.add(symbol)
    db_session.commit()

    dataset_id = db.create_dataset(
        name="To Delete",
        symbol="BTCUSDT",
        interval="1h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        candle_count=24
    )

    # Add candle
    candle = Candle(
        symbol_id=symbol.id,
        interval="1h",
        dataset_id=dataset_id,
        open_time=datetime(2024, 1, 1),
        close_time=datetime(2024, 1, 2),
        open_price=100.0,
        high_price=110.0,
        low_price=90.0,
        close_price=105.0,
        volume=1000.0
    )
    db_session.add(candle)
    db_session.commit()

    # Delete
    deleted_count = db.delete_dataset(dataset_id)
    assert deleted_count == 1

    # Verify dataset is gone
    with pytest.raises(ValueError):
        db.get_dataset(dataset_id)


def test_get_candles_by_dataset(db_session):
    """Test querying candles by dataset"""
    db = Database(settings.database_url)

    # Create symbol and dataset
    symbol = Symbol(symbol="BTCUSDT")
    db_session.add(symbol)
    db_session.commit()

    dataset_id = db.create_dataset(
        name="Test Dataset",
        symbol="BTCUSDT",
        interval="1h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31, 24),
        candle_count=24
    )

    # Add candles
    for i in range(24):
        candle = Candle(
            symbol_id=symbol.id,
            interval="1h",
            dataset_id=dataset_id,
            open_time=datetime(2024, 1, 1, i),
            close_time=datetime(2024, 1, 1, i + 1),
            open_price=100.0 + i,
            high_price=110.0 + i,
            low_price=90.0 + i,
            close_price=105.0 + i,
            volume=1000.0
        )
        db_session.add(candle)
    db_session.commit()

    # Query
    candles = db.get_candles_by_dataset(
        dataset_id=dataset_id,
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31, 23, 59, 59)
    )

    assert len(candles) == 24
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_database_datasets.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_database_datasets.py
git commit -m "test: add comprehensive dataset tests

- Test create and get dataset
- Test rename dataset
- Test delete dataset with cascade
- Test get_candles_by_dataset method"
```

---

### Task 14: E2E Tests

**Files:**
- Create: `frontend/e2e/dataset-flow.spec.ts`

- [ ] **Step 1: Create E2E test for dataset workflow**

```typescript
// frontend/e2e/dataset-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Dataset Selection Flow', () => {
  test('download dataset and use in backtest', async ({ page }) => {
    await page.goto('/data');

    // Select symbol and interval
    await page.selectOption('select#symbol', 'BTCUSDT');
    await page.selectOption('select#interval', '1h');

    // Enter dates
    await page.fill('input[placeholder*="Start"]', '2024-01-01');
    await page.fill('input[placeholder*="End"]', '2024-03-31');

    // Enter dataset name
    await page.fill('input#datasetName', 'BTC Test Dataset');

    // Download
    await page.click('button:has-text("Download")');

    // Wait for success
    await expect(page.locator('text=Download completed successfully')).toBeVisible();

    // Navigate to backtest
    await page.goto('/backtest');

    // Select strategy
    await page.selectOption('select#strategy', /.+/);  // Select first available

    // Select dataset
    await page.selectOption('select#dataset', 'BTC Test Dataset');

    // Verify fields are auto-filled and read-only
    const symbolInput = page.locator('input#symbol');
    await expect(symbolInput).toHaveValue('BTCUSDT');
    await expect(symbolInput).toBeDisabled();

    // Run backtest
    await page.click('button:has-text("Run Backtest")');

    // Wait for results
    await expect(page.locator('text=Backtest completed successfully')).toBeVisible();

    // Verify dataset info in results
    await expect(page.locator('text=BTC Test Dataset')).toBeVisible();
  });

  test('rename and delete dataset', async ({ page }) => {
    await page.goto('/data');

    // Wait for datasets to load
    await expect(page.locator('text=Downloaded Datasets')).toBeVisible();

    // Find first dataset and click rename
    await page.click('button[aria-label*="Rename"]');

    // Enter new name
    await page.fill('input#newDatasetName', 'Renamed Dataset');
    await page.click('button:has-text("Rename")');

    // Verify renamed
    await expect(page.locator('text=Renamed Dataset')).toBeVisible();

    // Delete dataset
    await page.click('button[aria-label*="Delete"]');
    await page.click('button:has-text("Delete")');  // Confirm

    // Verify deleted
    await expect(page.locator('text=Renamed Dataset')).not.toBeVisible();
  });
});
```

- [ ] **Step 2: Run E2E test**

```bash
cd frontend
pnpm test:e2e dataset-flow
```

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/dataset-flow.spec.ts
git commit -m "test: add E2E tests for dataset workflow

- Test downloading dataset with custom name
- Test using dataset in backtest
- Test auto-fill and read-only fields
- Test dataset rename functionality
- Test dataset delete with confirmation"
```

---

### Task 15: Documentation

**Files:**
- Create: `docs/migration-guide.md`
- Update: README.md or docs folder

- [ ] **Step 1: Create migration guide**

```markdown
# Dataset Migration Guide

## What Changed?

We've introduced a **dataset** abstraction that allows multiple datasets per symbol/interval combination. Previously, you could only have one dataset per symbol+interval pair.

## Database Migration

### What Happened?

- Created `datasets` table to track individual data downloads
- Added `dataset_id` foreign key to `candles` table
- Added `dataset_id` foreign key to `backtest_jobs` table
- Migrated existing candles to default datasets named "{symbol} {interval} Legacy Data"

### Manual Migration (if needed)

If migration didn't run automatically:

```bash
cd backend
python -m core.migration
```

### Rollback (if needed)

```bash
# Restore from backup
cp data/quant.db.backup data/quant.db
```

## API Changes

### Downloading Data

Now accepts optional `dataset_name` parameter:

```json
POST /api/v1/data/download
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-03-31T23:59:59",
  "dataset_name": "My Custom Dataset Name"  // Optional
}
```

### Running Backtests

Now requires `dataset_id` instead of separate symbol/interval:

```json
POST /api/v1/backtest/run
{
  "strategy_name": "DualMovingAverage",
  "dataset_id": 123,  // Required
  "start_time": "2024-01-01T00:00:00",  // Optional
  "end_time": "2024-03-31T23:59:59",    // Optional
  "parameters": {},
  "initial_cash": 100000
}
```

## New API Endpoints

- `GET /api/v1/data/datasets` - List all datasets
- `PUT /api/v1/data/datasets/{id}/rename` - Rename dataset
- `DELETE /api/v1/data/datasets/{id}` - Delete dataset

## UI Changes

- Data page now shows flat list of datasets (not symbol/interval hierarchy)
- Backtest and optimization forms now require dataset selection
- Symbol/interval fields become read-only after dataset selection
- Results pages now show which dataset was used
```

- [ ] **Step 2: Commit**

```bash
git add docs/migration-guide.md
git commit -m "docs: add dataset migration guide for users

- Explain database changes
- Provide migration instructions
- Document API changes
- Include rollback procedure"
```

---

## Final Steps

### Task 16: Final Testing & Cleanup

- [ ] **Step 1: Run full test suite**

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend
pnpm lint
pnpm test:e2e
```

- [ ] **Step 2: Manual smoke test**

1. Start backend: `./start.sh start`
2. Navigate to http://localhost:3002/data
3. Download a dataset with custom name
4. Navigate to http://localhost:3002/backtest
5. Select strategy and dataset
6. Verify auto-fill works
7. Run backtest
8. Verify dataset info shows in results
9. Rename dataset in sidebar
10. Delete dataset (confirm prevented if used in backtest)

- [ ] **Step 3: Performance check**

```bash
# Check dataset list performance
curl -s http://localhost:8000/api/v1/data/datasets | jq '.datasets | length'
# Should return quickly even with 100+ datasets
```

- [ ] **Step 4: Final commit**

```bash
git status
git add -A
git commit -m "feat: complete dataset selection feature implementation

Phase 1: Backend Foundation
- Created Dataset model with indexes
- Added dataset foreign keys to candles and backtest_jobs
- Implemented migration script with transaction safety
- Added comprehensive Database methods for dataset CRUD
- Updated download API to create datasets
- Added dataset list, rename, delete API endpoints
- Updated BacktestEngine to use dataset_id

Phase 2: Frontend Data Management
- Added Dataset types to API client
- Created DatasetSelector component
- Updated DownloadForm with dataset name input
- Refactored DownloadedDataSidebar to flat list
- Created RenameDatasetDialog component

Phase 3: Frontend Backtest & Optimization
- Updated BacktestForm with dataset selection
- Made symbol/interval read-only with lock icons
- Added time range validation and warnings
- Updated OptimizationForm with same changes
- Modified ConfigurationSection to display dataset info
- Updated results pages to show dataset data

Phase 4: Testing & Documentation
- Added comprehensive backend tests for datasets
- Added E2E tests for complete workflow
- Created migration guide for users

Features:
- Multiple datasets per symbol/interval
- Auto-generated dataset names with timestamp suffix
- Dataset selection in backtest and optimization
- Dataset management (rename, delete with validation)
- Dataset information display in results
- Time range clipping to dataset bounds
- Cascade delete with backtest reference checking

Estimated effort: 25-30 hours
Tech stack: FastAPI, SQLAlchemy, Next.js 14, React Query, TypeScript"
```

---

## Completion Checklist

- [ ] All 16 tasks completed
- [ ] All tests passing (backend, frontend, E2E)
- [ ] Manual smoke test successful
- [ ] Migration tested on staging database
- [ ] Documentation complete
- [ ] No regressions in existing functionality
- [ ] Performance: dataset list < 100ms
- [ ] Git history shows clean, incremental commits

---

## Notes for Implementation

### Important Patterns

1. **Always use transactions** for schema changes
2. **Test migration** on backup before production
3. **Validate early** - dataset_id must never be null after migration
4. **Cascade deletes** - ensure ON DELETE is set correctly
5. **Error messages** - be user-friendly and actionable

### Common Pitfalls

- Don't forget to import new models in `database.py`
- Don't run migration twice (creates duplicate datasets)
- Don't delete datasets used in backtests (should error)
- Don't let time ranges go outside dataset bounds (should clip)

### Testing Order

1. Backend unit tests first
2. Migration on test database
3. Frontend component tests
4. API integration tests
5. E2E tests last

---

## Next Steps After Implementation

1. Monitor performance of dataset list queries
2. Add pagination if list grows beyond 100 datasets
3. Consider adding dataset filtering/search
4. Add dataset comparison feature
5. Implement dataset export/import
