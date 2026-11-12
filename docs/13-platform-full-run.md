# 13 平台全打通收尾记录（2026-11-08）

## 一、这一轮真正落地的代码（已部署 `D:\Claude\crossbot-ai`，已重启 9000）

| # | 文件 | 作用 |
|---|---|---|
| 1 | `app/connectors/channels/spec.py` | 13 平台端点规格表：base / 鉴权方式 / 订单路径 / 消息路径 / 写回路径 / 文档链接 / `verified`（official / inferred / portal） |
| 2 | `app/connectors/channels/regional.py` | 规格驱动 `SpecAdapter`：basic、header_keys、bearer、oauth2_cc、tiktok_sign（HMAC-SHA256）；订单归一化；TikTok 收发消息；Allegro / Kaufland 写库存 |
| 3 | `app/connectors/channels/registry.py` | 13 平台分派：allegro 专用 → 7 家规格驱动 → 邮件 / 人工 / 部分 API 兜底；`describe()` 带 `endpoint_verified` + `docs_url` |
| 4 | `app/connectors/channels/allegro.py` | 真实写回：`PATCH /sale/product-offers/{offerId}` 改库存、`POST /sale/product-offers` 建 offer；缺 offerId 抛带指引的异常 |
| 5 | `app/connectors/capabilities.py` | 7 家从 manual/email 升级为 api：otto、emag、kaufland、zalando、cdiscount、fruugo；kaufland 补 `write_inventory=True` |
| 6 | `app/database.py` | 新增 `AddOnPurchase` 表 |
| 7 | `app/billing.py` | `ADDON_CATALOG` 四档：extra_shop $29 / extra_seat $6 / auto_reply $0.90 / incident $15 |
| 8 | `app/entitlements.py` | 加购接入位并入 `plan_slots`；`addon_credits` 扣减已消耗；`partner_approved` 解锁 TikTok 消息；套餐不含发送时可用加购额度放行 |
| 9 | `app/routers/billing.py` | `GET/POST /billing/addons`：目录、已购、余额（extra_slots / auto_reply_credits / incident_credits） |
| 10 | `app/routers/platform_auth.py` | `POST /{platform}/qualification`（TikTok 资质开关）；`/capabilities` 增加 `endpoints` + `verified_counts` |
| 11 | `app/schemas.py` + `app/routers/products.py` | `ProductDescriptionResponse.provenance`，单条与矩阵逐项写入 `build_provenance()` |
| 12 | `tests/test_platform_full.py` | 11 项：13 平台规格齐备、端点可信度、适配器分派、缺凭证抛 not_connected、Amazon 需 SigV4、Allegro 缺 offerId、加购价目、provenance 字段 |

## 二、线上实测（`100.124.185.46:9000`，新注册账号）

```
capabilities 200 total 13 verified {'official': 11, 'inferred': 1, 'portal': 1}
modes: 13 家全部 api（amazon/amazon_us 为 api_limited）
addons GET 200  catalog 四项齐全 balance {0,0,0}
addons POST 200  买 10 单 auto_reply → amount 9.0 → balance auto_reply_credits 10
qualification 200 {'partner_approved': True}
gate tiktok/send_message 200 allowed=True reason=ok tier=A（资质 + 加购额度放行）
products/descriptions/generate 200  provenance 含 content_hash=sha256:...、source_id、generated_at
```

测试：`test_platform_full + test_units + test_platform_auth + test_platform_auth_api` → **53 passed**；
全量 `pytest tests` → **296 passed / 42 failed**（失败集与本轮无交叉：Stripe 线上 key、sitemap 数量、`/` 跳转、watch 只处理付费计划等历史项）。

## 三、还没到"能对外卖"的部分（诚实清单）

1. **C2PA 仍是未签名骨架**：`c2pa_manifest.signed = False`，没有证书链、没有 COSE 签名，也没有把 XMP/IPTC 真写进图片或文档二进制。目前只能提供内容哈希与声明字段，不能对外举证。
2. **Amazon 未直连**：SP-API 需 AWS SigV4 四段密钥，`SpecAdapter` 遇到 lwa 直接抛 not_connected（带指引），实际订单/消息仍需 Seller Central 或官方 SDK。
3. **写回只坐实了 Allegro（listing + 库存）与 Kaufland（库存）**：其余 10 家的 listing / 库存仍缺"SKU → 平台 ID + 类目 schema"映射，只生成待提交 payload，未发真实写请求。
4. **没有任何真实卖家账号**：13 家的 `live=true` 校验从未成功跑过一次；emag（inferred）、fruugo（portal）两条路径从未实测通过。
5. **42 项历史失败未清**：其中 `test_stripe`、`test_users`、`test_platform_rules` 三条与售卖直接相关，尚未修。
6. **加购定价（29 / 6 / 0.90 / 15）未获用户确认**；pro 仍 $49 / business 仍 $149，而接入位已改 20 / 22。
