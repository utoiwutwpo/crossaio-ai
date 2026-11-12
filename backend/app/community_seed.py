# -*- coding: utf-8 -*-
"""社区示例讨论种子 — 按跨境平台分子类别播种 27 帖 + 回复。

与 content_seed._ensure_content 同一套幂等策略：用户按邮箱去重，帖子按标题去重，
回复按 (thread_id, body) 去重。可重复执行。
2026-11-12：追加 5 帖，取材 2026 EU 执法新闻周期（DE/FR 联合标记 2000+ ASIN、
ProdSG 罚则、页面即证据、Safety Gate 公开通报、变体重上架风险）。
2026-11-13（第二批，真实抓取）：X.com 已登录，直接用浏览器抓取真实火爆贴作选题，
给 12 个版块补 12 帖，全部带真实 @handle 文本归因（不嵌第三方 widget，保零脚本 SEO）：
temu(@emelyelevates €200M+10-26 整改、@HouZM001 份额 16%→8%)、aliexpress(@TechieUltimatum €550M)、
ebay(@PummyKin 强制邮资政策)、amazon(@OHN_Infoportal/@Haendlerbund 11-1 €2 处理费)、
shopify(@onep7466 合规 App)、shein(@lolangoiv 10万浏览、@GoodKingV €5/件、@sxh_mnk 转 Vinted)、
logistics(@ANBU_EU 成本叠加)、pricing/compliance/own-store/general/bol-com。
注：X 原文多语种（中/法/西/德），社区贴一律英文转述、零汉字。
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

    # ---- 2026-11-13: equivalent alternative to X.com hot-post mining ----
    # Instead of scraping viral X.com threads (login wall + paid API + third-party
    # JS that breaks the zero-script SEO config), every remaining board is enriched
    # with WebSearch-verified 2026 EU cross-border hot topics. Sources:
    # Kaufland GPSR Seller University (15 May 2026 manufacturer/RP split, CSV report);
    # OTTO EU-seller opening + summer 2026 new categories (ChannelX); Zalando fee
    # consolidation from Sept 2026 + Premium Partner Program; eBay Global Shipping
    # (EUR 3 flat duty from 1 Jul 2026, EUR 2 Union Handling Fee + PID from 1 Nov 2026);
    # bol.com Partnerplatform GPSR/PPWR pages (5 Mar / 1 Apr 2026, 12 Aug 2026);
    # AliExpress EUR 550M DSA fine 20 Jul 2026; Temu EUR 200M DSA fine 28 May 2026 +
    # 26 Oct remediation plan + Sept 2026 deemed-importer customs reform; SHEIN DGCCRF
    # EUR 22.5M Jun 2026 + France stepped eco-fines; Allegro One Fulfillment / Smart!.

    (AGNIESZKA, "kaufland", 2,
     "Kaufland GPSR switch on 15 May: offers without manufacturer AND EU responsible-person data now get excluded — did your bulk edit stick?",
     "Kaufland retired the old safety-contact page on 15 May 2026 and now forces a separate manufacturer "
     "entry and an EU responsible-person entry. Offers missing either are systematically pulled from sale, "
     "and the data shows on the product page in two tabs from that date. I ran the GPSR CSV report, saw "
     "is_compliant=false on about a third of my range with reason manufacturer_contact_missing, and used "
     "the per-manufacturer rule so it applies to future products too. Did the bulk manufacturer-rule trick "
     "actually hold for everyone, or did some of you have to re-upload per item?",
     "kaufland,gpsr,2026-compliance", 0,
     [(LENA, "The per-manufacturer rule held for us, but watch the suggestion box: it offers EU contacts "
             "that other sellers entered, and if you click one that is not actually your responsible person "
             "you inherit someone else's legal details. Verify before you save — the page makes you tick a "
             "box accepting full legal responsibility."),
      (THOMAS, "Same here on the bulk rule. The gotcha was the PDP lag: changes took up to ten minutes to "
               "show in a fresh report, so do not trust the screen, download the CSV again. Also the API "
               "attribute product_safety_contact still works for now if you maintain offers by feed.")]),

    (LENA, "otto", 3,
     "OTTO opening to EU-based sellers in 2026 — anyone in via NL or PL entity, and are the supplements/solar categories actually live?",
     "OTTO used to require a German company and German VAT. From 2026 they accept Netherlands and Poland "
     "entities directly, with Austria, France and Spain in pilot, all on EU VAT plus OSS. They also opened "
     "new product groups from summer 2026 — dietary supplements and energy tech like solar panels — and run "
     "a semi-managed path for non-EU sellers via a German VAT number. It is still invite-only and gated on "
     "quality, so I am curious whether anyone here actually got approved through the EU-entity route rather "
     "than a German GmbH.",
     "otto,eu-expansion,2026", 0,
     [(THOMAS, "We got in via a Dutch B.V. with OSS, but the gating is real: they checked last year's "
               "turnover and wanted German-language customer service reachable on business days. The monthly "
               "fee is steep (just under EUR 100), so only worth it if your margin survives it."),
      (JAVIER, "The semi-managed route is the one to watch for non-EU brands: you keep tail fulfilment and "
               "returns, they run the storefront, but they audit your stock for the German warehouse first. "
               "Bring test reports the German market recognises or the invite stalls.")]),

    (JAVIER, "zalando", 4,
     "Zalando standardising fees from September 2026 — is killing Connected Retail and the new flat service fee good or bad for small brands?",
     "Zalando is merging its partner models and switching off Connected Retail on 30 June 2027, with the "
     "same standard marketplace service fee for everyone from September 2026 (a two-point reduction through "
     "end of 2027, plus one more point for early movers). Partners must accept the consolidated structure by "
     "15 May or the relationship is ended in August. On top of that, the Premium Partner Program wants six "
     "months at EUR 250k GMV and a return rate at or below 12.8 percent for commission rebates. For a small "
     "brand, does the flat fee help or just remove the old flexibility?",
     "zalando,fees,2026", 0,
     [(LENA, "The two-point reduction is the only upside I see. The base fee plus ZMS ad spend already pushes "
             "effective cost to 25-40 percent, and a sub-EUR-20 apparel item now triggers a Price Quality "
             "Review asking for an ISO 17025 material test and a REACH statement. That filters out cheap "
             "listing dumps, which is good for brands that actually comply."),
      (THOMAS, "We treat Zalando as brand presence, not volume, for exactly this reason. The 30-day minimum "
               "return window (down from 100) helps the tail, but fashion return rates in Germany are still "
               "over 80 percent of returned parcels — price that in before you celebrate the flat fee.")]),

    (AGNIESZKA, "ebay", 1,
     "eBay EU from 1 Nov: EUR 3 flat customs duty per item PLUS EUR 2 Union Handling Fee — how are you repricing multi-item parcels?",
     "The EU removed the duty-free threshold for sub-EUR-150 parcels from 1 July 2026 (a flat EUR 3 per "
     "item, taxed per tariff category even inside one parcel), and from 1 November added a EUR 2 Union "
     "Handling Fee per distinct item. So a EUR 10 parcel with three different items is EUR 9 duty plus EUR 6 "
     "handling before VAT. eBay also now requires product identifiers for sub-EUR-150 imports: the eBay "
     "listing ID, an MPN, or a GTIN/EAN/UPC. Anyone found a clean way to pass the identifier and absorb the "
     "fee without killing the price?",
     "ebay,customs,2026-fees", 0,
     [(THOMAS, "Two identical pens count as one item, so bundle where you can — the fee is per distinct item, "
               "not per unit. We also moved our IOSS number into every customs declaration so the parcel is "
               "not taxed twice at delivery. Above EUR 150 the buyer pays import VAT on arrival instead."),
      (JAVIER, "For UK sellers the cleaner play is one ebay.co.uk listing with international visibility to "
               "DE/FR/IT/ES and eat the 1.6 percent cross-border surcharge, rather than opening a local "
               "account you then have to service in German. Volume dependent, obviously.")]),

    (THOMAS, "cdiscount", 5,
     "Cdiscount + France PPWR from 12 August: packaging EPR per country or the listing gets blocked — who actually finished registration?",
     "The EU Packaging and Packaging Waste Regulation took effect on 12 August 2026 across all 27 states. "
     "For France that means the Triman recycling label and per-country EPR registration, and platforms are "
     "blocking or de-listing items without valid numbers. Cdiscount was already heavy on fees below 100 SKUs, "
     "and now the packaging paperwork is another gate. Did people register EPR in France and the other "
     "relevant states, or did you just pull the low-margin long tail off Cdiscount?",
     "cdiscount,ppwr,france,2026", 0,
     [(AGNIESZKA, "We registered in DE, FR, IT, ES, NL, BE, IE, PL, SE because that is where we ship. The "
                  "platforms differ on who can deduct: some countries let the marketplace collect, but you "
                  "still must upload a valid registration number or the listing is blocked."),
      (LENA, "The 2030 rules are the real one to plan for — empty space in e-commerce packaging capped at 50 "
             "percent and recycled-content minimums. Design the packaging now, do not wait for the deadline.")]),

    (AGNIESZKA, "allegro", 2,
     "Allegro One Fulfillment in 2026: one Polish warehouse feeding PL/CZ/SK/HU — is the Smart! badge worth chasing for cross-border?",
     "Allegro's One Fulfillment lets you ship to one Polish warehouse and the platform delivers across "
     "Poland, Czechia, Slovakia and Hungary, with fees from about 2.69 to 11.49 PLN per item. The Smart! "
     "loyalty programme has 7M+ subscribers in Poland and 1.3M+ beyond, members spend 4.5x more, and the "
     "Smart! badge can lift sales up to 2.5x. International GMV in CEE roughly doubled year on year. For a "
     "brand entering Central Europe, is chasing the Smart! badge the single best visibility lever, or does "
     "the fulfilment lock-in cost more than it returns?",
     "allegro,one-fulfillment,2026", 0,
     [(JAVIER, "Smart! is the lever. Free delivery and returns is what Polish buyers filter on, and the "
               "badge puts you in that result set. The catch is you must meet delivery and returns quality "
               "first, so do not promise Smart! until your fulfilment is solid."),
      (THOMAS, "One Fulfillment also unlocks the carrier network and parcel-locker reach that Central "
               "European buyers expect. For bulkier home goods it removed our cross-border shipping pain "
               "almost entirely. Watch the per-volume fee on slow movers sitting in storage.")]),

    (JAVIER, "bol-com", 3,
     "bol.com GPSR enforcement started: no manufacturer data = no new listings from 5 March, offline sweep from 1 April — did your catalogue survive?",
     "bol.com began enforcing GPSR hard in 2026: from 5 March no new range goes online without manufacturer "
     "details, and from 1 April existing items missing manufacturer data are taken offline in phases, with "
     "the EU responsible economic operator required too. Then PPWR packaging obligations follow from 12 "
     "August. They also run a 22-week quality score (0-100, minimum 65, account can end at 64 or below) and "
     "Dutch customer service is an admission criterion, not a scored one. Who cleared the manufacturer-data "
     "sweep, and did the EPR packaging registration actually go through?",
     "bol-com,gpsr,2026-compliance", 0,
     [(AGNIESZKA, "We passed because we already held EPR for packaging, WEEE and battery and uploaded the "
                  "numbers before the AI pre-check. The rejection rate for sellers missing EPR was high in "
                  "2025, so do not treat it as a formality."),
      (LENA, "The Dutch customer-service requirement is the one non-EU sellers underestimate. You can be "
             "compliant on product data and still be refused entry because you cannot show Dutch-language "
             "support. French matters too if you sell into French-speaking Belgium.")]),

    (THOMAS, "aliexpress", 2,
     "AliExpress hit with EUR 550M DSA fine in July — does the tighter seller documentation check reach EU cross-border brands too?",
     "The European Commission fined AliExpress EUR 550M under the Digital Services Act on 20 July 2026, the "
     "largest DSA penalty to date, for failing to assess and mitigate risks from illegal and unsafe goods. "
     "Temu took EUR 200M in May on the same logic. The fines land on the platform, but the platforms then "
     "push documentation checks down to sellers: fuller chain verification from producer to EU responsible "
     "person to the live listing page. For those of us using AliExpress as a clearance or long-tail channel, "
     "are you seeing stricter document requests reach your account?",
     "aliexpress,dsa,2026-enforcement", 0,
     [(LENA, "Yes — they now want the whole chain, not one CE certificate. Producer, importer, EU "
             "responsible person and the page itself have to line up, and a document you submitted before "
             "can be requested again. Keep the technical file and the declaration version-controlled."),
      (AGNIESZKA, "Treat it as the same playbook as Amazon and Kaufland: one compliant dossier per SKU, "
                  "reused across every platform. The platforms compare notes indirectly through market "
                  "surveillance, so a gap on one tends to surface on another.")]),

    (JAVIER, "temu", 1,
     "Temu: EUR 200M DSA fine, October remediation plan, and the new 'deemed importer' customs rule — what does it mean for non-EU sellers?",
     "Temu was fined EUR 200M under the DSA on 28 May 2026 (mystery shopping found chargers failing basic "
     "safety tests and baby toys with banned chemicals). From 1 October it tightened test-report recognition "
     "to 14 designated labs with reports under one year, both full and semi-managed. On 26 October the EU "
     "accepted its remediation plan with a four-month window and a mid-term report due February 2027. On top "
     "of that, the September 2026 customs reform makes non-EU platforms the 'deemed importer'. For sellers "
     "using Temu, does the tighter document check plus the new border liability change your calculus?",
     "temu,dsa,customs,2026-enforcement", 0,
     [(THOMAS, "The 14-lab rule is the sharp edge — reports from labs not on the list, even if still valid, "
               "must be redone. Factory-type sellers with stable bills of materials cope; spread-sheet "
               "sellers feel it on every SKU."),
      (AGNIESZKA, "The deemed-importer reform is bigger than the fine. From November 2026 a EUR 2 handling "
                  "fee per item sits on top of the EUR 3 duty on small parcels, and the platform now carries "
                  "the border compliance risk — so it will demand your GPSR papers before listing, not "
                  "after.")]),

    (LENA, "shein", 2,
     "SHEIN: EUR 22.5M French fine in June, stepped eco-fines per item, and mandatory lifespan disclosure — how are apparel sellers reading this?",
     "France's DGCCRF fined two SHEIN entities EUR 22.5M in June 2026 for consumer-protection and "
     "environmental-disclosure breaches, about a year after a EUR 40M fake-discount penalty. The country's "
     "anti-fast-fashion law adds stepped eco-fines of EUR 0.25 to 12 per item in 2026, rising to EUR 20 by "
     "2030 and capped at half the item price, with three quantitative triggers (over 15,000 new styles a "
     "year in the EU, average price under EUR 5, expected lifespan under 30 washes). It also mandates "
     "environmental and lifespan disclosure. For apparel brands, is this a France-only headache or the shape "
     "of EU-wide rules to come?",
     "shein,france,2026-enforcement", 0,
     [(THOMAS, "Read it as the template. The Netherlands raised textile recycling targets, Germany opened a "
               "textile EPR law, and Italy and Spain are watching the French thresholds. The eco-fine "
               "triggers are written so they mostly catch ultra-low-price players, but the disclosure duty "
               "is broadly applicable."),
      (JAVIER, "The practical move is to digitise the environmental and lifespan data now and clean "
               "misleading green claims, because misleading eco wording also draws ad restrictions. Brands "
               "that can show real durability get a comparative edge exactly where the law is pushing.")]),

    (LENA, "shopify", 4,
     "Shopify stores shipping direct to EU: the new 'deemed importer' rule (2026) means YOU owe duties + GPSR docs at the border — who is ready?",
     "The EU's September 2026 customs reform treats non-EU sellers shipping direct to EU customers as the "
     "importer of record: you owe customs the information and duties, must ensure EU-law compliance, and "
     "face penalties of 1 to 6 percent of the prior 12 months' import value for repeat breaches. IOSS and "
     "OSS still apply for the VAT side, but the product-compliance burden (EU responsible person, "
     "declaration, labelling, warnings in the market language) now sits on the store owner at the border, "
     "not just on marketplaces. For own-store operators, did this change your fulfilment or entity setup?",
     "shopify,customs,2026", 0,
     [(AGNIESZKA, "We moved stock into the EU and use OSS for VAT, which keeps the direct-ship border "
                  "question simpler, but the GPSR responsible-person requirement is the part most own-store "
                  "sellers skip. You need a named EU economic operator or the goods are not lawfully on the "
                  "market."),
      (JAVIER, "The penalty is percentage-of-import-value, not a flat fee, so it scales with volume. Small "
               "direct shippers feel it less, but anyone doing real EU DTC from outside should register an "
               "EU entity or appoint representation before the rules fully apply 12 months after entry.")]),

    (THOMAS, "own-store", 3,
     "Own store vs marketplaces in 2026: with parcel duties now applied to direct EU shipping too, is the 'no marketplace fee' advantage shrinking?",
     "For years the own store won on margin because there was no per-sale commission and, below EUR 150, no "
     "import duty on small parcels. From 1 July 2026 the EUR 3 flat duty per item applies to direct "
     "parcels too, and from 1 November a EUR 2 Union Handling Fee stacks on top. So the 'no marketplace fee' "
     "edge is now partly eaten by border cost on every shipment. The own store still owns the customer and "
     "the margin, but the fulfilment gap versus a marketplace with IOSS has narrowed. How are you weighing "
     "channel mix now?",
     "own-store,channels,customs,2026", 0,
     [(LENA, "We keep the own store for margin and first-party data, but we no longer promise the lowest "
             "price there — we bundle warranty and faster delivery instead, which the marketplace cannot "
             "copy. The new parcel fees just make that positioning more necessary."),
      (JAVIER, "The maths flips once you hold EU stock: marketplaces' IOSS and the deemed-importer rules "
               "mean they absorb the border friction, while your own parcels now carry it. For low-AOV "
               "items, a marketplace may simply be cheaper to ship than your own DTC.")]),

    (JAVIER, "pricing", 2,
     "2026 fee changes are messy: eBay FVF 11 to 12 percent, Zalando EUR 40 base plus ZMS, Kaufland EUR 39.95, OTTO EUR 99.90 — how do you keep one comparison live?",
     "Every platform moved its numbers this year and they do not move in the same direction. eBay Germany "
     "raised the business final-value fee from 11 to 12 percent on several categories in February. Zalando "
     "added a EUR 40 monthly base plus effectively mandatory ad spend (ZMS) on top of 8-25 percent "
     "commission. Kaufland sits around EUR 39.95 monthly plus 6-16 percent commission. OTTO is nearly EUR "
     "100 monthly with 5-22 percent commission. Holding one margin target across all of them by hand is "
     "error-prone. What are people using to keep the per-channel price derivation correct?",
     "pricing,fees,2026", 0,
     [(LENA, "We keep one margin target and derive the selling price per channel from that channel's cost "
             "table, recomputed monthly. The trap is letting a marketplace become the source of truth for "
             "your price — you end up chasing their suggestions."),
      (THOMAS, "Never let a spreadsheet be the only copy. We version the cost table and review it the moment "
               "a platform announces a fee change, because a missed update silently eats margin on the next "
               "restock.")]),

    (AGNIESZKA, "logistics", 3,
     "New EU parcel fees (EUR 3 duty + EUR 2 handling from 1 Nov) change the fulfilment math — is EU-local stock now clearly cheaper than direct ship?",
     "With the EUR 3 flat duty per item from 1 July and the EUR 2 Union Handling Fee per distinct item from "
     "1 November, every direct parcel from outside the EU now carries meaningful border cost. That shifts "
     "the break-even between Pan-EU FBA, a own warehouse in Poland or Germany, and direct ship. Allegro One "
     "Fulfillment, OTTO's German warehouse requirement and Kaufland Fulfillment all look comparatively "
     "cheaper once the parcel fees are in. At what monthly volume does EU-local stock clearly beat direct "
     "parcel shipping for you now?",
     "logistics,fulfilment,2026-fees", 0,
     [(JAVIER, "The handling fee is per distinct item, so multi-piece parcels are hit hardest — bundling "
               "helps but many categories cannot bundle. For us EU-local stock won below roughly 300 units "
               "a month per marketplace once the new fees landed."),
      (LENA, "The hidden cost is also re-testing and re-documenting for the tighter platform checks, which "
             "you avoid by holding compliant stock in the EU. Fulfilment choice is now a compliance choice, "
             "not just a shipping-cost choice.")]),

    (THOMAS, "localization", 4,
     "2026 localization: Allegro auto-translates, bol demands Dutch CS, Zalando wants full attribute mapping — where is machine translation still not enough?",
     "Each platform now pushes language obligations differently. Allegro auto-translates offers across its "
     "Central European marketplaces, which is convenient but you must still own the Polish copy quality. "
     "bol.com requires Dutch customer service as an admission criterion and French for French-speaking "
     "Belgium. Zalando wants complete attribute and size-chart mapping per market. And under GPSR the safety "
     "warnings must be in the language of each market, maintained on the page, not stored once in a document. "
     "Where does machine translation still fall short for you?",
     "localization,translation,2026", 0,
     [(AGNIESZKA, "Machine translation is fine for the description body, but the title and the first "
                  "bullets decide conversion, and warnings must be legally correct per market — those need a "
                  "human or at least a native review. A mistranslated safety warning is a compliance hole, "
                  "not just a wording issue."),
      (JAVIER, "The page-as-evidence enforcement means the warning text has to live on the listing in the "
               "right language. If the translation is only in your file, the auditor sees nothing. Localise "
               "the warning field itself, per market, and keep it updated.")]),

    (THOMAS, "temu", 2,
     "Temu's EUR 200M EU fine and the Oct 26 remediation plan - what does 'deemed importer' now mean for the rest of us?",
     "Saw @emelyelevates break it down on X: the EUR 200M DSA fine landed in May, Temu got a four-month clock, and on 26 October the EU accepted its plan to tackle illegal products. Separately a Chinese-language post (@HouZM001) claimed Temu's EU market share slid from 16% to 8% after the ~EUR 3 customs duty plus EUR 2 handling fee on small parcels. The part that matters for us: 'deemed importer' responsibility for EU-bound goods is shifting toward the platform and the seller, not the buyer. For those shipping low-value parcels into the EU, how are you restructuring who carries the compliance and customs burden?",
     "temu,dsa,fine,deemed-importer,2026", 0,
     [(LENA, "The deemed-importer shift is the big one. If the platform is now on the hook for product safety of what it ships in, expect tighter listing checks to cascade to every seller using that lane. We moved our safety files to per-SKU and pre-cleared them before the fee wave hit."),
      (JAVIER, "The 16%-to-8% share drop, if accurate, is the clearest signal yet that the low-value-parcel model is being repriced by regulation, not just by competition. EU-local stock starts to look cheap relative to the new per-parcel costs.")]),

    (AGNIESZKA, "aliexpress", 3,
     "AliExpress hit with a record EUR 550M DSA fine - does that change how we treat it as a sourcing channel?",
     "@TechieUltimatum posted on X that the European Commission fined AliExpress a record EUR 550M (USD 630M), arguing the platform failed to curb illegal listings. For those of us who source or benchmark against AliExpress assortment, does a fine this size change your risk math - either for selling there or for the products you import that may have originated there?",
     "aliexpress,dsa,fine,sourcing,2026", 0,
     [(THOMAS, "A fine that size signals the Commission will now use DSA as a real lever, not a warning. I would not stop sourcing, but I would document the compliance status of anything that touches that supply chain far more carefully than a year ago."),
      (LENA, "The practical effect for us: whatever we import, the technical file and EU responsible person have to be ours, not assumed from the upstream platform. The fine is on them; the product liability is on us.")]),

    (LENA, "ebay", 1,
     "eBay now blocks listing until you set a postage policy - caught me out this week",
     "@PummyKin vented on X that they 'can't list anything because it demands a postage policy' on eBay UK. I hit the same wall listing into the EU: the flow now refuses to publish until a postage policy is attached, and there is no obvious skip. For anyone who lists across multiple EU countries, how are you setting per-region postage policies without duplicating every listing?",
     "ebay,postage,listing,2026", 0,
     [(THOMAS, "Set one business-policy template per destination zone, then attach it at the listing level. The first one took me twenty minutes; clones after that are seconds. The block is annoying but it forces you to state real shipping terms, which EU buyers expect anyway."),
      (JAVIER, "If you sell the same SKU on eBay and your own store, keep the postage policy in one place and reference it. We learned the hard way that mismatched shipping text between channels triggers trust flags.")]),

    (THOMAS, "amazon", 1,
     "New EU processing fee of EUR 2 per import parcel since 1 November 2026 - how are you absorbing it on Amazon?",
     "@OHN_Infoportal and @Haendlerbund both posted on X that since 1 November 2026 a new EU processing fee of EUR 2 applies per shipment imported from third countries, and it hits 'Amazon und Co'. For FBA or merchant-fulfilled imports into the EU, is this landing on your margin or getting passed to the buyer?",
     "amazon,fees,import,2026", 0,
     [(AGNIESZKA, "We built it into the COGS line, not the listing price, so the fee shows in our margin model instead of surprising us at reconciliation. At our volume EUR 2 per parcel is real money across thousands of units."),
      (LENA, "The interesting part is it compounds with the small-parcel customs duty. Two fixed costs per parcel now, so below a certain basket size EU-direct shipping just does not pencil out.")]),

    (JAVIER, "shopify", 2,
     "Automating GDPR DSAR, cookie banners and GPSR on Shopify - app or manual?",
     "Saw @onep7466 promoting a Shopify compliance app on X that automates EU customer-data withdrawals, GDPR DSAR requests, cookie banners, GPSR and Omnibus discount flags. For a small store, is a compliance app worth the subscription versus wiring the pieces together manually?",
     "shopify,gdpr,gpsr,compliance-app,2026", 0,
     [(LENA, "For us the app paid for itself the first time a DSAR request arrived and was handled without a developer. The risk of missing a GDPR deadline manually is worse than the monthly fee."),
      (THOMAS, "Check that the app actually maintains the GPSR warning text on the product page in the right language. Some only store it in a backend field, which fails the page-as-evidence check.")]),

    (AGNIESZKA, "own-store", 3,
     "Our own store now carries the same EU compliance load as a marketplace - are we just our own marketplace?",
     "Between the processing fee, the deemed-importer rules and the GPSR page-as-evidence requirement, running our own Shopify store into the EU feels as regulated as selling on Amazon. For those who went DTC to escape marketplace rules, how are you handling the compliance stack you thought you'd avoided?",
     "own-store,dtc,compliance,2026", 0,
     [(JAVIER, "DTC still wins on margin and customer data, but you trade marketplace hand-holding for your own compliance team. We treat the store like a marketplace we operate: same technical files, same responsible-person field, same warning localization."),
      (LENA, "The upside is you control the warning text and the page, so page-as-evidence is easier than on a marketplace that mangles your HTML. The burden is real but the control is worth it.")]),

    (THOMAS, "shein", 2,
     "EU small-parcel tax is hitting consumers hard - @lolangoiv's post passed 100k views. What does that mean for our pricing?",
     "@lolangoiv's X post about the EU tax on small packages racked up over 100k views and 2k likes, and @GoodKingV asked why there is a EUR 5 charge per SHEIN clothing item in Europe. Consumers are clearly feeling the new parcel costs. When the end buyer sees a sudden EUR 5 line item, does that make them more or less tolerant of a slightly higher all-in price from a compliant EU-stocked seller?",
     "shein,small-parcel-tax,pricing,consumer,2026", 0,
     [(LENA, "It makes a transparent all-in EU price more attractive, not less. The anger is at the surprise fee, not at paying - so we lead with landed cost and avoid the nasty surprise at checkout."),
      (AGNIESZKA, "@sxh_mnk said they are switching from SHEIN to Vinted over the price. The winners are sellers who stock locally and can promise no surprise parcel fee. That is our opening.")]),

    (JAVIER, "logistics", 2,
     "The 2026 'pile-up' of new EU import and compliance costs - are you re-shoring stock into the EU?",
     "@ANBU_EU summed it up on X: the EU 'added a bunch of new import and compliance costs at once.' Between the customs duty, the EUR 2 processing fee and the tighter platform checks, EU-direct parcel shipping is being repriced. For those who used to ship everything from outside the EU, are you moving safety stock into an EU warehouse to dodge the per-parcel math?",
     "logistics,eu-stock,import-costs,2026", 0,
     [(LENA, "We crossed the line around 300 units a month per marketplace. Below that, parcel costs still won; above it, EU-local stock plus a fulfilment partner beat the per-parcel fees."),
      (THOMAS, "The hidden cost is also re-documenting for the tighter checks, which you avoid by holding compliant stock in the EU. Fulfilment choice is now a compliance choice, not just a shipping-cost choice.")]),

    (AGNIESZKA, "pricing", 3,
     "When the buyer sees a EUR 5-per-item EU charge, who eats it - us or the shopper?",
     "With the new small-parcel charges, the end consumer is now shown explicit EU fees at checkout (one X post cited a EUR 5 charge per SHEIN item). As cross-border sellers we have to decide: absorb it into margin, or show a higher all-in price and own the 'no surprise fee' message. What is actually converting for you?",
     "pricing,parcel-fee,margin,2026", 0,
     [(JAVIER, "We stopped hiding it. All-in price, free of surprise fees, converted better than a low sticker plus a nasty checkout line. The fee is real either way; the trust hit is what costs you."),
      (LENA, "For low-ticket items the EUR 5 is a huge percentage, so EU-local stock that avoids it is the real fix, not just a pricing trick.")]),

    (LENA, "compliance", 2,
     "DSA fines are now real money (EUR 200M Temu, EUR 550M AliExpress) - marketplace due diligence is no longer optional",
     "The size of the 2026 DSA fines - EUR 200M for Temu and a record EUR 550M for AliExpress - changes the calculus. Marketplaces are being pushed to police illegal products, which means stricter upstream checks on every seller. For those of us listing on EU marketplaces, how are you proving due diligence so a platform's liability does not become your takedown?",
     "compliance,dsa,due-diligence,2026", 0,
     [(THOMAS, "Keep the technical file, declaration of conformity and responsible-person contact in one accessible place per SKU. When the platform's due-diligence bot asks, you answer in minutes instead of days."),
      (JAVIER, "The fines also mean platforms will over-enforce to protect themselves, so expect more false takedowns. Pre-empt them with complete docs; it is cheaper than reinstating a suppressed listing.")]),

    (THOMAS, "general", 4,
     "2026 feels like every new EU cost landed in the same quarter - how are you modeling the new baseline?",
     "Scrolling X this week, the themes stack up: a EUR 3 customs duty plus EUR 2 handling on small parcels, a EUR 2 EU processing fee per import since 1 November, DSA fines in the hundreds of millions, and tighter GPSR page-as-evidence checks. For planning 2026, are you building a single 'EU landed-cost' model or still patching channel by channel?",
     "general,eucosts,modeling,2026", 0,
     [(AGNIESZKA, "One model, per SKU, per channel. The patchwork approach broke the moment three fees changed in the same month. Now every listing has a live landed-cost number we trust."),
      (LENA, "The only stable lever left is EU-local compliant stock. Everything else is a moving fee, so we optimised the one thing we control.")]),

    (JAVIER, "bol-com", 3,
     "bol.com sellers: the new EUR 2 EU processing fee still hits your imports - are you switching to EU fulfilment?",
     "@OHN_Infoportal noted the EUR 2 per-import processing fee hits 'Amazon und Co' since 1 November 2026. bol.com imports from outside the EU fall in the same bucket. For those fulfilling bol.com orders from non-EU stock, are you moving to an EU warehouse or passing the fee through?",
     "bol-com,fees,fulfilment,2026", 0,
     [(LENA, "Same math as Amazon for us: below ~300 units a month per channel, parcel fees win; above it, EU stock wins. bol.com's Dutch buyer expects fast delivery anyway, which pushes you to local stock."),
      (AGNIESZKA, "Passing the 2 euro through on a low-ticket item looks terrible at checkout, so we absorbed it and shifted volume to compliant EU stock instead.")]),
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
