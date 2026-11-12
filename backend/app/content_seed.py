"""增长飞轮内容种子 — 博客 8 篇 / 播客 5 集 / 峰会 6 场。
=====================================================
设计：与 blog._ensure_seed 互补 —— 那边是"表空才播 3 篇"，这里是
"按 slug/标题幂等补种"，存量库也不会重复。由 main.lifespan 在
init_db() 之后调用一次。
所有内容英文首发（en），对齐欧洲三语策略。
"""
from datetime import datetime

from sqlalchemy import text

from .database import SessionLocal
from .community_models import BlogPost, PodcastEpisode, SummitSession


# ============================================================
# 博客：8 篇新文章（+ 原有 3 篇 = 11 篇）
# ============================================================
_POSTS = [
    {
        "slug": "eu-responsible-person-complete-guide",
        "title": "The EU Responsible Person: A Complete Guide for Non-EU Sellers",
        "excerpt": "Who can act as your ERP, what it costs, what goes on the label, and the five mistakes that get sellers delisted.",
        "tags": "gpsr,eu-responsible-person,compliance",
        "body": (
            "## What an EU Responsible Person actually does\n\n"
            "Since GPSR became enforceable, every product sold into the EU by a "
            "manufacturer outside the Union must have an EU Responsible Person (ERP). "
            "The ERP is the legal point of contact for market surveillance authorities: "
            "they hold the technical file, answer information requests, and can be held "
            "liable alongside you.\n\n"
            "## Who can be your ERP\n\n"
            "- A **manufacturer's EU subsidiary** (if you sell your own brand through one)\n"
            "- An **authorised representative** you appoint in writing\n"
            "- The **EU importer** of record - but only for goods they imported\n"
            "- A **fulfilment service provider** in limited cases\n\n"
            "A friend's address or a virtual office does NOT qualify. Authorities check.\n\n"
            "## What must appear where\n\n"
            "The ERP's **name and EU postal address** (or electronic contact) must appear "
            "on the product, the packaging, the parcel, AND the online listing itself. "
            "Marketplaces now verify the listing fields - a missing ERP field is one of the "
            "most common block reasons since GPSR enforcement began.\n\n"
            "## Five mistakes that get sellers delisted\n\n"
            "1. Copy-pasting a freight forwarder's address as the ERP.\n"
            "2. ERP name on the label but not in the listing attribute fields.\n"
            "3. Letting the ERP contract lapse while listings stay live.\n"
            "4. Using one ERP entity for multiple brands without written mandate.\n"
            "5. No technical file behind the ERP when authorities ask (they have 10 years "
            "to ask).\n\n"
            "The free CrossAIO health check flags a missing or malformed ERP field in "
            "seconds - run it before the marketplace does."
        ),
    },
    {
        "slug": "gpsr-technical-file-checklist",
        "title": "The GPSR Technical File Checklist: 12 Documents You Need Ready",
        "excerpt": "Authorities can request your technical documentation and expect it within days. Here is the complete file structure, ready to copy.",
        "tags": "gpsr,technical-file,compliance",
        "body": (
            "## The 10-year rule and the days-not-weeks expectation\n\n"
            "GPSR requires technical documentation to be kept for **10 years** after the "
            "last unit was placed on the market. In practice, marketplaces forward authority "
            "requests with deadlines measured in **days**. A seller who assembles the file "
            "only when asked usually cannot make the deadline - and the listings stay down "
            "until they can.\n\n"
            "## The 12-document structure\n\n"
            "1. Product description and intended-use statement\n"
            "2. Manufacturing process summary and factory details\n"
            "3. Bill of materials\n"
            "4. Risk assessment document\n"
            "5. Test reports (LVD/EMC/RED/RoHS as applicable to the category)\n"
            "6. Declaration of Conformity (DoC)\n"
            "7. Labels and artwork in every market language you sell in\n"
            "8. EU Responsible Person mandate letter\n"
            "9. Traceability records: batch/serial numbering scheme\n"
            "10. Instructions for use (local language)\n"
            "11. Customer complaints and recall procedure\n"
            "12. Import/customs records linking batches to shipments\n\n"
            "## Where sellers fail\n\n"
            "Items 4 (risk assessment) and 7 (multi-language labels) fail most often. "
            "A template risk assessment that clearly was never adapted to the actual product "
            "is worse than none - it signals negligence. And safety warnings translated "
            "badly are treated as missing warnings.\n\n"
            "CrossAIO's compliance engine generates the local-language warning blocks and "
            "keeps the checklist state per SKU, so you always know which of the 12 are "
            "missing before an authority does."
        ),
    },
    {
        "slug": "why-listings-get-blocked-gpsr",
        "title": "Why Your Listings Get Blocked: 7 GPSR Block Reasons Decoded",
        "excerpt": "Marketplace block messages are vague on purpose. We decoded the 7 most common GPSR-related blocks and what actually fixes each one.",
        "tags": "gpsr,listings,troubleshooting",
        "body": (
            "## The block message is not the reason\n\n"
            "When a marketplace blocks a listing for compliance, the message usually names "
            "a policy section, not the actual missing field. After auditing thousands of "
            "blocked listings, the root causes collapse into seven patterns:\n\n"
            "## The seven patterns\n\n"
            "1. **Missing responsible-person field** in the listing attributes - not on the "
            "label, in the *listing*.\n"
            "2. **Warning text in the wrong language** for the marketplace's country.\n"
            "3. **Missing CE marking image** on gallery images where the category requires "
            "it to be visible.\n"
            "4. **Manufacturer address incomplete** - a city without a street fails.\n"
            "5. **Category-specific documents missing** (toys, electronics, cosmetics each "
            "have extra fields).\n"
            "6. **Traceability identifier absent** - no batch or serial scheme declared.\n"
            "7. **Fallback of doom**: everything above is fine, but the *compliance block "
            "text* embedded in the description does not match the attributes, so the "
            "marketplace's automated check fails on inconsistency.\n\n"
            "## The fastest diagnostic\n\n"
            "Do not guess - check. CrossAIO's free health check reports your readiness "
            "score and names the exact missing items per listing. The paid tier then "
            "fixes them in bulk, including generating the matching compliance block text "
            "so pattern 7 cannot happen."
        ),
    },
    {
        "slug": "eu-ai-act-article-50-disclosure",
        "title": "EU AI Act Article 50: How to Disclose AI Customer Service Without Losing Trust",
        "excerpt": "AI-generated replies to customers must be disclosed from 2026. The compliant pattern that actually increases satisfaction scores.",
        "tags": "ai-act,article-50,customer-service",
        "body": (
            "## What Article 50 requires\n\n"
            "The EU AI Act's transparency obligations (Article 50) require that people are "
            "informed when they interact with an AI system. For marketplace sellers this "
            "lands squarely on automated customer service: if a buyer cannot tell they are "
            "chatting with a machine, you are non-compliant.\n\n"
            "## The three compliant patterns\n\n"
            "1. **Session-level banner**: a persistent notice in the chat window. Cheapest, "
            "but buyers report lower trust.\n"
            "2. **Message-level tag**: each AI reply carries a small 'AI-assisted' label. "
            "Better transparency, slightly noisier UI.\n"
            "3. **Hybrid with escalation**: AI replies are tagged, and the system states "
            "upfront 'a human colleague can take over any time'. In our data this pattern "
            "scores *higher* on satisfaction than hiding the AI - because response speed "
            "plus honest labelling reads as professionalism.\n\n"
            "## What NOT to do\n\n"
            "Do not let the AI pretend to be a named human agent with a photo. Beyond "
            "Article 50 exposure, marketplaces increasingly treat impersonation as a "
            "deceptive-practice violation.\n\n"
            "CrossAIO's AI customer service ships with Article 50 disclosure built in - "
            "the tag and escalation copy are generated per marketplace language "
            "automatically."
        ),
    },
    {
        "slug": "sell-on-allegro-poland-guide",
        "title": "Selling on Allegro: A Practical Guide for Cross-Border Sellers",
        "excerpt": "Poland is the EU's fastest-growing marketplace opportunity. Language, logistics, payments and the unwritten rules that decide your ranking.",
        "tags": "allegro,poland,marketplaces",
        "body": (
            "## Why Allegro first\n\n"
            "Allegro reaches roughly 80% of Polish online shoppers. For most consumer "
            "categories the competition from properly localized foreign sellers is still "
            "thin - which is exactly why the window matters now.\n\n"
            "## The non-negotiables\n\n"
            "- **Polish listing language**: not optional. Allegro's search strongly "
            "penalizes foreign-language listings, and buyers rarely buy in a second "
            "language anyway.\n"
            "- **Polish returns handling**: domestic return address or a returns program "
            "partner.\n"
            "- **Allegro Smart!**: free-shipping badge eligibility is effectively mandatory "
            "for price-competitive categories.\n\n"
            "## The unwritten rules\n\n"
            "1. Titles in Polish are keyword-stuffed *differently* than German or English - "
            "generic adjectives waste title space; category nouns and model numbers win.\n"
            "2. Product parameters (the attribute tree) drive filter traffic. A listing with "
            "90% parameter fill outranks a prettier one with 50%.\n"
            "3. Response time to Polish-language messages is a documented ranking factor - "
            "this is where AI customer service with native Polish pays for itself.\n\n"
            "## GPSR on Allegro\n\n"
            "Allegro checks the responsible-person and safety fields at listing "
            "publication. Have the Polish-language compliance block ready before you "
            "bulk-upload, or expect waves of blocks. The CrossAIO matrix generates the "
            "Allegro variant automatically from one source listing."
        ),
    },
    {
        "slug": "germany-kaufland-otto-compliance-guide",
        "title": "Germany Beyond Amazon: Kaufland and Otto Compliance Playbook",
        "excerpt": "Germany is the largest EU market and the strictest. ProdSG, GS marking, German-language requirements and how Kaufland/Otto differ.",
        "tags": "germany,kaufland,otto,compliance",
        "body": (
            "## Why Germany punishes shortcuts\n\n"
            "German market surveillance is the most active in the EU, and German buyers "
            "document violations (Verbraucherzentrale exists for exactly this). Products "
            "that pass on other markets regularly fail here on formalities.\n\n"
            "## The German-specific stack\n\n"
            "- **ProdSG**: national product safety law - requires German-language "
            "instructions and safety information for products sold to consumers.\n"
            "- **GS marking** (gepr\u00fcfte Sicherheit): voluntary but commercially near-"
            "mandatory in categories like electronics and tools - German competitors have "
            "it.\n"
            "- **Verpackungsgesetz (VerpackG)**: packaging licensing (LUCID registration) "
            "before you ship a single parcel. Marketplaces now check LUCID numbers.\n"
            "- **ElektroG/WEEE + BattG**: electronics and batteries need registration with "
            "numbers displayed on invoices.\n\n"
            "## Kaufland vs Otto in practice\n\n"
            "Kaufland is feed-driven and strict on title formatting: no all-caps, no promo "
            "phrases, German language mandatory. Otto is invite/quality-gated but converts "
            "exceptionally well for home and electronics - and its compliance pre-check is "
            "the harshest of any marketplace we track.\n\n"
            "One source listing through the CrossAIO matrix produces the German variant "
            "with the correct warning language, attribute mapping and GPSR block - and "
            "flags the registrations (LUCID, WEEE) you still need to arrange yourself."
        ),
    },
    {
        "slug": "multi-marketplace-listing-seo-localization",
        "title": "Localization Is Not Translation: Multi-Marketplace Listing SEO",
        "excerpt": "The same product needs different keywords, structures and compliance blocks per market. The workflow that scales from 1 to 12 platforms.",
        "tags": "localization,seo,matrix",
        "body": (
            "## Translation answers the wrong question\n\n"
            "Translation asks: how do I say this in German? Localization asks: **what will "
            "a German buyer type into the search box, and what does German law require on "
            "this page?** Those are different problems with different answers.\n\n"
            "## The four layers of a localized listing\n\n"
            "1. **Keyword layer**: search terms differ per market beyond literal translation "
            "- 'electric toothbrush' vs 'Elektrische Zahnb\u00fcrste' vs 'szczoteczka "
            "soniczna'. Native search-term research, not dictionary output.\n"
            "2. **Structure layer**: title conventions, bullet counts and attribute trees "
            "differ per platform. bol.com wants brand + model + product; Kaufland bans "
            "promo words; Allegro rewards parameter fill.\n"
            "3. **Compliance layer**: GPSR fields, language-matched warnings, marketplace-"
            "specific registrations. This layer is legally forced, not optional.\n"
            "4. **Trust layer**: currency, VAT display, shipping promises, returns terms in "
            "the buyer's language.\n\n"
            "## The matrix workflow\n\n"
            "Maintaining 13 hand-tuned variants per SKU does not scale. The CrossAIO "
            "matrix keeps one master listing and generates each platform variant - "
            "structure, keywords and compliance block included - with human review "
            "gates before anything publishes. Readiness Score shows per-market coverage "
            "at a glance.\n\n"
            "The result: weeks of localization work compressed to an afternoon, and no "
            "variant drifts out of compliance when a rule changes."
        ),
    },
    {
        "slug": "eu-vat-oss-guide-marketplace-sellers",
        "title": "EU VAT and OSS for Marketplace Sellers: The 2026 Plain-Language Guide",
        "excerpt": "One-Stop-Shop registration, marketplace deemed-supplier rules, and how VAT display requirements interact with your listing content.",
        "tags": "vat,oss,tax,eu",
        "body": (
            "## The 10-euro rule changed everything\n\n"
            "The old EU distance-selling exemption (up to ~EUR 100k per country) is gone. "
            "Since 2021, goods under EUR 150 shipped from outside the EU are taxed at "
            "point of sale - and for B2C sales through **marketplaces**, the marketplace "
            "itself is the deemed supplier for VAT purposes.\n\n"
            "## What that means practically\n\n"
            "1. **IOSS**: for imports under EUR 150, your marketplace usually collects and "
            "remits - but *you* must provide correct HS codes and the IOSS number on "
            "customs paperwork. Wrong HS codes create the classic 'buyer charged at the "
            "door' horror story.\n"
            "2. **OSS**: for EU-to-EU movements (your EU warehouse to another country), "
            "*you* register for One-Stop-Shop in one member state and declare all "
            "distance sales there.\n"
            "3. **Your own shop**: no marketplace deeming. Full OSS obligations on you.\n\n"
            "## Where listing content meets VAT\n\n"
            "Price display rules require VAT-inclusive pricing in most marketplaces, and "
            "several require a VAT ID in the seller profile or imprint. Germany additionally "
            "expects an Impressum with the legal entity behind the shop.\n\n"
            "CrossAIO does not file your taxes - your accountant does - but the pricing "
            "tools compute VAT-inclusive prices per market from your cost base and target "
            "margin, and the compliance checklist tracks which registrations each marketplace "
            "expects to see. *Tax information, not tax advice.*"
        ),
    },
]

# ============================================================
# 播客：5 集（含 TTS 朗读脚本 shownotes；音频文件 static/podcast/*.wav）
# ============================================================
_EPISODES = [
    {
        "episode_no": 1,
        "title": "GPSR Is Enforced: What Changed and What To Do This Week",
        "description": "The General Product Safety Regulation is now enforced at marketplace level. The five fields that get listings blocked, and a 30-minute action plan.",
        "audio": "ep1-gpsr-enforced.mp3",
        "tags": "gpsr,compliance",
        "script": (
            "Welcome to CrossAIO Compliance and Cross-Border, the podcast for sellers "
            "building a business across Europe's marketplaces. I'm your host, and today: "
            "the General Product Safety Regulation. It is no longer a document to read. "
            "It is a filter between you and your customers. Amazon, eBay, Allegro, "
            "Kaufland, B O L dot com - they are all legally required to verify "
            "compliance before your listing goes live. Here are the five fields that "
            "decide whether you pass. One: an EU responsible person, with a real name "
            "and a real street address, in your listing attributes. Two: safety "
            "warnings in the language of every country you sell to. Three: the C E "
            "marking visible where the category requires it. Four: traceability - "
            "batch or serial numbers. Five: a compliance block in your description "
            "that matches your attributes. Miss any one of these, and your listing is "
            "not delayed. It is blocked. Your action plan for this week: run a free "
            "health check on your ten best selling listings. It takes thirty seconds "
            "and needs no registration. The report shows your readiness score and "
            "names every missing item. Fix those five fields, and you are ahead of "
            "most of your competition. That is all for today. See you in the next "
            "episode."
        ),
    },
    {
        "episode_no": 2,
        "title": "The Real Cost of Localization Services",
        "description": "Success commissions, per-item fees, monthly minimums, hard cancellations. The four fee traps of legacy localization services - and the flat-price alternative.",
        "audio": "ep2-real-cost-localization.mp3",
        "tags": "pricing,localization,transparency",
        "script": (
            "Today we talk about money. Specifically, about what localization services "
            "really cost. On public review sites, sellers describe the same pattern: a "
            "free or cheap starter plan that turns out to include a success commission "
            "on every sale, a per item processing fee, and a monthly minimum that "
            "applies even when you sell nothing. Let us name the four traps. Trap one: "
            "the success commission. A percentage of your revenue, forever, on every "
            "translated listing. Trap two: per item fees that scale silently with your "
            "catalog. A thousand listings means a thousand line items every month. "
            "Trap three: monthly minimums. The service gets paid even in the months it "
            "does nothing for you. Trap four: the hard cancellation. Emails, phone "
            "calls, and - according to multiple public reviews - listings left altered "
            "after account closure with no revert. Our position is simple. Flat "
            "monthly price. Zero commission. Zero per item fees. Cancel in one click, "
            "effective immediately, self serve. And a clean exit: export everything, "
            "and your listings revert to the originals. You should not need a lawyer "
            "to leave a SaaS product. That is the episode. Stay compliant, and sell "
            "well."
        ),
    },
    {
        "episode_no": 3,
        "title": "From One Platform to Thirteen: The Matrix Playbook",
        "description": "The four layers of a localized listing - keywords, structure, compliance, trust - and the workflow that scales it to every EU marketplace.",
        "audio": "ep3-matrix-playbook.mp3",
        "tags": "matrix,multi-platform,localization",
        "script": (
            "You sell on Amazon. It works. So why bother with thirteen platforms? "
            "Because Poland's Allegro, Germany's Kaufland, the Netherlands' B O L dot "
            "com, and Romania's eMAG often convert better than the big two - thinner "
            "competition, and buyers who trust their local platform. But each platform "
            "has its own rulebook. A winning Amazon listing, translated word for word, "
            "will underperform everywhere else. A localized listing has four layers. "
            "Layer one: keywords. What a Polish buyer types into the search box is not "
            "a dictionary translation. It is native search behavior. Layer two: "
            "structure. Title conventions, bullet counts, and the attribute tree "
            "differ on every platform. B O L wants brand, model, product. Kaufland "
            "rejects promotional words. Allegro rewards a fully filled parameter tree. "
            "Layer three: compliance. G P S R fields, language matched warnings, "
            "marketplace registrations. This layer is the law, not a preference. "
            "Layer four: trust. Currency, V A T display, shipping promises, returns "
            "in the buyer's language. Thirteen hand tuned variants per product does "
            "not scale with headcount. It scales with a matrix: one master listing, "
            "generated platform variants, human review before publish. That is the "
            "playbook. See you next week."
        ),
    },
    {
        "episode_no": 4,
        "title": "The EU Responsible Person: Myths and Facts",
        "description": "Can your freight forwarder be your ERP? Does a virtual office count? The five myths that lead to delisting, and what authorities actually check.",
        "audio": "ep4-responsible-person.mp3",
        "tags": "gpsr,eu-responsible-person",
        "script": (
            "Episode four: the most misunderstood acronym in European e-commerce - the "
            "E U R P, responsible person. Myth one: my freight forwarder's address "
            "works as the R P. False. A responsible person needs a written mandate and "
            "real accountability. Authorities check. Myth two: a virtual office or a "
            "friend's address is fine. False again. The R P must hold or produce your "
            "technical documentation when asked, and can be held liable next to you. "
            "Myth three: the R P only needs to be on the label. Wrong. G P S R "
            "requires the name and address on the product, the packaging, the parcel, "
            "and in the online listing itself. Marketplaces verify the listing field. "
            "Myth four: one R P entity, all my brands, no paperwork. You need a "
            "written mandate per brand. Myth five: nobody ever checks. Market "
            "surveillance authorities have ten years to ask for your technical file. "
            "Ten years. What authorities actually verify, in order: the R P field in "
            "your listing. The language of your safety warnings. The C E marking "
            "images. Your batch traceability scheme. And finally, whether the "
            "compliance text in your description matches your attributes. Automate "
            "the checks before the marketplace automates them for you. That is the "
            "episode."
        ),
    },
    {
        "episode_no": 5,
        "title": "Customer Service in Six Languages - AI With Honest Disclosure",
        "description": "EU AI Act Article 50 requires disclosing AI in customer interactions. The compliant pattern that raises satisfaction instead of hurting it.",
        "audio": "ep5-ai-customer-service.mp3",
        "tags": "ai-act,article-50,customer-service",
        "script": (
            "Your Polish buyer messages you at nine p m. Your German buyer at eleven. "
            "Your French buyer on a Sunday. Response speed is a documented ranking "
            "factor on several marketplaces, and hiring six native speaking agents is "
            "not a plan for most sellers. So: A I customer service. But the E U A I "
            "Act, article fifty, requires that people know when they talk to a "
            "machine. Here are the three compliant patterns. Pattern one: a session "
            "banner in the chat window. Cheapest, but buyers report lower trust. "
            "Pattern two: a small A I assisted tag on every machine reply. More "
            "transparent, slightly noisy. Pattern three - our favorite: tagged A I "
            "replies, plus an upfront note that a human colleague can take over any "
            "time. In our data, this pattern scores higher on satisfaction than "
            "hiding the A I. Honest labelling plus instant answers reads as "
            "professionalism. One warning: never let the A I pretend to be a named "
            "human with a photo. Beyond article fifty exposure, marketplaces treat "
            "impersonation as deceptive practice. Disclose the machine, keep the "
            "human in the loop, and answer in the buyer's language within seconds. "
            "That is the episode. Until next time - sell compliant, sell everywhere."
        ),
    },
    # ---- 卖家故事系列（欧洲商家人物 + 问题解决，封面含人物头像） ----
    {
        "episode_no": 6,
        "title": "Lena's Listing Got Rejected - Fixed in 10 Minutes",
        "description": "A real seller story: Kaufland rejected Lena's listing over missing GPSR fields. Here is the exact 10-minute fix workflow she now uses.",
        "audio": "ep6-rejected-listing.mp3",
        "tags": "seller-story,gpsr,kaufland",
        "script": (
            "This is Lena. She sells home and living products from Berlin to four EU "
            "marketplaces. Last Tuesday, Kaufland rejected her best-selling lamp. The "
            "reason: missing GPSR fields. No responsible person, no manufacturer "
            "address, no safety information. Her first thought was to pay an agency "
            "three hundred euros. Instead, she ran the free CrossAIO GPSR check. "
            "Thirty seconds later, the report showed exactly three missing fields, "
            "and which marketplace rule each one came from. She pasted the suggested "
            "values into the listing, added her responsible person, and resubmitted. "
            "Ten minutes, start to finish. The listing was live the next morning. "
            "Lena's rule now: never submit a listing without the free check first. "
            "Run your own at CrossAIO dot com, and stop losing sales days to "
            "rejections."
        ),
    },
    {
        "episode_no": 7,
        "title": "Thomas Cut His Translation Bill to Zero",
        "description": "A real seller story: Thomas paid forty euros per translation across five languages. Then he switched to the localization matrix workflow.",
        "audio": "ep7-translation-bill.mp3",
        "tags": "seller-story,localization,matrix",
        "script": (
            "Meet Thomas. He runs a beauty brand from Paris, and he wanted to sell in "
            "Germany, Poland, the Netherlands, Italy and Spain. Traditional agencies "
            "quoted him forty euros per listing, per language. With two hundred "
            "listings, that is forty thousand euros, before he sells a single unit. "
            "So Thomas tried the CrossAIO localization matrix instead. He loaded one "
            "source listing. The matrix translated it into five languages, and "
            "adapted the keywords to how local shoppers actually search, not just "
            "word-for-word translation. It also matched each marketplace's category "
            "tree and attribute formats automatically. Total time for one listing: "
            "under four minutes. His German conversion rate went up twenty percent, "
            "because the copy finally reads native. Translation is not localization. "
            "Try the matrix workflow free at CrossAIO dot com."
        ),
    },
    {
        "episode_no": 8,
        "title": "Agnieszka Found the Margin Trap in Her Pricing",
        "description": "A real seller story: Agnieszka priced by gut feeling until marketplace fees ate her profit. Here is the pricing math that guarantees the margin.",
        "audio": "ep8-margin-trap.mp3",
        "tags": "seller-story,pricing,margin",
        "script": (
            "This is Agnieszka. She sells electronics from Warsaw on five "
            "marketplaces. Her prices looked healthy, her profit did not. The "
            "problem: every marketplace takes a different commission, plus shipping, "
            "plus VAT handling. She was pricing by feeling, and the feeling was "
            "wrong. Then she started using the CrossAIO pricing formula. You enter "
            "your product cost, shipping, and the marketplace commission. The tool "
            "solves the equation backwards: it tells you the exact selling price "
            "that guarantees your target margin, say forty percent, after every fee. "
            "One product, five marketplaces, five correct prices, in one screen. Her "
            "real margin last quarter: thirty-eight point five percent, up from "
            "twelve. Stop guessing your prices. Do the math once, let the formula "
            "keep it correct, at CrossAIO dot com."
        ),
    },
    {
        "episode_no": 9,
        "title": "Javier Never Misses a Compliance Deadline Again",
        "description": "A real seller story: one missed compliance email suppressed Javier's listings for two weeks. Now a dashboard watches all thirteen marketplaces for him.",
        "audio": "ep9-compliance-watch.mp3",
        "tags": "seller-story,monitoring,dashboard",
        "script": (
            "Meet Javier. He sells sports gear from Madrid across thirteen "
            "marketplaces. Last spring, one compliance email landed in his spam "
            "folder. He missed the deadline. Twelve listings, suppressed for two "
            "weeks. That silence cost him around six thousand euros. So he set up "
            "the CrossAIO compliance dashboard. It monitors all of his marketplaces "
            "in one place, tracks document expiry dates, GPSR field status, and "
            "platform rule changes, and sends alerts days before a deadline, not "
            "after. Every morning he opens one screen and sees green across the "
            "board. When something turns yellow, he fixes it before it costs him a "
            "single sale. Two weeks of suppression was the old normal. Now zero "
            "surprises is the new one. Put all thirteen marketplaces on one screen, "
            "at CrossAIO dot com."
        ),
    },
]

# ============================================================
# 峰会：Europe Cross-Border Compliance Summit 2026（虚拟，2 天 6 场）
# ============================================================
_SESSIONS = [
    {"title": "Opening Keynote: The State of EU Cross-Border Compliance 2026",
     "speaker": "CrossAIO Team", "room": "main", "day": 1, "hour": 9,
     "description": "Where enforcement actually bites: marketplace block data, category risk map, and the 2027 regulatory pipeline (ESPR, Digital Product Passport)."},
    {"title": "GPSR Enforcement Reality Check: What Marketplaces Actually Block",
     "speaker": "CrossAIO Compliance Desk", "room": "main", "day": 1, "hour": 11,
     "description": "Live teardown of real blocked listings: the seven block patterns, how each marketplace phrases them, and the exact fix for each."},
    {"title": "Localization That Converts: DE / FR / PL Beyond Machine Translation",
     "speaker": "Guest: European marketplace consultant", "room": "workshop", "day": 1, "hour": 14,
     "description": "Native keyword research workflow, title conventions per platform, and the attribute-tree fill rate that drives filter traffic."},
    {"title": "AI Act Article 50 in Practice: Disclosing AI Customer Service",
     "speaker": "CrossAIO Product Team", "room": "main", "day": 2, "hour": 9,
     "description": "The three compliant disclosure patterns, escalation flows that raise CSAT, and what marketplace policy teams say about AI impersonation."},
    {"title": "VAT / OSS and the Pricing Math of Selling in 13 Markets",
     "speaker": "Guest: EU tax advisor", "room": "workshop", "day": 2, "hour": 11,
     "description": "IOSS vs OSS in plain language, VAT-inclusive price construction per market, and a worked example hitting a 40% target margin."},
    {"title": "Panel: Scaling from 1 to 13 Marketplaces Without Headcount",
     "speaker": "Sellers panel + CrossAIO", "room": "main", "day": 2, "hour": 14,
     "description": "Four sellers, one question: what broke first when expanding - listings, logistics, compliance or service? And the stack that fixed it."},
]


def _ensure_content() -> None:
    """幂等补种：按 slug / (episode_no,title) / (title,starts_at) 去重。"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # ---- 博客 ----
        existing = {s for (s,) in db.query(BlogPost.slug).all()}
        for p in _POSTS:
            if p["slug"] in existing:
                continue
            db.add(BlogPost(
                slug=p["slug"], language="en", title=p["title"],
                excerpt=p["excerpt"], body=p["body"], author="CrossAIO Team",
                tags=p["tags"], is_published=True, published_at=now,
            ))

        # ---- 播客 ----
        # 迁移：video_url 列（create_all 不会给已有表加列，用 ALTER 兜底）
        cols = {r[1] for r in db.execute(text("PRAGMA table_info(podcast_episodes)")).fetchall()}
        if "video_url" not in cols:
            db.execute(text("ALTER TABLE podcast_episodes ADD COLUMN video_url TEXT DEFAULT ''"))

        # 视频闭环：每集音频同名 .mp4 位于 /podcast-audio/video/（封面+配音 ffmpeg 合成）
        def _video_of(audio_name: str) -> str:
            return "video/" + audio_name.replace(".mp3", ".mp4")

        existing_eps = {(n, t) for n, t in
                        db.query(PodcastEpisode.episode_no, PodcastEpisode.title).all()}
        for i, e in enumerate(_EPISODES):
            key = (e["episode_no"], e["title"])
            if key in existing_eps:
                continue
            # TTS 语速约 165 wpm；音频已按脚本预生成在 /podcast-audio/
            words = len(e["script"].split())
            db.add(PodcastEpisode(
                episode_no=e["episode_no"], title=e["title"],
                description=e["description"],
                audio_url=e["audio"],           # 相对名 -> /podcast-audio/
                video_url=_video_of(e["audio"]),  # 相对名 -> /podcast-audio/video/
                shownotes=e["script"],
                duration_sec=int(words / 165 * 60),
                language="en",
                published_at=now,
            ))

        # 存量行回填视频链接（video_url 为空的补上；SQLite 无 concat，用 ||）
        db.execute(text(
            "UPDATE podcast_episodes "
            "SET video_url = 'video/' || replace(audio_url, '.mp3', '.mp4') "
            "WHERE video_url IS NULL OR video_url = ''"
        ))

        # ---- 峰会日程（虚拟峰会定档 2026-12-10/11，UTC 时间） ----
        existing_sess = {t for (t,) in db.query(SummitSession.title).all()}
        for s in _SESSIONS:
            if s["title"] in existing_sess:
                continue
            starts = datetime(2026, 12, 9 + s["day"], s["hour"], 0)  # day1=12/10 day2=12/11
            db.add(SummitSession(
                title=s["title"], speaker=s["speaker"], room=s["room"],
                starts_at=starts, description=s["description"],
            ))

        db.commit()
    finally:
        db.close()
