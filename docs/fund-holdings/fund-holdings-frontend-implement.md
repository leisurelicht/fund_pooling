# 持仓管理系统 — 前端实施文档

> 状态：页面与样式已完成，Mock 已移除 | 更新：2026-11-25（修订 2）
>
> 页面结构、样式、交互已完成；数据层改为直接调用 `/api` 接口。后端未实现前，
> 页面显示空状态并在顶部提示接口错误。
>
> **注意：本文的类型定义与接口签名已落后于数据模型**（缺 currency / is_listed / venue /
> transfer_group / 转移类型 / 分页 / 双池成本字段）。以后端接口对接时一起更新，不要照本文
> 直接改类型。

---

## 一、实施策略

分四步走，每步产出可独立验证的页面：

| 步骤 | 内容 | 验收 |
|---|---|---|
| S1 骨架 | 左侧导航 + 路由 + 所有页面空壳 + 全局样式 | 五个导航项可切换，页面不报错 |
| S2 总览页 | 资产卡片 + 持仓表格 + 工具栏 + 列设置 | Mock 数据渲染正确，排序/列切换/视图切换可用 |
| S3 其他页面 | 交易页、定投页、资产详情页、设置页 | 各自交互可用，数据为 mock |
| S4 对接 | composable 层替换为真实 API | 逐页切换，旧 mock 保留作为 fallback |

---

## 二、目录结构

```
frontend/src/
├── api/
│   ├── client.ts              # 已有，不变
│   ├── auth.ts                # 已有，不变
│   ├── system.ts              # 已有，不变
│   └── portfolio.ts           # 新增：所有业务接口
├── auth/
│   └── session.ts             # 已有，不变
├── composables/
│   ├── usePositions.ts        # 新增：持仓数据 + 视图切换 + 排序
│   ├── useTransactions.ts     # 新增：交易流水 + 待确认
│   ├── useSipPlans.ts         # 新增：定投计划
│   ├── useSummary.ts          # 新增：总览头部数字
│   ├── useChannels.ts         # 新增：渠道管理
│   └── useAssetDetail.ts      # 新增：资产详情
├── components/
│   ├── app/
│   │   ├── AppSidebar.vue     # 新增：左侧导航
│   │   └── AppLayout.vue      # 新增：侧栏 + 内容区壳
│   ├── overview/
│   │   ├── AssetCards.vue     # 新增：资产卡片区
│   │   ├── PositionTable.vue  # 新增：持仓表格
│   │   ├── ColumnSettings.vue # 新增：列设置弹出面板
│   │   └── RecordEntry.vue    # 新增：记一笔浮层
│   ├── transactions/
│   │   ├── PendingSection.vue # 新增：待确认区
│   │   ├── TransactionTable.vue # 新增：流水表
│   │   └── ConfirmDialog.vue  # 新增：确认弹窗
│   ├── sips/
│   │   ├── SipCard.vue        # 新增：定投计划卡片
│   │   └── SipForm.vue        # 新增：新建/编辑计划表单
│   ├── settings/
│   │   └── ChannelManager.vue # 新增：渠道管理
│   ├── asset/
│   │   └── AssetDetail.vue    # 新增：资产详情内容
│   └── shared/
│       ├── EmptyState.vue     # 新增：空状态占位
│       └── ErrorBanner.vue    # 新增：异常提示条
├── mock/
│   ├── positions.ts           # 新增：持仓假数据
│   ├── transactions.ts        # 新增：交易假数据
│   ├── summary.ts             # 新增：总览假数据
│   ├── sips.ts                # 新增：定投假数据
│   ├── channels.ts            # 新增：渠道假数据
│   └── assets.ts              # 新增：资产详情假数据
├── router/
│   └── index.ts               # 已有，加新路由
├── types/
│   ├── appleid.d.ts           # 已有，不变
│   ├── google.d.ts            # 已有，不变
│   └── portfolio.ts           # 新增：业务类型定义
├── views/
│   ├── HomeView.vue           # 改为总览页（重写）
│   ├── LoginView.vue          # 已有，不变
│   ├── TransactionsView.vue   # 新增
│   ├── SipsView.vue           # 新增
│   ├── AnalysisView.vue       # 新增（空壳）
│   ├── SettingsView.vue       # 新增
│   └── AssetDetailView.vue    # 新增
├── App.vue                    # 重写：AppLayout 替换旧顶栏
├── main.ts                    # 已有，不变
└── style.css                  # 已有，增量加变量
```

---

## 三、类型定义

`types/portfolio.ts`：

```ts
// 资产类型
export type AssetType = 'fund' | 'stock' | 'bond' | 'money' | 'index' | 'qdii' | 'fof' | 'other'

export interface Asset {
  code: string
  name: string
  type: AssetType
  manager?: string
  risk_level?: string
  status: 'normal' | 'liquidated' | 'suspended'
}

// 价格
export interface AssetPrice {
  price: number          // 单位净值 / 收盘价
  acc_price?: number     // 累计净值（仅基金）
  daily_change?: number  // 日涨跌幅，小数（0.0123 = 1.23%）
  date: string           // YYYY-MM-DD
  source: 'auto' | 'manual'
}

// 渠道
export type ChannelType = 'third_party' | 'bank' | 'broker' | 'direct'

export interface Channel {
  id: number
  name: string
  type: ChannelType
  is_default: boolean
  is_archived: boolean
}

// 交易
export type TransactionType = 'buy' | 'sell' | 'cash_dividend'
  | 'reinvest_dividend' | 'share_adjustment' | 'opening_balance'

export type TransactionStatus = 'pending' | 'confirmed' | 'voided'

export type TransactionSource = 'manual' | 'import_csv' | 'sip'

export interface Transaction {
  id: number
  asset_code: string
  asset_name: string
  asset_type: AssetType
  channel_id: number
  channel_name: string
  type: TransactionType
  trade_date: string
  confirm_date?: string
  amount: string        // 正数金额
  shares: string        // 份额
  nav: string           // 成交价
  fee: string
  status: TransactionStatus
  source: TransactionSource
  notes?: string
}

// 持仓行
export interface Position {
  asset_code: string
  asset_name: string
  asset_type: AssetType
  channel_name: string
  shares: string
  cost_per_share: string   // 摊薄成本单价
  remaining_cost: string   // 剩余成本
  latest_price: string
  price_date: string
  market_value: string
  holding_gain: string
  holding_gain_pct: string
  realized_gain: string
  holding_days: number
  weight: string
  fee_total: string
}

// 总览头部
export interface Summary {
  total_market_value: string
  daily_gain: string
  daily_gain_pct: string
  total_gain: string
  total_gain_pct: string
  cost_basis: string
  in_transit: string
  holding_days: number
  price_updated_at: string
}

// 定投计划
export type SIPFrequency = 'weekly' | 'biweekly' | 'monthly'
export type SIPStatus = 'active' | 'paused' | 'ended'

export interface SIPPlan {
  id: number
  asset_code: string
  asset_name: string
  channel_id: number
  channel_name: string
  amount: string
  frequency: SIPFrequency
  deduction_day: number
  start_date: string
  end_type: 'unlimited' | 'by_count' | 'by_date'
  end_count?: number
  end_date?: string
  status: SIPStatus
  next_deduction_date?: string
  total_invested: string
}
```

---

## 四、数据来源

**不再保留 Mock 数据**。所有 composable 直接调用 `api/portfolio.ts` 里的接口，
接口未实现时由 composable 捕获错误并置空列表，页面渲染空状态 + 顶部错误提示条。

之所以删掉假数据：假数据会掩盖接口契约问题（字段名、空值、分页、错误码），
页面在「永远有数据」的状态下开发，等真接口接上才发现对不上。

## 五、Composable 层

每个 composable 负责「请求 → 错误处理 → 派生计算」，接口签名统一：

```ts
// 模式一：返回 reactive 数据 + 操作方法
export function usePositions() {
  const positions = ref<Position[]>([])
  const viewMode = ref<'by_asset' | 'by_channel'>('by_asset')
  const sortKey = ref<string>('market_value')
  const sortOrder = ref<'asc' | 'desc'>('desc')
  const visibleColumns = ref<Set<string>>(new Set(DEFAULT_COLUMNS))

  const sorted = computed(() => { /* 排序 + 过滤 */ })
  const totals = computed(() => { /* 合计行 */ })

  function toggleColumn(key: string) { }
  function setSort(key: string) { }
  function fetch() { /* S4: API 替换 */ }

  return { positions, viewMode, sorted, totals, visibleColumns, toggleColumn, setSort, fetch }
}

// 模式二：直接返回数据 + refresh
export function useSummary() {
  const summary = ref<Summary | null>(null)
  const loading = ref(false)
  async function fetch() { /* mock → API */ }
  return { summary, loading, fetch }
}
```

全局共享策略：每个页面独立创建 composable 实例，不跨页面共享（避免页面间无关的状态污染）。

---

## 六、路由

`router/index.ts` 新增路由：

```ts
const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/', name: 'Overview', component: () => import('@/views/HomeView.vue') },
  { path: '/transactions', name: 'Transactions', component: () => import('@/views/TransactionsView.vue') },
  { path: '/sips', name: 'Sips', component: () => import('@/views/SipsView.vue') },
  { path: '/analysis', name: 'Analysis', component: () => import('@/views/AnalysisView.vue') },
  { path: '/settings', name: 'Settings', component: () => import('@/views/SettingsView.vue') },
  { path: '/assets/:code', name: 'AssetDetail', component: () => import('@/views/AssetDetailView.vue') },
]
```

登录守卫不变。`/login` 保持为公开页，其余全部要求登录。

---

## 七、样式策略

**增量改，不重写**。现有 `style.css` 已有完整的 CSS 变量体系（`--bg`、`--surface`、`--accent`、`--ok`、`--error` 及深色模式），新增变量不改旧变量：

```css
:root {
  --up: #ef4444;        /* 涨（红涨绿跌默认） */
  --up-soft: rgba(239, 68, 68, 0.12);
  --down: #12b76a;      /* 跌 */
  --down-soft: rgba(18, 183, 106, 0.12);
  --sidebar-width: 200px;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;
}
```

绿涨红跌开关通过切换 CSS 类实现（`:root.green-up { --up / --down 互换 }`），存 localStorage。

**组件样式**：写在 `<style scoped>` 里，复用 CSS 变量。不使用 Tailwind/UI 框架，保持现有纯 CSS 路线。

---

## 八、S1：骨架搭建

### 8.1 AppLayout.vue

替换当前 `App.vue` 中的顶栏布局。结构：

```html
<div class="app-layout">
  <AppSidebar />
  <main class="app-main">
    <router-view />
  </main>
</div>
```

侧栏固定宽度 `var(--sidebar-width)`，内容区 `flex: 1`，背景色 `var(--bg)`。无顶栏——用户头像和菜单放在侧栏底部、内容区右上角。

### 8.2 AppSidebar.vue

从上到下三段：

1. **Logo 区**：圆角方块 + 系统名称「Fund Pooling」（沿用 `App.vue` 里的 brand 样式）
2. **导航项**：五个 `<router-link>`，当前页高亮（`router-link-active`）
3. **用户区**：头像（首字母圆形）+ 用户名 + 下拉菜单（设置、退出登录）

每个导航项 = Emoji 图标 + 文字。高亮态用 `--accent-soft` 背景 + `--accent` 左边框。

### 8.3 所有 View 空壳

每个 View 文件 = `<template>` + 标题 + `<script setup>` 空壳。分析页额外显示「分析功能将在后续版本上线」的 EmptyState。

### 8.4 旧代码改动

- `App.vue`：删除旧顶栏，改挂 `AppLayout`
- `HomeView.vue`：删除旧健康检查内容，改为空壳（S2 重写）
- `style.css`：去掉 `.app`（替换为 `.app-layout`）、保留 `.topbar` / `.brand` 供侧栏复用

---

## 九、S2：总览页

### 9.1 AssetCards.vue

6 个数字卡片，水平排列（flex wrap）。每个卡片：标签 + 数字（大号）+ 颜色（涨红跌绿）。

涨跌数字同时带颜色、`+/-` 符号和箭头 `↑↓`。

底部灰色小字「更新于 HH:MM:SS」，60 秒自动拉一次 `useSummary().fetch()`。

### 9.2 PositionTable.vue

标准 `<table>`，渲染 `usePositions().sorted`。

- **表头**：固定（sticky top），每列可点击排序。当前排序列显示 `▲` 或 `▼`
- **表体**：数字列 `text-align: right`，字体等宽（`--font-mono`）。涨/跌用颜色 + 符号
- **合计行**：sticky bottom，数据来自 `usePositions().totals`
- **行点击**：`router.push('/assets/' + row.asset_code)`
- **空状态**：无数据时渲染 EmptyState 组件

### 9.3 ColumnSettings.vue

弹出面板（`position: absolute`，从工具栏「列设置」按钮下方弹出）。

列出所有可用列，每行一个 `<label><input type="checkbox">`，绑定 `visibleColumns`。底部「重置」按钮恢复默认 8 列。

拖拽排序用原生 `dragstart/dragover/drop` 事件，排完后更新 `visibleColumns` 的存储顺序。顺序写 localStorage，下次打开保持。

### 9.4 视图切换

工具栏两个 `<button>`：「按资产」「按渠道」。切换 `viewMode`。按渠道视图时表格多一列「渠道」，资产同名合并仅在按资产视图生效。渠道列在按渠道视图中移到资产列之后。

### 9.5 RecordEntry.vue（记一笔浮层）

挂载在 `App.vue` 层，用 `<Teleport to="body">`。全屏半透明遮罩 + 居中白色面板。

表单分两段：类型选择（初始持仓 / 买入 / 卖出 / 分红 / 红利再投 / 份额调整）→ 根据类型动态显示字段。初始持仓时隐藏价格字段、成本标签改为「累计投入」、额外显示「已实现收益」字段。

提交逻辑：S3 阶段 console.log，S4 调 API。提交后关闭浮层，刷新持仓数据。

---

## 十、S3：其他页面

### 10.1 交易页 TransactionsView.vue

三个区域：`PendingSection` + 筛选栏 + `TransactionTable`。

**PendingSection**：遍历 `useTransactions().pending`，每条一行 + 确认按钮。点击确认弹出 `ConfirmDialog`。

**ConfirmDialog**：显示资产、类型、金额，三个可编辑字段（份额、净值、手续费），灰色参考值（定投时从计划推、手动时空白）。确认后调 confirm API，本地列表即时移除该条。

**CsvImport**：拖拽区 + 比对结果列表。比对结果分三类：匹配（绿色 ✓ 跳过）、新增（蓝色 + 将导入）、冲突（橙色 ⚠ 二选一）。用户逐条解决冲突后点「导入 N 条」。

### 10.2 定投页 SipsView.vue

`SipCard` 网格（2 列），每张卡片展示：资产名称、渠道、每期金额、周期描述、下次扣款日、累计已投、状态点（绿/黄/灰 = active/paused/ended）。

操作按钮按状态变化：active → [暂停] [修改] [结束]；paused → [恢复] [修改] [结束]；ended → 只读。

新建/编辑用 `SipForm` 浮层：资产搜索、渠道选择、金额、周期（每周/biweekly/每月）、扣款日（月选 1–28 日、周选周几）、开始日期、结束条件。

### 10.3 资产详情页 AssetDetailView.vue

路由参数 `code` → `useAssetDetail(code)`。四个区域：

1. 资产头部：名称 + 类型 + 风险等级 + 最新价格 + 日期
2. 我的持仓：按渠道分行 + 合计行（来源 usePositions 按 code + channel 过滤）
3. 净值走势：折线图（SVG 手写或轻量 chart 库，S3 阶段可用纯 CSS）
4. 交易时间线：按日期倒序，最近 10 条，底部「查看全部 →」跳转交易页并预填资产筛选

### 10.4 设置页 SettingsView.vue

**ChannelManager**：表格（名称、类型、默认、归档），行操作（设为默认、归档/取消归档、编辑名称）。新建弹窗：名称 + 类型下拉。

**价格源区**：开关 + 最后同步时间 + 手动同步按钮。按钮点击后有加载态 + 结果提示（成功 N 只 / 失败 M 只）。

**外观区**：明/暗/跟随系统三选一 radio。绿涨红跌 toggle 开关。

**数据区**：数据导出按钮、清空数据入口（二次确认 + 输入文本确认）。

### 10.5 EmptyState 与 ErrorBanner

`EmptyState`：居中显示图标 + 标题 + 描述 + 可选操作按钮。各页面按空状态表渲染不同文案。

`ErrorBanner`：固定顶部提示条，黄色背景，可关闭。用于价格同步失败等全局提醒。

---

## 十一、S4：对接后端（前端侧已完成）

前端侧已完成对接：每个 composable 的 `fetch()` 调用 `api/portfolio.ts` 对应函数，
捕获 `ApiError` 写入 `error`，页面用 `ErrorBanner` 展示，列表置空走空状态。

后端就绪后不需要再改前端，只需让接口返回约定结构：列表统一 `{ results: [...] }`，
总览与详情返回单个对象。

---

## 十二、踩坑预警

1. **CSRF**：所有 POST/PATCH/DELETE 请求走 `client.ts` 统一封装，自动带 `X-CSRFToken`。不要手写 fetch。
2. **数字格式化**：金额千分位用 `Intl.NumberFormat('zh-CN')`，份额/净值保留 4 位小数用 `toLocaleString`。所有格式化逻辑抽到 `utils/format.ts`，不在模板里写。
3. **空值 vs 0**：后端可能返回 `null`（无净值）或 `"0.0000"`（零份额），模板中统一判断 `value != null` 而非 `value`。空值显示「—」，0 显示 `0.00`。
4. **表头 sticky 与 overflow**：`position: sticky` 在 `<table>` 上需要 th/td 配合。表头的 sticky top 与合计行的 sticky bottom 分别在 thead 和 tfoot 上实现，tbody 不要设 overflow（用页面级滚动）。
5. **侧栏宽度与固定**：侧栏用 `position: fixed` + `overflow-y: auto`，内容区 `margin-left: var(--sidebar-width)`，不走 flex 布局（避免内容区随侧栏内容变长而偏移）。
6. **移动端降级**：用 CSS media query `max-width: 768px` 触发。侧栏变为底部导航栏（`position: fixed; bottom: 0`），表格用 `display: block` 逐行折叠为卡片。S3 阶段只做 CSS 降级，不做独立的移动端组件。
7. **深色模式**：所有新增组件颜色使用 CSS 变量，不做硬编码色值。涨跌色变量在 `.green-up` 类下互换。