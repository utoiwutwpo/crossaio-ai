# CrossAIO 架构与订阅设计：拼 13 平台、卖能力不卖数量

> 设计日期：2026-11-08
> 前置事实：13 平台授权已通（`/api/v1/platform-auth`）；通道能力注册表已上线（`app/connectors/capabilities.py`，A2 / B5 / C6，仅 Allegro 可自动外发）

---

## 一、一条原则：能力注册表驱动一切

现在的套餐是"平台数量"思维（free 1 个、pro 3 个、business 无限），但 13 个平台的能力根本不等价：

- Allegro 能读能回，接 1 个等于多一个客服；
- Amazon 只能发订单事务消息，接 10 个也读不到买家咨询；
- Fruugo 没有消息 API，接上只能邮件解析。

所以架构的第一原则是：**任何动作在触达平台前，先过双闸**：

```
动作请求
  ├─ 闸一：套餐是否允许（entitlement）
  └─ 闸二：平台是否支持（capability）
        ↓ 都通过才执行
      执行
        ↓ 任一不过
      返回 409 + reason_code + 修复提示（绝不给"假装成功"）
```

这一个逻辑同时解决了三件事：UI 不出现无效按钮、销售不卖出做不到的功能、客服不被"发送失败但显示成功"坑。

---

## 二、六层架构（每层对应到具体模块）

| 层 | 职责 | 落点 |
|---|---|---|
| L0 授权层 | 13 平台凭证加密存取、OAuth、令牌校验 | `routers/platform_auth.py`、`connectors/auth/*`（**已完成**） |
| L1 能力层 | 每平台 tier / mode / caps；自动外发白名单 | `connectors/capabilities.py`（**已完成**） |
| L2 适配层 | 统一 ChannelAdapter 接口，三种实现 | `connectors/channels/`（**待建**） |
| L3 统一模型 | 会话、消息、订单、商品、账号 | `routers/inbox.py` 现有 conversations/messages，**需扩 platform_account + external_id** |
| L4 AI 层 | 客服（多语种）/ 商品内容 / 合规 | `experts/customer_service.py`、新增 `experts/product_content.py`、`experts/gpsr_incident.py` |
| L5 编排层 | 轮询调度、事件队列、事故闭环 | `scheduler.py` + 新增 `automation/incident_pipeline.py` |
| L6 计费层 | 档位、接入位、用量计量 | `billing.py`（**需重定义**） |

数据流：适配器拉回消息 → 统一模型落库 → AI 层出草稿 → 双闸校验 → 发送或转人工 → 用量计量。

---

## 三、13 平台怎么"拼"：三种适配器，不是十三个

不要为 13 个平台写 13 套代码，写 **3 个适配器类**，平台用配置区分：

| 适配器 | 覆盖平台 | 做什么 | 做不到时 |
|---|---|---|---|
| `ApiChannel` | allegro、tiktok（资质后） | 拉消息、发回复、拉订单、写 listing、写库存 | — |
| `PartialApiChannel` | amazon、amazon_us、ebay、walmart、bol | 拉订单、写 listing/库存；消息按 `permitted_only`/`legacy`/`unverified` 分级支持 | 抛 `CapabilityNotSupported`，UI 显示"此平台不支持 API 读取买家咨询，请去卖家后台" |
| `EmailChannel` + `ManualTask` | otto、kaufland、cdiscount、emag、zalando、fruugo | IMAP 监听平台通知邮件 → 解析成会话；解析失败落"待归档" | 不假装同步成功，明确标"邮件通道" |

关键接口（新增 `connectors/channels/base.py`）：

```python
class CapabilityNotSupported(Exception):
    def __init__(self, platform, action, reason, fix_hint): ...

class ChannelAdapter:
    platform: str
    tier: str                 # A / B / C
    def caps(self) -> dict: ...
    async def fetch_messages(self, account, since) -> list[dict]: ...
    async def send_message(self, account, conv_id, text) -> dict: ...
    async def fetch_orders(self, account, since) -> list[dict]: ...
    async def push_listing(self, account, payload) -> dict: ...
    async def push_inventory(self, account, sku, qty) -> dict: ...
```

**降级契约是这套架构的命门**：B/C 档适配器的 `send_message` 必须抛异常而不是返回 False，路由层统一转成 409 + `fix_hint`。这样商家看到的是"去后台处理"，而不是"已发送"。

---

## 四、双闸校验的返回契约

```python
Decision = {
  "allowed": bool,
  "reason_code": "ok | plan_required | platform_unsupported | quota_exceeded | redline_hold",
  "hint": "升级到 Pro 可在 Allegro 自动发送" | "Amazon 不支持读取买家咨询，请去 Seller Central",
}
```

四种 reason 对应四种 UI 动作：

| reason_code | UI 表现 |
|---|---|
| `plan_required` | 升级按钮 + 对比当前档位差什么 |
| `platform_unsupported` | 置灰 + 跳转平台后台链接 |
| `quota_exceeded` | 显示用量与加购包 |
| `redline_hold` | 强制转人工，不允许一键发送（现有的红线逻辑接进来） |

---

## 五、订阅档位：按"接入位"计费

### 5.1 接入位权重

不同档位的平台，接入与维护成本差 3 倍以上，所以按权重计：

| 档位 | 权重 | 理由 |
|---|---|---|
| A | 3 位 | 消息轮询 + 发送 + 订单 + listing，四套 API |
| B | 2 位 | 订单/listing 可用，消息受限，需分级处理 |
| C | 1 位 | 邮件解析或纯人工，成本最低 |

**13 个全接 = 2×3 + 5×2 + 6×1 = 22 位。**

### 5.2 四档设计（沿用现有 plan key，不破坏代码）

| 档位 | 价格 | 接入位 | 实际能接什么 | AI 客服 | AI 商品内容 | GPSR 事故闭环 | 其它 |
|---|---|---|---|---|---|---|---|
| `free` | $0 | 2 | 1 个 B 或 2 个 C | 草稿 5 次/日 | — | 只提示 | 手动体检 |
| `starter` | $39 | 6 | 3 个 B，或 1B+4C | 草稿 100 次/日 | 10 条/月 | 3 次/月 | 每日体检 + 周报 |
| `pro` | $99 | 20 | **全部 5 个 B + 全部 6 个 C + 1 个 A（正好 Allegro）** | 草稿不限；**A 档可自动发送** | 100 条/月 | 10 次/月 | 每 8h 体检 + 日报 |
| `business` | $299 | 22+ | **13 个全接（含 TikTok 的 A 档）** | 全自动 + 多坐席 | 不限 | 不限 | 近实时 + API + Agentic feed |

这个阶梯是刻意的：**Pro 刚好够接满 B+C 加一个 Allegro，差 2 位接不了 TikTok；Business 才是"13 个全通"。** 卖家想全接就必须上 Business，而不是买个 Pro 慢慢加。

### 5.3 加购包（比涨价更好卖）

| 加购 | 价格 | 对标依据 |
|---|---|---|
| 额外接入位 | $6/位/月 | 让 Pro 客户自己补 TikTok |
| AI 解决工单包 | $0.90/单 | Gorgias 对自动化交互收 $0.90，同价但不强制套餐 |
| GPSR 事故闭环超量 | $15/次 | 含档案生成 + 上报草稿 + 下架任务 |
| 多店铺 | $29/店/月 | 现有模型是一平台一凭证，多店需扩 account |

### 5.4 用量计量维度（现有 UsageLog 只记 AI 调用，要补）

| 维度 | 用途 |
|---|---|
| `ai_calls` | 已有，控 LLM 成本 |
| `messages_handled` | 按会话量定价的备选口径 |
| `ai_resolved` | 未转人工即关闭的工单数（对标 Yuma 的"按解决计费"） |
| `content_items` | listing 生成条数 |
| `incident_closures` | 事故闭环次数 |
| `seats` | 坐席数（Business 起多坐席） |

---

## 六、迁移策略（不能让老客户掉档）

1. **保留 4 个 plan key**：`free / starter / pro / business`，只改内部配额，不改订阅记录里的字符串。
2. **老客户 grandfather 6 个月**：Pro 老客户继续按 $49 续费到 2027-05，之后转 $99。
3. **字段兼容**：`PLANS[x]["platforms"]` 保留但不再读，新增 `slots` / `a_slots`；读配额时 `slots` 优先、`platforms` 兜底。
4. **功能位新增**：`features` 加 `listing_gen`、`gpsr_closure`、`agentic_feed`，`has_feature()` 无需改动。

---

## 七、2026 新战场的挂点：Agentic feed（Business 专属）

ChannelEngine 已经在接 ACP（ChatGPT）/ UCP（Gemini、Copilot）。你不需要接协议，先做到"**商品数据能被 AI 代理读懂**"即可：

- 结构化输出：标准属性、尺寸、材质、适用场景、价格、库存、EU 责任人（GPSR 要求）、安全警示；
- 复用现有 listing 内容层 + 合规体检结果，生成 `agentic_feed.json`；
- Business 档开放导出与 API，Pro 档只能预览。

这一步成本极低（数据本来就有），但站位最早。

---

## 八、开发顺序（四迭代，每迭代都能上线）

| 迭代 | 内容 | 产出 |
|---|---|---|
| **I1（部分已完成）** | 能力注册表 ✅、`/capabilities` 端点 ✅ | 剩下：`can_act()` 双闸 + 409 契约 |
| **I2** | Allegro A 档全链路：轮询 → 会话 → 草稿 → 放行 → 回帖 | 第一个"真能自动回"的样板 |
| **I3** | 邮件通道（IMAP）+ B 档降级按钮 | 覆盖剩余 11 个平台 |
| **I4** | 计费重定义 + 六维计量 + 事故闭环 | 能收钱、能算账、能防事故 |

---

## 九、一句话总结

**平台不是"接得越多越好"，而是"能做的事越多越值钱"**——所以架构用能力注册表驱动降级与计费，档位用接入位权重定价，13 个平台用三种适配器拼，一个双闸兜住所有不该发生的动作。
