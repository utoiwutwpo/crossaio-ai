# -*- coding: utf-8 -*-
"""社区示例讨论种子 — 按跨境平台分子类别播种 27 帖 + 回复。

与 content_seed._ensure_content 同一套幂等策略：用户按邮箱去重，帖子按标题去重，
回复按 (thread_id, body) 去重。可重复执行。
2026-11-12：追加 5 帖，取材 2026 EU 执法新闻周期（DE/FR 联合标记 2000+ ASIN、
ProdSG 罚则、页面即证据、Safety Gate 公开通报、变体重上架风险）。
"""
from datetime import datetime, timedelta

from .auth import hash_password
from .database import User
from .community_models import CommunityThread, CommunityReply

# 4 位卖家人设（与 /img/avatar-*.png、播客人物故事视频一致）
PEOPLE = [
    {"email": "lena.k@community.crossaio.com", "name": "Lena K. — Berlin", "country": "🇩🇪"},
    {"email": "thomas.r@community.crossaio.com", "name": "Thomas R. — Paris", "country": "🇫🇷"},
    {"email": "agnieszka.w@community.crossaio.com", "name": "Agnieszka W. — Warsaw", "country": "🇵🇱"},
    {"email": "javier.m@community.crossaio.com", "name": "Javier M. — Madrid", "country": "🇪🇸"},
]
LENA, THOMAS, AGNIESZKA, JAVIER = 0, 1, 2, 3

# (author, category, days_ago, title, body, tags, pinned, replies)
THREADS = [
    (LENA, "general", 12,
     "New here — with ~€50k/year, which platform should a home & living brand start with?",
     "We make small kitchen storage items, mostly bamboo. Currently selling on our own Shopify store only. "
     "The question is where to expand first: Amazon, Kaufland, Otto, or Allegro? "
     "I care about total cost of entry (compliance, returns, warehouse) more than raw traffic.",
     "strategy,beginners,home-living", 1,
     [(THOMAS, "Start with Amazon.de if your product fits their restricted categories list — demand is there, "
               "and the fee structure is the most predictable of the German ones. Avoid Otto for now: category "
               "approval took me three weeks and I am not sure it pays back at our volume."),
      (AGNIESZKA, "Do not skip Allegro just because it is Polish. Transport and returns cost me less there than in "
                  "Germany, and the buyers convert well for home goods. But prepare the Polish listing copy properly — "
                  "machine translation is obvious to them.")]),

    (LENA, "amazon", 9,
     "Amazon.de rejected my listing: \"safety documentation missing\" — what actually satisfied them?",
     "Electric toothbrush, newly launched. The listing was suppressed twice. Support told me to upload "
     "a test report but would not say which standard. After two weeks I have a file with the manufacturer, "
     "EU responsible person and test report, and the listing finally went live. "
     "What is the minimal set that worked for you, and how long did it take?",
     "gpsr,electric-toothbrush,amazon-de", 0,
     [(THOMAS, "The standard that matters for a powered personal-care device is EN 60335 plus the EMC part. "
               "Attach the EU declaration of conformity, not just the lab report — support asked for the "
               "declaration twice before accepting the report."),
      (AGNIESZKA, "Two weeks is normal the first time. Build the technical file once and it applies to every "
                  "marketplace afterwards. Keep it in one folder per SKU, that is the whole trick.")]),

    (THOMAS, "amazon", 7,
     "Amazon.fr: our safety test report expired and the listing got suppressed — do we really need a new test?",
     "Our cosmetics brand on Amazon.fr lost visibility because the safety report in the file expired. "
     "Re-testing costs about €900 per product. Is there a cheaper path — for example a manufacturer "
     "declaration covering several products?",
     "gpsr,cosmetics,amazon-fr", 0,
     [(LENA, "If several products share the same design and risk profile, ask the lab explicitly whether one "
             "report can cover the family. Ours covered three SKUs — written confirmation in the report, not a "
             "verbal promise on the phone."),
      (JAVIER, "Also ask for the updated report to state the model range. That single line is what Amazon and "
               "Kaufland both accepted from us last time.")]),

    (AGNIESZKA, "kaufland", 8,
     "Kaufland.de asks for GPSR fields one by one — is there a checklist that passes on the first try?",
     "Each time I fix one missing field, another appears. Currently missing: manufacturer address, "
     "EU responsible person email, test report number, warning language. "
     "Before I go through this a sixth time, is there a field set that passes first submission?",
     "gpsr,kaufland,checklist", 0,
     [(LENA, "Yes — upload the technical file as one PDF with a table of contents, plus the EU declaration of "
             "conformity. Single upload instead of field-by-field, and it passed in one go for us."),
      (JAVIER, "Also put the responsible person phone number in the contact field. That one was requested twice "
               "even though it was in the file.")]),

    (JAVIER, "kaufland", 5,
     "Selling the same product on Amazon and Kaufland — how do you handle returns without losing margin?",
     "Same SKU on both. The customer buys on Amazon and returns to Kaufland sometimes, and the logistics partner "
     "charges per parcel either way. Is the standard to run separate stock per marketplace?",
     "logistics,returns,kaufland", 0,
     [(AGNIESZKA, "Separate stock is the clean answer but it doubles your cash tied up. We ran shared stock for a "
                  "year and the cost was worse than the duplication."),
      (LENA, "Look at your return rate per marketplace first. For our category Amazon returns were 6% and Kaufland "
             "3% — the problem was the fixed logistics cost, not the returns.")]),

    (LENA, "otto", 11,
     "Otto.de category approval for home goods took three weeks — was it worth the wait?",
     "They asked for a supplier audit-style document set. The approval finally came, but the traffic during those "
     "three weeks was zero and I had to keep the listing live elsewhere. "
     "For those of you approved: is it worth it as a second channel?",
     "otto,approval,home-living", 0,
     [(THOMAS, "For fashion-adjacent home goods it can be, but only if you already have the German market fit. "
               "I would not start there — start on Amazon or Kaufland and add Otto second.")]),

    (THOMAS, "zalando", 6,
     "Zalando Partner: price parity enforcement removed my margin — how are you handling it?",
     "Zalando requires prices to match my own store and the other partners. That kills the intro discount I use "
     "on my webshop, and then the marketplace fees leave me at 14% margin. "
     "Is anyone still growing through Zalando Partner in 2026?",
     "zalando,margin,pricing", 0,
     [(JAVIER, "We stopped using it as a volume channel and treat it as a brand-presence channel only. "
               "Everything that needs margin goes through our own store."),
      (LENA, "Price parity plus marketplace fees is a structural squeeze. I set the floor price on the own store "
             "first and let the marketplace match it, rather than the other way round.")]),

    (THOMAS, "ebay", 4,
     "eBay EU with IOSS vs OSS on a Pan-EU store — which registration for which sales?",
     "We ship from Germany to DE, FR, NL and IT directly from our own warehouse. IOSS covers up to €150 consignments "
     "from the store, OSS for the rest. What do you file where, and does it actually matter for a €20 product?",
     "ebay,ioss,oss,vat", 0,
     [(AGNIESZKA, "It matters more than people think. With OSS you charge VAT at checkout and then remit in each "
                  "country separately. IOSS is only for distance sales of goods up to €150, so it is the default "
                  "for us."),
      (JAVIER, "Use one EU store with IOSS for small consignments. If your average basket is below €150 you "
               "almost never need OSS.")]),

    (JAVIER, "ebay", 10,
     "Post-Black Friday return wave on eBay.de — restocking fee charged on items that were never restocked",
     "Refurbished electronics, so every returned unit needs inspection. eBay charged a restocking fee on units "
     "where the buyer simply did not send anything back. Has anyone successfully contested that?",
     "ebay,returns,electronics", 0,
     [(LENA, "Raise it through the seller protection flow and attach the tracking showing no return shipment. "
             "It is usually refunded when the unit is not received back within the window.")]),

    (AGNIESZKA, "cdiscount", 14,
     "Cdiscount.fr fee structure in 2026 — is it still viable for small sellers?",
     "Looking at Cdiscount for the French market instead of relying on Amazon alone. The commission plus fulfilment "
     "fees look heavy for a small catalogue. What is your real take after a year on it?",
     "cdiscount,fees,france", 0,
     [(THOMAS, "Viable if you have ≥100 SKUs and use their fulfilment. Below that the fees eat the contribution. "
               "We still prefer Amazon.fr for the catalogue and Cdiscount for clearance stock.")]),

    (AGNIESZKA, "allegro", 5,
     "Allegro: how good does the Polish listing translation have to be?",
     "Our German supplier gave me machine-translated Polish copy and I was told to rewrite it. How much does a "
     "native edit matter for conversion, and who do you use?",
     "allegro,translation,localization", 0,
     [(JAVIER, "It matters. Rewrite the title and the first two bullets by hand — that is where the conversion "
               "difference shows. Machine translation in the description body is tolerable."),
      (LENA, "We had a native speaker rewrite only the top 20 SKUs and the sales difference was clearly visible "
             "on those, not on the rest.")]),

    (JAVIER, "bol-com", 8,
     "bol.com requires the product information in Dutch inside the listing — how do you structure it?",
     "Dutch copy for the whole catalogue is a lot of work. Do you translate everything, or is there a template "
     "that satisfies their checks?",
     "bol-com,localization,netherlands", 0,
     [(AGNIESZKA, "Their checks are mostly structured fields: use, material, dimensions, warranty. You can generate "
                  "those from your ERP data. Only the description really needs human translation.")]),

    (THOMAS, "aliexpress", 13,
     "Selling on AliExpress EU: EU responsible person plus IOSS — is the volume worth the setup?",
     "Considering AliExpress for the long tail of our catalogue. Setup involves the EU responsible person, "
     "IOSS and local returns. Does anyone run this as a meaningful channel, or is it mainly for low-priced items?",
     "aliexpress,compliance,ioss", 0,
     [(AGNIESZKA, "Long tail only, and only if your unit economics survive their fee stack plus EU returns. "
                  "We treat it as clearance, not growth.")]),

    (AGNIESZKA, "temu", 3,
     "Temu seller hub changed the fee model — anyone else seeing margins move?",
     "The settlement report changed three weeks ago and our effective commission went up by roughly two points. "
     "No notification email, as far as I can see. Has anyone seen an official explanation?",
     "temu,fees,margin", 0,
     [(JAVIER, "Same here. Check whether the change is on the fulfilment side rather than the commission — "
               "ours moved from seller-fulfilled to a mixed model."),
      (LENA, "I asked support and got a generic answer. I am shifting the volume to own-store instead of "
             "accepting an unexplained change.")]),

    (JAVIER, "shein", 16,
     "SHEIN marketplace onboarding for EU brands — how long did it take in your case?",
     "We produce apparel accessories and got an invitation to sell on SHEIN. The onboarding asks for a lot of "
     "compliance material. How long does it realistically take?",
     "shein,onboarding,apparel", 0,
     [(LENA, "Six weeks for us, most of it waiting on the lab documents. Start the technical file before you "
             "apply, not after.")]),

    (LENA, "shopify", 6,
     "One catalogue, Amazon plus our own Shopify store — do we need one VAT registration or two?",
     "Legal entity sells on both channels, shipped from our own warehouse in Germany. IOSS covers the EU sales, "
     "Amazon handles its own. Is a single OSS registration enough for both, or do I need a separate one for "
     "the webshop?",
     "shopify,vat,oss", 0,
     [(AGNIESZKA, "One registration can cover all your EU distance sales if you are the same legal entity. "
                  "Marketplace sales through a deemed supplier are their responsibility, not yours.")]),

    (JAVIER, "own-store", 4,
     "Selling on marketplaces and our own shop — how do you avoid channel conflict on price?",
     "Amazon customers found our webshop via a price comparison site and complained that our own price was higher "
     "than the marketplace price. How do you keep one price story across channels?",
     "own-store,pricing,channels", 0,
     [(THOMAS, "Set the marketplace price as the anchor and give the webshop a permanent benefit that is not price: "
               "bundle, warranty, faster delivery. Otherwise you are in a race you cannot win."),
      (LENA, "We also enable the comparison site only for the marketplaces we want price parity on.")]),

    (THOMAS, "compliance", 9,
     "GPSR technical file checklist — what did your lab actually ask for?",
     "Collecting the requirements from three labs now and the checklists differ. Is there a single document set "
     "that satisfies EU market surveillance, Amazon, Kaufland and the labs at the same time?",
     "gpsr,technical-file,checklist", 0,
     [(AGNIESZKA, "Our lab gave us the list: risk assessment, test report, EU declaration of conformity, "
                  "manufacturer address, responsible person details, and the warnings in the local language. "
                  "That set passed everywhere else too."),
      (LENA, "Add a product-specific label mock-up. Two of my listings were rejected only because the label image "
             "was missing the responsible person address.")]),

    (AGNIESZKA, "pricing", 7,
     "Pricing across 13 marketplaces with different fees — how do you keep one formula?",
     "Every platform has its own commission, fulfilment and VAT treatment. Currently a spreadsheet, and it is "
     "already wrong in two places. Is there a smarter way to maintain it?",
     "pricing,fees,multi-marketplace", 0,
     [(LENA, "Keep one margin target and derive the selling price per channel from the channel cost, not the "
             "other way round. We recompute from the platform cost table monthly."),
      (THOMAS, "Never let a marketplace be the source of truth for your price. You will end up chasing their "
               "suggestions instead of your margin.")]),

    (JAVIER, "logistics", 5,
     "Pan-EU FBA versus our own warehouse in Poland — where is the break-even volume?",
     "Two models: store everything in Pan-EU FBA, or ship from our own Polish warehouse with a 24h dispatch "
     "promise. The FBA fees are high per unit but the delivery promise is better. At what monthly volume does "
     "one become clearly better?",
     "logistics,fba,warehouse", 0,
     [(AGNIESZKA, "Around 300 units a month per marketplace the own-warehouse model wins on cost, below that "
                  "FBA's per-unit fee is hard to beat.")]),

    (AGNIESZKA, "localization", 12,
     "Five-language listing: human edit or machine translation with a native pass? What did conversion do?",
     "We translated the top 40 listings into five languages. Full human translation was expensive; machine "
     "plus one native review was cheaper. Conversion changed, but I cannot isolate how much came from the "
     "translation and how much from the season.",
     "localization,translation,conversion", 0,
     [(THOMAS, "The title and the first three bullets decide most of it. Fully human for the top 20 SKUs, machine "
               "plus review for the long tail. That is where our cost per conversion dropped most."),
      (JAVIER, "Run the test on one language pair for a month before rolling it out. The seasonal effect you "
               "mention makes small samples very hard to read.")]),

    (LENA, "ebay", 2,
     "eBay EU: VAT number in the item specifics — does the marketplace validate it live?",
     "Our VAT ID was rejected twice for a formatting issue. Small question, but it cost us two days of listings.",
     "ebay,vat,listing", 0,
     [(AGNIESZKA, "It validates against VIES. Remove spaces, use the country prefix without dots, and it works.")]),

    # ---- 2026-11-12: five threads from the current EU enforcement news cycle ----
    # Sources: joint DE/FR market-surveillance sweep flagged 2,000+ ASINs for missing
    # Responsible Person data (June 2026), Amazon final-notice emails with 14-day
    # deadlines; German ProdSG revision in force 2026-02-19 with 32 administrative
    # offences (up to EUR 100k each) and GPSR Art. 45 up to 4% of global turnover;
    # authorities now audit the live listing page itself ("page as evidence");
    # EU Safety Gate notifications are public and permanent; relisting a suspended
    # ASIN via a variant risks account-level enforcement.

    (THOMAS, "compliance", 1,
     "2026 enforcement wave: DE and FR authorities flagged 2,000+ ASINs in June — did anyone get the final-notice email?",
     "Reports are everywhere now: a joint German-French sweep flagged over two thousand ASINs for missing "
     "Responsible Person data, and Amazon is sending final-notice compliance emails with 14-day deadlines "
     "before permanent removal. The transition period is clearly over. "
     "Who here actually received one of these notices, and what did the resolution path look like?",
     "gpsr,2026-enforcement,amazon-de", 1,
     [(LENA, "We got one for a SKU in June. What worked: submit the missing RP details straight through the "
             "Regulatory Compliance Portal with the declaration attached. Do not open a dispute first — "
             "sellers who argued spent weeks longer than sellers who just filed the documents."),
      (JAVIER, "Also important: do not relist the flagged ASIN under a variant while the case is open. "
               "That pattern reportedly moves the enforcement from the listing to the account level. "
               "Fourteen days is enough time to fix the file if the RP appointment already exists.")]),

    (AGNIESZKA, "compliance", 2,
     "ProdSG update in force since 19 February: fines up to €100k per violation — has anyone been fined in practice?",
     "The revised German ProdSG took effect in February: 32 administrative offences, each carrying up to "
     "€100,000, and GPSR Article 45 allows up to 4% of global annual turnover for serious cases. "
     "These numbers used to be theoretical — with authorities now doing proactive sweeps, has anyone here "
     "actually received a fine or an official request from a Marktüberwachungsbehörde?",
     "gpsr,prodsg,germany,2026-enforcement", 0,
     [(THOMAS, "No fine yet in our circle, but we have seen a Safety Gate notification for a competitor in "
               "kitchen electronics. The notification is public and permanent — the reputational hit was "
               "worse than any fine would have been."),
      (LENA, "The part people underestimate: enforcement no longer waits for a sample shipment. The live "
             "listing page itself is the evidence now — manufacturer details, product identifier, batch "
             "traceability, warnings in the destination language. Each missing item counts as its own "
             "violation, and they can check all of it from a desk.")]),

    (LENA, "amazon", 1,
     "Amazon now audits the listing page itself — 'page as evidence' enforcement, who else noticed?",
     "Market surveillance in DE and FR now pulls listing pages directly and checks them as compliance "
     "evidence: is the manufacturer named, is there a traceable product identifier, are the safety "
     "warnings in the language of the market, is the responsible person data there? No physical sampling "
     "needed. We cleaned up our warnings text and a months-old suppression lifted within days. "
     "Has anyone else seen a page-level fix resolve a listing-level block?",
     "gpsr,listings,2026-enforcement", 0,
     [(JAVIER, "Yes — same experience. Our FR listing had English-only warnings for months without issue, "
               "then got suppressed within a week of the June sweep. Rewriting the warnings in French was "
               "the only change we made, and it came back."),
      (AGNIESZKA, "This is why the warning texts need to be maintained per market, not stored once in a "
                  "document somewhere. If the text is not on the page, it does not exist for the auditor.")]),

    (JAVIER, "general", 2,
     "EU Safety Gate notifications are public and permanent — does anyone monitor their category?",
     "Learned this the hard way via a competitor: every withdrawal and recall under the Safety Gate rapid "
     "alert system is publicly searchable and stays up. For a small brand that notification can rank on "
     "your own brand name. Do you monitor the Safety Gate for your category, and what do you do when a "
     "competitor gets flagged?",
     "safety-gate,compliance,strategy", 0,
     [(THOMAS, "We check it monthly with a calendar reminder, filtered to our product categories. "
               "It doubles as free market intelligence — the flagged products tell you exactly which "
               "documentation gaps the authorities are hunting for right now."),
      (LENA, "Honestly, a competitor's notification is an opportunity. If they got flagged for missing "
             "responsible person data and you have yours in order, that is the moment to be visibly "
             "compliant on the same keywords.")]),

    (THOMAS, "amazon", 3,
     "Relisting a suspended ASIN via a variant — has anyone tried it and lived to tell?",
     "Our agency suggested dodging a GPSR suspension by creating a new child ASIN under the same parent. "
     "Everything I read says Amazon's compliance system links variants and that repeated evasion moves "
     "enforcement from the listing to the seller account. Before I argue with them: does anyone have a "
     "first-hand account of how that played out?",
     "gpsr,suspension,amazon,2026-enforcement", 0,
     [(AGNIESZKA, "Do not. We watched a neighbouring seller do exactly that twice; first suspension was "
                  "listing-level, the account review that followed was not. The appeal became ten times "
                  "harder than the original fix would have been."),
      (JAVIER, "The system is built to receive documents, not negotiate. Filing the missing compliance "
               "data through the portal took us two days; the account-level aftermath of an evasion "
               "attempt took someone we know most of a quarter.")]),
]


# ============================================================
# 播种执行（幂等）
# ============================================================
def ensure_community_threads() -> None:
    """创建演示人设用户 + 按平台分类的示例讨论与回复。可重复执行。"""
    import secrets

    from .database import SessionLocal

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # --- 演示人设用户 ---
        users = {}
        for p in PEOPLE:
            u = db.query(User).filter(User.email == p["email"]).first()
            if u is None:
                u = User(email=p["email"], full_name=p["name"], company_name="",
                         password_hash=hash_password(secrets.token_urlsafe(24)), plan="free")
                db.add(u)
                db.flush()
            users[p["email"]] = u

        # --- 帖子 + 回复 ---
        existing = {t for (t,) in db.query(CommunityThread.title).all()}
        for author, category, days, title, body, tags, pinned, replies in THREADS:
            if title in existing:
                continue
            u = users[PEOPLE[author]["email"]]
            created = now - timedelta(days=days)
            t = CommunityThread(
                user_id=u.id, author_name=u.full_name, category=category, language="en",
                title=title, body=body, tags=tags, is_pinned=bool(pinned),
                reply_count=len(replies), created_at=created, updated_at=created,
            )
            db.add(t)
            db.flush()
            for r_author, r_body in replies:
                ru = users[PEOPLE[r_author]["email"]]
                db.add(CommunityReply(
                    thread_id=t.id, user_id=ru.id, author_name=ru.full_name,
                    body=r_body, created_at=now - timedelta(days=max(days - 1, 0)),
                ))
        db.commit()
    finally:
        db.close()
