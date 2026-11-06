"""
平台原生 GPSR 规则库 — 「平台原生」GPSR 差异化模块（零竞品）

通用 gpsr.py 只按"平台覆盖国家"计算警示语言；本模块为每个平台维护
**平台原生合规规则**（当地语言政策名、官方政策链接、当地监管机构、
平台特有规则、欧代字段要求、回填字段、违规后果），并用平台原生措辞
直接生成可粘贴的合规块。

覆盖平台（2026-11-06 补齐 registry 全部 13 平台）：
  amazon (EU) · amazon_us (US) · ebay (EU/DE) · zalando (EU 15 国)
  fruugo (全球 30+ 国) · walmart (US) · tiktok (TikTok Shop EU)
  allegro (PL/CZ/SK) · emag (RO) · cdiscount (FR) · otto (DE)
  kaufland (DE/AT/CZ/SK) · bol (NL/BE)

⚠️ 政策摘要是工程辅助参考，非法律意见；以平台官方政策与欧盟官方文本为准。
"""
from typing import Dict, List, Optional

from . import gpsr
from .platform_registry import platform_config


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
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "pl": "Osoba odpowiedzialna w UE",
            "cs": "Odpovědná osoba v EU",
            "sk": "Zodpovedná osoba v EÚ",
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
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "nl": "Verantwoordelijke economische operator (EU)",
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_amazon() -> Dict:
    """Amazon 欧盟站（DE/FR/IT/ES/PL/SE/NL/BE/AT/IE）— 2026 后台卡点最深。"""
    return {
        "policy_name": "Product Compliance & GPSR Requirements (Amazon EU Seller Central)",
        "policy_url": "https://sellercentral.amazon.eu/help/hub/reference",
        "authority": "EU Member State Market Surveillance Authorities（各成员国市场监管机构）",
        "native_language": "en",
        "listing_field": "listing 安全属性字段 / Manage Your Compliance 后台提交",
        "rep_requirements": [
            "制造商名称 + 邮政地址（欧盟境外制造商须有 EU 责任人）",
            "产品标识（型号/批次）须与包装一致，按 ASIN 逐条匹配",
            "安全警示与合规文件按站点当地语言（DE/FR/IT/ES/PL/NL/SE）",
        ],
        "enforcement": "ASIN 屏蔽/下架 + Account Health 降权；批量上传缺 GPSR 字段报 Error 5995 拦截整批；成员国监管可强制召回",
        "rules": [
            "2024-12-13 起 GPSR 适用于欧盟站全部 listing（此前已投放市场的旧库存豁免，需可证明投放日期）",
            "2026 年主要卡点在后台：Manage Your Compliance 面板集中提交，批量上传缺字段直接报 Error 5995",
            "非欧盟卖家必须先绑定 EU 责任人，否则 ASIN 逐条屏蔽且无法通过模板补录",
            "警示语与安全信息须为各站点当地语言，仅英语在 DE/FR/IT/ES 站会被判不完整",
            "被屏蔽 ASIN 的申诉须附 DoC、EU RP 授权书与测试报告，材料不全直接驳回",
        ],
        "block_header": {
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
            "de": "PRODUKTSICHERHEITSINFORMATION (GPSR 2023/988)",
            "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
            "it": "INFORMAZIONI DI SICUREZZA DEL PRODOTTO (GPSR 2023/988)",
            "es": "INFORMACIÓN DE SEGURIDAD DEL PRODUCTO (GPSR 2023/988)",
            "nl": "PRODUCTVEILIGHEIDSINFORMATIE (GPSR 2023/988)",
            "pl": "INFORMACJE O BEZPIECZEŃSTWIE PRODUKTU (GPSR 2023/988)",
        },
        "rep_label": {
            "en": "Responsible Economic Operator (EU)",
            "de": "Wirtschaftsteilnehmer in der EU (Verantwortliche Person)",
            "fr": "Personne responsable dans l'UE",
            "it": "Operatore economico responsabile (UE)",
            "es": "Operador económico responsable (UE)",
            "nl": "Verantwoordelijke economische operator (EU)",
            "pl": "Osoba odpowiedzialna w UE",
        },
    }


def _rules_amazon_us() -> Dict:
    """Amazon 美国站 — GPSR 不直接适用，但向欧盟销售仍需 EU RP。"""
    return {
        "policy_name": "Product Safety & Compliance Requirements (Amazon US Seller Central)",
        "policy_url": "https://sellercentral.amazon.com/help/hub/reference",
        "authority": "CPSC（美国消费品安全委员会）",
        "native_language": "en",
        "listing_field": "description / Safety information 字段",
        "rep_requirements": [
            "美国站不强制 GPSR 字段；但经 FBA/NARF 销往欧盟的商品仍须提供 EU 责任人",
            "儿童产品须 CPSIA 追溯标签与测试报告",
            "警示信息英文即可（美国站执法语言）",
        ],
        "enforcement": "Listing 移除 + 销售权限暂停；CPSC 可强制召回并处罚",
        "rules": [
            "GPSR 仅在欧盟境内执法，美国站 listing 不填 GPSR 字段不算违规",
            "从美国仓直发欧盟（如 NARF/远程销售）的商品落入 GPSR 管辖，须有 EU RP 与当地语言警示",
            "美国站安全合规按 CPSC/FCC/UL 等类目规则执行，与 GPSR 是两套体系",
        ],
        "block_header": {
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_ebay() -> Dict:
    """eBay（ebay.de / eBay EU 商业卖家）。"""
    return {
        "policy_name": "GPSR-Anforderungen für gewerbliche Anbieter (eBay Help)",
        "policy_url": "https://www.ebay.de/help/home",
        "authority": "EU Member State Market Surveillance Authorities（各成员国市场监管机构）",
        "native_language": "de",
        "listing_field": "Angebotsbeschreibung / Produktsicherheitsangaben",
        "rep_requirements": [
            "商业卖家（gewerbliche Anbieter）listing 须含制造商名称+地址与产品标识",
            "欧盟境外制造商须有 EU 责任人，信息须为可读文本（非图片）",
            "私人卖家（二手个人物品）豁免 GPSR 大部分义务",
        ],
        "enforcement": "Listing 隐藏/下架 + 账户功能限制；成员国监管可处罚",
        "rules": [
            "2024-12-13 起 eBay 欧盟站点的商业卖家须提供 GPSR 信息，新上架先执行、存量分批覆盖",
            "de/eu 各站点警示语按站点语言（eBay.de 德语强制）",
            "不合规 listing 可能被过滤隐藏且不另行通知，需定期自查",
        ],
        "block_header": {
            "de": "PRODUKTSICHERHEITSINFORMATION (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
            "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
        },
        "rep_label": {
            "de": "Wirtschaftsteilnehmer in der EU (Verantwortliche Person)",
            "en": "Responsible Economic Operator (EU)",
            "fr": "Personne responsable dans l'UE",
        },
    }


def _rules_zalando() -> Dict:
    """Zalando（EU 15 国站点，时尚/家居为主）。"""
    return {
        "policy_name": "Product Safety & Compliance (Zalando Partner Programme / zDirect)",
        "policy_url": "https://partner.zalando.com/",
        "authority": "EU Member State Market Surveillance Authorities（各成员国市场监管机构）",
        "native_language": "de",
        "listing_field": "zDirect 产品数据模型 / 安全属性字段",
        "rep_requirements": [
            "非欧盟卖家须提供 EU 责任人并写入产品数据模型",
            "合规文件（DoC、测试报告）经 zDirect 提交与更新",
            "产品标识（EAN/型号/批次）须与实物一致",
        ],
        "enforcement": "产品下架 + 合作伙伴绩效影响；监管机构可处罚",
        "rules": [
            "Zalando 15 国站点警示语按销售国语言（de/fr/it/es/nl/pl/sv 等）",
            "GPSR 安全属性已并入产品数据模型，缺字段直接无法上架",
            "时尚品类涉及纺织品安全（REACH/化学限用）与 GPSR 双重要求",
        ],
        "block_header": {
            "de": "PRODUKTSICHERHEITSINFORMATION (GPSR 2023/988)",
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
            "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
            "it": "INFORMAZIONI DI SICUREZZA DEL PRODOTTO (GPSR 2023/988)",
            "es": "INFORMACIÓN DE SEGURIDAD DEL PRODUCTO (GPSR 2023/988)",
            "nl": "PRODUCTVEILIGHEIDSINFORMATIE (GPSR 2023/988)",
        },
        "rep_label": {
            "de": "Wirtschaftsteilnehmer in der EU (Verantwortliche Person)",
            "en": "Responsible Economic Operator (EU)",
            "fr": "Personne responsable dans l'UE",
        },
    }


def _rules_fruugo() -> Dict:
    """Fruugo（全球性 marketplace，30+ 国，非欧盟卖家占比高）。"""
    return {
        "policy_name": "Fruugo Seller Terms & Product Safety (GPSR)",
        "policy_url": "https://fruugo.com/",
        "authority": "EU Member State Market Surveillance Authorities（销售国监管机构）",
        "native_language": "en",
        "listing_field": "产品 feed 安全属性 / Safety information 字段",
        "rep_requirements": [
            "非欧盟卖家必须提供 EU 责任人，信息写入产品 feed",
            "产品标识（型号/批次）须与包装一致",
            "feed 安全属性缺失会被拒绝上架",
        ],
        "enforcement": "Feed 拒绝/停售 + 店铺暂停；监管机构可处罚",
        "rules": [
            "Fruugo 销售覆盖 30+ 国，警示语按 Fruugo 翻译矩阵本地化（含小语种市场）",
            "非欧盟卖家占比高，EU RP 是 feed 审核的常见拒绝原因",
            "GPSR 2024-12 起新增安全属性，存量 feed 需补字段后重新提交",
        ],
        "block_header": {
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
            "de": "PRODUKTSICHERHEITSINFORMATION (GPSR 2023/988)",
            "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
            "es": "INFORMACIÓN DE SEGURIDAD DEL PRODUCTO (GPSR 2023/988)",
            "it": "INFORMAZIONI DI SICUREZZA DEL PRODOTTO (GPSR 2023/988)",
            "nl": "PRODUCTVEILIGHEIDSINFORMATIE (GPSR 2023/988)",
        },
        "rep_label": {
            "en": "Responsible Economic Operator (EU)",
            "de": "Wirtschaftsteilnehmer in der EU (Verantwortliche Person)",
            "fr": "Personne responsable dans l'UE",
        },
    }


def _rules_walmart() -> Dict:
    """Walmart Marketplace（美国站）— GPSR 不直接适用。"""
    return {
        "policy_name": "Product Safety & Compliance (Walmart Marketplace)",
        "policy_url": "https://marketplace.walmart.com/",
        "authority": "CPSC（美国消费品安全委员会）",
        "native_language": "en",
        "listing_field": "description / Safety information 字段",
        "rep_requirements": [
            "美国站不强制 GPSR 字段；向欧盟销售的跨境卖家须另行安排 EU 责任人",
            "儿童产品须 CPSIA 追溯标签；警示信息英文",
        ],
        "enforcement": "Listing 移除 + 账户暂停；CPSC 可强制召回",
        "rules": [
            "Walmart Marketplace 主要为美国站，GPSR 仅约束欧盟境内销售",
            "美国站安全合规按 CPSC/FDA/FCC 等类目规则执行",
            "如经第三方物流销往欧盟，商品落入 GPSR 管辖，须满足 EU RP 与当地语言警示",
        ],
        "block_header": {
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
        },
        "rep_label": {
            "en": "Responsible Economic Operator (EU)",
        },
    }


def _rules_tiktok() -> Dict:
    """TikTok Shop EU（DE/FR/IT/ES/IE），短视频/直播带货场景。"""
    return {
        "policy_name": "Product Compliance & GPSR (TikTok Shop Seller Center)",
        "policy_url": "https://seller.tiktokglobalshop.com/",
        "authority": "EU Member State Market Surveillance Authorities（各成员国市场监管机构）",
        "native_language": "en",
        "listing_field": "Product Compliance 字段 / listing 安全信息",
        "rep_requirements": [
            "跨境卖家须提供 EU 责任人并写入 listing 合规字段",
            "产品标识（型号/批次）须与实物一致",
            "警示语按站点当地语言（de/fr/it/es）",
        ],
        "enforcement": "Listing 下架 + 流量限制 + 店铺分处罚；监管机构可处罚",
        "rules": [
            "2024-12-13 起 TikTok Shop EU 要求 listing 提供 GPSR 信息，不合规逐步下架",
            "短视频与直播带货场景同样须展示安全信息（不只 listing 页面）",
            "跨境店铺是重点执法对象，无 EU RP 的商品会被限流或下架",
        ],
        "block_header": {
            "en": "PRODUCT SAFETY INFORMATION (GPSR 2023/988)",
            "de": "PRODUKTSICHERHEITSINFORMATION (GPSR 2023/988)",
            "fr": "INFORMATIONS DE SÉCURITÉ DU PRODUIT (GPSR 2023/988)",
            "it": "INFORMAZIONI DI SICUREZZA DEL PRODOTTO (GPSR 2023/988)",
            "es": "INFORMACIÓN DE SEGURIDAD DEL PRODUCTO (GPSR 2023/988)",
        },
        "rep_label": {
            "en": "Responsible Economic Operator (EU)",
            "de": "Wirtschaftsteilnehmer in der EU (Verantwortliche Person)",
            "fr": "Personne responsable dans l'UE",
        },
    }


def _rules_generic() -> Dict:
    """未知平台兜底（英文基础）。"""
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
    "amazon": _rules_amazon,
    "amazon_us": _rules_amazon_us,
    "ebay": _rules_ebay,
    "zalando": _rules_zalando,
    "fruugo": _rules_fruugo,
    "walmart": _rules_walmart,
    "tiktok": _rules_tiktok,
    "allegro": _rules_allegro,
    "emag": _rules_emag,
    "cdiscount": _rules_cdiscount,
    "otto": _rules_otto,
    "kaufland": _rules_kaufland,
    "bol": _rules_bol,
}


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
                            eu_rep: Optional[Dict] = None) -> Dict:
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
    rep_name = rep.get("company_name", "[欧代公司名称]")
    rep_addr = rep.get("address", "[欧代地址]")
    rep_mail = rep.get("email", "[联系邮箱]")

    lines: List[str] = []
    shown_langs: List[str] = []
    for lang in ordered[:5]:  # 最多 5 段，防超 listing 字段长度
        header = rules["block_header"].get(lang) or rules["block_header"]["en"]
        label = rules["rep_label"].get(lang) or rules["rep_label"]["en"]
        lines.append(f"[{lang.upper()}] {header}")
        lines.append(f"  {label}: {rep_name}, {rep_addr}, {rep_mail}")
        lines.append(f"  Product: {product_name} | Model/Batch: [型号/批次]")
        # 警示语：优先该语言，其次 en；均无则不输出空 bullet
        warn_written = False
        for rule in categories:
            w = rule["warnings"].get(lang) or rule["warnings"].get("en")
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
    """已建平台原生规则的平台列表（覆盖 registry 全部 13 平台）。"""
    return list(_RULE_BUILDERS.keys())
