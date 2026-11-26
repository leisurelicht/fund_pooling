# 持仓管理系统 — 后端实施文档

> 状态：待实施 | 更新：2026-11-25（修订 9）
>
> 设计依据见 `fund-holdings-arch-design.md`；本文只写怎么落地，不重复为什么这样设计。

---

## 一、交付范围

| 里程碑 | 内容 | 完成标志 |
|---|---|---|
| M1 | 模型 + 领域计算（纯函数） | 单测覆盖全部流水类型与双池成本 |
| M2 | 接口：交易、持仓、总览、渠道、资产、设置、导出 | 契约字段齐全，分页与错误体符合 §5 |
| M3 | 前端联调 | 记账、确认、撤销、转移全链路可走 |
| M4 | 同步任务：价格、汇率、快照、定投生成 | 幂等、可重跑、失败可见 |

**本期不做**：批量导入（平台无导出能力）、分析接口、股票实时行情、多用户协作。

---

## 二、目录与模块

```
backend/apps/portfolio/
├── models.py                 # 六张表 + FxRate
├── domain/
│   ├── money.py              # Decimal 工具：量化、求和、安全除法
│   ├── replay.py             # 流水重放：份额与双池成本
│   ├── metrics.py            # 市值、收益、收益率
│   ├── xirr.py               # 年化收益率
│   └── calendar.py           # is_trading_day(market, date)：CN 查包、US 按规则算
├── services/
│   ├── positions.py          # 读模型：按资产 / 按渠道聚合
│   ├── summary.py            # 总览数字与新鲜度
│   ├── transactions.py       # 创建、确认、撤销、状态机
│   ├── transfers.py          # 转移：两笔成对写入
│   ├── snapshots.py          # 结算与补算
│   ├── settings.py           # 用户开关与手工价格 / 汇率的 upsert
│   └── exports.py            # 流水导出与数据清空
├── providers/
│   ├── base.py               # 价格源与汇率源接口
│   ├── eastmoney.py          # 基金净值适配
│   └── fx.py                 # 汇率适配
├── management/commands/
│   ├── sync_market_data.py
│   ├── settle_snapshot.py
│   └── generate_sip_orders.py
├── serializers.py
├── views.py
├── urls.py
├── pagination.py
├── exceptions.py
├── admin.py
└── tests/
```

**为什么单独有 `domain/`**：这一层不 import models，只接收普通数据类，方便脱离数据库单测，
也避免「序列化器里顺手算收益」这种把口径埋进接口的写法。

---

## 三、依赖

依赖不按体积一刀切，逐项看四件事：

| 判据 | 问什么 |
|---|---|
| 必要性 | 标准库能不能干？干起来是否容易出错？ |
| 运行成本 | 镜像增量、构建时间、攻击面、升级频率 |
| 运维形态 | 是多一个常驻进程/中间件，还是多一个函数调用 |
| 可逆性 | 后悔了能不能轻松删掉；越难回退，门槛越高 |

### 3.1 当前结论

| 依赖 | 结论 | 理由 |
|---|---|---|
| `chinesecalendar` | **引入** | 法定假日无法用规则推导，自己维护等于每年录表；90 KB、零依赖、覆盖 2004–2027 |
| numpy / pandas / scipy | 暂不引入 | XIRR 是几十条现金流的单变量求根，二分法三十行就够；分析页做矩阵运算与滚动窗口时**再评估**，不是永久禁止 |
| Celery / Redis | 不引入 | 负载是每天三个命令，却要换来 worker、beat、broker 三个常驻进程和一整套故障模式；多用户、上千资产、需要重试与并发控制时再考虑 |

### 3.2 使用约定

- `chinesecalendar` 没有 `py.typed`，补一个 `.pyi` 存根，不要用 `# type: ignore` 散落各处
- 每年随常规依赖升级顺带 `uv lock --upgrade-package chinesecalendar`
- 新增任何依赖都要在本节表格里补一行结论，写明判据，避免下次又靠印象争论

## 四、模型要点

### 4.1 精度

| 字段 | 精度 | 理由 |
|---|---|---|
| 金额 `amount` / `fee` / `realized_gain` | 18 位、2 位小数 | 留足位数，统一到分 |
| 份额 `shares` | 18 位、4 位小数 | 场外份额有零头，4 位够用 |
| 价格 `price` / `nav` | 12 位、4 位小数 | 基金净值 4 位；股票价格后续再放宽 |
| 汇率 `rate` | 18 位、6 位小数 | 汇率需要更高分辨率，否则折算误差被放大 |
| 快照金额 | 20 位、2 位小数 | 合计值比单笔大两个数量级 |

所有 Decimal 字段禁止用默认 `float` 转换；序列化统一 `coerce_to_string=True`。

### 4.2 约束

| 表 | 约束 |
|---|---|
| Asset | `code` 唯一；`code`、`name` 非空 |
| AssetPrice | `(asset, date, kind)` 唯一 |
| FxRate | `(base, quote, date)` 唯一 |
| Channel | `UniqueConstraint(fields=["user"], condition=Q(is_default=True))` |
| Transaction | `amount >= 0`、`fee >= 0`；`shares >= 0 OR type IN ('share_adjustment','transfer_out')`；`UniqueConstraint(fields=["user","asset","channel","venue"], condition=Q(type="opening_balance") & ~Q(status="voided"))`；`UniqueConstraint(fields=["user","client_request_id","type"], condition=Q(client_request_id__isnull=False))` |
| DailySnapshot | `(user, date)` 唯一 |

**约束写在数据库层**，应用层校验只负责给出可读报错；两者都要有，因为并发下只有数据库
约束能兜住。

### 4.3 索引

| 表 | 索引 |
|---|---|
| Transaction | `(user, trade_date)`、`(user, asset, trade_date)`、`(user, status)`、`transfer_group` |
| Channel | `(user)` |
| SIPPlan | `(user, status)` |
| DailySnapshot | `(user, date)` 唯一 |

外键默认建索引，`sip_plan` 不必额外加。

### 4.4 Meta

- `ordering` 只给默认展示用：Transaction 按 `trade_date` 倒序、`id` 倒序
- `related_name` 统一：`transactions`、`prices`、`sip_plans`、`snapshots`
- 资产与价格 `on_delete=PROTECT`；`sip_plan` 用 `SET_NULL`

---

## 五、领域计算

### 5.1 重放

输入是一条持仓行的已确认流水（按 `trade_date`、`id` 排序），输出：

```python
@dataclass(frozen=True)
class Holding:
    shares: Decimal
    cost_original: Decimal      # 原币成本池
    cost_cny: Decimal           # 人民币成本池
    realized_cny: Decimal       # 已实现收益
```

规则：

| 类型 | shares | cost_original | cost_cny | realized |
|---|---|---|---|---|
| opening_balance | += | += amount | += amount × fx_rate | += realized_gain |
| buy | += | += amount（含手续费） | += amount × fx_rate | — |
| sell | −= | −= 结转额 | −= 结转 × 池均价 | += 到账 − 结转 CNY |
| cash_dividend | — | — | — | += amount × fx_rate |
| reinvest_dividend | += | 不变 | 不变 | — |
| share_adjustment | ±= | — | — | — |
| transfer_out | +=（shares 为负） | −= 结转额 | −= 结转 × 池均价 | — |
| transfer_in | += | += amount | += amount × fx_rate | — |

要点：

- **成本价含手续费**：买入把支付总额（含费）计入成本池，与国内平台口径一致；这样确认日
  市值 = 金额 − 手续费，当日自然体现一笔费用损失，不需要另设费用科目
- **结转额按摊薄单价算**：`shares × (cost_original / shares_before)`
- **转移两笔的 `fx_rate` 由服务端写「来源持仓的成本加权汇率」**，不是成交日汇率；
  转入行据此入池，两笔精确抵消。任何情况下都不许前端传这个值
- **CNY 池按比例结转**：`cost_cny × (结转原币 / cost_original_before)`，比值恒为成本加权汇率
- `opening_balance` 多出的「历史已实现收益」存在 `realized_gain` 字段，直接计入 `realized`
- `reinvest_dividend` 只增份额，两池成本都不动——它不是新投入，否则收益会被同一笔分红吞掉两次
- 转移与分红的 `fee`：转移费计入已实现收益的负项，不进成本；分红无费用
- 卖出时 `到账 = amount − fee`，`amount` 是毛额

### 5.2 量化与残值

- 结转额先算全精度，写入前量化到 2 位小数（CNY 池）与 4 位（原币池）
- **份额归零时，剩余成本全部结转，残值强行归零**，不留几分钱挂在空仓上
- 比例结转后若 `cost_cny / cost_original` 与成本加权汇率偏离超过 1e-6，以 CNY 池为准修正

### 5.3 边界

| 情况 | 处理 |
|---|---|
| 份额为 0 时卖出 / 转出 | 抛业务异常，接口返回 400 |
| 成本池为 0（全清仓后再买） | 摊薄单价重新起算，不沿用旧值 |
| 负数成本（低于成本卖出超过池值） | 不允许：结转额上限为池值，差额计入已实现 |
| 汇率缺失 | 折算字段返回 None，不参与汇总 |

### 5.4 年化收益率

- 现金流：`opening_balance` 记 −成本（日期取该笔 trade_date，即用户填的起始日）、买入为负、卖出到账与分红为正、
  期末市值为正；转移视为资产内部移动，**排除**；转移费作为负项计入
- 按「资产」维度算（同资产跨渠道合并），总览再按组合整体算一次
- 用二分法求 `NPV(rate) = 0`，区间 `[-0.9999, 10]`
- 现金流不足两笔、或持仓期过短、或解不在区间内 → 返回 None，前端显示「—」
- 不做牛顿法：导数在极端场景会溢出，二分法稳定且收敛可预期

---

## 六、服务层

| 服务 | 职责 | 要点 |
|---|---|---|
| `positions` | 按 `(asset, channel, venue)` 重放并组装 | 一次查询取全部流水，内存分组；禁止 N+1 |
| `summary` | 总资产、今日涨跌、数据新鲜度 | 今日涨跌读昨日快照差分；无快照则返回 None |
| `transactions` | 创建、确认、撤销 | 状态机集中在服务层；定投生成的 pending 只允许作废不允许物理删除；可用份额要扣除同持仓行未撤销的待确认卖出 |
| `transfers` | 成对创建转出与转入 | 同一事务；来源持仓校验；结转成本由服务计算 |
| `sips` | 排期推导与到期生成 | 由「起始日 + 周期 + 已生成交易」推导下次扣款日与已执行期数（含顺延、排除跳过与作废）；不落库 |
| `snapshots` | 结算、补算、区间重算 | 默认补缺失日期；数据补齐后自动重算当时不完整的日期；完整日期只由显式重算改写 |
| `settings` | 数据源开关、手工价格与汇率 | 手工写入把同日 auto 行升级为 manual，不新增重复行 |
| `exports` | 流水导出、清空数据 | 导出含原币金额、成交汇率、场所；清空按用户维度，不动共享资产字典 |

**取价规则**：`venue=otc` 取 `kind=nav`，`venue=exchange` 取 `kind=close`；查询条件为
`date <= 目标日` 的最近一条，**不允许用未来价格回填历史**。找不到、或最后一条超过陈旧上限
（按 30 个自然日把握），都返回 None 并计入 `missing_price`；不跨 kind 回退，也不用旧价冒充当日。

**取汇率规则**：取 `date <= 目标日` 的最近一条；同币种返回 1；查不到返回 None。

**聚合**：`group=asset` 时按资产合并多渠道多场所行，合并后的成本价用「原币成本 / 份额」重算；
`group=channel` 时按渠道分组，附带小计。

---

## 七、接口实现要点

### 7.1 分页

- `PageNumberPagination`，`page_size=20`、`page_size_query_param="page_size"`、上限 100
- 持仓排序与分页都发生在**领域聚合之后**：先重放并排序全部行，再切片，不能依赖 ORM 排序
- `group=asset` 行键为 `(资产, 场所)`，只合并渠道；`group=channel` 按渠道分页，渠道内嵌资产
- 持仓接口在分页响应外层额外附 `totals`（全量聚合，不受分页影响），含缺价与缺汇率计数

### 7.2 错误体

自定义 `exception_handler`：

- DRF 校验错误 → `{"detail": "第一个字段错误", "fields": {"amount": ["必须为正"]}}`
- 业务异常 → `{"detail": "..."}`
- 未捕获异常 → 500 + 通用文案，日志留堆栈

### 7.3 幂等

创建类接口（记一笔、转移）接受 `client_request_id`，按 `(user, client_request_id, type)` 唯一
（转移两笔类型不同，可同时落库）；重复提交返回首次创建的对象，不再写第二笔。

| 操作 | 已处于目标状态时 |
|---|---|
| confirm | 200，返回当前对象，不重复写 |
| void | 200；若属于转移，连带撤销对侧并返回两笔 |

实现方式：`transaction.atomic()` + `select_for_update()` 锁住目标行；若已是目标状态则
直接返回当前对象（忽略入参），否则更新。**撤销转移必须在同一事务内同时更新两行**，
不允许「一侧已撤销、另一侧还在」。不做「先查再写」的非原子判断。

确认接口请求体：`{shares, nav, fee}`，仅 pending 可确认；`confirm_date` 由服务端取当天写入，
不接受前端传值；已 confirmed 时忽略入参返回 200。

### 7.4 权限

- 全局 `IsAuthenticated`
- 所有 queryset 以 `filter(user=request.user)` 开头
- 详情接口用 `get_object_or_404(model, pk=..., user=request.user)`，不先按 id 取再判断

---

## 八、定时任务

| 命令 | 时机 | 行为 |
|---|---|---|
| `sync_market_data` | 每日 23:30 | 无同步记录的资产从该用户最早已确认交易的 `trade_date` 起回补；其余按「最后成功日 + 1 → 今天」；**按资产 market 的日历决定是否拉价**；只插入缺失，不覆盖 manual |
| `settle_snapshot` | 每日 23:50 | 补算所有缺失日期的快照（含周末，周末沿用上一交易日价格）；缺价或缺汇率时照常写入、当日收益置空；**同步或手工补数后自动重算受影响日期** |
| `generate_sip_orders` | 每日 09:00 | 按「最后成功日 + 1 → 今天」回补，逐日生成；daily 仅在两个市场都开市日生成；固定日期型按 `on_non_trading` 顺延（默认）或跳过，顺延不得跨过下一期原定日期；`by_count` 只计已生成（含顺延），跳过与作废不占期数；按 `(sip_plan, trade_date)` 判重（含作废记录） |

```
# 容器内 cron 必须显式设置时区，否则 23:30 会变成 UTC 07:30
CRON_TZ=Asia/Shanghai
30 23 * * *   docker compose exec -T web python manage.py sync_market_data
50 23 * * *   docker compose exec -T web python manage.py settle_snapshot
0  9  * * *   docker compose exec -T web python manage.py generate_sip_orders
```

三个命令都要可以重复执行，且支持 `--date` 补跑指定日期。快照差分取「最近一个有快照的
日期」，不假设昨天一定存在。

---

## 九、数据源适配

| 接口 | 方法 |
|---|---|
| 价格源 | `fetch_prices(codes, start, end) -> dict[code, list[Price]]` |
| 汇率源 | `fetch_fx(pair, start, end) -> list[Rate]` |

- 适配层捕获网络与解析异常，向上返回「成功 / 失败清单」，不抛到任务层
- 失败清单写入用户设置（`last_sync_failures`），任务失败时非零退出，cron 能报警
- 同步水位按**单个资产**推进，而不是整批：只只失败不会让该资产的历史日期永久跳过
- 单只失败不影响整批
- 请求之间加间隔，避免被限流
- 源不可用时任务成功退出但记录失败清单，页面显示「更新至某日」

---

## 十、测试计划

| 测试类 | 覆盖 |
|---|---|
| ReplayTests | 八种类型的份额与双池变化、部分卖出、清仓再买、负成本保护 |
| TransferTests | 结转成本、两笔同额、跨场所、撤销连带 |
| MetricsTests | 市值、持仓收益、三种收益率、缺价与缺汇率 |
| XirrTests | 一次性买入、定投、中途卖出、不收敛返回 None |
| SnapshotTests | 首次结算、补缺失；完整日期不被改写；缺价日照常写入且 daily_gain 为空；当时不完整的日期在数据回补后自动重算 |
| ApiTests | 分页、totals、错误体、权限隔离、幂等确认 |
| SyncTests | 幂等写入、不覆盖 manual、单只失败不影响整批 |
| SettingsTests | 开关读写、手工价格与汇率升级 auto 行、手工值不被同步覆盖 |
| CalendarTests | 2026 感恩节（11-26）美股休市、11-27 半日市仍算交易日；春节前后中国休市；未知市场退回 CN；超覆盖年份退回工作日 |
| SipScheduleTests | daily 周末不生成；weekly 周一遇休市顺延到周二且占期数；skip 策略不生成不占期数；顺延跨过下一期时丢期并标记 |
| ExportTests | 导出列完整、清空只影响当前用户 |

Domain 层测试全部不碰数据库；服务层与接口层用 Django 的测试数据库。

---

## 十一、迁移与初始化

- 新增 app 只产生**一条**初始迁移，与 accounts 的既有迁移互不影响
- 不预置资产数据；基金按需创建
- 本地联调可用一个管理命令写入示例资产与流水（仅 dev 使用，不进生产镜像流程）

---

## 十二、验收清单

- [ ] 八个交易类型都能正确改变份额与双池成本
- [ ] 部分卖出后摊薄单价不变，累计收益率口径正确
- [ ] 转移不产生现金流、不产生已实现收益，撤销成对
- [ ] 持仓合计与总览数字一致，翻页后合计不变
- [ ] 缺价格或缺汇率时显示「—」，不静默按 1:1
- [ ] 重复确认、重复撤销返回 200
- [ ] 同步任务重跑无重复数据，manual 数据不被覆盖
- [ ] 跨用户访问返回 404 而不是 403（不泄露资源存在性）

---

## 十三、风险与踩坑

| 风险 | 应对 |
|---|---|
| Decimal 与 float 混用 | 领域层只接受 Decimal，接口层入口统一转换；测试里断言类型 |
| 时区导致自然日错位 | `USE_TZ=True` + `TIME_ZONE=Asia/Shanghai`；日期字段只用 `date` |
| 并发确认同一笔 | 状态更新用条件更新（`filter(status=pending).update(...)`），影响行数为 0 即幂等返回 |
| 定投重复生成 | 生成前按 `(sip_plan, trade_date)` 查重，并给该组合加唯一约束兜底 |
| XIRR 不收敛 | 二分法区间固定，超界返回 None，不返回瞎猜的数 |
| 数据源结构变化 | 适配层单测用固定响应样本；解析失败按「整批失败」处理，不写半截数据 |
| 依赖年份过期 | `chinesecalendar` 超出覆盖范围会抛异常；包装函数捕获后退回工作日判定，并让定投页显示告警 |
| 美股规则算错（观测日） | 单测固定断言 2026–2028 的休市日与半日市，另有「遇周六提前、遇周日推迟」用例 |

---

## 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-11-25 | 初稿：模块划分、模型精度与约束、领域计算规则、服务层、接口要点、定时任务、测试与验收 |
| v2 | 2026-11-25 | 移除 CSV 导入相关依赖与范围说明（支付宝无导出，功能取消） |
| v3 | 2026-11-25 | 引入 chinesecalendar（唯一新增依赖）并补 .pyi；新增 calendar 模块与按市场日历的同步/定投规则；补日历测试与超范围兜底 |
| v4 | 2026-11-25 | 依赖一节改为四维判据与逐项结论，去掉「按体积划等级」的一刀切表述 |
| v5 | 2026-11-25 | 六路审查修订：买入成本含费、转移 shares 用加法、快照缺价照常写并自动重算、定投水位回补、cron 时区、取价不晚于目标日、失败清单落库、创建幂等、定投作废与可用份额 |
| v6 | 2026-11-25 | 第三轮复验：确认接口 confirm_date 服务端写、幂等键改三元唯一并补入约束表、快照测试断言拆分 |
| v7 | 2026-11-25 | 第四轮复验：§7.3 的幂等键由二元改为三元，与架构一致 |
| v8 | 2026-11-25 | 定投生成支持 daily 与顺延/跳过策略，补跨周期保护与排期测试 |
| v9 | 2026-11-25 | 补 sips 服务与 by_count 计数口径（只计已生成含顺延，跳过与作废不占） |
