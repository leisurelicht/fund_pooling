# 持仓管理系统 — 前端实施文档

> 状态：前端代码已回退为空壳，等待按本文重新实现 | 更新：2026-11-26（修订 5）
>
> 设计依据见 `fund-holdings-design.md`（页面）与 `fund-holdings-arch-design.md`（接口契约）。
> 本文只写前端怎么落地，不重复为什么这样设计。
>
> 当前代码只保留登录页与服务状态看板（回到持仓功能开发之前的状态）；§二 的目录与 §七 的改造
> 清单是实现目标，不是现状。

---

## 一、当前状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| S1 骨架 | 已完成 | 侧栏、五个路由、六个页面壳、全局样式与色板 |
| S2 总览 | 已完成 | 指标条、持仓表、列设置、记一笔浮层 |
| S3 其他页 | 已完成 | 交易、定投、资产详情、设置，交互可点 |
| S4 对接 | **进行中** | `api/portfolio.ts` 已建，但**类型仍是旧模型**，需要按本文改造 |

代码现状与目标契约的差距集中在四处：类型字段、分页、操作入口、新增的转移与手工价格。下面按文件列出改法。

---

## 二、目录结构

```
frontend/src/
├── api/
│   ├── client.ts              # 已有：fetch + CSRF + 统一错误
│   └── portfolio.ts           # 已有：业务接口，需补分页与新端点
├── composables/
│   ├── useSummary.ts          # 已有：总览 + 60 秒刷新
│   ├── usePositions.ts        # 已有：需改服务端排序 / 分页 / totals
│   ├── useTransactions.ts     # 已有：需补筛选参数与分页
│   ├── useSipPlans.ts         # 已有：需补创建 / 修改 / 结束
│   ├── useChannels.ts         # 已有：需补归档过滤与删除
│   └── useAssetDetail.ts      # 已有：需补价格分组与最近交易
├── components/
│   ├── app/AppTopbar.vue      # 已有：顶部导航、五入口、用户菜单
│   ├── overview/
│   │   ├── AssetCards.vue     # 已有：指标条
│   │   ├── PositionTable.vue  # 已有：需改服务端排序 + totals + 场所/币种
│   │   ├── ColumnSettings.vue # 已有
│   │   └── RecordEntry.vue    # 已有：需加入场所、成交汇率、转移
│   ├── transactions/
│   │   ├── PendingSection.vue # 已有：需分「手动可改可删」与「定投只能作废」
│   │   ├── TransactionTable.vue # 已有：需加操作列、场所、来源筛选、分页
│   │   ├── ConfirmDialog.vue  # 已有：三字段，confirm_date 由服务端写
│   │   ├── TransferForm.vue   # 新增：转移专用表单
│   │   └── Pagination.vue     # 新增：通用分页控件
│   ├── sips/
│   │   ├── SipCard.vue        # 已有：需补下次扣款、累计已投、期次状态
│   │   └── SipForm.vue        # 已有：需补每日频率与顺延策略
│   ├── settings/
│   │   ├── ChannelManager.vue # 已有：需补删除与「定投计划也占用」提示
│   │   ├── DataSource.vue     # 新增：价格/汇率开关、同步状态、手工填汇率
│   │   └── DataDangerZone.vue # 新增：重算快照、清空数据
│   ├── asset/
│   │   ├── AssetDetail.vue    # 已有：需补收盘价/折溢价、价格列表、返回
│   │   └── PriceEditor.vue    # 新增：手工填价格 + 删除回退
│   └── shared/
│       ├── EmptyState.vue     # 已有
│       └── ErrorBanner.vue    # 已有
├── types/portfolio.ts         # 需整体重写（见 §三）
├── router/index.ts            # 已有：七条路由 + 分块失效自动刷新
├── views/                     # 六个页面，见 §七
├── App.vue                    # 已有：顶栏 + 内容区 + 退出登录
└── style.css                  # 已有：slate 色板、涨跌色、侧栏宽度
```

---

## 三、类型定义（目标状态）

```ts
export type Venue = 'exchange' | 'otc'
export type Market = 'CN' | 'US'
export type Currency = 'CNY' | 'USD'
export type PriceKind = 'nav' | 'close' | 'iopv'

export type AssetType = 'stock' | 'mix' | 'bond' | 'index' | 'qdii' | 'fof' | 'money' | 'other'

export interface Asset {
  code: string
  name: string
  type: AssetType
  currency: Currency
  market: Market
  is_listed: boolean
  manager?: string | null
  risk_level?: string | null
  status: 'normal' | 'liquidated' | 'suspended'
}

export interface AssetPrice {
  date: string
  kind: PriceKind
  price: string
  source: 'auto' | 'manual'
}

export type TransactionType =
  | 'buy' | 'sell' | 'cash_dividend' | 'reinvest_dividend'
  | 'share_adjustment' | 'opening_balance' | 'transfer_out' | 'transfer_in'

export interface Transaction {
  id: number
  asset_code: string
  asset_name: string
  asset_type: AssetType
  channel_id: number
  channel_name: string
  venue: Venue
  type: TransactionType
  trade_date: string
  confirm_date?: string | null
  amount: string
  fx_rate: string
  shares?: string | null      // pending 场外买入可为 null
  nav?: string | null
  fee: string
  realized_gain?: string | null
  status: 'pending' | 'confirmed' | 'voided'
  source: 'manual' | 'sip'
  sip_plan_id?: number | null
  transfer_group?: string | null
  notes?: string | null
}

export interface Position {
  asset_code: string
  asset_name: string
  asset_type: AssetType
  channel_id: number | null    // group=asset 合并渠道后为 null
  channel_name: string | null
  venue: Venue
  currency: Currency
  shares: string
  cost_per_share: string       // 原币摊薄单价（含费）
  remaining_cost: string       // CNY
  remaining_cost_original: string
  cost_fx_rate: string
  latest_price: string | null
  price_date: string | null
  market_value: string | null  // CNY
  market_value_original: string | null
  holding_gain: string | null
  holding_gain_pct: string | null
  cumulative_gain_pct: string | null
  realized_gain: string
  holding_days: number
  weight: string
  fee_total: string
}

export interface Summary {
  total_market_value: string
  daily_gain: string | null
  daily_gain_pct: string | null
  total_gain: string
  total_gain_pct: string
  cost_basis: string
  in_transit: string
  holding_days: number
  annualized_return: string | null
  price_as_of: string
  fx_as_of: string | null
  price_missing: number
  fx_missing: number
}

export type SipFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly'

export interface SIPPlan {
  id: number
  asset_code: string
  asset_name: string
  channel_id: number
  channel_name: string
  amount: string
  frequency: SipFrequency
  deduction_day: number | null   // daily 为 null
  on_non_trading: 'postpone' | 'skip' // daily 不适用
  start_date: string
  end_type: 'unlimited' | 'by_count' | 'by_date'
  end_count?: number | null
  end_date?: string | null
  status: 'active' | 'paused' | 'ended'
  next_deduction_date: string | null
  total_invested: string
  due_unconfirmed: number
  last_skip_reason?: string | null
}

export interface Channel {
  id: number
  name: string
  type: 'third_party' | 'bank' | 'broker' | 'direct'
  is_default: boolean
  is_archived: boolean
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PositionTotals {
  count: number
  market_value: string
  remaining_cost: string
  holding_gain: string
  holding_gain_pct: string
  missing_price: number
  missing_fx: number
}

export type PositionsResponse = Paginated<Position> & { totals: PositionTotals }
```

**注意**：金额、份额、价格、汇率全部是字符串；`null` 表示「没有」，不要与 `"0"` 混用。

---

## 四、API 层约定

### 4.1 响应与分页

- 列表统一 `{ count, next, previous, results }`，参数 `page` / `page_size`
- 持仓额外带 `totals`（全量，不随分页变）
- 价格与快照区间接口**不分页**，按 `from` / `to` 一次返回

### 4.2 错误

非 2xx 返回 `{ detail, fields? }`。`client.ts` 已解析 `detail`，新增逻辑：若存在 `fields`，在表单对应字段下展示细分提示，没有则只弹顶部提示条。

### 4.3 幂等

创建交易与转移时生成 `client_request_id`（`crypto.randomUUID()`），提交失败重试复用同一个值；成功后清空。转移请求与普通交易一样带该字段。

### 4.4 请求体

| 操作 | 字段 |
|---|---|
| 记一笔 | `asset_code`、`channel_id`、`venue`、`type`、`trade_date`、`amount`、`shares?`、`nav?`、`fee?`、`fx_rate?`、`sip_plan_id?`、`notes?`、`client_request_id` |
| 转移 | `asset_code`、`from_channel_id`、`from_venue`、`to_channel_id`、`to_venue`、`shares`、`trade_date`、`fee?`、`client_request_id` |
| 确认 | `shares`、`nav`、`fee?`（`confirm_date` 不由前端传） |
| 手工价格 | `date`、`kind`、`price` |
| 手工汇率 | `date`、`base`、`quote`、`rate` |
| 设置 | `price_sync_enabled?`、`fx_sync_enabled?` |

---

## 五、Composable 层

| Composable | 返回 | 要点 |
|---|---|---|
| `useSummary` | `summary`、`error`、`fetch` | 60 秒刷新；`price_as_of` / `fx_as_of` 用于显示新鲜度 |
| `usePositions` | `items`、`totals`、`page`、`ordering`、`includeZero`、`fetch` | 排序与分页全部交给服务端，前端不再本地排序 |
| `useTransactions` | `pending`、`items`、`total`、筛选、`page`、`fetch` | 待确认用 `status=pending` 单独请求 |
| `useSipPlans` | `plans`、`create`、`update`、`setStatus` | 结束后不可恢复；结束时提示未确认交易 |
| `useChannels` | `channels`、`create`、`update`、`remove` | 删除前检查引用，409 时提示改成归档 |
| `useAssetDetail` | `asset`、`prices`（按 kind 分组）、`position`、`recentTransactions` | 一次请求拿全；手工价格写入后局部刷新 |

每个 composable 保留 `loading` 与 `error`；页面用 `ErrorBanner` 展示，列表置空走空状态。不要在前端重算收益。

---

## 六、路由与导航

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录 | 公开 |
| `/` | 总览 | 默认页 |
| `/transactions` | 交易 | 含待确认、流水、分页 |
| `/sips` | 定投 | 计划卡片 |
| `/analysis` | 分析 | 二期占位 |
| `/settings` | 设置 | 渠道、数据源、数据、外观 |
| `/assets/:code` | 资产详情 | 下钻页 |

- 桌面顶部导航五个入口（吸顶、当前页下划线）；移动端顶栏保留 Logo 与用户，入口沉到底部五 tab
- 导航与内容区不再有 160px 的侧栏占位，`.app-main` 不需要左边距
- 资产详情左上角返回按钮，返回时恢复来源页的筛选与滚动位置（用 `router.back()` + 页面缓存，或把筛选写进 query）
- 进入详情时保留来源标识，从交易页进来时返回交易页而不是总览

---

## 七、S4 改造清单

### 7.1 类型与 API

1. 重写 `types/portfolio.ts` 为 §三 的内容
2. `api/portfolio.ts`：所有列表函数返回 `Paginated<T>`；`fetchPositions` 返回 `PositionsResponse`
3. 新增：手工价格 `upsertPrice` / `deletePrice`、手工汇率、`fetchSettings` / `updateSettings`、`fetchSyncResult`、`recalculateSnapshots`、`clearData`、`createTransfer`
4. 请求体按 §4.4 组装；创建类自动带 `client_request_id`

### 7.2 总览

- `usePositions` 改为服务端分页与排序，参数 `ordering`、`include_zero`、`page`
- 合计行直接用服务端 `totals`，不再累加当前页
- 指标条下方显示「价格更新至 · 汇率更新至」；`price_missing` / `fx_missing` 大于 0 时追加提示并可跳设置
- 工具栏加「显示已清仓」开关，对应 `include_zero`
- 表格列加「场所」，外币行价格后标币种；缺价行显示「—」并保留在列表

### 7.3 交易页

- 流水表加「操作」列：手动/场内的待确认给修改、删除、确认；定投生成的只给作废与确认；已确认只给撤销
- 撤销转移弹确认「将同时撤销转出与转入两笔」
- 加「场所」列与来源筛选（定投 / 手动）
- 底部接 `Pagination`；待确认区独立请求，不随流水翻页
- 删除待确认走 `DELETE`；定投生成的按钮文案为「作废」，走 `void`

### 7.4 记一笔与转移

- 表单加「场所」选择；场外买入的份额与价格可留空
- 外币资产显示「成交汇率」，默认当日汇率、可改
- 类型切到「转移」时切换为 `TransferForm`：转出渠道/场所 → 转入渠道/场所 → 份额；
  金额（结转成本）只读展示，由系统算；提交走 `/transactions/transfer/`
- 按类型动态显示字段：现金分红只要金额；红利再投要金额、份额、价格；份额调整只要份额增量

### 7.5 定投

- `SipForm` 周期加「每日」；选每日时隐藏扣款日与「遇非交易日」
- 固定日期型显示「遇非交易日：顺延（默认）/ 跳过」
- `SipCard` 显示下次扣款日、累计已投、到期未确认笔数、上次跳过原因；状态标签区分
  「进行中 / 已暂停 / 已结束」，并按策略显示「顺延至 X」「本期跳过」「本期未执行」
- 编辑走 `PATCH`；「结束」后不可恢复，结束时提示仍未确认的交易

### 7.6 资产详情

- 头部：场外只显示净值；上市资产显示「收盘价 · 净值 · 折溢价」
- 价格区块：区间切换 + 净值/收盘价切换；下方「最近价格」列表带来源（自动 / 手工）与删除
- `PriceEditor`：选日期、填价格；保存后刷新持仓与指标
- 持仓摘要：行内「成本价」原币、合计「持仓成本」CNY，三个收益率并排并标注口径
- 最近交易：默认 10 条，跳交易页时带 `asset` 筛选

### 7.7 设置

- 渠道：新建、设为默认、归档、删除；被定投计划引用的渠道提示「已使用，只能归档」
- 数据源：价格/汇率开关、最后同步时间、失败清单、「立即同步」、手工填汇率（可删除）
- 数据：导出、重算快照（选区间，展示重算与跳过原因）、清空数据（写明范围与确认文案）
- 外观：明暗、绿涨红跌

---

## 八、视觉与交互规范

- 色板与字号沿用现有 `style.css`：slate 灰阶、蓝色主色、涨跌色双向可切
- 数字用 `font-variant-numeric: tabular-nums`；金额千分位两位、份额最多四位、价格四位
- 状态用浅色胶囊标签；来源（定投/手动）用细边框小标签
- 空值统一「—」，不显示 0；缺价与缺汇率在悬浮提示中说明原因
- 涨跌同时用颜色、正负号、方向箭头，不只靠颜色
- 图表系列色避开红绿，用中性色或蓝紫色

---

## 九、验收清单

- [ ] 类型与接口返回一一对应，`npm run type-check` 零报错
- [ ] 持仓翻页后合计不变，与总览数字一致
- [ ] 排序切换走服务端，翻页后顺序稳定
- [ ] 场外买入不填份额可提交，确认后持仓出现
- [ ] 定投待确认只能作废，不会因重跑重复生成
- [ ] 转移提交一次生成两笔，撤销一笔两笔同时撤销
- [ ] 外币行显示原币价格与 CNY 市值，缺汇率时显示「—」并提示
- [ ] 手工价格可写、可删，删除后同步能补回
- [ ] 缺价行计入只数但不计入金额合计，页面有提示
- [ ] 移动端五 tab 与桌面入口一致，资产详情能返回原页

---

## 十、已知问题与踩坑

| 问题 | 处理 |
|---|---|
| 重新部署后旧页面点击导航无反应 | 路由已监听动态模块加载失败，自动刷新一次（`sessionStorage` 防循环） |
| CSRF | 所有写请求走 `client.ts`，不要手写 fetch |
| Decimal 用字符串 | 不要 `parseFloat` 后直接回写，格式化与计算分离 |
| `null` 与 `0` | 用 `value != null` 判断；`0.00` 是合法值 |
| 表格 sticky | 表头 sticky 在 `thead`、合计行 sticky 在 `tfoot`，`tbody` 不设 overflow |
| 60 秒刷新 | 只刷新 summary，不打断正在编辑的表单 |
| 日期 | 全部按 `YYYY-MM-DD` 字符串处理，不构造 `Date` 再格式化，避免时区偏移 |
| 分页与筛选 | 筛选变化时回到第 1 页；页面刷新后保留筛选（写进 query） |

---

## 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-11-25 | 初稿：分步实施、目录、类型、Mock 规划、composable、路由、样式、页面拆解 |
| v2 | 2026-11-25 | 页面与样式完成；移除 mock，composable 直连接口并统一错误提示 |
| v3 | 2026-11-26 | 对齐新契约：类型重写（venue/currency/market/transfer/双池/分页）、S4 改造清单、新增组件（转移、价格编辑、分页、数据源）、移动端五 tab、验收清单更新 |
| v4 | 2026-11-26 | 导航由侧栏改为顶栏，目录与路由说明同步 |
| v5 | 2026-11-26 | 前端代码回退到登录 + 服务状态页，本文改为「待实现」的目标说明 |
