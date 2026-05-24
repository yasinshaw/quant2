# 日期时间选择器改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 用 React DatePicker 替换原生 HTML date input，支持日期+时分选择，提供中文界面和更好的用户体验

**架构：** 创建可复用的 DateTimePicker 组件，封装 react-datepicker 库，配置中文国际化，与 Tailwind CSS 设计系统集成。在 DownloadForm（仅日期）、BacktestForm 和 OptimizationForm（日期+时间）中使用该组件。

**技术栈：** React DatePicker 6.9+, date-fns 3.3+, Next.js 14, TypeScript, Tailwind CSS

---

## 文件结构

```
frontend/
  components/
    DateTimePicker/
      index.tsx              # 主组件（新建）
      styles.css             # 自定义样式（新建）
    BacktestForm.tsx         # 回测表单（修改）
    DownloadForm.tsx         # 下载表单（修改）
    OptimizationForm.tsx     # 优化表单（修改）
  package.json               # 依赖管理（修改）
  e2e/
    backtest-flow.spec.ts    # E2E 测试（修改）
    data-download.spec.ts    # E2E 测试（修改）
    optimization.spec.ts     # E2E 测试（修改）
```

**设计原则：**
- 单一职责：DateTimePicker 只负责日期时间选择
- 可复用：通过 props 控制是否显示时间
- 不可变：使用 date-fns 进行日期操作，避免直接修改 Date 对象
- 向后兼容：API 接口保持 ISO 8601 字符串格式

---

## Task 1: 安装依赖包

**文件：**
- 修改: `frontend/package.json`

- [ ] **Step 1: 安装 react-datepicker 和 date-fns**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm add react-datepicker@^6.9.0 date-fns@^3.3.0
```

- [ ] **Step 2: 验证安装成功**

```bash
pnpm list react-datepicker date-fns
```

预期输出：
```
react-datepicker 6.9.0
date-fns 3.3.0
```

- [ ] **Step 3: 提交依赖变更**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore: add react-datepicker and date-fns dependencies"
```

---

## Task 2: 创建 DateTimePicker 组件

**文件：**
- 创建: `frontend/components/DateTimePicker/index.tsx`
- 创建: `frontend/components/DateTimePicker/styles.css`

- [ ] **Step 1: 创建组件目录**

```bash
mkdir -p /Users/yasin/code/quant2/frontend/components/DateTimePicker
```

- [ ] **Step 2: 编写 DateTimePicker 组件**

创建文件 `frontend/components/DateTimePicker/index.tsx`：

```typescript
'use client';

import ReactDatePicker from 'react-datepicker';
import { zhCN } from 'date-fns/locale';
import 'react-datepicker/dist/react-datepicker.css';
import './styles.css';

export interface DateTimePickerProps {
  /** 当前选中的日期时间 */
  value: Date | null;

  /** 日期时间变更回调 */
  onChange: (date: Date | null) => void;

  /** 是否显示时间选择（默认 false） */
  showTime?: boolean;

  /** 时间格式（默认 'HH:mm'） */
  timeFormat?: 'HH:mm' | 'HH:mm:ss';

  /** 占位符文本 */
  placeholder?: string;

  /** 最小可选日期 */
  minDate?: Date;

  /** 最大可选日期 */
  maxDate?: Date;

  /** 是否禁用 */
  disabled?: boolean;

  /** 输入框 ID（用于 label 关联） */
  id?: string;

  /** 额外的 CSS 类名 */
  className?: string;
}

export default function DateTimePicker({
  value,
  onChange,
  showTime = false,
  timeFormat = 'HH:mm',
  placeholder,
  minDate,
  maxDate,
  disabled = false,
  id,
  className = '',
}: DateTimePickerProps) {
  const dateFormat = showTime ? 'yyyy-MM-dd HH:mm' : 'yyyy-MM-dd';

  return (
    <ReactDatePicker
      selected={value}
      onChange={onChange}
      locale={zhCN}
      dateFormat={dateFormat}
      showTimeSelect={showTime}
      timeFormat={timeFormat}
      timeIntervals={15}
      placeholderText={placeholder}
      minDate={minDate}
      maxDate={maxDate}
      disabled={disabled}
      id={id}
      className={className}
      wrapperClassName="w-full"
      calendarClassName="custom-calendar"
      popperClassName="custom-popper"
    />
  );
}
```

- [ ] **Step 3: 编写自定义样式**

创建文件 `frontend/components/DateTimePicker/styles.css`：

```css
/* 输入框样式 - 匹配 Tailwind 设计系统 */
.react-datepicker__input-container input {
  @apply w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2;
  @apply bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100;
  @apply focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent;
  @apply transition-colors;
}

/* 日历容器样式 */
.react-datepicker {
  @apply font-sans border border-slate-200 dark:border-slate-700;
  @apply bg-white dark:bg-slate-800 rounded-lg shadow-lg;
}

/* 头部样式 */
.react-datepicker__header {
  @apply bg-slate-50 dark:bg-slate-700 border-b border-slate-200 dark:border-slate-600;
}

/* 星期标题样式 */
.react-datepicker__day-name {
  @apply text-slate-600 dark:text-slate-400 font-medium;
}

/* 日期样式 */
.react-datepicker__day {
  @apply text-slate-900 dark:text-slate-100;
  @apply hover:bg-slate-100 dark:hover:bg-slate-700 rounded;
}

/* 选中的日期 */
.react-datepicker__day--selected,
.react-datepicker__day--keyboard-selected {
  @apply bg-primary-600 hover:bg-primary-700 text-white;
}

/* 时间选择器样式 */
.react-datepicker__time-container {
  @apply border-l border-slate-200 dark:border-slate-600;
}

.react-datepicker__time-list-item {
  @apply hover:bg-slate-100 dark:hover:bg-slate-700;
}

.react-datepicker__time-list-item--selected {
  @apply bg-primary-600 text-white;
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .react-datepicker-popper {
    @apply bg-slate-800;
  }
}
```

- [ ] **Step 4: 提交组件代码**

```bash
git add frontend/components/DateTimePicker/
git commit -m "feat: add DateTimePicker component with Chinese locale support"
```

---

## Task 3: 更新 DownloadForm 组件

**文件：**
- 修改: `frontend/components/DownloadForm.tsx`

- [ ] **Step 1: 读取当前 DownloadForm 实现**

当前使用 `<input type="date">`，状态为字符串类型。

- [ ] **Step 2: 更新 DownloadForm 导入和状态**

在文件顶部添加导入：

```typescript
import DateTimePicker from './DateTimePicker';
import { startOfDay, endOfDay } from 'date-fns';
```

修改状态定义（第 18-19 行）：

```typescript
// 修改前
const [startDate, setStartDate] = useState(getDefaultDate(30));
const [endDate, setEndDate] = useState(getDefaultDate(0));

// 修改后
const [startDate, setStartDate] = useState<Date | null>(() => {
  const date = new Date();
  date.setDate(date.getDate() - 30);
  return startOfDay(date);
});
const [endDate, setEndDate] = useState<Date | null>(() => {
  return endOfDay(new Date());
});
```

删除 `getDefaultDate` 函数（第 12-16 行），因为不再需要。

- [ ] **Step 3: 替换表单输入组件**

替换开始日期输入（第 50-58 行）：

```typescript
// 修改前
<input
  type="date"
  id="start_date"
  value={startDate}
  onChange={(e) => setStartDate(e.target.value)}
  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
  required
/>
<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Data will start from 00:00:00 of this date</p>

// 修改后
<DateTimePicker
  value={startDate}
  onChange={(date) => setStartDate(date ? startOfDay(date) : null)}
  placeholder="选择开始日期"
  id="start_date"
/>
<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">数据将从当天的 00:00:00 开始</p>
```

替换结束日期输入（第 64-72 行）：

```typescript
// 修改前
<input
  type="date"
  id="end_date"
  value={endDate}
  onChange={(e) => setEndDate(e.target.value)}
  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
  required
/>
<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Data will end at 23:59:59 of this date</p>

// 修改后
<DateTimePicker
  value={endDate}
  onChange={(date) => setEndDate(date ? endOfDay(date) : null)}
  placeholder="选择结束日期"
  id="end_date"
/>
<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">数据将到当天的 23:59:59 结束</p>
```

- [ ] **Step 4: 更新提交逻辑**

修改 `handleSubmit` 函数中的日期处理（第 35-36 行）：

```typescript
// 修改前
const startISO = new Date(startDate + 'T00:00:00').toISOString();
const endISO = new Date(endDate + 'T23:59:59').toISOString();

// 修改后
const startISO = startDate ? startDate.toISOString() : '';
const endISO = endDate ? endDate.toISOString() : '';
```

- [ ] **Step 5: 更新验证逻辑**

修改日期验证（第 29-32 行）：

```typescript
// 修改前
if (new Date(startDate) >= new Date(endDate)) {
  alert('Start date must be before end date');
  return;
}

// 修改后
if (startDate && endDate && startDate >= endDate) {
  alert('Start date must be before end date');
  return;
}
```

- [ ] **Step 6: 验证组件工作**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm dev
```

在浏览器中打开 http://localhost:3001/data，测试：
- 日期选择器正常显示
- 中文界面
- 开始日期默认为 30 天前的 00:00
- 结束日期默认为今天的 23:59
- 表单提交正常

- [ ] **Step 7: 提交变更**

```bash
git add frontend/components/DownloadForm.tsx
git commit -m "feat: integrate DateTimePicker in DownloadForm"
```

---

## Task 4: 更新 BacktestForm 组件

**文件：**
- 修改: `frontend/components/BacktestForm.tsx`

- [ ] **Step 1: 读取当前 BacktestForm 实现**

当前使用 `<input type="date">`，状态为字符串类型。

- [ ] **Step 2: 更新 BacktestForm 导入和状态**

在文件顶部添加导入：

```typescript
import DateTimePicker from './DateTimePicker';
import { setHours, setMinutes, setSeconds } from 'date-fns';
```

修改状态定义（第 18-19 行）：

```typescript
// 修改前
const [startTime, setStartTime] = useState('');
const [endTime, setEndTime] = useState('');

// 修改后
const [startTime, setStartTime] = useState<Date | null>(null);
const [endTime, setEndTime] = useState<Date | null>(null);
```

- [ ] **Step 3: 添加智能默认值处理函数**

在组件内部添加辅助函数（在 `handleParameterChange` 之前）：

```typescript
// 智能设置开始时间为 00:00
const handleStartTimeChange = (date: Date | null) => {
  if (date) {
    const withDefaultTime = setHours(setMinutes(setSeconds(date, 0), 0), 0);
    setStartTime(withDefaultTime);
  } else {
    setStartTime(null);
  }
};

// 智能设置结束时间为 23:59
const handleEndTimeChange = (date: Date | null) => {
  if (date) {
    const withDefaultTime = setHours(setMinutes(setSeconds(date, 0), 59), 23);
    setEndTime(withDefaultTime);
  } else {
    setEndTime(null);
  }
};
```

- [ ] **Step 4: 替换表单输入组件**

替换开始时间输入（第 176-183 行）：

```typescript
// 修改前
<input
  id="startTime"
  type="date"
  value={startTime}
  onChange={(e) => setStartTime(e.target.value)}
  required
  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
/>

// 修改后
<DateTimePicker
  value={startTime}
  onChange={handleStartTimeChange}
  showTime={true}
  timeFormat="HH:mm"
  placeholder="选择开始时间"
  id="startTime"
/>
```

替换结束时间输入（第 190-197 行）：

```typescript
// 修改前
<input
  id="endTime"
  type="date"
  value={endTime}
  onChange={(e) => setEndTime(e.target.value)}
  required
  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
/>

// 修改后
<DateTimePicker
  value={endTime}
  onChange={handleEndTimeChange}
  showTime={true}
  timeFormat="HH:mm"
  placeholder="选择结束时间"
  id="endTime"
/>
```

- [ ] **Step 5: 更新提交逻辑**

修改 `handleSubmit` 函数中的日期处理（第 76-82 行）：

```typescript
// 修改前
if (!startTime || !endTime) {
  setError('Please select both start and end dates');
  return;
}

const start = new Date(startTime);
const end = new Date(endTime);

// 修改后
if (!startTime || !endTime) {
  setError('Please select both start and end times');
  return;
}

const start = startTime;
const end = endTime;
```

删除第 84-92 行的日期创建和验证逻辑，因为已经在 handleStartTimeChange 和 handleEndTimeChange 中处理。

- [ ] **Step 6: 验证组件工作**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm dev
```

在浏览器中打开 http://localhost:3001/backtest，测试：
- 日期时间选择器正常显示
- 可以选择日期和时分
- 中文界面
- 选择日期后自动设置时间为 00:00（开始）或 23:59（结束）
- 可以手动修改时间
- 表单提交正常

- [ ] **Step 7: 提交变更**

```bash
git add frontend/components/BacktestForm.tsx
git commit -m "feat: integrate DateTimePicker in BacktestForm with time selection"
```

---

## Task 5: 更新 OptimizationForm 组件

**文件：**
- 修改: `frontend/components/OptimizationForm.tsx`

- [ ] **Step 1: 读取当前 OptimizationForm 实现**

当前使用 `<input type="datetime-local">`（第 214-236 行）。

- [ ] **Step 2: 更新 OptimizationForm 导入和状态**

在文件顶部添加导入：

```typescript
import DateTimePicker from './DateTimePicker';
import { setHours, setMinutes, setSeconds } from 'date-fns';
```

修改状态定义（第 24-25 行）：

```typescript
// 修改前
const [startTime, setStartTime] = useState('');
const [endTime, setEndTime] = useState('');

// 修改后
const [startTime, setStartTime] = useState<Date | null>(null);
const [endTime, setEndTime] = useState<Date | null>(null);
```

- [ ] **Step 3: 添加智能默认值处理函数**

在 `handleRangeChange` 函数之后添加：

```typescript
// 智能设置开始时间为 00:00
const handleStartTimeChange = (date: Date | null) => {
  if (date) {
    const withDefaultTime = setHours(setMinutes(setSeconds(date, 0), 0), 0);
    setStartTime(withDefaultTime);
  } else {
    setStartTime(null);
  }
};

// 智能设置结束时间为 23:59
const handleEndTimeChange = (date: Date | null) => {
  if (date) {
    const withDefaultTime = setHours(setMinutes(setSeconds(date, 0), 59), 23);
    setEndTime(withDefaultTime);
  } else {
    setEndTime(null);
  }
};
```

- [ ] **Step 4: 替换表单输入组件**

替换开始时间输入（第 214-221 行）：

```typescript
// 修改前
<input
  id="startTime"
  type="datetime-local"
  value={startTime}
  onChange={(e) => setStartTime(e.target.value)}
  required
  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
/>

// 修改后
<DateTimePicker
  value={startTime}
  onChange={handleStartTimeChange}
  showTime={true}
  timeFormat="HH:mm"
  placeholder="选择开始时间"
  id="startTime"
/>
```

替换结束时间输入（第 228-235 行）：

```typescript
// 修改前
<input
  id="endTime"
  type="datetime-local"
  value={endTime}
  onChange={(e) => setEndTime(e.target.value)}
  required
  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
/>

// 修改后
<DateTimePicker
  value={endTime}
  onChange={handleEndTimeChange}
  showTime={true}
  timeFormat="HH:mm"
  placeholder="选择结束时间"
  id="endTime"
/>
```

- [ ] **Step 5: 更新提交逻辑**

修改 `handleSubmit` 函数中的日期处理（第 96-102 行）：

```typescript
// 修改前
if (!startTime || !endTime) {
  setError('Please select both start and end dates');
  return;
}

const start = new Date(startTime);
const end = new Date(endTime);

// 修改后
if (!startTime || !endTime) {
  setError('Please select both start and end times');
  return;
}

const start = startTime;
const end = endTime;
```

- [ ] **Step 6: 验证组件工作**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm dev
```

在浏览器中打开 http://localhost:3001/optimize，测试：
- 日期时间选择器正常显示
- 可以选择日期和时分
- 中文界面
- 选择日期后自动设置时间为 00:00（开始）或 23:59（结束）
- 可以手动修改时间
- 表单提交正常

- [ ] **Step 7: 提交变更**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: integrate DateTimePicker in OptimizationForm with time selection"
```

---

## Task 6: 更新 E2E 测试 - 数据下载

**文件：**
- 修改: `frontend/e2e/data-download.spec.ts`

- [ ] **Step 1: 读取当前测试文件**

查看现有的日期选择器测试代码。

- [ ] **Step 2: 更新日期选择器交互方式**

查找所有 `input[type="date"]` 相关的测试代码，替换为 DateTimePicker 的交互方式：

```typescript
// 修改前
await page.fill('input#start_date', '2024-01-01');
await page.fill('input#end_date', '2024-01-31');

// 修改后
// 点击开始日期输入框
await page.click('#start_date');
// 等待日历弹出
await page.waitForSelector('.react-datepicker');
// 选择 1 月 1 日
await page.click('.react-datepicker__day--001:not(.react-datepicker__day--outside-month)');
// 点击结束日期输入框
await page.click('#end_date');
// 选择 1 月 31 日
await page.click('.react-datepicker__day--031:not(.react-datepicker__day--outside-month)');
```

- [ ] **Step 3: 添加等待逻辑**

确保日期选择器弹出层有足够时间渲染：

```typescript
// 在点击日期选择器后添加
await page.waitForSelector('.react-datepicker', { state: 'visible' });
await page.waitForTimeout(100); // 等待动画完成
```

- [ ] **Step 4: 运行测试验证**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm test:e2e e2e/data-download.spec.ts
```

预期结果：所有测试通过

- [ ] **Step 5: 提交变更**

```bash
git add frontend/e2e/data-download.spec.ts
git commit -m "test: update E2E tests for DateTimePicker in data download"
```

---

## Task 7: 更新 E2E 测试 - 回测流程

**文件：**
- 修改: `frontend/e2e/backtest-flow.spec.ts`

- [ ] **Step 1: 读取当前测试文件**

查看现有的日期选择器测试代码。

- [ ] **Step 2: 更新日期时间选择器交互方式**

查找所有 `input[type="date"]` 相关的测试代码：

```typescript
// 修改前
await page.fill('input#startTime', '2024-01-01');
await page.fill('input#endTime', '2024-01-31');

// 修改后
// 选择开始时间
await page.click('#startTime');
await page.waitForSelector('.react-datepicker');
// 选择日期
await page.click('.react-datepicker__day--001:not(.react-datepicker__day--outside-month)');
// 选择时间（可选，因为有默认值）
await page.click('.react-datepicker__time-list-item--selected');

// 选择结束时间
await page.click('#endTime');
await page.waitForSelector('.react-datepicker');
// 选择日期
await page.click('.react-datepicker__day--031:not(.react-datepicker__day--outside-month)');
```

- [ ] **Step 3: 添加时间选择验证（可选）**

如果测试需要验证具体时间：

```typescript
// 验证时间显示格式
const startTimeValue = await page.$eval('#startTime', (el: HTMLInputElement) => el.value);
expect(startTimeValue).toMatch(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}/);
```

- [ ] **Step 4: 运行测试验证**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm test:e2e e2e/backtest-flow.spec.ts
```

预期结果：所有测试通过

- [ ] **Step 5: 提交变更**

```bash
git add frontend/e2e/backtest-flow.spec.ts
git commit -m "test: update E2E tests for DateTimePicker in backtest flow"
```

---

## Task 8: 更新 E2E 测试 - 参数优化

**文件：**
- 修改: `frontend/e2e/optimization.spec.ts`

- [ ] **Step 1: 读取当前测试文件**

查看现有的日期时间选择器测试代码。

- [ ] **Step 2: 更新日期时间选择器交互方式**

与 Task 7 类似，更新日期时间选择器交互：

```typescript
// 修改前
await page.fill('input#startTime', '2024-01-01T00:00');
await page.fill('input#endTime', '2024-01-31T23:59');

// 修改后
await page.click('#startTime');
await page.waitForSelector('.react-datepicker');
await page.click('.react-datepicker__day--001:not(.react-datepicker__day--outside-month)');

await page.click('#endTime');
await page.waitForSelector('.react-datepicker');
await page.click('.react-datepicker__day--031:not(.react-datepicker__day--outside-month)');
```

- [ ] **Step 3: 运行测试验证**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm test:e2e e2e/optimization.spec.ts
```

预期结果：所有测试通过

- [ ] **Step 4: 提交变更**

```bash
git add frontend/e2e/optimization.spec.ts
git commit -m "test: update E2E tests for DateTimePicker in optimization"
```

---

## Task 9: 运行完整测试套件

**文件：**
- 无文件修改

- [ ] **Step 1: 运行前端 lint 检查**

```bash
cd /Users/yasin/code/quant2/frontend
pnpm lint
```

预期结果：无错误

- [ ] **Step 2: 运行所有 E2E 测试**

```bash
pnpm test:e2e
```

预期结果：所有测试通过

- [ ] **Step 3: 手动测试所有场景**

在浏览器中测试以下场景：

1. **数据下载页面** (http://localhost:3001/data)
   - [ ] 日期选择器正常显示
   - [ ] 中文界面
   - [ ] 默认值正确（30天前 - 今天）
   - [ ] 日期范围验证正常
   - [ ] 提交后数据下载正常

2. **回测页面** (http://localhost:3001/backtest)
   - [ ] 日期时间选择器正常显示
   - [ ] 可以选择日期和时分
   - [ ] 中文界面
   - [ ] 选择日期后自动设置时间（00:00/23:59）
   - [ ] 可以手动修改时间
   - [ ] 表单提交正常

3. **参数优化页面** (http://localhost:3001/optimize)
   - [ ] 日期时间选择器正常显示
   - [ ] 可以选择日期和时分
   - [ ] 中文界面
   - [ ] 表单提交正常

4. **暗色模式**
   - [ ] 切换暗色模式
   - [ ] 日期选择器样式正常

5. **响应式设计**
   - [ ] 移动端显示正常
   - [ ] 日期选择器弹出层位置正确

- [ ] **Step 4: 检查浏览器控制台**

打开浏览器开发者工具，确认：
- 无 JavaScript 错误
- 无 CSS 警告
- 无网络请求失败

---

## Task 10: 最终验证和提交

**文件：**
- 无文件修改

- [ ] **Step 1: 确认所有功能正常**

检查清单：
- [ ] DownloadForm 日期选择正常
- [ ] BacktestForm 日期时间选择正常
- [ ] OptimizationForm 日期时间选择正常
- [ ] 中文界面显示正常
- [ ] 智能默认值工作正常
- [ ] 所有 E2E 测试通过
- [ ] 无控制台错误
- [ ] 暗色模式兼容
- [ ] 响应式布局正常

- [ ] **Step 2: 查看最终 diff**

```bash
git status
git diff main
```

确认所有变更符合预期。

- [ ] **Step 3: 推送所有提交**

```bash
git push origin main
```

- [ ] **Step 4: 更新设计文档状态**

修改 `docs/superpowers/specs/2026-03-24-datetime-picker-improvement-design.md`，将状态更新为：

```markdown
**状态：** 实施完成 ✅
```

提交更新：

```bash
git add docs/superpowers/specs/2026-03-24-datetime-picker-improvement-design.md
git commit -m "docs: mark datetime picker improvement as completed"
git push origin main
```

---

## 验收标准

实施完成后，应满足以下标准：

1. ✅ **功能完整性**
   - 用户可以选择精确到分钟的开始和结束时间
   - DownloadForm 仅选择日期，自动设置时间为 00:00-23:59
   - BacktestForm 和 OptimizationForm 可选择日期+时分
   - 中文界面，格式为 2024-01-15 14:30

2. ✅ **代码质量**
   - 组件可复用，接口清晰
   - 遵循不可变性原则
   - TypeScript 类型完整
   - 无 lint 错误

3. ✅ **测试覆盖**
   - 所有 E2E 测试通过
   - 测试覆盖所有表单场景

4. ✅ **用户体验**
   - 界面美观，与 Tailwind 设计系统一致
   - 暗色模式正常显示
   - 响应式布局正常
   - 无控制台错误或警告

5. ✅ **向后兼容**
   - API 接口保持不变
   - 数据格式保持 ISO 8601

---

## 回滚计划

如果实施后发现问题，可以按以下步骤回滚：

1. **回滚到实施前状态：**
```bash
git revert <commit-hash>
```

2. **卸载依赖：**
```bash
cd frontend
pnpm remove react-datepicker date-fns
```

3. **恢复原始表单组件：**
使用 git checkout 恢复原始文件：
```bash
git checkout <commit-before-implementation> -- frontend/components/DownloadForm.tsx frontend/components/BacktestForm.tsx frontend/components/OptimizationForm.tsx
```

---

## 未来优化建议

如果需要进一步改进，可以考虑：

1. **性能优化：**
   - 使用 Next.js dynamic import 延迟加载 react-datepicker
   - 减少包体积

2. **功能增强：**
   - 添加"最近7天"、"本月"等快捷选项
   - 支持日期范围一次性选择
   - 自定义时间间隔（15/30/60 分钟）

3. **可访问性：**
   - 添加键盘导航测试
   - 屏幕阅读器测试
