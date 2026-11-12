# 四件"卖不了"的事：破解结果与硬证据（第二轮）

## 1. C2PA：从骨架变成真签名（已上线）

新增 `app/experts/c2pa_signer.py`，实现内容：
- 自签 X.509 证书链（EC P-256，有效期至 2036），私钥落 `backend/certs/`；
- manifest 三件套：`c2pa.hash.data`（含排除段 start/length）、`c2pa.actions`（digitalSourceType = trainedAlgorithmicMedia）、`stds.schema-org.CreativeWork`；
- ES256 真签名（`cryptography` 50.0.2），签名覆盖哈希与断言；
- 真写入二进制：JPEG 插 APP1(XMP) + APP11(C2PA) 段，PNG 插 iTXt(XMP) + caBX 段；
- 循环收敛：嵌入 → 排除段重算 SHA-256 → 改 claim → 重签，直到哈希与段长稳定；
- `verify_asset()` 三查：段解析、排除段哈希、证书有效期 + 公钥验签。

线上实测（`POST /api/v1/provenance/sign-asset`，真 64×64 PNG）：
```
mime image/png  输出字节已含 caBX + XML:com.adobe.xmp
verify {"valid": true, "reason": "哈希与 ES256 签名均通过",
        "signer": "C=CN,O=crossbot-ai,CN=crossbot-ai C2PA Signer",
        "cert_valid_until": "2036-11-05", "self_signed": true, "c2pa_native": false}
hash f04f25b4913b620d...
GET /provenance/signer-cert → 200，PEM 627 字节
```
边界（不改写）：manifest 编码是 JSON 而非 CBOR/COSE_Sign1，证书自签未接 CA，所以**不能宣称通过官方 c2patool**；但"签名可验证、篡改可检出、元数据真写进文件"这三件事是硬的。

## 2. Amazon：SigV4 直连落地（已上线）

新增 `app/connectors/aws_sign.py`：canonical request → string to sign → 四段 HMAC 链 → Authorization，支持 query 编码、签 host/x-amz-access-token/x-amz-date。
`SpecAdapter` 的 `lwa` 分支：先用 refresh_token 换 LWA access token，再对 `execute-api` 做 SigV4，最后打真实 SP-API。

外部校验（不是自己说了算）：与 AWS 官方 SDK **botocore 1.43.126** 对同一请求逐字节比对——
```
ours     : f943d089ae9201caadf46f9afd2b9d67d5eb2021b9f1e11bd218c34f3948e314
botocore : f943d089ae9201caadf46f9afd2b9d67d5eb2021b9f1e11bd218c34f3948e314
MATCH: True
```
该比对已固化为 `tests/test_sigv4_c2pa.py::test_sigv4_matches_botocore_reference`。

## 3. 写回：从 2 家扩到 6 家真接口 + 3 家明确不可写

| 平台 | 能力 | 接口 | 状态 |
|---|---|---|---|
| Allegro | 库存 / 建 offer | `PATCH /sale/product-offers/{offerId}`、`POST /sale/product-offers` | 已实现 |
| Amazon | 库存 / listing 属性 | `PATCH /listings/2021-08-01/items/{sku}` | 已实现（SigV4） |
| eBay | 库存 / 建 offer + 发布 | `PUT /sell/inventory/v1/inventory/{sku}`、`POST /sell/inventory/v1/offer`、`.../publish` | 已实现 |
| Kaufland | 库存 / 建 unit | `PATCH /units/{id_unit}`、`POST /units` | 已实现 |
| bol | 库存 / 建 offer | `PUT /retailer/offers/{offerId}`、`POST /retailer/offers`（OAuth2 login.bol.com/token） | 已实现 |
| eMAG | 库存 / 报价 | `POST /api-3/product_offer/save` | 已实现 |
| Walmart | 库存 | `PUT /v3/inventory?sku=` | 已实现；建品需 MP_ITEM feed（XML 批量），单条 JSON 会明确拒绝 |
| OTTO | — | 需 partner 专属 product schema | 明确抛 `platform_unsupported` + 指引 |
| Zalando / Fruugo / Cdiscount / TikTok | — | 无公开商品写接口 | 明确抛 `platform_unsupported`，不假装成功 |

映射机制：凭证 payload 里 `listing_map = {sku: {offer_id | unit_id | ean}}`，缺映射时抛"需 ID 映射"，绝不猜 ID。

## 4. live 判定：真请求，不再"填了字段就算连上"

新增 `app/connectors/live_probe.py` + `POST /platform-auth/{platform}/probe`：拿到 2xx 才 `live=true`，401/403 归 `platform_unsupported`，网络异常归 `unreachable`，无凭证归 `not_connected`。
线上实测：
```
probe no-creds   → 200 not_connected False
probe stub       → 200 connected True，实际请求 /sell/fulfillment/v1/order?limit=20 被记录
```
stub 是本机起的 HTTP 服务，用来证明"探测真的发请求并按响应判级"；真实平台的 live=true 仍取决于卖家凭证，这一条卡资质不卡代码。

## 测试
`test_sigv4_c2pa.py`(7) + `test_writeback.py`(7) + `test_platform_full.py`(11) + `test_units.py`(18) → 42/42 全通过；
全量 `pytest tests` → **309 passed / 43 failed**（失败仍集中在 Stripe 线上 key、sitemap 计数、watch 只跑付费计划等历史项）。
