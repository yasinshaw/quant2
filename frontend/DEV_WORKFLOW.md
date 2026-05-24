# 开发工作流程指南

## 资源刷新问题解决方案

### 问题症状
- 修改代码后页面没有更新
- 样式更改不生效
- 需要手动刷新浏览器多次才能看到变化

### 解决方案

#### 1. 快速修复命令

```bash
# 完全清理并重启（推荐）
./scripts/dev-refresh.sh

# 或者手动执行
pnpm run dev:clean
```

#### 2. 开发命令

```bash
# 标准开发服务器
pnpm dev

# 使用Turbo模式（更快的HMR）
pnpm dev:turbo

# 完全清理后启动
pnpm dev:clean
```

#### 3. 自动刷新配置

项目已优化以下配置确保资源及时更新：

**Next.js配置 (next.config.js)**
- ✅ 文件监听轮询：每秒检查一次变化
- ✅ 延迟构建：300ms聚合变化后重新构建
- ✅ 忽略node_modules：提高性能

**React Query配置 (lib/QueryProvider.tsx)**
- ✅ 数据新鲜度：10秒内自动重新获取
- ✅ 窗口聚焦刷新：切换回标签页时自动更新
- ✅ 合理缓存时间：5分钟

### 最佳实践

#### 开发时
1. **启动服务器**：使用 `pnpm dev` 或 `./scripts/dev-refresh.sh`
2. **文件保存后**：
   - CSS/样式：立即生效（< 1秒）
   - 组件文件：HMR自动更新（< 2秒）
   - API文件：可能需要手动刷新页面
3. **如果更新不生效**：
   - 先等待2-3秒
   - 如果还不行，按 `Cmd+R` (Mac) 或 `Ctrl+R` (Windows/Linux)
   - 最后手段：运行 `./scripts/dev-refresh.sh`

#### 修改API或配置后
```bash
# 总是完全清理并重启
./scripts/dev-refresh.sh
# 选择选项 1
```

#### 修改依赖后
```bash
pnpm install
./scripts/dev-refresh.sh
```

### 浏览器开发技巧

1. **禁用缓存**（开发时）
   - 打开DevTools
   - Network标签
   - 勾选 "Disable cache"
   - 保持DevTools打开状态

2. **硬刷新**（当常规刷新无效时）
   - Mac: `Cmd+Shift+R`
   - Windows/Linux: `Ctrl+Shift+R`

3. **清除浏览器缓存**
   ```javascript
   // 在浏览器控制台运行
   location.reload(true);
   ```

### 常见问题

**Q: 为什么有时需要手动刷新？**
A: 某些深层更改（如路由配置、next.config.js）需要完整重启服务器。

**Q: Turbo模式有什么用？**
A: 使用Turbopack提供更快的HMR（热模块替换），大项目提速明显。

**Q: 什么时候需要完全清理？**
A: 出现以下情况时：
   - 构建错误无法修复
   - 样式完全不更新
   - 修改配置后无效果
   - 安装新依赖后

**Q: 清理缓存会删除我的数据吗？**
A: 不会。只删除：
   - `.next/` - Next.js构建缓存
   - `node_modules/.cache` - 工具缓存
   - `.turbo/` - Turbopack缓存

### 性能优化提示

**默认配置已优化：**
- 文件监听使用轮询（稳定但略耗CPU）
- 2核以上CPU可降低轮询间隔（修改next.config.js中的poll值）

**低配设备：**
```javascript
// next.config.js
poll: 2000, // 改为2秒检查一次
```

**高配设备：**
```javascript
poll: 500, // 改为500ms检查一次（更快）
```

### 故障排除清单

- [ ] 运行了 `./scripts/dev-refresh.sh`
- [ ] 浏览器DevTools已禁用缓存
- [ ] 使用了硬刷新（Cmd+Shift+R）
- [ ] 检查终端是否有构建错误
- [ ] 确认修改的是正确的文件
- [ ] 尝试重启浏览器
- [ ] 检查防火墙/代理是否阻止热重载

### 附加工具

**查看构建状态：**
- 终端输出会显示编译进度
- 浏览器控制台查看HMR日志

**手动触发重新构建：**
- 在终端中按 `Ctrl+C` 停止服务器
- 重新运行 `pnpm dev`

---

**最后更新：** 2025-03-27
**维护者：** 开发团队
