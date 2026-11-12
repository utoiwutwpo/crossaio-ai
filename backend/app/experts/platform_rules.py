"""
平台原生 GPSR 规则库 — 「平台原生」GPSR 差异化模块（零竞品）

通用 gpsr.py 只按"平台覆盖国家"计算警示语言；本模块为每个平台维护
**平台原生合规规则**（当地语言政策名、官方政策链接、当地监管机构、
平台特有规则、欧代字段要求、回填字段、违规后果），并用平台原生措辞
直接生成可粘贴的合规块。

覆盖平台（东欧/南欧为主，逐平台深耕）：
  allegro (PL/CZ/SK) · emag (RO) · cdiscount (FR) · otto (DE)
  kaufland (DE/AT/CZ/SK) · bol (NL/BE) · miravia (ES) · fruugo · zalando

⚠️ 政策摘要是工程辅助参考，非法律意见；以平台官方政策与欧盟官方文本为准。
"""
from typing import Dict, List, Optional

from . import gpsr
from .platform_registry import platform_config


# 12 平台共用语言层：平台自带表里没有的语言，用这套标准表述补齐，
# 避免 [DE]/[FR]/[HU] 段落到英文标题（此前 Amazon DE/FR、bol FR、allegro HU 都踩过）。
_GLOBAL_HEADER = {
    "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
    "de": "PRODUKTSICHERHEITSINFORMATIONEN (GPSR 2023/988)",
    "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
    "it": "INFORMAZIONI SULLA SICUREZZA DEL PRODOTTO (GPSR 2023/988)",
    "es": "INFORMACIÓN DE SEGURIDAD DEL PRODUCTO (GPSR 2023/988)",
    "pl": "INFORMACJE O BEZPIECZEŃSTWIE PRODUKTU (GPSR 2023/988)",
    "nl": "PRODUCTVEILIGHEIDSINFORMATIE (GPSR 2023/988)",
    "cs": "INFORMACE O BEZPEČNOSTI PRODUKTU (GPSR 2023/988)",
    "sk": "INFORMÁCIE O BEZPEČNOSTI PRODUKTU (GPSR 2023/988)",
    "hu": "TERMÉKBIZTONSÁGI INFORMÁCIÓK (GPSR 2023/988)",
    "ro": "INFORMAȚII DE SIGURANȚĂ A PRODUSULUI (GPSR 2023/988)",
    "sv": "PRODUKTSÄKERHETSINFORMATION (GPSR 2023/988)",
    "da": "PRODUKTSIKKERHEDSINFORMATION (GPSR 2023/988)",
    "bg": "ИНФОРМАЦИЯ ЗА БЕЗОПАСНОСТ НА ПРОДУКТА (GPSR 2023/988)",
}
_GLOBAL_REP_LABEL = {
    "en": "Responsible Economic Operator (EU)",
    "de": "Wirtschaftlicher Akteur in der EU",
    "fr": "Opérateur économique responsable (UE)",
    "it": "Operatore economico responsabile (UE)",
    "es": "Operador económico responsable (UE)",
    "pl": "Osoba odpowiedzialna w UE",
    "nl": "Verantwoordelijke economische operator (EU)",
    "cs": "Odpovědná osoba v EU",
    "sk": "Zodpovedná osoba v EÚ",
    "hu": "Felelős gazdasági szereplő (EU)",
    "ro": "Persoana responsabilă din UE",
    "sv": "Ansvarig ekonomisk aktör (EU)",
    "da": "Ansvarlig økonomisk aktør (EU)",
    "bg": "Отговорен икономически оператор (ЕС)",
}
_ROW_LABELS = {
    "en": {"mfr": "Manufacturer", "imp": "Importer", "product": "Product", "mb": "Model/Batch"},
    "de": {"mfr": "Hersteller", "imp": "Importeur", "product": "Produkt", "mb": "Modell/Charge"},
    "fr": {"mfr": "Fabricant", "imp": "Importateur", "product": "Produit", "mb": "Modèle/Lot"},
    "it": {"mfr": "Produttore", "imp": "Importatore", "product": "Prodotto", "mb": "Modello/Lotto"},
    "es": {"mfr": "Fabricante", "imp": "Importador", "product": "Producto", "mb": "Modelo/Lote"},
    "pl": {"mfr": "Producent", "imp": "Importer", "product": "Produkt", "mb": "Model/Partia"},
    "nl": {"mfr": "Fabrikant", "imp": "Importeur", "product": "Product", "mb": "Model/Batch"},
    "cs": {"mfr": "Výrobce", "imp": "Dovozce", "product": "Výrobek", "mb": "Model/Šarže"},
    "sk": {"mfr": "Výrobca", "imp": "Dovozca", "product": "Výrobok", "mb": "Model/Šarža"},
    "hu": {"mfr": "Gyártó", "imp": "Importőr", "product": "Termék", "mb": "Modell/Tétel"},
    "ro": {"mfr": "Producător", "imp": "Importator", "product": "Produs", "mb": "Model/Lot"},
    "sv": {"mfr": "Tillverkare", "imp": "Importör", "product": "Produkt", "mb": "Modell/Batch"},
    "da": {"mfr": "Producent", "imp": "Importør", "product": "Produkt", "mb": "Model/Batch"},
    "bg": {"mfr": "Производител", "imp": "Вносител", "product": "Продукт", "mb": "Модел/Партида"},
}


def _rules_allegro() -> Dict:
    return {
        "policy_name": "Bezpieczeństwo produktów i GPSR (Regulamin Allegro)",
        "policy_url": "https://allegro.pl/pomoc/faq/produkcja-i-bezpieczenstwo",
        "authority": "UOKiK（波兰竞争与消费者保护局）",
        "native_language": "pl",
        "listing_field": "description / Safety information 字段",
        "rep_requirements": [
            "欧盟责任人名称+邮政地址（波兰卖家可用本土实体）",
            "联系方式（email）必须可读，不允许纯图片",
            "产品标识（型号/批次）须与包装一致",
        ],
        "enforcement": "违规 listing 隐藏/下架；累犯限制账户功能；UOKiK 可处最高营业额 10% 罚款",
        "rules": [
            "2024-12 起 Allegro 要求非欧盟卖家在 listing 中披露欧盟责任人，否则按 GPSR 下架",
            "波兰语警示语为强制；CZ/SK 站点买家可读性按 Allegro 翻译政策处理",
            "玩具类须附 EN 71 测试摘要（DoC 可用链接形式）",
        ],
        "block_header": {
            "pl": "INFORMACJE O BEZPIECZEŃSTWIE PRODUKTU (GPSR 2023/988)",
            "cs": "INFORMACE O BEZPEČNOSTI PRODUKTU (GPSR 2023/988)",
            "sk": "INFORMÁCIE O BEZPEČNOSTI PRODUKTU (GPSR 2023/988)",
            "hu": "TERMÉKBIZTONSÁGI INFORMÁCIÓK (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "pl": "Osoba odpowiedzialna w UE",
            "cs": "Odpovědná osoba v EU",
            "sk": "Zodpovedná osoba v EÚ",
            "hu": "Felelős gazdasági szereplő (EU)",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_emag() -> Dict:
    return {
        "policy_name": "Politica de siguranță a produselor (eMAG Marketplace)",
        "policy_url": "https://marketplace.emag.ro/politici/siguranta-produselor",
        "authority": "ANPC（罗马尼亚国家消费者保护局）",
        "native_language": "ro",
        "listing_field": "Descriere / Secțiunea „Siguranță”",
        "rep_requirements": [
            "罗马尼亚境内可用欧盟责任人；eMAG 要求名称+地址+电话+email",
            "GPSR 信息须在照片之外以文字形式出现在 description 中",
            "产品页须含 DoC（符合性声明）链接或可索取方式",
        ],
        "enforcement": "ANPC 罚款（单次最高 10 万 RON）；eMAG 下架且冻结付款直至整改",
        "rules": [
            "eMAG 罗马尼亚站要求罗马尼亚语警示语（ANPC 执法语言）",
            "匈牙利语可选（eMAG.HU 为独立站点，不自动同步）",
            "电子产品须在描述中标注 RoHS 与 WEEE 回收信息",
        ],
        "block_header": {
            "ro": "INFORMAȚII DE SIGURANȚĂ A PRODUSULUI (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "ro": "Persoana responsabilă din UE",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_cdiscount() -> Dict:
    return {
        "policy_name": "Charte sécurité produits & GPSR (Cdiscount Marketplace)",
        "policy_url": "https://seller.cdiscount.com/marque-blanche/reglementation",
        "authority": "DGCCRF（法国竞争、消费与反欺诈总局）",
        "native_language": "fr",
        "listing_field": "Description longue / Informations de sécurité",
        "rep_requirements": [
            "欧盟责任人信息须为法文；DGCCRF 要求 email 可回执",
            "法国站强制法语警示语（Loi Toubon：对消费者信息必须法语）",
            "产品标识、CE 标识、欧代三要素须同页出现",
        ],
        "enforcement": "DGCCRF 行政传唤/刑事罚（最高 2 年监禁 + 30 万欧元）；Cdiscount 直接下架",
        "rules": [
            "法语警示语为强制（Loi Toubon 法），不可仅用英语替代",
            "食品接触产品须附法语「接触食品」声明与 DGCCRF 编号",
            "含纽扣电池产品须附儿童吞咽警示（2023 起法国专项执法重点）",
        ],
        "block_header": {
            "fr": "INFORMATIONS DE SÉCURITÉ PRODUIT (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "fr": "Opérateur économique responsable (UE)",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_otto() -> Dict:
    return {
        "policy_name": "Produktsicherheit & GPSR (Otto Marketplace Richtlinien)",
        "policy_url": "https://partner.otto.de/marktplatz/richtlinien",
        "authority": "Marktüberwachungsbehörden der Länder（德国各州市场监管机构）",
        "native_language": "de",
        "listing_field": "Produktbeschreibung / Sicherheitshinweise",
        "rep_requirements": [
            "德国市场监管（ProdSG 6 Abs. 2）要求欧代信息德文可读",
            "Otto 要求欧代信息在 listing 与包装双重一致",
            "GS 标志（如适用）与 CE 并列展示",
        ],
        "enforcement": "ProdSG 罚款最高 10 万欧元/例；Otto 下架并影响店铺评分",
        "rules": [
            "德语警示语强制；Otto 对德国站listing执行 GPSR 抽检",
            "插头制式须 Schuko（DE/AT），IT/CH 制式需单独说明",
            "包装法 (VerpackG) LUCID 注册号须可提供",
        ],
        "block_header": {
            "de": "PRODUKTSICHERHEITSINFORMATIONEN (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "de": "Wirtschaftlicher Akteur in der EU",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_kaufland() -> Dict:
    return {
        "policy_name": "Produktsicherheit (Kaufland Global Selling Richtlinien)",
        "policy_url": "https://seller.kaufland.de/help/product-safety",
        "authority": "Marktüberwachungsbehörden（DE）+ ČIA/ÚOP（CZ/SK）",
        "native_language": "de",
        "listing_field": "Produktbeschreibung / Sicherheitshinweise",
        "rep_requirements": [
            "欧代信息须覆盖全部销售站点语言（DE/AT/CZ/SK）",
            "Kaufland 要求上传 DoC 文件到 Seller Portal",
        ],
        "enforcement": "下架 + Seller Portal 违规记录；德国站 ProdSG 罚款风险",
        "rules": [
            "四国站点（DE/AT/CZ/SK）共享 listing，警示语需覆盖四语言",
            "玩具类上传 EN 71 DoC 为站点硬性要求",
        ],
        "block_header": {
            "de": "PRODUKTSICHERHEITSINFORMATIONEN (GPSR 2023/988)",
            "cs": "INFORMACE O BEZPEČNOSTI PRODUKTU (GPSR 2023/988)",
            "sk": "INFORMÁCIE O BEZPEČNOSTI PRODUKTU (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "de": "Wirtschaftlicher Akteur in der EU",
            "cs": "Odpovědná osoba v EU",
            "sk": "Zodpovedná osoba v EÚ",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_bol() -> Dict:
    return {
        "policy_name": "Productveiligheid & GPSR (bol Verkoopvoorwaarden)",
        "policy_url": "https://verkoper.bol.com/nl/hulp/productveiligheid",
        "authority": "ACM（荷兰消费者与市场管理局）+ FOD（比利时）",
        "native_language": "nl",
        "listing_field": "Omschrijving / Veiligheidsinformatie",
        "rep_requirements": [
            "荷兰语/法语（BE）责任人信息；ACM 要求 email 可回执",
            "bol 要求 EU 责任人信息出现在 listing 与发票两处",
        ],
        "enforcement": "ACM 罚款（最高营业额 1%/90 万欧元）；bol 下架且扣除转化权重",
        "rules": [
            "荷兰语警示语强制；比利时买家用法语警示语",
            "含电池产品须标注 RECURSEL/BEBAT 回收信息",
        ],
        "block_header": {
            "nl": "PRODUCTVEILIGHEIDSINFORMATIE (GPSR 2023/988)",
            "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "nl": "Verantwoordelijke economische operator (EU)",
            "fr": "Opérateur économique responsable (UE)",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_miravia() -> Dict:
    return {
        "policy_name": "Seguridad de productos (Miravia Marketplace Policies)",
        "policy_url": "https://seller.miravia.es/politicas",
        "authority": "AESAN / Ministerio de Consumo（西班牙）",
        "native_language": "es",
        "listing_field": "Descripción / Información de seguridad",
        "rep_requirements": [
            "西班牙语责任人信息；Miravia 要求 EU 责任人信息为文本非图片",
            "产品标识与批次须与实物一致",
        ],
        "enforcement": "下架 + 店铺评分降权；西班牙消费者法罚款最高 100 万欧元",
        "rules": [
            "西班牙语警示语强制",
            "Miravia 对跨境卖家执行 GPSR 文件抽查（DoC + 欧代授权书）",
        ],
        "block_header": {
            "es": "INFORMACIÓN DE SEGURIDAD DEL PRODUCTO (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "es": "Operador económico responsable (UE)",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_generic() -> Dict:
    """fruugo / zalando / tiktok / walmart / amazon 等走通用规则（英文基础）。"""
    return {
        "policy_name": "General Product Safety Regulation (EU) 2023/988",
        "policy_url": "https://eur-lex.europa.eu/eli/reg/2023/988/oj",
        "authority": "EU Member State Market Surveillance Authorities",
        "native_language": "en",
        "listing_field": "description / product safety details",
        "rep_requirements": [
            "EU responsible person name + postal address + email",
            "Product identifier (model/batch) must match packaging",
        ],
        "enforcement": "Listing removal per GPSR Art.35 / marketplace enforcement",
        "rules": [
            "Listing must show EU responsible person information (GPSR Art.9)",
            "Warnings must be in the language(s) of the sales country",
        ],
        "block_header": {
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "en": "Responsible Economic Operator (EU)",
        },
    }


_RULE_BUILDERS = {
    "allegro": _rules_allegro,
    "emag": _rules_emag,
    "cdiscount": _rules_cdiscount,
    "otto": _rules_otto,
    "kaufland": _rules_kaufland,
    "bol": _rules_bol,
}
_GENERIC_PLATFORMS = ("amazon", "ebay", "fruugo", "walmart",
                      "zalando", "tiktok_shop_eu", "tiktok_shop_uk")


def has_native_rules(platform: str) -> bool:
    return platform in _RULE_BUILDERS


def get_platform_rules(platform: str) -> Dict:
    """返回平台原生 GPSR 规则集（未知平台抛 KeyError）。"""
    platform_config(platform)  # 校验平台合法性
    if platform in _RULE_BUILDERS:
        return _RULE_BUILDERS[platform]()
    return _rules_generic()


def platform_rules_card(platform: str) -> Dict:
    """平台原生规则卡（免费展示层）：政策名/链接/监管机构/后果/规则数。

    展示"我们知道该平台所有合规规则"，但完整原生合规块文本需付费解锁。
    """
    r = get_platform_rules(platform)
    return {
        "platform": platform,
        "native_rules": has_native_rules(platform),
        "policy_name": r["policy_name"],
        "policy_url": r["policy_url"],
        "authority": r["authority"],
        "native_language": r["native_language"],
        "listing_field": r["listing_field"],
        "rep_requirements": r["rep_requirements"],
        "enforcement": r["enforcement"],
        "rules": r["rules"],
        "rule_count": len(r["rules"]),
        "warning_language_count": len(r["block_header"]),
    }


def native_compliance_block(platform: str, product_name: str,
                            keywords: List[str],
                            eu_rep: Optional[Dict] = None,
                            model_batch: str = "") -> Dict:
    """从平台原生规则直接生成对应语言合规块（「平台原生」差异化核心）。

    与通用 gpsr.gpsr_block_text 的区别：
    - 头部用平台当地语言（如 Allegro 波兰语 INFORMACJE O BEZPIECZEŃSTWIE）
    - 欧代行标签用平台原生语言
    - 警示语覆盖平台要求的全部语言（含东欧 CZ/SK/HU 等）
    - 末尾引用平台官方政策与当地监管机构
    """
    rules = get_platform_rules(platform)
    categories = gpsr.detect_categories(product_name, keywords)
    languages = gpsr.required_languages(platform)

    # 优先用平台 block_header 支持的语言；不足再补平台要求语言
    header_langs = list(rules["block_header"].keys())
    ordered = [l for l in header_langs if l in languages]
    ordered += [l for l in languages if l not in ordered]

    rep = eu_rep or {}
    # GPSR Art.16 标签必填：制造商 + 进口商（如有）+ 型号/批次。
    mfr_name = (rep.get("manufacturer") or "").strip()
    mfr_addr = (rep.get("manufacturer_address") or "").strip()
    imp_name = (rep.get("importer") or "").strip()
    imp_addr = (rep.get("importer_address") or "").strip()
    mfr_line = (mfr_name or "[MANUFACTURER REQUIRED]") + (", " + mfr_addr if mfr_addr else "")
    imp_line = (imp_name + (", " + imp_addr if imp_addr else "")) if imp_name else ""
    mb_text = (model_batch or "").strip() or "[MODEL/BATCH REQUIRED]"
    rep_name = rep.get("company_name", "[欧代公司名称]")
    rep_addr = rep.get("address", "[欧代地址]")
    rep_mail = rep.get("email", "[联系邮箱]")

    lines: List[str] = []
    shown_langs: List[str] = []
    for lang in ordered[:5]:  # 最多 5 段，防超 listing 字段长度
        native_header = rules["block_header"].get(lang) or _GLOBAL_HEADER.get(lang)
        header = native_header or rules["block_header"]["en"]
        label = (rules["rep_label"].get(lang) or _GLOBAL_REP_LABEL.get(lang)
                 or rules["rep_label"]["en"])
        row = _ROW_LABELS.get(lang) or _ROW_LABELS["en"]
        # 缺该语言母语标题时显式标 (EN)，不让 [CS]/[FR] 段冒充母语
        lines.append(f"[{lang.upper()}] {header}" + ("" if native_header else " (EN)"))
        lines.append(f"  {label}: {rep_name}, {rep_addr}, {rep_mail}")
        lines.append(f"  {row['mfr']}: {mfr_line}")
        if imp_line:
            lines.append(f"  {row['imp']}: {imp_line}")
        lines.append(f"  {row['product']}: {product_name} | {row['mb']}: {mb_text}")
        # 警示语：优先该语言，其次 en；均无则不输出空 bullet
        warn_written = False
        for rule in categories:
            w = rule["warnings"].get(lang)
            if not w:
                w = rule["warnings"].get("en")
                if w:
                    w = w + " (EN)"      # 回退英语必须显式标注，不冒充母语
            if w:
                lines.append(f"  • {w}")
                warn_written = True
        if not warn_written and categories:
            lines.append(f"  • Safety warnings: see user manual "
                         f"({rules['native_language'].upper()}/EN translation required)")
        lines.append("")
        shown_langs.append(lang)

    lines.append(f"ℹ️ 平台官方政策：{rules['policy_name']}")
    lines.append(f"ℹ️ 当地监管机构：{rules['authority']} — {rules['enforcement']}")

    return {
        "platform": platform,
        "native_rules": has_native_rules(platform),
        "product_name": product_name,
        "risk_level": ("high" if any(r["risk"] == "high" for r in categories)
                       else ("medium" if categories else "low")),
        "matched_categories": [r["label"] for r in categories],
        "required_languages": languages,
        "block_languages": shown_langs,
        "block": "\n".join(lines).strip(),
    }


# ---------- 模块级便捷导出 ----------
def list_native_rule_platforms() -> List[str]:
    """已建平台原生规则的平台列表（东欧/南欧深耕平台）。"""
    return list(_RULE_BUILDERS.keys())
