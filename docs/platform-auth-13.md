# CrossAIO 13 平台店铺授权接入说明

> 适用项目：`D:\Claude\crossbot-ai`（后端 FastAPI，服务端口 9000，接口前缀 `/api/v1`）
> 落地时间：2026-11-07　状态：**已上线并通过 20 项自动化测试**

## 一、目标与范围

把工作台注册表里的 **13 个跨境平台**做成统一的店铺授权接入，并让 **EN / DE / FR / PL 四语种同时可用**。

平台清单（顺序固定，与 `PLATFORM_ORDER` 一致）：

| # | platform | 平台 | 授权类型 | 必填字段 | 端点核实 |
|---|---|---|---|---|---|
| 1 | `amazon` | Amazon 欧洲站 | LWA refresh_token | client_id / client_secret / refresh_token | ✅ 已核实 |
| 2 | `amazon_us` | Amazon 美国站 | LWA refresh_token | 同上 | ✅ 已核实 |
| 3 | `ebay` | eBay | OAuth2 授权码 | client_id / client_secret | ✅ 已核实 |
| 4 | `fruugo` | Fruugo | API Key | merchant_id / api_key | ⚠️ 待核实 |
| 5 | `walmart` | Walmart | OAuth2 客户端凭证 | client_id / client_secret | ✅ 已核实 |
| 6 | `cdiscount` | Cdiscount | 传统 Key | api_key / seller_login | ⚠️ 待核实 |
| 7 | `otto` | Otto | OAuth2 客户端凭证 | client_id / client_secret | ⚠️ 待核实 |
| 8 | `allegro` | Allegro | OAuth2 授权码 | client_id / client_secret | ✅ 已核实 |
| 9 | `emag` | eMAG | API Token | api_key | ⚠️ 待核实 |
| 10 | `kaufland` | Kaufland | Header Key | client_key / secret_key | ⚠️ 待核实 |
| 11 | `bol` | bol.com | OAuth2 客户端凭证 | client_id / client_secret | ✅ 已核实 |
| 12 | `zalando` | Zalando | OAuth2 客户端凭证 | client_id / client_secret | ⚠️ 待核实 |
| 13 | `tiktok` | TikTok Shop | OAuth2 授权码 | app_key / app_secret | ⚠️ 待核实 |

**6 家已核实（confirmed）**：amazon、amazon_us、ebay、walmart、allegro、bol —— 可以发起真实令牌校验、可以生成 OAuth 跳转地址。
**7 家待核实（unconfirmed）**：fruugo、cdiscount、otto、emag、kaufland、zalando、tiktok —— 只做凭证形状校验，**代码里不写任何未核实的 URL**，避免臆造端点导致商家反复试错。

## 二、GitHub 参考（只作协议形状参考，运行时零依赖）

调研结论：Python 生态里可直接用的库只有 6 家，且多为 2018–2023 的旧代码，与项目现有 Python 3.13 + fastapi 0.115 环境不兼容。因此**不 vendor 这些库**，只用它们的实现作为字段与流程形状的交叉验证，运行时统一走项目已装好的 `httpx`。

| 平台 | 参考仓库 | Stars |
|---|---|---|
| Amazon | `saleweaver/python-amazon-sp-api` | 691 |
| eBay | `timotheus/ebaysdk-python` | 857 |
| Allegro | `chawel/python-allegro` | 27 |
| eMAG | `chawel/python-emag` | 7 |
| bol.com | `pennersr/python-bol-api` | 13 |
| Walmart | `whitebox-co/walmart-marketplace-api`（TS） | 31 |
| Kaufland | `hitmeister/api-sdk-php`（PHP） | 25 |
| Otto | `otto-de/marketplace-php-sdk`（PHP） | 5 |
| Zalando | `sbaumeister/zalando-zdirect-client-php`（PHP） | 1 |
| Cdiscount | `yangguo306/cdiscount-sdk` | 1 |
| TikTok Shop | `EcomPHP/tiktokshop-php`（PHP） | 216 |
| Fruugo | 无公开仓库 | — |

## 三、API 一览（前缀 `/api/v1/platform-auth`）

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/specs` | 否 | 13 平台规格 + 四语种文案（凭证中心表单的数据源） |
| GET | `/matrix` | 是 | 13 平台 × 4 语种 × 授权状态矩阵 |
| POST | `/{platform}/credentials` | 是 | 保存凭证（AES 加密入库，允许分步填写） |
| GET | `/{platform}/credential` | 是 | 查看哪些字段已配置（只回 `set` / `length`，**绝不回明文**） |
| DELETE | `/{platform}/credentials` | 是 | 解绑 |
| POST | `/{platform}/verify` | 是 | 校验；`?live=true` 时对 confirmed 平台发起真实令牌校验 |
| POST | `/verify-all` | 是 | 已配置平台一次性并发校验 |
| GET | `/{platform}/authorize-url` | 是 | 生成 OAuth 跳转地址（仅 ebay / allegro） |
| POST | `/{platform}/exchange` | 是 | 授权码换令牌，令牌直接写入加密存储，响应只回布尔 |

## 四、六态状态机（四语种同时返回）

`unconnected` → `pending` → `connected` → `live_ok` / `live_fail` / `live_unavailable`

- `pending`：字段缺失、占位符、含空格、密钥长度不足 8 位
- `connected`：形状校验通过
- `live_ok`：真实换取成功（仅 confirmed 平台）
- `live_fail`：平台明确拒绝
- `live_unavailable`：该平台无核实端点，或网络不可达

波兰语文案示例：`connected` → `Połączono (format zweryfikowany)`。

## 五、与现有前端的关系（重要）

现有凭证中心页面（`app/static/index.html`）走的是 `/api/v1/compliance/credentials/{platform}`，**写入的正是同一张 `platform_credentials` 表、同一套 AES 加密**。所以：

- 商家在现有 UI 里填好的凭证，本模块的 `/matrix`、`/verify` **可以直接读到并校验**——两边不需要迁移数据。
- 前端目前缺的只是「校验」「去授权」两个按钮，后端接口已经就绪。

## 六、已验证结论（2026-11-07 实测）

1. `pytest tests/test_platform_auth.py tests/test_platform_auth_api.py -q` → **20 passed**。
2. 线上服务 `GET /api/v1/platform-auth/specs` → 200，`total=13 confirmed=6 langs=en,de,fr,pl`。
3. 未带 token 访问 `/matrix`、`/credentials`、`/verify-all` → 401，鉴权生效。
4. 用假凭证打真实端点，返回的是平台级拒绝而非超时：
   - bol → 401 `{"error":"invalid_client"}`
   - amazon → 401 `Client authentication failed`
   - walmart → 400 `Bad Request`
   说明外网连通、端点地址正确、请求形状基本对齐。

## 七、遗留事项

1. 7 家 unconfirmed 平台的授权端点仍需按官方入驻文档逐个坐实（拿到卖家账号后可一次性补齐）。
2. 真实 `live_ok` 尚未出现过——需要至少一组真实卖家凭证。
3. 前端凭证中心尚未挂「校验 / 去授权」按钮。
4. 授权结果尚未回灌到消息同步链路：`routers/inbox.py` 仍不读这些凭证收消息，`customer_service` 仍无自动发送端点。

## 八、文件清单

```
backend/app/i18n/__init__.py            四语种导出
backend/app/i18n/locales.py             PL 语言包 + 状态机四语种 + 矩阵组装
backend/app/connectors/auth/__init__.py
backend/app/connectors/auth/spec.py      13 平台规格表 + stage 诚实分级
backend/app/connectors/auth/providers.py 形状校验 + 真实令牌校验 + 授权码换取
backend/app/routers/platform_auth.py     9 个端点
backend/tests/test_platform_auth.py      13 项单元测试
backend/tests/test_platform_auth_api.py  7 项接口级端到端测试
backend/app/main.py                      + import、+ include_router（前缀 /api/v1/platform-auth）
```
