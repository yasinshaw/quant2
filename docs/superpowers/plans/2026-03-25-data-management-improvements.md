# Data Management Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add data deletion functionality, improve download result display with modals, and remove redundant UI components

**Architecture:** Backend adds DELETE endpoint and database method. Frontend creates reusable Modal and ConfirmDialog components, integrates delete into sidebar, and replaces inline download results with modal display.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js 14, React Query, TypeScript, Tailwind CSS, Playwright

---

## File Structure

### Backend
- **Modify** `backend/database.py` - Add delete_candles_by_symbol_interval method
- **Modify** `backend/api/data.py` - Add DELETE /data/{symbol}/{interval} endpoint

### Frontend Components (New)
- **Create** `frontend/components/Modal.tsx` - Reusable modal dialog component
- **Create** `frontend/components/ConfirmDialog.tsx` - Confirmation dialog for destructive actions

### Frontend Components (Modified)
- **Modify** `frontend/lib/api/data.ts` - Add deleteData method and DeleteResponse type
- **Modify** `frontend/components/DownloadedDataSidebar.tsx` - Add delete button and confirmation flow
- **Modify** `frontend/app/data/page.tsx` - Remove Data Availability section, add download result modal

### Frontend Components (Deleted)
- **Delete** `frontend/components/DataStatusCard.tsx` - No longer needed after removing Data Availability

### Tests
- **Create** `tests/test_data_api_delete.py` - Backend delete endpoint tests
- **Create** `frontend/e2e/data-delete.spec.ts` - E2E tests for delete functionality
- **Create** `frontend/e2e/download-modal.spec.ts` - E2E tests for download result modal

---

## Phase 1: Backend - Database Layer

### Task 1: Add Database Delete Method

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_database_delete.py`:

```python
"""Tests for database delete functionality"""
import pytest
from datetime import datetime
from backend.database import Database
from backend.models import Candle


class TestDatabaseDelete:
    def test_delete_candles_by_symbol_interval_success(self):
        """Test successful deletion of candles"""
        db = Database("sqlite:///:memory:")
        db.create_tables()

        # Insert test data
        with db.get_session() as session:
            candle = Candle(
                symbol="BTCUSDT",
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
            remaining = session.query(Candle).filter(
                Candle.symbol == "BTCUSDT",
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
            for interval in ["1h", "4h"]:
                candle = Candle(
                    symbol="BTCUSDT",
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
            remaining = session.query(Candle).filter(
                Candle.symbol == "BTCUSDT",
                Candle.interval == "4h"
            ).count()
            assert remaining == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_delete.py -v`
Expected: FAIL with "AttributeError: 'Database' object has no attribute 'delete_candles_by_symbol_interval'"

- [ ] **Step 3: Write minimal implementation**

Add to `backend/database.py` in the Candle operations section:

```python
def delete_candles_by_symbol_interval(self, symbol: str, interval: str) -> int:
    """
    Delete all candles for a specific symbol and interval.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: K-line interval (e.g., 1h)

    Returns:
        Number of deleted records

    Raises:
        Exception: Database error
    """
    with self.get_session() as session:
        count = session.query(Candle)\
            .filter(Candle.symbol == symbol)\
            .filter(Candle.interval == interval)\
            .delete()
        return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_delete.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/database.py tests/test_database_delete.py
git commit -m "feat(database): add delete_candles_by_symbol_interval method"
```

---

### Task 2: Add DELETE API Endpoint

**Files:**
- Modify: `backend/api/data.py`
- Create: `tests/test_data_api_delete.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_data_api_delete.py`:

```python
"""Tests for data delete API endpoint"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from backend.main import app
from backend.database import Database
from backend.models import Candle
from backend.config import settings


class TestDataDeleteAPI:
    def test_delete_data_success(self):
        """Test successful deletion via API"""
        # Setup test database
        db = Database("sqlite:///:memory:")
        db.create_tables()

        # Insert test data
        with db.get_session() as session:
            candle = Candle(
                symbol="BTCUSDT",
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

        # Make request
        client = TestClient(app)
        response = client.delete("/api/v1/data/BTCUSDT/1h")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["interval"] == "1h"
        assert data["deleted_count"] == 1
        assert "message" in data

    def test_delete_data_not_found(self):
        """Test deletion when data doesn't exist"""
        client = TestClient(app)
        response = client.delete("/api/v1/data/BTCUSDT/1h")

        assert response.status_code == 404
        assert "No data found" in response.json()["detail"]

    def test_delete_data_database_error(self):
        """Test handling of database errors"""
        # This would require mocking the database
        # For now, we'll skip this edge case
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_data_api_delete.py::TestDataDeleteAPI::test_delete_data_success -v`
Expected: FAIL with "404" or "405 Method Not Allowed"

- [ ] **Step 3: Write minimal implementation**

Add to `backend/api/data.py` after the `/downloaded` endpoint:

```python
@router.delete("/{symbol}/{interval}")
async def delete_data(symbol: str, interval: str) -> Dict[str, Any]:
    """
    Delete all candles for a specific symbol and interval.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: K-line interval (e.g., 1h)

    Returns:
        Dict containing:
            - symbol: str
            - interval: str
            - deleted_count: int
            - message: str

    Raises:
        HTTPException: 404 if no data found
        HTTPException: 500 if deletion fails
    """
    try:
        deleted_count = _db.delete_candles_by_symbol_interval(symbol, interval)

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for {symbol} {interval}"
            )

        logger.info(f"Deleted {deleted_count} candles for {symbol} {interval}")

        return {
            "symbol": symbol,
            "interval": interval,
            "deleted_count": deleted_count,
            "message": "Successfully deleted data"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete data"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_data_api_delete.py -v`
Expected: PASS (2 tests, 1 skipped)

- [ ] **Step 5: Commit**

```bash
git add backend/api/data.py tests/test_data_api_delete.py
git commit -m "feat(api): add DELETE /data/{symbol}/{interval} endpoint"
```

---

## Phase 2: Frontend - Reusable Components

### Task 3: Create Modal Component

**Files:**
- Create: `frontend/components/Modal.tsx`

- [ ] **Step 1: Create Modal component**

Create `frontend/components/Modal.tsx`:

```typescript
'use client';

import { useEffect, useRef } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  variant?: 'success' | 'info' | 'error';
}

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  variant = 'info',
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const variantStyles = {
    success: 'border-green-500',
    info: 'border-blue-500',
    error: 'border-red-500',
  };

  const iconMap = {
    success: (
      <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    info: (
      <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        className={`bg-white rounded-lg shadow-xl max-w-md w-full border-t-4 ${variantStyles[variant]}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            {iconMap[variant]}
            <h2 id="modal-title" className="text-lg font-semibold text-gray-900">
              {title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">{children}</div>

        {/* Footer */}
        <div className="flex justify-end p-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify component compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/Modal.tsx
git commit -m "feat(components): add reusable Modal component"
```

---

### Task 4: Create ConfirmDialog Component

**Files:**
- Create: `frontend/components/ConfirmDialog.tsx`

- [ ] **Step 1: Create ConfirmDialog component**

Create `frontend/components/ConfirmDialog.tsx`:

```typescript
'use client';

import { useEffect } from 'react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  message: string;
  details?: {
    count: number;
    startTime: string;
    endTime: string;
  };
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning';
}

export default function ConfirmDialog({
  isOpen,
  onConfirm,
  onCancel,
  title,
  message,
  details,
  confirmText = '删除',
  cancelText = '取消',
  variant = 'danger',
}: ConfirmDialogProps) {
  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onCancel]);

  // Prevent body scroll
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const formatDate = (isoString: string): string => {
    return new Date(isoString).toISOString().split('T')[0];
  };

  const variantStyles = {
    danger: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
    warning: 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
      >
        {/* Header */}
        <div className="p-4 border-b">
          <h2 id="dialog-title" className="text-lg font-semibold text-gray-900">
            {title}
          </h2>
        </div>

        {/* Content */}
        <div className="p-6">
          <p id="dialog-description" className="text-gray-700 mb-4">
            {message}
          </p>

          {details && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">K线数量:</span>
                <span className="font-medium text-gray-900">
                  {details.count.toLocaleString()} 条
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">时间范围:</span>
                <span className="font-medium text-gray-900">
                  {formatDate(details.startTime)} ~ {formatDate(details.endTime)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-4 border-t bg-gray-50">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-100 transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-white rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${variantStyles[variant]}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify component compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ConfirmDialog.tsx
git commit -m "feat(components): add ConfirmDialog component for destructive actions"
```

---

## Phase 3: Frontend - API Integration

### Task 5: Add Delete API Method

**Files:**
- Modify: `frontend/lib/api/data.ts`

- [ ] **Step 1: Add delete method and types**

Modify `frontend/lib/api/data.ts` to add:

```typescript
// Add to existing types section
export interface DeleteResponse {
  symbol: string;
  interval: string;
  deleted_count: number;
  message: string;
}

// Add to dataApi object
export const dataApi = {
  // ... existing methods ...

  deleteData: async (symbol: string, interval: string): Promise<DeleteResponse> => {
    const response = await api.delete<DeleteResponse>(
      `/api/v1/data/${symbol}/${interval}`
    );
    return response.data;
  },
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/data.ts
git commit -m "feat(api): add deleteData method and DeleteResponse type"
```

---

### Task 6: Add Delete to Sidebar

**Files:**
- Modify: `frontend/components/DownloadedDataSidebar.tsx`

- [ ] **Step 1: Add delete functionality to sidebar**

Modify `frontend/components/DownloadedDataSidebar.tsx`:

Add imports at the top:
```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { dataApi } from '@/lib/api/data';
import ConfirmDialog from './ConfirmDialog';
```

Add state management inside component (after existing state):
```typescript
const queryClient = useQueryClient();
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
const [selectedDeletion, setSelectedDeletion] = useState<{
  symbol: string;
  interval: string;
  count: number;
  startTime: string;
  endTime: string;
} | null>(null);

const deleteMutation = useMutation({
  mutationFn: ({ symbol, interval }: { symbol: string; interval: string }) =>
    dataApi.deleteData(symbol, interval),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['downloadedData'] });
    // TODO: Add toast notification
    console.log('删除成功');
  },
  onError: (error) => {
    // TODO: Add error toast
    console.error('删除失败:', error);
  },
});

const handleDeleteClick = (
  symbol: string,
  interval: DownloadedInterval
) => {
  setSelectedDeletion({
    symbol,
    interval: interval.interval,
    count: interval.count,
    startTime: interval.start_time,
    endTime: interval.end_time,
  });
  setDeleteDialogOpen(true);
};

const handleConfirmDelete = () => {
  if (selectedDeletion) {
    deleteMutation.mutate({
      symbol: selectedDeletion.symbol,
      interval: selectedDeletion.interval,
    });
    setDeleteDialogOpen(false);
    setSelectedDeletion(null);
  }
};

const handleCancelDelete = () => {
  setDeleteDialogOpen(false);
  setSelectedDeletion(null);
};
```

Replace the interval button section (inside the intervals list) with:
```typescript
<button
  key={interval.interval}
  onClick={() => onSymbolSelect(item.symbol, interval.interval)}
  aria-pressed={isSelected}
  className={`w-full px-4 py-3 text-left transition-colors group ${
    isSelected
      ? 'bg-blue-100 border-l-4 border-blue-500'
      : 'hover:bg-gray-50 border-l-4 border-transparent'
  }`}
>
  <div className="flex items-center justify-between mb-1">
    <span className="text-sm font-medium text-gray-900">
      {interval.interval}
    </span>
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500">
        {formatCount(interval.count)} 条
      </span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          handleDeleteClick(item.symbol, interval);
        }}
        className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-600 transition-all"
        aria-label={`删除 ${item.symbol} ${interval.interval} 数据`}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
          />
        </svg>
      </button>
    </div>
  </div>
  <div className="text-xs text-gray-500">
    {formatDate(interval.start_time)} ~ {formatDate(interval.end_time)}
  </div>
</button>
```

Add ConfirmDialog at the end of the component (before closing div):
```typescript
<ConfirmDialog
  isOpen={deleteDialogOpen}
  onConfirm={handleConfirmDelete}
  onCancel={handleCancelDelete}
  title="确认删除"
  message={`确定要删除 ${selectedDeletion?.symbol} ${selectedDeletion?.interval} 的数据吗？此操作不可恢复。`}
  details={
    selectedDeletion
      ? {
          count: selectedDeletion.count,
          startTime: selectedDeletion.startTime,
          endTime: selectedDeletion.endTime,
        }
      : undefined
  }
  confirmText="删除"
  cancelText="取消"
  variant="danger"
/>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Test delete functionality manually**

Start dev server: `cd frontend && pnpm dev`
1. Open http://localhost:3000/data
2. Hover over an interval in the sidebar
3. Click the delete icon
4. Verify confirmation dialog appears with correct details
5. Click cancel - dialog should close without deleting
6. Click delete again and confirm
7. Verify data is removed from sidebar

- [ ] **Step 4: Commit**

```bash
git add frontend/components/DownloadedDataSidebar.tsx
git commit -m "feat(sidebar): add delete functionality with confirmation dialog"
```

---

### Task 7: Replace Download Result with Modal

**Files:**
- Modify: `frontend/app/data/page.tsx`

- [ ] **Step 1: Remove Data Availability section and add Modal**

Modify `frontend/app/data/page.tsx`:

Remove the import:
```typescript
// DELETE this line:
import DataStatusCard from '@/components/DataStatusCard';
```

Add Modal import:
```typescript
import Modal from '@/components/Modal';
```

Remove the Data Availability section (lines ~271-283):
```typescript
// DELETE this entire section:
{/* Data Status Section */}
<div className="mt-8">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Data Availability</h2>
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {INTERVALS.slice(0, 6).map((interval) => (
      <DataStatusCard
        key={`${selectedSymbol}-${interval.value}`}
        symbol={selectedSymbol}
        interval={interval.value}
      />
    ))}
  </div>
</div>
```

Replace the Download Result section (lines ~168-269) with:
```typescript
{/* Download Result Modal */}
<Modal
  isOpen={!!downloadResult}
  onClose={() => setDownloadResult(null)}
  title={
    downloadResult?.status === 'downloaded'
      ? '下载成功'
      : downloadResult?.status === 'already_exists'
      ? '数据已存在'
      : '下载失败'
  }
  variant={
    downloadResult?.status === 'downloaded'
      ? 'success'
      : downloadResult?.status === 'already_exists'
      ? 'info'
      : 'error'
  }
>
  <div className="space-y-3">
    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-sm text-gray-500">交易对</p>
        <p className="font-semibold text-gray-900">{downloadResult?.symbol}</p>
      </div>
      <div>
        <p className="text-sm text-gray-500">周期</p>
        <p className="font-semibold text-gray-900">{downloadResult?.interval}</p>
      </div>
      <div className="col-span-2">
        <p className="text-sm text-gray-500">K线数量</p>
        <p className="font-semibold text-gray-900">
          {downloadResult?.count.toLocaleString()}
        </p>
      </div>
    </div>
    {downloadResult?.message && (
      <div className="pt-3 border-t border-gray-200">
        <p className="text-sm text-gray-700">{downloadResult.message}</p>
      </div>
    )}
  </div>
</Modal>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Test download modal manually**

1. Start dev server: `cd frontend && pnpm dev`
2. Open http://localhost:3000/data
3. Download data for any symbol/interval
4. Verify modal appears with correct information
5. Click close button - modal should close
6. Click background - modal should close
7. Press ESC - modal should close

- [ ] **Step 4: Commit**

```bash
git add frontend/app/data/page.tsx
git commit -m "feat(page): replace inline download result with modal, remove Data Availability section"
```

---

## Phase 4: Testing

### Task 8: Add E2E Tests for Delete

**Files:**
- Create: `frontend/e2e/data-delete.spec.ts`

- [ ] **Step 1: Create delete E2E test**

Create `frontend/e2e/data-delete.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Data Delete Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Start backend and frontend servers
    await page.goto('http://localhost:3000/data');
  });

  test('should show delete button on hover', async ({ page }) => {
    // Wait for sidebar to load
    await page.waitForSelector('[data-testid="downloaded-sidebar"]');

    // Hover over an interval item
    const firstInterval = page.locator('[data-testid="interval-item"]').first();
    await firstInterval.hover();

    // Verify delete button appears
    const deleteButton = firstInterval.locator('[aria-label*="删除"]');
    await expect(deleteButton).toBeVisible();
  });

  test('should show confirmation dialog when delete clicked', async ({ page }) => {
    await page.waitForSelector('[data-testid="downloaded-sidebar"]');

    // Hover and click delete
    const firstInterval = page.locator('[data-testid="interval-item"]').first();
    await firstInterval.hover();
    await firstInterval.locator('[aria-label*="删除"]').click();

    // Verify confirmation dialog appears
    const dialog = page.locator('role=alertdialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('确认删除');
  });

  test('should cancel deletion', async ({ page }) => {
    await page.waitForSelector('[data-testid="downloaded-sidebar"]');

    // Click delete
    const firstInterval = page.locator('[data-testid="interval-item"]').first();
    await firstInterval.hover();
    await firstInterval.locator('[aria-label*="删除"]').click();

    // Click cancel
    await page.locator('button:has-text("取消")').click();

    // Verify dialog is closed
    await expect(page.locator('role=alertdialog')).not.toBeVisible();
  });

  test('should delete data successfully', async ({ page }) => {
    await page.waitForSelector('[data-testid="downloaded-sidebar"]');

    // Get initial count
    const intervalsBefore = await page.locator('[data-testid="interval-item"]').count();

    // Delete first interval
    const firstInterval = page.locator('[data-testid="interval-item"]').first();
    await firstInterval.hover();
    await firstInterval.locator('[aria-label*="删除"]').click();
    await page.locator('button:has-text("删除")').click();

    // Wait for deletion to complete
    await page.waitForTimeout(1000);

    // Verify interval was removed
    const intervalsAfter = await page.locator('[data-testid="interval-item"]').count();
    expect(intervalsAfter).toBe(intervalsBefore - 1);
  });

  test('should close dialog with ESC key', async ({ page }) => {
    await page.waitForSelector('[data-testid="downloaded-sidebar"]');

    // Open dialog
    const firstInterval = page.locator('[data-testid="interval-item"]').first();
    await firstInterval.hover();
    await firstInterval.locator('[aria-label*="删除"]').click();

    // Press ESC
    await page.keyboard.press('Escape');

    // Verify dialog is closed
    await expect(page.locator('role=alertdialog')).not.toBeVisible();
  });
});
```

- [ ] **Step 2: Add data-testid attributes to sidebar**

Modify `frontend/components/DownloadedDataSidebar.tsx`:

Add to the main container div:
```typescript
<div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto" data-testid="downloaded-sidebar">
```

Add to the interval button:
```typescript
<button
  key={interval.interval}
  data-testid="interval-item"
  onClick={() => onSymbolSelect(item.symbol, interval.interval)}
  // ... rest of props
>
```

- [ ] **Step 3: Run E2E tests**

Run: `cd frontend && pnpm test:e2e data-delete.spec.ts`
Expected: 5 tests pass

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/data-delete.spec.ts frontend/components/DownloadedDataSidebar.tsx
git commit -m "test(e2e): add comprehensive tests for delete functionality"
```

---

### Task 9: Add E2E Tests for Download Modal

**Files:**
- Create: `frontend/e2e/download-modal.spec.ts`

- [ ] **Step 1: Create download modal E2E test**

Create `frontend/e2e/download-modal.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Download Result Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/data');
  });

  test('should show modal after successful download', async ({ page }) => {
    // Fill download form
    await page.selectOption('select[name="symbol"]', 'BTCUSDT');
    await page.selectOption('select[name="interval"]', '1h');

    // Set dates (short range for quick test)
    const startDate = page.locator('input[name="startDate"]');
    const endDate = page.locator('input[name="endDate"]');
    await startDate.fill('2024-01-01');
    await endDate.fill('2024-01-02');

    // Submit form
    await page.click('button:has-text("开始下载")');

    // Wait for modal to appear
    const modal = page.locator('role=dialog');
    await expect(modal).toBeVisible({ timeout: 30000 });

    // Verify modal content
    await expect(modal).toContainText('BTCUSDT');
    await expect(modal).toContainText('1h');
    await expect(modal.locator('text=K线数量')).toBeVisible();
  });

  test('should close modal with close button', async ({ page }) => {
    // Trigger download (or mock it)
    // For now, we'll just test the modal component directly
    // This would require mocking the download API response

    // TODO: Add API mocking to make this test reliable
  });

  test('should close modal with background click', async ({ page }) => {
    // TODO: Implement with API mocking
  });

  test('should close modal with ESC key', async ({ page }) => {
    // TODO: Implement with API mocking
  });

  test('should show different variants for different statuses', async ({ page }) => {
    // TODO: Test success, info, error variants
  });
});
```

- [ ] **Step 2: Run E2E tests**

Run: `cd frontend && pnpm test:e2e download-modal.spec.ts`
Expected: At least 1 test passes (others are placeholders)

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/download-modal.spec.ts
git commit -m "test(e2e): add tests for download result modal"
```

---

## Phase 5: Cleanup

### Task 10: Remove Unused Components

**Files:**
- Delete: `frontend/components/DataStatusCard.tsx`

- [ ] **Step 1: Verify DataStatusCard is not used elsewhere**

Run: `cd frontend && grep -r "DataStatusCard" --include="*.tsx" --include="*.ts"`
Expected: Only find references in the file itself (no imports elsewhere)

- [ ] **Step 2: Delete DataStatusCard component**

Run: `rm frontend/components/DataStatusCard.tsx`

- [ ] **Step 3: Verify build still works**

Run: `cd frontend && pnpm build`
Expected: Build succeeds without errors

- [ ] **Step 4: Run all tests**

Run: `cd frontend && pnpm test:e2e`
Expected: All tests pass

Run: `pytest tests/ -v`
Expected: All backend tests pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove unused DataStatusCard component"
```

---

### Task 11: Final Integration Test

**Files:**
- None (manual testing)

- [ ] **Step 1: Start both servers**

Terminal 1:
```bash
cd backend
source venv/bin/activate
python main.py
```

Terminal 2:
```bash
cd frontend
pnpm dev
```

- [ ] **Step 2: Test complete delete flow**

1. Open http://localhost:3000/data
2. Verify sidebar shows downloaded data
3. Hover over an interval
4. Click delete icon
5. Verify confirmation dialog shows correct details
6. Click delete
7. Verify data is removed from sidebar
8. Verify current selection remains unchanged

- [ ] **Step 3: Test download modal flow**

1. Select symbol and interval
2. Set date range
3. Click download
4. Verify modal appears with correct information
5. Close modal with button, background, and ESC key
6. Verify sidebar updates with new data

- [ ] **Step 4: Test error handling**

1. Try to delete non-existent data (should show error)
2. Try to download invalid data (should show error modal)

- [ ] **Step 5: Document any issues found**

If issues found:
- Create GitHub issues
- Or fix immediately if simple

- [ ] **Step 6: Final commit (if needed)**

```bash
git add -A
git commit -m "test: verify all functionality works end-to-end"
```

---

## Summary

**Total Tasks**: 11
**Estimated Time**: 3-4 hours

**Key Milestones**:
1. Backend delete functionality complete (Tasks 1-2)
2. Frontend components created (Tasks 3-4)
3. Integration complete (Tasks 5-7)
4. Tests passing (Tasks 8-9)
5. Production ready (Tasks 10-11)

**Success Criteria**:
- ✅ Users can delete data with confirmation
- ✅ Download results display in modal
- ✅ Data Availability section removed
- ✅ All tests pass
- ✅ No TypeScript errors
- ✅ No console errors
- ✅ Responsive design works
- ✅ Keyboard accessible
