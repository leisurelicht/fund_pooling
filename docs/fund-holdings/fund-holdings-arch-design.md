# 持仓管理系统 — 架构设计

> 状态：设计稿（未实现） | 更新：2026-11-25（修订 23）
>
> 本文只记录思路与设计，不贴代码。

---

## 一、目标与边界

做一本**自用的资产账本**（基金 + 未来扩展至股票）：只录交易流水，持仓、成本、收益全部
自动得出。

**做**：记账、持仓、收益口径、净值/价格同步、定投计划。

**不做**：行情 K 线、下单交易、社交分享、多用户协作、货币基金（一期）。

---

## 二、架构

| 层 | 职责 |
|---|---|
| Vue SPA | 展示、录入交互、数字格式化，不参与收益计算 |
| DRF 接口 | 鉴权、参数校验、序列化、筛选分页 |
| 领域计算（纯函数） | 份额重放、摊薄成本、收益与收益率 |
| PostgreSQL | Asset、AssetPrice、Channel、Transaction、SIPPlan、DailySnapshot |

全部业务模型放在一个 app `apps/portfolio` 下。

| 模型 | 职责 | 带用户外键 |
|---|---|---|
| Asset | 资产代码、名称、类型、计价币种、是否上市 | 否 |
| AssetPrice | 每只资产每个自然日、每种价格类型（净值 / 收盘价 / IOPV）的原币价格 | 否 |
| FxRate | 每日汇率，用于折算人民币口径 | 否 |
| Channel | 购买渠道（支付宝、天天基金、券商等） | 是 |
| Transaction | 一笔买卖/分红/初始持仓的事实记录 | 是 |
| SIPPlan | 定投意向（仅基金） | 是 |
| DailySnapshot | 用户每日资产定格 | 是 |
| UserSettings | 用户级开关（价格同步、汇率同步） | 是 |

---

## 三、数据模型

### 3.1 关系总览

```
User ─┬─ Channel ─┐
      ├─ Transaction ── Asset ── AssetPrice
      ├─ SIPPlan ────┘
      └─ DailySnapshot

FxRate（全局，不挂用户）
```

- 资产与价格是**共享字典**，不带用户外键
- 渠道、交易、定投、快照是**用户私有**，全部带 user
- 汇率是全局数据，不挂用户

### 3.2 Asset

| 字段 | 说明 |
|---|---|
| code | 业务主键，唯一 |
| name | 名称 |
| type | stock / mix / bond / index / qdii / fof / money / other |
| currency | 计价币种，CNY 默认，美元份额与美股为 USD |
| market | 标的市场：CN / US / HK，决定交易日历 |
| is_listed | 是否存在场内价格；决定同步是否要拉收盘价 |
| manager | 管理人，可空 |
| risk_level | 风险等级，可空 |
| status | normal / liquidated / suspended |
| created_at / updated_at | 审计时间 |

**currency 为什么现在就要有**：QDII 美元份额与美股的价格是原币，字段缺了后面只能靠「约定俗成的字符串」猜币种。
**status 的用途**：`liquidated`（已清盘）不再参与价格同步与定投生成，持仓按最后一个可用价格
估值；`suspended`（暂停申购）不生成新的定投待确认交易，已有持仓照常估值。

**为什么 type 里已经有 stock 还要 currency**：type 描述「是什么资产」，currency 描述「用什么钱计价」，两者正交。

**为什么 venue 不放在 Asset 上**：同一只 LOF 可以同时在支付宝持有场外份额、在券商持有场内份额。
venue 描述的是「这笔持仓在哪儿」，属于交易与持仓，不属于资产本身。资产只需要知道「有没有场内价格」（is_listed）。

### 3.3 AssetPrice

| 字段 | 说明 |
|---|---|
| asset | 外键，PROTECT |
| date | 自然日 |
| kind | nav（单位净值）/ close（收盘价）/ iopv（参考净值） |
| price | 原币价格，不做任何换算 |

| source | auto / manual |
| created_at | |

约束：`(asset, date, kind)` 唯一。同步任务只插入缺失组合，**永不覆盖 source=manual 的行**。

**为什么不留「累计净值」「日涨跌」字段**：累计净值没有任何消费者；日涨跌既可以由相邻两天
价格差出来，也与快照差分重复，两套来源迟早打架。只留「某个日期的某种价格」这一件事。

**为什么价格要按 kind 分行**：场内 ETF 同一天既有收盘价也有净值，两者之比就是折溢价；只存一个 price 就永远算不出折溢价。
场外资产通常只有 nav 一行，场内资产有 close 与 nav 两行，IOPV 可选。

**取价规则**：持仓行 `venue=otc` 用 nav、`venue=exchange` 用 close；折溢价按 close ÷ nav − 1 现算，不落库。

**为什么价格存原币、不在写入时折算**：汇率天天变，把折算结果写进价格表等于把两个变量混在一个字段里；折算发生在读取时（见 §3.10）。

### 3.4 FxRate

| 字段 | 说明 |
|---|---|
| date | 自然日 |
| base / quote | 币种对，如 USD / CNY |
| rate | 1 单位 base 折多少 quote |
| source | auto / manual |
| created_at | |

约束：`(base, quote, date)` 唯一。

**取汇率规则**：取「不晚于目标日的最近一条」。同步失败时沿用最近可用汇率，并在总览提示汇率日期。
从未同步过汇率时，外币资产折算为空并提示缺少汇率，**禁止按 1:1 顶替**。

**只存一个方向**：表里只保留 USD/CNY 这类正向报价，反向汇率由代码取倒数，避免两个方向各存一份、
彼此不一致。

### 3.5 Channel

| 字段 | 说明 |
|---|---|
| user | 外键，CASCADE |
| name | 渠道名 |
| type | third_party / bank / broker / direct |
| is_default | 是否默认 |
| is_archived | 是否归档 |
| created_at / updated_at | |

约束：
- **每人最多一个默认渠道**（部分唯一索引：user where is_default）
- 不约束 `(user, name)` 唯一：归档后允许同名重建

### 3.6 Transaction

| 字段 | 说明 |
|---|---|
| user | 外键，CASCADE |
| asset | 外键，PROTECT |
| channel | 外键，PROTECT |
| sip_plan | 外键，可空，SET_NULL；标记这笔由哪个定投计划生成 |
| type | opening_balance / buy / sell / cash_dividend / reinvest_dividend / share_adjustment / transfer_out / transfer_in |
| venue | exchange（场内）/ otc（场外） |
| transfer_group | 可空，转出与转入共享同一个配对标识 |
| trade_date | 交易日 |
| confirm_date | 份额确认日，可空；卖出的净流入按这一天归属 |
| amount | 发生额，**以资产币种计**，恒为正 |
| fx_rate | 成交日该币种对 CNY 的汇率，CNY 资产恒为 1 |
| shares | 份额；份额调整与转出可为负 |
| nav | 成交价，原币，可空 |
| fee | 手续费，同币种，默认 0 |
| realized_gain | 可空，仅 opening_balance 使用：录入时的历史已实现收益（CNY） |
| client_request_id | 可空，创建幂等键；转移两笔共用同一个值 |
| status | pending / confirmed / voided |
| source | manual / sip |
| notes | 自由文本 |
| created_at / updated_at | |

**各类型的字段语义**：

| 类型 | amount | shares | nav | 现金流 |
|---|---|---|---|---|
| opening_balance | 累计成本 | 持有份额 | 空 | 无（重放起点，可另填历史已实现收益） |
| buy | 买入金额（含费） | 确认份额 | 有 | 流出 = amount |
| sell | 卖出毛额（份额 × 价格） | 卖出份额 | 有 | 流入 = amount − fee |
| cash_dividend | 分红金额 | 0 | 空 | 流入 = amount |
| reinvest_dividend | 再投金额 | 增加份额 | 有 | 无 |
| share_adjustment | 0 | 增减份额 | 空 | 无 |
| transfer_out | 结转成本 | 负 | 空 | 无（转托管费另计） |
| transfer_in | 结转成本 | 正 | 空 | 无（转托管费另计） |

约束：
- `amount >= 0`、`fee >= 0`
- `shares >= 0`，仅 share_adjustment 与 transfer_out 允许为负；**负值直接落库**，
  重放统一用 `shares += tx.shares`，不再二次取反
- **同一 (user, asset, channel, venue) 最多一条未撤销的 opening_balance**（部分唯一索引）
- 持仓分组键：`(asset, channel, venue)`
- 索引：`(user, trade_date)`、`(user, asset, trade_date)`、`(user, status)`、`transfer_group`
- 唯一约束：`(user, client_request_id, type)`，`client_request_id` 非空时生效。转移两笔共用同一个
  值，但类型不同（transfer_out / transfer_in），两行都能落库；重试时按 client_request_id 查回
  整组（转移返回两笔），因此不需要「只对首笔建索引」这种无法用条件表达的做法

**转出 / 转入的语义**：份额在两个持仓行之间搬家，钱没有动，也不产生已实现收益（转托管费除外）。
amount 记的是「结转成本」而不是金额，两边记同一个数，重放时一转一出正好抵消。
平台间转移（同资产、同 venue、换渠道）与场外转场内（同资产、换 venue、渠道可能也变）
都用这两个类型，区别只在目标行的 channel 与 venue。
UI 必须成对录入：选「转出」时指定目标渠道与场所，系统自动生成转入那笔，金额由系统带出且不可编辑。
两笔共享同一个 transfer_group：**撤销任意一侧时必须同时撤销另一侧**，否则成本会凭空少一半。
转托管可能产生费用：允许填 fee，计为现金流出，**不进成本**，但计入已实现收益的负项——
它是真实支出，不能让它在累计收益里消失。

**转移两笔的 fx_rate 存「来源持仓的成本加权汇率」**，不是成交日汇率：转移没有成交价，
只有成本搬家。转出按该汇率结转 CNY 成本，转入用同一个数入池，两边才能精确抵消；
若取转移日汇率，外币份额每搬一次家，CNY 成本就会漂一次。

**为什么金额以资产币种而非人民币**：用户看到的对账单就是原币金额，录入时不需要先心算汇率；折算放到读取时统一做。
**为什么单独存 fx_rate**：成本必须用成交当时的汇率折算，否则今天的汇率波动会凭空改变历史成本。

### 3.7 SIPPlan

| 字段 | 说明 |
|---|---|
| user / asset / channel | 外键，资产与渠道 PROTECT |
| amount | 每期金额，资产币种 |
| frequency | daily / weekly / biweekly / monthly |
| deduction_day | 月扣 1–28；周扣 1–7；每日定投为空 |
| on_non_trading | postpone（顺延，默认）/ skip（跳过）；仅固定日期型周期有效 |
| start_date | 起始日 |
| end_type | unlimited / by_count / by_date |
| end_count / end_date | 与 end_type 对应，可空 |
| status | active / paused / ended |
| created_at / updated_at | |

**周期字段的语义**（不写死实现时一定歧义）：

| 字段 | 语义 |
|---|---|
| `frequency=daily` | 每个**交易日**扣一次，不是每个自然日；周末与节假日不在扣款日集合里，天然没有记录。`deduction_day` 为空，`on_non_trading` 不适用 |
| `frequency=monthly` | `deduction_day` 为月内第几日，取值 1–28 |
| `frequency=weekly` | `deduction_day` 为 ISO 周几，1=周一、7=周日 |
| `frequency=biweekly` | 同上；以 `start_date` 所在自然周为第 1 周，隔周执行 |
| 首个扣款日 | 从 `start_date` 起第一个满足周期规则的日期；`start_date` 与扣款日冲突时以「不早于 start_date」为准 |
| 顺延（postpone） | 扣款日非交易日时顺延到**第一个「中国 + 资产市场」都开市的交易日**生成；该期算已执行、正常占期数；下一期仍按原周期锚点推算，不整体后移 |
| 跳过（skip） | 当期不生成、不占期数；下一期仍按原周期推算 |
| 期数（`by_count`） | 只计已生成（含顺延）的期次；被跳过或作废的期次不占期数；作废记录仅用于判重 |

**顺延不能跨过下一个原定扣款日**：周投周一遇到整周休市（春节长假），或月投 15 日一直顺延到
下个月，说明这一期实际不会发生——此时丢弃该期并提示「本期未执行」，避免同一周期生成两笔。

**为什么默认 postpone**：主流平台（支付宝、天天基金）的固定日期定投遇非交易日多顺延到下一交易日；
猜错时「多一笔待确认 → 作废」的成本，远低于「平台扣了、系统没记 → 手工补录 + 期数错位」。

**下次扣款日与累计已投不落库**：由「起始日 + 周期 + 已生成的交易」推导。理由与持仓一致——多一份状态就多一处不一致。

**生成的交易固定 venue=otc**：定投是场外申购，没有自动扣款的场内通道，计划本身不需要 venue 字段。

**生成条件是「中国交易日 且 资产市场交易日」**：QDII 基金在海外休市日没有净值、基金公司通常
暂停申购，只按中国日历判断会在感恩节、圣诞、独立日生成无法确认的待确认交易。

**daily 与 on_non_trading 的关系**：每日定投的周期本身就是交易日集合，不存在「非交易日」这一
状态，因此 `on_non_trading` 只对 weekly / biweekly / monthly 生效。

### 3.8 DailySnapshot

| 字段 | 说明 |
|---|---|
| user | 外键 |
| date | 自然日 |
| total_market_value / remaining_cost / holding_gain / realized_gain | 当日定格，**CNY 口径** |
| in_transit / net_inflow / daily_gain | 在途、当日净流入、当日收益，CNY |
| daily_gain_pct | 当日收益率，分母为昨日（市值 + 在途） |
| missing_price / missing_fx | 当日缺价、缺汇率的持仓行数 |
| daily_gain_reason | 当日收益为空的原因：缺价 / 缺汇率 / 转移日 / 无前序快照 |
| created_at | |

约束：`(user, date)` 唯一；重跑结算只补缺失日期，当时数据不完整的日期在数据补齐后自动重算，完整日期不改写。

**净流入与在途的口径**（当日收益公式依赖这两个值，必须唯一定义）：

- 净流入 = Σ(buy 金额，含 pending，含手续费，按 trade_date) − Σ(sell 到账，按 confirm_date)，
  CNY 折算；**不含**分红、红利再投、转入转出
- 在途 = Σ(pending buy 金额)，CNY；只算「钱已付、份额未确认」的买入
- 当日收益 = (今日市值 + 今日在途) − (昨日市值 + 昨日在途) + 当日现金分红 − 当日净流入
  − 当日转移手续费
- 现金分红按**除息日**（trade_date）计入收益，不等到账；红利再投不进公式
- 当日有转移发生时，该日 `daily_gain` 置空并标注原因——场外转场内会切换取价口径，
  折溢价差不是收益
- `daily_gain_pct` = 当日收益 ÷ (昨日市值 + 昨日在途)
- 「昨日」取**最近一个有快照的日期**，不是严格的日历昨天

**为什么买入按付款日、卖出按到账日**：买入当天钱已经出去（在途增加），必须同时记一笔正向净流入
才能让收益归零；卖出当天金额要到确认才确定，记在成交日就只能估一个数，确认后还会与市值变化
错位。按「现金实际发生日」归属，两个方向都自洽。

**快照只存 CNY 合计**：快照是给人看的「那天值多少钱」，原币明细在交易与价格里可随时重算；汇率按日存表，事后要复盘也能查到当日汇率。

### 3.9 约束与索引汇总

| 表 | 关键约束 | 索引 |
|---|---|---|
| Asset | code 唯一 | code |
| AssetPrice | (asset, date, kind) 唯一 | 唯一索引即查询索引 |
| FxRate | (base, quote, date) 唯一 | 唯一索引即查询索引 |
| Channel | 每人至多一个默认渠道 | (user) |
| Transaction | 金额/手续费非负；份额符号（调整/转出可负）；初始持仓按 (资产, 渠道, 场所) 唯一；(user, client_request_id, type) 唯一 | (user, trade_date)；(user, asset, trade_date)；(user, status) |
| SIPPlan | 金额为正；周期与扣款日匹配（应用层） | (user, status) |
| DailySnapshot | (user, date) 唯一 | 唯一索引即查询索引 |

### 3.10 折算口径

| 场景 | 用什么汇率 |
|---|---|
| 持仓市值 | 场外取 nav、场内取 close，再按最新可用汇率折算 |
| 剩余成本（原币池） | 不折算，按原币成交额累加 |
| 剩余成本（CNY 池） | 每笔成交额 × 成交日 fx_rate 累加 |
| 已实现收益 | 到账 CNY − 结转 CNY 成本 |
| 在途金额 | 交易日 fx_rate（与成本同口径） |
| 快照 | 结算当天最新可用汇率 |
| 总览合计 | 各资产按最新汇率折算后相加 |

**成本为什么按两个池维护**：原币池锁住历史成交价，CNY 池锁住历史汇率。只留 CNY 池，
显示「成本价」时要反算成原币，会随今天的汇率漂移，回本价天天变；只留原币池，又算不出人民币收益。
两池在卖出时按份额比例同步结转，比值恒等于该持仓的成本加权汇率。

**持仓行需要返回**：原币成本、原币成本价、成本加权汇率、CNY 成本。人民币资产 fx 恒为 1，
两池数值相同，逻辑自然退化，不需要写分支。

**汇率缺失时**：从未同步过汇率的外币资产，折算结果为空，持仓显示「—」并提示缺少汇率，
不允许按 1:1 顶替。

### 3.11 UserSettings

| 字段 | 说明 |
|---|---|
| user | OneToOne，CASCADE |
| price_sync_enabled | 价格自动同步开关，默认开 |
| fx_sync_enabled | 汇率自动同步开关，默认开 |
| price_synced_at / fx_synced_at | 价格、汇率最后一次成功同步时间 |
| last_sync_failures | JSON，最近一次同步的失败清单（资产代码、日期、原因） |
| updated_at | |

**为什么不塞进环境变量**：开关是用户运行时的偏好，改一次就要重启服务不合理。
单人使用也用行存，是为了「删除用户时一并清理」和「以后多用户零改动」。

### 3.12 交易日历

判定入口只有一个：`is_trading_day(market, date)`。

| 市场 | 规则 | 数据来源 |
|---|---|---|
| CN | 周一至周五 且 非法定节假日 | 轻量数据包（覆盖至 2027，每年随依赖升级） |
| US | 周一至周五 且 非 NYSE 假日；含「遇周六提前到周五、遇周日推迟到周一」的观测规则与耶稣受难日 | 按规则自行计算，无年份上限、无依赖 |
| HK | 一期不提供，按 CN 处理并在页面标注 | — |
| 未知 | 退回 CN 规则 | — |

**为什么美股不查表而自己算**：美国交易所的休市规则几十年不变（固定日期 + 几个「第 N 个周一/周四」），
四十行代码就能算到任意年份；引入日历包要背着 pandas 或每年喂数据，收益为负。

**日历用在两处**：定投生成（需中国与资产市场同时开市）、价格同步（避免在目标市场休市日空跑）。
快照不受它约束——快照每天写，周末沿用上一交易日价格。

**兜底**：中国日历数据超出覆盖年份时，退回「仅按工作日判断」，并在定投页提示升级依赖。

---

## 四、核心口径

### 4.1 交易流水是唯一事实来源

持仓不建表，份额和成本由已确认交易实时重放得出：

- 初始持仓 → 份额、原币成本、CNY 成本直接作为起始游标值
- 买入 → 份额增；原币成本增（**金额，含手续费**）；CNY 成本增（原币成本 × 成交日汇率）
- 卖出 → 按当前原币摊薄单价结转原币成本，CNY 成本按同一比例结转，差额计入已实现收益
- 红利再投 → 份额增，成本不变
- 现金分红 → 份额与成本不变，计入已实现收益
- 转出 → 份额减，两池成本按摊薄单价同步减少
- 转入 → 份额增，两池成本接收转出方的结转值，不产生现金流
- 金额恒为正，方向由类型表达

Transaction 类型统一为：`opening_balance`（初始持仓）、`buy`（买入/申购）、`sell`
（卖出/赎回）、`cash_dividend`（现金分红）、`reinvest_dividend`（红利再投，仅基金）、
`share_adjustment`（份额调整，仅基金）、`transfer_out` / `transfer_in`（份额转移）。

### 4.2 收益

| 口径 | 定义 |
|---|---|
| 持仓收益 | CNY 市值 − CNY 剩余成本 |
| 已实现收益 | 卖出结转收益 + 现金分红 + 初始持仓历史已实现收益 − 转移手续费（均为 CNY） |
| 累计收益 | 持仓收益 + 已实现收益 |
| 持仓收益率 | 持仓收益 / CNY 剩余成本 |
| 累计收益率 | （累计收益 − 初始持仓的历史已实现收益）/ 累计净投入（CNY：Σbuy 金额 − Σsell 到账 + Σ转入结转成本 − Σ转出结转成本 + 初始持仓成本；分母 ≤ 0 返回 null） |
| 年化收益率 | 按资产（同资产跨渠道、跨场所合并）计算的 IRR；总览另给组合级 |
| 当日收益 | 见 §3.8 的唯一公式：Δ(市值 + 在途) + 当日分红 − 当日净流入 − 当日转移费（CNY） |

三种收益率并存，界面标注所用口径。用摊薄成本法；人民币资产两个成本池重合。

**年化的现金流**：opening_balance 记 −成本（日期取 **trade_date**，即用户填的起始日）、buy 记 −金额、
sell 与现金分红记 +到账、期末市值记 +；**转移视为资产内部移动，排除**；转移手续费作为负项计入。
只录过初始持仓的账户因此也有期初投入，NPV 不会恒正。

「市值」按每条持仓行的 venue 选价：场外取 nav，场内取 close；取不到对应价格时该持仓市值
为空，不拿另一种价格顶替。持仓按 (资产, 渠道, 场所) 分组重放。

### 4.3 每日快照

每天结算（含周末）写一行，锁定当日市值、成本、收益、在途金额（全部 CNY 口径）。
周末与非交易日沿用上一交易日的价格与汇率，因此快照每天都在，不会出现空洞。

用途：①走势图不随净值回补漂移；②当日收益按 §3.8 的公式与上一快照差分；③总览页
「今日涨跌」的涨幅百分比同样从此差分得出。完整日期的快照不自动改写；当时数据不完整的
日期在补齐后自动重算，其余历史修正需用户显式触发（区间重算入口）。

某一日缺价格或缺汇率时，快照**照常写入**：缺价的持仓沿用最近一个可用价格（超过陈旧上限则视为
缺价、计入 `missing_price`），该日 `daily_gain` 置空并记录原因，不整日跳过——否则次日会拿
几天前的快照做差分，把多日涨跌算成一天。

**数据回补后自动重算**：价格或汇率从「缺」变「有」时（同步回补、手工补价），自动重算受影响的
日期区间——只重算当时数据不完整的日期，完整的历史不动。QDII 净值常在次日凌晨才出，靠人工点
重算等于每天都要点一次。

### 4.4 初始持仓

每只资产 × 每个渠道 × 每个场所一条：填当前持有的总份额、累计成本（原币）、历史已实现
收益（realized_gain，CNY 口径）与成交日汇率。重放时作为起始游标值，价格不存（由同步任务补齐），此后按正常交易叠加。

同一资产 × 渠道 × 场所只允许一条未撤销的初始持仓；撤销后可重录。

### 4.5 交易状态

| 状态 | 含义 | 允许的操作 |
|---|---|---|
| pending（手动 / 场内） | 已提交、份额未确认 | 修改、删除、确认、撤销 |
| pending（定投生成） | 已提交、份额未确认 | 只能作废或确认；不可修改（改 trade_date 会破坏判重） |
| confirmed | 已计入持仓与收益 | 撤销（不可改、不可删） |
| voided | 已撤销，不计入任何计算 | 无 |

**初始状态按类型定，不只按 venue**：

| 类型 | 初始状态 | 理由 |
|---|---|---|
| 场外 buy / sell | pending | 份额 T+1 才知道 |
| 场内 buy / sell | confirmed | 撮合成交价已知 |
| opening_balance | confirmed | 录入的是既成事实，没有「待确认」 |
| 现金分红 / 红利再投 | confirmed | 金额由平台公告确定 |
| 份额调整 | confirmed | 人工登记的事实 |
| transfer_out / transfer_in | confirmed | 份额搬家即时生效 |

- 确认、撤销都幂等：重复操作返回 200，不重复写
- 已确认交易不可原地修改，只能撤销后重录——改历史会让数字凭空变化
- 转移的两笔共享 `transfer_group`，撤销任一侧必须连带撤销另一侧，且在同一事务内完成
- **定投生成的 pending 只能作废、不能物理删除**：删掉会让 `(sip_plan, trade_date)` 判重失效，
  重跑会再生成一次；作废记录仅参与判重，不占用期数
- **可用份额 = 已确认份额 − 同一持仓行未撤销的待确认卖出份额**：否则连下两笔超额赎回都能通过校验

---

## 五、接口契约

### 5.1 通用约定

| 项 | 约定 |
|---|---|
| 路径 | `/api/` 下，统一带尾斜杠 |
| 鉴权 | Session Cookie；写操作校验 `X-CSRFToken` |
| 列表 | 一律分页，结构见 5.2 |
| 日期 | `YYYY-MM-DD`，自然日，不做时区换算 |
| 时间戳 | ISO 8601 带时区偏移 |
| 数值 | 字符串（金额、份额、价格均为 Decimal） |
| 空值 | `null`，不用 `0` 或空串顶替 |
| 错误 | 非 2xx 返回 `{ detail, fields? }`，detail 为可直接展示的中文 |

**数值为什么用字符串**：JSON 数字是双精度浮点，`0.1 + 0.2` 这种误差在金额上不可接受；
后端序列化 Decimal 为字符串，前端只在展示时格式化。

### 5.2 分页

所有列表接口分页，参数 `page`（从 1 开始）、`page_size`（默认 20，上限 100）。

| 字段 | 说明 |
|---|---|
| count | 全量条数 |
| next / previous | 下一页 / 上一页的完整 URL，无则 null |
| results | 当前页数据 |

两处例外，都是为了不让分页影响结论：

- **持仓接口额外返回 `totals`**：全量合计，与当前页无关，字段为 `count`（有份额的行数）、
  `market_value`、`remaining_cost`、`holding_gain`、`holding_gain_pct`、`missing_price`
  （缺价行数）、`missing_fx`（缺汇率行数）。份额为 0 的行不计入；缺价或缺汇率的行计入
  count，但不计入金额合计——宁可少算一部分并明确提示，也不按 1:1 或成本价顶替。
- **`group=channel` 按渠道分页**：一页是一条渠道及其名下资产，小计随渠道一起返回，
  不会出现「同一渠道的小计被拆到两页」。
- **`group=asset` 只合并渠道，不合并场所**：同一只 LOF 的场外与场内仍是两行，各自按
  nav / close 取价；合并后的行不再有单一 `channel_name`，该字段返回 null。
- **`ordering` 白名单**：`market_value`、`holding_gain`、`holding_gain_pct`、`asset_name`、
  `shares`、`channel_name`；写法 `field` / `-field`；缺省 `-market_value`。
- **`include_zero`**：默认 false；为 true 时附带 0 份额的行，不计入 totals。
- **时间序列接口不分页**：`/snapshots/` 与 `/assets/{code}/prices/` 是区间数据，按 `from` / `to`
  一次返回，不套分页结构——一年 365 个点翻页拼不起来。
- **待确认列表单独请求**：`/transactions/?status=pending`，同样分页；与流水表分开取，
  避免「待确认区」受流水页大小影响。

### 5.3 错误与状态码

| 码 | 场景 |
|---|---|
| 400 | 参数或业务校验失败，`fields` 指出具体字段 |
| 401 | 未登录 |
| 404 | 资源不存在，或资源不属于当前用户（不区分两者，避免泄露存在性） |
| 409 | 状态冲突：删除已确认交易、删除定投生成的待确认交易、删除有引用（交易或定投计划）的渠道、重复初始持仓 |
| 403 | 账号被禁用等与资源无关的拒绝 |
| 500 | 未预期错误，不泄露堆栈 |

**创建是幂等的**：`POST /transactions/` 与 `POST /transactions/transfer/` 接受可选的
`client_request_id`，同一用户内唯一（按 `user + client_request_id + type` 建唯一约束）；
重复提交返回首次创建的对象（转移返回两笔），不再写第二笔。前端每次打开表单生成一个，
提交失败重试时复用。

**确认与撤销是幂等的**：重复确认已确认的交易、重复撤销已撤销的交易，都返回 200 与当前
状态，不报错——前端双击或网络重试不应该看到红色提示。

### 5.4 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/summary/` | 总览数字与提示位 |
| GET | `/api/positions/` | `group`（asset / channel）、`ordering`、`include_zero`，分页 + 全量 totals |
| GET | `/api/transactions/` | 流水分页，支持 status / asset / channel / type / 日期区间 |
| POST | `/api/transactions/` | 记一笔（含 venue 与 fx_rate） |
| PATCH | `/api/transactions/{id}/` | 仅非定投来源的待确认可改 |
| DELETE | `/api/transactions/{id}/` | 仅待确认可删；定投生成的只能作废，删除返回 409 |
| POST | `/api/transactions/{id}/confirm/` | 幂等转为已确认 |
| POST | `/api/transactions/{id}/void/` | 幂等撤销；转移自动连带对侧 |
| POST | `/api/transactions/transfer/` | 一次创建转出与转入两笔 |
| GET/POST | `/api/channels/` | 渠道列表（分页）/ 新建 |
| PATCH / DELETE | `/api/channels/{id}/` | 改默认、归档；无引用的才可删 |
| GET | `/api/assets/?q=` | 搜索资产（分页） |
| POST | `/api/assets/` | 手工新建资产 |
| GET | `/api/assets/{code}/` | 资产 + 最新价格 + 我的持仓（一次返回） |
| GET | `/api/assets/{code}/prices/?kind=` | 价格区间，按 kind 分组 |
| POST | `/api/assets/sync/` | 手动同步价格与汇率 |
| POST | `/api/assets/{code}/prices/` | 手工写价格，同日 auto 行就地升级为 manual |
| POST | `/api/fx-rates/` | 手工写汇率，语义同上 |
| DELETE | `/api/assets/{code}/prices/?date=&kind=` | 删除手工价格行；之后同步会把它当缺失重新拉取 |
| DELETE | `/api/fx-rates/?date=&base=&quote=` | 删除手工汇率行，语义同上 |
| GET | `/api/settings/` | 读取数据源开关与最后同步时间 |
| PATCH | `/api/settings/` | 修改价格 / 汇率同步开关 |
| GET | `/api/export/transactions/` | 导出流水 CSV（含原币金额、成交汇率、场所） |
| POST | `/api/data/clear/` | 清空当前用户数据，请求体需带确认口令 |
| POST | `/api/snapshots/recalculate/` | 按区间重算快照，显式触发 |
| GET/POST | `/api/sip-plans/` | 定投计划（分页）/ 新建 |
| PATCH | `/api/sip-plans/{id}/` | 暂停、恢复、修改 |
| GET | `/api/snapshots/?from=&to=` | 资产走势区间 |

**资产详情为什么合并成一个接口**：分开请求会出现「资产已拿到、价格还在路上」的中间态，
前端要处理两套 loading；合并后一次到位，数据天然一致。

**转移为什么单独一个端点**：普通创建接口只需处理单笔；转移要校验来源持仓、计算结转成本、
同时写两笔并共享配对标识，逻辑独立成端点更清楚，也不让创建接口背两套分支。

### 5.4.1 主要请求体

| 端点 | 字段 |
|---|---|
| `POST /transactions/` | `asset_code`、`channel_id`、`venue`、`type`、`trade_date`、`amount`；`shares` / `nav` / `fee` / `fx_rate` / `notes` / `sip_plan_id` 可空；`client_request_id` 可选 |
| `POST /transactions/transfer/` | `asset_code`、`from_channel_id`、`from_venue`、`to_channel_id`、`to_venue`、`shares`、`trade_date`、`fee` 可空、`client_request_id` 可选；`fx_rate` 与结转金额由服务端计算 |
| `PATCH /transactions/{id}/` | 与创建相同字段的子集；仅非定投来源的待确认可改 |
| `POST /transactions/{id}/confirm/` | `shares`、`nav`、`fee` 可空；`confirm_date` 由服务端取确认当天写入，不接受前端传值；已确认时忽略入参返回 200 |
| `POST /transactions/` 的补充字段 | `realized_gain`（仅 opening_balance） |
| `POST /sip-plans/` | `asset_code`、`channel_id`、`amount`、`frequency`、`deduction_day`（daily 可空）、`on_non_trading`（默认 postpone）、`start_date`、`end_type`、`end_count` / `end_date` |
| `POST /assets/` | `code`、`name`、`type`、`currency`、`market`、`is_listed`、`manager` / `risk_level` 可空 |
| `POST /assets/{code}/prices/` | `date`、`kind`、`price`；同日 auto 行就地升级为 manual |
| `POST /fx-rates/` | `date`、`base`、`quote`、`rate` |
| `PATCH /settings/` | `price_sync_enabled` / `fx_sync_enabled`，至少一个 |
| `POST /data/clear/` | `confirm_text`，必须与约定口令一致 |

**pending 的场外买入**：`shares` 与 `nav` 允许为 null，确认时才要求非空；返回 null 而不是 0。
外币交易的 `fx_rate` 必须非空，缺汇率时拒绝提交并提示先手工填汇率——它决定成本折算，
缺失会让该资产后续收益永久算不出来。

### 5.5 关键响应字段

**持仓行**

| 字段 | 说明 |
|---|---|
| asset_code / asset_name / asset_type | 资产 |
| channel_id / channel_name | 渠道 |
| venue | exchange / otc |
| currency | 计价币种 |
| shares | 份额 |
| cost_per_share | 原币摊薄成本价 |
| remaining_cost | CNY 剩余成本 |
| remaining_cost_original | 原币剩余成本 |
| cost_fx_rate | 成本加权汇率 |
| latest_price / price_date | 原币最新价与日期 |
| market_value | CNY 市值 |
| market_value_original | 原币市值 |
| holding_gain / holding_gain_pct | CNY 持仓收益与持仓收益率 |
| cumulative_gain_pct | 累计收益率（分子已剔除初始持仓的历史已实现） |
| realized_gain | CNY 已实现收益 |
| holding_days / weight / fee_total | 天数、占比、累计费用 |

**总览**

`total_market_value`、`daily_gain`、`daily_gain_pct`、`total_gain`、`total_gain_pct`、
`cost_basis`、`in_transit`、`holding_days`、`annualized_return`（组合级 IRR，样本不足为 null），
另加数据新鲜度与缺口字段：`price_as_of`、`fx_as_of`、`fx_missing`（缺汇率资产数）、
`price_missing`（缺价资产数）。

**交易行**

在现有字段外增加 `venue`、`currency`、`fx_rate`、`transfer_group`、`sip_plan_id`、
`source`、`realized_gain`（仅初始持仓有值）；
金额、份额、价格、手续费均为字符串。

**定投计划**

`id`、`asset_code` / `asset_name`、`channel_id` / `channel_name`、`amount`、`frequency`、
`deduction_day`、`on_non_trading`、`start_date`、`end_type` / `end_count` / `end_date`、`status`，
外加推导字段：`next_deduction_date`、`total_invested`（只计已确认）、`due_unconfirmed`
（到期未确认的笔数）、`last_skip_reason`（如海外休市）。

**设置**

`price_sync_enabled`、`fx_sync_enabled`、`price_synced_at`、`fx_synced_at`、
`last_sync_failures`（失败清单，可空）。

**同步结果**

`{ price: { success, failed, failures: [...] }, fx: { success, failed }, as_of }`。

**渠道**

`id`、`name`、`type`、`is_default`、`is_archived`；列表支持 `include_archived`（默认 true）。

**资产搜索**

`code`、`name`、`type`、`currency`、`market`、`is_listed`。

**资产详情**

一次返回四段：资产本体（含 `currency`、`is_listed`）、价格分组（`nav` / `close` / `iopv`
各自数组）、我的持仓（无持仓为 null，含持仓收益率、累计收益率与该资产年化收益率；
年化样本不足时返回 null）、最近交易（`recent_transactions`，默认 10 条，按交易日倒序）。

---

## 六、关键流程

**定投自动生成（主流程）**：设好定投计划 → 扣款日系统根据计划参数自动生成待确认交易
（source=sip，金额已知、净值待填）→ 用户确认时补份额、净值、手续费 → 交易转为已确认
→ 持仓重放自动纳入。扣款日落在非交易日时按计划的 `on_non_trading` 处理：默认顺延到下一个两市都开市的交易日，也可配成跳过。

**手动录入（补充）**：通过「记一笔」接口提交交易（类型 buy/sell/opening_balance 等）→
场外交易提交后为 pending，等份额确认后补净值与份额转 confirmed；**场内交易成交即确定，
提交时直接为 confirmed**。初始持仓不要求价格，份额和成本直接作为重放起始游标值。

**首次使用**：登录 → 创建渠道 → 录入初始持仓 → 同步历史价格 → 持仓出现。

**每日结算**：取有持仓的资产 → 按资产所在市场的日历决定是否拉价 → 逐只拉最新价格（幂等写入）
→ 拉当日汇率（有外币资产时）→
算当天快照（总市值、剩余成本、持仓收益、已实现收益、在途金额、当日净流入、当日收益）→
记录同步结果。价格或汇率缺失时照常写入快照、当日收益置空并记录原因；数据补齐后自动重算受影响日期。

---

## 七、设计决策

| 决策 | 理由 |
|---|---|
| 交易流水是唯一事实来源，持仓实时派生 | 多一份状态就多一处不一致 |
| 渠道独立成表 | 「所有持仓」是多渠道之和 |
| 摊薄成本法 | 与国内平台口径一致 |
| 三种收益率并存并标注 | 单一口径必然误导 |
| 快照只做用户日聚合 | 资产级行数过高 |
| 完整快照不自动改写，不完整日期随补数重算 | 静默修正破坏信任；但迟到数据不重算会让走势长期错 |
| 撤销而非删除 | 保留审计痕迹 |
| 金额为正、方向由类型表达 | 避免四处判断符号 |
| 不引入 Celery/Redis | 一天一次同步，crontab 足够 |
| 前端不做口径计算 | 避免两处公式漂移 |
| Transaction 类型统一为 buy/sell | 未来加股票不需新增类型 |
| 资产带 currency + 汇率表 | 美元份额与美股不是假设，缺币种就没法合计 |
| 交易金额记原币并保存成交日汇率 | 成本是历史事实，不能被今天的汇率改写 |
| Transaction 记录 sip_plan | 否则分不清哪笔由哪个计划生成，累计投入无法推导 |
| 下次扣款日与累计已投不落库 | 与持仓同理，避免多份状态不一致 |
| venue 放在交易与持仓上 | 同一只 LOF 可同时有场外份额与场内份额，挂在资产上会二选一 |
| 转出 / 转入用结转成本记账 | 份额搬家不产生现金流与已实现收益，两边同额抵消 |
| 价格按 kind 分行 | 场内同一天有收盘价与净值，合并成一个字段就算不出折溢价 |
| 年化收益率自己实现，不引入 numpy / pandas | 它们不支持不规则日期的 XIRR；几十条现金流用二分法即可，分析页需要矩阵运算时再评估 |
| 依赖按必要性、运行成本、运维形态、可逆性逐项判断 | 不按体积一刀切；假日数据无法自行推导故引入轻量数据包，任务队列与负载不匹配故不引 |

---

## 八、边界

| 情况 | 处理 |
|---|---|
| 新资产无价格 | 显示「—」，不按成本冒充市值 |
| 价格接口失败 | 提示最后成功日期，不写脏数据 |
| 卖出份额超可用 | 拒绝，提示可用份额 |
| 定投扣款日非交易日（postpone） | 顺延到下一个中国 + 资产市场都开市的交易日，该期算已执行 |
| 定投扣款日非交易日（skip） | 本期跳过，不占用期数，下次扣款日按原周期推算 |
| 顺延超过下一期原定扣款日 | 丢弃该期并提示「本期未执行」，禁止同一周期生成两笔 |
| 每日定投遇周末或节假日 | 不在扣款日集合内，不生成也不算漏扣 |
| 扣款日中国开市、资产市场休市 | 固定日期型按策略处理（默认顺延到两市都开市）；daily 不生成、不算漏扣 |
| 交易日历超出覆盖年份 | 退回「仅工作日」判断，定投页提示升级依赖 |
| 重复初始持仓 | 拒绝，提示先撤销旧的 |
| 渠道下有交易或定投计划时删除 | 拒绝，只允许归档 |
| 渠道无引用时删除 | 允许，二次确认；删除默认渠道后按「创建时间最早的非归档渠道」顺延 |
| 跨用户访问 | 强制按用户过滤 |
| 货币基金 | 一期明确拒绝 |
| 场内资产做定投 | 一期不支持：场内没有自动扣款，只能手动买入 |
| 转出份额超过该持仓可用份额 | 拒绝，提示可用份额 |
| 转移两岸金额不一致 | 不允许：转入金额由转出自动带出，禁止手工改 |
| 撤销转移的任意一侧 | 两侧同时撤销；只撤一侧会让另一侧变成没有来源的份额 |
| 平台间转移后成本变化 | 不允许：结转成本原样搬走，不产生已实现收益 |
| 场内资产只有收盘价、缺净值 | 市值正常（用 close），折溢价显示「—」，不拿收盘价冒充净值 |
| 价格过于陈旧（超过合理期限） | 视为缺价，计入 missing_price，不用旧价冒充当日市值 |
| 当日发生转移 | 该日 daily_gain 置空并标注原因，避免把取价口径切换当成收益 |
| 场外资产缺净值 | 市值为空，显示「—」 |
| 持仓合计遇到缺价或缺汇率 | 该行计入只数，不计入金额合计，并在 totals 与总览给出缺口计数 |
| 份额归零（已清仓） | 默认不在持仓表展示；可开启「显示已清仓」，但**不计入合计与 totals** |
| 定投扣款日净值未出 | 待确认交易正常生成，净值字段留空，不阻塞用户后续确认 |

---

## 九、未来扩展

### 9.1 股票

设计已预留扩展空间：
- `Asset` 类型枚举预留 `stock`（A 股/港股/美股），新建时选类型即可
- `Transaction` 类型 `buy` / `sell` / `cash_dividend` 直接对应股票买卖分红
- `AssetPrice` 的 `kind` 已经能同时容纳收盘价与净值

需新增的能力：
- 交易时段感知（股票盘中价格 vs 基金日终净值）
- 实时行情源（当前同步按日拉取，股票需要盘中价）

### 9.2 其他

- 货币基金独立口径
- 定投提醒
- 港股与其他市场的交易日历
- 批量导入：平台支持导出或能可靠识别截图时再做，当前无数据来源
- 基准对比、回撤、相关性
- OCR 截图记账
- 更多币种（当前只做了 CNY / USD 折算）
- 年度报告导出

---

## 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-11-25 | 从功能设计文档拆出：架构分层、数据模型（Fund→Asset）、口径、接口、流程、决策、边界、股票扩展预留 |
| v2 | 2026-11-25 | 重写关键流程（定投自动生成为主、CSV 比对为月度纠错、手动录入为补充）；补快照用于今日涨跌的口径；补三条 CSV/定投边界；CSV 导入从未来扩展移除 |
| v3 | 2026-11-25 | 补渠道删除边界：有交易只能归档，无交易可删且顺延默认渠道 |
| v4 | 2026-11-25 | 新增数据模型一节：字段、约束、索引、折算口径；新增 FxRate 表、Asset.currency、Transaction.sip_plan 与 fx_rate |
| v5 | 2026-11-25 | 新增 Asset.venue 区分场内/场外；AssetPrice 增加 kind 维度，支持收盘价与净值并存并计算折溢价 |
| v6 | 2026-11-25 | venue 从 Asset 下移到 Transaction；新增 transfer_out / transfer_in 支持平台间转移与场外转场内 |
| v7 | 2026-11-25 | 转移两笔加 transfer_group 配对，撤销必须成对 |
| v8 | 2026-11-25 | 初始持仓唯一约束补 venue；成本改为原币池 + CNY 池双池维护；补汇率缺失兜底、转移费用、在途汇率、定投固定场外 |
| v9 | 2026-11-25 | 接口一节扩写为接口契约：通用约定、全量分页与 totals、错误码、幂等规则、转移端点、关键响应字段 |
| v10 | 2026-11-25 | 补 Transaction.realized_gain：初始持仓需要录入历史已实现收益，此前模型缺该字段 |
| v11 | 2026-11-25 | 记录决策：XIRR 自行实现，不引入 numpy / pandas |
| v12 | 2026-11-25 | 删除 CSV 导入流程与相关边界：支付宝无交易记录导出，功能失去数据来源；每日结算补汇率同步 |
| v13 | 2026-11-25 | 修正 §二 Asset 描述；403 改为 404；补已清仓策略、累计收益率分母、已实现收益口径；新增交易状态机；totals 字段列全；修正股票扩展命名 |
| v14 | 2026-11-25 | 四文档审查修订：红利再投与转移口径、净流入与在途定义、按类型初始状态、年化现金流与范围、快照每日与差分基准、分页参数与分组、补手工价格/汇率等端点、新增 UserSettings、累计收益率剔除历史已实现 |
| v15 | 2026-11-25 | 新增 Asset.market 与交易日历一节：定投生成要求中国与资产市场同时开市；美股日历按规则计算；补海外休市与超范围兜底 |
| v16 | 2026-11-25 | 设计决策补依赖判据：按必要性、运行成本、运维形态、可逆性逐项判断，不按体积一刀切 |
| v17 | 2026-11-25 | 六路审查修订：统一当日收益公式与净流入归属、快照完整性与自动重算、买入成本含费、转移符号、累计收益率净投入口径、定投作废与可用份额、接口请求/响应补齐、创建幂等 |
| v18 | 2026-11-25 | 补定投周期字段语义、渠道引用与默认顺延规则、主要端点请求体、外币交易 fx_rate 必填 |
| v19 | 2026-11-25 | 复验修复：统一缺价快照与自动重算表述、累计收益率减转出成本、DELETE 排除定投、补定投/资产/PATCH 请求体与 realized_gain、UserSettings 补同步字段、client_request_id 入模型、期数与顺延统一、移动端五 tab |
| v20 | 2026-11-25 | 第三轮复验：快照措辞三处统一、作废不占期数、幂等键定为 (user, client_request_id, type)、confirm_date 由服务端写、定投 pending 禁止修改、手工价格删除参数与 409 场景补齐 |
| v21 | 2026-11-25 | 第四轮复验：§4.3 开头改为限定表述；PATCH 请求体补「非定投来源」限定 |
| v22 | 2026-11-25 | 定投新增 daily 频率与 on_non_trading 策略（默认顺延）；明确顺延锚点不变、跨周期保护与期数口径 |
| v23 | 2026-11-25 | 修正 §六 与 §八 残留的「一律跳过」表述，改为按 on_non_trading 策略 |