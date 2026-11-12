# -*- coding: utf-8 -*-
"""English (en) data module for /en/features/* landing pages.

Pure data: no FastAPI routing, no logic. Structure mirrors
``app/routers/feature_pages.py::FEATURES`` one-to-one so the en wiring layer
can render /en/features/{slug} exactly like the zh source page.

Sections:
  FEATURES_EN  — 9 page dicts, same keys as FEATURES
  CHROME_EN    — page chrome (CTAs, section titles, footer, index page copy)
  MOCKUP_EN    — UI strings shown inside the SVG mockups, per mockup key
"""

# ---------------------------------------------------------------------------
# A) FEATURES_EN — 9 pages, isomorphic to FEATURES
# ---------------------------------------------------------------------------

FEATURES_EN = {
    "gpsr": {
        "icon": "🛡️",
        "name": "GPSR compliance engine",
        "title": "GPSR compliance engine — CE category detection · EU Rep + local-language warnings · one-click compliance block backfill | CrossAIO",
        "meta_desc": "EU 2023/988 GPSR is already enforced: auto-detect CE categories and applicable directives, generate a compliance block with EU Rep and 16-language warnings, hard-block on the attribute tree, 7×24 monitoring with safety-event alerts. Start with a free compliance check.",
        "eyebrow": "Capability ① · #1 reason to pay",
        "h1": "One missing compliance block, <br>and your listing risks<em> full delisting</em>",
        "sub": "CrossAIO's compliance engine: CE category auto-detection → applicable directive matching → EU Rep + local-language safety warnings → a GPSR compliance block you can paste or backfill via API. A fear-driven reason to pay: one violation costs more than a year of subscription.",
        "hero_note": "✓ Free check first reports risks · ✓ Starter unlocks the full compliance block · ✓ No store binding required",
        "mockup": "gpsr",
        "pain_title": "The cost of skipping GPSR",
        "pains": [
            "EU 2023/988 has been enforced since 2024-12: non-food products sold in the EU must show an EU Rep plus local-language warnings; one missing piece means delisting",
            "SellSafe handles compliance documents but not listing copy; copy tools (H10 and alike) ignore compliance entirely — neither solves 'the compliance block inside the listing'",
            "Machine-translated warnings are not accepted by regulators: German/French/Polish/Romanian warnings must read as native market phrasing, not literal translation",
            "EU Rep details live scattered in Excel and chat logs; 30% of listings forget them or enter them wrong",
        ],
        "caps": [
            {"group": "Compliance block generation", "color": "g1", "items": [
                ("CE category auto-detection", "A rule library of 7 CE categories (toys/electrical/PPE/baby-maternal/food-contact, etc.) auto-matches applicable directives"),
                ("EU Rep + warning compliance block", "The EU Rep line auto-substitutes the default responsible person from your registry; 7 natively-worded warning languages, not literal translations"),
                ("Platform-native headers", "Platform-local headers — Allegro in Polish, eMAG in Romanian — backfill the corresponding fields directly"),
            ]},
            {"group": "Hard block & monitoring", "color": "g2", "items": [
                ("Attribute-tree hard block", "Hard-blocks like platform review does: bad EAN check digit, missing material → ready_to_list = false"),
                ("7×24 monitoring + daily risk report", "Daily scheduled checks on live listings, automatic re-checks on rule updates, pushed daily risk reports"),
                ("Safety-event alerts", "Buyer messages touching safety/physical harm → 15-day Safety Gate reporting reminder"),
            ]},
        ],
        "steps": [
            ("Enter product info", "Product title + keywords + category, no store binding, check results in 30 seconds"),
            ("Auto-detect category & directives", "The 7-rule CE library matches applicable directives and warning requirements; the free version reports the issue list first"),
            ("Unlock the block & backfill", "Starter unlocks the full block: EU Rep line + local-language warnings + platform-native headers, paste or API-backfill"),
        ],
        "stats": [("7", "CE category rules"), ("7", "native warning languages"), ("13", "platform backfill adapters"), ("15-day", "Safety Gate reporting reminder")],
        "tier_line": "Free: check reports issues only · Starter €29/month: full compliance block + attribute-tree validation + 7×24 monitoring",
        "faqs": [
            ("What's the difference between the free check and the paid block?", "The free check tells you what's missing and how you'll be penalized (an issue list); from Starter, CrossAIO generates the full paste-ready compliance block (EU Rep + warnings + platform-native headers) and supports API backfill to 12 platforms."),
            ("Are the warnings machine-translated?", "No. The German/French/Italian/Spanish/Polish/Romanian/English warnings are native market phrasing (e.g. the German ProdSG / French DGCCRF enforcement context), not literal translation. Other languages output an explicitly marked English annotation line instead of an empty placeholder."),
            ("Where does the EU Rep info come from?", "You maintain multiple EU Responsible Persons in your EU Rep registry and set a default; the block auto-substitutes placeholders, so you never fill it by hand."),
        ],
        "related": [("listing-generator", "📦 Listing generator"), ("matrix", "🌍 Multi-platform matrix"), ("safety-redline", "🚨 Policy safety red-line layer")],
    },

    "listing-generator": {
        "icon": "📦",
        "name": "Listing generator",
        "title": "Listing generator — per-platform character hard validation · bullet points + description + search terms · 16 languages | CrossAIO",
        "meta_desc": "One input generates title/bullets/description/search terms, with hard limits like Otto 70 / Allegro 75 / Amazon 200 characters; auto-scored on generation with violations flagged; 16-language localization. 5 free runs a day.",
        "eyebrow": "Capability ② · The entry point",
        "h1": "One input, <br>listing copy that <em>passes review</em> by platform rules",
        "sub": "Title + bullet points + description + search terms, generated against the character, language and structure rules of 12 platforms. Auto-scored on generation with violations flagged — not 'suggested fields', but hard validation like platform review does.",
        "hero_note": "✓ 5 free runs/day · ✓ No store binding · ✓ Copy-paste to publish",
        "mockup": "generator",
        "pain_title": "The common flaw of copy tools",
        "pains": [
            "Generic AI writes titles over Otto's 70-character / Allegro's 75-character limits, and platforms reject them outright",
            "Write first, translate later: translated bullet points don't read like a native seller's phrasing, and conversion halves",
            "Quality relies on eyeball checks; no tool hard-validates against platform rules at generation time",
            "Descriptions and search terms ignore platform structure rules, silently hurting search ranking",
        ],
        "caps": [
            {"group": "Generation", "color": "g1", "items": [
                ("Title / bullets / description / search terms", "All four in one generation, organized per platform structure — not a simple splice"),
                ("16-language localization", "en/de/fr/es/it/pl/ro/nl/cs/sk/hu/bg/sv and more, auto-matched per platform"),
                ("Ad copy", "From Pro: on-site ad headlines and selling-point copy, sharing the same keywords as the listing"),
            ]},
            {"group": "Validation", "color": "g2", "items": [
                ("Character hard validation", "Limits like Otto 70 / Allegro 75 / Amazon 200 are built-in hard rules; over-length is flagged immediately"),
                ("Completeness score", "Auto-scored on generation; violations and missing fields are flagged before you publish"),
                ("Platform structure rules", "Title structure, bullet count and search-term format kept current per Seller Central docs"),
            ]},
        ],
        "steps": [
            ("Enter product info", "Product name + core keywords; optional brand/EAN/material attributes"),
            ("Pick platforms & generate", "Single-platform refinement or batch matrix; language and rules auto-matched"),
            ("Validate & publish", "After character hard validation and completeness scoring pass, copy-paste into the platform Seller Central"),
        ],
        "stats": [("13", "platform rules built in"), ("16", "languages generated"), ("5/day", "free quota"), ("90%", "average ops time saved")],
        "tier_line": "Free: 5 runs/day · Starter €29/month: 50 runs/day + embedded GPSR block · Pro €49/month: 200 runs/day + ad copy",
        "faqs": [
            ("How is this different from writing in ChatGPT?", "ChatGPT doesn't know hard platform rules like Otto 70 characters or Allegro 75, and doesn't know what GPSR must embed. CrossAIO turns the rules of 12 platforms into hard validation: compliant the moment it's generated, no revision loops."),
            ("How is the generated listing quality guaranteed?", "Auto-scored on generation: characters, language and structure requirements checked item by item with violations flagged; the attribute tree hard-blocks issues like EAN check digits, so review-rejectable problems surface before publishing."),
            ("Do I need to bind my store?", "No. CrossAIO is a standalone workbench: sign up and use it. Copy results into any platform's Seller Central."),
        ],
        "related": [("matrix", "🌍 Multi-platform matrix"), ("gpsr", "🛡️ GPSR compliance engine"), ("review-rewrite", "📈 Review rewriting loop")],
    },

    "matrix": {
        "icon": "🌍",
        "name": "Multi-platform matrix",
        "title": "Multi-platform matrix — one input, batch localization for 12 platforms · zero-competition coverage on Allegro/eMAG/Cdiscount | CrossAIO",
        "meta_desc": "One input → batch-generate localized listings for 12 platforms: Amazon EU+US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com. Standalone workbench, no store binding.",
        "eyebrow": "Capability ③ · The scale lever",
        "h1": "One input, <br>batch localization for <em>12 platforms</em>",
        "sub": "Amazon EU + US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com — all rules built in, languages auto-matched. H10 ignores local platforms; Marqetir forces store binding; we do neither.",
        "hero_note": "✓ Standalone workbench, no store binding · ✓ Long-tail platforms cover Eastern/Southern Europe · ✓ Results editable per platform",
        "mockup": "matrix",
        "pain_title": "The real cost of expanding platforms",
        "pains": [
            "Every new platform means re-learning rules from scratch: character limits, language, category attributes and compliance fields all differ",
            "H10 only covers Amazon; Marqetir/SellerCloud require store API binding to work — data security is questionable",
            "Allegro (Poland), eMAG (Romania), Cdiscount (France) have zero coverage in mainstream tools, yet they are the fastest-growing markets in Eastern/Southern Europe",
            "Translating and copy-pasting platform by platform takes a full day to push one SKU live everywhere",
        ],
        "caps": [
            {"group": "Matrix generation", "color": "g1", "items": [
                ("12-platform batch generation", "One input → localized results for 12 platforms; editable, copyable and backfillable per platform"),
                ("Auto language matching", "pl/de/fr/ro/nl etc. auto-selected per platform, no manual setup"),
                ("Embedded compliance blocks", "Every output carries its GPSR block (from Starter) — expanding platforms never drops compliance"),
            ]},
            {"group": "Long-tail platforms", "color": "g3", "items": [
                ("Eastern Europe growth engine", "Allegro (PL/CZ/SK/HU) + eMAG (RO/HU/BG) — markets with zero competitor coverage"),
                ("Southern/Western Europe gap filled", "Cdiscount (FR) + Fruugo (pan-EU, 20+ countries) supported first"),
                ("Rule pages fully public", "Rule details for the six deep-dive platforms are published as free landing pages; the rule library stays transparent"),
            ]},
        ],
        "steps": [
            ("Enter product info once", "Product name + keywords + attributes; one input for all platforms"),
            ("Tick target platforms", "Single-platform refinement or select all 13; rules and languages auto-matched per platform"),
            ("Export / backfill in batch", "Copy-paste per platform, or backfill via the API adapter layer (Amazon SP-API / eBay REST)"),
        ],
        "stats": [("13", "platform rules built in"), ("16", "languages generated"), ("0", "stores required to bind"), ("4", "long-tail platforms competitors miss")],
        "tier_line": "Free: single-platform trial · Pro €49/month: 3-platform matrix · Business €149/month: unlimited platform matrix + priority support",
        "faqs": [
            ("Which 12 platforms are included?", "Amazon EU+US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com. Among them, Cdiscount, Allegro, eMAG and Fruugo have zero coverage in competing tools."),
            ("How about matrix quality and small-language quality?", "Each platform is hard-validated against its Seller Central docs for characters/language/structure; small languages are auto-matched to the local language, with GPSR warnings in native phrasing."),
            ("Really no store binding?", "Correct. Matrix generation happens entirely inside the CrossAIO workbench. Only 'API backfill' needs your developer credentials for the corresponding platform (Amazon SP-API / eBay OAuth); credentials live in your own environment variables."),
        ],
        "related": [("listing-generator", "📦 Listing generator"), ("gpsr", "🛡️ GPSR compliance engine"), ("ai-service", "💬 AI customer service")],
    },

    "review-rewrite": {
        "icon": "📈",
        "name": "Review rewriting loop",
        "title": "Review rewriting loop — 8-theme detection · bullet fixes · semantic scoring (Rufus/iZi ready) | CrossAIO",
        "meta_desc": "Negative reviews auto-tagged into 8 themes, generating bullet-point fixes and rewrites; semantic coverage scoring over 8 common buyer questions, optimized for AI shopping assistants like Rufus / iZi. Weekly use, directly tied to conversion.",
        "eyebrow": "Capability ④ · Renewal reason",
        "h1": "A negative review isn't the end — <br>it's a <em>rewrite directive</em> for the listing",
        "sub": "Negative reviews are auto-tagged into 8 themes (oversized/battery too short/packaging damage, etc.), generating bullet fixes and rewriting the corresponding selling points; then a semantic score checks whether your listing answers the 8 questions buyers ask most — so that AI guides like Rufus and iZi recommend your product too.",
        "hero_note": "✓ Weekly use · ✓ Fix suggestions generate new bullets directly · ✓ Free semantic-score trial",
        "mockup": "review",
        "pain_title": "Wasted negative-review data",
        "pains": [
            "Reviews are only 'replied to', never 'exploited': themes stay scattered in comments and nobody converts them systematically into listing fixes",
            "AI shopping assistants like Rufus (Amazon) and iZi (Allegro) are starting to decide for buyers; questions your listing doesn't answer get answered as a competitor's",
            "Rewriting bullets by gut feel; no tool quantifies 'how many buyer-question themes does this listing answer'",
            "Reviews mix in safety claims (breaking/overheating/choking risk), and ordinary support flows miss the GPSR safety-event reporting duty",
        ],
        "caps": [
            {"group": "Review → Listing loop", "color": "g1", "items": [
                ("8-theme detection", "Auto-tags: size/battery/material/packaging/logistics/genuineness doubts/setup difficulty/safety claims"),
                ("Bullet fixes + rewrite", "Generates fix suggestions per theme and rewrites the corresponding bullets into a publishable new version"),
                ("Safety-claim alerts", "Safety-themed reviews auto-trigger the GPSR safety-event alert (15-day Safety Gate reminder)"),
            ]},
            {"group": "Semantic scoring", "color": "g3", "items": [
                ("8-question coverage", "Quantifies how well the listing answers common buyer questions, theme by theme, with gaps listed"),
                ("Rufus / iZi ready", "Semantic structure optimized for AI shopping assistants, so they quote your selling points"),
                ("Iteration tracking", "Re-score after rewrites, quantifying the coverage gain from each fix"),
            ]},
        ],
        "steps": [
            ("Import reviews", "Paste negative reviews/comments, or auto-pull per platform (in development: eBay integration)"),
            ("Theme detection + fixes", "Tags into 8 themes and generates fixes and rewrites for the corresponding bullets"),
            ("Re-score & publish", "Re-scores coverage; the new version replaces the live one directly"),
        ],
        "stats": [("8", "review themes"), ("8", "semantic dimensions"), ("2", "AI guide platforms"), ("weekly", "typical usage")],
        "tier_line": "Free: semantic-score trial · Pro €49/month: review rewriting loop + ad copy · Business: batch monitoring",
        "faqs": [
            ("Where does the review data come from?", "Today, manual paste of reviews/comments is supported; after eBay integration, authorized auto-pull becomes available. All analysis stays inside your CrossAIO account and is never shared with third parties."),
            ("What is the semantic score?", "It takes the 8 most common buyer questions (size, battery, material, safety, etc.) as dimensions and quantifies how well your listing answers each. AI guides like Rufus and iZi filter for buyers with similar logic."),
            ("Are safety-themed reviews handled differently?", "Yes. Reviews touching safety/physical injury auto-trigger a compliance-first flow: GPSR guidance + 15-day Safety Gate reporting reminder, never processed as an ordinary review."),
        ],
        "related": [("gpsr", "🛡️ GPSR compliance engine"), ("listing-generator", "📦 Listing generator"), ("safety-redline", "🚨 Policy safety red-line layer")],
    },

    "ai-service": {
        "icon": "💬",
        "name": "AI customer service",
        "title": "AI customer service — native EU AI Act Art.50 disclosure · eBay integration · cross-platform unified inbox | CrossAIO",
        "meta_desc": "Buyer messages pushed via webhook → LLM drafts replies → every reply natively embeds the EU AI Act Art.50 disclosure (mandatory 2026-08-02), with GPSR red-line interception and a cross-platform unified inbox. Competitors sell fast replies; we sell non-violating ones.",
        "eyebrow": "Capability ⑤ · Compliance acquisition entry",
        "h1": "Every AI reply <br>natively embeds <em>AI Act Art.50 disclosure</em>",
        "sub": "After eBay seller authorization, buyer messages webhook-push into CrossAIO; AI drafts replies and sends back only after you confirm. Every reply natively embeds the EU AI Act Art.50 machine-identity disclosure (mandatory from 2026-08-02, fines up to €15M or 3% of revenue). 16-language disclosure, managed in a cross-platform unified inbox.",
        "hero_note": "✓ Sent only after your confirmation · ✓ Art.50 disclosure in 16 languages · ✓ No third-party support tools needed",
        "mockup": "inbox",
        "pain_title": "The compliance blind spot of support tools",
        "pains": [
            "Official Amazon/eBay AI support only solves 'fast replies' with no AI Act compliance layer at all",
            "Support tools like Responso / eDesk / BaseLinker still have zero built-in AI Act Art.50 disclosure — and it takes effect mandatorily on 2026-08-02",
            "Safety claims inside buyer messages (product breaking/overheating/children swallowing) get auto-replied as ordinary inquiries, missing the GPSR reporting duty",
            "Buyer messages from 12 platforms sit scattered in each seller backend; reply styles diverge and compliance status can't be tracked",
        ],
        "caps": [
            {"group": "Replies & disclosure", "color": "g1", "items": [
                ("Native Art.50 disclosure", "Every AI reply carries a 16-language machine-identity disclosure, phrased in the buyer's language"),
                ("LLM reply drafts", "Context-aware drafts; sent only after your confirmation, fully logged"),
                ("GPSR red-line interception", "Buyer messages touching safety/physical harm → switch to a 'compliance-first reply': GPSR guidance + 15-day Safety Gate reminder"),
            ]},
            {"group": "Inbox & integrations", "color": "g2", "items": [
                ("eBay webhook integration", "OAuth2 authorization enables real-time buyer-message push, no third-party tools"),
                ("Cross-platform unified inbox", "12 platforms' conversations managed together: manual import + API pull, GPSR/AI Act status marked per thread"),
                ("Data stays with you", "All data lives in your CrossAIO account; credentials in your own environment variables"),
            ]},
        ],
        "steps": [
            ("Authorize & connect", "eBay OAuth2 authorization pushes buyer messages via webhook (other platforms: manual import)"),
            ("AI drafts replies", "The LLM drafts in the buyer's language with Art.50 disclosure auto-embedded; safety claims trigger compliance-first replies"),
            ("Confirm & send", "You confirm in the unified inbox before sending; GPSR / AI Act status of every conversation is logged and auditable"),
        ],
        "stats": [("16", "Art.50 disclosure languages"), ("13", "unified inbox platforms"), ("€15M", "max AI Act fine"), ("2026-08", "Art.50 effective date")],
        "tier_line": "Pro €49/month: AI customer service + unified inbox · Business: multi-store + priority support",
        "faqs": [
            ("What is the AI Act Art.50 disclosure?", "EU AI Act Article 50 requires disclosing machine identity whenever AI interacts with people; it takes effect mandatorily on 2026-08-02, with fines up to €15M or 3% of global revenue. CrossAIO natively embeds the disclosure text, phrased in the buyer's language, into every AI reply."),
            ("Will the AI send replies directly to buyers?", "No. AI only drafts; you confirm in the unified inbox before sending. Safety claims are forced into a 'compliance-first reply' with the 15-day reporting duty reminder."),
            ("Which platforms besides eBay connect?", "eBay is connected (real-time webhook push); the other 12 platforms support manual import + an API adapter layer in the unified inbox, with real-time access rolling out per platform."),
        ],
        "related": [("safety-redline", "🚨 Policy safety red-line layer"), ("gpsr", "🛡️ GPSR compliance engine"), ("matrix", "🌍 Multi-platform matrix")],
    },

    "safety-redline": {
        "icon": "🚨",
        "name": "Policy safety red-line layer",
        "title": "Policy safety red-line layer — threat/extortion detection · compliance-first replies · 15-day Safety Gate reporting | CrossAIO",
        "meta_desc": "Threats, extortion and physical-injury claims are auto-detected: reassure + hand off to a human, logged — no mindless auto-replies. Triggers the GPSR safety-event flow (15-day Safety Gate reminder) plus AI Act disclosure. Compliance over efficiency.",
        "eyebrow": "Capability ⑥ · The safety net",
        "h1": "Threats, extortion, injury claims — <br><em>compliance first</em>, no mindless auto-reply",
        "sub": "No matter how fast AI customer service is, it can't auto-reply to threats, extortion or physical-injury claims. CrossAIO's red-line layer auto-detects high-risk messages: reassure + hand off to a human + keep an auditable trail, triggering the GPSR safety-event flow (15-day Safety Gate reminder) and AI Act disclosure. Competitors sell efficiency; we hold your compliance floor.",
        "hero_note": "✓ High-risk messages forced to a human · ✓ Reporting deadlines auto-reminded · ✓ Fully logged, auditable",
        "mockup": "redline",
        "pain_title": "The cost of mindless auto-replies",
        "pains": [
            "Pure efficiency AI support still politely auto-replies to 'product caught fire / child swallowed something', missing the 15-day mandatory Safety Gate window",
            "Threat and extortion messages are handled as ordinary disputes, unlogged — when a dispute or platform appeal comes later, there's no evidence chain",
            "After emotions escalate, different agents pick up arbitrarily, messages stay inconsistent, and small disputes drag into platform complaints",
            "No support tool has built-in the GPSR safety-event flow (delisting assessment, reporting, recall assessment)",
        ],
        "caps": [
            {"group": "Detection & block", "color": "g2", "items": [
                ("High-risk message detection", "Threat/extortion/physical-harm/child-safety claims are auto-classified and hard-blocked from auto-reply"),
                ("Reassure + hand off", "Generates a reassuring script and hands off to a human, with evidence-check prompts (screenshots/order number/original message)"),
                ("Compliance-first reply", "Safety events switch to GPSR-guided replies: stop-sale assessment advice + 15-day Safety Gate reminder"),
            ]},
            {"group": "Evidence & reporting", "color": "g3", "items": [
                ("Full evidence trail", "Every conversation is fully logged: detection result, handling actions, reply content — auditable"),
                ("Safety Gate reminder", "The 15-day reporting deadline is auto-reminded, with a Safety Gate submission checklist"),
                ("Art.50 stays intact", "Red-line replies also natively embed the AI Act disclosure — no blind spots in the compliance layer"),
            ]},
        ],
        "steps": [
            ("Message hits the red-line layer", "All buyer messages pass high-risk detection first (threat/extortion/harm/child safety)"),
            ("Forced hand-off + evidence", "High-risk messages skip auto-reply: reassuring script + hand off to human + evidence prompts"),
            ("GPSR safety-event flow", "Confirmed safety event → stop-sale assessment + 15-day Safety Gate reminder → fully logged"),
        ],
        "stats": [("15-day", "Safety Gate deadline"), ("4", "high-risk message types"), ("100%", "of high-risk messages to a human"), ("full", "audit trail")],
        "tier_line": "From Pro €49/month, including the red-line layer · linked with AI customer service and the unified inbox",
        "faqs": [
            ("What counts as a high-risk message?", "Four types: threats (violence/lawsuit intimidation), extortion (leveraging reviews/reports), product injury claims (fire/breakage/allergy), and child-safety claims (swallowing/choking). Any hit blocks auto-reply."),
            ("What happens after a block?", "A reassuring script is generated and handed off to a human, with evidence prompts; if it's confirmed as a safety event, the GPSR flow runs: stop-sale assessment advice and the 15-day Safety Gate reminder. Every action is logged."),
            ("How does this relate to AI customer service?", "The red-line layer is the front layer of AI support: all messages pass high-risk detection first; only ordinary messages enter the AI draft flow. Both layers run inside the unified inbox."),
        ],
        "related": [("ai-service", "💬 AI customer service"), ("gpsr", "🛡️ GPSR compliance engine"), ("review-rewrite", "📈 Review rewriting loop")],
    },

    "inbox": {
        "icon": "📥",
        "name": "Unified inbox",
        "title": "Unified inbox — buyer messages from 12 platforms in one place · AI replies in buyers' native language · compliance status per thread | CrossAIO",
        "meta_desc": "Bring buyer messages from 12 platforms like Amazon/eBay/Allegro/Otto/Kaufland into one interface: AI drafts replies in the buyer's native language, with Art.50 disclosure and GPSR safety guidance auto-embedded, compliance status logged per thread.",
        "eyebrow": "Capability ⑦ · The scale-bottleneck cure",
        "h1": "Buyer messages from 12 platforms, <br>managed in <em>one inbox</em>",
        "sub": "European cross-border sellers run 6+ platforms on average, with buyer messages scattered across backends in different languages. CrossAIO's unified inbox brings 12 platforms' conversations together: eBay real-time sync via OAuth, other platforms via self-serve credentials or batch import; AI drafts in the buyer's native language, with Art.50 disclosure + GPSR safety guidance auto-embedded.",
        "hero_note": "✓ eBay real-time sync · ✓ 12 platforms via self-serve credentials/import · ✓ Replies logged for compliance",
        "mockup": "inbox",
        "pain_title": "The triple cost of multi-platform support",
        "pains": [
            "Logging into each platform to check messages: switching between 6 backends a day; one missed reply becomes a bad review or a return",
            "German/Polish/Romanian messages you can't read; machine-translated replies convert poorly and sound rude",
            "AI support tools ignore platform rules: missing Art.50 disclosure, safety claims answered as ordinary questions",
            "Which thread was handled, which triggered a safety event — scattered across platforms, impossible to audit",
        ],
        "caps": [
            {"group": "Aggregation & sync", "color": "g1", "items": [
                ("eBay real-time sync", "OAuth2 authorization enables real-time buyer-message webhook push; AI replies can be sent directly"),
                ("12 platforms via self-serve credentials/import", "Paste API credentials for Allegro/Otto/Kaufland etc. (AES-256 encrypted) to connect, or batch-import 200 messages per load"),
                ("Platform & language filters", "Filter conversations by platform/language/compliance status; safety threads prioritized"),
            ]},
            {"group": "Replies & compliance", "color": "g2", "items": [
                ("AI native-language drafts", "Drafts in the buyer's language; sent only after your confirmation"),
                ("Art.50 + GPSR auto-embedding", "Every reply runs the combined workflow: AI identity disclosure + safety claims escalated to compliance-first replies"),
                ("Compliance status logging", "GPSR / AI Act handling status marked per conversation — auditable and traceable"),
            ]},
        ],
        "steps": [
            ("Connect platforms", "eBay one-click OAuth; other platforms paste API credentials or batch-import messages in the workbench credential center"),
            ("Unified handling", "One list for 12 platforms' conversations: filter → AI native-language draft → confirm & send"),
            ("Compliance logging", "Art.50 disclosure and GPSR events marked per thread; export audits anytime"),
        ],
        "stats": [("13", "platforms unified"), ("12", "self-serve credential platforms"), ("16", "AI reply languages"), ("100%", "of replies logged")],
        "tier_line": "Pro €49/month: unified inbox + AI customer service · Business: multi-store isolation + priority sync",
        "faqs": [
            ("Which platforms sync in real time?", "eBay connects via OAuth real-time sync; 12 platforms like Allegro/Otto/Kaufland support self-serve API credential connection (credentials AES-256 encrypted) or batch import of 200 messages per load; real-time sync rolls out per platform."),
            ("Are credentials safe?", "Sealed with AES-256 encryption; plain text is never shown in the UI or logs. You can also disconnect and delete them anytime in the workbench."),
            ("Are AI replies compliant?", "Every reply natively embeds the EU AI Act Art.50 machine-identity disclosure (in the buyer's language); product-safety triggers automatically switch to the GPSR compliance-first reply + 15-day Safety Gate reminder."),
        ],
        "related": [("ai-service", "💬 AI customer service"), ("safety-redline", "🚨 Policy safety red-line layer"), ("gpsr", "🛡️ GPSR compliance engine")],
    },

    "ad-copy": {
        "icon": "📣",
        "name": "Ad copy",
        "title": "Ad copy — generated per platform placement rules · banned-word validation · multi-language A/B variants | CrossAIO",
        "meta_desc": "One-click generation of Amazon SP/SB/SD ad titles and descriptions, plus copy for each platform's ad placements: characters and banned words hard-validated per platform rules, multi-language variants for A/B testing, no violating promo terms.",
        "eyebrow": "Capability ⑧ · The growth lever",
        "h1": "Ad copy stops flying blind — <br>platform rules are validated <em>before generation</em>",
        "sub": "One rejected ad copy burns a day's traffic. CrossAIO generates titles/descriptions against the target platform's placement rules: characters, banned words (hard bans on best/cheapest/contact info) and local phrasing are all validated upfront, outputting multiple variants for A/B campaigns.",
        "hero_note": "✓ Banned words blocked upfront · ✓ Multi-language A/B variants · ✓ Character hard validation",
        "mockup": "ad",
        "pain_title": "Three hidden traps in ad copy",
        "pains": [
            "Promo words over the line: best / cheapest / No.1 are rejected outright under most platforms' ad policies",
            "German-site ads written in English halve conversion; native copywriters you can't afford for localization",
            "Every platform's ad placement has different character rules; hand-writing 13 platform versions is pure manual drain",
        ],
        "caps": [
            {"group": "Generation", "color": "g1", "items": [
                ("Multi-platform ad copy", "Generates titles + descriptions per platform placement rules; one input, multi-platform output"),
                ("A/B variants", "Multi-language variants per output for campaign testing and picking winners"),
                ("Cultural localization", "Rewritten per market profile: Germany weights specs and certifications, France weights scenarios (same profile engine as listings)"),
            ]},
            {"group": "Compliance", "color": "g2", "items": [
                ("Banned words blocked upfront", "Promo/exaggeration/contact info blocked before generation — no wasted rejection opportunities"),
                ("Character hard validation", "Each platform's placement character limits checked item by item; over-length flagged instantly"),
            ]},
        ],
        "steps": [
            ("Enter product & platforms", "Pick target platforms and languages, give core keywords"),
            ("Validate rules & generate", "Banned-word and character pre-check → generate multiple compliant copy variants"),
            ("Campaign & pick winners", "Run A/B variants; regenerate underperformers anytime"),
        ],
        "stats": [("13", "platform rule library"), ("0", "promo-word rejection target"), ("8", "market cultural profiles"), ("11", "output languages")],
        "tier_line": "Starter from €9/month: ad copy · Pro: multi-platform matrix + A/B variants",
        "faqs": [
            ("Will it generate copy that gets rejected?", "Banned-word and character hard validation run per platform ad policy before generation; promo/exaggeration terms and contact info are blocked directly. But platform review policies change constantly — the platform's judgment is final."),
            ("Which languages are supported?", "Same engine as the listing generator: 11 output languages + 8 market cultural profiles (German/French/Italian/Spanish/Polish/Dutch/Romanian, etc.)"),
            ("How is this different from the listing generator?", "The listing generator produces the four-piece product page set; ad copy targets placement scenarios, outputting shorter, conversion-focused titles/descriptions and A/B variants."),
        ],
        "related": [("listing-generator", "📦 Listing generator"), ("matrix", "🌍 Multi-platform matrix"), ("gpsr", "🛡️ GPSR compliance engine")],
    },

    "listing-watch": {
        "icon": "📡",
        "name": "Listing monitoring daily report",
        "title": "Listing monitoring — daily automated check · instant daily report on risk escalation · compliance-drift alerts | CrossAIO",
        "meta_desc": "Daily automated check of your listings: character drift, missing compliance blocks, new reviews, declining semantic scores — tracked item by item; when risk escalates, an email daily report lands in your inbox, no daily backend patrol needed.",
        "eyebrow": "Capability ⑨ · The retention hook",
        "h1": "A listing isn't 'done' once published — <br>it gets <em>an automated check every day</em>",
        "sub": "Listings silently rewritten by platforms, compliance blocks swallowed, new reviews carrying safety words — by the time you notice, the loss has happened. CrossAIO runs a daily scheduled check of your watchlist: character drift / missing compliance / review themes / semantic score, item by item, emailing a daily report the moment risk escalates.",
        "hero_note": "✓ Daily scheduled check · ✓ Email report on risk escalation · ✓ Review-theme tracking",
        "mockup": "watch",
        "pain_title": "The cost of ignoring",
        "pains": [
            "Platforms silently rewrite listings: keywords deleted, category swapped — sales drop before you notice",
            "Safety claims in new reviews (overheating/breakage) go unseen → missed 15-day Safety Gate window",
            "Daily manual per-platform patrol is another round of manual drain, and easy to miss",
        ],
        "caps": [
            {"group": "Automated checks", "color": "g1", "items": [
                ("Daily scheduled check", "Listings on your watchlist run daily: characters / compliance block / semantic score"),
                ("Risk tiers", "Fatal (missing compliance) / High (safety words in reviews) / Medium (score decline) tiered alerts"),
                ("Email daily report", "When risk escalates, SMTP email lands directly — no backend patrol"),
            ]},
            {"group": "Fix loop", "color": "g2", "items": [
                ("Review-theme tracking", "New reviews auto-tagged by theme; safety types route straight to the GPSR compliance-first flow"),
                ("One-click rewrite", "Jump from the report straight to the review rewriting loop; re-score gains after fixes"),
            ]},
        ],
        "steps": [
            ("Add to watchlist", "Add the listings you want to watch (per platform)"),
            ("Daily check", "Scheduled task runs daily, comparing drift and risks item by item"),
            ("Daily report lands", "Risk escalation → email report → one-click jump to fix"),
        ],
        "stats": [("daily", "check frequency"), ("146", "incident-term library"), ("3", "risk tiers"), ("15-day", "Safety Gate window")],
        "tier_line": "Starter from €9/month: 5 watch slots · Pro: 50 + email report · Business: multi-store",
        "faqs": [
            ("What's monitored?", "Title/bullet character drift, GPSR compliance-block completeness, new reviews and themes, semantic-score changes — run daily and tiered."),
            ("How do I get notified?", "On risk escalation, an SMTP email daily report lands directly (SMTP must be configured in the environment); historical reports are also viewable in the workbench anytime."),
            ("How does this relate to review rewriting?", "When the report spots a safety-themed review, one click jumps into the review rewriting loop: theme detection → bullet fixes → re-score tracking — a monitor-fix loop."),
        ],
        "related": [("review-rewrite", "📈 Review rewriting loop"), ("gpsr", "🛡️ GPSR compliance engine"), ("ai-service", "💬 AI customer service")],
    },
}


# ---------------------------------------------------------------------------
# B) CHROME_EN — page chrome (keys mirror the hard-coded zh strings in _page())
# ---------------------------------------------------------------------------

CHROME_EN = {
    # Hero CTAs
    "cta_start": "Start free",
    "cta_workbench": "🚀 Open in workbench →",

    # Capabilities section
    "sec_caps_eyebrow": "Capability breakdown",
    "sec_caps_title": "{icon} What {name} can do",
    "sec_caps_sub": "Grouped by category — every item maps to a gap left by competitors",

    # How-it-works section
    "sec_steps_eyebrow": "How it works",
    "sec_steps_title": "Start in three steps",

    # Coverage / platform marquee section
    "sec_cover_eyebrow": "Coverage",
    "sec_cover_title": "One setup · live across 12 platforms",
    "sec_cover_sub": "Hover pauses the marquee · click 'Platforms' in the nav for per-platform rule details",

    # Pricing tier band
    "tier_cta": "See full pricing →",

    # FAQ section
    "sec_faq_eyebrow": "FAQ",
    "sec_faq_title": "About {name}",

    # Bottom CTA band
    "cta_band_title": "{icon} Try {name} now",
    "cta_band_sub": "Free to sign up · no credit card · no store binding",
    "cta_band_start": "Start free →",
    "cta_band_workbench": "🚀 Open in workbench",

    # Cross links
    "x_related_title": "Explore other capabilities",
    "x_rules_title": "Related platform-native rule pages",
    "rel_small": "CrossAIO capability · standalone page",
    "rules_small": "Platform-native GPSR rule page",

    # Footer
    "footer_home": "Home",
    "footer_features": "Capabilities",
    "footer_rules": "Rules reference",
    "footer_pricing": "Pricing",
    "footer_check": "free compliance check",
    "footer_skills": "open-source Skills",
    "footer_signin": "Sign in",
    "footer_tag": "CrossAIO — the all-Europe platform Listing quality + compliance engine · © 2026",

    # Platform short links
    "platform_short": {
        "allegro": "🇵🇱 Allegro rules →",
        "emag": "🇷🇴 eMAG rules →",
        "cdiscount": "🇫🇷 Cdiscount rules →",
        "otto": "🇩🇪 Otto rules →",
    },

    # /features index page
    "index_title": "Capabilities overview — 9 standalone landing pages | CrossAIO",
    "index_meta": "CrossAIO capabilities: GPSR compliance engine, Listing generator, Multi-platform matrix, Review rewriting loop, AI customer service, Unified inbox, Policy safety red-line layer, Ad copy, and Listing monitoring daily report. One standalone page per capability.",
    "index_eyebrow": "Capabilities",
    "index_h2": "Nine capabilities, nine standalone pages",
    "index_sub": "Each capability has its own pain-point analysis, capability breakdown, how-it-works walkthrough and pricing entry.",
}


# ---------------------------------------------------------------------------
# C) MOCKUP_EN — visible Chinese strings inside the 7 SVG mockup functions.
#    Keys are the exact source literals (incl. alt=/title= args of
#    _MOCKUP_SHELL.format); values are the English UI copy.
# ---------------------------------------------------------------------------

MOCKUP_EN = {
    # --- _m_gpsr -----------------------------------------------------------
    # Note: _m_gpsr already carries its own native "en" branch in
    # _M_GPSR (alt/title/risk/sub/chk/ok*/no*/block/copy/api/mon/mond), so no
    # extra keys are needed here for the gpsr mockup body.

    # --- _m_generator ------------------------------------------------------
    "generator": {
        "输入产品": "Enter product",
        "平台规则自动匹配": "Platform rules auto-matched",
        "Otto ≤70 · Allegro ≤75 · Amazon ≤200 字符 · de/pl/en": "Otto ≤70 · Allegro ≤75 · Amazon ≤200 chars · de/pl/en",
        "标题（Otto · 德语） 47/70 字符": "Title (Otto · German) 47/70 chars",
        "五点描述（5/5） · 详情 · 搜索词 已生成": "Bullet points (5/5) · Description · Search terms — generated",
        "硬校验": "Hard validation",
        "✓ 字数 ✓ 语言 ✓ 结构 ✓ GPSR 内嵌": "✓ Characters ✓ Language ✓ Structure ✓ GPSR embedded",
        "完整度评分 94/100": "Completeness score 94/100",
        "可直接复制到卖家中心 · 16 语言可选": "Copy straight to Seller Central · 16 languages available",
        "Free 每天 5 次 · Starter 起 GPSR 合规块内嵌输出": "Free 5 runs/day · Starter+ outputs embedded GPSR compliance block",
        "Listing 生成器界面": "Listing generator UI",
        "Listing 生成器": "Listing generator",
    },

    # --- _m_matrix ---------------------------------------------------------
    "matrix": {
        "✓ 已生成": "✓ generated",
        "泛欧 20+ 国": "Pan-EU 20+ countries",
        "en→多语言": "en→multi-language",
        "输入一次产品信息": "Enter product info once",
        "标题 + 关键词 + 属性（品牌/EAN/材质）": "Title + keywords + attributes (brand/EAN/material)",
        "12 平台规则内置 · 16 语言自动匹配": "12 platforms' rules built in · 16 languages auto-matched",
        "不绑店 · 独立工作台 · 结果逐平台可编辑": "No store binding · standalone workbench · per-platform results editable",
        "Allegro / eMAG / Cdiscount / Fruugo —— 主流工具覆盖率为零，CrossAIO 率先补齐": "Allegro / eMAG / Cdiscount / Fruugo — zero coverage in mainstream tools; CrossAIO fills the gap first",
        "12 平台矩阵批量生成": "12-platform matrix batch generation",
        "多平台矩阵": "Multi-platform matrix",
    },

    # --- _m_review ---------------------------------------------------------
    "review": {
        "⭐ 差评输入（1 星）": "⭐ Negative review input (1 star)",
        '"左耳三个月就断了一个角，客服': '"The hinge corner cracked after three months, support',
        '只说重新买。充电盒也过热。"': 'only told us to re-buy. The charging case also overheats."',
        "主题：材质": "Theme: material",
        "主题：过热⚠": "Theme: overheating ⚠",
        "⚠ 安全诉求 → 触发 GPSR 事件预警": "⚠ Safety claim → GPSR event alert triggered",
        "修复建议 + 五点改写": "Fix suggestions + bullet rewrite",
        '五点② 改写：增加 "增强铰链结构，': 'Bullet ② rewrite: add "reinforced hinge structure,',
        '通过 5,000 次开合测试"': 'passes 5,000 open/close tests"',
        '五点④ 改写：增加 "过热保护认证"': 'Bullet ④ rewrite: add "overheat protection certified"',
        '过热保护认证': 'overheat protection certified',
        "生成新版本": "Generate new version",
        "语义评分（Rufus / iZi 适配）": "Semantic score (Rufus / iZi ready)",
        "尺寸 8/10": "Size 8/10",
        "耐用性 5→8/10": "Durability 5→8/10",
        "安全 4→9/10": "Safety 4→9/10",
        "续航 9/10": "Battery life 9/10",
        "8 类买家问题覆盖度逐项量化 · 改写后复评追踪提升": "8 buyer-question themes scored item by item · re-scored after rewrite to track gains",
        "8 类主题定位 · 安全类差评自动走 GPSR 合规优先流程": "8-theme detection · safety reviews auto-route to the GPSR compliance-first flow",
        "差评分析与五点改写": "Negative review analysis and bullet rewrite",
        "差评改写闭环": "Review rewriting loop",
    },

    # --- _m_inbox ----------------------------------------------------------
    "inbox": {
        "统一收件箱": "Unified inbox",
        "Produit en feu ! — 安全事件": "Produit en feu ! — safety event",
        "AI 草稿 · Art.50 已披露 ✓": "AI draft · Art.50 disclosed ✓",
        "替换/退款方案 + 欧代联系方式": "Replacement/refund options + EU Rep contact",
        "确认发送": "Confirm & send",
        "编辑草稿": "Edit draft",
        "⚠ 红线拦截：fr 会话命中「安全事件」": "⚠ Red-line block: FR conversation flagged as safety event",
        "自动切换合规优先回复 · 15 天 Safety Gate 提示 · 强制转人工": "Switched to compliance-first reply · 15-day Safety Gate reminder · hand-off to a human forced",
        "统一收件箱与 Art.50 披露": "Unified inbox with Art.50 disclosure",
        "AI 客服 · 统一收件箱": "AI customer service · Unified inbox",
    },

    # --- _m_ad -------------------------------------------------------------
    "ad": {
        "📣 广告标题生成（SP 广告位）": "📣 Ad title generation (SP placement)",
        "A：Wireless Earbuds, 40H Playtime,": "A: Wireless Earbuds, 40H Playtime,",
        "IPX5 Waterproof — DE 站德语版": "IPX5 Waterproof — DE site, German version",
        "B：Kabellose Ohrhörer, 40H Akku,": "B: Kabellose Ohrhörer, 40H Akku,",
        "Wasserdicht IPX5（A/B 变体）": "Wasserdicht IPX5 (A/B variant)",
        "A/B 测试": "A/B test",
        "🚫 禁用词前置拦截": "🚫 Banned words blocked upfront",
        "→ best / 年份夸大 · 违反广告政策": "→ best / year exaggeration · violates ad policy",
        "字数：标题 ≤ 50 字符 ✓": "Characters: title ≤ 50 chars ✓",
        "联系方式 / 促销堆叠：已剔除 ✓": "Contact info / stacked promotions: removed ✓",
        "重新生成合规版": "Regenerate compliant version",
        "多平台多语言输出": "Multi-platform, multi-language output",
        "禁用词前置拦截 · 字数硬校验 · 8 市场文化画像改写": "Banned words blocked upfront · character hard validation · 8-market cultural profiles",
        "广告文案生成与禁用词拦截": "Ad copy generation with banned-word blocking",
        "广告文案生成": "Ad copy generator",
    },

    # --- _m_watch -----------------------------------------------------------
    "watch": {
        "📡 今日体检 · 12 个 Listing · 2 项风险升级": "📡 Today's check · 12 listings · 2 risk escalations",
        "每日 08:00 定时运行 · 逐项比对字数 / 合规块 / 差评 / 语义评分": "Runs daily 08:00 · checks characters / compliance block / reviews / semantic score item by item",
        "🔴 致命": "🔴 Critical",
        "Bluetooth 耳机（DE 站）": "Bluetooth headphones (DE site)",
        "GPSR 合规块消失": "GPSR compliance block missing",
        "→ 平台改写吞块 · 立即修复": "→ Platform rewrite swallowed it · fix now",
        "一键修复": "Fix in one click",
        "🟠 高": "🟠 High",
        "充电盒（FR 站）新差评": "Charging case (FR site) — new review",
        '"surchauffe（过热）"': '"surchauffe (overheating)"',
        'surchauffe（过热）': 'surchauffe (overheating)',
        "→ 命中事故词库 · GPSR 事件": "→ Hit the incident-term library · GPSR event",
        "15 天 Safety Gate 窗口内": "Inside the 15-day Safety Gate window",
        "🟢 正常 10 项": "🟢 OK — 10 items",
        "字数漂移 0 · 合规块完整": "0 character drift · compliance block intact",
        "语义评分均值 82（+1）": "Mean semantic score 82 (+1)",
        "差评主题：无线充（非安全类）": "Review theme: wireless charging (non-safety)",
        "风险升级 → SMTP 邮件日报直达 · 差评主题一键转差评改写闭环": "Risk escalation → SMTP email report lands directly · review themes route one-click to the rewriting loop",
        "Listing 每日体检与风险分级日报": "Daily listing check and risk-tiered daily report",
        "Listing 监控日报": "Listing monitoring daily report",
    },

    # --- _m_redline --------------------------------------------------------
    "redline": {
        '🚨 红线层命中：人身伤害诉求（置信度 0.97）': "🚨 Red-line hit: personal-injury claim (confidence 0.97)",
        '"充电时充电盒冒烟，孩子当时在旁边" — 自动回复已阻止': '"The charging case smoked while charging, the child was right next to it" — auto-reply blocked',
        '充电时充电盒冒烟，孩子当时在旁边': 'The charging case smoked while charging, the child was right next to it',
        "1 · 拦截自动回复": "1 · Block auto-reply",
        "消息标记为安全事件": "Message tagged as safety event",
        "不走 AI 草稿流程": "Bypasses the AI draft flow",
        "2 · 安抚 + 转人工": "2 · Reassure + hand off to a human",
        "安抚话术 · 留证要点提示": "Reassuring script · evidence-check prompts",
        "订单号 / 消息原文 / 截图": "Order number / original message / screenshots",
        "3 · GPSR 事件流程": "3 · GPSR event flow",
        "停售评估建议": "Stop-sale assessment advice",
        "15 天 Safety Gate 提示": "15-day Safety Gate reminder",
        "留证时间线（可审计）": "Evidence timeline (auditable)",
        "14:02 识别拦截 → 14:02 转人工 → 14:15 GPSR 流程开启 → 上报倒计时 D-15": "14:02 detected & blocked → 14:02 handed off → 14:15 GPSR flow started → reporting countdown D-15",
        "✓ 红线回复同样内嵌 AI Act Art.50 披露 · 合规层无死角 · 高风险 100% 转人工": "✓ Red-line replies also embed AI Act Art.50 disclosure · compliance layer with no blind spots · 100% of high-risk messages handed to humans",
        "安全红线拦截流程": "Safety red-line block flow",
        "政策安全红线层": "Policy safety red-line layer",
    },
}
