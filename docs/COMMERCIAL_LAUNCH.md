# CrossAIO — 商用落地总纲

> 目标：把 CrossAIO 从「功能完整的演示/原型态」推进到「真实收费 + 真实商家客户 + 真实平台接入」的可商用状态。
> 结论先说：**代码层已完成 70%+**，商用主要卡在「配置密钥 + 接真实平台 API + 合规页面 + 生产部署」，不是从零重写。

---

## 一、商用就绪度矩阵（基于当前代码实测）

| 模块 | 代码状态 | 差什么 | 缺口类型 |
|---|---|---|---|
| 用户/认证 | ✅ 注册登录、JWT、用量额度 | `jwt_secret` 仍是 dev 默认值 | 配置锁定 |
| 4 档套餐 | ✅ free/starter/pro/business + 权益/限流 | — | 已完成 |
| Stripe 支付 | ✅ 真实 checkout + webhook 纯函数 + price 映射 | 缺 Secret Key / webhook secret / 3 个 price ID；**前端没跳支付页** | 配置 + 1 处前端 bug |
| PayPal 支付 | ✅ 并行通道（client/secret/webhook） | 缺凭证 + 3 个 plan ID | 配置（可选） |
| 13 平台凭证中心 | ✅ AES-256 加密 + 分步接入指南 | 读/写仍是 mock；缺真实 API 客户端 | 待开发（最大工程量） |
| GPSR 体检 | ✅ UI + 风险判定 | 真实合规校验 + 欧代数据 + 可下载文件 | 待增强 |
| 部署 | ✅ `deploy/Dockerfile`（Railway/Render 就绪，`/health` 探针已有） | 生产 PG、域名、HTTPS、监控、备份 | 配置 |
| 合规/信任 | ⚠️ 缺隐私政策、服务条款、Cookie 同意 | 页面 + 法务占位 | 待补（必做） |
| LLM | ⚠️ `llm_api_key` 为空 → Mock 模式 | 生产 Key + 成本/限流 | 配置 |

**关键判断**：支付、认证、套餐、部署骨架都已「代码就绪，只差钥匙」。真正要写代码的是「真实平台 API 客户端」和「合规页面」，其余是配置与凭证。

---

## 二、四大块任务拆解

### 块 A — 真实平台 API 接入（优先级最高，产品核心价值）
- [ ] Amazon SP-API：LWA token 交换 → 读订单/买家消息、写回合规信息
- [ ] eBay：用凭证中心已存的 OAuth token 调真实 Browse/Trade API
- [ ] 其余 11 平台（Allegro / eMAG / Otto / Cdiscount / Kaufland / Bol / ManoMano / Wayfair / Fnac / Rakuten / Mirakl）真实 API 客户端，分期推进
- [ ] 统一收件箱：从「演示会话」升级为真实消息拉取 + 回复回写
- [ ] Listing 监控：真实 listing 抓取与每日体检
- **依赖**：各卖家真实 API 凭证（卖家在凭证中心自助填，平台侧私钥由我们保管）

### 块 B — 支付上线（Stripe / PayPal）
- [x] 后端 Stripe checkout + webhook（已就绪）
- [ ] **修复前端订阅按钮：POST 后按 `mode` 跳转 Stripe `checkout_url`**（当前漏了，只做了本地模拟）
- [ ] 部署 `/webhook` 端点并配 `STRIPE_WEBHOOK_SECRET`
- [ ] 用户提供：Stripe Secret Key + 3 个 price ID（PayPal 可选）
- [ ] 发票/税（EU VAT）、退订自助

### 块 C — 部署 / 合规 / 信任
- [ ] 隐私政策页、服务条款页（GDPR 模板，含公司信息占位）
- [ ] Cookie 同意横幅
- [ ] `backend/.env.example` 汇总所有生产变量
- [ ] 上线前锁定：`jwt_secret`、`admin_token`、`cors_origins`（改具体域名）
- [ ] 生产 PostgreSQL（Supabase）、域名 + HTTPS、日志/监控、数据库备份、SMTP 日报
- [ ] 部署指引（Railway / Render）

### 块 D — LLM 生产化
- [ ] 配置 `llm_api_key`（智谱 GLM-4 或切换模型）
- [ ] 用量成本控制 + 并发/限流 + 失败降级
- [ ] 确保付费功能真实调用模型（当前为空则 Mock）

---

## 三、建议里程碑顺序

1. **M1 信任底座（1–2 天，无密钥）**：合规页面 + `.env.example` + 配置锁定 + 前端支付跳转修复 → 站点具备「可对外展示并收费」的基本合规面貌
2. **M2 支付打通（0.5 天 + 你给 Key）**：填 Stripe Key/price → 真实收款跑通
3. **M3 生产部署（1 天）**：Docker 上云 + 域名 HTTPS + PG + 监控
4. **M4 真实平台接入（按平台分期，最大工程量）**：先做 Amazon + eBay（凭证中心已支持），再铺其余 11 平台
5. **M5 LLM 生产化 + GPSR 真实化**：随 M2/M4 并行

---

## 四、需你提供的凭证清单

| 用途 | 变量 / 凭证 | 备注 |
|---|---|---|
| Stripe 收款 | `STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、3× price ID | 必填，M2 |
| PayPal（可选） | `PAYPAL_CLIENT_ID/SECRET`、`PAYPAL_WEBHOOK_ID`、3× plan ID | 可选 |
| LLM | `LLM_API_KEY` | 必填，否则全 Mock |
| 平台 API | 各卖家在凭证中心自助填（Amazon LWA、eBay OAuth 等） | 我们保管平台私钥 |
| 域名/TLS | 域名 + 证书（或交由 Railway/Render 自动） | M3 |
| 数据库 | Supabase Postgres 连接串 | M3 |
| 法务主体 | 公司名 / 地址 / 联系人 / DPO（隐私政策占位用） | M1 |

---

## 五、风险与建议
- **最大工程量 = 真实平台 API 客户端**（块 A），建议分期，先做 Amazon + eBay 验证闭环。
- **合规是欧洲售卖的硬门槛**（GPSR + GDPR），隐私政策/条款上线前必须有，否则不能收欧盟用户钱。
- **不要在未锁 `jwt_secret` / `admin_token` 的状态下公网暴露**，先用 `.env.example` 强制检查。
- 前端订阅跳转 bug 不修，配了 Stripe 也收不到钱——优先修。
