# CrossAIO 架构开发路线（可执行版）

> 依据：六层架构设计 + 13 平台能力注册表（已上线）+ 竞品/合规报告的 P0 清单
> 原则：每一步都能单独上线，不堆积半成品；拒绝码统一；先跑通 1 个 A 档再铺量

---

## 依赖关系

```
I0 修地基（0.5d）
  └─ I1 双闸（1d）
       ├─ I2 Allegro A 档全链路（3d）
       │    └─ I3 覆盖剩余 11 平台（4d）
       │         └─ I4 计费 + 事故闭环（3d）
       └─ I5 C2PA 标记（1.5d，12-02 前必须）
```

I5 与 I2 可并行，两者互不依赖；其余严格串行。

---

## I0 · 修地基（0.5 天，先做，因为它决定后面所有判断）

| # | 文件 | 动作 | 验收 |
|---|---|---|---|
| 1 | `app/experts/ai_act.py` | 删掉"2026 全欧洲客服/CS 工具均未内建"的错误注释，改为"披露文本已内置，是否展示取决于调用方传 language" | 全文搜索无该措辞 |
| 2 | `app/billing.py` | `pro.auto_writeback` / `business.auto_reply` 注释与实现对齐（改为"需人工确认/未接入写回"）；`can_auto_writeback()`、`can_auto_reply()` 改为叠加 `capabilities.supports()` 判定 | 对 amazon 调 `can_auto_reply()` 返回 False |
| 3 | `app/experts/customer_service.py` | `REDLINE_PATTERNS` 补 de/fr/pl 关键词（Anwalt / Rechtsanwalt / avocat / adwokat / pozew…）；`INTENT_KEYWORDS` 同步补齐 | 德语"我要找律师"命中 legal 红线 |
| 4 | 同上 | 删除 `_tracking_reply` 写死的"3-7 个工作日"、`_return_reply` 写死的"30 天无理由"；改为读卖家 policy 配置，未配置时返回"需人工确认"并转人工 | 无 policy 配置时输出不含任何时效承诺 |
| 5 | `app/routers/workbench_pro.py` | 清理 11 个接口 summary 里的旧黑话 | `/openapi.json` 不含该词汇 |

测试：新增 6 条断言（红线命中、无 policy 不承诺、can_auto_reply 受 capability 约束）。

---

## I1 · 双闸（1 天）

新增 `app/entitlements.py`：

```python
REASON = ("ok", "plan_required", "platform_unsupported",
          "quota_exceeded", "redline_hold")

def can_act(user, platform: str, action: str, quota_left: int | None = None) -> dict:
    """action ∈ read_messages / send_message / write_listing / auto_send / content_gen"""
    # 1) 平台能力
    if action in CAPABILITY_KEYS and not supports(platform, action):
        return {"allowed": False, "reason_code": "platform_unsupported",
                "hint": fix_hint(platform, action)}
    # 2) 套餐
    plan = plan_config(user.plan)
    if not plan_allows(plan, action, platform):
        return {"allowed": False, "reason_code": "plan_required",
                "hint": "升级到 Pro 可在 Allegro 自动发送"}
    # 3) 配额
    if quota_left is not None and quota_left <= 0:
        return {"allowed": False, "reason_code": "quota_exceeded", ...}
    return {"allowed": True, "reason_code": "ok", "hint": ""}
```

- 所有动作端点前置调用；拒绝统一返回 `409` + `{reason_code, hint, platform, action}`
- 新增 `GET /api/v1/entitlements/check?platform=&action=` 供前端预判按钮状态
- `fix_hint()` 内置每平台人话：amazon → "Amazon 无收件箱读取权限，请去 Seller Central 处理"

验收：四种 reason 各一例；`amazon + send_message` → `platform_unsupported`；`free + allegro + auto_send` → `plan_required`。

---

## I2 · Allegro A 档全链路（3 天，第一个"真能自动回"的样板）

| 文件 | 内容 |
|---|---|
| `app/connectors/channels/base.py` | `ChannelAdapter` 协议、`CapabilityNotSupported(reason, fix_hint)`、`Message/Conversation` DTO |
| `app/connectors/channels/allegro.py` | `fetch_messages()` 拉 `/messaging/threads`、`send_message()` 回帖、`fetch_orders()`、`push_listing()` |
| `app/connectors/channels/registry.py` | `get_adapter(platform)`，按 `capabilities.CHANNELS[p]["mode"]` 选实现 |
| `app/workers/message_sync.py` | APScheduler 轮询，间隔读 `AUTOMATION_INTERVALS`；按平台 tier 定基础频率（A 档 60s 起） |
| `app/routers/inbox.py` | 从 adapter 拉数据落库，替代 `/seed-demo`；保留手动导入入口 |
| `app/routers/customer_service.py` | 草稿生成后走 `can_act` → 通过则入 outbox，等待确认或按 plan 自动发 |

关键约束：令牌来自 `platform_credentials`（与现有凭证中心同表同加密），不新建存储。

验收：真实/沙箱凭证拉取成功 → 会话落库 → 生成草稿 → `can_act` 放行 → 回帖返回平台 message id，全链带 trace id；失败时返回平台原始错误码而不是吞掉。

---

## I3 · 覆盖剩余 11 平台（4 天）

| 文件 | 覆盖 |
|---|---|
| `channels/partial_api.py` | amazon、amazon_us、ebay、walmart、bol：订单/listing/库存可用；`send_message` 按 caps 抛 `NotSupported`（`permitted_only` → "仅订单事务消息"；`unverified` → "未核实，请去后台"） |
| `channels/email.py` | otto、kaufland、cdiscount、emag、zalando、fruugo：IMAP 收平台通知邮件 → 解析成会话；解析失败落"待归档"，不标记为已同步 |
| `channels/manual.py` | 无 API 场景：生成任务卡（平台 + 链接 + 建议回复），卖家点"处理完"归档 |
| `routers/platform_tasks.py` | 任务卡列表 / 完成 / 导出 |

验收：13 平台逐个跑 `sync`；B 档返回 409 + 正确 hint；C 档邮件解析覆盖 3 类模板（订单、退货、投诉）。

---

## I4 · 计费 + 事故闭环（3 天）

**计费**
- `billing.py` 四档改接入位（free 2 / starter 6 / pro 20 / business 22），`platforms` 保留兜底
- 新表 `usage_events(kind, qty, ref_id, created_at)`：`ai_calls / messages_handled / ai_resolved / content_items / incident_closures / seats`
- `has_feature()` 增加 `listing_gen / gpsr_closure / agentic_feed`
- 老客户 grandfather：`grandfathered_until` 字段，读价时优先

**事故闭环**（`app/automation/incident_pipeline.py`）
```
is_safety_incident(msg)
  → 冻结 SKU（capabilities 允许则调平台写库存，否则生成下架任务卡）
  → 生成事故档案（产品/批次/买家/时间/描述/证据编号）
  → safety_gate 生成 15 天倒计时草稿
  → listing_backfill 产出各平台改写 payload（不自动提交，走确认）
  → usage_events 记 incident_closures
```

验收：输入"锅起火了" → 一次调用产出 4 个产物 + 倒计时；计量 6 维各有数据；无写权限的平台降级为任务卡而不是报错。

---

## I5 · C2PA / IPTC 标记（1.5 天，卡 2026-12-02）

新增 `app/experts/content_provenance.py`：

```python
def build_provenance(platform, model, text, extra=None) -> dict:
    """返回可写入 XMP/IPTC 的字段 + C2PA 声明骨架"""
    # dc:creator / Iptc4xmpExt:DigitalSourceType = trainedAlgorithmicMedia
    # 附 model、生成时间、内容 hash、生成参数摘要
```

- `products.py` 的 `descriptions/generate`、`market-matrix` 响应增加 `provenance` 字段
- 新增 `GET /api/v1/products/{id}/provenance` 导出 sidecar JSON
- 前端文案区提供"AI 辅助生成"可见标注开关（默认开）

验收：生成一条描述 → 返回 provenance 含 AI 标识/model/时间/hash；导出 sidecar 可被解析。

---

## 上线判据（每一步都要能回答这三问）

1. `curl` 能不能拿到期望状态码与字段？
2. 失败时返回的是**明确原因**还是"未知错误"？
3. 关掉某个平台凭证，系统是否**降级而不是崩溃**？

三问有一个答不上，就不算完成。
