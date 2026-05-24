# 样式问题快速修复指南

## 🎯 常见样式问题及解决方案

### 问题1：修改后样式没有更新

**快速修复：**
```bash
# 使用快速修复脚本
./scripts/quick-fix.sh
```

**手动步骤：**
```bash
# 1. 停止开发服务器（如果正在运行）
# Ctrl+C 或
lsof -ti:3002 | xargs kill -9

# 2. 清理缓存
rm -rf .next
rm -rf node_modules/.cache

# 3. 重新启动
pnpm dev
```

### 问题2：Ant Design组件样式缺失

**症状：**
- DatePicker没有样式
- 按钮看起来很原始
- Toast消息没有显示

**解决方案：**

1. **检查layout.tsx配置：**
```tsx
import { App } from 'antd'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <App>  {/* ← 必须有这个 */}
          {children}
        </App>
      </body>
    </html>
  )
}
```

2. **检查globals.css：**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  .ant-btn {
    @apply transition-colors duration-200;
  }
}
```

### 问题3：Toast消息不显示

**检查清单：**
- [ ] `lib/toast.ts` 文件存在
- [ ] `layout.tsx` 中导入了 `initToast`
- [ ] `layout.tsx` 用 `<App>` 组件包裹
- [ ] 组件中导入了 `toast` 并使用 `toast.error()`

**修复示例：**
```tsx
import { toast } from '@/lib/toast'

// ❌ 错误
alert('错误消息')

// ✅ 正确
toast.error('错误消息')
```

### 问题4：Dark Mode样式不正确

**检查Tailwind配置：**
```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class', // 或 'media'
  // ...
}
```

**检查globals.css：**
```css
/* 必须有这些基础样式 */
body {
  @apply text-slate-900 bg-slate-50;
}

.dark body {
  @apply text-slate-100 bg-slate-900;
}
```

## 🛠️ 诊断工具

### 检查构建状态
```bash
pnpm build
```
查看是否有错误或警告。

### 检查浏览器控制台
1. 打开DevTools (F12)
2. 查看Console标签的错误
3. 查看Network标签是否有404

### 检查React DevTools
1. 安装React DevTools扩展
2. 检查组件树
3. 查看props和state

### 检查样式加载
在浏览器控制台运行：
```javascript
// 检查antd样式
console.log(document.querySelector('.ant-btn'))

// 检查Tailwind
console.log(document.documentElement.classList)

// 检查CSS加载
Array.from(document.styleSheets).forEach(sheet => {
  console.log(sheet.href)
})
```

## 🚀 最佳实践

### 开发时
1. **启动服务器**：`pnpm dev`
2. **打开DevTools**：禁用缓存
3. **保存文件**：等待HMR自动刷新
4. **如没更新**：硬刷新（Cmd+Shift+R）

### 提交代码前
```bash
# 1. 清理并构建
pnpm build

# 2. 检查构建输出
# 确保没有错误

# 3. 本地测试
pnpm dev
# 测试所有页面和功能
```

### 修改配置后
```bash
# 总是完全清理
./scripts/quick-fix.sh
```

## 📋 问题检查清单

遇到样式问题时，按顺序检查：

**基础检查：**
- [ ] 开发服务器正在运行
- [ ] 浏览器访问 http://localhost:3002
- [ ] 控制台没有错误
- [ ] 网络面板没有404

**配置检查：**
- [ ] `layout.tsx` 包含 `<App>` 组件
- [ ] `globals.css` 包含 Tailwind 指令
- [ ] `tailwind.config.js` 正确配置
- [ ] `next.config.js` 正确配置

**代码检查：**
- [ ] 组件正确导入样式
- [ ] 使用 `toast` 而不是 `alert`
- [ ] className 拼写正确
- [ ] 没有CSS冲突

**缓存检查：**
- [ ] 清理了 `.next` 目录
- [ ] 清理了浏览器缓存
- [ ] 硬刷新了页面

## 🔍 调试技巧

### 1. 添加调试边框
```css
/* globals.css */
* {
  outline: 1px solid red !important;
}
```
看到所有元素的边框，帮助定位问题。

### 2. 检查CSS优先级
在DevTools中：
1. 右键元素 → 检查
2. 查看Styles面板
3. 看哪些CSS被应用，哪些被覆盖

### 3. 强制重新加载
```javascript
// 控制台运行
window.location.reload(true)
```

### 4. 清除所有缓存
```bash
# 完全清理
rm -rf .next node_modules/.cache .turbo
rm -rf node_modules
pnpm install
pnpm dev
```

## 🆘 紧急恢复

如果什么都不行，最后手段：

```bash
# 1. 备份当前更改
git add .
git commit -m "备份：样式修复前"

# 2. 重置到上一个工作版本
git reset --hard HEAD~1

# 3. 重新应用更改
# （手动重新做你的修改）

# 4. 测试
pnpm dev
```

## 📞 获取帮助

如果问题仍然存在：
1. 检查终端输出
2. 检查浏览器控制台
3. 运行 `pnpm build` 查看详细错误
4. 查看 `DEV_WORKFLOW.md` 获取更多帮助

---

**最后更新：** 2025-03-27
