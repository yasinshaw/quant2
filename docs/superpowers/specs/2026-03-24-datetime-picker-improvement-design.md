# 日期时间选择器改进设计文档

**日期：** 2026-03-24
**状态：** 设计完成，待实施

## 背景

当前项目使用原生 HTML `<input type="date">` 进行日期选择，存在以下问题：
- 无法选择时分秒，只能选择日期
- 用户体验不佳，交互方式原始
- 在 BacktestForm 和 DownloadForm 中，时间被硬编码（00:00:00 和 23:59:59）
- 缺乏灵活性，无法满足精确时间选择需求

## 需求

### 功能需求
1. 支持日期 + 时分选择（灵活配置）
2. 混合式交互：下拉选择 + 手动输入
3. 智能默认值：开始时间 00:00，结束时间 23:59
4. 中文界面 + 标准格式（2024-01-15 14:30）

### 非功能需求
1. 与现有 Tailwind CSS 设计系统无缝集成
2. 保持 API 接口向后兼容
3. 轻量级，不影响页面加载性能
4. 良好的可访问性（a11y）

### 使用场景差异
- **DownloadForm：** 仅需要日期选择（数据下载以天为单位）
- **BacktestForm：** 需要日期 + 时分选择（回测需要精确时间点）

## 技术方案

### 选型：React DatePicker

**选择理由：**
- GitHub 8.2k+ stars，npm 2M+ 周下载量，社区成熟
- 功能全面，原生支持日期 + 时间选择
- 高度可定制，样式灵活
- 优秀的 TypeScript 支持
- 内置国际化支持（包含中文）
- 包体积适中（~50KB gzipped）
- 与 Tailwind CSS 配合良好

**依赖库：**
```json
{
  "react-datepicker": "^6.9.0",
  "date-fns": "^3.3.0"
}
```

- `react-datepicker`：主组件库
- `date-fns`：轻量级日期处理库（替代 moment.js，tree-shakable）

### 架构设计

#### 组件结构

```
frontend/components/
  DateTimePicker/
    index.tsx          # 主组件
    styles.css         # 自定义样式
```

#### 组件接口

```typescript
interface DateTimePickerProps {
  // 当前选中的日期时间
  value: Date | null;

  // 日期时间变更回调
  onChange: (date: Date | null) => void;

  // 是否显示时间选择（默认 false）
  showTime?: boolean;

  // 时间格式（默认 'HH:mm'）
  timeFormat?: 'HH:mm' | 'HH:mm:ss';

  // 占位符文本
  placeholder?: string;

  // 最小可选日期
  minDate?: Date;

  // 最大可选日期
  maxDate?: Date;

  // 是否禁用
  disabled?: boolean;

  // 输入框 ID（用于 label 关联）
  id?: string;

  // 额外的 CSS 类名
  className?: string;
}
```

#### 核心实现

```typescript
import ReactDatePicker from 'react-datepicker';
import { zhCN } from 'date-fns/locale';
import 'react-datepicker/dist/react-datepicker.css';
import './styles.css';

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
  className,
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

### 样式集成

#### Tailwind CSS + 自定义样式

**styles.css：**
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

### 页面集成

#### DownloadForm（仅日期）

**当前实现：**
```typescript
<input
  type="date"
  value={startDate}
  onChange={(e) => setStartDate(e.target.value)}
  required
/>
```

**改进后：**
```typescript
const [startDate, setStartDate] = useState<Date | null>(getDefaultDate(30));
const [endDate, setEndDate] = useState<Date | null>(getDefaultDate(0));

<DateTimePicker
  value={startDate}
  onChange={(date) => setStartDate(date)}
  placeholder="选择开始日期"
  id="start_date"
/>

<DateTimePicker
  value={endDate}
  onChange={(date) => setEndDate(date)}
  placeholder="选择结束日期"
  id="end_date"
/>
```

**提交逻辑：**
```typescript
const startISO = startDate
  ? new Date(startDate.setHours(0, 0, 0, 0)).toISOString()
  : '';
const endISO = endDate
  ? new Date(endDate.setHours(23, 59, 59, 999)).toISOString()
  : '';
```

#### BacktestForm（日期 + 时间）

**当前实现：**
```typescript
<input
  type="date"
  value={startTime}
  onChange={(e) => setStartTime(e.target.value)}
  required
/>
```

**改进后：**
```typescript
const [startTime, setStartTime] = useState<Date | null>(null);
const [endTime, setEndTime] = useState<Date | null>(null);

<DateTimePicker
  value={startTime}
  onChange={(date) => setStartTime(date)}
  showTime={true}
  timeFormat="HH:mm"
  placeholder="选择开始时间"
  id="startTime"
/>

<DateTimePicker
  value={endTime}
  onChange={(date) => setEndTime(date)}
  showTime={true}
  timeFormat="HH:mm"
  placeholder="选择结束时间"
  id="endTime"
/>
```

**智能默认值：**
- 用户选择日期后，自动设置时间为 00:00（开始）或 23:59（结束）
- 用户可以随时修改时间

**提交逻辑：**
```typescript
const start = startTime ? startTime.toISOString() : '';
const end = endTime ? endTime.toISOString() : '';
```

### 国际化配置

使用 date-fns 的中文 locale：

```typescript
import { zhCN } from 'date-fns/locale';

<ReactDatePicker
  locale={zhCN}
  // 月份显示：一月、二月...
  // 星期显示：日、一、二、三、四、五、六
/>
```

### 智能默认值实现

```typescript
// 当用户选择日期时，智能设置时间
const handleStartDateChange = (date: Date | null) => {
  if (date) {
    // 开始时间默认为当天的 00:00
    date.setHours(0, 0, 0, 0);
  }
  setStartTime(date);
};

const handleEndDateChange = (date: Date | null) => {
  if (date) {
    // 结束时间默认为当天的 23:59
    date.setHours(23, 59, 0, 0);
  }
  setEndTime(date);
};
```

### 数据处理

#### 时区处理
- 保持当前逻辑：使用本地时间
- 提交时转换为 ISO 8601 格式
- 后端继续使用 UTC 时间

#### 向后兼容
- API 接口保持不变
- 继续使用 ISO 8601 字符串格式
- 后端无需修改

### 测试策略

#### 单元测试（可选）
- 测试 DateTimePicker 组件的基本功能
- 验证时间格式化逻辑
- 测试边界情况

#### E2E 测试（必需）
更新 Playwright 测试以适配新组件：

```typescript
// 旧代码：直接填写 input[type="date"]
await page.fill('input[type="date"]', '2024-01-01');

// 新代码：点击日期选择器，选择日期
await page.click('[data-testid="start-date-picker"]');
await page.click('.react-datepicker__day--001'); // 选择 1 号
await page.click('.react-datepicker__day--015'); // 选择 15 号
```

**需要更新的测试文件：**
- `frontend/e2e/data-download.spec.ts`
- `frontend/e2e/backtest-flow.spec.ts`
- `frontend/e2e/optimization.spec.ts`

## 实施步骤

### Phase 1: 安装和配置
1. 安装依赖包（react-datepicker, date-fns）
2. 创建 DateTimePicker 组件目录结构
3. 配置 TypeScript 类型定义

### Phase 2: 组件开发
4. 实现 DateTimePicker 组件
5. 编写自定义样式（styles.css）
6. 配置中文国际化
7. 测试组件基本功能

### Phase 3: 页面集成
8. 更新 BacktestForm 组件
9. 更新 DownloadForm 组件
10. 测试表单提交逻辑
11. 验证数据格式

### Phase 4: 测试更新
12. 更新 E2E 测试
13. 运行完整测试套件
14. 修复发现的问题

### Phase 5: 验证和部署
15. 手动测试所有场景
16. 验证暗色模式兼容性
17. 验证响应式设计
18. 提交代码

## 风险和缓解措施

### 风险 1: 包体积增加
- **风险：** react-datepicker 增加 ~50KB gzipped
- **缓解：** 使用动态导入（dynamic import）延迟加载
- **评估：** 可接受，功能收益大于体积成本

### 风险 2: 样式冲突
- **风险：** react-datepicker 默认样式与 Tailwind 冲突
- **缓解：** 使用 CSS Modules 或自定义类名前缀
- **评估：** 已在设计中解决

### 风险 3: E2E 测试不稳定
- **风险：** 日期选择器 UI 测试可能不稳定
- **缓解：** 使用可靠的 CSS 选择器，添加适当的等待
- **评估：** 需要在实施时注意

### 风险 4: 向后兼容性
- **风险：** 可能影响现有用户习惯
- **缓解：** 保持默认值逻辑不变，提供相似的用户体验
- **评估：** 影响很小

## 性能考虑

1. **按需加载：** 如果包体积成为问题，可以使用 Next.js dynamic import
2. **缓存优化：** date-fns 支持 tree-shaking，只打包使用的函数
3. **渲染优化：** 日期选择器只在用户交互时渲染，不影响初始加载

## 可访问性（A11y）

React DatePicker 提供良好的可访问性支持：
- 键盘导航支持
- ARIA 属性完整
- 屏幕阅读器兼容
- 符合 WCAG 2.1 AA 标准

## 未来扩展

如果将来需要更多功能，可以考虑：
1. **日期范围选择器：** 一次性选择开始和结束日期
2. **快捷选项：** "最近7天"、"本月"、"上月"等快捷按钮
3. **自定义时间间隔：** 允许用户设置时间间隔（15分钟、30分钟、1小时）
4. **时区选择：** 支持多时区选择

## 成功标准

1. ✅ 用户可以选择精确到分钟的开始和结束时间
2. ✅ 界面显示中文，符合用户习惯
3. ✅ 所有现有功能正常工作（数据下载、回测、优化）
4. ✅ E2E 测试全部通过
5. ✅ 无控制台错误或警告
6. ✅ 暗色模式正常显示
7. ✅ 移动端响应式布局正常

## 参考资源

- [React DatePicker 官方文档](https://reactdatepicker.com/)
- [date-fns 文档](https://date-fns.org/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [WCAG 2.1 指南](https://www.w3.org/WAI/WCAG21/quickref/)
