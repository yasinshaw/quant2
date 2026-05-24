# Data Management Improvements Design

**Date**: 2026-03-25
**Status**: Draft
**Author**: Claude

## Overview

Improve the data management page by adding delete functionality, removing redundant UI components, and enhancing user experience with modal dialogs.

## Goals

1. Enable users to delete downloaded historical data
2. Remove redundant Data Availability module (duplicate of sidebar information)
3. Display download results in a modal dialog for better UX

## User Stories

### Story 1: Delete Data
**As a** user
**I want to** delete downloaded data I no longer need
**So that** I can manage my data storage and keep only relevant datasets

**Acceptance Criteria**:
- Delete button visible on each interval in the sidebar
- Confirmation dialog shows data details before deletion
- Success/error feedback after deletion
- Sidebar refreshes automatically after successful deletion
- Current selection remains unchanged after deletion

### Story 2: View Download Results
**As a** user
**I want to** see download results in a popup dialog
**So that** I get clear feedback without scrolling the page

**Acceptance Criteria**:
- Modal automatically appears after download completes
- Different visual styles for success/existing/error states
- Manual dismiss by clicking close button or background
- Clear display of symbol, interval, and candle count

### Story 3: Cleaner Interface
**As a** user
**I want** a simplified data management interface
**So that** I can focus on essential actions without redundant information

**Acceptance Criteria**:
- Data Availability section removed (duplicate of sidebar)
- Page layout remains balanced and functional
- All essential functionality preserved

## Technical Design

### Backend Changes

#### 1. New DELETE Endpoint

**File**: `backend/api/data.py`

**Endpoint**: `DELETE /api/v1/data/{symbol}/{interval}`

**Purpose**: Delete all candles for a specific symbol and interval

**Request**:
- Path parameters: `symbol` (string), `interval` (string)

**Response**:
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "deleted_count": 8760,
  "message": "Successfully deleted data"
}
```

**Error Responses**:
- 404: Data not found
- 500: Database deletion failed

**Implementation**:
```python
@router.delete("/{symbol}/{interval}")
async def delete_data(symbol: str, interval: str) -> Dict[str, Any]:
    """
    Delete all candles for a specific symbol and interval.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: K-line interval (e.g., 1h)

    Returns:
        Dict containing deletion confirmation and count

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

#### 2. Database Method

**File**: `backend/database.py`

**Method**: `delete_candles_by_symbol_interval(symbol: str, interval: str) -> int`

**Purpose**: Delete all candles matching symbol and interval

**Implementation**:
```python
def delete_candles_by_symbol_interval(self, symbol: str, interval: str) -> int:
    """
    Delete all candles for a specific symbol and interval.

    Args:
        symbol: Trading pair symbol
        interval: K-line interval

    Returns:
        Number of deleted records

    Raises:
        Exception: Database error
    """
    with self.create_session() as session:
        count = session.query(Candle)\
            .filter(Candle.symbol == symbol)\
            .filter(Candle.interval == interval)\
            .delete()
        return count
```

### Frontend Changes

#### 1. New Component: Modal

**File**: `frontend/components/Modal.tsx` (新建)

**Purpose**: Reusable modal dialog component

**Props**:
```typescript
interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  variant?: 'success' | 'info' | 'error'
}
```

**Features**:
- Responsive design (mobile-friendly)
- Click background to close
- ESC key to close
- Color variants for different states
- Accessible (ARIA attributes)

**Implementation Details**:
- Use Tailwind CSS for styling
- Portal rendering to avoid z-index issues
- Focus trap for accessibility
- Smooth enter/exit animations

#### 2. New Component: ConfirmDialog

**File**: `frontend/components/ConfirmDialog.tsx` (新建)

**Purpose**: Confirmation dialog for destructive actions

**Props**:
```typescript
interface ConfirmDialogProps {
  isOpen: boolean
  onConfirm: () => void
  onCancel: () => void
  title: string
  message: string
  details?: {
    count: number
    startTime: string
    endTime: string
  }
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning'
}
```

**Features**:
- Danger variant with red button for delete actions
- Display detailed information (count, time range)
- Click outside or cancel to dismiss
- Keyboard accessible

#### 3. Modified Component: DownloadedDataSidebar

**File**: `frontend/components/DownloadedDataSidebar.tsx` (修改)

**Changes**:
1. Add delete button to each interval item
2. Add state management for delete confirmation
3. Integrate ConfirmDialog component
4. Handle delete mutation with React Query

**New State**:
```typescript
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
const [selectedDeletion, setSelectedDeletion] = useState<{
  symbol: string
  interval: string
  count: number
  startTime: string
  endTime: string
} | null>(null)
```

**Delete Button**:
- Trash icon (Heroicons outline trash)
- Positioned on the right side of each interval item
- Gray by default, red on hover
- Size: small (w-4 h-4)

**Delete Flow**:
```
User clicks delete icon
→ Set selectedDeletion state
→ Open ConfirmDialog
→ User confirms
→ Call deleteData API
→ On success: show toast, refetch downloaded data
→ On error: show error toast
→ Keep current selection unchanged
```

#### 4. Modified Page: Data Management

**File**: `frontend/app/data/page.tsx` (修改)

**Changes**:
1. Remove Data Availability section (lines 271-283)
2. Replace inline download result card with Modal component
3. Remove DataStatusCard import

**Removed Code**:
- Lines 271-283: Data Availability section
- Line 7: DataStatusCard import (if not used elsewhere)

**Added Modal for Download Results**:
```typescript
<Modal
  isOpen={!!downloadResult}
  onClose={() => setDownloadResult(null)}
  title={...}
  variant={...}
>
  {/* Display symbol, interval, count, message */}
</Modal>
```

#### 5. API Client Update

**File**: `frontend/lib/api/data.ts` (修改)

**New Method**:
```typescript
deleteData: async (symbol: string, interval: string): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(
    `/api/v1/data/${symbol}/${interval}`
  )
  return response.data
}
```

**New Type**:
```typescript
export interface DeleteResponse {
  symbol: string
  interval: string
  deleted_count: number
  message: string
}
```

#### 6. Deleted File

**File**: `frontend/components/DataStatusCard.tsx` (删除)

**Reason**: Component only used in Data Availability section, which is being removed

## Data Flow

### Delete Data Flow
```
User Action: Click delete button
     ↓
UI State: Open ConfirmDialog with details
     ↓
User Action: Confirm deletion
     ↓
API Call: DELETE /api/v1/data/{symbol}/{interval}
     ↓
Backend: Database.delete_candles_by_symbol_interval()
     ↓
Response: { deleted_count, message }
     ↓
Frontend:
  - Show success toast
  - Invalidate 'downloadedData' query
  - Sidebar refetches automatically
  - Keep current selection
```

### Download Data Flow
```
User Action: Submit download form
     ↓
API Call: POST /api/v1/data/download
     ↓
Backend: DataManager.download_and_save()
     ↓
Response: { status, count, message }
     ↓
Frontend:
  - Set downloadResult state
  - Modal opens automatically
  - Show result with appropriate styling
  - Invalidate 'downloadedData' query
  - Sidebar refetches automatically
     ↓
User Action: Close modal
```

## Component Interactions

```
┌─────────────────────────────────────────────────────┐
│ Data Page (page.tsx)                                │
│                                                     │
│  ┌──────────────┐  ┌────────────────────────────┐ │
│  │   Sidebar    │  │  Main Content              │ │
│  │              │  │                            │ │
│  │  Downloaded  │  │  - Market Selection        │ │
│  │  DataSidebar │  │  - Download Form           │ │
│  │              │  │  - [Removed] Data Avail.   │ │
│  │  - Symbol 1  │  │                            │ │
│  │    - 1h [🗑️] │  │                            │ │
│  │    - 4h [🗑️] │  │                            │ │
│  │  - Symbol 2  │  │                            │ │
│  │    - 1d [🗑️] │  │                            │ │
│  │              │  │                            │ │
│  └──────────────┘  └────────────────────────────┘ │
│                                                     │
│  [Modal - Download Result]                          │
│  [ConfirmDialog - Delete Confirmation]              │
└─────────────────────────────────────────────────────┘
```

## Error Handling

### Backend Errors
- **404 Not Found**: No data exists for the specified symbol/interval
- **500 Internal Server Error**: Database operation failed
- All errors logged with stack traces
- User-friendly error messages in responses

### Frontend Errors
- Network errors caught and displayed as toast notifications
- Loading states shown during API calls
- Error boundaries prevent app crashes
- User can retry failed operations

## Testing Strategy

### Backend Tests
**File**: `tests/test_data_api.py`

**Test Cases**:
1. `test_delete_data_success` - Successfully delete existing data
2. `test_delete_data_not_found` - Attempt to delete non-existent data
3. `test_delete_data_database_error` - Handle database errors gracefully

### Frontend Tests (E2E)
**File**: `frontend/e2e/data-management.spec.ts`

**Test Cases**:
1. Delete data flow - click delete, confirm, verify removal
2. Cancel delete - click delete, cancel, verify data still exists
3. Download result modal - download data, verify modal appears
4. Modal dismissal - close modal with button, background click, ESC key
5. Sidebar refresh after delete - verify sidebar updates automatically

## Migration & Rollout

### Phase 1: Backend
1. Add database method
2. Add DELETE endpoint
3. Test with pytest
4. Verify no breaking changes

### Phase 2: Frontend Components
1. Create Modal component
2. Create ConfirmDialog component
3. Unit test components in isolation

### Phase 3: Integration
1. Update API client
2. Modify DownloadedDataSidebar
3. Modify data page
4. Remove DataStatusCard

### Phase 4: Testing
1. Run all backend tests
2. Run all E2E tests
3. Manual testing of delete flow
4. Manual testing of download modal

### Phase 5: Cleanup
1. Remove unused DataStatusCard file
2. Update any documentation
3. Code review

## Success Criteria

1. ✅ Users can delete data with confirmation dialog
2. ✅ Download results display in modal instead of inline card
3. ✅ Data Availability section removed
4. ✅ All existing tests pass
5. ✅ New tests for delete functionality pass
6. ✅ No console errors
7. ✅ Responsive design works on mobile
8. ✅ Accessibility requirements met (keyboard navigation, ARIA)

## Rollback Plan

If issues arise:
1. Revert frontend changes (git revert)
2. Remove DELETE endpoint from backend
3. Remove database method
4. DataStatusCard can be restored if needed

No database migrations required, so rollback is straightforward.

## Future Enhancements

Potential improvements not in scope:
- Bulk delete (select multiple intervals)
- Delete by time range (not just entire dataset)
- Undo delete (soft delete with restore capability)
- Download history with retry option
- Progress indicator for large downloads
