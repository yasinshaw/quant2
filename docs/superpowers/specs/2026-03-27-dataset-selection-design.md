# Dataset Selection Feature Design

**Date:** 2026-03-27
**Status:** Revised (v1.2) - Added results page dataset display
**Author:** Claude Code
**Revision Log:**
- v1.2 (2026-03-27): Added dataset information display in backtest and optimization results pages
- v1.1 (2026-03-27): Fixed schema issues, added backtest engine updates, clarified constraints
- v1.0 (2026-03-27): Initial design

## Overview

Enable users to download multiple datasets for the same symbol and interval (different time periods), and select datasets when running backtests and parameter optimization. This allows comparing strategy performance across different time periods and managing data more flexibly.

## Requirements

### Functional Requirements

1. **Multiple Datasets Support**
   - Users can download multiple datasets for the same symbol + interval combination
   - Each dataset has a unique ID and user-facing name (auto-generated or user-defined)
   - Overlapping time periods are allowed
   - Datasets are stored independently with unique IDs
   - Dataset names can be duplicate (uniqueness enforced by ID only)

2. **Dataset Selection in Backtesting**
   - Dataset selector placed before symbol/interval selectors
   - Auto-fills symbol, interval, start time, end time upon selection
   - Symbol and interval become read-only (locked) after dataset selection
   - Time range remains adjustable within dataset boundaries
   - Visual warnings when time exceeds dataset range
   - Backtest engine queries by dataset_id instead of symbol/interval

3. **Dataset Selection in Parameter Optimization**
   - Same UX as backtesting
   - Integrated with existing optimization form

4. **Dataset Management**
   - Rename datasets (auto-generated names can be customized)
   - Delete datasets with confirmation
   - Pre-deletion check for dependent backtest results
   - Flat list display in data management sidebar
   - Show dataset name, symbol, interval, time range, and candle count

5. **Dataset Information in Results**
   - Backtest results page displays which dataset was used
   - Parameter optimization results page displays dataset information
   - Show dataset name, symbol, interval, and time range
   - Link to dataset details (future: dataset management page)

### Non-Functional Requirements

- Data migration for existing candles with transaction safety
- Backward compatibility with current database
- Performance: dataset list query should be < 100ms
- UI: clear visual feedback for locked/unlocked states
- Data integrity: no orphaned candles after migration

## Architecture

### Database Schema

#### New Table: `datasets`

```sql
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    candle_count INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    -- Note: No UNIQUE constraint on name - allows duplicate names for overlapping datasets
);

-- Indexes for performance
CREATE INDEX idx_datasets_symbol_interval ON datasets(symbol, interval);
CREATE INDEX idx_datasets_created_at ON datasets(created_at);
CREATE INDEX idx_datasets_name ON datasets(name);
```

#### Modify Table: `candles`

Add foreign key to datasets with cascade delete:

```sql
-- Add dataset_id column with NOT NULL constraint and default value
-- Default value ensures existing data can be migrated, then removed
ALTER TABLE candles ADD COLUMN dataset_id INTEGER NOT NULL DEFAULT 0 REFERENCES datasets(id) ON DELETE CASCADE;

-- After migration completes, remove the default value:
-- ALTER TABLE candles ALTER COLUMN dataset_id DROP DEFAULT;

-- Composite index for efficient time range queries within datasets
CREATE INDEX idx_candles_dataset_time ON candles(dataset_id, open_time);
```

#### Modify Table: `backtest_jobs`

Add dataset_id reference:

```sql
ALTER TABLE backtest_jobs ADD COLUMN dataset_id INTEGER NOT NULL DEFAULT 0 REFERENCES datasets(id) ON DELETE SET NULL;
```

### API Endpoints

#### 1. Download with Dataset Name

**POST /api/v1/data/download**

Request:
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-03-31T23:59:59",
  "dataset_name": "BTC 2024 Q1"  // Optional
}
```

Response:
```json
{
  "dataset_id": 123,
  "dataset_name": "BTC 2024 Q1",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 2184,
  "status": "downloaded",
  "message": "Data downloaded successfully"
}
```

**Auto-naming rule:**
- Default: `{symbol} {interval} ({start_date} ~ {end_date})_{timestamp}`
- Example: `BTCUSDT 1h (2024-01-01 ~ 2024-03-31)_1711892400`
- Timestamp suffix prevents name collisions when downloading same range multiple times

#### 2. List Datasets

**GET /api/v1/data/datasets**

Response:
```json
{
  "datasets": [
    {
      "id": 123,
      "name": "BTC 2024 Q1",
      "symbol": "BTCUSDT",
      "interval": "1h",
      "start_time": "2024-01-01T00:00:00",
      "end_time": "2024-03-31T23:59:59",
      "candle_count": 2184,
      "created_at": "2024-03-27T10:30:00"
    }
  ]
}
```

**Future enhancement:** Add pagination parameters (page, page_size) for scalability.

#### 3. Rename Dataset

**PUT /api/v1/data/datasets/{id}/rename**

Request:
```json
{
  "name": "BTC Q1 2024 Updated"
}
```

Response:
```json
{
  "id": 123,
  "name": "BTC Q1 2024 Updated"
}
```

Error response (duplicate name):
```json
{
  "detail": "Dataset name already exists. Please choose a different name."
}
```

#### 4. Delete Dataset

**DELETE /api/v1/data/datasets/{id}**

Pre-deletion checks:
- Returns 409 Conflict if dataset is referenced by existing backtest results
- Returns 404 if dataset not found

Response (success):
```json
{
  "deleted_count": 2184,
  "message": "Dataset deleted successfully"
}
```

Response (conflict):
```json
{
  "detail": "Cannot delete dataset: used by 3 backtest results. Delete backtest results first."
}
```

### Backend Core Updates

#### Backtest Engine Modifications

**File:** `backend/core/backtest_engine.py`

**New signature:**
```python
async def run(
    self,
    strategy_class: Type[StrategyBase],
    dataset_id: int,          # NEW: Required parameter
    start_time: datetime = None,   # Optional: defaults to dataset.start_time
    end_time: datetime = None,     # Optional: defaults to dataset.end_time
    parameters: Dict[str, Any] = None,
    initial_cash: float = 100000.0,
    commission: float = 0.001,
    job_id: int = None
) -> Dict[str, Any]:
    """
    Run backtest on specified dataset.

    Args:
        dataset_id: ID of dataset to use
        start_time: Optional override (clipped to dataset bounds)
        end_time: Optional override (clipped to dataset bounds)
    """
    # Fetch dataset metadata
    dataset = self.db.get_dataset(dataset_id)

    # Use dataset time range if not specified
    if start_time is None:
        start_time = dataset.start_time
    if end_time is None:
        end_time = dataset.end_time

    # Validate time range is within dataset bounds
    if start_time < dataset.start_time or end_time > dataset.end_time:
        raise ValueError(f"Time range must be within dataset bounds "
                        f"({dataset.start_time} ~ {dataset.end_time})")

    # Query candles by dataset_id AND time range
    candles = self.db.get_candles_by_dataset(
        dataset_id=dataset_id,
        start_time=start_time,
        end_time=end_time
    )

    # ... rest of implementation
```

#### Database Class Additions

**File:** `backend/database.py`

**New methods:**
```python
def get_all_symbol_interval_combinations(self) -> List[Tuple[str, str]]:
    """Get all distinct symbol + interval combinations for migration."""
    ...

def get_time_range(self, symbol: str, interval: str) -> TimeRange:
    """Get min/max timestamp for symbol/interval combination."""
    ...

def create_dataset(
    self,
    name: str,
    symbol: str,
    interval: str,
    start_time: datetime,
    end_time: datetime,
    candle_count: int
) -> int:
    """Create dataset record and return dataset_id."""
    ...

def update_candles_dataset_id(
    self,
    symbol: str,
    interval: str,
    dataset_id: int
) -> int:
    """Update all candles for symbol/interval to have dataset_id."""
    ...

def get_datasets(self) -> List[Dataset]:
    """Get all datasets."""
    ...

def get_dataset(self, dataset_id: int) -> Dataset:
    """Get single dataset by ID."""
    ...

def rename_dataset(self, dataset_id: int, new_name: str) -> bool:
    """Rename dataset. Returns False if name already exists."""
    ...

def delete_dataset(self, dataset_id: int) -> int:
    """Delete dataset and associated candles (cascade). Returns deleted count."""
    ...

def get_candles_by_dataset(
    self,
    dataset_id: int,
    start_time: datetime,
    end_time: datetime
) -> List[Candle]:
    """Get candles for dataset within time range."""
    ...

def check_dataset_usage(self, dataset_id: int) -> int:
    """Check how many backtest results reference this dataset."""
    ...
```

### Frontend Components

#### 1. Dataset Selector Component

**Location:** `frontend/components/DatasetSelector.tsx`

**Props:**
```typescript
interface DatasetSelectorProps {
  value: number | null;
  onChange: (datasetId: number, dataset: Dataset) => void;
  disabled?: boolean;
}
```

**Features:**
- Dropdown with format: `{name} ({symbol} {interval}, {count}条)`
- Empty state: "No datasets available. [Download Data]" button
- Loading state with skeleton
- Error handling with retry button

#### 2. BacktestForm Modifications

**New State:**
```typescript
const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
const [selectedDatasetData, setSelectedDatasetData] = useState<Dataset | null>(null);
```

**Layout Order:**
1. Strategy selector
2. **Dataset selector** (NEW)
3. Symbol & Interval (read-only, locked)
4. Time Range (editable, with validation)
5. Initial Cash
6. Strategy Parameters

**Visual Feedback:**
- Lock icon on read-only symbol/interval fields
- Orange warning when time exceeds dataset range
- Helper text: "Dataset range: YYYY-MM-DD ~ YYYY-MM-DD"
- If time outside range: "⚠️ Clipped to dataset range" (submission will clip to bounds)

#### 3. OptimizationForm Modifications

Same as BacktestForm, applied to parameter optimization flow.

#### 4. DownloadedDataSidebar Refactor

**Before (3-layer hierarchy):**
```
BTCUSDT ▶
  1h ▶
    - Q1 Data [删除]
```

**After (flat list):**
```
All Datasets
├── BTC 2024 Q1 (BTCUSDT 1h, 2184条) [重命名] [删除]
├── BTC 2024 Q2 (BTCUSDT 1h, 2184条) [重命名] [删除]
└── ETH Full Year (ETHUSDT 4h, 2190条) [重命名] [删除]
```

**Actions:**
- Click to select (highlights selected)
- Edit icon to rename
- Trash icon to delete
- Show confirmation before delete with dataset details

#### 5. DownloadForm Modifications

Add optional dataset name input:

```tsx
<div className="mb-4">
  <label htmlFor="datasetName">Dataset Name (Optional)</label>
  <input
    id="datasetName"
    type="text"
    value={datasetName}
    onChange={(e) => setDatasetName(e.target.value)}
    placeholder="Auto-generated if empty"
  />
  <p className="text-xs text-gray-500">
    Default: {symbol} {interval} ({startDate} ~ {endDate})_[timestamp]
  </p>
</div>
```

#### 6. Results Page Dataset Display

**Backtest Results Page**

**File:** `frontend/app/results/[id]/page.tsx` and `frontend/components/ConfigurationSection.tsx`

**New display format in ConfigurationSection:**

```tsx
// Existing configuration section
<div className="bg-white rounded-lg shadow-md p-6 mb-8">
  <h2 className="text-xl font-bold text-gray-900 mb-4">Configuration</h2>

  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-4">
    <div>
      <span className="text-gray-600">Strategy:</span>
      <p className="font-medium text-gray-900">{strategy_name}</p>
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
            {formatDate(dataset.start_time)} ~ {formatDate(dataset.end_time)}
          </p>
        </div>
        <div>
          <span className="text-gray-600">Data Points:</span>
          <p className="font-medium text-gray-900">{dataset.candle_count} candles</p>
        </div>
      </>
    )}

    <div>
      <span className="text-gray-600">Symbol:</span>
      <p className="font-medium text-gray-900">{symbol}</p>
    </div>
    <div>
      <span className="text-gray-600">Interval:</span>
      <p className="font-medium text-gray-900">{interval}</p>
    </div>
    <div>
      <span className="text-gray-600">Time Range:</span>
      <p className="font-medium text-gray-900">
        {formatDate(start_time)} ~ {formatDate(end_time)}
      </p>
    </div>
  </div>

  {/* Parameters section */}
  {parameters && Object.keys(parameters).length > 0 && (
    <div className="border-t pt-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Strategy Parameters</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
        {Object.entries(parameters).map(([key, value]) => (
          <div key={key}>
            <span className="text-gray-600">{key}:</span>
            <span className="font-medium text-gray-900 ml-1">{value}</span>
          </div>
        ))}
      </div>
    </div>
  )}
</div>
```

**Parameter Optimization Results Page**

**File:** Similar modifications to optimization results display

**Display dataset info alongside optimization summary:**
- Dataset name
- Dataset symbol and interval
- Dataset time range
- Number of candles used

**Backend Changes:**

Update report generation to include dataset information:

```python
# In backtest engine or report generator
report = {
    # ... existing fields ...
    "dataset": {
        "id": dataset.id,
        "name": dataset.name,
        "symbol": dataset.symbol,
        "interval": dataset.interval,
        "start_time": dataset.start_time.isoformat(),
        "end_time": dataset.end_time.isoformat(),
        "candle_count": dataset.candle_count
    } if dataset_id else None
}
```

**API Response Updates:**

`GET /api/v1/backtest/results/{id}` response includes:

```json
{
  "id": 123,
  "strategy_name": "DualMovingAverage",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-03-31T23:59:59",
  "dataset": {
    "id": 456,
    "name": "BTC 2024 Q1",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-12-31T23:59:59",
    "candle_count": 8760
  },
  "total_return": 0.15,
  // ... rest of fields
}
```

## User Flows

### Flow 1: Download Dataset

1. Navigate to Data Management page
2. Select symbol, interval, start time, end time
3. (Optional) Enter custom dataset name
4. Click "Download"
5. System creates dataset record, downloads candles, associates them
6. Sidebar refreshes, shows new dataset

### Flow 2: Rename Dataset

1. In data management sidebar, find target dataset
2. Click edit (pencil) icon
3. Modal dialog appears with input field
4. Enter new name and confirm
5. API call updates dataset name (validates no duplicates)
6. Sidebar refreshes with new name

### Flow 3: Run Backtest with Dataset

1. Navigate to Backtest page
2. Select strategy
3. Select dataset from dropdown
4. System auto-fills symbol, interval, start/end times
5. (Optional) Adjust time range (warns if outside dataset bounds, will clip)
6. Configure strategy parameters
7. Click "Run Backtest"
8. Backtest executes using selected dataset

### Flow 4: Delete Dataset

1. In data management sidebar, find target dataset
2. Click trash icon
3. Confirmation modal shows:
   - Dataset name
   - Time range
   - Candle count
   - Warning if used in backtests
4. Confirm deletion (if not used in backtests)
5. API deletes dataset and associated candles (cascade)
6. Sidebar refreshes

## Data Migration

### Migration Script

```python
def migrate_existing_data():
    """
    Migrate existing candles to new dataset schema.
    Creates one default dataset per unique symbol+interval combination.
    Uses transaction for atomic rollback on failure.
    """
    migrated_count = 0

    try:
        with db.engine.begin() as conn:  # Transaction
            # Get all distinct symbol + interval combinations
            combinations = db.get_all_symbol_interval_combinations()

            for symbol, interval in combinations:
                # Get time range for this combination
                time_range = db.get_time_range(symbol, interval)
                count = db.get_candles_count(
                    symbol, interval,
                    time_range.start, time_range.end
                )

                if count == 0:
                    continue

                # Create default dataset
                dataset_name = f"{symbol} {interval} Legacy Data"
                dataset_id = db.create_dataset(
                    name=dataset_name,
                    symbol=symbol,
                    interval=interval,
                    start_time=time_range.start,
                    end_time=time_range.end,
                    candle_count=count
                )

                # Associate candles to dataset using raw SQL
                conn.execute(
                    text("""
                        UPDATE candles
                        SET dataset_id = :dataset_id
                        WHERE symbol = :symbol
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

            logger.info(f"Migration complete: {migrated_count} datasets created")
            return migrated_count

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Transaction automatically rolls back
        raise
```

### Rollback Plan

If migration fails:
1. Database transaction automatically rolls back
2. Drop `dataset_id` column from `candles`
3. Drop `datasets` table
4. Restore from backup (if transaction rollback fails)

**Pre-migration checklist:**
- [ ] Create full database backup
- [ ] Test migration script on staging environment
- [ ] Verify backup can be restored

## Error Handling

### API Errors

- **Duplicate dataset name**: Return 400, suggest alternative name with suffix
- **Dataset not found**: Return 404 with helpful message
- **Delete referenced dataset**: Return 409 Conflict with backtest count
- **Foreign key violation**: Return 400, explain cascading behavior
- **Time range outside dataset**: Return 400 with dataset bounds
- **Database errors**: Return 500, log error details

### Frontend Validation

- **Empty dataset list**: Show friendly message with "Download Data" button/link
- **Time range exceeds dataset**: Show orange warning, explain clipping behavior
- **Rename to existing name**: Show error, prevent duplicate
- **Delete confirmation**: Show candle count + backtest count if any
- **Loading states**: Show spinners during async operations

### Toast Messages

- Success: "Dataset downloaded successfully"
- Success: "Dataset renamed to '{name}'"
- Success: "Dataset deleted ({count} candles removed)"
- Error: "Failed to download dataset: {detail}"
- Error: "Dataset name already exists. Try '{name}_2'"
- Warning: "Time range will be clipped to dataset bounds"
- Warning: "Cannot delete dataset used in {n} backtests"

## Testing Strategy

### Backend Tests

1. **Dataset API Tests**
   - Create dataset with custom name
   - Create dataset with auto-generated name (timestamp suffix)
   - List datasets
   - Rename dataset (success and duplicate name error)
   - Delete dataset (success and conflict when referenced)

2. **Download Tests**
   - Download creates dataset record
   - Download associates candles to dataset
   - Duplicate names get timestamp suffix

3. **Migration Tests**
   - Test with empty database
   - Test with existing candles
   - Test rollback on error
   - Verify no orphaned candles after migration
   - Verify dataset counts match candle counts

4. **Backtest Engine Tests**
   - Backtest uses correct dataset
   - Time range clipping works
   - Error when time range completely outside dataset

### Frontend Tests

1. **Dataset Selector Tests**
   - Renders dataset list
   - Shows empty state with link
   - Calls onChange on selection
   - Disabled state works
   - Loading state shows skeleton

2. **BacktestForm Integration Tests**
   - Dataset selection fills symbol/interval/times
   - Symbol/interval are read-only after selection
   - Time validation shows warnings
   - Form submission uses dataset parameters
   - Empty state navigation works

3. **Sidebar Tests**
   - Flat list renders correctly
   - Rename dialog opens and submits
   - Delete confirmation shows details
   - Delete removes dataset from list
   - Delete prevented when used in backtests

4. **Results Page Tests**
   - Dataset information displays correctly
   - Dataset info shows name, symbol, interval, range
   - Dataset info handles null/missing gracefully
   - Layout works on mobile and desktop

### E2E Tests

1. **Download Dataset Flow**
   - Navigate to data page
   - Configure and download dataset
   - Verify dataset appears in sidebar
   - Verify dataset appears in backtest selector

2. **Backtest with Dataset Flow**
   - Navigate to backtest page
   - Select strategy and dataset
   - Verify auto-filled fields
   - Adjust time range
   - Run backtest successfully
   - Verify backtest result shows dataset info

3. **Dataset Management Flow**
   - Rename existing dataset
   - Delete dataset with confirmation
   - Verify backtest selector updates
   - Verify delete prevented when used in backtest

4. **Results Page Dataset Display**
   - Run backtest with specific dataset
   - Navigate to results page
   - Verify dataset information is displayed
   - Verify dataset shows name, symbol, interval, time range
   - Verify layout is responsive

## Implementation Phases

### Phase 1: Backend Foundation (Priority: High)

**Tasks:**
- [ ] Create `datasets` table with indexes
- [ ] Add `dataset_id` column to `candles` table with NOT NULL and DEFAULT
- [ ] Add `dataset_id` column to `backtest_jobs` table
- [ ] Create `Dataset` model in `backend/models/dataset.py`
- [ ] Implement new Database methods (see "Backend Core Updates")
- [ ] Implement migration script with transaction safety
- [ ] Test migration on staging database
- [ ] Modify download API to create datasets with timestamp suffix
- [ ] Implement dataset list API endpoint
- [ ] Implement dataset rename API endpoint
- [ ] Modify delete API with backtest reference check
- [ ] Update `BacktestEngine.run()` signature
- [ ] Update `BacktestEngine` to query by dataset_id

**Estimated Effort:** 8-10 hours

### Phase 2: Frontend Data Management (Priority: Medium)

**Tasks:**
- [ ] Add dataset types to `frontend/lib/api/data.ts`
- [ ] Create `DatasetSelector` component with empty state link
- [ ] Modify `DownloadForm` to include dataset name input
- [ ] Refactor `DownloadedDataSidebar` to flat list
- [ ] Add rename dialog component
- [ ] Add delete confirmation with backtest count
- [ ] Update sidebar styling and icons
- [ ] Add loading states for all operations

**Estimated Effort:** 5-6 hours

### Phase 3: Frontend Backtest & Optimization (Priority: Medium)

**Tasks:**
- [ ] Modify `BacktestForm` to add dataset selector
- [ ] Implement symbol/interval read-only logic with lock icons
- [ ] Add time range validation and clipping warnings
- [ ] Modify form submission to pass dataset_id
- [ ] Modify `OptimizationForm` with same changes
- [ ] Add loading and error states
- [ ] Test time range clipping behavior
- [ ] Modify `ConfigurationSection` to display dataset information
- [ ] Update backtest results API to include dataset data
- [ ] Update optimization results to show dataset info
- [ ] Test dataset display in results pages

**Estimated Effort:** 6-8 hours

### Phase 4: Testing & Documentation (Priority: Low)

**Tasks:**
- [ ] Write backend unit tests
- [ ] Write frontend component tests
- [ ] Write E2E tests
- [ ] Update user documentation with screenshots
- [ ] Create migration guide for users
- [ ] Performance testing (dataset list with 100+ datasets)

**Estimated Effort:** 5-6 hours

**Total Estimated Effort:** 25-30 hours

## Future Enhancements

### Potential Improvements

1. **Dataset Merging**
   - Allow users to merge multiple datasets
   - Automatically handle deduplication
   - Useful for combining adjacent time periods

2. **Dataset Tags**
   - Add custom tags to datasets (e.g., "bull-market", "test")
   - Filter datasets by tags in selector

3. **Dataset Export/Import**
   - Export dataset to CSV
   - Import dataset from file
   - Useful for sharing data between environments

4. **Dataset Validation**
   - Check for data gaps
   - Validate candle continuity
   - Show data quality score

5. **Quick Filters**
   - Filter datasets by symbol in selector
   - Filter by date range
   - Sort by creation date or candle count
   - Pagination for large dataset lists

6. **Dataset Comparison**
   - Compare backtest results across datasets
   - Side-by-side performance metrics

## Dependencies

### External Dependencies

- None (uses existing FastAPI, Next.js, React Query)

### Internal Dependencies

- Backend: `database.py`, `api/data.py`, `core/data_manager.py`, `core/backtest_engine.py`
- Frontend: `components/DownloadedDataSidebar`, `components/BacktestForm`, `components/OptimizationForm`, `lib/api/data.ts`

## Risks & Mitigations

### Risk 1: Migration Failure

**Impact:** High - Existing data could be lost or corrupted

**Mitigation:**
- Create full database backup before migration
- Use database transactions for atomic rollback
- Test migration script on staging database first
- Provide manual migration instructions as fallback
- Add comprehensive logging during migration

### Risk 2: Performance Degradation

**Impact:** Medium - Large dataset lists could slow down UI

**Mitigation:**
- Add pagination to dataset list API (future enhancement)
- Implement server-side filtering/sorting
- Add database indexes on all queried fields
- Cache dataset list in React Query (5-minute stale time)
- Monitor query performance with EXPLAIN QUERY PLAN

### Risk 3: User Confusion

**Impact:** Medium - Users may not understand dataset concept

**Mitigation:**
- Clear UI labels and helper text
- Empty state messages guide users to download data
- Visual cues (lock icons) indicate read-only state
- "What is a dataset?" tooltip or help text
- Update user documentation with screenshots

### Risk 4: Backtest Result Orphaning

**Impact:** Medium - Deleting dataset used in backtests breaks referential integrity

**Mitigation:**
- Add dataset_id to backtest_jobs table
- Check for dependent backtests before deletion
- Return 409 Conflict with helpful message
- Consider ON DELETE SET NULL to preserve results

## Success Criteria

- [ ] Users can download multiple datasets for same symbol/interval
- [ ] Dataset selector appears in backtest and optimization forms
- [ ] Selecting dataset auto-fills all related fields
- [ ] Users can rename and delete datasets
- [ ] Existing data migrates successfully without data loss
- [ ] Backtest engine uses dataset_id for queries
- [ ] Delete prevented when dataset used in backtests
- [ ] All tests pass (backend, frontend, E2E)
- [ ] Performance: dataset list loads in < 100ms
- [ ] No regression in existing functionality

## Glossary

- **Dataset**: A named collection of candles for a specific symbol, interval, and time range
- **Legacy Data**: Existing candles migrated to the new dataset schema
- **Auto-generated name**: Default dataset name created by system with timestamp suffix
- **Flat list**: UI pattern showing all datasets in a single-level list (no hierarchy)
- **Locked state**: Read-only form fields that cannot be modified by user
- **Cascade delete**: Deleting a dataset automatically deletes associated candles
- **Time range clipping**: Backtest automatically adjusts time range to fit dataset bounds

## References

- Existing codebase: `~/code/quant2`
- Database schema: `backend/database.py`
- Backtest engine: `backend/core/backtest_engine.py`
- Frontend components: `frontend/components/`
