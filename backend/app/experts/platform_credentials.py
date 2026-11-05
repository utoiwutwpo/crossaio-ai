"""13 平台商家自助接入注册表 — 每个平台的凭证字段、官方申请入口与门槛说明。

设计原则（诚实营销）：
- 只列该平台真实存在的凭证字段与官方申请 URL，不编造"一键接入"。
- 门槛（是否需要开发者审核、是否免费、卖家账号要求）如实标注。
- eBay 用户级走 OAuth（eBayConnection），不在粘贴流程内。
"""
from typing import Dict, List

# 每字段：(key, 中文名, 是否敏感(显示为密码框), 帮助文案)
_C = List[tuple]

PLATFORM_CRED_REGISTRY: Dict[str, dict] = {
    "amazon": {
        "label": "Amazon 欧洲站",
        "apply_url": "https://sellercentral.amazon.de/sw/user/central-developer",
        "apply_note": "Seller Central → 集成 → 开发者，注册 LWA 应用；专业卖家账户可申请，部分权限需 Amazon 审核（1~3 天）。",
        "fields": [
            ("client_id", "LWA Client ID", False, "开发者档案页 Client ID"),
            ("client_secret", "LWA Client Secret", True, "与 Client ID 同页"),
            ("refresh_token", "卖家 Refresh Token", True, "授权卖家档案后换取，长期有效"),
        ],
        "unlocks": "合规块真实写回 Amazon Listing（回填 dry_run=False）",
    },
    "amazon_us": {
        "label": "Amazon 美国站",
        "apply_url": "https://sellercentral.amazon.com/sw/user/central-developer",
        "apply_note": "同欧洲站流程；美国站需在 developer profile 选择北美市场。",
        "fields": [
            ("client_id", "LWA Client ID", False, "开发者档案页 Client ID"),
            ("client_secret", "LWA Client Secret", True, "与 Client ID 同页"),
            ("refresh_token", "卖家 Refresh Token", True, "授权后长期有效"),
        ],
        "unlocks": "美国站合规块写回 + Listing 回填",
    },
    "ebay": {
        "label": "eBay",
        "apply_url": "https://developer.ebay.com/signin",
        "apply_note": "eBay 无需商家自己申请开发者账号：平台运营方配置应用后，卖家点「去授权」完成 OAuth 即可（token 加密封存）。",
        "fields": [],  # OAuth 流程，不走粘贴表单
        "oauth": True,
        "unlocks": "买家消息实时同步 + AI 回复直发",
    },
    "allegro": {
        "label": "Allegro（波兰）",
        "apply_url": "https://developer.allegro.pl/",
        "apply_note": "developer.allegro.pl 免费注册应用即得 Client ID/Secret（测试环境 instant，正式环境自动审批）。",
        "fields": [
            ("client_id", "Client ID", False, "Allegro 应用列表页"),
            ("client_secret", "Client Secret", True, "与 Client ID 同页"),
        ],
        "unlocks": "波兰语买家消息自动导入 + 合规回复",
    },
    "otto": {
        "label": "Otto（德国）",
        "apply_url": "https://developer.otto.market/",
        "apply_note": "OTTO Marketplace 卖家可在 developer.otto.market 申请 API 访问，需卖家账号已激活。",
        "fields": [
            ("client_id", "Client ID", False, "OTTO 开发者后台"),
            ("client_secret", "Client Secret", True, "开发者后台"),
        ],
        "unlocks": "德语买家消息自动导入 + 合规回复",
    },
    "kaufland": {
        "label": "Kaufland（德/中东欧）",
        "apply_url": "https://seller.kaufland.de/",
        "apply_note": "门槛最低之一：Kaufland Seller Portal → 设置 → API 直接生成 Client-Key / Secret-Key，无需另行审核。",
        "fields": [
            ("client_key", "Client Key", False, "Seller Portal → API 设置"),
            ("secret_key", "Secret Key", True, "与 Client Key 同页生成"),
        ],
        "unlocks": "多国买家消息自动导入 + 合规回复",
    },
    "cdiscount": {
        "label": "Cdiscount（法国）",
        "apply_url": "https://dev.cdiscount.com/",
        "apply_note": "dev.cdiscount.com 注册后需绑定 Cdiscount 卖家账户，SOAP API 凭证由运营方邮件发放。",
        "fields": [
            ("api_key", "API Key", False, "Cdiscount 开发者邮件"),
            ("seller_login", "卖家登录名", False, "Cdiscount 后台账号"),
        ],
        "unlocks": "法语买家消息自动导入 + 合规回复",
    },
    "emag": {
        "label": "eMAG（罗马尼亚）",
        "apply_url": "https://marketplace.emag.eu/",
        "apply_note": "eMAG Marketplace 卖家后台 → 设置 → API 访问，生成后即时可用。",
        "fields": [
            ("api_key", "API Token", True, "eMAG 卖家后台 API 页"),
        ],
        "unlocks": "罗马尼亚语买家消息自动导入 + 合规回复",
    },
    "zalando": {
        "label": "Zalando（欧洲时尚）",
        "apply_url": "https://partners.zalando.de/",
        "apply_note": "Zalando Partner Program（zDirect）会员可申请 API 客户端，审核较严。",
        "fields": [
            ("client_id", "Client ID", False, "zDirect 后台"),
            ("client_secret", "Client Secret", True, "zDirect 后台"),
        ],
        "unlocks": "多语言买家消息自动导入 + 合规回复",
    },
    "bol": {
        "label": "bol.com（荷/比）",
        "apply_url": "https://developer.bol.com/",
        "apply_note": "developer.bol.com 用卖家账号登录创建 API 凭证（Client ID + Secret），即时生效。",
        "fields": [
            ("client_id", "Client ID", False, "bol 开发者后台"),
            ("client_secret", "Client Secret", True, "开发者后台"),
        ],
        "unlocks": "荷兰语买家消息自动导入 + 合规回复",
    },
    "walmart": {
        "label": "Walmart（美国）",
        "apply_url": "https://developer.walmart.com/",
        "apply_note": "Walmart Seller Center → 设置 → API Key 生成（卖家即时可得）。",
        "fields": [
            ("client_id", "Client ID", False, "Seller Center → API Key"),
            ("client_secret", "Client Secret", True, "同页生成"),
        ],
        "unlocks": "英语买家消息自动导入 + 合规回复",
    },
    "fruugo": {
        "label": "Fruugo（泛欧）",
        "apply_url": "https://merchant.fruugo.com/",
        "apply_note": "Fruugo Merchant Portal → 账户 → API，生成 Merchant ID + API Key。",
        "fields": [
            ("merchant_id", "Merchant ID", False, "Merchant Portal"),
            ("api_key", "API Key", True, "Merchant Portal"),
        ],
        "unlocks": "多语言买家消息自动导入 + 合规回复",
    },
    "tiktok": {
        "label": "TikTok Shop",
        "apply_url": "https://partner.tiktokshop.com/",
        "apply_note": "TikTok Shop Partner Center → 开发者 → 创建应用（个人卖家可用自用型应用）。",
        "fields": [
            ("app_key", "App Key", False, "Partner Center"),
            ("app_secret", "App Secret", True, "Partner Center"),
        ],
        "unlocks": "英语买家消息自动导入 + 合规回复",
    },
}

# 粘贴流程统一走这些 key 的平台（eBay 走 OAuth 除外）
PASTE_PLATFORMS = [p for p, cfg in PLATFORM_CRED_REGISTRY.items()
                   if not cfg.get("oauth")]


# ---------------------------------------------------------------------------
# 多语言包（en / de / fr）— 与 PLATFORM_CRED_REGISTRY 同 key 同字段顺序。
# 每平台: {label, apply_note, unlocks, fields: [(label, hint), ...]}
# fields 顺序必须与注册表 fields 一致（不含 key/secret 标记，直接按位置对齐）。
# ---------------------------------------------------------------------------
PLATFORM_CRED_I18N: Dict[str, Dict[str, dict]] = {
    "en": {
        "amazon": {
            "label": "Amazon Europe",
            "apply_note": "Seller Central → Integration → Developer, register an LWA application; available to Professional seller accounts, some permissions require Amazon review (1–3 days).",
            "fields": [("LWA Client ID", "Client ID on the developer profile page"),
                       ("LWA Client Secret", "Same page as the Client ID"),
                       ("Seller Refresh Token", "Obtained after authorising the seller profile; long-lived")],
            "unlocks": "Write GPSR compliance blocks back to real Amazon Listings (backfill dry_run=False)",
        },
        "amazon_us": {
            "label": "Amazon US",
            "apply_note": "Same process as Europe; for the US marketplace select North America in your developer profile.",
            "fields": [("LWA Client ID", "Client ID on the developer profile page"),
                       ("LWA Client Secret", "Same page as the Client ID"),
                       ("Seller Refresh Token", "Long-lived once authorised")],
            "unlocks": "Compliance block write-back for the US marketplace + Listing backfill",
        },
        "ebay": {
            "label": "eBay",
            "apply_note": "No seller-side developer account needed: once the platform operator configures the app, the seller just clicks \"Authorise\" to complete OAuth (token stored encrypted).",
            "fields": [],
            "unlocks": "Real-time buyer message sync + direct AI reply sending",
        },
        "allegro": {
            "label": "Allegro (Poland)",
            "apply_note": "Register an app for free at developer.allegro.pl and you get a Client ID/Secret instantly (sandbox instant; production auto-approved).",
            "fields": [("Client ID", "Allegro app list page"),
                       ("Client Secret", "Same page as the Client ID")],
            "unlocks": "Polish buyer message auto-import + compliant replies",
        },
        "otto": {
            "label": "Otto (Germany)",
            "apply_note": "OTTO Marketplace sellers can apply for API access at developer.otto.market; requires an activated seller account.",
            "fields": [("Client ID", "OTTO developer backend"),
                       ("Client Secret", "Developer backend")],
            "unlocks": "German buyer message auto-import + compliant replies",
        },
        "kaufland": {
            "label": "Kaufland (Germany / CEE)",
            "apply_note": "One of the lowest barriers: Kaufland Seller Portal → Settings → API generates a Client-Key / Secret-Key directly, no extra review.",
            "fields": [("Client Key", "Seller Portal → API settings"),
                       ("Secret Key", "Generated on the same page as the Client Key")],
            "unlocks": "Multi-country buyer message auto-import + compliant replies",
        },
        "cdiscount": {
            "label": "Cdiscount (France)",
            "apply_note": "Register at dev.cdiscount.com and link a Cdiscount seller account; SOAP API credentials are sent by e-mail from the operator.",
            "fields": [("API Key", "Cdiscount developer e-mail"),
                       ("Seller login", "Cdiscount backend account")],
            "unlocks": "French buyer message auto-import + compliant replies",
        },
        "emag": {
            "label": "eMAG (Romania)",
            "apply_note": "eMAG Marketplace seller backend → Settings → API access; usable immediately after generating.",
            "fields": [("API Token", "eMAG seller backend API page")],
            "unlocks": "Romanian buyer message auto-import + compliant replies",
        },
        "zalando": {
            "label": "Zalando (European fashion)",
            "apply_note": "Zalando Partner Program (zDirect) members can apply for an API client; review is stricter.",
            "fields": [("Client ID", "zDirect backend"),
                       ("Client Secret", "zDirect backend")],
            "unlocks": "Multilingual buyer message auto-import + compliant replies",
        },
        "bol": {
            "label": "bol.com (Netherlands / Belgium)",
            "apply_note": "Log in at developer.bol.com with your seller account and create API credentials (Client ID + Secret); effective immediately.",
            "fields": [("Client ID", "bol developer backend"),
                       ("Client Secret", "Developer backend")],
            "unlocks": "Dutch buyer message auto-import + compliant replies",
        },
        "walmart": {
            "label": "Walmart (US)",
            "apply_note": "Walmart Seller Center → Settings → generate API Key (available to sellers instantly).",
            "fields": [("Client ID", "Seller Center → API Key"),
                       ("Client Secret", "Generated on the same page")],
            "unlocks": "English buyer message auto-import + compliant replies",
        },
        "fruugo": {
            "label": "Fruugo (pan-European)",
            "apply_note": "Fruugo Merchant Portal → Account → API, generate a Merchant ID + API Key.",
            "fields": [("Merchant ID", "Merchant Portal"),
                       ("API Key", "Merchant Portal")],
            "unlocks": "Multilingual buyer message auto-import + compliant replies",
        },
        "tiktok": {
            "label": "TikTok Shop",
            "apply_note": "TikTok Shop Partner Center → Developer → create an app (individual sellers can use a self-use app).",
            "fields": [("App Key", "Partner Center"),
                       ("App Secret", "Partner Center")],
            "unlocks": "English buyer message auto-import + compliant replies",
        },
    },
    "de": {
        "amazon": {
            "label": "Amazon Europa",
            "apply_note": "Seller Central → Integrationen → Entwickler, LWA-Anwendung registrieren; für Professional-Verkäuferkonten verfügbar, einzelne Berechtigungen erfordern eine Amazon-Prüfung (1–3 Tage).",
            "fields": [("LWA Client ID", "Client ID auf der Entwickler-Profilseite"),
                       ("LWA Client Secret", "Gleiche Seite wie die Client ID"),
                       ("Refresh Token des Verkäufers", "Nach Freigabe des Verkäuferprofils eingetauscht, langfristig gültig")],
            "unlocks": "Compliance-Blöcke in echte Amazon-Listings zurückschreiben (Backfill dry_run=False)",
        },
        "amazon_us": {
            "label": "Amazon USA",
            "apply_note": "Wie beim europäischen Prozess; für den US-Marktplatz im Entwicklerprofil Nordamerika wählen.",
            "fields": [("LWA Client ID", "Client ID auf der Entwickler-Profilseite"),
                       ("LWA Client Secret", "Gleiche Seite wie die Client ID"),
                       ("Refresh Token des Verkäufers", "Nach Autorisierung langfristig gültig")],
            "unlocks": "Compliance-Block-Rückschreiben für den US-Marktplatz + Listing-Backfill",
        },
        "ebay": {
            "label": "eBay",
            "apply_note": "Kein eigenes Entwicklerkonto nötig: Nachdem der Betreiber die App konfiguriert hat, klickt der Verkäufer nur auf „Autorisieren“, um die OAuth-Freigabe abzuschließen (Token verschlüsselt gespeichert).",
            "fields": [],
            "unlocks": "Echtzeit-Sync der Käufernachrichten + direkter Versand von KI-Antworten",
        },
        "allegro": {
            "label": "Allegro (Polen)",
            "apply_note": "Auf developer.allegro.pl kostenlos eine Anwendung registrieren — Client ID/Secret gibt es sofort (Sandbox sofort, Produktion automatisch freigegeben).",
            "fields": [("Client ID", "Anwendungsliste bei Allegro"),
                       ("Client Secret", "Gleiche Seite wie die Client ID")],
            "unlocks": "Automatischer Import polnischer Käufernachrichten + konforme Antworten",
        },
        "otto": {
            "label": "Otto (Deutschland)",
            "apply_note": "OTTO-Marketplace-Verkäufer können unter developer.otto.market API-Zugang beantragen; ein aktiviertes Verkäuferkonto ist erforderlich.",
            "fields": [("Client ID", "OTTO-Entwicklerbackend"),
                       ("Client Secret", "Entwicklerbackend")],
            "unlocks": "Automatischer Import deutscher Käufernachrichten + konforme Antworten",
        },
        "kaufland": {
            "label": "Kaufland (Deutschland / Osteuropa)",
            "apply_note": "Eine der niedrigsten Hürden: Kaufland Seller Portal → Einstellungen → API erzeugt Client-Key / Secret-Key direkt, ohne weitere Prüfung.",
            "fields": [("Client Key", "Seller Portal → API-Einstellungen"),
                       ("Secret Key", "Auf derselben Seite wie der Client Key erzeugt")],
            "unlocks": "Automatischer Import von Käufernachrichten aus mehreren Ländern + konforme Antworten",
        },
        "cdiscount": {
            "label": "Cdiscount (Frankreich)",
            "apply_note": "Auf dev.cdiscount.com registrieren und ein Cdiscount-Verkäuferkonto verknüpfen; die SOAP-API-Zugangsdaten verschickt der Betreiber per E-Mail.",
            "fields": [("API Key", "Cdiscount-Entwickler-E-Mail"),
                       ("Verkäufer-Login", "Cdiscount-Backend-Konto")],
            "unlocks": "Automatischer Import französischer Käufernachrichten + konforme Antworten",
        },
        "emag": {
            "label": "eMAG (Rumänien)",
            "apply_note": "eMAG-Marketplace-Verkäuferbackend → Einstellungen → API-Zugang; nach dem Erzeugen sofort nutzbar.",
            "fields": [("API Token", "API-Seite im eMAG-Verkäuferbackend")],
            "unlocks": "Automatischer Import rumänischer Käufernachrichten + konforme Antworten",
        },
        "zalando": {
            "label": "Zalando (europäische Mode)",
            "apply_note": "Mitglieder des Zalando Partner Program (zDirect) können einen API-Client beantragen; die Prüfung ist strenger.",
            "fields": [("Client ID", "zDirect-Backend"),
                       ("Client Secret", "zDirect-Backend")],
            "unlocks": "Automatischer Import mehrsprachiger Käufernachrichten + konforme Antworten",
        },
        "bol": {
            "label": "bol.com (Niederlande / Belgien)",
            "apply_note": "Auf developer.bol.com mit dem Verkäuferkonto anmelden und API-Zugangsdaten erstellen (Client ID + Secret), sofort wirksam.",
            "fields": [("Client ID", "bol-Entwicklerbackend"),
                       ("Client Secret", "Entwicklerbackend")],
            "unlocks": "Automatischer Import niederländischer Käufernachrichten + konforme Antworten",
        },
        "walmart": {
            "label": "Walmart (USA)",
            "apply_note": "Walmart Seller Center → Einstellungen → API-Key erzeugen (für Verkäufer sofort verfügbar).",
            "fields": [("Client ID", "Seller Center → API-Key"),
                       ("Client Secret", "Auf derselben Seite erzeugt")],
            "unlocks": "Automatischer Import englischer Käufernachrichten + konforme Antworten",
        },
        "fruugo": {
            "label": "Fruugo (paneuropäisch)",
            "apply_note": "Fruugo Merchant Portal → Konto → API, Merchant ID + API-Key erzeugen.",
            "fields": [("Merchant ID", "Merchant Portal"),
                       ("API Key", "Merchant Portal")],
            "unlocks": "Automatischer Import mehrsprachiger Käufernachrichten + konforme Antworten",
        },
        "tiktok": {
            "label": "TikTok Shop",
            "apply_note": "TikTok Shop Partner Center → Entwickler → Anwendung erstellen (Einzelverkäufer können eine Selbstnutzungs-App verwenden).",
            "fields": [("App Key", "Partner Center"),
                       ("App Secret", "Partner Center")],
            "unlocks": "Automatischer Import englischer Käufernachrichten + konforme Antworten",
        },
    },
    "fr": {
        "amazon": {
            "label": "Amazon Europe",
            "apply_note": "Seller Central → Intégration → Développeur, enregistrez une application LWA ; réservé aux comptes vendeurs Professionnels, certaines autorisations exigent une validation Amazon (1 à 3 jours).",
            "fields": [("LWA Client ID", "Client ID sur la page du profil développeur"),
                       ("LWA Client Secret", "Même page que le Client ID"),
                       ("Refresh Token vendeur", "Obtenu après autorisation du profil vendeur ; valide longtemps")],
            "unlocks": "Écriture réelle des blocs de conformité sur les listings Amazon (backfill dry_run=False)",
        },
        "amazon_us": {
            "label": "Amazon États-Unis",
            "apply_note": "Même procédure que l'Europe ; pour la place de marché US, sélectionnez l'Amérique du Nord dans le profil développeur.",
            "fields": [("LWA Client ID", "Client ID sur la page du profil développeur"),
                       ("LWA Client Secret", "Même page que le Client ID"),
                       ("Refresh Token vendeur", "Valide longtemps après autorisation")],
            "unlocks": "Écriture des blocs de conformité sur la place de marché US + backfill des listings",
        },
        "ebay": {
            "label": "eBay",
            "apply_note": "Aucun compte développeur côté vendeur : une fois l'application configurée par l'opérateur de la plateforme, le vendeur clique simplement sur « Autoriser » pour finaliser l'OAuth (jeton stocké chiffré).",
            "fields": [],
            "unlocks": "Synchronisation en temps réel des messages acheteurs + envoi direct des réponses IA",
        },
        "allegro": {
            "label": "Allegro (Pologne)",
            "apply_note": "Inscrivez gratuitement une application sur developer.allegro.pl et obtenez immédiatement un Client ID/Secret (sandbox instantané, production validée automatiquement).",
            "fields": [("Client ID", "Page de la liste des applications Allegro"),
                       ("Client Secret", "Même page que le Client ID")],
            "unlocks": "Import automatique des messages acheteurs en polonais + réponses conformes",
        },
        "otto": {
            "label": "Otto (Allemagne)",
            "apply_note": "Les vendeurs OTTO Marketplace peuvent demander un accès API sur developer.otto.market ; un compte vendeur activé est requis.",
            "fields": [("Client ID", "Back-end développeur OTTO"),
                       ("Client Secret", "Back-end développeur")],
            "unlocks": "Import automatique des messages acheteurs en allemand + réponses conformes",
        },
        "kaufland": {
            "label": "Kaufland (Allemagne / Europe centrale)",
            "apply_note": "L'une des barrières les plus basses : Kaufland Seller Portal → Paramètres → API génère directement un Client-Key / Secret-Key, sans validation supplémentaire.",
            "fields": [("Client Key", "Seller Portal → Paramètres API"),
                       ("Secret Key", "Généré sur la même page que le Client Key")],
            "unlocks": "Import automatique des messages acheteurs multi-pays + réponses conformes",
        },
        "cdiscount": {
            "label": "Cdiscount (France)",
            "apply_note": "Inscrivez-vous sur dev.cdiscount.com et liez un compte vendeur Cdiscount ; les identifiants SOAP API sont envoyés par e-mail par l'opérateur.",
            "fields": [("API Key", "E-mail développeur Cdiscount"),
                       ("Identifiant vendeur", "Compte back-end Cdiscount")],
            "unlocks": "Import automatique des messages acheteurs en français + réponses conformes",
        },
        "emag": {
            "label": "eMAG (Roumanie)",
            "apply_note": "Back-end vendeur eMAG Marketplace → Paramètres → accès API ; utilisable immédiatement après génération.",
            "fields": [("API Token", "Page API du back-end vendeur eMAG")],
            "unlocks": "Import automatique des messages acheteurs en roumain + réponses conformes",
        },
        "zalando": {
            "label": "Zalando (mode européenne)",
            "apply_note": "Les membres du Zalando Partner Program (zDirect) peuvent demander un client API ; la validation est plus stricte.",
            "fields": [("Client ID", "Back-end zDirect"),
                       ("Client Secret", "Back-end zDirect")],
            "unlocks": "Import automatique des messages acheteurs multilingues + réponses conformes",
        },
        "bol": {
            "label": "bol.com (Pays-Bas / Belgique)",
            "apply_note": "Connectez-vous sur developer.bol.com avec votre compte vendeur et créez les identifiants API (Client ID + Secret), effectifs immédiatement.",
            "fields": [("Client ID", "Back-end développeur bol"),
                       ("Client Secret", "Back-end développeur")],
            "unlocks": "Import automatique des messages acheteurs en néerlandais + réponses conformes",
        },
        "walmart": {
            "label": "Walmart (États-Unis)",
            "apply_note": "Walmart Seller Center → Paramètres → génération de la clé API (disponible immédiatement pour les vendeurs).",
            "fields": [("Client ID", "Seller Center → clé API"),
                       ("Client Secret", "Généré sur la même page")],
            "unlocks": "Import automatique des messages acheteurs en anglais + réponses conformes",
        },
        "fruugo": {
            "label": "Fruugo (pan-européen)",
            "apply_note": "Fruugo Merchant Portal → Compte → API, générez un Merchant ID + une clé API.",
            "fields": [("Merchant ID", "Merchant Portal"),
                       ("API Key", "Merchant Portal")],
            "unlocks": "Import automatique des messages acheteurs multilingues + réponses conformes",
        },
        "tiktok": {
            "label": "TikTok Shop",
            "apply_note": "TikTok Shop Partner Center → Développeur → créer une application (les vendeurs individuels peuvent utiliser une application à usage personnel).",
            "fields": [("App Key", "Partner Center"),
                       ("App Secret", "Partner Center")],
            "unlocks": "Import automatique des messages acheteurs en anglais + réponses conformes",
        },
    },
}


def _tr(platform: str, lang: str) -> dict | None:
    """取指定语言的平台文案包（zh 之外的语言缺省回退中文）。"""
    if lang in ("zh", "", None):
        return None
    return PLATFORM_CRED_I18N.get(lang, {}).get(platform)


def cred_guide(platform: str, lang: str = "zh") -> dict | None:
    """对外暴露的接入指南（不含任何密钥值）。lang 支持 zh/en/de/fr。"""
    cfg = PLATFORM_CRED_REGISTRY.get(platform)
    if not cfg:
        return None
    tr = _tr(platform, lang)
    label = (tr or cfg)["label"] if tr else cfg["label"]
    apply_note = tr["apply_note"] if tr else cfg["apply_note"]
    unlocks = tr["unlocks"] if tr else cfg["unlocks"]
    fields = cfg["fields"]
    if tr:
        fields = [(k, tr["fields"][i][0], s, tr["fields"][i][1])
                  for i, (k, _l, s, _h) in enumerate(fields)]
    return {
        "label": label,
        "oauth": cfg.get("oauth", False),
        "apply_url": cfg["apply_url"],
        "apply_note": apply_note,
        "fields": [{"key": k, "label": l, "secret": s, "hint": h}
                   for k, l, s, h in fields],
        "unlocks": unlocks,
    }
