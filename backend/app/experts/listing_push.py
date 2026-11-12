"""AI 商品内容 → 平台 listing 写回：统一成稿转各平台 payload。

支持平台（凭证 + listing_map）：allegro / ebay / bol / kaufland / emag / amazon / walmart
不支持：otto / zalando / fruugo / cdiscount / tiktok（无公开写接口或需类目 schema）
"""
import json

UNSUPPORTED = {
    "otto": "OTTO 无公开 listing 写接口，需通过 OTTO Seller 后台或对接其 EDI",
    "zalando": "Zalando 走 zDirect Partner 接口，需 partner 资质与类目协议",
    "fruugo": "Fruugo 走 FTP/CSV 批量上架，无单条写接口",
    "cdiscount": "Cdiscount 走后台批量模板或 XML feed",
    "tiktok": "TikTok Shop 写回需 Partner 资质与类目白名单",
}

ENDPOINT = {
    "allegro": "POST /sale/product-offers",
    "ebay": "PUT /sell/inventory/v1/inventory/{sku} + POST /sell/inventory/v1/offer",
    "bol": "POST /retailer/offers",
    "kaufland": "POST /units",
    "emag": "POST /api-3/product_offer/save",
    "amazon": "PATCH /listings/2021-08-01/items/{sku}",
    "walmart": "POST /v3/feeds?feedType=MP_ITEM（multipart XML）",
}


def _points(rec):
    out = []
    for b in (rec.bullet_points or []):
        if isinstance(b, dict):
            head = (b.get("heading") or "").strip()
            body = (b.get("content") or "").strip()
            out.append((head + ": " + body).strip(": "))
    return out[:5]


def _text(rec):
    parts = _points(rec)
    if rec.description:
        parts.append(rec.description)
    return "\n".join(p for p in parts if p)


def build_listing_payload(platform, rec, *, sku, mapping=None, price=None,
                          currency="EUR", quantity=10):
    """把一条生成稿转成该平台写回 payload；不支持平台直接返回原因，不假装成功。"""
    p = (platform or "").strip().lower()
    mapping = mapping or {}
    title = (rec.title or "")[:200]
    body = _text(rec)

    if p in UNSUPPORTED:
        return {"platform": p, "supported": False, "reason": UNSUPPORTED[p],
                "payload": None, "endpoint": None}

    if p == "allegro":
        payload = {
            "name": title,
            "description": {"sections": [{"items": [
                {"type": "TEXT", "content": body}]}]},
            "external": {"id": sku},
            "stock": {"available": int(quantity)},
        }
        if price:
            payload["sellingMode"] = {"price": {"amount": str(price), "currency": currency}}
    elif p == "ebay":
        payload = {
            "sku": sku,
            "inventory_item": {"product": {
                "title": title, "description": body}},
            "offer": {"sku": sku, "marketplaceId": "EBAY_DE",
                      "format": "FIXED_PRICE", "listingDescription": body[:5000]},
        }
        if price:
            payload["offer"]["price"] = {"value": float(price), "currency": currency}
            payload["offer"]["availableQuantity"] = int(quantity)
    elif p == "bol":
        payload = {
            "offerReference": mapping.get("offer_id") or sku,
            "ean": mapping.get("ean", ""),
            "title": title,
            "description": body,
        }
        if price:
            payload["pricing"] = {"bundlePrices": [{
                "unitPrice": float(price), "quantity": 1}]}
    elif p == "kaufland":
        payload = {
            "title": title,
            "description": body,
            "ean": mapping.get("ean", ""),
            "quantity": int(quantity),
        }
        if price:
            payload["price"] = float(price)
    elif p == "emag":
        payload = {"id": mapping.get("offer_id") or sku, "name": title,
                   "description": body, "stock": int(quantity)}
        if price:
            payload["sale_price"] = float(price)
    elif p == "amazon":
        patches = [
            {"op": "replace", "path": "/attributes/item_name",
             "value": [{"value": title, "marketplace_id": "A1PA6795UKMFR9",
                        "language_tag": "de_DE"}]},
            {"op": "replace", "path": "/attributes/product_description",
             "value": [{"value": body, "marketplace_id": "A1PA6795UKMFR9",
                        "language_tag": "de_DE"}]},
        ]
        payload = {"sku": sku, "productType": "PRODUCT", "patches": patches}
    elif p == "walmart":
        payload = {"feedType": "MP_ITEM", "sku": sku,
                   "xml": build_walmart_feed_xml([{
                       "sku": sku, "product_name": title, "description": body,
                       "price": price, "quantity": int(quantity),
                       "product_category": mapping.get("category", ""),
                       "brand": mapping.get("brand", ""),
                       "upc": mapping.get("upc") or mapping.get("ean", ""),
                   }]),
                   "note": "MP_ITEM XML 骨架；类目/主图/UPC 等必填项需以 Walmart 类目模板补齐"}
    else:
        return {"platform": p, "supported": False,
                "reason": "平台未登记", "payload": None, "endpoint": None}

    return {"platform": p, "supported": True, "endpoint": ENDPOINT.get(p),
            "payload": payload,
            "warnings": ["字段映射按平台公开结构生成；类目必填项需以卖家中心模板为准",
                         "首推建议 dry_run=true 审核后再提交"] if p != "walmart" else
                        ["Walmart 走 MP_ITEM XML feed 提交，需补类目/UPC/主图",
                         "签名需 consumer_id + RSA 私钥（WMSEC）"]}



def build_walmart_feed_xml(items):
    """把一条或多条产物拼成 Walmart MP_ITEM feed（XML 骨架，3.x）。"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def esc(v):
        return (str(v or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))

    rows = []
    for it in items:
        rows.append(
            "  <MPItem>\n"
            "    <orderable>\n"
            f"      <SKU>{esc(it.get('sku'))}</SKU>\n"
            f"      <productName>{esc(it.get('product_name'))[:200]}</productName>\n"
            f"      <longDescription>{esc(it.get('description'))[:4000]}</longDescription>\n"
            f"      <price>{esc(it.get('price') or '')}</price>\n"
            f"      <shippingWeight>1</shippingWeight>\n"
            f"      <productIdentifiers><productIdentifier>"
            f"<productIdType>UPC</productIdType><productId>{esc(it.get('upc'))}</productId>"
            "</productIdentifier></productIdentifiers>\n"
            "    </orderable>\n"
            "    <product>\n"
            f"      <productName>{esc(it.get('product_name'))[:200]}</productName>\n"
            f"      <brand>{esc(it.get('brand'))}</brand>\n"
            f"      <productCategory>{esc(it.get('product_category'))}</productCategory>\n"
            "      <mainImageUrl></mainImageUrl>\n"
            "    </product>\n"
            "  </MPItem>\n")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<MPItemFeed xmlns="http://walmart.com/">\n'
            "  <MPItemFeedHeader>\n"
            "    <version>3.1</version>\n"
            f"    <feedDate>{now}</feedDate>\n"
            "    <mart>WALMART_US</mart>\n"
            "  </MPItemFeedHeader>\n" + "".join(rows) + "</MPItemFeed>\n")
