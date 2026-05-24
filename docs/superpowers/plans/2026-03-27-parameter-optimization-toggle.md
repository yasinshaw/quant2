# Parameter Optimization Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-click toggle buttons to enable/disable all parameter optimization switches simultaneously in the OptimizationForm component

**Architecture:** Pure frontend state management enhancement - add two handler functions and state calculation using React hooks, modify JSX to render button group in Parameters section header

**Tech Stack:** React hooks (useState, useMemo), TypeScript, Tailwind CSS

---

## File Structure

**Single file modification:**
- `frontend/components/OptimizationForm.tsx` - Add state calculation, handler functions, and JSX button group

No new files, no test files (manual testing only for this UI enhancement).

---

### Task 1: Add State Calculation with useMemo

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (insert after line 180, after `totalCombinations` useMemo)

- [ ] **Step 1: Add useMemo for allParamsOptimized state**

Find line 180 (after `totalCombinations` useMemo), insert:

```typescript
// Calculate optimization states for toggle buttons
const allParamsOptimized = useMemo(() => {
  return Object.values(parameterConfigs).every(config => config.optimize);
}, [parameterConfigs]);

const noParamsOptimized = useMemo(() => {
  return Object.values(parameterConfigs).every(config => !config.optimize);
}, [parameterConfigs]);
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: add state calculation for parameter toggle buttons"
```

---

### Task 2: Add handleEnableAll Handler Function

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (insert after Task 1 additions, before `handleSubmit` function)

- [ ] **Step 1: Add handleEnableAll function**

Insert after the useMemo blocks (around line 186):

```typescript
// Enable optimization for all parameters
const handleEnableAll = () => {
  setParameterConfigs(prev => {
    const updated = { ...prev };
    Object.keys(updated).forEach(key => {
      updated[key] = {
        ...updated[key],
        optimize: true,
        // Initialize range if not exists
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

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: add handleEnableAll function for batch parameter optimization"
```

---

### Task 3: Add handleDisableAll Handler Function

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (insert after `handleEnableAll` function)

- [ ] **Step 1: Add handleDisableAll function**

Insert immediately after `handleEnableAll`:

```typescript
// Disable optimization for all parameters
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

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: add handleDisableAll function for batch parameter optimization"
```

---

### Task 4: Modify JSX to Add Button Group

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (replace lines 568-577)

- [ ] **Step 1: Replace Parameters header JSX**

Find the existing Parameters header (around line 568-577):
```tsx
<div className="flex justify-between items-center mb-4">
  <h3 className="text-lg font-semibold text-gray-900">Parameters</h3>
  <div className="text-sm text-gray-600">
    {optimizationMethod === 'bayesian' ? (
      <span>Trials: <span className="font-bold text-blue-600">{totalCombinations}</span></span>
    ) : (
      <span>Combinations: <span className="font-bold text-blue-600">{totalCombinations}</span></span>
    )}
  </div>
</div>
```

Replace with:
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

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: add toggle buttons to Parameters section header"
```

---

### Task 5: Manual Testing

**Files:**
- None (browser testing)

- [ ] **Step 1: Start frontend dev server**

Run: `cd frontend && pnpm dev`
Expected: Server starts at http://localhost:3002

- [ ] **Step 2: Open optimization page**

Browser: Navigate to http://localhost:3002/optimize
Expected: Optimization form loads

- [ ] **Step 3: Select a strategy with multiple parameters**

Action: Choose any strategy from dropdown (e.g., DualMovingAverage)
Expected: Parameters section appears with individual toggle switches

- [ ] **Step 4: Test "Enable All" button**

Action: Click "全部开启" button
Expected:
- All parameter switches turn ON
- Min/Max/Step inputs appear for all parameters
- "全部开启" button becomes disabled
- Combinations count updates

- [ ] **Step 5: Test "Disable All" button**

Action: Click "全部关闭" button
Expected:
- All parameter switches turn OFF
- Fixed value inputs appear for all parameters
- "全部关闭" button becomes disabled
- "全部开启" button becomes enabled

- [ ] **Step 6: Test mixed state**

Action: Manually toggle one parameter ON
Expected:
- Both "全部开启" and "全部关闭" buttons are enabled

- [ ] **Step 7: Test individual switches still work**

Action: Click individual parameter switches after batch operation
Expected:
- Individual switches still work independently
- Button states update correctly

- [ ] **Step 8: Test strategy switch**

Action: Change strategy selection
Expected:
- Button states reset correctly
- All parameters default to disabled

- [ ] **Step 9: Test visual feedback**

Action: Hover over buttons, check disabled state styling
Expected:
- Hover effect on enabled buttons
- Disabled buttons show reduced opacity

---

### Task 6: Cross-browser Testing

- [ ] **Step 1: Test in Chrome**

Browser: Chrome latest version
Expected: All functionality works as expected

- [ ] **Step 2: Test in Firefox**

Browser: Firefox latest version
Expected: All functionality works as expected

- [ ] **Step 3: Test in Safari**

Browser: Safari (macOS)
Expected: All functionality works as expected

- [ ] **Step 4: Test in Edge**

Browser: Edge latest version
Expected: All functionality works as expected

---

### Task 7: Final Verification and Cleanup

- [ ] **Step 1: Check for console errors**

Action: Open browser DevTools Console during testing
Expected: No errors or warnings

- [ ] **Step 2: Verify responsive design**

Action: Resize browser window to mobile size
Expected: Buttons remain visible and usable

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat: complete parameter optimization toggle buttons

- Add smart state calculation for toggle buttons
- Add handleEnableAll and handleDisableAll functions
- Add button group to Parameters section header
- All manual testing scenarios passed
- Cross-browser testing completed"
```

---

## Success Criteria

✅ Users can enable all parameters with one click
✅ Users can disable all parameters with one click
✅ Button states reflect current parameter configuration
✅ Individual parameter switches still work independently
✅ No TypeScript errors
✅ No console errors in browser
✅ Works across Chrome, Firefox, Safari, Edge
✅ Responsive design maintained

---

## Notes

- **No backend changes**: This is purely frontend state management
- **No API calls**: All operations are local React state updates
- **No breaking changes**: Fully backward compatible
- **Performance**: useMemo ensures efficient state calculation
- **Accessibility**: Buttons include proper disabled states and labels

---

## References

- Design Spec: `docs/superpowers/specs/2026-03-27-parameter-optimization-toggle-design.md`
- Component: `frontend/components/OptimizationForm.tsx`
- Parameter Config Interface: lines 11-20
- Existing Toggle Switch Component: lines 27-45
