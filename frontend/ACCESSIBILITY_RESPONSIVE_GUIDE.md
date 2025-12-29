# 可访问性和响应式设计指南

本文档描述了 MCP 平台前端应用中实现的可访问性和响应式设计功能。

## 可访问性功能 (Accessibility Features)

### 1. 键盘导航 (Keyboard Navigation) - 需求 10.4

#### 跳转到内容链接 (Skip to Content)
- 位于页面顶部的隐藏链接
- 仅在键盘焦点时可见
- 允许键盘用户跳过导航直接到主内容
- 使用 `#main-content` 锚点

```tsx
<a href="#main-content" className="skip-to-content">
  跳转到主内容
</a>
```

#### 焦点指示器 (Focus Indicators)
- 所有交互元素都有清晰的焦点环
- 使用 `focus-visible` 伪类仅在键盘导航时显示
- 鼠标用户不会看到焦点环
- 自定义焦点样式使用 `.focus-enhanced` 类

```css
.focus-enhanced {
  @apply focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2;
}
```

#### Tab 顺序 (Tab Order)
- 逻辑的 Tab 顺序遵循视觉布局
- 侧边栏导航项按顺序排列
- 表单字段按逻辑顺序排列
- 模态对话框捕获焦点

#### 键盘快捷键
- `Escape` 键关闭模态对话框和下拉菜单
- `Enter` 键激活按钮和链接
- 箭头键在菜单中导航（由 Radix UI 提供）

### 2. ARIA 标签和语义 HTML (ARIA Labels & Semantic HTML) - 需求 10.5

#### 语义 HTML 元素
- `<header>` 用于页面头部
- `<nav>` 用于导航区域
- `<main>` 用于主要内容
- `<footer>` 用于页脚
- `<section>` 用于内容分组
- `<article>` 用于独立内容

#### ARIA 标签
所有交互元素都有适当的 ARIA 标签：

```tsx
// 按钮
<Button aria-label="打开菜单">
  <Menu />
</Button>

// 导航
<nav aria-label="主导航">
  <ul role="list">
    <li>
      <Link aria-current="page">仪表板</Link>
    </li>
  </ul>
</nav>

// 区域
<section aria-labelledby="stats-heading">
  <h2 id="stats-heading" className="sr-only">统计概览</h2>
</section>
```

#### 动态内容更新通知

使用 `LiveRegion` 组件和 `useAnnouncer` hook 向屏幕阅读器宣布动态更新：

```tsx
import { useAnnouncer } from '@/components/common';

function MyComponent() {
  const announce = useAnnouncer();
  
  useEffect(() => {
    if (dataLoaded) {
      announce('数据已加载');
    }
  }, [dataLoaded]);
}
```

#### 屏幕阅读器专用内容

使用 `.sr-only` 类隐藏视觉内容但保持屏幕阅读器可访问：

```tsx
<h2 className="sr-only">统计概览</h2>
```

#### 图标的 ARIA 处理
- 装饰性图标使用 `aria-hidden="true"`
- 功能性图标有文本标签或 `aria-label`

```tsx
<Icon className="h-5 w-5" aria-hidden="true" />
<span>文本标签</span>
```

### 3. 颜色对比 (Color Contrast)
- 文本对比度至少 4.5:1（WCAG AA 标准）
- 大文本对比度至少 3:1
- 使用 shadcn/ui 的主题系统确保对比度
- 支持深色模式

### 4. 表单可访问性
- 所有表单字段都有关联的标签
- 错误消息与字段关联
- 必填字段标记清晰
- 使用 `aria-invalid` 和 `aria-describedby`

```tsx
<Input
  id="email"
  aria-invalid={!!errors.email}
  aria-describedby={errors.email ? "email-error" : undefined}
/>
{errors.email && (
  <p id="email-error" className="text-destructive">
    {errors.email.message}
  </p>
)}
```

## 响应式设计 (Responsive Design)

### 1. 断点 (Breakpoints) - 需求 10.1, 10.2, 10.3

应用使用 Tailwind CSS 的默认断点：

- **Mobile**: < 640px (sm)
- **Tablet**: 640px - 1023px (md)
- **Desktop**: ≥ 1024px (lg)

### 2. 响应式布局组件

#### ResponsiveContainer
提供一致的响应式内边距和最大宽度：

```tsx
<ResponsiveContainer maxWidth="xl" padding="md">
  {children}
</ResponsiveContainer>
```

#### ResponsiveGrid
响应式网格布局：

```tsx
<ResponsiveGrid 
  cols={{ mobile: 1, tablet: 2, desktop: 4 }}
  gap="md"
>
  {items.map(item => <Card key={item.id} {...item} />)}
</ResponsiveGrid>
```

#### ResponsiveStack
垂直堆叠，桌面端可选水平：

```tsx
<ResponsiveStack direction="horizontal-on-desktop" spacing="lg">
  <div>左侧内容</div>
  <div>右侧内容</div>
</ResponsiveStack>
```

### 3. 响应式 Hooks

#### useMediaQuery
检测媒体查询匹配：

```tsx
const isMobile = useMediaQuery('(max-width: 768px)');
```

#### 预定义断点 Hooks
```tsx
const isMobile = useIsMobile();      // < 640px
const isTablet = useIsTablet();      // 640px - 1023px
const isDesktop = useIsDesktop();    // ≥ 1024px
const breakpoint = useBreakpoint();  // 'mobile' | 'tablet' | 'desktop'
```

### 4. 响应式文本大小

使用响应式文本工具类：

```tsx
<h1 className="text-responsive-2xl">标题</h1>
<p className="text-responsive-base">正文</p>
```

### 5. 触摸目标 (Touch Targets)

所有交互元素至少 44x44px（WCAG 2.1 AA）：

```tsx
<Button className="touch-target">点击</Button>
```

### 6. 移动优先设计

- 默认样式针对移动设备
- 使用 `md:` 和 `lg:` 前缀添加更大屏幕的样式
- 侧边栏在移动设备上可折叠
- 表格在小屏幕上可滚动

### 7. 响应式间距

```tsx
<div className="space-responsive">
  {/* 移动: 16px, 平板: 24px, 桌面: 32px */}
</div>

<div className="gap-responsive">
  {/* 响应式网格间距 */}
</div>
```

### 8. 视口配置

在 `index.html` 中确保正确的视口设置：

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

## 测试指南

### 可访问性测试

1. **键盘导航测试**
   - 使用 Tab 键浏览整个应用
   - 确保所有交互元素可访问
   - 验证焦点指示器可见
   - 测试 Escape 键关闭对话框

2. **屏幕阅读器测试**
   - 使用 NVDA (Windows) 或 VoiceOver (Mac)
   - 验证所有内容可读
   - 测试动态内容更新通知
   - 检查 ARIA 标签

3. **自动化测试**
   - 使用 axe-core 进行自动化测试
   - 在 CI/CD 中集成可访问性检查

### 响应式设计测试

1. **浏览器开发工具**
   - 使用 Chrome DevTools 的设备模式
   - 测试所有断点
   - 验证触摸目标大小

2. **真实设备测试**
   - 在实际移动设备上测试
   - 测试不同屏幕尺寸
   - 验证触摸交互

3. **文本缩放测试**
   - 将浏览器文本大小增加到 200%
   - 确保布局不会破坏
   - 验证内容仍然可读

## 最佳实践

### 可访问性
1. 始终为图像提供 alt 文本
2. 使用语义 HTML 元素
3. 确保颜色对比度充足
4. 提供键盘替代方案
5. 测试屏幕阅读器兼容性

### 响应式设计
1. 移动优先开发
2. 使用相对单位（rem, em）
3. 测试所有断点
4. 优化触摸交互
5. 考虑性能影响

## 相关文件

- `frontend/src/index.css` - 全局样式和工具类
- `frontend/src/components/common/LiveRegion.tsx` - 动态内容通知
- `frontend/src/components/layout/ResponsiveContainer.tsx` - 响应式布局组件
- `frontend/src/hooks/useMediaQuery.ts` - 响应式 hooks
- `frontend/src/components/layout/AppLayout.tsx` - 主布局
- `frontend/src/components/layout/Sidebar.tsx` - 侧边栏
- `frontend/src/components/layout/Header.tsx` - 头部

## 验证需求

此实现验证以下需求：

- **需求 10.1**: 桌面布局优化
- **需求 10.2**: 平板布局优化
- **需求 10.3**: 移动布局优化
- **需求 10.4**: 键盘导航支持
- **需求 10.5**: ARIA 标签和语义 HTML

## 未来改进

1. 添加更多键盘快捷键
2. 实现焦点陷阱管理
3. 添加高对比度模式
4. 支持更多语言的屏幕阅读器
5. 实现更细粒度的响应式断点
