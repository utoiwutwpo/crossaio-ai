# CrossAIO AI 客服：能力边界、平台接入与开发方案

> 核对时间：2026-11-08　对象：`D:\Claude\crossbot-ai`（后端 `backend/app`，服务 `http://100.124.185.46:9000/app`）
> 结论一句话：**大脑够用，手脚没接上；13 个平台里真正能程序化收买家消息的只有 1 个半。**

---

## 一、这个 AI 客服现在到底能解决什么

### 1. 已经真能干的（代码里跑得通）

| 能力 | 实现位置 | 实际效果 |
|---|---|---|
| 意图分类 | `experts/customer_service.py:20` `INTENT_KEYWORDS` | 物流 / 退货 / 投诉 / 产品咨询 四类，关键词命中即判定，未命中走 LLM 兜底 |
| 情感检测 | 同上 `detect_sentiment` | 负面词计数 ≥2 判 `very_negative`，触发转人工 |
| 政策安全红线 | `REDLINE_PATTERNS`（5 类：差评威胁 / 退款勒索 / 人身伤害 / 法律诉讼 / 假货指控） | 命中即切换为固定安抚话术、**不承诺退款、不认责**、强制转人工，并给出留证提示 |
| GPSR 安全事件 | `compliance_workflow.is_safety_incident` → `compliance_priority_reply` | 买家提到受伤/起火/进医院，优先输出当地语言安全指引 + EU 2023/988 Art.35 的 15 天 Safety Gate 上报提示 |
| EU AI Act 身份披露 | `ai_act.identity_text` | 按平台语言加"我是 AI 助手"声明（Art.50） |
| 合规上下文注入 | `handle()` 的 `compliance_block` | 把最近一次 GPSR 体检未通过项塞进 prompt，回答时不虚构合规状态 |
| 差评→Listing 改写 | `routers/customer_service.py` P0-4 | 只生成/导出，不自动发布 |

**这套东西的真实价值**：它不是"会聊天的客服"，是"知道哪些话不能说的客服"。红线层拦截的是会造成真实资金损失的场景（退款勒索、假货指控、法律威胁），这是通用 AI 客服最容易翻车的地方，也是这个项目唯一别人不容易抄的部分。

### 2. 看着有、其实不能用的（半成品）

| 现象 | 证据 |
|---|---|
| 收件箱没有真实消息源 | `routers/inbox.py:6-7` 自己写明"实时消息同步连接器未实现；会话可通过手动导入或 /seed-demo 演示数据创建" |
| 连接器只有 1 个 active | `connectors/__init__.py`：eBay `active`，其余 7 个全 `pending` |
| 回复只落库，发不出去 | `inbox.py` 的 `/conversations/{id}/reply` 只写库；`customer_service.py:87` 明注"无自动发送端点" |
| Amazon 连接器只是状态推导 | `inbox.py:197` `/connectors/amazon/status` 只做本地三态推导，不发外部请求 |

### 3. 三个会直接制造事故的硬编码（必须先改）

| 风险 | 代码 | 后果 |
|---|---|---|
| **物流状态是编的** | `_tracking_reply()` 写死"已发货，预计 3-7 个工作日送达"，旁边就是 `# TODO 接入 17track / AfterShip` | 买家拿着这句去开纠纷，平台判卖家虚假陈述 |
| **退货政策是编的** | `_return_reply()` 写死"30 天无理由退货" | 卖家实际政策若不是 30 天，AI 已经替卖家做了承诺，构成对买家的合同性表述 |
| **非中英文买家直接失灵** | `INTENT_KEYWORDS` / `SENTIMENT_NEGATIVE_WORDS` / `REDLINE_PATTERNS` 全部只有 en + zh | 德语 "Ich schalte einen Anwalt ein"（我要找律师）命中不了 `legal_action`；波兰语投诉被判 neutral；回复永远是"英文/中文"双语，波兰买家收到的不是波兰语 |

第三条尤其严重：既然上一轮已经做了 EN/DE/FR/PL 四语种授权层，客服层却仍是中英双语，等于**四语种只做到"能连上"，没做到"能对话"**。

---

## 二、能不能接入跨境店铺客服？按平台能力分三档

| 档位 | 平台 | 买家消息能否程序化收发 | 说明 |
|---|---|---|---|
| **A. 可收发** | `allegro` | ✅ REST `/messaging` 可读可回 | 13 个里唯一确定能全自动的 |
| **A. 可收发（需资质）** | `tiktok` | ⚠️ 需 TikTok Shop 合作方资质审核 | 拿到资质后可全自动 |
| **B. 受限** | `amazon` / `amazon_us` | ⚠️ SP-API 只有 **Permitted Messages**（订单事务类，可发不可读） | 买家主动咨询没有公开 API，只能在 Seller Central 里看，**做不到收件箱同步** |
| **B. 受限** | `ebay` | ⚠️ Trading API 消息接口可收发，属老接口 | 需申请对应权限，稳定性一般 |
| **B. 待核实** | `bol` / `walmart` | ⚠️ 有卖家 API，买家消息能力尚未逐个坐实 | 需要卖家账号验证 |
| **C. 只能人工/邮件** | `otto` `kaufland` `cdiscount` `emag` `zalando` `fruugo` | ❌ 无公开卖家消息 API | 平台以邮件通知或卖家后台留言，只能邮件解析或 RPA |

**这个结论要纠正一个常见误解**：Amazon 号称"API 最全"，但它的 SP-API Messaging 设计初衷是**订单事务通知**（发货、退款、定制确认），不是买家咨询收件箱。想靠它做"AI 自动回买家咨询"是走不通的，强行做反而违反 Buyer-Seller Messaging 政策。

---

## 三、GitHub 上有什么可用的（实测数据，2026-11-08）

| 项目 | Stars | 最近提交 | 语言 / 许可 | 能拿来做什么 | 能不能直接接 13 平台 |
|---|---|---|---|---|---|
| `chatwoot/chatwoot` | 39,048 | 2026-11-07 | Ruby | 开源全渠道客服台，有 **API channel**（可程序化投喂消息 + 回调 webhook） | ❌ 无任何 marketplace 渠道，接不到平台 |
| `langgenius/dify` | 160,618 | 2026-11-07 | Python | AI 应用平台：RAG 知识库、工作流、多模型，纯 HTTP API 可被 FastAPI 调用 | 不负责接平台，负责"答得准" |
| `n8n-io/n8n` | 209,757 | 2026-11-07 | TypeScript | 无代码编排，把邮件/表单/Webhook 搬进系统 | 可用于 C 档平台的邮件搬运 |
| `RasaHQ/rasa` | 21,373 | 2026-07-24 | Python / Apache-2.0 | 本地 NLU，私有化部署 | 重，不建议 |
| `botpress/botpress` | 14,985 | 2026-11-06 | TS / MIT | 对话机器人搭建 | 与现有专家层重复 |
| `baptisteArno/typebot.io` | 10,609 | 2026-11-07 | TS | 表单式对话 | 不适合售后场景 |
| `zammad/zammad` | 6,091 | 2026-11-06 | Ruby / AGPL-3.0 | 工单式客服台，邮件通道强 | ❌ 同样无 marketplace 渠道 |
| `papercups-io/papercups` | 6,123 | 2024-02-15 | Elixir / MIT | 网页聊天 | 已两年未更新，不建议 |
| `freescout-help-desk/freescout` | 4,646 | 2026-11-07 | PHP / AGPL-3.0 | 轻量共享邮箱 | 只解决 C 档邮件 |
| `erxes/erxes` | 4,113 | 2026-11-07 | TS | CX 平台（营销+销售+客服） | 过重，且无平台渠道 |
| `chaskiq/chaskiq` | 3,582 | 2026-06-30 | TS | 聊天 + AI | 社区活跃度下滑 |

### 关键判断

**GitHub 上没有任何一个项目能直接接这 13 个跨境平台的买家消息。** Chatwoot、Zammad、Freescout 的"全渠道"指的是网页聊天、邮件、WhatsApp、Telegram、Messenger —— 跨境平台一个都不在里面。所以"装个开源客服台就解决问题"是幻觉，真正的工作量在**平台适配层**，这块社区是空白。

能复用的只有三样，且都不在"接平台"这条链上：

1. **Chatwoot 的会话模型与客服台交互** —— 参考它怎么设计 inbox / conversation / assignment / canned response / SLA 视图，自己照做，不引入 Ruby。
2. **Dify 的 RAG 与工作流** —— 用它替掉现在"把买家问题直接丢给 LLM"的做法，让回答基于真实商品资料、物流数据、退货政策，从根上消灭编造。
3. **n8n 的邮件搬运** —— C 档 6 个平台只能靠邮件通知，用 n8n 起 IMAP 监听比自写更省事。

---

## 四、开发方案（唯一路线，不做备选）

### 核心架构：四层，各管一件事

```
平台层（13 个）
   ↓ 通道适配（channels/）— 三档降级：API 直连 / 邮件解析 / 人工粘贴
消息中枢（conversations / messages 统一模型）
   ↓
AI 层（语言检测 → 多语种意图 → 红线 → 检索真实政策与物流 → 草稿）
   ↓
商家工作台（统一收件箱：分配 / 模板 / SLA / 一键放行）
```

### 阶段 1：把"假话"换成"真数据"（约 2 天，风险最高，先做）

1. `_tracking_reply()` 删除硬编码，接 17track 或 AfterShip（`TODO` 已留好位置），查不到就回"正在核实，稍后同步"，**绝不报预计天数**。
2. `_return_reply()` 的退货政策改为读卖家配置（`platform_credentials` 里加一个 `policy` 字段），未配置时只说"我帮您转人工确认退货政策"。
3. 新增 `policy_guard`：任何含"退款/退货/赔偿/时效承诺"的 AI 输出，若没有对应配置来源，直接降级为转人工。

### 阶段 2：四语种打通到对话层（约 3 天）

1. 引入语言检测（`langdetect` 或轻量 n-gram），按买家语言回复，默认 en。
2. `INTENT_KEYWORDS` / `SENTIMENT_NEGATIVE_WORDS` / `REDLINE_PATTERNS` 全部扩到 en/de/fr/pl —— 红线尤其关键，德语 `Anwalt`（律师）、波兰语 `pozywam do sądu`（起诉）、法语 `contrefaçon`（假货）必须能命中。
3. 复用已建好的 `app/i18n` 层，把回复模板也纳入四语种，避免现在"英文/中文"双语硬拼。

### 阶段 3：接平台（按档位分三次上线）

1. **A 档**：Allegro `/messaging` 全自动（拉消息 → 建会话 → AI 草稿 → 人工放行 → 回帖）。这是唯一能做出"自动回复"效果的，先跑通它做样板。
2. **B 档**：Amazon 只做 **Permitted Messages** 的订单事务类自动通知（发货、退款进度），买家咨询用"跳转 Seller Central 处理"按钮，明示不支持自动读；eBay 走 Trading API 消息；bol/walmart 拿真实账号验证后补。
3. **C 档**：邮件通道（IMAP 监听 + 平台通知模板解析），解析成功即建会话，解析不准就落"待人工归档"，**不假装成功**。

### 阶段 4：商家管理体验（约 4 天，决定好不好用）

| 功能 | 为什么商家需要 |
|---|---|
| 统一收件箱 + 平台色标 | 13 个后台来回切换是最大时间浪费 |
| 会话分配 + SLA 倒计时 | 平台考核首响时长，超时直接扣分 |
| AI 草稿 + 一键放行 | 红线类消息零自动发送，普通咨询人工一键过 |
| 模板库（四语种） | 80% 咨询是重复问题，模板 + 变量比 AI 更快更稳 |
| 平台能力提示条 | 在 Amazon 会话上直接标"此平台不支持 API 回复，请去后台" |
| 每日看板 | 首响时长、未处理数、红线命中数、各平台分布 |

---

## 五、为什么不自研全部、也不整包上 Chatwoot

- 整包上 Chatwoot：多一套 Ruby 服务要养，且它的渠道列表里没有 marketplace，接平台仍要自己写适配 —— 白多一层运维。
- 全自研到底：会话分配、SLA、模板、快捷回复这些是纯工程活，照 Chatwoot 的交互抄即可，不需要它的代码。

**结论：工作台继续做"大脑 + 适配层"，客服台 UI 自己长；Dify 只用来把回答喂准，n8n 只用来搬邮件。**

---

## 六、现状与目标差距一览

| 项 | 现在 | 目标 |
|---|---|---|
| 真实消息源 | 0 个平台（仅演示数据） | A 档全自动 + B 档受限 + C 档邮件 |
| 四语种 | 授权层有，对话层无 | 意图/红线/回复全语种 |
| 出站发送 | 无 | A 档直发，其余生成草稿 + 跳转 |
| 承诺类话术 | 3 处硬编码 | 全部来自卖家配置，缺失即转人工 |
| 商家管理功能 | 只有会话列表 | 分配 / SLA / 模板 / 看板 |
