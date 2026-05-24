# Date Picker Redesign Design Spec

**Date:** 2025-03-25
**Author:** Claude Code
**Status:** Draft

## Overview

优化回测和参数优化页面的日期选择器体验，从原生的 HTML5 `date` 和 `datetime-local` 输入框升级为功能丰富的日历组件，提供更流畅的用户体验。

## Current State

- **BacktestForm**: 使用 `<input type="date">`，只能选择日期
- **OptimizationForm**: 使用 `<input type="datetime-local">`，可选择日期和时间
- 问题：需要在浏览器原生的两个弹窗中选择月份和日期，体验不流畅

## Goals

1. 提供单个日历面板的日期选择体验
2. 支持快速月份切换和年份跳转
3. 提供预设日期范围快捷选项
4. 自动禁用无效日期（未来日期、数据不可用日期）
5. 保持与现有设计系统一致

## Solution

使用 [react-day-picker](https://daypicker.dev/) 作为核心日历组件库，结合自定义的预设范围按钮和月份快速选择功能。

### Component Architecture

```
DatePicker/
├── DatePicker.tsx          # 主组件，包装 react-day-picker
├── PresetButtons.tsx       # 预设日期范围快捷按钮（父组件级别）
├── MonthGrid.tsx           # 月份快速选择网格组件
└── index.tsx               # 导出文件
```

### Styling Approach

**使用 Tailwind CSS（与项目保持一致）**
- 不使用 CSS Modules（项目未采用）
- 通过 Tailwind 的 `@layer` 指令覆盖 react-day-picker 样式
- 统一使用 `slate` 色系（与 BacktestForm 保持一致）
- 统一使用 `rounded-lg`（与 BacktestForm 保持一致）
- 完整支持暗黑模式（`dark:` 前缀）

### Component Responsibilities

#### DatePicker (Main Component)

- 封装 react-day-picker 的 `DayPicker` 组件
- 处理日历显示/隐藏逻辑
- 管理选中状态和当前显示月份
- 支持月份快速切换（内置导航）
- 支持年份跳转（双箭头导航）
- 集成月份网格快速选择器
- 接收 `disabledDays` prop 来禁用无效日期

#### PresetButtons（父组件级别）

- 在 BacktestForm/OptimizationForm 中实现（不在 DatePicker 内部）
- 管理两个 DatePicker 实例（开始和结束日期）
- 渲染预设范围按钮："最近7天"、"最近30天"、"最近3个月"、"最近1年"
- 点击后同时更新两个 DatePicker 的值

#### MonthGrid

- 自定义组件，提供 12 月份的 3x4 网格选择
- 作为弹出层显示在日历面板中
- 点击月份后更新日历显示的月份并关闭网格

## UI/UX Design

### Input Box

- 保持与现有表单输入框一致的样式（使用 BacktestForm 样式标准）
  - `border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2`
  - `bg-white dark:bg-slate-700`
  - `text-slate-900 dark:text-slate-100`
  - `focus:ring-2 focus:ring-blue-500`
- 添加日历图标（右侧）
- 点击输入框时显示日历弹窗
- 完整支持暗黑模式

### Calendar Popup Layout

```
┌─────────────────────────────┐
│  ◀◀  ◀  2024年3月  ▶  ▶▶   │  ← 月份导航（双箭头跳转年份）
│      [快速选择月份]          │  ← 月份网格触发按钮
├─────────────────────────────┤
│  预设: [7天] [30天] [3月] [1年] │  ← 快捷按钮
├─────────────────────────────┤
│  日  一  二  三  四  五  六  │
│                      1   2  │
│  3   4   5   6   7   8   9  │  ← 日历网格
│  10  11  12  13  14  15  16 │
│  17  18  19  20  21  22  23 │
│  24  25  26  27  28  29  30 │
│  31                         │
└─────────────────────────────┘
```

### Date States

**Light Mode:**
- **Normal**: White background, clickable
- **Hover**: Light blue background (blue-50)
- **Selected**: Blue background (primary-600), white text
- **Disabled**: Gray text (slate-400), not clickable, cursor-not-allowed
- **Today**: Blue border (primary-600)

**Dark Mode:**
- **Normal**: Dark background (slate-700), clickable
- **Hover**: Darker blue background (slate-600)
- **Selected**: Blue background (primary-500), white text
- **Disabled**: Gray text (slate-500), not clickable
- **Today**: Blue border (primary-500)

### Navigation Behaviors

- **◀▶ Single arrows**: Previous/Next month
- **◀◀ ▶▶ Double arrows**: Previous/Next year
- **"快速选择月份" button**: Opens month grid

### Month Grid Popup

```
┌─────────────────┐
│  1月   2月   3月 │
│  4月   5月   6月 │
│  7月   8月   9月 │
│ 10月  11月  12月 │
└─────────────────┘
```

- 3x4 grid layout for all 12 months
- Click to jump to selected month
- Current month highlighted

**MonthGrid Component Implementation:**

```typescript
// MonthGrid.tsx
interface MonthGridProps {
  currentMonth: Date;
  onSelectMonth: (month: number) => void;
  onClose: () => void;
}

const MONTHS = [
  '1月', '2月', '3月', '4月', '5月', '6月',
  '7月', '8月', '9月', '10月', '11月', '12月'
];

export function MonthGrid({ currentMonth, onSelectMonth, onClose }: MonthGridProps) {
  const currentMonthIndex = currentMonth.getMonth();

  return (
    <div className="absolute top-full left-0 mt-2 bg-white dark:bg-slate-700 rounded-lg shadow-lg border border-slate-200 dark:border-slate-600 p-4 z-50">
      <div className="grid grid-cols-3 gap-2">
        {MONTHS.map((month, index) => (
          <button
            key={month}
            onClick={() => {
              onSelectMonth(index);
              onClose();
            }}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              index === currentMonthIndex
                ? 'bg-primary-600 text-white'
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

### Interactions

1. **Open/Close**
   - Click input box → Open calendar
   - Click outside → Close calendar
   - Select date → Auto close calendar

2. **Preset Buttons**
   - Click preset → Set start and end dates automatically
   - Example: "最近30天" = [today-30days, today]
   - Close both calendars (if two are open)

3. **Disabled Dates**
   - Disable future dates (cannot select after today)
   - Disable unavailable dates (queried from backend)

### Accessibility (WCAG 2.1 Level AA)

**Keyboard Navigation:**
- `Tab`: Focus input
- `Enter/Space`: Open calendar
- `Arrow Keys`: Navigate dates
- `PageUp/PageDown`: Previous/Next month
- `Shift+PageUp/PageDown`: Previous/Next year
- `Home`: First day of month
- `End`: Last day of month
- `Escape`: Close calendar

**ARIA Attributes:**
```typescript
<input
  id={id}
  type="text"
  value={formattedDate}
  aria-label={label || "选择日期"}
  aria-required={required}
  aria-invalid={error ? 'true' : 'false'}
  aria-describedby={error ? `${id}-error` : undefined}
  readOnly
/>

<div role="dialog" aria-label="日历" aria-modal="true">
  <DayPicker {...props} />
</div>
```

**Screen Reader Support:**
- react-day-picker 内置屏幕阅读器支持
- 日期格式化为本地化格式（中文）
- 选中日期通过 aria-live 朗读

## Technical Implementation

### Dependencies

```bash
pnpm add react-day-picker date-fns
```

- `react-day-picker`: v9+
- `date-fns`: Date manipulation utilities

### Props Interface

```typescript
interface DatePickerProps {
  value: string;                    // Selected date (YYYY-MM-DD)
  onChange: (date: string) => void; // Date change callback
  id?: string;                      // Input ID (for accessibility/testing)
  label?: string;                   // Input label text
  placeholder?: string;             // Placeholder text (default: "选择日期")
  required?: boolean;               // Required field indicator
  minDate?: string;                 // Minimum selectable date
  maxDate?: string;                 // Maximum selectable date (default: today)
  disabled?: boolean;               // Disabled state
  // Note: Preset buttons are managed at parent component level
}

interface PresetRange {
  label: string;      // Button text, e.g. "最近7天"
  days: number;       // Days from today, e.g. 7
}
```

### State Management

**Internal State:**
```typescript
const [isOpen, setIsOpen] = useState(false);        // Calendar visibility
const [currentMonth, setCurrentMonth] = useState<Date>(); // Displayed month
const [showMonthGrid, setShowMonthGrid] = useState(false); // Month grid visibility
```

**Data Flow:**
1. Parent Component → DatePicker: `value` prop
2. User clicks date → DatePicker calls `onChange(selectedDate)`
3. Parent updates `startTime`/`endTime` state
4. DatePicker re-renders with new value

**Preset Buttons (Parent Component Level):**

Preset buttons are implemented in the parent component (BacktestForm/OptimizationForm), not inside DatePicker.

```typescript
// In BacktestForm.tsx
const handlePresetClick = (days: number) => {
  const end = new Date();
  const start = subDays(end, days);
  setStartTime(format(start, 'yyyy-MM-dd'));
  setEndTime(format(end, 'yyyy-MM-dd'));
};

// Render preset buttons between date inputs and other form fields
<div className="flex gap-2 mb-4">
  <button onClick={() => handlePresetClick(7)}>最近7天</button>
  <button onClick={() => handlePresetClick(30)}>最近30天</button>
  <button onClick={() => handlePresetClick(90)}>最近3个月</button>
  <button onClick={() => handlePresetClick(365)}>最近1年</button>
</div>

// Two independent DatePickers
<DatePicker id="startTime" value={startTime} onChange={setStartTime} />
<DatePicker id="endTime" value={endTime} onChange={setEndTime} />
```

### Disabled Days Logic

```typescript
const disabledDays = [
  { after: new Date() },  // Disable future dates
  ...(minDate ? [{ before: new Date(minDate) }] : []),
];
```

### CSS Strategy

**使用 Tailwind CSS（与项目保持一致）:**

在 `frontend/app/globals.css` 中添加：

```css
@layer components {
  /* Light mode */
  .rdp-root {
    --rdp-cell-size: 36px;
    --rdp-accent-color: #2563eb; /* primary-600 */
    --rdp-background-color: #ffffff;
    --rdp-text-color: #0f172a; /* slate-900 */
    --rdp-day-hover-bg: #eff6ff; /* blue-50 */
    --rdp-disabled-color: #94a3b8; /* slate-400 */
  }

  /* Dark mode */
  .dark .rdp-root {
    --rdp-accent-color: #3b82f6; /* primary-500 */
    --rdp-background-color: #334155; /* slate-700 */
    --rdp-text-color: #f1f5f9; /* slate-100 */
    --rdp-day-hover-bg: #475569; /* slate-600 */
    --rdp-disabled-color: #64748b; /* slate-500 */
  }

  /* 覆盖更多样式 */
  .rdp-day_selected {
    font-weight: 600;
  }

  .rdp-day_today {
    border: 2px solid var(--rdp-accent-color);
  }
}
```

或者通过 inline style 设置 CSS 变量：

```typescript
<div
  className="rdp-root"
  style={{
    '--rdp-cell-size': '36px',
    '--rdp-accent-color': '#2563eb',
  } as React.CSSProperties}
>
  <DayPicker {...props} />
</div>
```

### Click Outside Detection

```typescript
useEffect(() => {
  const handleClickOutside = (event: MouseEvent) => {
    if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
      setIsOpen(false);
      setShowMonthGrid(false);
    }
  };

  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
}, []);
```

### Preset Ranges Implementation

```typescript
const defaultPresets: PresetRange[] = [
  { label: '最近7天', days: 7 },
  { label: '最近30天', days: 30 },
  { label: '最近3个月', days: 90 },
  { label: '最近1年', days: 365 },
];

// Usage in form
const handlePresetClick = (days: number) => {
  const end = new Date();
  const start = subDays(end, days);
  setStartTime(format(start, 'yyyy-MM-dd'));
  setEndTime(format(end, 'yyyy-MM-dd'));
};
```

## Error Handling

### Date Validation
- User-selected dates are always valid (guaranteed by react-day-picker)
- Parent component validates date range (start < end)
- Keep existing validation logic unchanged

### Edge Cases
```typescript
// Disable date boundaries
const isDateDisabled = (date: Date) => {
  if (maxDate && date > new Date(maxDate)) return true;
  if (minDate && date < new Date(minDate)) return true;
  return false;
};

// Empty value handling
if (!value) {
  return <div>请选择日期</div>;
}
```

### Available Date Range Query

**当前版本：禁用未来日期**

```typescript
// 默认禁用未来日期
<DatePicker
  maxDate={new Date().toISOString().split('T')[0]} // 今天
/>
```

**未来增强：查询可用数据范围**

注意：后端目前没有提供可用日期范围的 API。这需要在后端添加新端点。

后端实现计划（未来版本）：
```python
# backend/api/data.py
@router.get("/range/{symbol}/{interval}")
def get_date_range(symbol: str, interval: str):
    """返回可用数据的最早和最晚日期"""
    # 查询数据库获取 earliest_date 和 latest_date
    return {
        "earliest_date": "2020-01-01",
        "latest_date": "2024-12-31"
    }
```

前端使用（未来版本）：
```typescript
const { data: availableDateRange } = useQuery({
  queryKey: ['available-dates', symbol, interval],
  queryFn: () => dataApi.getDateRange(symbol, interval),
});

<DatePicker
  minDate={availableDateRange?.earliest_date}
  maxDate={availableDateRange?.latest_date}
/>
```

## Testing Strategy

### Unit Tests

```typescript
describe('DatePicker', () => {
  it('should render selected date correctly', () => {
    // Test date display
  });

  it('should call onChange when date is selected', () => {
    // Test date selection callback
  });

  it('should disable future dates', () => {
    // Test disable logic
  });

  it('should close when clicking outside', () => {
    // Test click outside close
  });

  it('should navigate months with arrows', () => {
    // Test month navigation
  });

  it('should jump years with double arrows', () => {
    // Test year navigation
  });

  it('should show month grid on button click', () => {
    // Test month grid trigger
  });

  it('should close month grid and update calendar when month selected', () => {
    // Test month grid selection
  });

  it('should disable dates before minDate', () => {
    // Test minDate boundary
  });

  it('should disable dates after maxDate', () => {
    // Test maxDate boundary
  });

  it('should render in dark mode', () => {
    // Test dark mode styling
  });
});

describe('MonthGrid', () => {
  it('should render all 12 months in 3x4 grid', () => {
    // Test grid layout
  });

  it('should highlight current month', () => {
    // Test current month highlighting
  });

  it('should call onSelectMonth when month clicked', () => {
    // Test month selection
  });
});

describe('BacktestForm with DatePicker', () => {
  it('should update both date pickers when preset button clicked', () => {
    // Test preset button integration
    // Verify startTime and endTime both updated
  });
});
```

### Integration Tests (Playwright E2E)

```typescript
test('can select date range for backtest', async ({ page }) => {
  await page.goto('/backtest');

  // Select strategy first
  await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

  // Open start date picker
  await page.click('#startTime');

  // Select date
  await page.click('[data-date="2024-01-15"]');

  // Verify input value
  await expect(page.locator('#startTime')).toHaveValue('2024-01-15');

  // Open end date picker
  await page.click('#endTime');

  // Select date
  await page.click('[data-date="2024-03-20"]');

  // Verify input value
  await expect(page.locator('#endTime')).toHaveValue('2024-03-20');
});

test('preset buttons update both start and end dates', async ({ page }) => {
  await page.goto('/backtest');
  await page.selectOption('select#strategy', 'DualMovingAverageStrategy');

  // Click "最近30天" button
  await page.click('button:has-text("最近30天")');

  // Verify both dates are set correctly
  const today = new Date().toISOString().split('T')[0];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  await expect(page.locator('#endTime')).toHaveValue(today);
  await expect(page.locator('#startTime')).toHaveValue(thirtyDaysAgo);
});

test('can navigate to different month and year', async ({ page }) => {
  await page.goto('/backtest');
  await page.selectOption('select#strategy', 'DualMovingAverageStrategy');
  await page.click('#startTime');

  // Click next month arrow
  await page.click('.rdp-nav_button-next');
  await expect(page.locator('.rdp-caption')).toBeVisible();

  // Click next year arrow (double arrow)
  await page.click('.rdp-nav_button-next-double');
  await expect(page.locator('.rdp-caption')).toBeVisible();

  // Open month grid
  await page.click('button:has-text("快速选择月份")');
  await expect(page.locator('.month-grid')).toBeVisible();

  // Select a month
  await page.click('button:has-text("6月")');
  await expect(page.locator('.month-grid')).not.toBeVisible();
});

test('future dates are disabled', async ({ page }) => {
  await page.goto('/backtest');
  await page.selectOption('select#strategy', 'DualMovingAverageStrategy');
  await page.click('#startTime');

  // Try to click a future date
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const dateString = tomorrow.toISOString().split('T')[0];

  const futureDay = await page.locator(`[data-date="${dateString}"]`);
  await expect(futureDay).toHaveAttribute('disabled');
});

test('keyboard navigation works', async ({ page }) => {
  await page.goto('/backtest');
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
  const inputValue = await page.locator('#startTime').inputValue();
  expect(inputValue).toBeTruthy();
});

test('dark mode styling is correct', async ({ page }) => {
  // Enable dark mode (if app has dark mode toggle)
  await page.goto('/backtest');
  await page.click('[data-testid="theme-toggle"]'); // if exists

  await page.selectOption('select#strategy', 'DualMovingAverageStrategy');
  await page.click('#startTime');

  // Verify dark mode styles
  const calendar = await page.locator('.rdp-root');
  await expect(calendar).toHaveClass(/dark/);
});
```

## Migration Plan

### Phase 1: Install Dependencies
```bash
pnpm add react-day-picker date-fns
```

### Phase 2: Create DatePicker Component
- Create `frontend/components/DatePicker/` directory
- Implement `DatePicker.tsx`
- Implement `PresetButtons.tsx`
- Add style files

### Phase 3: Update BacktestForm
- Replace `<input type="date">` with `<DatePicker />`
- Test backtest flow

### Phase 4: Update OptimizationForm
- 替换 `<input type="datetime-local">` 为 `<DatePicker />`（仅日期部分）
- **移除时间选择**：优化表不需要精确到小时/分钟
- 保持现有的日期格式化逻辑（`toISOString()`）

**决策说明：**
- 回测和参数优化都是基于日线或更长周期的数据
- 精确到小时/分钟没有实际意义
- 简化用户操作流程

### Phase 5: Style Adjustments
- Fine-tune styles for consistency
- Add dark mode support

### Backward Compatibility

- No impact on API interfaces
- No impact on database schema
- UI layer improvement only

## Success Criteria

- [ ] Users can select dates in a single calendar panel
- [ ] Month and year navigation is smooth
- [ ] Month grid provides quick month selection
- [ ] Preset range buttons work correctly
- [ ] Future dates are disabled
- [ ] Click outside closes the calendar
- [ ] Styles match existing design system (slate color, rounded-lg)
- [ ] Dark mode works correctly (colors, backgrounds, text)
- [ ] All existing tests pass
- [ ] New component has unit tests (>80% coverage)
- [ ] E2E tests cover main user flows
- [ ] Accessibility: Keyboard navigation works
- [ ] Accessibility: ARIA labels are present
- [ ] Performance is acceptable (no noticeable lag)

## Future Enhancements (Out of Scope)

- Date range picker in single calendar (highlight range between start and end)
- Time zone support
- Custom date formats
- Custom holidays/weekends
- Localization (i18n)
- Keyboard navigation optimization
