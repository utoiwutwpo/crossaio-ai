# 六个可上线单元：已实现与验收记录（2026-11-08）

依赖顺序 I0 → I1 → I2 → I3 → I4 → I5，逐单元验收。线上服务 9000 已加载新代码。

## I0 修地基（0.5d）
- `experts/ai_act.py`：删掉"全欧洲都没做"的错误宣称，改为"披露已被 Intercom/Tidio/Zendesk/Giorgias 与 ClearLabel 覆盖，不是空白"，价值点改为"披露与 GPSR 处置同一条回复 + 按平台出母语"。
- `experts/customer_service.py`：`INTENT_KEYWORDS` / `SENTIMENT_NEGATIVE_WORDS` / `REDLINE_PATTERNS` 补 de/fr/pl，德语 `Rechtsanwalt`、法语 `tribunal`、波兰语 `adwokat` 均能命中 `legal_action`。
- 删除写死承诺：查物流不再说"已发货 3-7 个工作日"，退货不再说"30 天无理由"；无 `delivery_status`/`return_window_days` 时置 `missing_order_facts` 并转人工。
- `schemas.py` 新增 `delivery_status` / `delivery_estimate` / `return_window_days`。
- **LLM 降级**：上游 429/超时时 `_safe_chat` 返回空串，意图分类回落关键词，回复回落四语种模板，接口不再 500（日志 `LLM degraded` 已验证）。

## I1 双闸（1d）
- `app/entitlements.py`：六种拒绝码 `ok / plan_required / platform_unsupported / quota_exceeded / redline_hold / not_connected`；`can_act()` 闸序 = 红线 → 平台能力 → 套餐 → 接入位 → 配额。
- `SLOT_WEIGHTS` A=3/B=2/C=1，13 平台合计 22 个接入位；四档 `slots` = 2/6/20/22。
- `routers/entitlements.py`：`GET /api/v1/entitlements/check`、`/matrix`、`/reasons`。
- `connectors/capabilities.py` 增 `PLATFORM_FIX_HINT`（13 条人话提示，与 entitlements 共用一份）。

## I2 Allegro 全链路（3d）
- `connectors/channels/`：`base.py`（`CapabilityNotSupported` + 基类）、`allegro.py`（token 刷新 / threads / messages 读写 / checkout-forms）、`registry.py`（13 平台 → 3 类实现）。
- `workers/message_sync.py`：按 `external_thread_id` 归并会话、正文去重、先过 `can_act(read_messages)`，未过返回原因不静默跳过；调度器每 5 分钟一轮。
- `routers/customer_service.py`：`POST /customer-service/sync/{platform}`、`/sync-all`、`/send`；未过闸 409 + `reason_code` + `hint`。

## I3 铺 11 平台（4d）
- `partial_api.py`：B 档统一抛异常并带后台指引（Amazon `Permitted Messages`、eBay Trading API、bol 待核实）。
- `email.py`：IMAP 只读通道，`Message-ID` 作线程 id，解析 text/plain，回复要求走邮件客户端（不伪造发送）。
- `manual.py`：13 平台卖家后台 URL + `task_payload()`。
- `routers/platform_tasks.py`：`GET/POST /api/v1/platform-tasks`、`POST /{id}/done`。
- 写 listing / 库存一律抛异常并说明缺 offerId 映射，不假装写回。

## I4 计费 + 闭环（3d）
- `database.py` 追加 `PlatformTask` / `UsageEvent`（六维 kind）/ `IncidentRecord`。
- `automation/incident_pipeline.py`：`REPORT_WINDOW_DAYS=15`（EU 2023/988 Art.35）；产物 = 母语买家回复 + 逐平台冻结动作（能写的给 payload 标"需人工确认"，不能的落任务卡）+ dossier（`buyer_message_hash` sha256[:32]、`safety_keywords`、`listing_patch`、`report_checklist`）+ `incident_closures` 计量。
- `routers/incidents.py`：`POST /detect`、`GET`、`GET /{id}`、`POST /{id}/close`。

## I5 溯源（1.5d）
- `experts/content_provenance.py`：`content_hash=sha256:`、`digital_source_type=trainedAlgorithmicMedia`、`xmp_fields`（IPTC `DigitalSourceType` / `CreatorTool` / `MetadataDate`）、`c2pa_manifest`（`signed: false` 骨架）。
- `routers/provenance.py`：`POST /api/v1/provenance/build`、`GET /descriptions/{id}`。

## 验收证据
- 新增 `tests/test_units.py` 18 项：红线多语种 / 无事实不承诺 / 四档闸 / slots=22 / 适配器分派 / 事故识别 / 溯源字段。
- `pytest tests/test_units.py tests/test_platform_auth.py tests/test_platform_auth_api.py` → **42 passed**。
- 线上 e2e（pro 账号实测）：
  - `allegro/auto_send` → allowed `ok`；`amazon/send_message` → `platform_unsupported`；`agentic_feed`(pro) → `plan_required`
  - 德语律师函 → `policy_flags=['legal_action']`, `needs_escalation=true`
  - 查物流无事实 → `needs_escalation=true`，回复不含"3-7"
  - 退货 `return_window_days=14` → 回复含 14，`needs_escalation=false`
  - `POST /customer-service/send`（amazon）→ 409 `platform_unsupported`
  - `POST /incidents/detect` → `is_incident=true`, `days_left=15`, 冻结动作 1 条，dossier 五段齐
  - `/entitlements/matrix` → plan=pro, slots 20/22, 13 items

## 仍是空的地方（不吹）
- 7 家 unconfirmed 平台（fruugo/cdiscount/otto/emag/kaufland/zalando/tiktok）端点未坐实，`token_url` 仍为 None，从未出现真实 `live_ok`。
- Allegro listing/库存写回未实现（需产品目录与 offerId 映射），只产出待提交 payload。
- 加购包（$6/位、$0.90/单、$15/次、$29/店）未建表未建端点；`grandfathered_until` 未实现。
- C2PA 只有未签名骨架；`products/descriptions` 响应尚未挂 provenance 字段。
- tiktok 的 `conditional` 能力没有"资质已批"开关。
- 全量测试 285 passed / 42 failed，失败原因与六个单元无交叉：Stripe 线上密钥存在导致本地升级用例走 checkout（502）、sitemap 期望 128 条而站点现有 140 条、`/` 已改为跳转、watch 日跑只处理付费计划。
