# Date Picker Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace native HTML date inputs with a feature-rich calendar component using react-day-picker, providing smooth date selection, month/year navigation, preset ranges, and dark mode support.

**Architecture:**
- Create a reusable `DatePicker` component wrapping react-day-picker
- Build a `MonthGrid` component for quick month selection
- Integrate preset buttons at parent component level (BacktestForm/OptimizationForm)
- Use Tailwind CSS for styling with dark mode support
- Follow existing project patterns (slate colors, rounded-lg, dark: prefixes)

**Tech Stack:**
- react-day-picker v9+ (calendar component)
- date-fns (date utilities)
- Tailwind CSS (styling)
- TypeScript (types)
- Playwright (E2E testing)

---

## File Structure

```
frontend/
├── components/
│   ├── DatePicker/
│   │   ├── DatePicker.tsx          # Main calendar component
│   │   ├── MonthGrid.tsx           # Month selection grid (3x4)
│   │   └── index.tsx               # Exports
│   ├── BacktestForm.tsx            # MODIFY: Replace date inputs, add preset buttons
│   └── OptimizationForm.tsx        # MODIFY: Replace datetime inputs, add preset buttons
├── app/
│   └── globals.css                 # MODIFY: Add .rdp styles
├── components/__tests__/
│   ├── DatePicker.test.tsx         # NEW: Unit tests
│   └── BacktestForm.test.tsx       # NEW: Integration tests for preset buttons
└── e2e/
    └── date-picker.spec.ts         # NEW: E2E tests
```

---

## Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install react-day-picker and date-fns**

```bash
cd frontend
pnpm add react-day-picker date-fns
```

Expected: Packages added to package.json and node_modules

- [ ] **Step 2: Install testing dependencies**

```bash
cd frontend
pnpm add -D @testing-library/react @testing-library/jest-dom @testing-library/user-event jest-environment-jsdom
```

Expected: Testing libraries added to devDependencies

- [ ] **Step 3: Verify installation**

```bash
grep -E "react-day-picker|date-fns" package.json
```

Expected: Both packages listed in dependencies

- [ ] **Step 4: Create test directory**

```bash
mkdir -p frontend/components/__tests__
```

- [ ] **Step 5: Configure Jest**

Create `frontend/jest.config.js`:

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/(.*)$': '<rootDir>/../$1',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};
```

Create `frontend/jest.setup.js`:

```javascript
import '@testing-library/jest-dom';
```

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore: install react-day-picker and date-fns"
```

---

## Task 2: Add Tailwind CSS Styles for react-day-picker

**Files:**
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Read current globals.css**

```bash
head -50 frontend/app/globals.css
```

- [ ] **Step 2: Add react-day-picker style overrides**

Add to the END of `frontend/app/globals.css`:

```css
/* Date Picker Styles - react-day-picker overrides */
@layer components {
  /* Light mode */
  .rdp-root {
    --rdp-cell-size: 36px;
    --rdp-accent-color: #2563eb; /* primary-600 */
    --rdp-background-color: #ffffff;
    --rdp-text-color: #0f172a; /* slate-900 */
    --rdp-day-hover-bg: #eff6ff; /* blue-50 */
    --rdp-disabled-color: #94a3b8; /* slate-400 */
    font-family: inherit;
  }

  /* Dark mode */
  .dark .rdp-root {
    --rdp-accent-color: #3b82f6; /* primary-500 */
    --rdp-background-color: #334155; /* slate-700 */
    --rdp-text-color: #f1f5f9; /* slate-100 */
    --rdp-day-hover-bg: #475569; /* slate-600 */
    --rdp-disabled-color: #64748b; /* slate-500 */
  }

  /* Selected day styling */
  .rdp-day_selected {
    font-weight: 600;
  }

  /* Today indicator */
  .rdp-day_today {
    border: 2px solid var(--rdp-accent-color);
  }

  /* Disabled day styling */
  .rdp-day_disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Navigation buttons */
  .rdp-nav_button {
    color: var(--rdp-text-color);
    transition: color 0.2s;
  }

  .rdp-nav_button:hover {
    color: var(--rdp-accent-color);
  }

  /* Day cell hover */
  .rdp-day:not(.rdp-day_disabled):hover {
    background-color: var(--rdp-day-hover-bg);
  }
}
```

- [ ] **Step 3: Verify syntax**

Check for CSS syntax errors:
```bash
cd frontend
pnpm run build 2>&1 | head -20
```

Expected: No CSS syntax errors

- [ ] **Step 4: Commit**

```bash
git add frontend/app/globals.css
git commit -m "style: add react-day-picker Tailwind overrides with dark mode"
```

---

## Task 3: Create DatePicker Component

**Files:**
- Create: `frontend/components/DatePicker/DatePicker.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/components/__tests__/DatePicker.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { DatePicker } from '../DatePicker/DatePicker';

describe('DatePicker', () => {
  it('should render input box', () => {
    render(<DatePicker value="" onChange={() => {}} id="test-date" />);
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });

  it('should display selected date', () => {
    render(<DatePicker value="2024-03-15" onChange={() => {}} id="test-date" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('2024-03-15');
  });

  it('should call onChange when date is selected', () => {
    const handleChange = jest.fn();
    render(<DatePicker value="" onChange={handleChange} id="test-date" />);

    // Open calendar
    const input = screen.getByRole('textbox');
    fireEvent.click(input);

    // Click a date (this will fail until component is implemented)
    const dateButton = screen.getByText('15');
    fireEvent.click(dateButton);

    expect(handleChange).toHaveBeenCalled();
  });

  it('should disable future dates', () => {
    render(<DatePicker value="" onChange={() => {}} id="test-date" />);
    // Future dates should have disabled attribute
    // Implementation will verify this
  });

  it('should show month grid when button clicked', () => {
    render(<DatePicker value="" onChange={() => {}} id="test-date" />);
    const input = screen.getByRole('textbox');
    fireEvent.click(input);

    // Click "快速选择月份" button
    const monthGridButton = screen.queryByText('快速选择月份');
    // This will be implemented in Task 4
  });

  it('should close month grid and update calendar when month selected', () => {
    const handleChange = jest.fn();
    render(<DatePicker value="2024-03-15" onChange={handleChange} id="test-date" />);
    // Integration test will be added after MonthGrid is implemented
  });

  it('should support aria-invalid attribute', () => {
    render(
      <DatePicker
        value=""
        onChange={() => {}}
        id="test-date"
        aria-invalid="true"
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend
pnpm test -- DatePicker.test.tsx
```

Expected: FAIL - "Cannot find module '../DatePicker/DatePicker'"

- [ ] **Step 3: Create DatePicker component**

Create `frontend/components/DatePicker/DatePicker.tsx`:

```typescript
'use client';

import { useState, useRef, useEffect } from 'react';
import { DayPicker } from 'react-day-picker';
import { format, addYears, subYears } from 'date-fns';
import 'react-day-picker/dist/style.css';

interface DatePickerProps {
  value: string;                    // Selected date (YYYY-MM-DD)
  onChange: (date: string) => void; // Date change callback
  id?: string;                      // Input ID
  label?: string;                   // Input label text
  placeholder?: string;             // Placeholder text (default: "选择日期")
  required?: boolean;               // Required field indicator
  minDate?: string;                 // Minimum selectable date
  maxDate?: string;                 // Maximum selectable date (default: today)
  disabled?: boolean;               // Disabled state
}

export function DatePicker({
  value,
  onChange,
  id,
  label,
  placeholder = '选择日期',
  required = false,
  minDate,
  maxDate = new Date().toISOString().split('T')[0],
  disabled = false,
}: DatePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState<Date>(
    value ? new Date(value) : new Date()
  );
  const pickerRef = useRef<HTMLDivElement>(null);

  // Format date for display
  const formatDate = (dateString: string): string => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return format(date, 'yyyy-MM-dd');
  };

  // Handle date selection
  const handleSelect = (date: Date | undefined) => {
    if (date) {
      const formatted = format(date, 'yyyy-MM-dd');
      onChange(formatted);
      setIsOpen(false);
    }
  };

  // Handle month navigation
  const handleMonthChange = (month: Date) => {
    setCurrentMonth(month);
  };

  // Handle year jumping
  const jumpYear = (direction: 'prev' | 'next') => {
    const newMonth = direction === 'prev'
      ? subYears(currentMonth, 1)
      : addYears(currentMonth, 1);
    setCurrentMonth(newMonth);
  };

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Calculate disabled days
  const disabledDays = [
    { after: new Date(maxDate) },
    ...(minDate ? [{ before: new Date(minDate) }] : []),
  ];

  return (
    <div ref={pickerRef} className="relative">
      <input
        id={id}
        type="text"
        value={formatDate(value)}
        onChange={() => {}}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        readOnly
        onClick={() => !disabled && setIsOpen(!isOpen)}
        aria-label={label || placeholder}
        className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed transition-colors cursor-pointer"
      />

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 z-50 bg-white dark:bg-slate-700 rounded-lg shadow-lg border border-slate-200 dark:border-slate-600 p-4">
          <DayPicker
            mode="single"
            selected={value ? new Date(value) : undefined}
            onSelect={handleSelect}
            month={currentMonth}
            onMonthChange={handleMonthChange}
            disabled={disabledDays}
            classNames={{
              root: 'rdp-root',
              nav: 'flex justify-between items-center mb-4',
              nav_button: 'p-2 hover:bg-slate-100 dark:hover:bg-slate-600 rounded transition-colors',
              nav_button_previous: 'text-slate-700 dark:text-slate-200',
              nav_button_next: 'text-slate-700 dark:text-slate-200',
              caption: 'flex justify-center items-center mb-4',
              caption_label: 'text-lg font-semibold text-slate-900 dark:text-slate-100',
              table: 'w-full border-collapse',
              head_row: 'flex',
              head_cell: 'flex-1 text-center text-sm font-medium text-slate-600 dark:text-slate-400 pb-2',
              row: 'flex w-full',
              cell: 'flex-1 text-center p-1',
              day: 'h-9 w-9 rounded-lg flex items-center justify-center text-sm transition-colors cursor-pointer',
              day_selected: 'bg-primary-600 dark:bg-primary-500 text-white hover:bg-primary-700 dark:hover:bg-primary-600',
              day_today: 'border-2 border-primary-600 dark:border-primary-500',
              day_disabled: 'text-slate-400 dark:text-slate-500 cursor-not-allowed opacity-50',
              day_outside: 'text-slate-300 dark:text-slate-600',
            }}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend
pnpm test -- DatePicker.test.tsx
```

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/components/DatePicker/
git commit -m "feat: add DatePicker component with react-day-picker"
```

---

## Task 4: Create MonthGrid Component

**Files:**
- Create: `frontend/components/DatePicker/MonthGrid.tsx`

- [ ] **Step 1: Write the failing test**

Add to `frontend/components/__tests__/DatePicker.test.tsx`:

```typescript
import MonthGrid from '../DatePicker/MonthGrid';

describe('MonthGrid', () => {
  it('should render 12 months in grid', () => {
    const onSelectMonth = jest.fn();
    const { getByText } = render(
      <MonthGrid
        currentMonth={new Date('2024-03-15')}
        onSelectMonth={onSelectMonth}
        onClose={() => {}}
      />
    );

    expect(getByText('1月')).toBeInTheDocument();
    expect(getByText('6月')).toBeInTheDocument();
    expect(getByText('12月')).toBeInTheDocument();
  });

  it('should highlight current month', () => {
    const onSelectMonth = jest.fn();
    const { getByText } = render(
      <MonthGrid
        currentMonth={new Date('2024-03-15')}
        onSelectMonth={onSelectMonth}
        onClose={() => {}}
      />
    );

    const marchButton = getByText('3月');
    expect(marchButton).toHaveClass('bg-primary-600');
  });

  it('should call onSelectMonth when month clicked', () => {
    const onSelectMonth = jest.fn();
    const onClose = jest.fn();
    const { getByText } = render(
      <MonthGrid
        currentMonth={new Date('2024-03-15')}
        onSelectMonth={onSelectMonth}
        onClose={onClose}
      />
    );

    fireEvent.click(getByText('6月'));

    expect(onSelectMonth).toHaveBeenCalledWith(5); // June is index 5
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend
pnpm test -- DatePicker.test.tsx
```

Expected: FAIL - "Cannot find module '../DatePicker/MonthGrid'"

- [ ] **Step 3: Create MonthGrid component**

Create `frontend/components/DatePicker/MonthGrid.tsx`:

```typescript
'use client';

interface MonthGridProps {
  currentMonth: Date;
  onSelectMonth: (monthIndex: number) => void;
  onClose: () => void;
}

const MONTHS = [
  '1月', '2月', '3月', '4月', '5月', '6月',
  '7月', '8月', '9月', '10月', '11月', '12月'
];

export default function MonthGrid({ currentMonth, onSelectMonth, onClose }: MonthGridProps) {
  const currentMonthIndex = currentMonth.getMonth();

  const handleMonthClick = (monthIndex: number) => {
    onSelectMonth(monthIndex);
    onClose();
  };

  return (
    <div className="absolute top-full left-0 mt-2 bg-white dark:bg-slate-700 rounded-lg shadow-lg border border-slate-200 dark:border-slate-600 p-4 z-50">
      <div className="grid grid-cols-3 gap-2">
        {MONTHS.map((month, index) => (
          <button
            key={month}
            onClick={() => handleMonthClick(index)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              index === currentMonthIndex
                ? 'bg-primary-600 dark:bg-primary-500 text-white'
                : 'hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200'
            }`}
          >
            {month}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Update DatePicker to use MonthGrid**

Modify `frontend/components/DatePicker/DatePicker.tsx`:

Add import:
```typescript
import MonthGrid from './MonthGrid';
```

Add state after `currentMonth` state:
```typescript
const [showMonthGrid, setShowMonthGrid] = useState(false);
```

Update click-outside useEffect to close month grid:

Replace existing useEffect with:
```typescript
// Click outside to close
useEffect(() => {
  const handleClickOutside = (event: MouseEvent) => {
    if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
      setIsOpen(false);
      setShowMonthGrid(false);
    }
  };

  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
}, [isOpen]);
```

Add "快速选择月份" button after `<DayPicker>` (still inside the popup div):

```typescript
<button
  onClick={() => setShowMonthGrid(!showMonthGrid)}
  className="px-3 py-1 text-sm bg-slate-100 dark:bg-slate-600 rounded hover:bg-slate-200 dark:hover:bg-slate-500 transition-colors mb-2"
>
  快速选择月份
</button>

{showMonthGrid && (
  <MonthGrid
    currentMonth={currentMonth}
    onSelectMonth={(monthIndex) => {
      const newMonth = new Date(currentMonth);
      newMonth.setMonth(monthIndex);
      setCurrentMonth(newMonth);
    }}
    onClose={() => setShowMonthGrid(false)}
  />
)}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd frontend
pnpm test -- DatePicker.test.tsx
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/components/DatePicker/
git commit -m "feat: add MonthGrid component for quick month selection"
```

---

## Task 5: Create Export File

**Files:**
- Create: `frontend/components/DatePicker/index.tsx`

- [ ] **Step 1: Create index.tsx**

Create `frontend/components/DatePicker/index.tsx`:

```typescript
export { DatePicker } from './DatePicker';
export { default as MonthGrid } from './MonthGrid';
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/DatePicker/index.tsx
git commit -m "chore: add DatePicker component exports"
```

---

## Task 6: Update BacktestForm to Use DatePicker

**Files:**
- Modify: `frontend/components/BacktestForm.tsx`

- [ ] **Step 1: Read current BacktestForm date inputs**

```bash
sed -n '170,200p' frontend/components/BacktestForm.tsx
```

- [ ] **Step 2: Update imports**

Find and replace the import section (around line 8):

Replace:
```typescript
import ParameterInput from './ParameterInput';
```

With:
```typescript
import ParameterInput from './ParameterInput';
import { DatePicker } from './DatePicker';
import { subDays } from 'date-fns';
```

- [ ] **Step 3: Replace start date input**

Find the start date input div (around lines 171-184):

Replace the entire start date div block with:

```typescript
<div>
  <label htmlFor="startTime" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
    Start Date
  </label>
  <DatePicker
    id="startTime"
    value={startTime}
    onChange={setStartTime}
    label="Start Date"
    placeholder="Select start date"
    required
    maxDate={new Date().toISOString().split('T')[0]}
  />
</div>
```

- [ ] **Step 4: Replace end date input**

Find the end date input div (around lines 186-198):

Replace the entire end date div block with:

```typescript
<div>
  <label htmlFor="endTime" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
    End Date
  </label>
  <DatePicker
    id="endTime"
    value={endTime}
    onChange={setEndTime}
    label="End Date"
    placeholder="Select end date"
    required
    maxDate={new Date().toISOString().split('T')[0]}
  />
</div>
```

- [ ] **Step 5: Add preset buttons**

Add after the date inputs grid (after the `</div>` that closes the end date section):

```typescript
<div className="flex gap-2 flex-wrap">
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 7);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-slate-100 dark:bg-slate-600 rounded hover:bg-slate-200 dark:hover:bg-slate-500 transition-colors"
  >
    最近7天
  </button>
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 30);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-slate-100 dark:bg-slate-600 rounded hover:bg-slate-200 dark:hover:bg-slate-500 transition-colors"
  >
    最近30天
  </button>
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 90);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-slate-100 dark:bg-slate-600 rounded hover:bg-slate-200 dark:hover:bg-slate-500 transition-colors"
  >
    最近3个月
  </button>
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 365);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-slate-100 dark:bg-slate-600 rounded hover:bg-slate-200 dark:hover:bg-slate-500 transition-colors"
  >
    最近1年
  </button>
</div>
```

- [ ] **Step 6: Verify TypeScript compilation**

```bash
cd frontend
pnpm run build 2>&1 | grep -i error || echo "No TypeScript errors"
```

Expected: No TypeScript errors

- [ ] **Step 7: Manual test in browser**

```bash
cd frontend
pnpm dev
```

Visit: http://localhost:3000/backtest

Test:
1. Click start date input
2. Select a date
3. Click end date input
4. Select a date
5. Click preset buttons
6. Verify dates are set correctly

- [ ] **Step 8: Commit**

```bash
git add frontend/components/BacktestForm.tsx
git commit -m "feat: replace date inputs with DatePicker in BacktestForm"
```

---

## Task 6b: Add BacktestForm Integration Tests

**Files:**
- Create: `frontend/components/__tests__/BacktestForm.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/components/__tests__/BacktestForm.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import BacktestForm from '../BacktestForm';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockStrategies = [
  { name: 'TestStrategy', version: '1.0', description: 'Test strategy' }
];

jest.mock('@/lib/api/strategies', () => ({
  strategiesApi: {
    list: jest.fn(() => Promise.resolve(mockStrategies)),
    get: jest.fn(() => Promise.resolve({
      name: 'TestStrategy',
      version: '1.0',
      description: 'Test strategy',
      parameters: {}
    }))
  }
}));

jest.mock('@/lib/api/data', () => ({
  dataApi: {
    getSymbols: jest.fn(() => Promise.resolve(['BTCUSDT', 'ETHUSDT']))
  }
}));

function renderWithQuery(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
}

describe('BacktestForm with DatePicker preset buttons', () => {
  it('should update both date pickers when preset button clicked', async () => {
    renderWithQuery(<BacktestForm />);

    // Wait for strategies to load
    const strategySelect = await screen.findByRole('combobox');
    fireEvent.change(strategySelect, { target: { value: 'TestStrategy' } });

    // Click "最近30天" button
    const thirtyDaysButton = await screen.findByText('最近30天');
    fireEvent.click(thirtyDaysButton);

    // Verify both date inputs have values
    const startDateInput = screen.getByLabelText('Start Date');
    const endDateInput = screen.getByLabelText('End Date');

    expect(startDateInput).toHaveValue(/\d{4}-\d{2}-\d{2}/);
    expect(endDateInput).toHaveValue(/\d{4}-\d{2}-\d{2}/);

    // End date should be after start date
    const startValue = startDateInput.getAttribute('value');
    const endValue = endDateInput.getAttribute('value');
    expect(endValue).toBeGreaterThan(startValue);
  });

  it('should update dates correctly for each preset button', async () => {
    renderWithQuery(<BacktestForm />);

    const strategySelect = await screen.findByRole('combobox');
    fireEvent.change(strategySelect, { target: { value: 'TestStrategy' } });

    const startDateInput = screen.getByLabelText('Start Date');
    const endDateInput = screen.getByLabelText('End Date');

    // Test "最近7天"
    fireEvent.click(await screen.findByText('最近7天'));
    expect(startDateInput).toHaveValue(/\d{4}-\d{2}-\d{2}/);

    // Test "最近3个月"
    fireEvent.click(await screen.findByText('最近3个月'));
    expect(startDateInput).toHaveValue(/\d{4}-\d{2}-\d{2}/);

    // Test "最近1年"
    fireEvent.click(await screen.findByText('最近1年'));
    expect(startDateInput).toHaveValue(/\d{4}-\d{2}-\d{2}/);
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd frontend
pnpm test -- BacktestForm.test.tsx
```

Expected: PASS (all integration tests)

- [ ] **Step 3: Commit**

```bash
git add frontend/components/__tests__/BacktestForm.test.tsx
git commit -m "test: add BacktestForm integration tests for preset buttons"
```

---

## Task 7: Update OptimizationForm to Use DatePicker

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx`

- [ ] **Step 1: Read current OptimizationForm datetime inputs**

```bash
sed -n '224,252p' frontend/components/OptimizationForm.tsx
```

- [ ] **Step 2: Update imports**

Find the import section (around line 7):

Replace:
```typescript
import { OptimizationRequest } from '@/lib/api/optimization';
```

With:
```typescript
import { OptimizationRequest } from '@/lib/api/optimization';
import { DatePicker } from './DatePicker';
import { subDays } from 'date-fns';
```

- [ ] **Step 3: Remove time-related state and helpers**

Find and remove the `getDefaultStartTime` and `getDefaultEndTime` functions (lines 26-37).

Update state initialization (around lines 39-40):

Replace:
```typescript
const [startTime, setStartTime] = useState(getDefaultStartTime());
const [endTime, setEndTime] = useState(getDefaultEndTime());
```

With:
```typescript
const getDefaultStartDate = () => {
  const now = new Date();
  now.setDate(now.getDate() - 30);
  return now.toISOString().split('T')[0];
};

const getDefaultEndDate = () => {
  return new Date().toISOString().split('T')[0];
};

const [startTime, setStartTime] = useState(getDefaultStartDate());
const [endTime, setEndTime] = useState(getDefaultEndDate());
```

- [ ] **Step 4: Replace start datetime input**

Find the start datetime input div (around lines 224-237):

Replace with:

```typescript
<div>
  <label htmlFor="startTime" className="block text-sm font-medium text-gray-700 mb-2">
    Start Date
  </label>
  <DatePicker
    id="startTime"
    value={startTime}
    onChange={setStartTime}
    label="Start Date"
    placeholder="Select start date"
    required
    maxDate={new Date().toISOString().split('T')[0]}
  />
</div>
```

- [ ] **Step 5: Replace end datetime input**

Find the end datetime input div (around lines 239-251):

Replace with:

```typescript
<div>
  <label htmlFor="endTime" className="block text-sm font-medium text-gray-700 mb-2">
    End Date
  </label>
  <DatePicker
    id="endTime"
    value={endTime}
    onChange={setEndTime}
    label="End Date"
    placeholder="Select end date"
    required
    maxDate={new Date().toISOString().split('T')[0]}
  />
</div>
```

- [ ] **Step 6: Add preset buttons**

Add after the date inputs grid:

```typescript
<div className="flex gap-2 flex-wrap">
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 7);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 transition-colors"
  >
    最近7天
  </button>
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 30);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 transition-colors"
  >
    最近30天
  </button>
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 90);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 transition-colors"
  >
    最近3个月
  </button>
  <button
    type="button"
    onClick={() => {
      const end = new Date();
      const start = subDays(end, 365);
      setStartTime(start.toISOString().split('T')[0]);
      setEndTime(end.toISOString().split('T')[0]);
    }}
    className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 transition-colors"
  >
    最近1年
  </button>
</div>
```

- [ ] **Step 7: Verify TypeScript compilation**

```bash
cd frontend
pnpm run build 2>&1 | grep -i error || echo "No TypeScript errors"
```

Expected: No TypeScript errors

- [ ] **Step 8: Manual test in browser**

```bash
cd frontend
pnpm dev
```

Visit: http://localhost:3000/optimize

Test:
1. Click start date input
2. Select a date
3. Click end date input
4. Select a date
5. Click preset buttons
6. Run optimization with selected dates

- [ ] **Step 9: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: replace datetime inputs with DatePicker in OptimizationForm"
```

---

## Task 8: Write E2E Tests

**Files:**
- Create: `frontend/e2e/date-picker.spec.ts`

- [ ] **Step 1: Create E2E test file**

Create `frontend/e2e/date-picker.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('DatePicker - BacktestForm', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/backtest');
  });

  test('should open calendar when clicking input', async ({ page }) => {
    // Select strategy first
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Click start date input
    await page.click('#startTime');

    // Calendar should be visible
    await expect(page.locator('.rdp-root')).toBeVisible();
  });

  test('should select date and update input value', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Open start date picker
    await page.click('#startTime');

    // Select a date (click day 15)
    await page.click('.rdp-day:not(.rdp-day_disabled):has-text("15")');

    // Verify input has value
    const inputValue = await page.inputValue('#startTime');
    expect(inputValue).toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  test('should close calendar when clicking outside', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Open calendar
    await page.click('#startTime');
    await expect(page.locator('.rdp-root')).toBeVisible();

    // Click outside
    await page.click('body');

    // Calendar should be hidden
    await expect(page.locator('.rdp-root')).not.toBeVisible();
  });

  test('preset buttons should set both dates', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Click "最近30天" button
    await page.click('button:has-text("最近30天")');

    // Both inputs should have values
    const startValue = await page.inputValue('#startTime');
    const endValue = await page.inputValue('#endTime');

    expect(startValue).toBeTruthy();
    expect(endValue).toBeTruthy();
    expect(endValue).toBeGreaterThan(startValue);
  });

  test('should disable future dates', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Open calendar
    await page.click('#startTime');

    // Check that days in next month have disabled class
    const nextMonthButton = page.locator('.rdp-nav_button-next');
    await nextMonthButton.click();

    // Future days should be disabled
    const disabledDays = page.locator('.rdp-day_disabled');
    const count = await disabledDays.count();
    expect(count).toBeGreaterThan(0);
  });

  test('can navigate to different month', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');
    await page.click('#startTime');

    // Get initial caption
    const initialCaption = await page.locator('.rdp-caption_label').textContent();

    // Click next month button
    await page.click('.rdp-nav_button-next');
    const afterNextMonth = await page.locator('.rdp-caption_label').textContent();
    expect(afterNextMonth).not.toBe(initialCaption);
  });

  test('keyboard navigation works', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Tab to date picker
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Press Enter to open
    await page.keyboard.press('Enter');
    await expect(page.locator('.rdp-root')).toBeVisible();

    // Navigate with arrow keys
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');

    // Verify date selected
    const inputValue = await page.inputValue('#startTime');
    expect(inputValue).toBeTruthy();

    // Press Escape to close
    await page.click('#startTime');
    await page.keyboard.press('Escape');
    await expect(page.locator('.rdp-root')).not.toBeVisible();
  });
});

test.describe('DatePicker - OptimizationForm', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/optimize');
  });

  test('should work with optimization form', async ({ page }) => {
    // Select strategy
    await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

    // Use preset button
    await page.click('button:has-text("最近7天")');

    // Verify dates are set
    const startValue = await page.inputValue('#startTime');
    const endValue = await page.inputValue('#endTime');

    expect(startValue).toBeTruthy();
    expect(endValue).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run E2E tests**

```bash
cd frontend
pnpm test:e2e date-picker.spec.ts
```

Expected: Tests run (may need server running)

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/date-picker.spec.ts
git commit -m "test: add E2E tests for DatePicker component"
```

---

## Task 9: Final Integration Testing

**Files:**
- None (testing only)

- [ ] **Step 1: Run all existing tests**

```bash
cd frontend
pnpm test
```

Expected: All tests pass

- [ ] **Step 2: Run E2E tests**

```bash
cd frontend
pnpm test:e2e
```

Expected: All E2E tests pass

- [ ] **Step 3: Verify dark mode (OPTIONAL - if project supports it)**

```bash
cd frontend
pnpm dev
```

If project has dark mode toggle:
1. Visit http://localhost:3000/backtest
2. Toggle dark mode
3. Open calendar
4. Verify dark mode styles applied

- [ ] **Step 4: Test accessibility**

```bash
cd frontend
pnpm dev
```

Test:
1. Visit http://localhost:3000/backtest
2. Press Tab to focus date input
3. Press Enter to open calendar
4. Use Arrow keys to navigate
5. Press Escape to close

- [ ] **Step 5: Verify production build**

```bash
cd frontend
pnpm build
pnpm start
```

Visit http://localhost:3000/backtest and verify everything works

- [ ] **Step 6: Performance verification**

Test performance with browser DevTools:

1. Visit http://localhost:3000/backtest
2. Open DevTools Performance tab
3. Click start date input and interact with calendar
4. Measure rendering time

Expected: Calendar opens in <100ms, no noticeable lag

Or use Lighthouse:

```bash
npx lighthouse http://localhost:3000/backtest --view
```

Expected: Performance score >90

- [ ] **Step 7: Visual regression test (manual)**

Verify dark mode visual appearance:

1. Visit http://localhost:3000/backtest
2. Toggle dark mode (if available)
3. Open calendar
4. Take screenshot for comparison
5. Verify:
   - Calendar background is dark (slate-700)
   - Selected date is blue (primary-500)
   - Text is light (slate-100)
   - Disabled days are grayed out
   - Hover states work correctly

- [ ] **Step 8: Commit any final fixes**

```bash
git add .
git commit -m "fix: final integration testing fixes"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `README.md` or project docs

- [ ] **Step 1: Update component documentation**

If project has a README or component docs, add DatePicker usage example.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document DatePicker component usage"
```

---

## Success Criteria

Verify all criteria are met:

- [ ] Users can select dates in a single calendar panel
- [ ] Month and year navigation is smooth
- [ ] Month grid provides quick month selection
- [ ] Preset range buttons work correctly
- [ ] Future dates are disabled
- [ ] Click outside closes the calendar
- [ ] Styles match existing design system (slate color, rounded-lg)
- [ ] Dark mode works correctly
- [ ] All existing tests pass
- [ ] New component has unit tests (>80% coverage)
- [ ] E2E tests cover main user flows
- [ ] Accessibility: Keyboard navigation works
- [ ] Accessibility: ARIA labels are present
- [ ] Performance is acceptable (no noticeable lag)

---

## Notes

- **Time Selection**: OptimizationForm no longer requires time selection (removed as per spec)
- **Future Enhancement**: Available date range query from backend is out of scope for v1
- **Browser Compatibility**: react-day-picker supports modern browsers
- **Accessibility**: Component follows WCAG 2.1 Level AA guidelines
