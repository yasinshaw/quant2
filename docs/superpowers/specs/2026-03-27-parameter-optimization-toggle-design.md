# Parameter Optimization Toggle Design

**Date**: 2026-03-27
**Author**: Claude
**Status**: Draft
**Type**: Feature Enhancement

## Overview

Add a one-click toggle mechanism to the parameter optimization form, allowing users to enable or disable all parameter optimization switches simultaneously. This improves user efficiency when configuring multiple parameters for optimization.

## Problem Statement

Currently, users must manually toggle each parameter's optimization switch individually. For strategies with many parameters (5+), this becomes tedious and error-prone. A batch operation feature would significantly improve the user experience.

## Design

### UI Design

**Location**: In the "Parameters" section header (OptimizationForm.tsx, line 568-577)

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Parameters                    Combinations: 125         │
│                      [全部开启] [全部关闭]               │
└─────────────────────────────────────────────────────────┘
```

**Button Styling**:
- Style: Primary buttons (blue background)
- "Enable All": `bg-blue-600 hover:bg-blue-700`
- "Disable All": `bg-blue-600 hover:bg-blue-700`
- Size: Small `px-3 py-1 text-sm`
- Spacing: `space-x-2` between buttons
- Disabled state: `disabled:opacity-50 disabled:cursor-not-allowed`

**Smart State Management**:
- All parameters enabled → "Enable All" disabled, "Disable All" enabled
- All parameters disabled → "Disable All" disabled, "Enable All" enabled
- Mixed state → Both buttons enabled

### Implementation

#### State Calculation

```typescript
const allParamsOptimized = Object.values(parameterConfigs).every(config => config.optimize);
const noParamsOptimized = Object.values(parameterConfigs).every(config => !config.optimize);
```

#### Handler Functions

**Enable All**:
```typescript
const handleEnableAll = () => {
  setParameterConfigs(prev => {
    const updated = { ...prev };
    Object.keys(updated).forEach(key => {
      updated[key] = {
        ...updated[key],
        optimize: true,
        range: updated[key].range || {
          min: updated[key].strategyDefaultValue * 0.5,
          max: updated[key].strategyDefaultValue * 2,
          step: typeof updated[key].strategyDefaultValue === 'number' &&
                Number.isInteger(updated[key].strategyDefaultValue) ? 1 : 0.1
        }
      };
    });
    return updated;
  });
};
```

**Disable All**:
```typescript
const handleDisableAll = () => {
  setParameterConfigs(prev => {
    const updated = { ...prev };
    Object.keys(updated).forEach(key => {
      updated[key] = {
        ...updated[key],
        optimize: false
      };
    });
    return updated;
  });
};
```

#### JSX Structure

```tsx
<div className="flex justify-between items-center mb-4">
  <h3 className="text-lg font-semibold text-gray-900">Parameters</h3>
  <div className="flex items-center gap-4">
    <div className="text-sm text-gray-600">
      {optimizationMethod === 'bayesian' ? (
        <span>Trials: <span className="font-bold text-blue-600">{totalCombinations}</span></span>
      ) : (
        <span>Combinations: <span className="font-bold text-blue-600">{totalCombinations}</span></span>
      )}
    </div>
    <div className="flex gap-2">
      <button
        type="button"
        onClick={handleEnableAll}
        disabled={allParamsOptimized}
        className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        全部开启
      </button>
      <button
        type="button"
        onClick={handleDisableAll}
        disabled={noParamsOptimized}
        className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        全部关闭
      </button>
    </div>
  </div>
</div>
```

### Data Flow

1. User clicks "Enable All" → `handleEnableAll()` invoked
2. Iterate through `parameterConfigs`, set all `optimize` to `true`
3. If parameter lacks `range`, auto-initialize with default range (0.5x-2x of strategy default)
4. Update `parameterConfigs` state
5. React re-renders:
   - All parameter switches turn on
   - Min/Max/Step inputs appear
   - Recalculate `totalCombinations`
   - "Enable All" button becomes disabled

### User Experience

- **Immediate response**: No confirmation dialog (non-destructive operation)
- **Visual feedback**: Button disabled state provides clear feedback
- **Flexibility**: Individual parameter switches still work
- **Non-disruptive**: Preserves existing parameter values

### Edge Cases & Error Handling

1. **No parameters**: Handled by existing logic (lines 703-707), toggle buttons won't render
2. **Single parameter**: Works normally, buttons are mutually exclusive
3. **Parameters with existing range**: Preserves existing range values
4. **Strategy switch**: useEffect (lines 136-151) resets `parameterConfigs`, button states auto-reset

**No API calls involved** - pure frontend state management, minimal risk.

## Implementation Plan

### File Modifications

- **File**: `frontend/components/OptimizationForm.tsx`
- **Location**: Lines 568-577 (Parameters header)
- **Changes**:
  1. Add `useMemo` for state calculation
  2. Add handler functions
  3. Modify JSX structure to include button group

### Steps

1. Add state calculation with `useMemo`
2. Implement `handleEnableAll` and `handleDisableAll` functions
3. Update JSX to render button group
4. Test scenarios: all enabled, all disabled, mixed state, single parameter

### Backward Compatibility

- ✅ Fully compatible, no breaking changes
- ✅ No API interface changes
- ✅ No impact on other components

## Testing Strategy

### Manual Testing Checklist

- [ ] All parameters disabled → click "Enable All" → all enabled, button disabled
- [ ] All parameters enabled → click "Disable All" → all disabled, button disabled
- [ ] Mixed state → both buttons enabled
- [ ] Single parameter → buttons work correctly
- [ ] Strategy switch → button states reset correctly
- [ ] Individual switches still work after batch operation

### Cross-browser Testing

- Chrome, Firefox, Safari, Edge

## Estimated Effort

- **Complexity**: Low (pure frontend state management)
- **Time Estimate**: 30 minutes
- **Risk Level**: Minimal (no backend changes)
- **User Value**: High (significant efficiency improvement)

## Alternatives Considered

1. **Simple Toggle**: Single button that alternates between all-on and all-off
   - Rejected: Less clear, harder to understand current state

2. **Checkbox-style**: Single checkbox for "optimize all parameters"
   - Rejected: Doesn't allow quick disable-all action

3. **Confirmation Dialog**: Show confirmation before batch operation
   - Rejected: Unnecessary friction for non-destructive operation

## Rationale for Smart State Design

The chosen approach (方案2) provides:
- **Best UX**: Clear visual feedback of current state
- **Prevents redundant operations**: Disabled buttons indicate no-op
- **Reasonable implementation**: Only requires state calculation logic
- **Modern UI pattern**: Aligns with "select all/deselect all" patterns

## References

- Current Implementation: `frontend/components/OptimizationForm.tsx` lines 566-700
- Toggle Switch Component: lines 27-45
- Parameter Config Interface: lines 11-20
