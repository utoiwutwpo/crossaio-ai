"""Workbench Pro（2026-11-07）：竞品「离不开」功能的离线落地层。

四类功能全部为**纯函数生成器**（无第三方 API 依赖、无平台授权要求），共 11 端点：
- 救命型（低频×离不开）
    appeal         ：按 SKU + 下架原因生成 EN/DE/FR 申诉信 + 证据清单 + 恢复步骤
    rp-contract    ：EU RP 签约台账：三语书面授权书 + 6 项 Art.16 条款 + 到期 60 天预警
    evidence       ：DoC 草案 + 风险清单 + 10 年存档编号（对标 ProductIP）
    evidence-index ：归档清单 + 检索 + 缺件与到期预警 + CSV
    rescue(SOP)    ：前端三场景急救流程（Error 5995 / MYC / 申诉）
- 护城河（高频×离不开）
    gpsr-pack      ：SKU 母表 → 平台母语合规块 + 可导入 TSV（对标 Amazon MYC / Error 5995）
    tsv-pack       ：一份 SKU 母表 → 12 平台分文件 TSV + manifest + 上传指南，单个 ZIP 下载（产品最小验证）
    field-map      ：12 平台字段映射、字数硬校验、本地语言警示
    stock-guard    ：多渠道库存/价格一致性比对（离线防超卖，非实时 API 同步）
    rp             ：EU 责任人标签块 + 三语声明模板（对标 Webinterpret 的 RP 角色）
- 效率型（高频×可替代）
    pricing        ：毛利率 + VAT + 平台系数批量定价（对标 ChannelEngine 规则引擎）
- 锦上添花：原有产品描述 / AI 客服 / 统一收件箱等面板，本模块不新增
数据源全部来自 platform_registry / platform_rules，与 13 条 /rules/<p> 页面同一份数据。
仅本地开发（未推送）：不 commit / 不 push / 不部署 Render。
"""
import hashlib
import time
import json as _json
from pathlib import Path as _Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..database import User, get_db
from sqlalchemy.orm import Session
from fastapi.routing import APIRoute as _APIRoute
from pydantic import BaseModel

# ---------- 跨仓库兼容：远程 crossbot-ai 若无 experts 模块，用内置精简数据降级 ----------
_FB_PLATFORMS = {
    "amazon": {
        "display": "Amazon 欧洲站 + 美国站",
        "countries": [
            "UK",
            "DE",
            "FR",
            "IT",
            "ES",
            "NL",
            "SE",
            "PL",
            "BE",
            "US"
        ],
        "language": "en",
        "title_max": 200,
        "bullets": 5,
        "search_terms_max": 249,
        "description_max": 2000,
        "notes": [
            "标题前 3 个词包含核心关键词；德国站标题须为德语",
            "五点描述：痛点→功能→场景→品质→售后",
            "后台搜索词（generic keywords）不重复标题已有关键词，禁用竞品品牌名",
            "美国站：无 GPSR 强制，合规重心为 FTC 产品声明与类目审核（FDA/UL/FCC 类目需资质）；标题禁促销词与全大写单词"
        ]
    },
    "ebay": {
        "display": "eBay",
        "countries": [
            "UK",
            "DE",
            "FR",
            "IT",
            "ES"
        ],
        "language": "en",
        "title_max": 80,
        "bullets": 5,
        "search_terms_max": 500,
        "description_max": 4000,
        "notes": [
            "标题 80 字符是硬限制，关键词前置",
            "描述支持 HTML；必填 Item Specifics（品牌/型号/兼容性）在结构化字段中单独填写"
        ]
    },
    "fruugo": {
        "display": "Fruugo（泛欧）",
        "countries": [
            "UK",
            "DE",
            "FR",
            "IT",
            "ES",
            "NL",
            "PL",
            "Nordics"
        ],
        "language": "en",
        "title_max": 100,
        "bullets": 5,
        "search_terms_max": 300,
        "description_max": 3000,
        "notes": [
            "主目录用英语提交，Fruugo 平台自动翻译成各国语言",
            "属性（颜色/尺码/材质）必须结构化填写，否则无法翻译分发"
        ]
    },
    "walmart": {
        "display": "Walmart",
        "countries": [
            "US"
        ],
        "language": "en",
        "title_max": 100,
        "bullets": 5,
        "search_terms_max": 500,
        "description_max": 4000,
        "notes": [
            "标题格式：品牌 + 型号 + 商品名 + 关键属性，禁促销词与特殊字符",
            "Key Features 恰好 3-10 条（工程上统一生成 5 条）"
        ]
    },
    "cdiscount": {
        "display": "Cdiscount",
        "countries": [
            "FR"
        ],
        "language": "fr",
        "title_max": 120,
        "bullets": 5,
        "search_terms_max": 300,
        "description_max": 3000,
        "notes": [
            "全法语 listing，禁英语混杂",
            "描述需包含技术参数表；法国消费者重视保修与退换条款"
        ]
    },
    "otto": {
        "display": "Otto",
        "countries": [
            "DE"
        ],
        "language": "de",
        "title_max": 70,
        "bullets": 5,
        "search_terms_max": 250,
        "description_max": 2500,
        "notes": [
            "纯德语 listing，语法拼写要求高（德国用户敏感）",
            "Otto 对品质描述与材质说明要求严格，避免绝对化宣传用语"
        ]
    },
    "allegro": {
        "display": "Allegro",
        "countries": [
            "PL",
            "CZ",
            "HU"
        ],
        "language": "pl",
        "title_max": 75,
        "bullets": 5,
        "search_terms_max": 300,
        "description_max": 8000,
        "notes": [
            "波兰语 listing；标题 75 字符硬限制",
            "描述支持 HTML；波兰买家重视配送时效与 Allegro Smart 兼容性"
        ]
    },
    "emag": {
        "display": "eMAG",
        "countries": [
            "RO",
            "HU",
            "BG"
        ],
        "language": "ro",
        "title_max": 150,
        "bullets": 5,
        "search_terms_max": 300,
        "description_max": 4000,
        "notes": [
            "罗马尼亚语 listing",
            "必填品类特定结构化字段（家族/品牌/型号），否则审核被拒"
        ]
    },
    "kaufland": {
        "display": "Kaufland Global",
        "countries": [
            "DE",
            "AT",
            "CZ",
            "SK"
        ],
        "language": "de",
        "title_max": 150,
        "bullets": 5,
        "search_terms_max": 250,
        "description_max": 4000,
        "notes": [
            "德语 listing（德区为主），拼写语法要求与 Otto 同级",
            "制造商信息必须与 GPSR 欧代/制造商一致",
            "EAN 是商品主键，缺失无法创建"
        ]
    },
    "bol": {
        "display": "bol.com",
        "countries": [
            "NL",
            "BE"
        ],
        "language": "nl",
        "title_max": 120,
        "bullets": 5,
        "search_terms_max": 200,
        "description_max": 3000,
        "notes": [
            "荷兰语 listing（NL/BE），EAN 是商品唯一键，缺失直接建不了 offer",
            "荷兰买家重视 Delivery Promise 与 bol 分销服务评分"
        ]
    },
    "zalando": {
        "display": "Zalando",
        "countries": [
            "DE",
            "AT",
            "CH",
            "FR",
            "IT",
            "ES",
            "NL",
            "BE",
            "PL",
            "CZ",
            "SE"
        ],
        "language": "en",
        "title_max": 120,
        "bullets": 5,
        "search_terms_max": 250,
        "description_max": 3000,
        "notes": [
            "仅开放时尚类目（服装/鞋靴/箱包/配饰/美妆），需通过 Zalando Partner 品牌入驻审核（zDirect）",
            "EAN/GTIN 是商品唯一键，缺失无法创建；尺码网格（size grid）与材质成分必填，缺失直接拒收",
            "主目录用英语提交，Zalando 平台按站点自动本地化；德区消费者对材质与洗涤说明极敏感",
            "纺织品类目强制 GPSR + 纤维成分标签（EU 1007/2011），缺欧代与当地语言警示语会被下架"
        ]
    },
    "tiktok": {
        "display": "TikTok Shop",
        "countries": [
            "UK",
            "US",
            "ES",
            "IT",
            "DE",
            "FR"
        ],
        "language": "en",
        "title_max": 255,
        "bullets": 5,
        "search_terms_max": 200,
        "description_max": 3000,
        "notes": [
            "标题可带 emoji，前 20 字符抓眼球（信息流场景）；描述侧重短视频种草场景与使用瞬间",
            "欧盟站点（ES/IT/DE/FR）同样强制 GPSR/CE 合规：缺欧代与当地语言警示语会被下架",
            "合规红线：禁医妆类夸大功效词（治疗/治愈/瘦身特效）、禁绝对化用语、认证类目须上传资质",
            "搜索词字段用于商品关键词/话题标签（#hashtag），不重复标题"
        ]
    }
}

_LANG_BY_PLATFORM = {
    "amazon": ["en","de","fr","it","es","nl","sv","pl"],
    "ebay": ["en","de","fr","it","es"], "cdiscount": ["fr"], "otto": ["de"],
    "allegro": ["pl"], "emag": ["ro"], "fruugo": ["en","de","fr","nl"],
    "walmart": ["en"], "zalando": ["de","fr","nl","pl"],
    "bol": ["nl"], "tiktok": ["en","de","fr","it","es"],
    "miravia": ["es"], "kaufland": ["de"],
}
_HIGH_RISK = ("child","children","kids","baby","toy","electrical","electric","battery",
              "lithium","laser","chemical","cosmetic","food","medical","protective")


class _FallbackRules:
    """平台数据缺失时的降级实现：输出结构必须与原生 platform_rules 一致。"""
    @staticmethod
    def platform_config(p):
        if p not in _FB_PLATFORMS:
            raise KeyError(p)
        return _FB_PLATFORMS[p]

    @staticmethod
    def platform_rules_card(p):
        cfg = _FB_PLATFORMS[p]
        return {"platform": p, "native_rules": False,
                "policy_name": "GPSR (EU) 2023/988",
                "policy_url": "https://eur-lex.europa.eu/eli/reg/2023/988/oj",
                "authority": "EU market surveillance authority",
                "native_language": cfg.get("language", "en"),
                "listing_field": "Safety information / EU responsible person",
                "rep_requirements": "EU responsible person (GPSR Art. 16)",
                "enforcement": "Listing removal / sales restriction",
                "rules": [], "rule_count": 0, "warning_language_count": 7}

    @staticmethod
    def native_compliance_block(platform, product_name, keywords, eu_rep=None):
        if platform not in _FB_PLATFORMS:
            raise KeyError(platform)
        kws = [str(k).lower() for k in (keywords or [])] + [product_name.lower()]
        hit = sorted({k for k in kws for h in _HIGH_RISK if h in k})
        matched = ["children's product" if any("child" in h or "kid" in h or "baby" in h or "toy" in h for h in hit)
                   else "electrical / battery product" if any(h in ("electrical","electric","battery","lithium") for h in hit)
                   else "general product safety"]
        risk = "high" if hit else "medium"
        langs = _LANG_BY_PLATFORM.get(platform, ["en"])
        rep = eu_rep or {}
        lines = [
            "SAFETY INFORMATION / GPSR (EU) 2023/988",
            "Product: " + product_name,
            "Manufacturer: " + str(rep.get("manufacturer") or "[to be filled]"),
            "EU Responsible Person: " + str(rep.get("company_name") or "[to be filled]"),
            "RP address: " + str(rep.get("address") or "[to be filled]"),
            "RP email: " + str(rep.get("email") or "[to be filled]"),
            "Warnings: provide in " + ", ".join(langs),
            "Risk level: " + risk + " | categories: " + ", ".join(matched),
        ]
        return {"platform": platform, "product_name": product_name, "risk_level": risk,
                "block": "\n".join(lines), "matched_categories": matched,
                "required_languages": langs, "native_language": _FB_PLATFORMS[platform].get("language", "en")}


try:
    from ..experts import platform_rules
    from ..experts.platform_registry import PLATFORMS
except Exception:                       # 远程仓库缺模块时自动降级，保证服务不 500
    platform_rules = _FallbackRules()
    PLATFORMS = _FB_PLATFORMS

# ---------- 操作日志（订阅档位改版 2026-11-07）----------
# 每次调用 /api/v1/pro/* 端点都落一行 JSONL，供 /report 生成操作报告。
# 日志文件在 backend/app/data/op_log.jsonl；Render 临时盘会被部署清空，
# 所以 /report 同时把聚合摘要打进 logger，可从 Render Logs 恢复历史。

_OP_LOG = _Path(__file__).resolve().parent.parent / "data" / "op_log.jsonl"


def _oplog(entry: Dict) -> None:
    try:
        _OP_LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
        with open(_OP_LOG, "a", encoding="utf-8") as f:
            f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志绝不影响主流程


class _LoggingRoute(_APIRoute):
    """自动记录每个 Pro 端点的调用（时间/路径/状态/耗时），无需侵入各 handler。"""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):  # request: starlette.requests.Request
            t0 = time.time()
            status = 200
            try:
                resp = await original(request)
                status = resp.status_code
                return resp
            except HTTPException as he:
                status = he.status_code
                raise
            except Exception:
                status = 500
                raise
            finally:
                _oplog({"route": self.path,
                        "method": ",".join(sorted(self.methods)),
                        "status": status,
                        "ms": round((time.time() - t0) * 1000, 1)})

        return handler


router = APIRouter(route_class=_LoggingRoute)


def _dump(model) -> Optional[Dict]:
    if model is None:
        return None
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


# ---------------------------------------------------------------- GET /platforms
@router.get("/platforms", summary="12 平台规则摘要（工作台字段映射/批量包数据源）")
def pro_platforms():
    out = []
    for p, cfg in PLATFORMS.items():
        card = platform_rules.platform_rules_card(p)
        out.append({
            "platform": p,
            "display": cfg.get("display", p),
            "listing_language": cfg.get("language"),
            "countries": cfg.get("countries", []),
            "title_max": cfg.get("title_max"),
            "bullets": cfg.get("bullets"),
            "search_terms_max": cfg.get("search_terms_max"),
            "description_max": cfg.get("description_max"),
            "notes": cfg.get("notes", []),
            "native_language": card["native_language"],
            "listing_field": card["listing_field"],
            "rep_requirements": card["rep_requirements"],
            "authority": card["authority"],
            "enforcement": card["enforcement"],
            "rule_count": card["rule_count"],
            "warning_language_count": card["warning_language_count"],
            "native_rules": card["native_rules"],
        })
    return {"count": len(out), "platforms": out}


# ---------------------------------------------------------------- POST /gpsr-pack
class PackRow(BaseModel):
    sku: str
    title: str
    keywords: List[str] = []
    manufacturer: str = ""
    model_batch: str = ""


class EURep(BaseModel):
    company_name: str = ""
    address: str = ""
    email: str = ""
    # GPSR Art.16 / Art.9：制造商与进口商是标签必填项。
    # 此前 EURep 只有欧代三字段，导致标签里 Manufacturer 只能落到占位符，
    # 签约授权书又把 manufacturer 填成欧代自己（自己任命自己）。
    manufacturer: str = ""
    manufacturer_address: str = ""
    importer: str = ""
    importer_address: str = ""


class PackReq(BaseModel):
    platform: str
    rows: List[PackRow]
    eu_rep: Optional[EURep] = None


@router.post("/gpsr-pack", summary="低频刚需：SKU 母表 → 平台母语合规块 + 可导入 TSV")
def pro_gpsr_pack(req: PackReq):
    if not (1 <= len(req.rows) <= 200):
        raise HTTPException(400, "rows must contain 1..200 items")
    try:
        platform_rules.platform_config(req.platform)
    except Exception:
        raise HTTPException(400, f"unknown platform: {req.platform}")
    rep = _dump(req.eu_rep)
    rows = []
    for r in req.rows:
        blk = platform_rules.native_compliance_block(
            req.platform, r.title, r.keywords, rep, model_batch=r.model_batch)
        rows.append({"sku": r.sku, "manufacturer": r.manufacturer, **blk})
    tsv = ["sku\tproduct\tblock_risk\tblock_text"]
    for row in rows:
        tsv.append(f"{row['sku']}\t{row['product_name']}\t{row['risk_level']}\t"
                   + row["block"].replace("\n", " ⏎ "))
    return {
        "platform": req.platform,
        "count": len(rows),
        "rows": rows,
        "tsv": "\n".join(tsv),
        "hint": "TSV 使用 Tab 分隔；Excel 导入请选 UTF-8 并保留 BOM；"
                "Amazon Manage Your Compliance 请按品类/站点/语言各传一份文件。",
    }


# ---------------------------------------------------------------- POST /field-map
class MapReq(BaseModel):
    title: str
    keywords: List[str] = []


@router.post("/field-map", summary="高频效率：一次输入 → 12 平台字段映射与字数硬校验")
def pro_field_map(req: MapReq):
    title = (req.title or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    out = []
    for p, cfg in PLATFORMS.items():
        tmax = cfg.get("title_max") or 0
        truncated = title[:tmax] if tmax and len(title) > tmax else title
        out.append({
            "platform": p,
            "display": cfg.get("display", p),
            "title_max": tmax,
            "title_len": len(title),
            "fits": bool(tmax and len(title) <= tmax),
            "title_for_platform": truncated,
            "listing_language": cfg.get("language"),
            "bullets": cfg.get("bullets"),
            "search_terms_max": cfg.get("search_terms_max"),
            "description_max": cfg.get("description_max"),
            "notes": cfg.get("notes", []),
            "rep_requirements": platform_rules.platform_rules_card(p)["rep_requirements"],
            "native_language": platform_rules.platform_rules_card(p)["native_language"],
        })
    out.sort(key=lambda x: x["fits"])
    return {"input_len": len(title), "platforms": out,
            "all_fit": all(x["fits"] for x in out)}


# ---------------------------------------------------------------- POST /pricing
class PriceRow(BaseModel):
    sku: str
    cost: float
    shipping: float = 0.0


class PriceReq(BaseModel):
    rows: List[PriceRow]
    margin: float = 0.40          # 目标毛利率（净价口径）
    vat: float = 0.19             # 增值税（DE 19%）
    rounding: float = 0.99        # 心理价位尾数
    min_price: float = 0.0
    factors: Dict[str, float] = {}   # platform -> 价格系数


@router.post("/pricing", summary="高频效率：毛利率+VAT+平台系数批量定价")
def pro_pricing(req: PriceReq):
    if not (0 <= req.margin < 0.95):
        raise HTTPException(400, "margin must be in [0, 0.95)")
    if req.vat < 0 or req.vat > 0.5:
        raise HTTPException(400, "vat must be in [0, 0.5]")
    out = []
    for r in req.rows:
        base = (r.cost + r.shipping) / (1 - req.margin) if req.margin < 1 else r.cost + r.shipping
        net = base * (1 + req.vat)
        per_platform = {}
        for p in PLATFORMS:
            factor = req.factors.get(p, 1.0)
            raw = net * factor
            if req.rounding > 0:
                price = int(raw) + req.rounding
                if price < raw:
                    price += 1.0
            else:
                price = round(raw, 2)
            if price < req.min_price:
                price = req.min_price
            per_platform[p] = round(price, 2)
        out.append({
            "sku": r.sku, "cost": r.cost, "shipping": r.shipping,
            "base": round(base, 2), "net_with_vat": round(net, 2),
            "platform_prices": per_platform,
        })
    return {
        "rules": {"margin": req.margin, "vat": req.vat, "rounding": req.rounding,
                  "min_price": req.min_price, "factors": req.factors},
        "rows": out,
        "note": "公式：售价 = (采购价+运费)/(1-毛利率) × (1+VAT) × 平台系数，尾数取心理价位。",
    }


# ---------------------------------------------------------------- POST /evidence
class EvidenceReq(BaseModel):
    sku: str
    product: str
    manufacturer: str
    address: str = ""
    category: str = ""
    keywords: List[str] = []
    standards: List[str] = []
    platform: str = "amazon"


@router.post("/evidence", summary="差异化：DoC 草案 + 风险清单 + 10 年存档编号")
def pro_evidence(req: EvidenceReq):
    try:
        blk = platform_rules.native_compliance_block(
            req.platform, req.product, req.keywords, None)
    except Exception:
        raise HTTPException(400, f"unknown platform: {req.platform}")
    doc_id = "DOC-" + hashlib.sha256(
        f"{req.sku}|{req.product}|{req.manufacturer}".encode()).hexdigest()[:12].upper()
    year = time.strftime("%Y")
    doc = {
        "doc_id": doc_id,
        "issued": time.strftime("%Y-%m-%d"),
        "retain_until": f"{int(year) + 10}-12-31",
        "sku": req.sku,
        "product": req.product,
        "manufacturer": req.manufacturer,
        "address": req.address,
        "category": req.category or " / ".join(blk["matched_categories"]) or "general",
        "risk_level": blk["risk_level"],
        "matched_categories": blk["matched_categories"],
        "declaration": [
            f"Declaration of Conformity (draft) — {doc_id}",
            f"We, {req.manufacturer}{(', ' + req.address) if req.address else ''}, "
            f"declare under our sole responsibility that the product",
            f"「{req.product}」 (SKU: {req.sku}) is in conformity with the applicable "
            f"Union harmonisation legislation, including GPSR (EU) 2023/988.",
            f"Applicable standards: {', '.join(req.standards) if req.standards else '[to be filled per product family]'}",
            f"Signed for and on behalf of: {req.manufacturer}, {time.strftime('%Y-%m-%d')}",
        ],
        "risk_checklist": blk["matched_categories"] or ["general product safety"],
        "required_languages": blk["required_languages"],
        "retention_note": "Technical documentation and DoC must be kept for 10 years "
                          "after the product was placed on the market (GPSR Art. 9).",
    }
    return {"platform": req.platform, **doc}


# ---------------------------------------------------------------- POST /rp
class RPProduct(BaseModel):
    sku: str = ""
    title: str
    keywords: List[str] = []
    model_batch: str = ""


class RPReq(BaseModel):
    eu_rep: EURep
    products: List[RPProduct]
    platforms: List[str] = []


_RP_TEMPLATES = {
    "en": ("EU Responsible Person declaration — {company}, {address}, {email} "
           "acts as the responsible person (Article 16 GPSR) for the listed products."),
    "de": ("Erklärung zur verantwortlichen Person (EU) — {company}, {address}, {email} "
           "tritt gemäß Art. 16 GPSR als verantwortliche Person für die gelisteten Produkte auf."),
    "fr": ("Déclaration de la personne responsable (UE) — {company}, {address}, {email} "
           "agit en tant que personne responsable (art. 16 du GPSR) pour les produits listés."),
}


@router.post("/rp", summary="差异化：EU 责任人标签块 + 三语声明模板")
def pro_rp(req: RPReq):
    rep = _dump(req.eu_rep)
    platforms = req.platforms or list(PLATFORMS.keys())
    labels = []
    for p in platforms:
        try:
            platform_rules.platform_config(p)
        except Exception:
            continue
        for prod in req.products[:20]:
            blk = platform_rules.native_compliance_block(
                p, prod.title, prod.keywords, rep, model_batch=prod.model_batch)
            labels.append({"platform": p, "sku": prod.sku, **blk})
    filled = {k: v.format(company=req.eu_rep.company_name, address=req.eu_rep.address,
                          email=req.eu_rep.email) for k, v in _RP_TEMPLATES.items()}
    missing = [k for k, v in {"company": req.eu_rep.company_name, "address": req.eu_rep.address,
                              "email": req.eu_rep.email,
                              "manufacturer": req.eu_rep.manufacturer}.items()
               if not v.strip()]
    # 型号/批次是 GPSR Art.9 追溯标识，任一产品缺即整批标红
    if any(not (prod.model_batch or "").strip() for prod in req.products):
        missing.append("model_batch")
    return {
        "labels": labels,
        "declarations": filled,
        "missing_fields": missing,
        "required_fields": ["company", "address", "email", "manufacturer", "model_batch"],
        "field_hints": {
            "manufacturer": "标签正文的 Manufacturer 行；欧盟执法检查第一眼就查它",
            "model_batch": "包装与 listing 必须一致的型号/批次（GPSR Art.9 追溯）",
            "company": "欧盟境内责任人公司名（Art.16）",
            "address": "欧盟境内可送达邮政地址",
            "email": "可联系邮箱",
        },
        "count": len(labels),
        "note": "标签块可直接粘贴至 listing 合规字段 / 包装铭牌；声明模板供 RP 协议附件使用。",
    }


# =====================================================================
# 补齐竞品「离不开」四象限缺失的 4 条业务闭环（2026-11-07 16:00）
#   rp-contract   : EU 责任人「签约」台账（此前只有标签/声明）
#   appeal        : 下架申诉信按 SKU 生成（此前只有 SOP 文档）
#   evidence-index: 证据档案归档与检索（此前只有 DoC 草案生成）
#   stock-guard   : 库存/价格防超卖离线比对（此前完全缺失）
# 全部为纯函数，无平台 API 依赖；stock-guard 明确标注为离线近似版。
# =====================================================================
import datetime as _dt


class RPContractReq(BaseModel):
    eu_rep: EURep
    # 授权书的委托方 = 制造商自己，绝不能等于欧代
    manufacturer: str = ""
    manufacturer_address: str = ""
    contract_start: str = ""
    contract_end: str = ""
    authorized_signatory: str = ""
    product_families: List[str] = []
    platforms: List[str] = []
    has_written_mandate: bool = False
    has_liability_clause: bool = False
    has_termination_clause: bool = False


_RP_MANDATE = {
    "en": ("WRITTEN MANDATE (GPSR Art. 16) — {manufacturer} appoints {company}, "
           "{address}, {email}, as its EU responsible person for the product families "
           "{families} on {platforms}. The RP keeps the EU declaration of conformity "
           "and technical documentation available for 10 years, cooperates with market "
           "surveillance authorities and notifies the manufacturer of any risk. "
           "Signed: {signatory}. Valid {start} – {end}."),
    "de": ("SCHRIFTLICHE BEVOLLMÄCHTIGUNG (GPSR Art. 16) — {manufacturer} benennt {company}, "
           "{address}, {email}, als verantwortliche Person in der EU für die Produktfamilien "
           "{families} auf {platforms}. Die RP hält EU-Konformitätserklärung und technische "
           "Dokumentation 10 Jahre bereit, kooperiert mit den Marktüberwachungsbehörden und "
           "meldet dem Hersteller jedes Risiko. Unterzeichnet: {signatory}. Gültig {start} – {end}."),
    "fr": ("MANDAT ÉCRIT (GPSR art. 16) — {manufacturer} désigne {company}, {address}, {email}, "
           "comme personne responsable dans l'UE pour les familles de produits {families} "
           "sur {platforms}. La PR conserve la déclaration UE de conformité et la documentation "
           "technique pendant 10 ans, coopère avec les autorités de surveillance du marché et "
           "signale tout risque au fabricant. Signé : {signatory}. Valable {start} – {end}."),
}


@router.post("/rp-contract", summary="低频刚需：EU RP 签约台账 + 三语授权书 + 到期提醒")
def pro_rp_contract(req: RPContractReq):
    today = _dt.date.today()
    days_left = None
    expiry_status = "unknown"
    if req.contract_end:
        try:
            end = _dt.date.fromisoformat(req.contract_end)
            days_left = (end - today).days
            expiry_status = ("expired" if days_left < 0 else
                             "renew_now" if days_left <= 60 else "ok")
        except ValueError:
            expiry_status = "invalid_date"
    start = req.contract_start or today.isoformat()
    end = req.contract_end or (today + _dt.timedelta(days=365)).isoformat()
    principal = (req.manufacturer or req.eu_rep.manufacturer or "").strip()
    principal_addr = (req.manufacturer_address or req.eu_rep.manufacturer_address or "").strip()
    ctx = dict(manufacturer=(principal or "[MANUFACTURER NAME REQUIRED]")
               + (", " + principal_addr if principal_addr else ""),
               company=req.eu_rep.company_name or "[RP company]",
               address=req.eu_rep.address or "[EU address]",
               email=req.eu_rep.email or "[email]",
               families=", ".join(req.product_families) or "[product families]",
               platforms=", ".join(req.platforms) or "all marketplaces",
               signatory=req.authorized_signatory or "[signatory]",
               start=start, end=end)
    clauses = [
        {"key": "manufacturer_principal", "ok": bool(principal),
         "why": "mandate must name the manufacturer (principal); RP cannot appoint itself"},
        {"key": "written_mandate", "ok": req.has_written_mandate,
         "why": "GPSR Art.16 requires a written mandate naming the RP"},
        {"key": "eu_establishment", "ok": bool(req.eu_rep.company_name and req.eu_rep.address),
         "why": "RP must be established in the EU with a postal address"},
        {"key": "doc_retention_10y", "ok": True,
         "why": "DoC + technical documentation kept 10 years (GPSR Art.9)"},
        {"key": "authority_cooperation", "ok": True,
         "why": "RP must cooperate with market surveillance authorities"},
        {"key": "liability_clause", "ok": req.has_liability_clause,
         "why": "contract should allocate product-liability duties"},
        {"key": "termination_clause", "ok": req.has_termination_clause,
         "why": "termination + document handover must be defined"},
    ]
    missing = [c["key"] for c in clauses if not c["ok"]]
    return {
        "rp": _dump(req.eu_rep), "manufacturer": principal,
        "principal_missing": (not bool(principal)),
        "valid_from": start, "valid_until": end,
        "days_left": days_left, "expiry_status": expiry_status,
        "renew_hint": ("EXPIRED — renew before listing again" if expiry_status == "expired" else
                       "RENEW WITHIN 60 DAYS — start signature process now" if expiry_status == "renew_now" else
                       "valid" if expiry_status == "ok" else "set contract_end as YYYY-MM-DD"),
        "mandates": {k: v.format(**ctx) for k, v in _RP_MANDATE.items()},
        "clause_checklist": clauses, "missing": missing,
        "activation_note": "Activate the RP at account level in Seller Central and wait 1–3 days before bulk submission.",
        "csv": "key,value\n" + "\n".join(
            ["manufacturer," + principal,
             "rp_company," + (req.eu_rep.company_name or ""),
             "rp_address," + (req.eu_rep.address or ""),
             "rp_email," + (req.eu_rep.email or ""),
             "valid_from," + start, "valid_until," + end,
             "signatory," + (req.authorized_signatory or ""),
             "product_families," + " / ".join(req.product_families),
             "platforms," + " / ".join(req.platforms)]),
    }


class AppealReq(BaseModel):
    sku: str
    product: str
    platform: str = "amazon"
    reason: str = "5995"
    manufacturer: str = ""
    lang: str = "en"
    evidence_ids: List[str] = []
    root_cause: str = ""
    fix_applied: str = ""


_APPEAL = {
    "en": {"subject": "Appeal for reinstatement — SKU {sku} ({reason})",
           "body": ("Dear {platform} Seller Performance Team,\n\n"
                    "We request reinstatement of SKU {sku} — {product}.\n"
                    "Root cause: {root_cause}\n"
                    "Corrective action already completed: {fix_applied}\n"
                    "Evidence attached: {evidence}\n\n"
                    "All GPSR (EU) 2023/988 fields, the EU responsible person and the "
                    "declaration of conformity are now on file and retained for 10 years. "
                    "We have added a per-SKU pre-submission check to prevent recurrence.\n\n"
                    "Please reinstate the listing or advise the exact remaining requirement.\n"
                    "Regards,\n{manufacturer}")},
    "de": {"subject": "Einspruch auf Wiederaufnahme — SKU {sku} ({reason})",
           "body": ("Sehr geehrtes {platform} Seller Performance Team,\n\n"
                    "wir bitten um Wiederaufnahme der SKU {sku} — {product}.\n"
                    "Ursache: {root_cause}\n"
                    "Bereits umgesetzte Korrektur: {fix_applied}\n"
                    "Beigefügte Nachweise: {evidence}\n\n"
                    "Alle GPSR-(EU)-2023/988-Felder, die verantwortliche Person in der EU "
                    "und die Konformitätserklärung liegen vor und werden 10 Jahre aufbewahrt. "
                    "Eine SKU-Prüfung vor jeder Einreichung verhindert künftige Fehler.\n\n"
                    "Bitte reaktivieren Sie das Listing oder nennen Sie die konkrete Restanforderung.\n"
                    "Mit freundlichen Grüßen\n{manufacturer}")},
    "fr": {"subject": "Recours de rétablissement — SKU {sku} ({reason})",
           "body": ("Bonjour l'équipe Seller Performance {platform},\n\n"
                    "Nous demandons le rétablissement de la SKU {sku} — {product}.\n"
                    "Cause : {root_cause}\n"
                    "Correction déjà appliquée : {fix_applied}\n"
                    "Pièces jointes : {evidence}\n\n"
                    "Tous les champs GPSR (UE) 2023/988, la personne responsable dans l'UE "
                    "et la déclaration de conformité sont archivés pour 10 ans. "
                    "Un contrôle par SKU avant chaque soumission prévient toute récidive.\n\n"
                    "Merci de rétablir l'annonce ou d'indiquer l'exigence restante exacte.\n"
                    "Cordialement,\n{manufacturer}")},
}
_REASON_HINT = {
    "5995": "Bulk upload rejected — resubmit per SKU, one category/site/language per TSV file",
    "documents": "Compliance document request — attach DoC + technical file archive IDs",
    "safety": "Safety complaint — attach risk assessment and RP incident record",
    "delisting": "Listing removed — map the reason code to one specific corrective action",
}


def _default_fix(req) -> str:
    """申诉信不能留 [占位]，按原因码给出可直接提交的整改陈述。"""
    if req.reason == "5995":
        return ("resubmitted the SKU as a single-category / single-site / single-language "
                "file, with the GPSR safety block, EU responsible person, manufacturer and "
                "model/batch fields completed on the child ASIN")
    if req.reason in ("documents", "doc"):
        return ("uploaded the EU declaration of conformity and the technical file index "
                "in Manage Your Compliance and linked them to this SKU")
    if req.reason in ("safety", "gpsr"):
        return ("replaced the listing content with the native-language safety information, "
                "added the EU responsible person and manufacturer label block, and filed "
                "the risk assessment in the evidence vault")
    if req.reason in ("delisting", "takedown", "inauthentic"):
        return ("removed the infringing claims, re-sourced the supply batch with invoices "
                "matching the ASIN, and re-uploaded compliant images and documentation")
    return ("corrected the specific attribute cited in the notice and re-submitted the "
            "listing through the original case")


def _default_evidence(req) -> str:
    ids = ", ".join(req.evidence_ids) or "DoC archive ID + technical file index"
    return ids + " (10-year retention per GPSR Art.9)"


@router.post("/appeal", summary="低频刚需：按 SKU 生成三语下架申诉信 + 证据清单")
def pro_appeal(req: AppealReq):
    lang = req.lang if req.lang in _APPEAL else "en"
    tpl = _APPEAL[lang]
    ctx = dict(sku=req.sku, product=req.product, platform=req.platform,
               reason=req.reason, manufacturer=req.manufacturer or "[company]",
               root_cause=req.root_cause or _REASON_HINT.get(req.reason, "[describe root cause]"),
               fix_applied=req.fix_applied or _default_fix(req),
               evidence=", ".join(req.evidence_ids) or _default_evidence(req))
    return {
        "platform": req.platform, "sku": req.sku, "reason": req.reason, "lang": lang,
        "subject": tpl["subject"].format(**ctx), "body": tpl["body"].format(**ctx),
        "translations": {k: {"subject": v["subject"].format(**ctx),
                             "body": v["body"].format(**ctx)} for k, v in _APPEAL.items()},
        "reason_hint": _REASON_HINT.get(req.reason, "Describe the exact reason code and the fix"),
        "missing_inputs": [k for k, v in {
            "root_cause": req.root_cause, "manufacturer": req.manufacturer}.items()
            if not v],
        "filleable": ["root_cause", "manufacturer"],
        "auto_filled": [k for k, v in {"fix_applied": req.fix_applied,
                                       "evidence_ids": req.evidence_ids}.items() if not v],
        "attachment_checklist": [
            "DoC draft + archive ID (generate in 合规证据档案 / Evidence vault)",
            "Technical documentation / risk assessment (10-year retention)",
            "EU RP mandate + label block (generate in EU 责任人 / RP contract)",
            "Screenshot of Manage Your Compliance status after the fix",
            "Per-SKU compliance TSV used for resubmission",
        ],
        "submit_checklist": [
            "One issue per appeal, max 3 screenshots",
            "Submit through the original case / Seller Performance, not a new random case",
            "If rejected, wait 72h and add evidence only — never change the facts",
            "After two rejections escalate to Seller Performance and open a Case for the owning team",
        ],
        "recovery_steps": [
            "Fix the field → regenerate the per-SKU compliance block",
            "Upload one file per category/site/language in Manage Your Compliance",
            "Wait 24–48h for status clear, then attach the screenshot to this appeal",
            "Relist only after the compliance attribute shows accepted",
        ],
    }


class RescueReq(BaseModel):
    platform: str = "amazon"
    sku: str = ""
    code: str = "5995"
    product: str = ""
    manufacturer: str = ""
    lang: str = "en"
    detail: str = ""


_RESCUE_CODES = {
    "5995": {
        "title": "批量上传被拒（Error 5995）",
        "severity": "high",
        "why": "批量上传权限墙：账号没有该站点/类目的批量提交权限，或一次文件里混了多个站点、类目、语言。数据本身通常没错。",
        "first_response": "当天处理：先拆文件重提一次，再决定是否开 Case。",
        "steps": [
            {"n": 1, "action": "把母表按「站点 × 类目 × 语言」拆成单文件，一文件一组合", "where": "本工作台 12 平台 TSV 导出"},
            {"n": 2, "action": "确认已先在账号级激活 EU 责任人并等 1–3 天生效", "where": "Seller Central > Manage Your Compliance"},
            {"n": 3, "action": "只提交 5–20 行的小文件做探针，观察是否仍报 5995", "where": "Manage Your Compliance 上传页"},
            {"n": 4, "action": "探针通过后按同一结构分批放量，每批后核对状态", "where": "Manage Your Compliance > 提交记录"},
            {"n": 5, "action": "仍报 5995 则开 Case，标题写 Bulk upload permission — site/category，附探针文件与错误截图", "where": "帮助 > 开店支持 Case"},
        ],
        "evidence": ["报错截图（含时间戳与文件名）", "探针用小文件", "账号级 RP 生效截图", "DoC 与技术文件索引编号"],
        "escalation": ["第一轮拒绝后等 72 小时再补证据，不改事实", "两次拒绝后要求转交 Seller Performance 或类目团队"],
        "do_not": ["不要把 12 个平台的文件合成一个 Excel", "不要为绕过 5995 改类目或拆 ASIN"],
    },
    "myc": {
        "title": "合规属性待补（Manage Your Compliance 卡住）",
        "severity": "high",
        "why": "GPSR 合规属性未通过校验：安全信息、欧代、制造商或型号/批次缺一，或语言不是该站点母语。",
        "first_response": "24 小时内补齐属性并重传，别等自动下架。",
        "steps": [
            {"n": 1, "action": "导出当前属性表，逐 SKU 对照缺口字段", "where": "Seller Central > Manage Your Compliance"},
            {"n": 2, "action": "用平台母语重生成合规块（含 Manufacturer / Importer / Model-Batch 行）", "where": "本工作台 RP 标签 / 批量提交包"},
            {"n": 3, "action": "只补缺口字段，不改已通过字段，避免触发全量重审", "where": "Manage Your Compliance 编辑页"},
            {"n": 4, "action": "重传后 24–48 小时复查状态，截图留档", "where": "Manage Your Compliance 状态列"},
        ],
        "evidence": ["补字段前后的属性表", "母语合规块全文", "RP 标签图或包装铭牌照片"],
        "escalation": ["48 小时未清状态开 Case，标题写 GPSR attribute stuck — ASIN 列表"],
        "do_not": ["不要用英文块顶替德语/法语/波兰语站点", "不要只改父 ASIN 而不改子 ASIN"],
    },
    "safety": {
        "title": "安全投诉 / 事故报告",
        "severity": "critical",
        "why": "平台收到产品安全投诉或事故报告，按 GPSR 需在限期内给出风险评估与纠正措施。",
        "first_response": "当天响应：先确认是否已有人身伤害，再决定召回口径。",
        "steps": [
            {"n": 1, "action": "冻结该 SKU 出货，拉出批次与销售流向", "where": "ERP / 订单后台"},
            {"n": 2, "action": "做一页风险评估：失效模式、受影响批次、已售数量、伤害记录", "where": "本工作台 证据档案"},
            {"n": 3, "action": "按需发召回或修正通知，同步平台与买家", "where": "平台安全事件入口 + 买家消息"},
            {"n": 4, "action": "提交纠正措施与 10 年留档编号", "where": "平台合规 Case / 证据档案"},
        ],
        "evidence": ["批次追溯表", "风险评估页", "纠正措施记录", "与买家的沟通记录"],
        "escalation": ["涉及人身伤害立即上报平台安全团队与欧代，不要只走普通客服"],
        "do_not": ["不要删除投诉记录", "不要在未定责前公开承认超出事实的结论"],
    },
    "takedown": {
        "title": "Listing 被下架 / 侵权投诉",
        "severity": "high",
        "why": "下架通常来自知识产权、真实性或类目合规三类通知，处理路径完全不同。",
        "first_response": "24 小时内读完通知原文，先定性再写申诉。",
        "steps": [
            {"n": 1, "action": "按通知类型定性：知产 / 真伪 / 合规，记录 case ID 与要求", "where": "账户状况 > 政策合规性"},
            {"n": 2, "action": "知产类：拿到授权链或改图改文案；真伪类：拉采购发票与供应链证明", "where": "供应商 / 品牌授权文件"},
            {"n": 3, "action": "用三语申诉信说明根因与已完成的整改", "where": "本工作台 申诉信"},
            {"n": 4, "action": "在原 case 内提交，一次只提一个 SKU 一个问题", "where": "原 Case 回复"},
        ],
        "evidence": ["授权书或发票", "整改后 listing 截图", "申诉信正文", "同批次其他 SKU 的合规证明"],
        "escalation": ["两次被拒后要求升级 Seller Performance，附全部 case 编号"],
        "do_not": ["不要换账号重上同一 SKU", "不要用新 Case 覆盖旧 Case 的事实"],
    },
    "account": {
        "title": "账户状况 / 审核冻结",
        "severity": "critical",
        "why": "账户级审核会连带所有站点的资金与 listing，优先级高于任何单 SKU 问题。",
        "first_response": "立即处理：账户级问题按天计损失。",
        "steps": [
            {"n": 1, "action": "截图账户状况页全部红色项与到期日", "where": "账户状况"},
            {"n": 2, "action": "按项准备：身份/地址/供应链/税务四类材料", "where": "企业证照与账单"},
            {"n": 3, "action": "提交计划书：根因、已采取措施、预防机制", "where": "账户状况申诉入口"},
            {"n": 4, "action": "同步暂停自动化写回，避免冻结期继续触发风控", "where": "本工作台 自动化流水线"},
        ],
        "evidence": ["证照与地址证明", "供应链发票", "行动计划书", "历史合规记录"],
        "escalation": ["资金冻结另开资金 Case，不要混在合规 Case 里"],
        "do_not": ["不要在冻结期大量改价或批量上传"],
    },
}


def _rescue_payload(req: RescueReq):
    code = (req.code or "5995").lower()
    if code not in _RESCUE_CODES:
        code = "5995"
    card = _RESCUE_CODES[code]
    steps = [dict(step) for step in card["steps"]]
    body = (
        "Subject: Urgent compliance remediation — {sku} ({code})\n\n"
        "We have received the {code} notice for SKU {sku} ({product}).\n"
        "Immediate action taken: {first_step}\n"
        "Owner: {owner}. Evidence attached: {evidence}.\n"
        "We will report the outcome within one business day and keep the documentation "
        "for 10 years per GPSR Art.9.\n"
    ).format(sku=req.sku or "[SKU]", code=code.upper(), product=req.product or "[product]",
             first_step=steps[0]["action"], owner=req.manufacturer or "[company]",
             evidence=", ".join(card["evidence"][:3]))
    return {
        "platform": req.platform, "code": code, "title": card["title"],
        "severity": card["severity"], "why": card["why"],
        "first_response": card["first_response"],
        "steps": steps, "evidence": card["evidence"],
        "escalation": card["escalation"], "do_not": card["do_not"],
        "template": {"subject": "Urgent compliance remediation — %s (%s)" % (req.sku or "SKU", code.upper()),
                     "body": body, "lang": req.lang},
        "sla_note": "时限为工程建议，以平台通知原文的截止日为准。",
    }


@router.get("/rescue/codes", summary="急救 SOP 原因码目录")
def pro_rescue_codes():
    return {"count": len(_RESCUE_CODES),
            "codes": [{"code": k, "title": v["title"], "severity": v["severity"]}
                      for k, v in _RESCUE_CODES.items()]}


@router.post("/rescue", summary="急救 SOP：按原因码出处置步骤 + 证据清单 + 首封回复模板")
def pro_rescue(req: RescueReq):
    return _rescue_payload(req)


class ArchiveRow(BaseModel):
    doc_id: str
    sku: str
    product: str = ""
    issued: str = ""
    retain_until: str = ""
    file_ref: str = ""
    standards: List[str] = []


class ArchiveReq(BaseModel):
    rows: List[ArchiveRow]
    query: str = ""
    warn_days: int = 365


@router.post("/evidence-index", summary="低频刚需：10 年证据档案归档清单 + 检索 + 到期预警")
def pro_evidence_index(req: ArchiveReq):
    today = _dt.date.today()
    q = req.query.strip().lower()
    matched, expiring, missing = [], [], []
    by_sku: Dict[str, int] = {}
    for r in req.rows:
        if q and q not in " ".join([r.doc_id, r.sku, r.product, r.file_ref]).lower():
            continue
        days = None
        if r.retain_until:
            try:
                days = (_dt.date.fromisoformat(r.retain_until) - today).days
                if days < 0:
                    expiring.append({"doc_id": r.doc_id, "sku": r.sku, "days": days, "status": "expired"})
                elif days <= req.warn_days:
                    expiring.append({"doc_id": r.doc_id, "sku": r.sku, "days": days, "status": "renew_soon"})
            except ValueError:
                pass
        gaps = [k for k, v in {"file_ref": r.file_ref, "retain_until": r.retain_until,
                               "standards": r.standards}.items() if not v]
        if gaps:
            missing.append({"doc_id": r.doc_id, "sku": r.sku, "missing": gaps})
        by_sku[r.sku] = by_sku.get(r.sku, 0) + 1
        matched.append({"doc_id": r.doc_id, "sku": r.sku, "product": r.product,
                        "issued": r.issued, "retain_until": r.retain_until,
                        "days_left": days, "file_ref": r.file_ref, "standards": r.standards})
    csv = ["doc_id,sku,product,issued,retain_until,file_ref,standards"] + [
        ",".join([r["doc_id"], r["sku"], r["product"], r["issued"], r["retain_until"],
                  r["file_ref"], " / ".join(r["standards"])]) for r in matched]
    return {
        "total": len(req.rows), "matched": len(matched), "query": req.query,
        "records": matched, "by_sku": by_sku,
        "retention_warnings": expiring, "incomplete_records": missing,
        "csv": "\n".join(csv),
        "note": "GPSR Art.9: keep DoC + technical documentation 10 years after placing on the market. "
                "This index is an offline register; the actual files stay in your own document store.",
    }


class StockRow(BaseModel):
    sku: str
    platform: str
    stock: int
    price: float


class StockGuardReq(BaseModel):
    rows: List[StockRow]
    available_stock: Dict[str, int] = {}
    cost: Dict[str, float] = {}
    min_margin: float = 0.40
    max_price_gap: float = 0.15


@router.post("/stock-guard", summary="差异化：多渠道库存/价格一致性比对（离线防超卖）")
def pro_stock_guard(req: StockGuardReq):
    groups: Dict[str, List[StockRow]] = {}
    for r in req.rows:
        groups.setdefault(r.sku, []).append(r)
    out, alerts = [], []
    for sku, rows in groups.items():
        committed = sum(max(0, r.stock) for r in rows)
        avail = req.available_stock.get(sku)
        prices = [r.price for r in rows if r.price > 0]
        lo, hi = (min(prices), max(prices)) if prices else (0, 0)
        gap = round((hi - lo) / lo, 4) if lo > 0 else 0
        floor = round(req.cost[sku] / (1 - req.min_margin), 2) if sku in req.cost and req.min_margin < 1 else None
        underpriced = [r.platform for r in rows if floor is not None and 0 < r.price < floor]
        zero = [r.platform for r in rows if r.stock <= 0]
        oversell = (committed - avail) if avail is not None and committed > avail else 0
        issues = []
        if oversell:
            issues.append("oversell_risk")
            alerts.append(f"{sku}: committed {committed} > available {avail} (reduce by {oversell})")
        if gap > req.max_price_gap:
            issues.append("price_gap")
            alerts.append(f"{sku}: cross-channel price gap {round(gap*100,1)}% > {round(req.max_price_gap*100,1)}%")
        if underpriced:
            issues.append("below_margin")
            alerts.append(f"{sku}: below margin floor on {', '.join(underpriced)}")
        if zero:
            issues.append("zero_stock")
        out.append({
            "sku": sku, "channels": len(rows), "committed": committed,
            "available": avail, "oversell_excess": oversell,
            "price_min": lo, "price_max": hi, "price_gap": gap,
            "margin_floor": floor, "underpriced_platforms": underpriced,
            "zero_stock_platforms": zero, "issues": issues,
            "suggested_cut": max(0, oversell // max(1, len(rows))),
        })
    csv = ["sku,channels,committed,available,oversell_excess,price_gap,issues"] + [
        ",".join([r["sku"], str(r["channels"]), str(r["committed"]),
                  str(r["available"] if r["available"] is not None else ""),
                  str(r["oversell_excess"]), str(r["price_gap"]), " / ".join(r["issues"])])
        for r in out]
    return {
        "skus": len(out), "alerts": alerts, "rows": out, "csv": "\n".join(csv),
        "note": "OFFLINE comparison of a multi-channel stock/price CSV. It is NOT real-time API "
                "synchronisation: export your channel inventory, run this check, then fix quantities "
                "in each channel. Real-time prevention requires marketplace API/ERP integration.",
    }


# =====================================================================
# /tsv-pack — 产品最小验证能力并入工作后台（2026-11-07 16:20）
# 一份 SKU 母表 -> 12 个平台分文件 TSV + manifest + 上传指南，打成单个 ZIP。
# 与 offline_tsv/gpsr_tsv_offline.py 同一套规则与 SOP，但在 /app 内可直接用。
# 纯离线：无平台 API、无网络、不落盘、不改 content_seed.py、不部署 Render。
# =====================================================================
import base64 as _b64
import csv as _csv
import io as _io
import zipfile as _zip

_TSV_COLUMNS = ["sku", "manufacturer_reference", "manufacturer", "model_batch",
                "platform", "listing_language",
                "title", "title_len", "title_max", "title_status",
                "eu_responsible_person", "rp_address", "rp_email",
                "warning_languages", "compliance_block", "risk_level", "flags"]
_TSV_HEADER = {
    "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
    "de": "PRODUKTSICHERHEITSINFORMATION (GPSR 2023/988)",
    "fr": "INFORMATIONS DE SECURITE PRODUIT (GPSR 2023/988)",
    "pl": "INFORMACJE O BEZPIECZENSTWIE PRODUKTU (GPSR 2023/988)",
    "nl": "PRODUCTVEILIGHEIDSINFORMATIE (GPSR 2023/988)",
    "ro": "INFORMATII PRIVIND SIGURANTA PRODUSULUI (GPSR 2023/988)",
}
_TSV_RP_LABEL = {
    "en": "EU Responsible Person (Art. 16)",
    "de": "Verantwortliche Person in der EU (Art. 16)",
    "fr": "Personne responsable dans l'UE (art. 16)",
    "pl": "Osoba odpowiedzialna w UE (art. 16)",
    "nl": "Verantwoordelijke persoon in de EU (art. 16)",
    "ro": "Persoana responsabila in UE (art. 16)",
}
_TSV_GUIDE = """CrossAIO GPSR TSV pack - upload guide
=====================================
1. Each TSV is ONE marketplace. Never merge them into one Excel file.
2. Amazon Manage Your Compliance: split further by category x site x language,
   one file per combination. Upload through MYC, not Account Health.
3. UTF-8 with BOM (already applied), TAB separated, hidden columns expanded.
4. Key the master sheet on manufacturer reference / SKU, NOT ASIN.
5. Enter values on CHILD ASINs. Activate the account-level EU Responsible
   Person first and wait 1-3 days before any bulk submission.
6. Safety warnings must appear in every language listed in warning_languages.
7. Error 5995 is usually a bulk-permission wall for sellers without Brand
   Registry, not a data error. Resubmit per SKU, one small file at a time,
   then re-check MYC status after 48h.
8. Keep DoC + technical documentation for 10 years (GPSR Art. 9).
Generated offline inside the CrossAIO workbench: no platform API was called.
Policy summaries are engineering aids, not legal advice.
"""


class TsvRow(BaseModel):
    sku: str
    title: str
    keywords: List[str] = []
    manufacturer: str = ""
    model_batch: str = ""
    category: str = ""


_TSV_COLUMNS_SLIM = ["sku", "manufacturer_reference", "manufacturer", "model_batch",
                     "platform", "listing_language",
                     "title", "title_len", "title_max", "title_status",
                     "eu_responsible_person", "rp_address", "rp_email",
                     "risk_level", "flags"]
_DELIMS = {"tab": "\t", "comma": ",", "semicolon": ";"}


class TsvPackReq(BaseModel):
    rows: List[TsvRow]
    eu_rep: Optional[EURep] = None
    platforms: List[str] = []
    # 导出设置（默认值 = 平台后台可直接导入的规格）
    delimiter: str = "tab"          # tab | comma | semicolon
    bom: bool = True                # UTF-8 BOM
    line_ending: str = "crlf"       # crlf | lf
    include_compliance_block: bool = True
    title_policy: str = "flag"      # flag（保留原文并标记）| cut（按平台上限截断）
    columns: str = "full"           # full（17 列）| slim（15 列）
    columns_list: List[str] = []    # 自定义列（非空时优先于 columns）
    amazon_split: bool = False      # Amazon 按 10 个站点拆成独立文件
    site: str = ""                  # single=true 且 Amazon 拆分时指定站点
    single: bool = False            # true 时只允许一个平台，直接返回单文件文本


@router.post("/tsv-pack", summary="差异化：SKU 母表 → 12 平台分文件 TSV（ZIP / 单文件）")
def pro_tsv_pack(req: TsvPackReq):
    if not (1 <= len(req.rows) <= 500):
        raise HTTPException(400, "rows must contain 1..500 items")
    delim = _DELIMS.get(req.delimiter)
    if delim is None:
        raise HTTPException(400, "delimiter must be tab|comma|semicolon")
    if req.line_ending not in ("crlf", "lf"):
        raise HTTPException(400, "line_ending must be crlf|lf")
    if req.title_policy not in ("flag", "cut"):
        raise HTTPException(400, "title_policy must be flag|cut")
    base_cols = _TSV_COLUMNS_SLIM if req.columns == "slim" else _TSV_COLUMNS
    if req.columns_list:
        unknown = [c for c in req.columns_list if c not in _TSV_COLUMNS]
        if unknown:
            raise HTTPException(400, "unknown columns: " + ", ".join(unknown))
        columns = [c for c in _TSV_COLUMNS if c in req.columns_list]
    else:
        columns = base_cols
    if req.amazon_split and "marketplace_site" not in columns:
        columns = list(columns) + ["marketplace_site"]
    _SITE_LANG = {"UK": "en", "DE": "de", "FR": "fr", "IT": "it", "ES": "es",
                  "NL": "nl", "SE": "sv", "PL": "pl", "BE": "nl", "US": "en"}
    term = "\r\n" if req.line_ending == "crlf" else "\n"
    rep = _dump(req.eu_rep) or {}
    plats = [p for p in (req.platforms or list(_FB_PLATFORMS.keys()))
             if p in _FB_PLATFORMS]
    if not plats:
        raise HTTPException(400, "no valid platform selected")
    if req.single and len(plats) != 1:
        raise HTTPException(400, "single export requires exactly one platform")
    stamp = time.strftime("%Y%m%d")

    def build(p, site=None):
        cfg = _FB_PLATFORMS[p]
        lang = _SITE_LANG.get(site, cfg.get("language", "en")) if site else cfg.get("language", "en")
        tmax = int(cfg.get("title_max", 200))
        warnings = (lang if site else " ".join(_LANG_BY_PLATFORM.get(p, [lang])))
        local = {"rows": 0, "truncated": 0, "cut": 0, "missing_rp": 0,
                 "high_risk": 0, "missing_batch": 0}
        sio = _io.StringIO()
        w = _csv.DictWriter(sio, fieldnames=columns, delimiter=delim,
                            lineterminator=term, extrasaction="ignore")
        w.writeheader()
        for r in req.rows:
            sku, title = r.sku.strip(), r.title.strip()
            if not sku or not title:
                continue
            blob = (title + " " + " ".join(r.keywords)).lower()
            risk = "HIGH" if any(k in blob for k in _HIGH_RISK) else "NORMAL"
            out_title, tstatus = title, "OK"
            if len(title) > tmax:
                if req.title_policy == "cut":
                    out_title, tstatus = title[:tmax], "CUT"
                    local["cut"] += 1
                else:
                    tstatus = "TRUNC"
                    local["truncated"] += 1
            flags = []
            if tstatus != "OK":
                flags.append("TITLE_" + tstatus)
            if not (rep.get("company_name") and rep.get("address") and rep.get("email")):
                flags.append("MISSING_EU_RP")
                local["missing_rp"] += 1
            if risk == "HIGH":
                flags.append("HIGH_RISK_CATEGORY")
                local["high_risk"] += 1
            mb = (getattr(r, "model_batch", "") or "").strip()
            if not mb:
                flags.append("MISSING_MODEL_BATCH")
                local["missing_batch"] += 1
            block = ""
            if req.include_compliance_block:
                parts = [
                    _TSV_HEADER.get(lang, _TSV_HEADER["en"]),
                    "Product: " + out_title,
                    "Manufacturer: " + (r.manufacturer or rep.get("manufacturer")
                                         or "[MANUFACTURER REQUIRED]"),
                    "Model/Batch: " + (mb or "[MODEL/BATCH REQUIRED]"),
                    _TSV_RP_LABEL.get(lang, _TSV_RP_LABEL["en"]) + ": "
                    + (rep.get("company_name") or "[EU RP REQUIRED]"),
                    "RP address: " + (rep.get("address") or "[EU postal address REQUIRED]"),
                    "RP email: " + (rep.get("email") or "[contact REQUIRED]"),
                    "Safety warnings required in: " + warnings,
                    "Traceability: " + (mb or "[MODEL/BATCH REQUIRED]")
                    + " must match packaging and listing",
                ]
                block = " | ".join(parts)
            row = {
                "sku": sku, "manufacturer_reference": sku,
                "manufacturer": (r.manufacturer or rep.get("manufacturer") or ""),
                "model_batch": mb, "platform": p,
                "listing_language": lang, "title": out_title,
                "title_len": len(out_title), "title_max": tmax, "title_status": tstatus,
                "eu_responsible_person": rep.get("company_name", ""),
                "rp_address": rep.get("address", ""), "rp_email": rep.get("email", ""),
                "warning_languages": warnings, "compliance_block": block,
                "risk_level": risk, "flags": ";".join(flags) or "OK",
            }
            if site:
                row["marketplace_site"] = site
            w.writerow(row)
            local["rows"] += 1
        meta = {"platform": p, "display": cfg.get("display", p), "language": lang,
                "title_max": tmax, "rows": local["rows"], "warnings": warnings,
                "site": site or ""}
        return sio.getvalue(), local, meta

    settings = {"delimiter": req.delimiter, "bom": req.bom,
                "line_ending": req.line_ending,
                "include_compliance_block": req.include_compliance_block,
                "title_policy": req.title_policy, "columns": req.columns,
                "column_count": len(columns), "platforms": len(plats),
                "amazon_split": req.amazon_split,
                "columns_selected": list(columns)}

    if req.single:
        site = None
        if plats[0] == "amazon" and req.amazon_split and req.site:
            site = req.site
        text, local, meta = build(plats[0], site)
        return {"filename": ("gpsr_%s_%s_%s.tsv" % (plats[0], site, stamp) if site
                             else "gpsr_%s_%s.tsv" % (plats[0], stamp)),
                "platform": plats[0], "site": site or "",
                "display": meta["display"],
                "language": meta["language"], "title_max": meta["title_max"],
                "rows": local["rows"], "content": text, "settings": settings,
                "summary": local,
                "note": "Single-platform TSV generated offline; paste into the marketplace importer."}

    stats = {"rows": 0, "truncated": 0, "cut": 0, "missing_rp": 0,
             "high_risk": 0, "missing_batch": 0}
    files = []
    buf = _io.BytesIO()
    prefix = "\ufeff" if req.bom else ""
    with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as z:
        for p in plats:
            sites = []
            if p == "amazon" and req.amazon_split:
                sites = list(_FB_PLATFORMS[p].get("countries", []))
            for site in (sites or [None]):
                text, local, meta = build(p, site)
                for k in stats:
                    stats[k] += local.get(k, 0)
                name = ("gpsr_%s_%s_%s.tsv" % (p, site, stamp) if site
                        else "gpsr_%s_%s.tsv" % (p, stamp))
                z.writestr(name, (prefix + text).encode("utf-8"))
                files.append({"file": name, "platform": p, "display": meta["display"],
                              "language": meta["language"], "title_max": meta["title_max"],
                              "rows": meta["rows"], "warnings": meta["warnings"],
                              "site": meta["site"]})
        manifest = _io.StringIO()
        mw = _csv.writer(manifest, lineterminator="\r\n")
        mw.writerow(["platform", "site", "display", "listing_language", "title_max",
                     "delimiter", "bom", "line_ending", "rows", "file"])
        for f in files:
            mw.writerow([f["platform"], f.get("site", ""), f["display"], f["language"],
                         f["title_max"], req.delimiter, req.bom, req.line_ending,
                         f["rows"], f["file"]])
        manifest_text = manifest.getvalue()
        z.writestr("manifest.csv", ("\ufeff" + manifest_text).encode("utf-8"))
        guide_text = _TSV_GUIDE + (
            "\nExport settings used\n---------------------\n"
            "delimiter=%s | BOM=%s | line ending=%s | compliance block=%s\n"
            "title policy=%s | columns=%s (%d cols) | platforms=%d\n"
            % (req.delimiter, req.bom, req.line_ending,
               req.include_compliance_block, req.title_policy,
               req.columns, len(columns), len(plats)))
        z.writestr("UPLOAD_GUIDE.txt", guide_text)

    return {
        "filename": "gpsr_%dplatforms_%s.zip" % (len(plats), stamp),
        "zip_base64": _b64.b64encode(buf.getvalue()).decode("ascii"),
        "files": files, "summary": stats, "settings": settings,
        "manifest_text": manifest_text, "guide_text": guide_text,
        "note": "One file per marketplace. Amazon MYC needs further splitting by "
                "category x site x language. UTF-8 BOM is optional now; tab separated "
                "by default. Manufacturer reference is the key; values go on child ASINs. "
                "Error 5995 is a bulk-permission wall, not a data error. Generated fully offline.",
    }


# ---------- 店铺授权与自动化分析（订阅档位改版 2026-11-07）----------

_AUTH_METHODS = [
    {"method": "A. 官方 API OAuth", "tier": "Business",
     "desc": "最稳、可全自动写回；需平台开发者审核（Amazon SP-API / bol / Allegro / eMAG API）",
     "setup": "1-4 周（开发者审核 + 店铺授权页确认）", "risk": "低"},
    {"method": "B. 浏览器登录态代操作", "tier": "Business",
     "desc": "无需开发者资质，Cookie 持久化后由自动化代操作；适合只读采集与低频动作（Reddit / sellerforum.de 已用此通道上线）",
     "setup": "1 天", "risk": "中（平台风控与自动化条款灰色地带，仅限自有账号低频操作）"},
    {"method": "C. 手动导出 / 导入", "tier": "全部档位",
     "desc": "零授权零风险：TSV / CSV 下载后人工上传平台后台；当前所有生成器的默认通道",
     "setup": "0（已实现）", "risk": "无"},
]

_AUTOMATION_MATRIX = [
    {"feature": "GPSR 合规体检", "tier": "Free", "auth": "无需授权",
     "level": "全自动（已实现）", "how": "输入 SKU/平台即出结果，无平台交互"},
    {"feature": "产品描述 / 广告文案 / 差评改写", "tier": "Free", "auth": "无需授权",
     "level": "全自动（已实现）", "how": "纯文本生成器，输入即输出"},
    {"feature": "GPSR 批量提交包（单平台 TSV）", "tier": "Starter", "auth": "C 手动导入（已实现）；A SP-API 可升级",
     "level": "半自动（已实现）→ 全自动（需授权）", "how": "全自动 = Amazon SP-API Listings 写回：开发者注册审核 + 店铺 LWA OAuth 授权后由服务端推送"},
    {"feature": "12 平台 TSV 分文件导出", "tier": "Pro", "auth": "C 手动导入（已实现）",
     "level": "半自动（已实现）", "how": "一份母表 → 12 平台分文件 ZIP；写回各平台需逐平台接 API"},
    {"feature": "12 平台字段映射 / 批量定价", "tier": "Starter", "auth": "无需授权",
     "level": "全自动（已实现）", "how": "规则引擎（字数硬校验 / 毛利+VAT+平台系数），无平台交互"},
    {"feature": "下架申诉信 / RP 签约 / 证据档案", "tier": "Starter → Pro", "auth": "生成无需授权；提交动作须人工",
     "level": "全自动生成 + 人工提交", "how": "Amazon 仅允许 Seller Central 后台人工提交申诉；自动化只能到『一键复制 + 清单核对』为止"},
    {"feature": "库存价格防超卖", "tier": "Pro", "auth": "当前手动导出 CSV（已实现）；A 各平台 API 可升级",
     "level": "半自动（已实现）→ 全自动轮询（需授权）", "how": "bol / Allegro / eMAG 均有官方 REST API，店铺 OAuth 后可定时拉取实时库存并自动改价"},
    {"feature": "Listing 监控", "tier": "Pro", "auth": "公开页面抓取无需授权；API 更稳",
     "level": "半自动（定时抓取）→ 全自动（API）", "how": "注意频率与 robots；API 版可推送变动告警"},
    {"feature": "AI 客服 / 统一收件箱", "tier": "Business", "auth": "A 消息类 API（Amazon Buyer-Seller Messaging 等）",
     "level": "草稿全自动；发送按档位（Pro 确认发送 / Business 自动发送）", "how": "需店铺 OAuth 消息 API 权限"},
    {"feature": "论坛答疑发布（Reddit / sellerforum.de）", "tier": "推广通道", "auth": "B 浏览器登录态（已上线）",
     "level": "全自动（限速队列 1+1/天，已上线）", "how": "官方 API 更稳；浏览器通道存在风控风险，仅自有账号低频"},
    {"feature": "Facebook 公共主页发帖", "tier": "推广通道", "auth": "Meta Business Suite 原生排期（已上线）",
     "level": "云端全自动（已上线）", "how": "Meta 服务器定时发布，无需额外授权"},
]


@router.get("/automation", summary="订阅档位：店铺授权方式与各功能自动化可行性矩阵")
@router.post("/automation", summary="订阅档位：店铺授权方式与各功能自动化可行性矩阵（POST 兼容前端 wpost）")
def pro_automation():
    return {"tiers": ["Free", "Starter €29（1 平台）", "Pro €49（3 平台 · 全功能）", "Business €149（无限平台 · API）"],
            "auth_methods": _AUTH_METHODS, "matrix": _AUTOMATION_MATRIX,
            "summary": "纯生成器功能（体检/文案/定价/映射/申诉信/档案）已 100% 自动化且零授权；"
                       "需要店铺授权才能自动化的只有『写回平台』类：TSV 写回、库存实时同步、消息自动发送。"
                       "升级路径：手动导入（0 授权）→ 浏览器登录态（1 天）→ 官方 API OAuth（1-4 周审核）。"}


@router.get("/report", summary="订阅档位：操作报告（按天数聚合 Pro 端点调用日志）")
@router.post("/report", summary="订阅档位：操作报告（POST 兼容前端 wpost）")
def pro_report(days: int = 7):
    days = max(1, min(days, 90))
    cutoff = (_dt.date.today() - _dt.timedelta(days=days - 1)).isoformat()
    recs = []
    try:
        with open(_OP_LOG, encoding="utf-8") as f:
            for line in f:
                try:
                    r = _json.loads(line)
                    if r.get("ts", "")[:10] >= cutoff:
                        recs.append(r)
                    else:
                        break
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    total = len(recs)
    ok = sum(1 for r in recs if r.get("status") == 200)
    errors = [{"ts": r["ts"], "route": r["route"], "status": r["status"]}
              for r in recs if r.get("status") != 200][-10:]
    by_route: Dict[str, int] = {}
    by_day: Dict[str, int] = {}
    ms_total = 0.0
    for r in recs:
        by_route[r["route"]] = by_route.get(r["route"], 0) + 1
        d = r["ts"][:10]
        by_day[d] = by_day.get(d, 0) + 1
        ms_total += r.get("ms", 0)
    avg_ms = round(ms_total / total, 1) if total else 0
    md_lines = [
        f"# CrossAIO 操作报告（最近 {days} 天）",
        "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Pro 端点调用总数：{total}（成功 {ok} / 异常 {total - ok}）",
        f"- 平均响应：{avg_ms} ms",
        "",
        "## 按功能分布",
        "",
    ]
    for k in sorted(by_route, key=lambda x: -by_route[x]):
        md_lines.append(f"- `{k}`：{by_route[k]} 次")
    md_lines += ["", "## 按日期分布", ""]
    for d in sorted(by_day):
        md_lines.append(f"- {d}：{by_day[d]} 次")
    if errors:
        md_lines += ["", "## 最近异常", ""]
        for e in errors:
            md_lines.append(f"- {e['ts']} `{e['route']}` → {e['status']}")
    md_lines += ["",
                 "> 日志存于服务端 op_log.jsonl；Render 临时盘部署后清空，聚合摘要会同步写入 Render Logs 可恢复。"]
    report_md = "\n".join(md_lines)
    _oplog({"route": "/report(aggregate)", "method": "GET", "status": 200, "ms": 0,
            "note": f"report generated: {total} calls/{days}d"})
    return {"days": days, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_calls": total, "ok": ok, "errors": errors,
            "by_route": by_route, "by_day": by_day, "avg_ms": avg_ms,
            "report_md": report_md,
            "note": "每次部署会清空临时盘历史（SQLite 与本日志），聚合摘要已同步写 Render Logs。"}


@router.get("/platforms/live-probe", summary="12 平台真连通自检：有凭证就发真请求，没凭证如实报 not_connected")
async def platforms_live_probe(user: User = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    import json as _json
    from ..database import PlatformCredential
    from ..ebay_service import decrypt_secret
    from ..connectors.live_probe import probe_platform
    from ..connectors.capabilities import CHANNELS

    rows = []
    for platform in CHANNELS.keys():
        cred = (db.query(PlatformCredential)
                .filter(PlatformCredential.user_id == user.id,
                        PlatformCredential.platform == platform).first())
        payload = {}
        if cred:
            try:
                raw = decrypt_secret(cred.payload)
                payload = _json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception:
                payload = {}
        try:
            res = await probe_platform(platform, payload)
        except Exception as exc:
            res = {"platform": platform, "live": False, "status": "unreachable",
                   "hint": f"{type(exc).__name__}: {str(exc)[:120]}"}
        res["connected"] = bool(payload)
        rows.append(res)

    live = sum(1 for r in rows if r.get("live"))
    rows.sort(key=lambda r: (not r.get("live"), not r.get("connected"), r["platform"]))
    return {"total": len(rows), "live": live, "probed": len(rows), "items": rows,
            "note": "live 只认 2xx；401/403 记 auth；无凭证记 not_connected，不猜测"}

# =====================================================================
# 2026-11-09 · 六个生成器多平台批量能力（字段映射 / 提交包 / 申诉 / 证据 / 定价 / 库存）
# 统一约定：platforms 为空 = 全部 12 个在列平台；返回 CSV/manifest 便于直接导出。
# =====================================================================
_CURRENCY = {"walmart": "USD", "tiktok": "USD", "amazon": "EUR"}
_FEE_DEFAULT = {"amazon": 0.15, "ebay": 0.12, "fruugo": 0.15, "walmart": 0.15,
                "cdiscount": 0.12, "otto": 0.15, "allegro": 0.10, "emag": 0.12,
                "kaufland": 0.15, "bol": 0.12, "zalando": 0.18, "tiktok": 0.05}


def _plats(lst):
    ps = [p for p in (lst or list(PLATFORMS.keys())) if p in PLATFORMS]
    if not ps:
        raise HTTPException(400, "no valid platform selected")
    return ps


def _csv_text(header, rows):
    sio = _io.StringIO()
    w = _csv.writer(sio, lineterminator="\r\n")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return sio.getvalue()


def _zip_b64(files, bom=False):
    """files: [(name, text)] -> base64 zip."""
    buf = _io.BytesIO()
    prefix = "\ufeff" if bom else ""
    with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as z:
        for name, text in files:
            z.writestr(name, (prefix + text).encode("utf-8"))
    return _b64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------- 字段映射
class FieldMapRow(BaseModel):
    sku: str = ""
    title: str


class FieldMapPackReq(BaseModel):
    rows: List[FieldMapRow]
    platforms: List[str] = []
    title_policy: str = "flag"      # flag 保留原文并标记 | cut 按平台上限截断


@router.post("/field-map-pack", summary="字段映射：多标题 × 12 平台字数硬校验与截断")
def pro_field_map_pack(req: FieldMapPackReq):
    if not (1 <= len(req.rows) <= 200):
        raise HTTPException(400, "rows must contain 1..200 items")
    if req.title_policy not in ("flag", "cut"):
        raise HTTPException(400, "title_policy must be flag|cut")
    ps = _plats(req.platforms)
    items, csv_rows, fails = [], [], 0
    strict = min(((p, int(PLATFORMS[p].get("title_max") or 0)) for p in ps),
                 key=lambda x: x[1]) if ps else ("", 0)
    for r in req.rows:
        title = (r.title or "").strip()
        if not title:
            continue
        per, row_fail = [], False
        for p in ps:
            cfg = PLATFORMS[p]
            tmax = int(cfg.get("title_max") or 0)
            fit = bool(tmax and len(title) <= tmax)
            out = title if fit or req.title_policy == "flag" else title[:tmax]
            per.append({"platform": p, "display": cfg.get("display", p),
                        "title_max": tmax, "fit": fit, "title_out": out,
                        "language": cfg.get("listing_language") or cfg.get("language", "en")})
            csv_rows.append([r.sku, p, cfg.get("display", p), len(title), tmax,
                             "OK" if fit else "OVER", out])
            if not fit:
                row_fail = True
        if row_fail:
            fails += 1
        items.append({"sku": r.sku, "title": title, "len": len(title),
                      "fit_all": not row_fail, "platforms": per})
    summary = {"rows": len(items), "checks": len(items) * len(ps),
               "failing_rows": fails, "platforms": len(ps),
               "strict_platform": strict[0], "strict_limit": strict[1],
               "all_fit": fails == 0}
    return {"platforms": ps, "items": items, "summary": summary,
            "csv": _csv_text(["sku", "platform", "display", "title_len", "title_max",
                              "fit", "title_out"], csv_rows),
            "note": "标题只做字数硬校验；平台禁词/站点语言需人工复核。"}


# ---------------------------------------------------------------- 批量提交包
class PackBatchReq(BaseModel):
    rows: List[PackRow]
    platforms: List[str] = []
    eu_rep: Optional[EURep] = None
    bom: bool = True


@router.post("/pack-batch", summary="批量提交包：母表 × 12 平台 → 每平台 TSV + 合规块 + 清单 ZIP")
def pro_pack_batch(req: PackBatchReq):
    if not (1 <= len(req.rows) <= 100):
        raise HTTPException(400, "rows must contain 1..100 items")
    ps = _plats(req.platforms)
    rep = _dump(req.eu_rep)
    stamp = time.strftime("%Y%m%d")
    files, meta = [], []
    total_rows = high = trunc = 0
    for p in ps:
        cfg = PLATFORMS[p]
        tmax = int(cfg.get("title_max") or 0)
        lang = cfg.get("listing_language") or cfg.get("language", "en")
        rows_out, blocks = [], []
        for r in req.rows:
            blk = platform_rules.native_compliance_block(
                p, r.title, r.keywords, rep, model_batch=r.model_batch)
            risk = blk.get("risk_level", "NORMAL")
            title = r.title
            status = "OK"
            if tmax and len(title) > tmax:
                title = title[:tmax]
                status = "TRUNC"
                trunc += 1
            if risk == "HIGH":
                high += 1
            rows_out.append([r.sku, title, p, lang, len(title), tmax, status, risk,
                             (r.manufacturer or rep.get("manufacturer") or ""),
                             r.model_batch or "", blk.get("block", "").replace("\n", " ⏎ ")])
            blocks.append("[" + r.sku + "]\n" + blk.get("block", ""))
            total_rows += 1
        tsv_name = "gpsr_" + p + "_" + stamp + ".tsv"
        files.append((tsv_name, _csv_text(
            ["sku", "title", "platform", "listing_language", "title_len", "title_max",
             "title_status", "risk_level", "manufacturer", "model_batch",
             "compliance_block"], rows_out)))
        files.append(("compliance_blocks_" + p + ".txt", "\n\n".join(blocks)))
        meta.append({"platform": p, "display": cfg.get("display", p), "language": lang,
                     "title_max": tmax, "rows": len(rows_out), "file": tsv_name})
    manifest = _csv_text(["platform", "display", "listing_language", "title_max",
                          "rows", "file"],
                         [[m["platform"], m["display"], m["language"], m["title_max"],
                           m["rows"], m["file"]] for m in meta])
    files.append(("manifest.csv", manifest))
    files.append(("UPLOAD_GUIDE.txt",
                  "每平台一份 TSV + 一份合规块文本。Amazon 请再按 类目×站点×语言 拆分后上传；"
                  "错误 5995 是批量权限墙，先用 5-20 行探针文件。\n"))
    summary = {"rows": total_rows, "files": len(ps), "high_risk": high,
               "truncated": trunc, "platforms": len(ps)}
    return {"filename": "gpsr_pack_" + str(len(ps)) + "platforms_" + stamp + ".zip",
            "zip_base64": _zip_b64(files, req.bom), "files": meta,
            "manifest_text": manifest, "summary": summary,
            "note": "离线生成；不调用平台 API。"}


# ---------------------------------------------------------------- 申诉信
class AppealBatchRow(BaseModel):
    sku: str
    product: str


class AppealBatchReq(BaseModel):
    rows: List[AppealBatchRow]
    platforms: List[str] = []
    reason: str = "5995"
    lang: str = "en"
    manufacturer: str = ""
    root_cause: str = ""
    fix_applied: str = ""
    evidence_ids: List[str] = []


@router.post("/appeal-batch", summary="申诉信：多 SKU × 12 平台 → EN/DE/FR 信 + 清单 ZIP")
def pro_appeal_batch(req: AppealBatchReq):
    if not (1 <= len(req.rows) <= 50):
        raise HTTPException(400, "rows must contain 1..50 items")
    ps = _plats(req.platforms)
    lang = req.lang if req.lang in _APPEAL else "en"
    stamp = time.strftime("%Y%m%d")
    letters, files, rows_meta = [], [], []
    missing = 0
    for r in req.rows:
        for p in ps:
            ctx = dict(sku=r.sku, product=r.product, platform=p, reason=req.reason,
                       manufacturer=req.manufacturer or "[company]",
                       root_cause=req.root_cause or _REASON_HINT.get(req.reason, "[describe root cause]"),
                       fix_applied=req.fix_applied or _default_fix(req),
                       evidence=", ".join(req.evidence_ids) or _default_evidence(req))
            tpl = _APPEAL[lang]
            body = tpl["body"].format(**ctx)
            file = "appeal_" + p + "_" + r.sku + "_" + lang + ".txt"
            files.append((file, "Subject: " + tpl["subject"].format(**ctx) + "\n\n" + body))
            miss = [k for k, v in {"root_cause": req.root_cause,
                                   "manufacturer": req.manufacturer}.items() if not v]
            if miss:
                missing += 1
            letters.append({"sku": r.sku, "product": r.product, "platform": p,
                            "display": PLATFORMS[p].get("display", p),
                            "subject": tpl["subject"].format(**ctx),
                            "body": body, "lang": lang, "file": file,
                            "missing_inputs": miss})
            rows_meta.append([r.sku, p, req.reason, lang, file, " / ".join(miss) or "OK"])
    manifest = _csv_text(["sku", "platform", "reason", "lang", "file", "missing_inputs"],
                         rows_meta)
    files.append(("manifest.csv", manifest))
    summary = {"letters": len(letters), "skus": len(req.rows), "platforms": len(ps),
               "with_missing_inputs": missing}
    return {"filename": "appeals_" + str(len(letters)) + "_" + stamp + ".zip",
            "zip_base64": _zip_b64(files), "letters": letters,
            "manifest_text": manifest, "summary": summary,
            "note": "一封申诉只谈一个问题；被拒后等 72h 只补证据，不改事实。"}


# ---------------------------------------------------------------- 证据档案
class EvidenceBatchRow(BaseModel):
    sku: str
    product: str
    manufacturer: str
    address: str = ""
    category: str = ""
    keywords: List[str] = []


class EvidenceBatchReq(BaseModel):
    rows: List[EvidenceBatchRow]
    platforms: List[str] = []


@router.post("/evidence-batch", summary="证据档案：多产品 × 12 平台风险块 → DoC 草案 + 归档清单")
def pro_evidence_batch(req: EvidenceBatchReq):
    if not (1 <= len(req.rows) <= 50):
        raise HTTPException(400, "rows must contain 1..50 items")
    ps = _plats(req.platforms)
    year = int(time.strftime("%Y"))
    docs, files, csv_rows = [], [], []
    high = 0
    for r in req.rows:
        doc_id = "DOC-" + hashlib.sha256(
            (r.sku + "|" + r.product + "|" + r.manufacturer).encode()).hexdigest()[:12].upper()
        per, risk_max = [], "NORMAL"
        for p in ps:
            blk = platform_rules.native_compliance_block(p, r.product, r.keywords, None)
            risk = blk.get("risk_level", "NORMAL")
            if risk == "HIGH":
                risk_max = "HIGH"
                high += 1
            per.append({"platform": p, "display": PLATFORMS[p].get("display", p),
                        "risk_level": risk, "categories": blk.get("matched_categories", []),
                        "required_languages": blk.get("required_languages", []),
                        "block": blk.get("block", "")})
            csv_rows.append([doc_id, r.sku, p, risk,
                             " / ".join(blk.get("matched_categories", [])),
                             " / ".join(blk.get("required_languages", []))])
        declaration = [
            "Declaration of Conformity (draft) — " + doc_id,
            "We, " + r.manufacturer + (", " + r.address if r.address else "") +
            ", declare under our sole responsibility that the product",
            '「' + r.product + '」 (SKU: ' + r.sku + ") is in conformity with GPSR (EU) 2023/988.",
            "Retention: until " + str(year + 10) + "-12-31 (10 years, GPSR Art.9).",
        ]
        doc = {"doc_id": doc_id, "issued": time.strftime("%Y-%m-%d"),
               "retain_until": str(year + 10) + "-12-31", "sku": r.sku,
               "product": r.product, "manufacturer": r.manufacturer,
               "risk_level": risk_max, "platforms": per, "declaration": declaration}
        docs.append(doc)
        txt = "\n".join(declaration) + "\n\nPlatform checks:\n" + "\n".join(
            "- " + x["display"] + " / " + x["risk_level"] + " / " +
            " / ".join(x["categories"]) for x in per)
        files.append((doc_id + "_" + r.sku + ".txt", txt))
    manifest_text = _csv_text(["doc_id", "sku", "platform", "risk_level",
                               "categories", "required_languages"], csv_rows)
    files.append(("archive_manifest.csv", manifest_text))
    summary = {"docs": len(docs), "checks": len(csv_rows), "high_risk_checks": high,
               "platforms": len(ps)}
    return {"filename": "evidence_" + str(len(docs)) + "_docs.zip",
            "zip_base64": _zip_b64(files), "docs": docs,
            "manifest_text": manifest_text, "summary": summary,
            "note": "DoC 为草案；签字与标准编号须由制造商确认后归档。"}


# ---------------------------------------------------------------- 批量定价
class PricePackReq(BaseModel):
    rows: List[PriceRow]
    platforms: List[str] = []
    margin: float = 0.40
    vat: float = 0.19
    rounding: float = 0.99
    min_price: float = 0.0
    commission: float = 0.0            # 0 = 用平台默认费率
    factors: Dict[str, float] = {}


@router.post("/pricing-pack", summary="批量定价：采购价 × 12 平台 → 售价/佣金/净利 + CSV")
def pro_pricing_pack(req: PricePackReq):
    if not (1 <= len(req.rows) <= 500):
        raise HTTPException(400, "rows must contain 1..500 items")
    if not (0 <= req.margin < 0.95):
        raise HTTPException(400, "margin must be in [0, 0.95)")
    if req.vat < 0 or req.vat > 0.5:
        raise HTTPException(400, "vat must be in [0, 0.5]")
    ps = _plats(req.platforms)
    out, csv_rows = [], []
    for r in req.rows:
        base = (r.cost + r.shipping) / (1 - req.margin)
        net = base * (1 + req.vat)
        per = {}
        for p in ps:
            factor = req.factors.get(p, 1.0)
            raw = net * factor
            if req.rounding > 0:
                price = int(raw) + req.rounding
                if price < raw:
                    price += 1.0
            else:
                price = round(raw, 2)
            price = max(price, req.min_price)
            fee = req.commission if req.commission > 0 else _FEE_DEFAULT.get(p, 0.12)
            gross = price / (1 + req.vat)
            profit = round(gross * (1 - fee) - r.cost - r.shipping, 2)
            margin_pct = round(profit / price * 100, 1) if price else 0
            per[p] = {"price": round(price, 2), "fee": fee,
                      "fee_amount": round(price * fee, 2),
                      "net_profit": profit, "margin_pct": margin_pct,
                      "currency": _CURRENCY.get(p, "EUR")}
            csv_rows.append([r.sku, p, round(price, 2), _CURRENCY.get(p, "EUR"),
                             round(fee * 100, 1), round(price * fee, 2), profit, margin_pct])
        out.append({"sku": r.sku, "cost": r.cost, "shipping": r.shipping,
                    "base": round(base, 2), "net_with_vat": round(net, 2),
                    "platforms": per})
    summary = {"skus": len(out), "cells": len(csv_rows), "platforms": len(ps)}
    return {"rows": out, "summary": summary,
            "csv": _csv_text(["sku", "platform", "price", "currency", "fee_pct",
                              "fee_amount", "net_profit", "margin_pct"], csv_rows),
            "note": "佣金为可调估算值；真实费率为平台类目费率 + 仓储/支付费，需按后台核对。"}


# ---------------------------------------------------------------- 库存风险
class StockRef(BaseModel):
    sku: str
    available: int
    cost: float = 0.0


class StockPackReq(BaseModel):
    rows: List[StockRow]
    refs: List[StockRef] = []
    platforms: List[str] = []
    min_margin: float = 0.40
    max_price_gap: float = 0.15


@router.post("/stock-pack", summary="风险扫描：多渠库存/价格一致性 → 超卖/价差/破价 + CSV")
def pro_stock_pack(req: StockPackReq):
    if not (1 <= len(req.rows) <= 1000):
        raise HTTPException(400, "rows must contain 1..1000 items")
    ps = _plats(req.platforms)
    refs = {x.sku: x for x in req.refs}
    invalid = sorted(set(r.platform for r in req.rows if r.platform not in PLATFORMS))
    groups = {}
    for r in req.rows:
        if r.platform in ps:
            groups.setdefault(r.sku, []).append(r)
    out, alerts = [], []
    counts = {"oversell_risk": 0, "price_gap": 0, "below_margin": 0, "zero_stock": 0}
    for sku, rows in groups.items():
        committed = sum(max(0, x.stock) for x in rows)
        ref = refs.get(sku)
        avail = ref.available if ref else None
        prices = [x.price for x in rows if x.price > 0]
        lo, hi = (min(prices), max(prices)) if prices else (0, 0)
        gap = round((hi - lo) / lo, 4) if lo > 0 else 0
        floor = round(ref.cost / (1 - req.min_margin), 2) if ref and ref.cost and req.min_margin < 1 else None
        under = [x.platform for x in rows if floor and 0 < x.price < floor]
        zero = [x.platform for x in rows if x.stock <= 0]
        oversell = (committed - avail) if avail is not None and committed > avail else 0
        issues = []
        if oversell:
            issues.append("oversell_risk"); counts["oversell_risk"] += 1
            alerts.append(sku + ": committed " + str(committed) + " > available " + str(avail))
        if gap > req.max_price_gap:
            issues.append("price_gap"); counts["price_gap"] += 1
            alerts.append(sku + ": price gap " + str(round(gap * 100, 1)) + "%")
        if under:
            issues.append("below_margin"); counts["below_margin"] += 1
            alerts.append(sku + ": below floor on " + ", ".join(under))
        if zero:
            issues.append("zero_stock"); counts["zero_stock"] += 1
        out.append({"sku": sku, "channels": len(rows), "committed": committed,
                    "available": avail, "oversell_excess": oversell,
                    "price_min": lo, "price_max": hi, "price_gap": gap,
                    "margin_floor": floor, "underpriced_platforms": under,
                    "zero_stock_platforms": zero, "issues": issues,
                    "suggested_cut": max(0, oversell // max(1, len(rows)))})
    csv = _csv_text(["sku", "channels", "committed", "available", "oversell_excess",
                     "price_min", "price_max", "price_gap", "issues"],
                    [[x["sku"], x["channels"], x["committed"],
                      x["available"] if x["available"] is not None else "",
                      x["oversell_excess"], x["price_min"], x["price_max"],
                      x["price_gap"], " / ".join(x["issues"])] for x in out])
    return {"skus": len(out), "alerts": alerts, "rows": out, "csv": csv,
            "invalid_platforms": invalid, "summary": counts,
            "note": "离线比对，不是实时 API 同步；改数量需回各平台后台。"}

# =====================================================================
# 2026-11-09 · 12 平台跨境要求矩阵（驱动六个生成器的硬校验与提示）
# 说明：费率为参考值，可在定价设置里覆盖；合规项按 GPSR/DSA/EPR + 平台后台字段归纳。
# =====================================================================
_PLATFORM_REQ = {
    "amazon": {"title_max": 200, "language": "站点语言（UK/DE/FR/IT/ES/NL/SE/PL/BE/US）",
               "currency": "EUR / USD", "fee": 0.15, "vat": 19,
               "upload": "Manage Your Compliance 按 类目×站点×语言 拆分子文件（TSV/Excel）",
               "required": ["EU 责任人", "制造商", "型号/批次", "安全警告（站点语言）"],
               "docs": ["DoC", "技术文件", "风险评估"], "epr": "包装/电池/电子类需 EPR 注册号",
               "appeal": "Seller Performance Case（原 case 内追加证据）", "sla": "首次回复 24–48h",
               "rules": ["非品牌卖家批量上传常撞 5995 权限墙", "标题禁促销词/全大写", "美国站无 GPSR，走 FTC/CPSC"]},
    "ebay": {"title_max": 80, "language": "站点语言（DE/FR/IT/ES）", "currency": "EUR",
             "fee": 0.12, "vat": 19, "upload": "File Exchange（TSV/CSV）",
             "required": ["EU 责任人", "制造商", "物品特定属性（Type/MPN）"],
             "docs": ["DoC（按请求提交）"], "epr": "德国包装 LUCID 注册号",
             "appeal": "Resolution Center / eBay 客服", "sla": "3–5 个工作日",
             "rules": ["GPSR 责任人字段在 Business Policies/物品特定属性", "多站点需分站点文件"]},
    "fruugo": {"title_max": 100, "language": "英语（可本地化）", "currency": "EUR / GBP",
               "fee": 0.15, "vat": 19, "upload": "CSV/XML 批量",
               "required": ["EU 责任人", "制造商", "GPSR 信息"],
               "docs": ["DoC"], "epr": "按类目",
               "appeal": "Fruugo 商家支持工单", "sla": "2–3 个工作日",
               "rules": ["以英语母表分发多国", "价格含 VAT"]},
    "walmart": {"title_max": 100, "language": "英语", "currency": "USD",
                "fee": 0.15, "vat": 0, "upload": "Item Spec 批量表 / API",
                "required": ["制造商", "合规属性", "美国责任人（部分类目）"],
                "docs": ["CPSC/FTC 合规文件（按类目）"], "epr": "美国无 EPR；电池/电子需合规",
                "appeal": "Seller Support Case", "sla": "1–2 个工作日",
                "rules": ["美国站不走 GPSR", "需 GTIN/UPC", "危险品需 Hazmat 审核"]},
    "cdiscount": {"title_max": 120, "language": "法语", "currency": "EUR",
                  "fee": 0.12, "vat": 20, "upload": "CSV/XML",
                  "required": ["EU 责任人", "制造商", "法语安全信息"],
                  "docs": ["DoC"], "epr": "法国 EPR（包装/电子/家具）UIN",
                  "appeal": "Cdiscount 商家后台工单", "sla": "3–5 个工作日",
                  "rules": ["法语必填", "EPR 号缺失会被下架"]},
    "otto": {"title_max": 70, "language": "德语", "currency": "EUR",
             "fee": 0.15, "vat": 19, "upload": "Partner Portal CSV",
             "required": ["EU 责任人", "制造商", "德语安全信息", "图片白底"],
             "docs": ["DoC", "技术文件"], "epr": "德国 LUCID/电池注册",
             "appeal": "OTTO Partner Support", "sla": "2–4 个工作日",
             "rules": ["标题上限最严 70", "德语内容强制", "价格含 VAT"]},
    "allegro": {"title_max": 75, "language": "波兰语", "currency": "PLN",
                "fee": 0.10, "vat": 23, "upload": "CSV 批量",
                "required": ["EU 责任人", "制造商", "DSA 商家信息"],
                "docs": ["DoC"], "epr": "波兰 EPR（包装/电子）",
                "appeal": "Allegro 商家支持", "sla": "2–3 个工作日",
                "rules": ["DSA 要求商家身份/联系方式可见", "标题 75 字符"]},
    "emag": {"title_max": 150, "language": "罗马尼亚语", "currency": "RON",
             "fee": 0.12, "vat": 19, "upload": "CSV 批量",
             "required": ["EU 责任人", "制造商"],
             "docs": ["DoC"], "epr": "罗马尼亚 EPR",
             "appeal": "eMAG Marketplace 工单", "sla": "3–5 个工作日",
             "rules": ["罗语内容", "本地退货地址"]},
    "kaufland": {"title_max": 150, "language": "德语", "currency": "EUR",
                 "fee": 0.15, "vat": 19, "upload": "CSV / API",
                 "required": ["EU 责任人", "制造商", "德语安全信息"],
                 "docs": ["DoC"], "epr": "德国 LUCID",
                 "appeal": "Kaufland 商家支持", "sla": "2–4 个工作日",
                 "rules": ["德语必填", "需 GTIN"]},
    "bol": {"title_max": 120, "language": "荷兰语", "currency": "EUR",
            "fee": 0.12, "vat": 21, "upload": "CSV",
            "required": ["EU 责任人", "制造商", "荷兰语安全信息"],
            "docs": ["DoC"], "epr": "荷兰包装 EPR",
            "appeal": "bol.com 商家支持", "sla": "2–3 个工作日",
            "rules": ["荷语内容", "价格含 VAT"]},
    "zalando": {"title_max": 120, "language": "德语", "currency": "EUR",
                "fee": 0.18, "vat": 19, "upload": "Partner Portal",
                "required": ["EU 责任人", "制造商", "德语内容"],
                "docs": ["DoC"], "epr": "德国 LUCID",
                "appeal": "Zalando Partner Support", "sla": "3–5 个工作日",
                "rules": ["时尚类目为主", "内容审核严"]},
    "tiktok": {"title_max": 255, "language": "英语/站点语言", "currency": "USD / EUR",
               "fee": 0.05, "vat": 19, "upload": "CSV / API",
               "required": ["EU 责任人（欧盟站点）", "制造商"],
               "docs": ["DoC（欧盟站点）"], "epr": "欧盟站点按类目",
               "appeal": "TikTok Shop 商家工单", "sla": "1–3 个工作日",
               "rules": ["短视频内容与商品一致", "欧盟站点需 GPSR"]},
}


_CS_REQ = {
    "amazon": {"channel": "Buyer-Seller Messaging（站内信）", "first_response": "24 小时",
               "resolution": "48 小时内给出下一步", "return_window": "30 天（平台政策）；欧盟撤回权 14 天",
               "languages": ["en", "de", "fr", "it", "es", "nl", "sv", "pl"],
               "auto_reply": "可发模板/草稿；禁促销与站外联系方式；须 AI 身份披露",
               "must_include": ["订单号", "处理时限", "下一步动作"],
               "escalation": ["退款/赔偿承诺", "法律威胁", "产品安全事件", "假货指控"],
               "legal": ["GPSR 安全事件 15 天评估", "EU AI Act Art.50 披露", "DSA 商家信息"],
               "notes": ["德国/法国/意大利/西班牙站必须站点语言", "不得引导买家站外沟通"]},
    "ebay": {"channel": "Member-to-Member / Seller Hub Messages", "first_response": "24 小时",
             "resolution": "3 个工作日内", "return_window": "30 天（卖家政策）；欧盟撤回权 14 天",
             "languages": ["en", "de", "fr", "it", "es"],
             "auto_reply": "可自动回复；禁站外交易与联系方式；须 AI 身份披露",
             "must_include": ["Item ID / 订单号", "退货地址", "处理时限"],
             "escalation": ["Case 升级", "退款争议", "差评威胁", "法律威胁"],
             "legal": ["EU AI Act Art.50 披露", "GPSR 责任人字段", "DSA 商家信息"],
             "notes": ["多站点分语言回复", "退货政策以 listing 为准"]},
    "fruugo": {"channel": "Fruugo 商家消息", "first_response": "24–48 小时",
               "resolution": "48 小时", "return_window": "14 天（欧盟撤回权）",
               "languages": ["en", "de", "fr", "it", "es", "nl", "sv", "pl"],
               "auto_reply": "可草稿；退款/责任必须人工确认",
               "must_include": ["订单号", "退货流程", "预计处理时间"],
               "escalation": ["退款", "损坏", "安全事件"],
               "legal": ["EU AI Act Art.50 披露", "GPSR 信息"],
               "notes": ["英语母表可分发多国", "价格含 VAT"]},
    "walmart": {"channel": "Seller Center Messages", "first_response": "24 小时",
                "resolution": "48 小时", "return_window": "30 天（美国站）",
                "languages": ["en", "es"],
                "auto_reply": "可自动回复；禁站外联系方式；须 AI 身份披露",
                "must_include": ["订单号", "退货标签", "处理时限"],
                "escalation": ["退款", "法律威胁", "产品安全", "CPSC 召回"],
                "legal": ["FTC/CPSC 产品声明", "AI 身份披露"],
                "notes": ["美国站不走 GPSR", "危险品需 Hazmat 审核"]},
    "cdiscount": {"channel": "Cdiscount 商家后台消息", "first_response": "24 小时",
                 "resolution": "48 小时", "return_window": "14 天（欧盟撤回权）",
                 "languages": ["fr"],
                 "auto_reply": "可草稿；退款/责任必须人工确认",
                 "must_include": ["订单号", "法语回复", "处理时限"],
                 "escalation": ["退款", "法律威胁", "安全事件", "EPR 下架"],
                 "legal": ["EU AI Act Art.50 披露", "法国 EPR", "GPSR"],
                 "notes": ["法语必填", "EPR 号缺失会被下架"]},
    "otto": {"channel": "OTTO Partner Portal 消息", "first_response": "24 小时",
             "resolution": "48 小时", "return_window": "30 天（平台政策）；欧盟撤回权 14 天",
             "languages": ["de"],
             "auto_reply": "可草稿；退款/责任必须人工确认",
             "must_include": ["订单号", "德语回复", "处理时限"],
             "escalation": ["退款", "法律威胁", "安全事件"],
             "legal": ["EU AI Act Art.50 披露", "GPSR", "德国 LUCID"],
             "notes": ["德语强制", "退货地址须德国本地"]},
    "allegro": {"channel": "Allegro 站内消息", "first_response": "24 小时",
                "resolution": "48 小时", "return_window": "14 天（欧盟撤回权）",
                "languages": ["pl", "en"],
                "auto_reply": "可草稿；退款/责任必须人工确认",
                "must_include": ["订单号", "波兰语回复", "处理时限"],
                "escalation": ["退款", "法律威胁", "安全事件", "DSA 投诉"],
                "legal": ["EU AI Act Art.50 披露", "DSA 商家信息", "GPSR"],
                "notes": ["波兰语优先", "DSA 要求商家身份可见"]},
    "emag": {"channel": "eMAG Marketplace 消息", "first_response": "24 小时",
             "resolution": "48 小时", "return_window": "14 天（欧盟撤回权）",
             "languages": ["ro", "en"],
             "auto_reply": "可草稿；退款/责任必须人工确认",
             "must_include": ["订单号", "罗语回复", "本地退货地址"],
             "escalation": ["退款", "法律威胁", "安全事件"],
             "legal": ["EU AI Act Art.50 披露", "GPSR", "罗马尼亚 EPR"],
             "notes": ["罗语内容", "本地退货地址"]},
    "kaufland": {"channel": "Kaufland 商家后台消息", "first_response": "24 小时",
                 "resolution": "48 小时", "return_window": "14 天（欧盟撤回权）",
                 "languages": ["de"],
                 "auto_reply": "可草稿；退款/责任必须人工确认",
                 "must_include": ["订单号", "德语回复", "处理时限"],
                 "escalation": ["退款", "法律威胁", "安全事件"],
                 "legal": ["EU AI Act Art.50 披露", "GPSR", "德国 LUCID"],
                 "notes": ["德语必填", "需 GTIN"]},
    "bol": {"channel": "bol.com 商家消息", "first_response": "24 小时",
            "resolution": "48 小时", "return_window": "14 天（欧盟撤回权）",
            "languages": ["nl", "en"],
            "auto_reply": "可草稿；退款/责任必须人工确认",
            "must_include": ["订单号", "荷语回复", "处理时限"],
            "escalation": ["退款", "法律威胁", "安全事件"],
            "legal": ["EU AI Act Art.50 披露", "GPSR", "荷兰包装 EPR"],
            "notes": ["荷语内容", "价格含 VAT"]},
    "zalando": {"channel": "Zalando Partner Portal 消息", "first_response": "24 小时",
                "resolution": "48 小时", "return_window": "30 天（时尚类平台政策）；欧盟撤回权 14 天",
                "languages": ["de", "en"],
                "auto_reply": "可草稿；退款/责任必须人工确认",
                "must_include": ["订单号", "德语回复", "尺码/退货指引"],
                "escalation": ["退款", "法律威胁", "安全事件", "内容审核"],
                "legal": ["EU AI Act Art.50 披露", "GPSR", "德国 LUCID"],
                "notes": ["时尚类目为主", "内容审核严"]},
    "tiktok": {"channel": "TikTok Shop 商家消息", "first_response": "24 小时",
               "resolution": "48 小时", "return_window": "14 天（欧盟）/ 30 天（美国）",
               "languages": ["en", "de", "fr", "it", "es"],
               "auto_reply": "可草稿；禁站外交易；须 AI 身份披露",
               "must_include": ["订单号", "处理时限", "下一步"],
               "escalation": ["退款", "法律威胁", "安全事件", "短视频内容不符"],
               "legal": ["EU AI Act Art.50 披露", "GPSR（欧盟站点）", "DSA 商家信息"],
               "notes": ["短视频内容与商品一致", "欧盟站点需 GPSR"]},
}


@router.get("/customer-service-requirements", summary="12 平台 AI 客服服务口径")
def pro_customer_service_requirements():
    out = []
    for p, cfg in PLATFORMS.items():
        r = dict(_CS_REQ.get(p, {}))
        out.append({"platform": p, "display": cfg.get("display", p),
                    "countries": cfg.get("countries", []),
                    "listing_language": cfg.get("listing_language"),
                    **r})
    return {"count": len(out), "platforms": out,
            "note": "服务口径为工作台默认参考值；首次回复/退货期限以平台最新规则与卖家设置为主，AI 不替代人工承诺。"}


class CsCheckReq(BaseModel):
    platform: str = "amazon"
    language: str = "en"
    reply: str = ""
    message: str = ""


@router.post("/customer-service-check", summary="发送前客服草稿合规检查")
def pro_customer_service_check(req: CsCheckReq):
    policy = dict(_CS_REQ.get(req.platform, {}))
    issues = []
    reply = (req.reply or "").strip()
    low = reply.lower()

    if not reply:
        issues.append({"level": "high", "code": "empty", "text": "草稿为空，不能发送"})
    if len(reply) > 2000:
        issues.append({"level": "high", "code": "too_long", "text": "草稿超过 2000 字符，平台消息会被截断"})

    lang = (req.language or "en").lower()[:2]
    allowed = policy.get("languages") or []
    if allowed and lang not in allowed:
        issues.append({"level": "warning", "code": "language",
                       "text": "该平台建议语种为 " + " / ".join(allowed) + "，当前为 " + lang})

    if _re.search(r"(guarantee|guaranteed|100%|full refund|refund immediately|sofort.{0,20}(erstatt|rück)|rembours.{0,20}immédiat|gwarant.{0,20}zwrot|一定.{0,6}退款|保证.{0,6}退款)", low):
        issues.append({"level": "high", "code": "refund_promise",
                       "text": "出现退款/赔偿保证表述；AI 只能说明流程，不能替卖家承诺"})

    if _re.search(r"(we accept responsibility|we are liable|haftbar|responsable|odpowiedzialn|承担.{0,4}责任)", low):
        issues.append({"level": "high", "code": "liability",
                       "text": "出现责任认定表述；须人工审核后再发"})

    disclosure_words = (" ai", "assistant", "chatbot", "ki", "ia ", "sztuczn", "assistente")
    if not any(w in (" " + low) for w in disclosure_words):
        issues.append({"level": "warning", "code": "disclosure",
                       "text": "未见 AI 身份披露；EU AI Act Art.50 要求告知买家正在与 AI 沟通"})

    if _re.search(r"(order|bestellung|commande|zamów|订单|物流|tracking|sendung|colis|przesył)", (req.message or "").lower())             and not _re.search(r"\d{4,}", reply):
        issues.append({"level": "warning", "code": "order_fact",
                       "text": "买家问到订单/物流，但草稿没有订单号或可核实的节点"})

    score = 100 - 30 * len([i for i in issues if i["level"] == "high"]) - 10 * len([i for i in issues if i["level"] == "warning"])
    score = max(0, score)
    return {"ok": not any(i["level"] == "high" for i in issues), "score": score,
            "issues": issues, "policy": policy,
            "note": "检查为规则级预检，不替代平台后台审核；退款/责任/安全事件仍须人工。"}


@router.get("/platform-requirements", summary="12 平台跨境要求矩阵")
def pro_platform_requirements():
    out = []
    for p, cfg in PLATFORMS.items():
        r = dict(_PLATFORM_REQ.get(p, {}))
        out.append({"platform": p, "display": cfg.get("display", p),
                    "title_max": cfg.get("title_max"),
                    "countries": cfg.get("countries", []),
                    "listing_language": cfg.get("listing_language"),
                    "requirements": r})
    return {"count": len(out), "platforms": out,
            "note": "费率为参考值；合规项按 GPSR/DSA/EPR 与平台后台字段归纳，提交前以平台最新规则为准。"}


# ================================================================
# 2026-11-09  AI 商品内容 / 合规×事故 / Listing 监控
# 三块统一数据源：12 平台内容硬门槛 + 批量成稿 + 合规事故矩阵 + 监控体检
# 纯离线生成，不依赖第三方 API；写回仍走授权中心凭证。
# ================================================================
import base64 as _b64
import csv as _csv
import datetime as _dt
import io as _io
import re as _re
import zipfile as _zip

_LANGS8 = ["en", "de", "fr", "pl", "ro", "nl", "it", "es"]
_LANG_NAME = {"en": "英语", "de": "德语", "fr": "法语", "pl": "波兰语",
              "ro": "罗马尼亚语", "nl": "荷兰语", "it": "意语", "es": "西语"}
_PLAT_LANG = {"amazon": "en", "ebay": "en", "fruugo": "en", "walmart": "en",
              "cdiscount": "fr", "otto": "de", "allegro": "pl", "emag": "ro",
              "kaufland": "de", "bol": "nl", "zalando": "de", "tiktok": "en"}

_CONTENT_REQ = {
    "amazon": {"desc_max": 2000, "bullets": 5, "bullet_max": 500, "search_max": 249,
               "images_min": 7, "video": True, "aplus": True,
               "language": "站点语言（10 站）",
               "claims": "医疗功效/治愈、FDA 认证、100%/绝对化、促销词、全大写",
               "attrs": ["品牌", "型号", "颜色", "材质", "尺寸", "电池信息"],
               "extra": "美国站标题禁促销词；德国站须德语；A+ 仅品牌备案可用"},
    "ebay": {"desc_max": 4000, "bullets": 5, "bullet_max": 1000, "search_max": 500,
             "images_min": 12, "video": True, "aplus": False,
             "language": "站点语言（DE/FR/IT/ES）",
             "claims": "医疗功效、虚假时效、竞品品牌词",
             "attrs": ["品牌", "型号", "EAN", "MPN", "兼容性"],
             "extra": "Item Specifics 是硬字段，描述 HTML 可用"},
    "fruugo": {"desc_max": 5000, "bullets": 5, "bullet_max": 500, "search_max": 250,
               "images_min": 3, "video": False, "aplus": False,
               "language": "英语（泛欧统一）",
               "claims": "医疗功效、绝对化、未经授权品牌",
               "attrs": ["EAN", "品牌", "重量", "原产国"],
               "extra": "泛欧聚合，英语主稿 + 本地语言补充"},
    "walmart": {"desc_max": 1500, "bullets": 5, "bullet_max": 200, "search_max": 200,
                "images_min": 4, "video": True, "aplus": False,
                "language": "英语（美国）",
                "claims": "医疗功效、CPSC 召回词、竞品品牌",
                "attrs": ["GTIN", "品牌", "类目属性", "运输重量"],
                "extra": "美国站不走 GPSR，合规重心 FTC/CPSC"},
    "cdiscount": {"desc_max": 5000, "bullets": 5, "bullet_max": 500, "search_max": 250,
                  "images_min": 5, "video": False, "aplus": False,
                  "language": "法语",
                  "claims": "医疗功效、绝对化、法语拼写错误",
                  "attrs": ["EAN", "品牌", "法国 EPR UIN"],
                  "extra": "法语强制，EPR 号缺失会下架"},
    "otto": {"desc_max": 1000, "bullets": 5, "bullet_max": 300, "search_max": 200,
             "images_min": 6, "video": False, "aplus": False,
             "language": "德语",
             "claims": "医疗功效、价格比较、促销词",
             "attrs": ["GTIN", "品牌", "德语安全信息", "白底图"],
             "extra": "标题上限最严 70，德语内容强制"},
    "allegro": {"desc_max": 3000, "bullets": 5, "bullet_max": 500, "search_max": 300,
                "images_min": 8, "video": False, "aplus": False,
                "language": "波兰语",
                "claims": "医疗功效、绝对化、竞品品牌",
                "attrs": ["EAN", "品牌", "DSA 商家信息"],
                "extra": "DSA 要求商家身份/联系方式可见"},
    "emag": {"desc_max": 3000, "bullets": 5, "bullet_max": 500, "search_max": 200,
             "images_min": 5, "video": False, "aplus": False,
             "language": "罗马尼亚语",
             "claims": "医疗功效、绝对化",
             "attrs": ["EAN", "品牌", "本地退货地址"],
             "extra": "罗语内容，本地退货地址必填"},
    "kaufland": {"desc_max": 2000, "bullets": 5, "bullet_max": 500, "search_max": 200,
                 "images_min": 6, "video": False, "aplus": False,
                 "language": "德语",
                 "claims": "医疗功效、促销词、绝对化",
                 "attrs": ["GTIN", "品牌", "德语安全信息"],
                 "extra": "德语必填，需 GTIN"},
    "bol": {"desc_max": 3000, "bullets": 5, "bullet_max": 500, "search_max": 200,
            "images_min": 6, "video": False, "aplus": False,
            "language": "荷兰语",
            "claims": "医疗功效、绝对化",
            "attrs": ["EAN", "品牌", "荷兰语安全信息"],
            "extra": "荷语内容，价格含 VAT"},
    "zalando": {"desc_max": 2000, "bullets": 5, "bullet_max": 300, "search_max": 200,
                "images_min": 6, "video": False, "aplus": False,
                "language": "德语",
                "claims": "医疗功效、材质夸大",
                "attrs": ["品牌", "材质", "尺码/版型"],
                "extra": "时尚类目为主，内容审核严"},
    "tiktok": {"desc_max": 1000, "bullets": 5, "bullet_max": 300, "search_max": 200,
               "images_min": 5, "video": True, "aplus": False,
               "language": "英语/站点语言",
               "claims": "医疗功效、绝对化、短视频不一致",
               "attrs": ["品牌", "类目属性", "欧盟站点 GPSR"],
               "extra": "短视频内容须与商品一致"},
}

_L8 = {
    "en": {
        "join": "for",
        "b": ["Built for daily use: {k} with a durable, easy-care finish.",
              "Safety-first design: clear instructions, batch and model marked on the label.",
              "Practical for {use}: ready to use out of the box, compact to store.",
              "Quality-checked before dispatch; documents available for marketplace checks.",
              "Support in your marketplace language; spare parts and guides on request."],
        "desc": "{name} is made for everyday use. {usp} Key features: {kw}. The pack includes the product and a multilingual quick-start guide. Read the safety instructions before first use.",
    },
    "de": {
        "join": "für",
        "b": ["Für den täglichen Einsatz gebaut: {k} – robust und pflegeleicht.",
              "Sicherheitsorientiert: klare Anleitung, Charge und Modell auf dem Etikett.",
              "Praktisch für {use}: sofort einsatzbereit und kompakt verstaubar.",
              "Vor dem Versand geprüft; Unterlagen für Marktplatzprüfungen verfügbar.",
              "Support in Ihrer Marktplatzsprache; Ersatzteile und Anleitungen auf Anfrage."],
        "desc": "{name} ist für den täglichen Gebrauch gemacht. {usp} Hauptmerkmale: {kw}. Im Lieferumfang: Produkt und mehrsprachige Kurzanleitung. Bitte vor dem ersten Gebrauch die Sicherheitshinweise lesen.",
    },
    "fr": {
        "join": "pour",
        "b": ["Conçu pour un usage quotidien : {k}, robuste et facile à entretenir.",
              "Priorité à la sécurité : notice claire, lot et modèle indiqués sur l'étiquette.",
              "Pratique pour {use} : prêt à l'emploi, compact à ranger.",
              "Contrôlé avant expédition ; documents disponibles pour les vérifications.",
              "Assistance dans la langue de votre place de marché ; pièces et guides sur demande."],
        "desc": "{name} est conçu pour un usage quotidien. {usp} Caractéristiques clés : {kw}. L'emballage comprend le produit et un guide de démarrage multilingue. Lisez les consignes de sécurité avant la première utilisation.",
    },
    "pl": {
        "join": "do",
        "b": ["Stworzony do codziennego użytku: {k} – trwały i łatwy w pielęgnacji.",
              "Bezpieczeństwo przede wszystkim: jasna instrukcja, partia i model na etykiecie.",
              "Praktyczny do {use}: gotowy do użycia, kompaktowy w przechowywaniu.",
              "Sprawdzony przed wysyłką; dokumenty dostępne do weryfikacji marketplace.",
              "Wsparcie w języku Twojego marketplace; części i instrukcje na zamówienie."],
        "desc": "{name} został stworzony do codziennego użytku. {usp} Najważniejsze cechy: {kw}. Zestaw zawiera produkt oraz wielojęzyczną szybką instrukcję. Przed pierwszym użyciem przeczytaj zasady bezpieczeństwa.",
    },
    "ro": {
        "join": "pentru",
        "b": ["Creat pentru utilizare zilnică: {k} – rezistent și ușor de întreținut.",
              "Siguranța pe primul loc: instrucțiuni clare, lot și model pe etichetă.",
              "Practic pentru {use}: gata de utilizare, compact pentru depozitare.",
              "Verificat înainte de expediere; documente disponibile pentru platformă.",
              "Suport în limba platformei tale; piese și ghiduri la cerere."],
        "desc": "{name} este creat pentru utilizare zilnică. {usp} Caracteristici principale: {kw}. Pachetul include produsul și un ghid multilingv. Citiți instrucțiunile de siguranță înainte de prima utilizare.",
    },
    "nl": {
        "join": "voor",
        "b": ["Ontworpen voor dagelijks gebruik: {k} – stevig en eenvoudig te onderhouden.",
              "Veiligheid voorop: duidelijke instructies, batch en model op het label.",
              "Praktisch voor {use}: direct klaar voor gebruik, compact op te bergen.",
              "Gecontroleerd voor verzending; documenten beschikbaar voor marketplace-checks.",
              "Support in de taal van je marketplace; onderdelen en gidsen op aanvraag."],
        "desc": "{name} is ontworpen voor dagelijks gebruik. {usp} Belangrijkste kenmerken: {kw}. Het pakket bevat het product en een meertalige snelstartgids. Lees de veiligheidsinstructies voor het eerste gebruik.",
    },
    "it": {
        "join": "per",
        "b": ["Pensato per l'uso quotidiano: {k} – resistente e facile da pulire.",
              "Sicurezza al primo posto: istruzioni chiare, lotto e modello sull'etichetta.",
              "Pratico per {use}: pronto all'uso, compatto da riporre.",
              "Controllato prima della spedizione; documenti disponibili per il marketplace.",
              "Supporto nella lingua del marketplace; ricambi e guide su richiesta."],
        "desc": "{name} è pensato per l'uso quotidiano. {usp} Caratteristiche principali: {kw}. La confezione include il prodotto e una guida rapida multilingue. Leggere le istruzioni di sicurezza prima del primo utilizzo.",
    },
    "es": {
        "join": "para",
        "b": ["Diseñado para el uso diario: {k}: resistente y fácil de limpiar.",
              "Seguridad primero: instrucciones claras, lote y modelo en la etiqueta.",
              "Práctico para {use}: listo para usar, compacto de guardar.",
              "Revisado antes del envío; documentos disponibles para el marketplace.",
              "Soporte en el idioma de tu marketplace; recambios y guías bajo pedido."],
        "desc": "{name} está diseñado para el uso diario. {usp} Características principales: {kw}. El paquete incluye el producto y una guía rápida multilingüe. Lea las instrucciones de seguridad antes del primer uso.",
    },
}

_CLAIMS = ["cure", "heal", "medical", "fda", "100%", "best ", "no.1", "guarantee",
           "heil", "guérir", "guarir", "wyleczyć", "vindec", "curar", "millor"]


def _content_requirements() -> dict:
    out = []
    for p, cfg in PLATFORMS.items():
        c = dict(_CONTENT_REQ.get(p, {}))
        c["title_max"] = cfg.get("title_max")
        c["display"] = cfg.get("display", p)
        out.append({"platform": p, "display": c["display"], **c})
    return {"count": len(out), "platforms": out,
            "langs": [{"code": k, "name": v} for k, v in _LANG_NAME.items()],
            "note": "标题/描述上限按平台注册表；图片、视频、A+ 为后台硬门槛；宣称词按平台审核口径归纳。"}


@router.get("/content-requirements", summary="12 平台商品内容硬门槛（标题/描述/五点/图片/宣称）")
def pro_content_requirements():
    return _content_requirements()


def _cut(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,.;:-")


class ContentRow(BaseModel):
    sku: str
    name: str
    keywords: List[str] = []
    usp: List[str] = []
    audience: str = ""
    images: int = 0
    eu_rep: bool = False
    manufacturer: bool = False
    doc: bool = False
    epr: bool = False
    warnings: bool = False


class ContentPackReq(BaseModel):
    rows: List[ContentRow]
    platforms: List[str] = []
    langs: List[str] = []
    tone: str = "clear"


def _title_for(name, kws, audience, lang, limit):
    body = name.strip()
    if kws:
        body += " – " + ", ".join([k for k in kws[:2] if k])
    if audience:
        body += " " + _L8[lang]["join"] + " " + audience
    return _cut(body, limit)


def _bullets_for(kws, lang, use):
    k = kws[0] if kws else "product"
    tpl = _L8[lang]["b"]
    return [tpl[0].replace("{k}", k), tpl[1], tpl[2].replace("{use}", use or "daily use"),
            tpl[3], tpl[4]]


def _desc_for(name, kws, usp, lang):
    kw = ", ".join(kws[:4]) if kws else "product"
    u = " ".join(usp[:2]) if usp else "Designed for reliable everyday performance."
    return _L8[lang]["desc"].replace("{name}", name).replace("{usp}", u).replace("{kw}", kw)


def _claim_hits(text: str):
    low = text.lower()
    return [c for c in _CLAIMS if c in low]


def _zip_b64(files, bom=False) -> str:
    buf = _io.BytesIO()
    prefix = "\ufeff" if bom else ""
    items = files.items() if isinstance(files, dict) else files
    with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as z:
        for n, c in items:
            if isinstance(c, (bytes, bytearray)):
                z.writestr(n, c)
            else:
                z.writestr(n, (prefix + str(c)).encode("utf-8"))
    return _b64.b64encode(buf.getvalue()).decode()


@router.post("/content-pack", summary="一次母表 × 12 平台 × 8 语种 → 成稿包 + 校验 + ZIP")
def pro_content_pack(req: ContentPackReq):
    rows = [r for r in req.rows if r.sku and r.name]
    if not rows:
        raise HTTPException(400, "rows 至少一条，且 sku/name 必填")
    platforms = [p for p in dict.fromkeys(req.platforms) if p in PLATFORMS]
    langs = [l for l in dict.fromkeys(req.langs or _LANGS8) if l in _L8]
    if not platforms:
        raise HTTPException(400, "至少选一个平台")
    if not langs:
        raise HTTPException(400, "至少选一个语种")

    drafts, csv_rows, zip_files = [], [], {}
    truncated = claims = gaps = 0
    for r in rows:
        kws = [k.strip() for k in r.keywords if k and k.strip()]
        usp = [u.strip() for u in r.usp if u and u.strip()]
        use = r.audience or (kws[0] if kws else "daily use")
        for p in platforms:
            cfg = PLATFORMS[p]
            creq = _CONTENT_REQ.get(p, {})
            limit = int(cfg.get("title_max") or 200)
            for lang in langs:
                title = _title_for(r.name, kws, r.audience, lang, limit)
                cut = len(_title_for(r.name, kws, r.audience, lang, 9999)) > limit
                bullets = _bullets_for(kws, lang, use)[: int(creq.get("bullets") or 5)]
                desc = _desc_for(r.name, kws, usp, lang)
                desc = desc[: int(creq.get("desc_max") or 2000)]
                search = " ".join(kws[:6] + ([r.audience] if r.audience else []))
                search = _re.sub(r"[^0-9A-Za-z\u00C0-\u024F ]", " ", search)
                search = _cut(" ".join(search.split()), int(creq.get("search_max") or 200))
                hits = _claim_hits(" ".join([title, desc, " ".join(bullets)]))
                if hits:
                    claims += 1
                if cut:
                    truncated += 1
                gpsr = []
                if p != "walmart":
                    if not r.eu_rep:
                        gpsr.append("EU 责任人")
                    if not r.manufacturer:
                        gpsr.append("制造商")
                    if not r.doc:
                        gpsr.append("DoC/技术文件")
                    if not r.epr:
                        gpsr.append("EPR 注册号")
                    if not r.warnings:
                        gpsr.append("站点语言安全警告")
                if gpsr:
                    gaps += 1
                min_images = int(creq.get("images_min") or 1)
                fit_images = (r.images == 0) or (r.images >= min_images)
                media_required = bool(creq.get("video"))
                aplus_required = bool(creq.get("aplus"))
                attrs = list(creq.get("attrs") or [])
                status = "ok" if (not cut and not hits and not gpsr and fit_images) else "check"
                score = 100
                score -= 10 if cut else 0
                score -= 15 if hits else 0
                score -= min(20, 5 * len(gpsr))
                score -= 10 if not fit_images else 0
                d = {"sku": r.sku, "name": r.name, "platform": p,
                     "display": cfg.get("display", p), "lang": lang,
                     "lang_name": _LANG_NAME[lang], "title": title,
                     "title_len": len(title), "title_max": limit,
                     "bullets": bullets, "description": desc,
                     "desc_len": len(desc), "desc_max": int(creq.get("desc_max") or 0),
                     "search_terms": search, "search_max": int(creq.get("search_max") or 0),
                     "images_min": min_images, "images_have": r.images,
                     "images_ok": fit_images, "claims": hits, "gpsr_gaps": gpsr,
                     "video_required": media_required, "aplus_required": aplus_required,
                     "attrs": attrs, "score": score,
                     "checklist": {
                         "images": {"required": min_images, "provided": r.images, "ok": fit_images},
                         "video": {"required": media_required, "ok": True, "note": "需在主图视频位确认"},
                         "aplus": {"required": aplus_required, "ok": True, "note": "品牌备案后需上传 A+ 模块"},
                         "attributes": {"required": attrs, "ok": bool(attrs), "note": "按平台后台属性字段填写"},
                         "claims": {"ok": not hits, "hits": hits},
                         "gpsr": {"ok": not gpsr, "gaps": gpsr},
                     },
                     "status": status}
                drafts.append(d)
                csv_rows.append({"sku": r.sku, "platform": p, "lang": lang,
                                 "title": title, "title_len": len(title),
                                 "title_max": limit, "bullets": len(bullets),
                                 "desc_len": len(desc), "desc_max": d["desc_max"],
                                 "search_terms": search, "images_have": r.images,
                                 "images_min": min_images, "score": score,
                                 "claims": ";".join(hits),
                                 "gpsr_gaps": ";".join(gpsr), "status": status})
                key = "content_%s_%s.tsv" % (p, lang)
                if key not in zip_files:
                    zip_files[key] = "sku\tplatform\tlang\ttitle\tbullet1\tbullet2\tbullet3\tbullet4\tbullet5\tdescription\tsearch_terms\n"
                line = "\t".join([r.sku, p, lang, title] + bullets[:5] + ([""] * (5 - len(bullets[:5]))) + [desc, search])
                zip_files[key] += line + "\n"

    manifest = _io.StringIO()
    w = _csv.writer(manifest)
    w.writerow(["sku", "platform", "lang", "title_len", "title_max", "desc_len", "desc_max",
                "bullets", "images_have", "images_min", "score", "claims", "gpsr_gaps", "status"])
    for c in csv_rows:
        w.writerow([c["sku"], c["platform"], c["lang"], c["title_len"], c["title_max"],
                    c["desc_len"], c["desc_max"], c["bullets"], c["images_have"], c["images_min"],
                    c["score"], c["claims"], c["gpsr_gaps"], c["status"]])
    zip_files["manifest.csv"] = manifest.getvalue()
    zip_files["README.txt"] = ("CrossAIO content pack\n"
                               "平台：" + ", ".join(platforms) + "\n"
                               "语种：" + ", ".join(langs) + "\n"
                               "说明：按各平台标题/描述/五点/搜索词上限裁剪；缺 EU 责任人/制造商/DoC/EPR/警告语或图片不足的行在 manifest 标 check；score 为发布前检查分。\n")
    csv_text = manifest.getvalue()
    summary = {"skus": len(rows), "platforms": len(platforms), "langs": len(langs),
               "drafts": len(drafts), "truncated": truncated, "claims": claims,
               "gpsr_gaps": gaps, "ok": len([d for d in drafts if d["status"] == "ok"]),
               "image_gaps": len([d for d in drafts if not d["images_ok"]]),
               "video_required": len([d for d in drafts if d["video_required"]]),
               "aplus_required": len([d for d in drafts if d["aplus_required"]]),
               "avg_score": round(sum(d["score"] for d in drafts) / len(drafts), 1) if drafts else 0}
    return {"summary": summary, "drafts": drafts, "csv": csv_text,
            "manifest_text": csv_text, "zip_base64": _zip_b64(zip_files),
            "filename": "content_pack_%s.zip" % _dt.datetime.now().strftime("%Y%m%d"),
            "note": "离线成稿；标题按平台上限裁剪，宣称词与 GPSR 缺项已在结果里标出。"}


# ---------------------------------------------------------------- 合规 × 事故
class ComplianceRow(BaseModel):
    sku: str
    product: str
    category: str = ""
    eu_rep: bool = False
    manufacturer: bool = False
    doc: bool = False
    epr: bool = False
    label: bool = False
    warnings: bool = False
    traceability: bool = False
    incident_msg: str = ""


class CompliancePackReq(BaseModel):
    rows: List[ComplianceRow]
    platforms: List[str] = []
    scenario: str = "routine"   # routine | incident | recall


_REPLY = {
    "en": "We are sorry about this. Please stop using the product immediately, keep it away from children and do not return it before our safety team contacts you. Case {id} is open; we will reply within 24 hours.",
    "de": "Das tut uns leid. Bitte verwenden Sie das Produkt sofort nicht mehr, halten Sie es von Kindern fern und senden Sie es erst zurück, wenn unser Sicherheitsteam Sie kontaktiert. Fall {id} ist eröffnet; wir antworten innerhalb von 24 Stunden.",
    "fr": "Nous sommes désolés. Arrêtez immédiatement d'utiliser le produit, tenez-le hors de portée des enfants et ne le renvoyez pas avant le contact de notre équipe sécurité. Dossier {id} ouvert ; réponse sous 24 heures.",
    "pl": "Przepraszamy. Natychmiast zaprzestań używania produktu, trzymaj go poza zasięgiem dzieci i nie zwracaj go przed kontaktem z naszym zespołem ds. bezpieczeństwa. Sprawa {id} jest otwarta; odpowiemy w ciągu 24 godzin.",
    "ro": "Ne pare rău. Opriți imediat utilizarea produsului, țineți-l departe de copii și nu îl returnați înainte de contactul echipei noastre de siguranță. Cazul {id} este deschis; răspundem în 24 de ore.",
    "nl": "Het spijt ons. Stop onmiddellijk met het gebruik van het product, houd het uit de buurt van kinderen en stuur het niet terug voordat ons veiligheidsteam contact opneemt. Zaak {id} is geopend; wij reageren binnen 24 uur.",
    "it": "Ci scusiamo. Interrompere subito l'uso del prodotto, tenerlo lontano dai bambini e non restituirlo prima del contatto del nostro team sicurezza. Caso {id} aperto; risponderemo entro 24 ore.",
    "es": "Lo sentimos. Deje de usar el producto de inmediato, manténgalo fuera del alcance de los niños y no lo devuelva antes de que nuestro equipo de seguridad se ponga en contacto. Caso {id} abierto; responderemos en 24 horas.",
}


@router.get("/listing-requirements", summary="12 平台 Listing 监控口径（频率/字段/阈值）")
def pro_listing_requirements():
    out = []
    for p, cfg in PLATFORMS.items():
        creq = _CONTENT_REQ.get(p, {})
        buybox = p in ("amazon", "walmart", "tiktok")
        out.append({"platform": p, "display": cfg.get("display", p),
                    "title_max": cfg.get("title_max"),
                    "images_min": creq.get("images_min"),
                    "language": creq.get("language"),
                    "cadence": "价格/库存 15 分钟 · 内容 24 小时" if buybox else "价格/库存 30 分钟 · 内容 24 小时",
                    "fields": ["标题", "价格", "库存", "Buybox" if buybox else "上架状态",
                               "主图数量", "GPSR 合规块", "最后更新时间"],
                    "rules": ["标题超上限即拦截", "库存低于阈值报超卖", "价格跌破参考价报价差",
                              "Buybox 丢失报流量风险" if buybox else "上架状态异常报流量风险",
                              "内容 14 天未更新报陈旧"]})
    return {"count": len(out), "platforms": out,
            "note": "频率为工作台默认 SLA；真实实时同步需在授权中心接入平台 API。"}


@router.post("/compliance-pack", summary="合规×事故：SKU × 12 平台风险矩阵 + 事故闭环 + ZIP")
def pro_compliance_pack(req: CompliancePackReq):
    rows = [r for r in req.rows if r.sku and r.product]
    if not rows:
        raise HTTPException(400, "rows 至少一条，且 sku/product 必填")
    platforms = [p for p in dict.fromkeys(req.platforms) if p in PLATFORMS]
    if not platforms:
        raise HTTPException(400, "至少选一个平台")
    scenario = req.scenario if req.scenario in ("routine", "incident", "recall") else "routine"
    docs, zip_files = [], {}
    high = medium = 0
    deadline = (_dt.datetime.now() + _dt.timedelta(days=15)).strftime("%Y-%m-%d") if scenario != "routine" else ""
    for r in rows:
        for p in platforms:
            cfg = PLATFORMS[p]
            pr = _PLATFORM_REQ.get(p, {})
            checks = []
            eu = p != "walmart"
            if eu:
                checks += [("EU 责任人/进口商", bool(r.eu_rep), "硬阻断"),
                           ("制造商信息", bool(r.manufacturer), "硬阻断" if p in ("amazon", "otto", "kaufland") else "必填"),
                           ("DoC/技术文件", bool(r.doc), "硬阻断"),
                           ("EPR 注册号", bool(r.epr), "必填"),
                           ("标签/批次追溯", bool(r.label and r.traceability), "硬阻断" if p in ("amazon", "otto") else "必填"),
                           ("站点语言安全警告", bool(r.warnings), "必填")]
            else:
                checks += [("GTIN/类目属性", bool(r.label), "必填"),
                           ("FTC/CPSC 声明", bool(r.warnings), "必填"),
                           ("运输重量/尺寸", bool(r.traceability), "建议")]
            checks += [("平台专属：" + ("、".join((pr.get("required") or [])[:2]) or "后台字段"), True, "平台")]
            blockers = [c[0] for c in checks if not c[1] and c[2] == "硬阻断"]
            warns = [c[0] for c in checks if not c[1] and c[2] != "硬阻断"]
            risk = "high" if (blockers or scenario == "incident") else ("medium" if warns else "low")
            if risk == "high":
                high += 1
            elif risk == "medium":
                medium += 1
            inc_id = ""
            actions = []
            if scenario != "routine":
                inc_id = "INC-" + hashlib.sha1((r.sku + p + r.incident_msg).encode("utf-8")).hexdigest()[:8].upper()
                actions = ["冻结该平台 SKU 并暂停投放",
                           "给买家发安全指引（不认责、不承诺赔偿）",
                           "按 GPSR 安全门准备上报材料",
                           "改写 listing：补 EU 责任人/警告语/批次",
                           "证据归档：买家原话、截图、时间线、处理动作"]
            else:
                actions = ["补齐硬阻断项后再上架"] if blockers else (
                    ["补齐 EPR/警告语后复查"] if warns else ["维持现状，按周复查"])
            reply = ""
            if scenario == "incident":
                reply = _REPLY.get(_PLAT_LANG.get(p, "en"), _REPLY["en"]).replace("{id}", inc_id)
            d = {"sku": r.sku, "product": r.product, "platform": p,
                 "display": cfg.get("display", p), "risk": risk,
                 "blockers": blockers, "warnings": warns, "checks": checks,
                 "actions": actions, "incident_id": inc_id,
                 "deadline": deadline, "buyer_reply": reply}
            docs.append(d)
            fn = "dossier_%s_%s.txt" % (p, r.sku)
            zip_files[fn] = ("CrossAIO compliance dossier\n"
                             "SKU: %s\nProduct: %s\nPlatform: %s\nScenario: %s\nRisk: %s\nIncident: %s\nDeadline: %s\n"
                             "Checks:\n%s\nActions:\n%s\nBuyer reply:\n%s\n") % (
                r.sku, r.product, cfg.get("display", p), scenario, risk, inc_id, deadline,
                "\n".join(["  [%s] %s (%s)" % ("OK" if c[1] else "MISS", c[0], c[2]) for c in checks]),
                "\n".join(["  - " + a for a in actions]), reply)
    manifest = _io.StringIO()
    w = _csv.writer(manifest)
    w.writerow(["sku", "product", "platform", "risk", "blockers", "warnings", "incident", "deadline"])
    for d in docs:
        w.writerow([d["sku"], d["product"], d["platform"], d["risk"],
                    ";".join(d["blockers"]), ";".join(d["warnings"]), d["incident_id"], d["deadline"]])
    zip_files["manifest.csv"] = manifest.getvalue()
    summary = {"docs": len(docs), "skus": len(rows), "platforms": len(platforms),
               "high": high, "medium": medium, "incident": scenario != "routine"}
    return {"summary": summary, "docs": docs, "csv": manifest.getvalue(),
            "zip_base64": _zip_b64(zip_files),
            "filename": "compliance_pack_%s.zip" % _dt.datetime.now().strftime("%Y%m%d"),
            "note": "离线合规矩阵；硬阻断项需补齐后再上架，事故场景按内部 15 天 SLA 计时。"}


# ---------------------------------------------------------------- Listing 监控
class WatchRow(BaseModel):
    sku: str
    platform: str
    product: str = ""
    title: str = ""
    price: float = 0
    ref_price: float = 0
    stock: int = 0
    buybox: bool = True
    last_update: str = ""
    images: int = 0
    gpsr: bool = True


class WatchPackReq(BaseModel):
    rows: List[WatchRow]
    platforms: List[str] = []
    min_stock: int = 0
    price_gap_pct: float = 10
    stale_days: int = 14
    require_buybox: bool = True


@router.post("/listing-watch-pack", summary="Listing 监控：多 SKU × 12 平台体检 + 告警 + CSV")
def pro_listing_watch_pack(req: WatchPackReq):
    rows = [r for r in req.rows if r.sku and r.platform in PLATFORMS]
    if not rows:
        raise HTTPException(400, "rows 至少一条，且 sku/platform 有效")
    if req.platforms:
        allowed = set(req.platforms)
        rows = [r for r in rows if r.platform in allowed]
    alerts, out = [], []
    counts = {"title": 0, "price": 0, "stock": 0, "buybox": 0, "stale": 0, "content": 0}
    for r in rows:
        cfg = PLATFORMS[r.platform]
        creq = _CONTENT_REQ.get(r.platform, {})
        issues = []
        score = 100
        limit = int(cfg.get("title_max") or 200)
        if r.title and len(r.title) > limit:
            issues.append(("标题超上限 %d/%d" % (len(r.title), limit), "high", "按上限裁剪并重新提交"))
            counts["title"] += 1
            score -= 25
        if r.stock <= req.min_stock:
            issues.append(("库存 %d ≤ 阈值 %d" % (r.stock, req.min_stock), "high", "补货或下架防超卖"))
            counts["stock"] += 1
            score -= 25
        if r.ref_price and r.price and r.price < r.ref_price * (1 - req.price_gap_pct / 100.0):
            issues.append(("价格 %.2f 低于参考价 %.2f 超 %.0f%%" % (r.price, r.ref_price, req.price_gap_pct), "medium", "核对促销/汇率后调价"))
            counts["price"] += 1
            score -= 15
        if req.require_buybox and not r.buybox:
            issues.append(("Buybox 丢失", "high", "检查价格/配送/卖家指标"))
            counts["buybox"] += 1
            score -= 20
        stale = None
        if r.last_update:
            try:
                t = _dt.datetime.fromisoformat(r.last_update.replace("Z", "+00:00")).date()
                stale = (_dt.date.today() - t).days
            except Exception:
                stale = None
        if stale is None:
            issues.append(("缺少最后更新时间", "medium", "补更新时间后纳入日报"))
            counts["stale"] += 1
            score -= 10
        elif stale > req.stale_days:
            issues.append(("内容 %d 天未更新" % stale, "medium", "复查标题/图片/合规块"))
            counts["stale"] += 1
            score -= 10
        imin = int(creq.get("images_min") or 0)
        if imin and r.images and r.images < imin:
            issues.append(("主图 %d 张少于平台 %d 张" % (r.images, imin), "medium", "补图后再提交"))
            counts["content"] += 1
            score -= 10
        if r.platform != "walmart" and not r.gpsr:
            issues.append(("GPSR 合规块缺失", "high", "补 EU 责任人/警告语后回填"))
            counts["content"] += 1
            score -= 20
        risk = "high" if any(i[1] == "high" for i in issues) else ("medium" if issues else "low")
        d = {"sku": r.sku, "platform": r.platform, "display": cfg.get("display", r.platform),
             "product": r.product, "price": r.price, "stock": r.stock,
             "score": max(0, score), "risk": risk,
             "issues": [{"msg": i[0], "level": i[1], "fix": i[2]} for i in issues]}
        out.append(d)
        for i in issues:
            alerts.append({"sku": r.sku, "platform": r.platform, "level": i[1],
                           "alert": i[0], "fix": i[2]})
    csvb = _io.StringIO()
    w = _csv.writer(csvb)
    w.writerow(["sku", "platform", "product", "price", "stock", "score", "risk", "issues", "fixes"])
    for d in out:
        w.writerow([d["sku"], d["platform"], d["product"], d["price"], d["stock"],
                    d["score"], d["risk"], ";".join([i["msg"] for i in d["issues"]]),
                    ";".join([i["fix"] for i in d["issues"]])])
    summary = {"rows": len(rows), "alerts": len(alerts),
               "high": len([a for a in alerts if a["level"] == "high"]),
               "medium": len([a for a in alerts if a["level"] == "medium"]),
               "counts": counts}
    return {"summary": summary, "rows": out, "alerts": alerts, "csv": csvb.getvalue(),
            "note": "离线体检；Buybox/价格/库存实时值需授权中心接入平台 API 后回填。"}



# ---------- UI i18n dictionaries（三语界面词典，各语种独立端点） ----------
_UI_I18N_DIR = _Path(__file__).resolve().parent.parent / "static" / "ui_i18n"


@router.get("/ui-i18n/{lang}")
def get_ui_i18n(lang: str):
    """Return the UI dictionary for one language.

    Each language has its own file and endpoint so the switcher can load only
    the dictionary it needs: /pro/ui-i18n/en, /de, /fr.
    """
    if lang not in ("en", "de", "fr"):
        raise HTTPException(status_code=404, detail="unsupported language")
    p = _UI_I18N_DIR / (lang + ".json")
    if not p.exists():
        return {"lang": lang, "strings": {}}
    return {"lang": lang, "strings": _json.loads(p.read_text(encoding="utf-8"))}
