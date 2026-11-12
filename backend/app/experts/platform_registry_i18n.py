"""
PLATFORM_I18N — /rules 速查 SPA 的数据层本地化（en/de/fr）。

数据源纪律：
- 本模块只做「展示文案翻译」，不改 PLATFORMS 注册表任何字段。
- display / notes 与 PLATFORMS[key] 的 zh 条目一一对应（条数、顺序一致）。
- 数值（title_max / bullets / search_terms_max / description_max）、国家代码、
  语言代码、EAN/GTIN/ASIN/GPSR/CE 等专名一律保留原值，不翻译。
- localize_platform(key, lang) 在 lang 缺失或无该语言条目时回退 zh 注册表原值。
"""

from .platform_registry import PLATFORMS

PLATFORM_I18N: dict = {
    # ===== Amazon 欧洲站 =====
    "amazon": {
        "en": {
            "display": "Amazon EU + US",
            "notes": [
                "First 3 words of the title should carry the core keyword; titles on the German site must be in German",
                "Bullet points: pain point → feature → scenario → quality → after-sales",
                "Backend search terms (generic keywords) must not repeat keywords already in the title; competitor brand names are banned",
            ],
        },
        "de": {
            "display": "Amazon EU + US",
            "notes": [
                "Die ersten 3 Wörter des Titels sollten das Kernkeyword enthalten; Titel auf dem deutschen Marktplatz müssen auf Deutsch sein",
                "Bulletpoints: Schmerzpunkt → Funktion → Anwendungsbereich → Qualität → After-Sales",
                "Backend-Suchbegriffe (generic keywords) dürfen bereits im Titel genannte Keywords nicht wiederholen; Markennamen von Wettbewerbern sind verboten",
            ],
        },
        "fr": {
            "display": "Amazon UE + États-Unis",
            "notes": [
                "Les 3 premiers mots du titre doivent porter le mot-clé principal ; les titres du site allemand doivent être en allemand",
                "Puces : point douloureux → fonction → scénario → qualité → service après-vente",
                "Les mots-clés de recherche backend (generic keywords) ne doivent pas répéter les mots-clés déjà présents dans le titre ; les noms de marques concurrentes sont interdits",
            ],
        },
    },
    # ===== Amazon 美国站 =====
    # ===== eBay =====
    "ebay": {
        "en": {
            "display": "eBay",
            "notes": [
                "The 80-character title limit is a hard cap; front-load the keywords",
                "The description supports HTML; required Item Specifics (brand / MPN / compatibility) must be filled separately in the structured fields",
            ],
        },
        "de": {
            "display": "eBay",
            "notes": [
                "Das Titel-Limit von 80 Zeichen ist eine harte Obergrenze; Keywords gehören nach vorn",
                "Die Beschreibung unterstützt HTML; Pflicht-Item-Specifics (Marke / Modell / Kompatibilität) sind separat in den strukturierten Feldern zu pflegen",
            ],
        },
        "fr": {
            "display": "eBay",
            "notes": [
                "La limite de 80 caractères du titre est un plafond dur ; placez les mots-clés en tête",
                "La description prend en charge le HTML ; les Item Specifics obligatoires (marque / modèle / compatibilité) doivent être saisis séparément dans les champs structurés",
            ],
        },
    },
    # ===== Fruugo（泛欧） =====
    "fruugo": {
        "en": {
            "display": "Fruugo (pan-EU)",
            "notes": [
                "Submit the primary catalog in English; Fruugo auto-translates into each local language",
                "Attributes (color / size / material) must be filled in structured fields, otherwise translation and distribution fail",
            ],
        },
        "de": {
            "display": "Fruugo (paneuropäisch)",
            "notes": [
                "Den Primärkatalog auf Englisch einreichen; Fruugo übersetzt automatisch in die jeweilige Landessprache",
                "Attribute (Farbe / Größe / Material) müssen strukturiert gepflegt werden, sonst scheitern Übersetzung und Distribution",
            ],
        },
        "fr": {
            "display": "Fruugo (paneuropéen)",
            "notes": [
                "Soumettez le catalogue principal en anglais ; Fruugo le traduit automatiquement dans chaque langue locale",
                "Les attributs (couleur / taille / matière) doivent être renseignés de manière structurée, sinon la traduction et la distribution échouent",
            ],
        },
    },
    # ===== Walmart =====
    "walmart": {
        "en": {
            "display": "Walmart",
            "notes": [
                "Title format: brand + model + product name + key attributes; promotional words and special characters are banned",
                "Key Features must be exactly 3-10 bullets (we generate a uniform 5)",
            ],
        },
        "de": {
            "display": "Walmart",
            "notes": [
                "Titelformat: Marke + Modell + Produktname + Schlüsselattribute; Werbewörter und Sonderzeichen sind verboten",
                "Key Features müssen exakt 3–10 Bulletpoints umfassen (wir generieren einheitlich 5)",
            ],
        },
        "fr": {
            "display": "Walmart",
            "notes": [
                "Format du titre : marque + modèle + nom du produit + attributs clés ; les mots promotionnels et caractères spéciaux sont interdits",
                "Les Key Features doivent comporter exactement 3 à 10 puces (nous en générons uniformément 5)",
            ],
        },
    },
    # ===== Cdiscount =====
    "cdiscount": {
        "en": {
            "display": "Cdiscount",
            "notes": [
                "The listing must be entirely in French; no English mixed in",
                "The description must include a technical specification table; French buyers value warranty and return terms",
            ],
        },
        "de": {
            "display": "Cdiscount",
            "notes": [
                "Das Listing muss komplett auf Französisch sein; keine englischen Beimischungen",
                "Die Beschreibung muss eine technische Parametertabelle enthalten; französische Käufer legen Wert auf Garantie- und Rückgabebedingungen",
            ],
        },
        "fr": {
            "display": "Cdiscount",
            "notes": [
                "Le listing doit être intégralement en français ; aucun mélange avec l'anglais",
                "La description doit comporter un tableau de caractéristiques techniques ; les acheteurs français privilégient la garantie et les conditions de retour",
            ],
        },
    },
    # ===== Otto =====
    "otto": {
        "en": {
            "display": "Otto",
            "notes": [
                "Pure German listing; grammar and spelling bar is high (German buyers are sensitive to this)",
                "Otto enforces strict quality on material and craftsmanship descriptions; avoid absolute claims",
            ],
        },
        "de": {
            "display": "Otto",
            "notes": [
                "Rein deutsches Listing; hohe Anforderungen an Grammatik und Rechtschreibung (deutsche Käufer reagieren empfindlich)",
                "Otto stellt strenge Anforderungen an Qualitäts- und Materialbeschreibungen; Werbe-Absolutformeln sind zu vermeiden",
            ],
        },
        "fr": {
            "display": "Otto",
            "notes": [
                "Listing rédigé intégralement en allemand ; exigences élevées sur la grammaire et l'orthographe (les acheteurs allemands y sont sensibles)",
                "Otto impose des exigences strictes sur les descriptions de qualité et de matière ; évitez les allégations absolues",
            ],
        },
    },
    # ===== Allegro =====
    "allegro": {
        "en": {
            "display": "Allegro",
            "notes": [
                "Polish listing; the 75-character title limit is a hard cap",
                "The description supports HTML; Polish buyers care about delivery speed and Allegro Smart eligibility",
            ],
        },
        "de": {
            "display": "Allegro",
            "notes": [
                "Polnisches Listing; das Titel-Limit von 75 Zeichen ist eine harte Obergrenze",
                "Die Beschreibung unterstützt HTML; polnische Käufer legen Wert auf Liefergeschwindigkeit und Allegro-Smart-Tauglichkeit",
            ],
        },
        "fr": {
            "display": "Allegro",
            "notes": [
                "Listing en polonais ; la limite de 75 caractères du titre est un plafond dur",
                "La description prend en charge le HTML ; les acheteurs polonais privilégient la rapidité de livraison et l'éligibilité Allegro Smart",
            ],
        },
    },
    # ===== eMAG =====
    "emag": {
        "en": {
            "display": "eMAG",
            "notes": [
                "Romanian listing",
                "Category-specific structured fields (product family / brand / model) are mandatory, otherwise review is rejected",
            ],
        },
        "de": {
            "display": "eMAG",
            "notes": [
                "Rumänisches Listing",
                "Kategoriespezifische strukturierte Pflichtfelder (Produktfamilie / Marke / Modell) sind erforderlich, sonst wird die Prüfung abgelehnt",
            ],
        },
        "fr": {
            "display": "eMAG",
            "notes": [
                "Listing en roumain",
                "Les champs structurés obligatoires propres à la catégorie (famille de produits / marque / modèle) doivent être renseignés, sinon l'évaluation est refusée",
            ],
        },
    },
    # ===== Kaufland Global =====
    "kaufland": {
        "en": {
            "display": "Kaufland Global",
            "notes": [
                "German listing (mainly the DE region); spelling and grammar bar is on par with Otto",
                "Manufacturer information must match the GPSR EU representative / manufacturer",
                "The EAN is the primary product key; without it, the offer cannot be created",
            ],
        },
        "de": {
            "display": "Kaufland Global",
            "notes": [
                "Deutsches Listing (Schwerpunkt DE); Anforderungen an Rechtschreibung und Grammatik auf Otto-Niveau",
                "Die Herstellerangaben müssen mit dem GPSR-EU-Verantwortlichen / Hersteller übereinstimmen",
                "Die EAN ist der Primärschlüssel des Produkts; ohne sie lässt sich kein Angebot anlegen",
            ],
        },
        "fr": {
            "display": "Kaufland Global",
            "notes": [
                "Listing en allemand (principalement la zone DE) ; exigences orthographe et grammaire équivalentes à Otto",
                "Les informations fabricant doivent correspondre au représentant UE / fabricant requis par le GPSR",
                "L'EAN est la clé primaire du produit ; à défaut, l'offre ne peut pas être créée",
            ],
        },
    },
    # ===== bol.com =====
    "bol": {
        "en": {
            "display": "bol.com",
            "notes": [
                "Dutch listing (NL/BE); the EAN is the unique product key — without it, no offer can be created",
                "Dutch buyers care about the Delivery Promise and bol's distribution-service rating",
            ],
        },
        "de": {
            "display": "bol.com",
            "notes": [
                "Niederländisches Listing (NL/BE); die EAN ist der eindeutige Produkt-Schlüssel — ohne sie ist kein Offer anlegbar",
                "Niederländische Käufer legen Wert auf das Delivery Promise und die Bewertung des bol-Vertriebsservice",
            ],
        },
        "fr": {
            "display": "bol.com",
            "notes": [
                "Listing en néerlandais (NL/BE) ; l'EAN est la clé unique du produit — à défaut, aucune offre ne peut être créée",
                "Les acheteurs néerlandais privilégient le Delivery Promise et la note du service de distribution bol",
            ],
        },
    },
    # ===== Zalando =====
    "zalando": {
        "en": {
            "display": "Zalando",
            "notes": [
                "Fashion categories only (apparel / footwear / bags / accessories / beauty); must pass Zalando Partner brand onboarding (zDirect)",
                "EAN/GTIN is the unique product key; without it, creation fails. Size grid and material composition are mandatory — missing them means outright rejection",
                "Submit the primary catalog in English; Zalando localizes per site automatically. German shoppers are highly sensitive to material and wash instructions",
                "Textile categories require GPSR plus fibre-composition labeling (EU 1007/2011); missing an EU representative or local-language warnings gets the listing delisted",
            ],
        },
        "de": {
            "display": "Zalando",
            "notes": [
                "Nur Fashion-Kategorien (Bekleidung / Schuhe / Taschen / Accessoires / Beauty); muss das Zalando-Partner-Brand-Onboarding (zDirect) bestehen",
                "EAN/GTIN ist der eindeutige Produkt-Schlüssel; ohne sie ist keine Anlage möglich. Size-Grid und Materialzusammensetzung sind Pflicht — Fehlende bedeutet direkte Ablehnung",
                "Den Primärkatalog auf Englisch einreichen; Zalando lokalisiert automatisch je Marktplatz. Deutsche Käufer reagieren extrem empfindlich auf Material- und Pflegehinweise",
                "Textilkategorien verlangen GPSR plus Faserkennzeichnung (EU 1007/2011); fehlender EU-Verantwortlicher oder Warnhinweise in Landessprache führen zum De-Listing",
            ],
        },
        "fr": {
            "display": "Zalando",
            "notes": [
                "Catégories mode uniquement (vêtements / chaussures / sacs / accessoires / beauté) ; passage obligé par l'onboarding marque Zalando Partner (zDirect)",
                "L'EAN/GTIN est la clé unique du produit ; à défaut, la création échoue. La grille des tailles (size grid) et la composition matière sont obligatoires — à défaut, refus pur et simple",
                "Soumettez le catalogue principal en anglais ; Zalando localise automatiquement par site. Les acheteurs allemands sont extrêmement sensibles à la matière et aux instructions d'entretien",
                "Les catégories textiles imposent le GPSR plus l'étiquetage de composition des fibres (UE 1007/2011) ; un représentant UE ou des avertissements en langue locale manquants entraînent le retrait de l'offre",
            ],
        },
    },
    # ===== TikTok Shop =====
    "tiktok": {
        "en": {
            "display": "TikTok Shop",
            "notes": [
                "Titles may carry emoji; the first 20 characters must grab attention (feed scenario). The description should lean into short-video product-seeding moments and in-the-moment usage",
                "EU sites (ES/IT/DE/FR) enforce GPSR/CE compliance the same way; missing an EU representative or local-language warnings gets the listing delisted",
                "Compliance red lines: no exaggerated medical/beauty efficacy claims (cure / healing / weight-loss effects), no absolute wording; certified categories require uploaded qualifications",
                "The search-terms field is for product keywords and hashtags (#); it must not repeat the title",
            ],
        },
        "de": {
            "display": "TikTok Shop",
            "notes": [
                "Titel dürfen Emoji enthalten; die ersten 20 Zeichen müssen im Feed aufmerksam machen. Die Beschreibung setzt auf Short-Video-Product-Seeding-Momente und Nutzungssituationen",
                "EU-Marktplätze (ES/IT/DE/FR) erzwingen GPSR-/CE-Compliance gleichermaßen; fehlender EU-Verantwortlicher oder Warnhinweise in Landessprache führen zum De-Listing",
                "Compliance-Rotlinie: keine überzogenen Wirkungsversprechen bei Medizin-/Kosmetik (Heilung / Wunder / Abnehm-Effekte), keine Absolutformeln; zertifizierungspflichtige Kategorien benötigen hochgeladene Qualifikationsnachweise",
                "Das Suchbegriff-Feld dient Produkt-Keywords und Hashtags (#) und wiederholt den Titel nicht",
            ],
        },
        "fr": {
            "display": "TikTok Shop",
            "notes": [
                "Les titres peuvent comporter des emoji ; les 20 premiers caractères doivent accrocher (scénario du feed). La description privilégie les moments de product-seeding en vidéo courte et l'usage sur le vif",
                "Les sites UE (ES/IT/DE/FR) imposent également la conformité GPSR/CE ; un représentant UE ou des avertissements en langue locale manquants entraînent le retrait de l'offre",
                "Lignes rouges de conformité : aucune allégation d'efficacité médicale/cosmétique exagérée (guérison / effet miracle / amincissement), aucun terme absolu ; les catégories certifiées exigent le dépôt de qualifications",
                "Le champ mots-clés sert aux mots-clés produit et aux hashtags (#) ; il ne répète pas le titre",
            ],
        },
    },
}


def localize_platform(key: str, lang: str) -> dict:
    """返回 {"display": str, "notes": [str, ...]}。

    - lang 为空 / "zh" / 不在 PLATFORM_I18N[key] 中 → 回退 zh 注册表原值。
    - 其余字段（countries/language/title_max/...）不在此处，由路由层保留原字段。
    """
    cfg = PLATFORMS.get(key)
    if cfg is None:
        raise KeyError(f"未知平台: {key}")
    entry = (PLATFORM_I18N.get(key) or {}).get(lang or "")
    if entry:
        return {
            "display": entry.get("display") or cfg["display"],
            "notes": list(entry.get("notes") or cfg["notes"]),
        }
    return {"display": cfg["display"], "notes": list(cfg["notes"])}
