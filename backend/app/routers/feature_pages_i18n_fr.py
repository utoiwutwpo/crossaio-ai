# -*- coding: utf-8 -*-
"""Données françaises (fr) pour les pages de fonctionnalités — /fr/features/*.

Module de données pur, sans logique ni route. Trois blocs au sommet :
  - FEATURES_FR : même structure que FEATURES (feature_pages.py), 9 pages
  - CHROME_FR   : textes de la charte de page (boutons, sections, footer…)
  - MOCKUP_FR   : littéraux visibles à contenu chinois dans les maquettes SVG

Conventions terminologiques :
  représentant UE (conforme au _M_GPSR["fr"] interne et au référentiel) ;
  bloc de conformité ; avertissements de sécurité en langue locale ; puces ;
  mots-clés back-end ; limites strictes de caractères ; backfill ;
  déréférencement ; boîte de réception unifiée ; atelier.
"""

# ---------------------------------------------------------------------------
# A) FEATURES_FR — 9 pages, structure identique à FEATURES
# ---------------------------------------------------------------------------

FEATURES_FR = {
    "gpsr": {
        "icon": "🛡️",
        "name": "Moteur de conformité GPSR",
        "title": "Moteur de conformité GPSR — catégories CE · représentant UE + avertissements de sécurité en langue locale · bloc de conformité en un clic | CrossAIO",
        "meta_desc": "Le GPSR (UE 2023/988) est obligatoire : identification automatique des catégories CE et des directives applicables, génération du bloc de conformité avec représentant UE et avertissements en 16 langues, blocage dur sur l'arbre d'attributs, surveillance 7×24 et alertes incidents de sécurité. Vérification gratuite.",
        "eyebrow": "Fonctionnalité ① · 1re raison de payer",
        "h1": "Sans un bloc de conformité, <br>votre listing peut être<em> entièrement déréférencé</em>",
        "sub": "Le moteur de conformité CrossAIO : identification automatique des catégories CE → appariement des directives applicables → représentant UE + avertissements de sécurité en langue locale → génération du bloc de conformité GPSR prêt à coller ou à backfiller via l'API. Une raison de payer portée par la peur : un seul manquement coûte bien plus qu'un an d'abonnement.",
        "hero_note": "✓ La vérification gratuite signale d'abord les risques · ✓ Starter débloque le bloc de conformité complet · ✓ Aucune boutique à connecter",
        "mockup": "gpsr",
        "pain_title": "Le coût de l'absence de GPSR",
        "pains": [
            "L'UE 2023/988 est entrée en vigueur obligatoire en décembre 2024 : tout produit non alimentaire sur le marché UE exige un représentant UE + des avertissements de sécurité en langue locale ; un élément manqué suffit au déréférencement",
            "SellSafe ne gère que les documents de conformité, pas les textes du listing ; les outils de rédaction (H10…) ignorent totalement la conformité — aucun des deux ne résout le « bloc de conformité dans le listing »",
            "Les avertissements traduits automatiquement ne sont pas reconnus par les autorités : les avertissements en allemand, français, polonais, roumain, etc. doivent être des « formulations du marché » dans la langue visée, pas une traduction littérale",
            "Les infos représentant UE sont dispersées entre Excel et fils de discussion : 30 % des listings les oublient ou les remplissent mal",
        ],
        "caps": [
            {"group": "Génération du bloc de conformité", "color": "g1", "items": [
                ("Identification automatique des catégories CE", "base de règles de 7 catégories (jouets / électrique / EPI / bébé-enfant / contact alimentaire…), appariement automatique des directives applicables"),
                ("Bloc de conformité représentant UE + avertissements", "la ligne représentant UE remplace automatiquement le responsable par défaut du registre ; avertissements natifs dans 7 langues, non littéraux"),
                ("En-tête natif de la plateforme", "en-têtes en langue locale — Allegro en polonais / eMAG en roumain — à backfiller directement dans les champs correspondants"),
            ]},
            {"group": "Blocage dur et surveillance", "color": "g2", "items": [
                ("Blocage dur sur l'arbre d'attributs", "un contrôle aussi dur que l'audit plateforme : chiffre de contrôle EAN erroné, matière manquante → ready_to_list = false"),
                ("Surveillance 7×24 + rapport de risque quotidien", "vérification quotidienne planifiée des listings en ligne, re-vérification automatique après mise à jour des règles, envoi du rapport de risque quotidien"),
                ("Alerte incidents de sécurité", "un message acheteur évoque sécurité / blessure corporelle → rappel de signalement Safety Gate sous 15 jours"),
            ]},
        ],
        "steps": [
            ("Saisissez les infos produit", "titre + mots-clés + catégorie, sans boutique connectée, résultat de vérification en 30 secondes"),
            ("Identification automatique catégorie et directive", "appariement dans la base des 7 règles CE des directives applicables et des exigences d'avertissements ; la version gratuite signale d'abord la liste des problèmes"),
            ("Débloquez le bloc et backfillez", "Starter débloque le bloc de conformité complet : ligne représentant UE + avertissements en langue locale + en-tête natif plateforme, à coller ou à backfiller via l'API"),
        ],
        "stats": [("7", "catégories de règles CE"), ("7", "langues natives d'avertissement"), ("13", "plateformes de backfill"), ("15 jours", "rappel de signalement Safety Gate")],
        "tier_line": "Free : la vérification signale seulement les problèmes · Starter €29/mois : bloc complet + contrôle de l'arbre d'attributs + surveillance 7×24",
        "faqs": [
            ("Quelle différence entre la vérification gratuite et le bloc payant ?", "La vérification gratuite vous dit ce qui manque et comment vous serez sanctionné (liste des problèmes) ; dès Starter, génération du bloc de conformité complet prêt à coller (représentant UE + avertissements + en-tête natif plateforme), avec backfill API vers 12 plateformes."),
            ("Les avertissements sont-ils traduits automatiquement ?", "Non. Les avertissements en allemand, français, italien, espagnol, polonais, roumain et anglais (7 langues) sont des formulations natives du marché dans la langue visée (contexte ProdSG en Allemagne / DGCCRF en France), pas une traduction littérale. Pour les autres langues, une ligne en anglais est produite et clairement signalée, sans placeholder vide."),
            ("D'où viennent les infos représentant UE ?", "Vous gérez plusieurs représentants UE dans le registre et en définissez un par défaut ; lors de la génération du bloc, le placeholder est remplacé automatiquement, sans ressaisie manuelle."),
        ],
        "related": [("listing-generator", "📦 Générateur de listings"), ("matrix", "🌍 Matrice multi-plateformes"), ("safety-redline", "🚨 Couche de lignes rouges de sécurité")],
    },

    "listing-generator": {
        "icon": "📦",
        "name": "Générateur de listings",
        "title": "Générateur de listings — limites strictes de caractères par plateforme · puces + description + mots-clés back-end · 16 langues | CrossAIO",
        "meta_desc": "Une saisie pour générer titre / puces / description / mots-clés back-end, limites strictes Otto 70 / Allegro 75 / Amazon 200, notation automatique et signalement des non-conformités, localisation en 16 langues. Gratuit : 5 générations par jour.",
        "eyebrow": "Fonctionnalité ② · point d'entrée",
        "h1": "Une seule saisie, <br>un listing écrit selon les règles de chaque plateforme<em> prêt à passer l'audit</em>",
        "sub": "Titre + puces + description + mots-clés back-end, générés selon les règles de caractères, de langue et de structure des 12 plateformes. Après génération : notation automatique et signalement des non-conformités — pas une « suggestion à remplir », mais un contrôle dur comme l'audit plateforme.",
        "hero_note": "✓ 5 générations gratuites par jour · ✓ Aucune boutique à connecter · ✓ Copier-coller, c'est mis en ligne",
        "mockup": "generator",
        "pain_title": "Le travers des outils de rédaction",
        "pains": [
            "Un titre écrit par une IA générique dépasse la limite Otto de 70 caractères / Allegro de 75 caractères, et se fait refuser net par la plateforme",
            "On écrit d'abord, puis on traduit : les puces traduites ne sonnent pas comme « la formulation d'un vendeur dans la langue », et le taux de conversion chute de moitié",
            "La qualité dépend du contrôle visuel humain ; aucun outil ne contrôle en dur selon les règles plateforme dès la génération",
            "La description et les mots-clés back-end ne respectent pas la structure attendue, un frein invisible au référencement",
        ],
        "caps": [
            {"group": "Génération", "color": "g1", "items": [
                ("Titre / puces / description / mots-clés back-end", "le pack complet en une seule génération, organisé selon la structure plateforme, pas un simple collage"),
                ("Localisation en 16 langues", "en/de/fr/es/it/pl/ro/nl/cs/sk/hu/bg/sv…, appariement automatique selon la plateforme"),
                ("Textes publicitaires", "dès Pro : titres et arguments pour les emplacements publicitaires internes, mots-clés issus de la même source que le listing"),
            ]},
            {"group": "Contrôle", "color": "g2", "items": [
                ("Limites strictes de caractères", "les limites Otto 70 / Allegro 75 / Amazon 200 sont des règles dures intégrées : tout dépassement est signalé"),
                ("Score de complétude", "notation automatique après génération, signalement des non-conformités et champs manquants pour détecter les problèmes avant mise en ligne"),
                ("Règles de structure plateforme", "structure des titres, nombre de puces, format des mots-clés back-end, maintenus en continu selon la documentation du centre vendeur de chaque plateforme"),
            ]},
        ],
        "steps": [
            ("Saisissez les infos produit", "nom du produit + mots-clés principaux, et éventuellement marque / EAN / matière"),
            ("Choisissez la plateforme et générez", "ajustement fin sur une plateforme ou matrice en masse, langue et règles appariées automatiquement"),
            ("Contrôlé puis mis en ligne", "une fois les limites de caractères et le score de complétude validés, copiez-collez dans le centre vendeur"),
        ],
        "stats": [("13", "règles plateforme intégrées"), ("16", "langues de génération"), ("5×/jour", "quotas gratuits"), ("90%", "gain de temps moyen sur l'opération")],
        "tier_line": "Free : 5 par jour · Starter €29/mois : 50 par jour + bloc de conformité GPSR intégré · Pro €49/mois : 200 par jour + textes publicitaires",
        "faqs": [
            ("Quelle différence avec une rédaction directe dans ChatGPT ?", "ChatGPT ne connaît pas les règles dures Otto 70 caractères, Allegro 75 caractères, ni ce que le GPSR exige d'intégrer. CrossAIO transforme les règles des 12 plateformes en contrôle dur : généré = conforme, sans allers-retours."),
            ("Comment garantir la qualité du listing généré ?", "Notation automatique après génération : caractères, langue, contraintes de structure, contrôle point par point avec signalement des non-conformités ; l'arbre d'attributs applique un blocage dur au chiffre de contrôle EAN, pour repérer avant mise en ligne les éléments qui seraient refusés."),
            ("Faut-il connecter ma boutique ?", "Non. CrossAIO est un atelier indépendant, prêt à l'emploi dès l'inscription ; copiez-collez le résultat dans le centre vendeur de n'importe quelle plateforme."),
        ],
        "related": [("matrix", "🌍 Matrice multi-plateformes"), ("gpsr", "🛡️ Moteur de conformité GPSR"), ("review-rewrite", "📈 Réécriture d'avis négatifs")],
    },

    "matrix": {
        "icon": "🌍",
        "name": "Matrice multi-plateformes",
        "title": "Matrice multi-plateformes — une saisie, localisation en masse sur 12 plateformes · concurrence à couverture zéro sur Allegro / eMAG / Cdiscount | CrossAIO",
        "meta_desc": "Une saisie → listings localisés en masse sur 12 plateformes : Amazon UE+US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com. Atelier indépendant, sans connecter de boutique.",
        "eyebrow": "Fonctionnalité ③ · levier d'échelle",
        "h1": "Une saisie, <br>localisation en masse sur <em>12 plateformes</em>",
        "sub": "Amazon Europe + US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com — toutes les règles intégrées, langues appariées automatiquement. H10 ignore les plateformes locales, Marqetir vous force à connecter votre boutique : nous ne faisons ni l'un ni l'autre.",
        "hero_note": "✓ Atelier indépendant sans boutique · ✓ Couverture des plateformes secondaires vers l'Europe de l'Est / du Sud · ✓ Résultats modifiables plateforme par plateforme",
        "mockup": "matrix",
        "pain_title": "Le vrai coût de l'expansion",
        "pains": [
            "Chaque nouvelle plateforme exige de réapprendre les règles : caractères, langue, attributs de catégorie, champs de conformité, tout diffère",
            "H10 ne fait que l'Amazon ; Marqetir / SellerCloud exigent de connecter l'API de la boutique pour fonctionner, avec un doute sur la sécurité des données",
            "Allegro (Pologne), eMAG (Roumanie), Cdiscount (France) ont une couverture nulle dans les outils grand public, alors que ce sont les marchés à la croissance la plus rapide d'Europe de l'Est / du Sud",
            "Traduire et coller plateforme par plateforme, un SKU sur toutes les plateformes, consume une journée entière",
        ],
        "caps": [
            {"group": "Génération matrice", "color": "g1", "items": [
                ("Génération en masse sur 12 plateformes", "une saisie → résultats localisés sur 12 plateformes, modifiables, copiables et backfillables plateforme par plateforme"),
                ("Appariement automatique des langues", "pl/de/fr/ro/nl… choisis automatiquement selon la plateforme, sans réglage manuel"),
                ("Bloc de conformité embarqué", "chaque listing sort avec son bloc de conformité GPSR (dès Starter), pour ne rien oublier en étendant"),
            ]},
            {"group": "Synergie plateformes secondaires", "color": "g3", "items": [
                ("Moteur de croissance est-européen", "Allegro (Pologne / Tchéquie / Slovaquie / Hongrie) + eMAG (Roumanie / Hongrie / Bulgarie) — des marchés à couverture concurrentielle nulle"),
                ("Comblement Europe du Sud / de l'Ouest", "Cdiscount (France) + Fruugo (20+ pays européens) pris en charge en priorité"),
                ("Pages de règles entièrement publiques", "les détails des règles des 6 plateformes maîtrisées sont des pages de destination gratuites, base de règles transparente et consultable"),
            ]},
        ],
        "steps": [
            ("Saisissez une seule fois les infos produit", "nom + mots-clés + attributs, une même saisie pour toutes les plateformes"),
            ("Cochez les plateformes cibles", "ajustement fin mono-plateforme ou sélection des 13, règles et langues appariées automatiquement"),
            ("Export / backfill en masse", "copier-coller plateforme par plateforme, ou backfill via la couche d'adaptation API (Amazon SP-API / eBay REST)"),
        ],
        "stats": [("13", "règles plateforme intégrées"), ("16", "langues de génération"), ("0", "boutiques à connecter"), ("4", "plateformes secondaires à couverture concurrentielle nulle")],
        "tier_line": "Free : essai mono-plateforme · Pro €49/mois : matrice 3 plateformes · Business €149/mois : matrice illimitée + support prioritaire",
        "faqs": [
            ("Quelles sont les 12 plateformes ?", "Amazon Europe + US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com. Dont Cdiscount, Allegro, eMAG, Fruugo à couverture nulle chez les concurrents."),
            ("Quelle est la qualité de la génération en matrice et des petites langues ?", "Chaque plateforme est contrôlée en dur selon les règles de caractères / langue / structure de sa documentation centre vendeur ; les petites langues sont appariées automatiquement sur la langue locale, les avertissements GPSR en formulation native."),
            ("Vraiment sans connecter de boutique ?", "Oui. La génération en matrice se déroule entièrement dans l'atelier CrossAIO. Seul le « backfill API » exige que vous fournissiez les identifiants développeur de la plateforme (Amazon SP-API / eBay OAuth), stockés dans vos propres variables d'environnement."),
        ],
        "related": [("listing-generator", "📦 Générateur de listings"), ("gpsr", "🛡️ Moteur de conformité GPSR"), ("ai-service", "💬 Service client IA")],
    },

    "review-rewrite": {
        "icon": "📈",
        "name": "Boucle de réécriture d'avis",
        "title": "Réécriture d'avis négatifs — identification de 8 thèmes · correctifs des puces · score sémantique (adaptation Rufus / iZi) | CrossAIO",
        "meta_desc": "Identification automatique du thème des avis négatifs (8 catégories), génération de correctifs des puces et réécriture ; score de couverture sémantique des 8 types de questions acheteurs, optimisé pour les assistants d'achat IA Rufus / iZi. Usage hebdomadaire, impact direct sur la conversion.",
        "eyebrow": "Fonctionnalité ④ · raison de renouvellement",
        "h1": "Un avis négatif n'est pas une fin, <br>c'est une<em> consigne de réécriture</em> pour votre listing",
        "sub": "Identification automatique du thème des avis négatifs (taille trop grande / autonomie insuffisante / emballage abîmé…, 8 catégories), génération de correctifs des puces et réécriture des arguments correspondants ; puis un score sémantique vérifie si votre listing répond aux 8 types de questions les plus fréquentes des acheteurs — pour que Rufus, iZi et autres conseillers IA recommandent aussi votre produit.",
        "hero_note": "✓ Usage hebdomadaire · ✓ les correctifs génèrent directement de nouvelles puces · ✓ essai gratuit du score sémantique",
        "mockup": "review",
        "pain_title": "La donnée des avis négatifs gaspillée",
        "pains": [
            "Les avis négatifs sont seulement « répondus », jamais « exploités » : les thèmes sont épars dans les commentaires, personne ne les transforme systématiquement en correctifs du listing",
            "Les assistants d'achat IA comme Rufus (Amazon), iZi (Allegro) commencent à décider à la place des acheteurs : ce que votre listing ne répond pas, l'IA le répond par un concurrent",
            "Réécrire les puces à la main relève du feeling, aucun outil ne quantifie « à combien de types de questions acheteurs ce listing répond »",
            "Les avis négatifs mêlent des demandes de sécurité (casse / surchauffe / risque d'étouffement), que le service client classique laisse passer à côté de l'obligation de signalement GPSR des incidents de sécurité",
        ],
        "caps": [
            {"group": "Boucle avis négatifs → listing", "color": "g1", "items": [
                ("Identification de 8 thèmes", "taille / autonomie / matière / emballage / logistique / soupçon de contrefaçon / difficulté d'installation / demande de sécurité, catégorisés automatiquement"),
                ("Correctifs des puces + réécriture", "des correctifs sont générés par thème, les puces correspondantes sont réécrites directement, pour une nouvelle version prête à mettre en ligne"),
                ("Alerte demandes de sécurité", "un avis négatif à thème sécurité déclenche l'alerte incident GPSR (rappel Safety Gate sous 15 jours)"),
            ]},
            {"group": "Score sémantique", "color": "g3", "items": [
                ("Couverture des 8 types de questions acheteurs", "quantification de la couverture de vos réponses aux questions courantes des acheteurs, avec le détail des lacunes par catégorie"),
                ("Adaptation Rufus / iZi", "structure sémantique optimisée pour les assistants d'achat IA, pour que le conseiller IA cite vos arguments"),
                ("Suivi itératif", "nouvelle évaluation après réécriture, quantification du gain de couverture apporté par chaque correctif"),
            ]},
        ],
        "steps": [
            ("Importez les avis négatifs", "collez avis / commentaires, ou sélectionnez la plateforme pour un rapatriement automatique (en développement : connexion eBay)"),
            ("Identification du thème + correctifs", "catégorisation des 8 thèmes, génération des correctifs et réécriture des puces correspondantes"),
            ("Réévaluation et mise en ligne", "le score sémantique réévalue la couverture, la nouvelle version remplace directement l'ancienne"),
        ],
        "stats": [("8", "types de thèmes d'avis négatifs"), ("8", "dimensions de couverture sémantique"), ("2", "plateformes de conseil IA adaptées"), ("hebdo", "fréquence d'usage typique")],
        "tier_line": "Free : essai du score sémantique · Pro €49/mois : boucle de réécriture + textes publicitaires · Business : surveillance en masse",
        "faqs": [
            ("D'où viennent les données des avis négatifs ?", "Pour l'instant, collez manuellement avis / commentaires ; une fois eBay connecté, rapatriement automatique après autorisation. Toute l'analyse se déroule dans votre compte CrossAIO, sans partage avec des tiers."),
            ("C'est quoi, le score sémantique ?", "Il prend les 8 types de questions les plus courantes des acheteurs (taille, autonomie, matière, sécurité…) comme dimensions, et quantifie la couverture de vos réponses par catégorie. Les conseillers IA comme Rufus, iZi filtrent pour les acheteurs selon une logique voisine."),
            ("Les avis négatifs à thème sécurité sont-ils traités à part ?", "Oui. Tout avis évoquant sécurité / blessure corporelle déclenche le flux de conformité prioritaire : consignes GPSR + rappel de signalement Safety Gate sous 15 jours, jamais traité comme un simple avis."),
        ],
        "related": [("gpsr", "🛡️ Moteur de conformité GPSR"), ("listing-generator", "📦 Générateur de listings"), ("safety-redline", "🚨 Couche de lignes rouges de sécurité")],
    },

    "ai-service": {
        "icon": "💬",
        "name": "Service client IA + Art.50",
        "title": "Service client IA — divulgation Art.50 de l'AI Act nativement intégrée · connexion eBay · boîte de réception unifiée multi-plateforme | CrossAIO",
        "meta_desc": "Webhook des messages acheteurs → brouillon de réponse par LLM → chaque réponse intègre nativement la divulgation Art.50 de l'EU AI Act (obligatoire dès 2026-08-02), filtre rouge GPSR, boîte de réception unifiée multi-plateforme. Les concurrents vendent la réponse rapide, nous vendons la non-infraction.",
        "eyebrow": "Fonctionnalité ⑤ · entrée d'acquisition conforme",
        "h1": "Chaque réponse IA <br>intègre nativement la <em>divulgation Art.50 de l'AI Act</em>",
        "sub": "Après autorisation du vendeur eBay, les messages acheteurs arrivent par webhook dans CrossAIO, l'IA génère un brouillon de réponse que vous validez avant envoi ; chaque réponse intègre nativement la divulgation d'identité machine de l'EU AI Act Art.50 (entrée en vigueur obligatoire le 2026-08-02, amende jusqu'à 15 M€ ou 3 % du chiffre d'affaires mondial). Divulgation en 16 langues, pilotée depuis une boîte de réception unifiée multi-plateforme.",
        "hero_note": "✓ Envoi seulement après votre validation · ✓ divulgation Art.50 en 16 langues · ✓ aucun outil de service client tiers requis",
        "mockup": "inbox",
        "pain_title": "L'angle mort conformité des outils de service client",
        "pains": [
            "Le service client IA officiel d'Amazon / eBay ne résout que la « réponse rapide », sans aucune couche de conformité AI Act",
            "Responso / eDesk / BaseLinker n'ont à ce jour aucune divulgation Art.50 de l'AI Act intégrée — alors qu'elle devient obligatoire le 2026-08-02",
            "Les demandes de sécurité dans les messages acheteurs (produit qui casse / surchauffe / ingestion par un enfant) sont traitées en consultation ordinaire avec une réponse automatique instantanée, en passant à côté de l'obligation de signalement GPSR",
            "Les messages acheteurs des 12 plateformes sont dispersés dans chaque back-office, des réponses incohérentes, et un état de conformité impossible à suivre",
        ],
        "caps": [
            {"group": "Réponse et divulgation", "color": "g1", "items": [
                ("Divulgation Art.50 nativement intégrée", "chaque réponse IA porte automatiquement la divulgation d'identité machine en 16 langues, formulation choisie selon la langue de l'acheteur"),
                ("Brouillon de réponse par LLM", "réponse générée en contexte, envoyée seulement après votre validation, traçable de bout en bout"),
                ("Filtre rouge GPSR", "un message acheteur évoque sécurité / blessure corporelle → bascule en « réponse prioritaire de conformité » : consignes GPSR + rappel Safety Gate sous 15 jours"),
            ]},
            {"group": "Connexion et boîte de réception", "color": "g2", "items": [
                ("Connexion webhook eBay", "après autorisation OAuth2, messages acheteurs en temps réel, sans outil tiers"),
                ("Boîte de réception unifiée multi-plateforme", "gestion unifiée des conversations de 12 plateformes, import manuel + rapatriement API, état GPSR / AI Act marqué conversation par conversation"),
                ("Données privées", "toutes les données restent dans votre compte CrossAIO, identifiants stockés dans vos propres variables d'environnement"),
            ]},
        ],
        "steps": [
            ("Autorisez la connexion", "autorisation OAuth2 eBay, webhook des messages acheteurs vers CrossAIO (les autres plateformes : import manuel)"),
            ("L'IA génère le brouillon", "le LLM rédige la réponse dans la langue de l'acheteur, avec divulgation Art.50 intégrée ; une demande de sécurité déclenche la réponse prioritaire de conformité"),
            ("Validez et envoyez", "vous validez dans la boîte de réception unifiée avant envoi ; l'état GPSR / AI Act de chaque conversation est traçable et auditable"),
        ],
        "stats": [("16", "langues de divulgation Art.50"), ("13", "plateformes de la boîte unifiée"), ("15 M€", "amende maximale AI Act"), ("2026-08", "date d'entrée en vigueur Art.50")],
        "tier_line": "Pro €49/mois : service client IA + boîte de réception unifiée · Business : multi-boutiques + support prioritaire",
        "faqs": [
            ("C'est quoi, la divulgation Art.50 de l'AI Act ?", "L'article 50 de l'EU AI Act exige de divulguer l'identité machine lors d'une interaction avec une IA, entrée en vigueur obligatoire le 2026-08-02, amende jusqu'à 15 M€ ou 3 % du CA mondial. CrossAIO intègre nativement, dans chaque réponse IA, un texte de divulgation choisi selon la langue de l'acheteur."),
            ("L'IA envoie-t-elle directement aux acheteurs ?", "Non. L'IA ne génère qu'un brouillon, envoyé seulement après votre validation dans la boîte unifiée ; les demandes de sécurité basculent de force en « réponse prioritaire de conformité » avec rappel de l'obligation de signalement sous 15 jours."),
            ("Outre eBay, quelles plateformes puis-je connecter ?", "eBay est connecté (webhook temps réel) ; les 12 autres plateformes supportent l'import manuel + la couche d'adaptation API dans la boîte unifiée, avec connexion temps réel ouverte progressivement."),
        ],
        "related": [("safety-redline", "🚨 Couche de lignes rouges de sécurité"), ("gpsr", "🛡️ Moteur de conformité GPSR"), ("matrix", "🌍 Matrice multi-plateformes")],
    },

    "safety-redline": {
        "icon": "🚨",
        "name": "Couche de lignes rouges de sécurité",
        "title": "Couche de lignes rouges de sécurité — détection menaces / chantage · réponse prioritaire de conformité · signalement Safety Gate sous 15 jours | CrossAIO",
        "meta_desc": "Détection automatique des menaces, du chantage et des demandes de blessure corporelle : apaisement + transfert à un agent humain traçable, pas de réponse automatique bête ; déclenche le flux incident GPSR (rappel Safety Gate sous 15 jours) + divulgation AI Act. La conformité avant l'efficacité.",
        "eyebrow": "Fonctionnalité ⑥ · ligne de fond",
        "h1": "Menaces, chantage, demandes de blessure : <br><em>la conformité d'abord</em>, jamais de réponse automatique bête",
        "sub": "Quelle que soit l'efficacité du service client IA, face à une menace, un chantage ou une demande de blessure corporelle, on ne répond pas en automatique instantanée. La couche de lignes rouges CrossAIO détecte automatiquement les messages à haut risque : apaisement + transfert à un agent humain + traçabilité, et déclenche le flux incident GPSR (rappel Safety Gate sous 15 jours) et la divulgation AI Act — les concurrents vendent l'efficacité, nous protégeons votre ligne de fond conformité.",
        "hero_note": "✓ transfert forcé à un agent humain pour les messages à haut risque · ✓ rappel automatique du délai de signalement · ✓ traçabilité auditable de bout en bout",
        "mockup": "redline",
        "pain_title": "Le coût de la réponse automatique bête",
        "pains": [
            "Un service client IA purement efficace répond poliment et instantanément à un message « produit en feu / ingestion par un enfant », et rate la fenêtre de signalement obligatoire Safety Gate de 15 jours",
            "Un message de menace ou de chantage est traité comme un litige ordinaire, sans traçabilité, et l'on ne dispose d'aucune chaîne de preuves en cas de litige / recours plateforme",
            "Après montée en charge émotionnelle, un agent différent reprend n'importe comment, des discours incohérents, et un petit litige dégénère en réclamation plateforme",
            "Aucun outil de service client n'embarque le flux GPSR de traitement des incidents de sécurité (évaluation du déréférencement, signalement, évaluation du rappel)",
        ],
        "caps": [
            {"group": "Détection et filtrage", "color": "g2", "items": [
                ("Détection des messages à haut risque", "menace / chantage / blessure corporelle / demande de sécurité enfant, classés et marqués automatiquement, réponse automatique interdite"),
                ("Apaisement + transfert à un agent humain", "génération d'un discours d'apaisement et transfert à un humain, avec rappel des points à tracer (capture / numéro de commande / texte original)"),
                ("Réponse prioritaire de conformité", "l'incident de sécurité bascule en réponse consignes GPSR : conseil d'arrêt de vente + rappel Safety Gate sous 15 jours"),
            ]},
            {"group": "Traçabilité et signalement", "color": "g3", "items": [
                ("Traçabilité de bout en bout", "historique complet de la conversation : résultat de détection, action de traitement, contenu de la réponse, auditable"),
                ("Rappel Safety Gate", "rappel automatique du délai de signalement de 15 jours, avec la checklist des points à soumettre à Safety Gate"),
                ("Conformité Art.50 intacte", "les réponses de la couche rouge intègrent aussi la divulgation AI Act, la couche conformité n'a aucun angle mort"),
            ]},
        ],
        "steps": [
            ("Le message entre dans la couche rouge", "tout message acheteur passe d'abord par la détection haut risque (menace / chantage / blessure / sécurité enfant)"),
            ("Transfert forcé à un humain et traçabilité", "le message à haut risque échappe à la réponse auto : discours d'apaisement + transfert à un humain + rappel de traçabilité"),
            ("Flux incident GPSR", "incident de sécurité confirmé → conseil d'arrêt de vente + rappel Safety Gate sous 15 jours → historique tracé de bout en bout"),
        ],
        "stats": [("15 jours", "délai de signalement Safety Gate"), ("4", "types de messages à haut risque"), ("100%", "transfert forcé à un humain"), ("bout en bout", "traçabilité auditable")],
        "tier_line": "Pro €49/mois et plus, couche rouge incluse · synergie avec le service client IA et la boîte unifiée",
        "faqs": [
            ("Qu'est-ce qu'un message à haut risque ?", "Quatre catégories : menace (intimidation physique / juridique), chantage (chantage par avis négatif / signalement), demande de blessure corporelle liée au produit (incendie / casse / allergie), demande de sécurité enfant (ingestion / étouffement). Toute catégorisation déclenche le blocage de la réponse automatique."),
            ("Que se passe-t-il concrètement après le filtrage ?", "Génération d'un discours d'apaisement, transfert à un agent humain, rappel des points à tracer ; si un incident de sécurité est confirmé, flux GPSR : conseil d'arrêt de vente, rappel Safety Gate sous 15 jours. Toutes les actions sont tracées."),
            ("Quel est le lien avec le service client IA ?", "La couche rouge est l'étage amont du service client IA : tous les messages passent d'abord par la détection haut risque, seuls les messages ordinaires entrent dans le flux de brouillon IA. Les deux étages fonctionnent dans la boîte unifiée."),
        ],
        "related": [("ai-service", "💬 Service client IA"), ("gpsr", "🛡️ Moteur de conformité GPSR"), ("review-rewrite", "📈 Réécriture d'avis négatifs")],
    },

    "inbox": {
        "icon": "📥",
        "name": "Boîte de réception unifiée",
        "title": "Boîte de réception unifiée — messages acheteurs de 12 plateformes au même endroit · réponses IA dans la langue maternelle · état de conformité marqué conversation par conversation | CrossAIO",
        "meta_desc": "Regroupe au même endroit les messages acheteurs d'Amazon / eBay / Allegro / Otto / Kaufland et 12 plateformes : l'IA rédige les réponses dans la langue maternelle de l'acheteur, divulgation Art.50 et consignes sécurité GPSR intégrées automatiquement, état de conformité tracé conversation par conversation.",
        "eyebrow": "Fonctionnalité ⑦ · remède au goulot d'échelle",
        "h1": "Les messages acheteurs de 12 plateformes, <br>une seule boîte pour <em>tout gérer</em>",
        "sub": "Un vendeur transfrontalier européen gère en moyenne 6+ plateformes en parallèle, les messages acheteurs sont épars dans les back-offices, en des langues variées. La boîte de réception unifiée CrossAIO regroupe les conversations de 12 plateformes au même endroit : synchro temps réel eBay via OAuth, connexion par identifiants ou import en masse pour les autres ; le brouillon IA est rédigé dans la langue maternelle de l'acheteur, avec divulgation Art.50 + consignes sécurité GPSR intégrées automatiquement.",
        "hero_note": "✓ synchro temps réel eBay · ✓ identifiants en libre-service / import pour 12 plateformes · ✓ réponses conformes et tracées",
        "mockup": "inbox",
        "pain_title": "La triple dépense du service client multi-plateforme",
        "pains": [
            "Se connecter plateforme par plateforme pour lire les messages : 6 back-offices par jour, un seul message oublié = avis négatif ou retour",
            "Des messages en allemand / polonais / roumain incompréhensibles, une réponse par traduction automatique qui convertit mal et manque de politesse",
            "Les outils de service client IA ne connaissent pas les règles plateforme : divulgation Art.50 absente, demandes de sécurité traitées en consultation ordinaire",
            "Quelle conversation a été traitée, quelle a déclenché un incident de sécurité — dispersé par plateforme, impossible à auditer",
        ],
        "caps": [
            {"group": "Regroupement et synchro", "color": "g1", "items": [
                ("Synchro temps réel eBay", "après autorisation OAuth2, webhook des messages acheteurs en temps réel, la réponse IA peut être envoyée directement"),
                ("Identifiants / import en libre-service pour 12 plateformes", "collez les identifiants API (chiffrement AES-256) pour Allegro / Otto / Kaufland…, ou import en masse de 200 messages par lot"),
                ("Filtres plateforme et langue", "filtrez les conversations par plateforme / langue / état de conformité, priorisez les demandes de sécurité"),
            ]},
            {"group": "Réponse et conformité", "color": "g2", "items": [
                ("Brouillon IA en langue maternelle", "brouillon rédigé dans la langue de l'acheteur, envoyé seulement après votre validation"),
                ("Art.50 + GPSR intégrés automatiquement", "chaque réponse passe par le workflow combiné : divulgation d'identité IA + escalade des demandes de sécurité en réponse prioritaire de conformité"),
                ("État de conformité tracé", "état de traitement GPSR / AI Act marqué conversation par conversation, auditable et traçable"),
            ]},
        ],
        "steps": [
            ("Connectez les plateformes", "eBay en un clic OAuth ; les autres plateformes : collez les identifiants API ou importez les messages en masse depuis le centre d'identifiants de l'atelier"),
            ("Traitement unifié", "une liste pour les conversations des 12 plateformes : filtre → brouillon IA en langue maternelle → validation et envoi"),
            ("Traçabilité conformité", "divulgation Art.50 et incidents GPSR marqués conversation par conversation, exportables à tout moment pour audit"),
        ],
        "stats": [("13", "plateformes connectées en unifié"), ("12", "identifiants en libre-service"), ("16", "langues de réponse IA"), ("100%", "réponses conformes et tracées")],
        "tier_line": "Pro €49/mois : boîte de réception unifiée + service client IA · Business : isolement multi-boutiques + synchro prioritaire",
        "faqs": [
            ("Quelles plateformes en synchro temps réel ?", "eBay est connecté en synchro temps réel OAuth ; Allegro / Otto / Kaufland et 12 autres plateformes supportent la saisie libre des identifiants API (chiffrés AES-256) ou l'import en masse de 200 messages par lot, la synchro temps réel s'ouvrant progressivement."),
            ("Les identifiants sont-ils en sécurité ?", "Scellés par chiffrement AES-256, jamais affichés en clair dans l'interface ni les journaux ; vous pouvez couper et supprimer en un clic à tout moment."),
            ("Les réponses IA sont-elles conformes ?", "Chaque réponse intègre automatiquement la divulgation d'identité machine de l'EU AI Act Art.50 (selon la langue de l'acheteur), et bascule automatiquement en réponse prioritaire de conformité GPSR + rappel Safety Gate sous 15 jours dès qu'un problème de sécurité produit est évoqué."),
        ],
        "related": [("ai-service", "💬 Service client IA"), ("safety-redline", "🚨 Couche de lignes rouges de sécurité"), ("gpsr", "🛡️ Moteur de conformité GPSR")],
    },

    "ad-copy": {
        "icon": "📣",
        "name": "Générateur de textes publicitaires",
        "title": "Générateur de textes publicitaires — génération selon les règles des emplacements publicitaires · contrôle des mots interdits · variantes multilingues A/B | CrossAIO",
        "meta_desc": "Titres et descriptions des pubs Amazon SP/SB/SD, textes des emplacements promotionnels multi-plateforme en un clic : limites de caractères et mots interdits contrôlés en dur selon les règles plateforme, variantes multilingues pour tests A/B, sans mot promotionnel non conforme.",
        "eyebrow": "Fonctionnalité ⑧ · levier de croissance",
        "h1": "Fini la publicité à l'aveugle, <br>les règles plateforme sont <em>contrôlées avant génération</em>",
        "sub": "Un texte publicitaire refusé une fois, et c'est une journée de trafic brûlée. CrossAIO génère titre / description selon les règles de l'emplacement publicitaire de la plateforme cible : caractères, mots interdits (best / cheapest / interdiction formelle des coordonnées), habitudes de la langue locale, tous contrôlés en amont, avec plusieurs variantes pour la diffusion A/B.",
        "hero_note": "✓ filtrage en amont des mots interdits · ✓ variantes multilingues A/B · ✓ limites strictes de caractères",
        "mockup": "ad",
        "pain_title": "Trois pièges invisibles des textes publicitaires",
        "pains": [
            "Les mots promotionnels franchissent la ligne : best / cheapest / No.1 sont directement refusés dans la politique publicitaire de la plupart des plateformes",
            "Un site allemand avec une pub en anglais, la conversion chute de moitié ; et l'on ne peut pas payer un rédacteur natif pour chaque localisation",
            "Les limites de caractères des emplacements publicitaires diffèrent selon la plateforme, écrire à la main les versions des 12 plateformes est un pur coût humain",
        ],
        "caps": [
            {"group": "Génération", "color": "g1", "items": [
                ("Textes publicitaires multi-plateforme", "titre + description générés selon les règles de l'emplacement publicitaire, une saisie pour des sorties multi-plateforme"),
                ("Variantes A/B", "chaque jeu produit des variantes multilingues, pour diffuser et retenir la meilleure"),
                ("Localisation culturelle", "réécrite selon le profil du marché : l'Allemagne mise sur les certifications techniques, la France sur les scènes d'usage (même moteur de profilage que le listing)"),
            ]},
            {"group": "Conformité", "color": "g2", "items": [
                ("Filtrage en amont des mots interdits", "mots promotionnels / exagérés / coordonnées bloqués avant génération, sans gaspiller une occasion de refus"),
                ("Limites strictes de caractères", "contrôle point par point des limites de caractères des emplacements publicitaires, signalement instantané au dépassement"),
            ]},
        ],
        "steps": [
            ("Saisissez produit et plateforme", "choisissez la plateforme cible et la langue, donnez les mots-clés principaux"),
            ("Contrôle des règles et génération", "filtrage en amont des mots interdits et des caractères → génération de plusieurs variantes conformes"),
            ("Diffusion et sélection", "diffusez les variantes A/B, régénérez à tout moment celles qui performent mal"),
        ],
        "stats": [("13", "plateformes dans la base de règles"), ("0", "cible de refus pour mot promotionnel"), ("8", "profils culturels de marché"), ("11", "langues de sortie")],
        "tier_line": "Starter €9/mois et plus : textes publicitaires · Pro : matrice multi-plateforme + variantes A/B",
        "faqs": [
            ("Générez-vous des textes qui seront refusés ?", "Avant génération, contrôle en dur des mots interdits et des caractères selon la politique publicitaire plateforme, les mots promotionnels exagérés et les coordonnées sont directement bloqués ; mais les politiques d'audit évoluant, c'est la plateforme qui tranche in fine."),
            ("Quelles langues sont supportées ?", "Même moteur que le générateur de listings : 11 langues de sortie + 8 profils culturels de marché (allemand / français / italien / espagnol / polonais / néerlandais / roumain…)."),
            ("Quelle différence avec le générateur de listings ?", "Le générateur de listings produit le pack complet de la page produit ; le texte publicitaire vise les emplacements promotionnels, avec des titres / descriptions plus courts et plus centrés conversion, et des variantes A/B."),
        ],
        "related": [("listing-generator", "📦 Générateur de listings"), ("matrix", "🌍 Matrice multi-plateformes"), ("gpsr", "🛡️ Moteur de conformité GPSR")],
    },

    "listing-watch": {
        "icon": "📡",
        "name": "Rapport de surveillance quotidien des listings",
        "title": "Surveillance des listings — vérification automatisée quotidienne · rapport dès montée du risque · alerte de dérive de conformité | CrossAIO",
        "meta_desc": "Vérification quotidienne automatique de vos listings : dérive des caractères, bloc de conformité manquant, nouveaux avis négatifs, baisse du score sémantique, suivis point par point ; rapport de risque quotidien par e-mail dès escalade, sans à devoir vous connecter chaque jour.",
        "eyebrow": "Fonctionnalité ⑨ · levier de rétention",
        "h1": "Un listing ne s'arrête pas d'être publié, <br>il mérite une <em>vérification automatique quotidienne</em>",
        "sub": "Un listing réécrit en silence par la plateforme, un bloc de conformité avalé, un nouvel avis négatif porteur de mot-sécurité — vous les découvrez quand le mal est déjà fait. CrossAIO vérifie chaque jour, à heure fixe, votre liste de surveillance : dérive de caractères / conformité manquante / thèmes d'avis négatifs / score sémantique, suivis point par point, avec envoi d'un rapport quotidien par e-mail dès montée du risque.",
        "hero_note": "✓ vérification quotidienne planifiée · ✓ rapport par e-mail dès montée du risque · ✓ suivi des thèmes d'avis négatifs",
        "mockup": "watch",
        "pain_title": "Le coût de l'indifférence",
        "pains": [
            "La plateforme réécrit le listing en silence : mots-clés supprimés, catégorie changée, on ne s'en rend compte que quand les ventes chutent",
            "Les demandes de sécurité dans un nouvel avis négatif (surchauffe / casse) passent inaperçues → la fenêtre de signalement Safety Gate de 15 jours est ratée",
            "Une inspection manuelle quotidienne plateforme par plateforme = un nouveau coût humain, et facile à oublier",
        ],
        "caps": [
            {"group": "Vérification automatique", "color": "g1", "items": [
                ("Vérification quotidienne planifiée", "chaque jour, passage automatique sur les listings de la liste de surveillance : caractères / bloc de conformité / score sémantique"),
                ("Niveaux de risque", "alerte classée par niveau : critique (conformité manquante) / élevé (mot-sécurité dans un avis négatif) / moyen (baisse du score)"),
                ("Rapport par e-mail", "dès montée du risque, rapport quotidien par e-mail SMTP, sans connexion au back-office"),
            ]},
            {"group": "Boucle de correctifs", "color": "g2", "items": [
                ("Suivi des thèmes d'avis négatifs", "identification automatique du thème des nouveaux avis, les demandes de sécurité basculent directement dans le flux de conformité GPSR prioritaire"),
                ("Réécriture en un clic", "depuis le rapport, accès direct à la boucle de réécriture d'avis négatifs, nouvelle évaluation et suivi du gain après correctif"),
            ]},
        ],
        "steps": [
            ("Ajoutez à la surveillance", "ajoutez les listings à surveiller à la liste de surveillance (par plateforme)"),
            ("Vérification quotidienne", "la tâche planifiée tourne chaque jour, comparaison point par point de la dérive et du risque"),
            ("Rapport direct", "montée du risque → rapport par e-mail → correctif en un clic"),
        ],
        "stats": [("chaque jour", "fréquence de la vérification auto"), ("146", "mots d'incident répertoriés"), ("3 niveaux", "degré de risque"), ("15 jours", "fenêtre Safety Gate")],
        "tier_line": "Starter €9/mois et plus : 5 emplacements de surveillance · Pro : 50 + rapport par e-mail · Business : multi-boutiques",
        "faqs": [
            ("Que surveillez-vous ?", "Dérive du nombre de caractères du titre / des puces, complétude du bloc de conformité GPSR, nouveaux avis négatifs et leurs thèmes, évolution du score sémantique — le tout passé en revue chaque jour et classé par niveau."),
            ("Comment suis-je notifié ?", "Dès montée du risque, rapport quotidien par e-mail SMTP (SMTP à configurer dans l'environnement) ; vous pouvez aussi consulter l'historique des rapports à tout moment dans l'atelier."),
            ("Quel est le lien avec la réécriture d'avis négatifs ?", "Dès qu'un rapport détecte un avis négatif à thème sécurité, accès en un clic à la boucle de réécriture : identification du thème → correctifs des puces → réévaluation suivie, pour une boucle surveillance-correctif."),
        ],
        "related": [("review-rewrite", "📈 Réécriture d'avis négatifs"), ("gpsr", "🛡️ Moteur de conformité GPSR"), ("ai-service", "💬 Service client IA")],
    },
}


# ---------------------------------------------------------------------------
# B) CHROME_FR — textes de charte de page
# ---------------------------------------------------------------------------

CHROME_FR = {
    "cta_start": "Démarrer gratuitement",
    "cta_workbench": "🚀 Utiliser dans l'atelier →",
    "sec_caps_eyebrow": "Fonctionnalités détaillées",
    "sec_caps_title": "{icon} {name}, ce qu'il sait faire",
    "sec_caps_sub": "Regroupées par catégorie, chacune répond à un vide laissé par la concurrence",
    "sec_steps_eyebrow": "Comment ça marche",
    "sec_steps_title": "Trois étapes pour commencer",
    "sec_cover_eyebrow": "Couverture",
    "sec_cover_title": "Une seule configuration · synchronisée sur 12 plateformes",
    "sec_cover_sub": "Survolez pour suspendre le défilement · cliquez sur « Plateformes » dans la navigation pour le détail des règles",
    "tier_cta": "Voir les tarifs complets →",
    "sec_faq_eyebrow": "Questions fréquentes",
    "sec_faq_title": "À propos de {name}",
    "cta_band_title": "{icon} Essayez {name} dès maintenant",
    "cta_band_sub": "Inscription gratuite, prêt à l'emploi · sans carte bancaire · sans boutique à connecter",
    "cta_band_start": "Démarrer gratuitement →",
    "cta_band_workbench": "🚀 Utiliser dans l'atelier",
    "x_related_title": "Continuez à découvrir les autres fonctionnalités",
    "x_rules_title": "Pages de règles natives des plateformes",
    "rel_small": "Fonctionnalité CrossAIO · page dédiée",
    "rules_small": "Page de règles GPSR natives de la plateforme",
    "footer_home": "Accueil",
    "footer_features": "Fonctionnalités",
    "footer_rules": "référentiel de règles",
    "footer_pricing": "Tarifs",
    "footer_check": "vérification de conformité gratuite",
    "footer_skills": "Skills open source",
    "footer_signin": "Connexion",
    "footer_tag": "CrossAIO — moteur de qualité de listings et de conformité pour toutes les plateformes européennes · © 2026",
    "platform_short": {
        "allegro": "🇵🇱 Règles Allegro →",
        "emag": "🇷🇴 Règles eMAG →",
        "cdiscount": "🇫🇷 Règles Cdiscount →",
        "otto": "🇩🇪 Règles Otto →",
    },
    "index_title": "Aperçu des fonctionnalités — 6 pages dédiées | CrossAIO",
    "index_meta": "Fonctionnalités CrossAIO : moteur de conformité GPSR, générateur de listings, matrice multi-plateformes, boucle de réécriture d'avis, service client IA + boîte de réception unifiée, couche de lignes rouges de sécurité. Chaque fonctionnalité a sa page dédiée.",
    "index_eyebrow": "Fonctionnalités",
    "index_h2": "Six fonctionnalités, six pages dédiées",
    "index_sub": "Chaque fonctionnalité a son analyse des points de douleur, son détail, son fonctionnement et son entrée tarifs",
}


# ---------------------------------------------------------------------------
# C) MOCKUP_FR — littéraux visibles (contenu chinois) des 7 maquettes SVG
#    clé = littéral source chinois exact ; valeur = traduction française.
# ---------------------------------------------------------------------------

MOCKUP_FR = {
    "generator": {
        "Listing 生成器界面": "Interface du générateur de listings",
        "Listing 生成器": "Générateur de listings",
        "输入产品": "Saisir produit",
        "平台规则自动匹配": "Règles plateforme auto-appariées",
        "Otto ≤70 · Allegro ≤75 · Amazon ≤200 字符 · de/pl/en": "Otto ≤70 · Allegro ≤75 · Amazon ≤200 caractères · de/pl/en",
        "标题（Otto · 德语） 47/70 字符": "Titre (Otto · allemand) 47/70 caractères",
        "五点描述（5/5） · 详情 · 搜索词 已生成": "Puces (5/5) · description · mots-clés back-end générés",
        "硬校验": "Contrôle dur",
        "✓ 字数 ✓ 语言 ✓ 结构 ✓ GPSR 内嵌": "✓ caractères ✓ langue ✓ structure ✓ GPSR intégré",
        "完整度评分 94/100": "Score de complétude 94/100",
        "可直接复制到卖家中心 · 16 语言可选": "À copier dans le centre vendeur · 16 langues",
        "Free 每天 5 次 · Starter 起 GPSR 合规块内嵌输出": "Free : 5/jour · dès Starter : bloc GPSR intégré en sortie",
    },
    "matrix": {
        "12 平台矩阵批量生成": "Génération en masse, matrice 12 plateformes",
        "多平台矩阵": "Matrice multi-plateformes",
        "泛欧 20+ 国": "Europe 20+ pays",
        "en→多语言": "en→multilingue",
        "✓ 已生成": "✓ généré",
        "输入一次产品信息": "Saisir une fois le produit",
        "标题 + 关键词 + 属性（品牌/EAN/材质）": "Titre + mots-clés + attributs (marque/EAN/matière)",
        "12 平台规则内置 · 16 语言自动匹配": "Règles 12 plateformes intégrées · 16 langues auto",
        "不绑店 · 独立工作台 · 结果逐平台可编辑": "Sans boutique · atelier indépendant · résultats modifiables",
        "Allegro / eMAG / Cdiscount / Fruugo —— 主流工具覆盖率为零，CrossAIO 率先补齐": "Allegro / eMAG / Cdiscount / Fruugo — couverture nulle chez les outils grand public, CrossAIO les comble en premier",
    },
    "review": {
        "差评分析与五点改写": "Analyse d'avis négatif et réécriture des puces",
        "差评改写闭环": "Boucle de réécriture d'avis",
        "⭐ 差评输入（1 星）": "⭐ Avis négatif saisi (1 étoile)",
        '"左耳三个月就断了一个角，客服': "« Le côté gauche a cassé un coin après trois mois, le SAV",
        "只说重新买。充电盒也过热。\"": "n'a propos que de racheter. L'étui chauffe aussi. »",
        "主题：材质": "Thème : matière",
        "主题：过热⚠": "Thème : surchauffe⚠",
        "⚠ 安全诉求 → 触发 GPSR 事件预警": "⚠ Demande de sécurité → alerte incident GPSR",
        "修复建议 + 五点改写": "Correctifs + réécriture des puces",
        '五点② 改写：增加 "增强铰链结构，': "Puce② réécrite : ajouter « charnière renforcée,",
        '通过 5,000 次开合测试"': "testée à 5 000 ouvertures/fermetures »",
        '五点④ 改写：增加 "过热保护认证"': "Puce④ réécrite : ajouter « certification protection surchauffe »",
        "生成新版本": "Générer la nouvelle version",
        "语义评分（Rufus / iZi 适配）": "Score sémantique (adaptation Rufus / iZi)",
        "尺寸 8/10": "Taille 8/10",
        "耐用性 5→8/10": "Durabilité 5→8/10",
        "安全 4→9/10": "Sécurité 4→9/10",
        "续航 9/10": "Autonomie 9/10",
        "8 类买家问题覆盖度逐项量化 · 改写后复评追踪提升": "Couverture des 8 questions acheteurs quantifiée · réévaluation après réécriture",
        "8 类主题定位 · 安全类差评自动走 GPSR 合规优先流程": "8 thèmes détectés · les avis sécurité basculent en flux GPSR prioritaire",
    },
    "inbox": {
        "统一收件箱与 Art.50 披露": "Boîte unifiée et divulgation Art.50",
        "AI 客服 · 统一收件箱": "Service client IA · boîte unifiée",
        "统一收件箱": "Boîte de réception unifiée",
        "Produit en feu ! — 安全事件": "Produit en feu ! — incident de sécurité",
        "AI 草稿 · Art.50 已披露 ✓": "Brouillon IA · Art.50 divulgué ✓",
        "替换/退款方案 + 欧代联系方式": "Solution remboursement/échange + contact représentant UE",
        "确认发送": "Confirmer l'envoi",
        "编辑草稿": "Modifier le brouillon",
        "⚠ 红线拦截：fr 会话命中「安全事件」": "⚠ Filtre rouge : conversation fr = « incident de sécurité »",
        "自动切换合规优先回复 · 15 天 Safety Gate 提示 · 强制转人工": "Bascule réponse prioritaire conformité · rappel Safety Gate 15 j · transfert forcé humain",
    },
    "ad": {
        "广告文案生成与禁用词拦截": "Génération de textes pub et filtrage des mots interdits",
        "广告文案生成": "Générateur de textes publicitaires",
        "📣 广告标题生成（SP 广告位）": "📣 Génération titre pub (emplacement SP)",
        "IPX5 Waterproof — DE 站德语版": "IPX5 Waterproof — version allemande (site DE)",
        "Wasserdicht IPX5（A/B 变体）": "Wasserdicht IPX5 (variante A/B)",
        "A/B 测试": "Test A/B",
        "🚫 禁用词前置拦截": "🚫 Filtrage en amont des mots interdits",
        "→ best / 年份夸大 · 违反广告政策": "→ best / exagération d'année · infraction politique pub",
        "字数：标题 ≤ 50 字符 ✓": "Caractères : titre ≤ 50 ✓",
        "联系方式 / 促销堆叠：已剔除 ✓": "Coordonnées / accumulation promo : retiré ✓",
        "重新生成合规版": "Régénérer la version conforme",
        "多平台多语言输出": "Sortie multi-plateforme multilingue",
        "禁用词前置拦截 · 字数硬校验 · 8 市场文化画像改写": "Filtrage mots interdits · limites de caractères · 8 profils culturels",
    },
    "watch": {
        "Listing 每日体检与风险分级日报": "Vérif quotidienne listing et rapport de risque",
        "Listing 监控日报": "Rapport de surveillance quotidien",
        "📡 今日体检 · 12 个 Listing · 2 项风险升级": "📡 Vérif du jour · 12 listings · 2 risques escaladés",
        "每日 08:00 定时运行 · 逐项比对字数 / 合规块 / 差评 / 语义评分": "Quotidien 08:00 · caractères / bloc / avis / score sémantique",
        "🔴 致命": "🔴 Critique",
        "Bluetooth 耳机（DE 站）": "Écouteurs Bluetooth (site DE)",
        "GPSR 合规块消失": "Bloc de conformité GPSR disparu",
        "→ 平台改写吞块 · 立即修复": "→ réécrit par la plateforme, bloc avalé · corriger",
        "一键修复": "Corriger en un clic",
        "🟠 高": "🟠 Élevé",
        "充电盒（FR 站）新差评": "Nouvel avis négatif, étui (site FR)",
        '"surchauffe（过热）"': "« surchauffe »",
        "→ 命中事故词库 · GPSR 事件": "→ mot d'incident détecté · incident GPSR",
        "15 天 Safety Gate 窗口内": "Fenêtre Safety Gate : 15 jours",
        "🟢 正常 10 项": "🟢 OK : 10 items",
        "字数漂移 0 · 合规块完整": "Dérive caractères 0 · bloc complet",
        "语义评分均值 82（+1）": "Score sémantique moyen 82 (+1)",
        "差评主题：无线充（非安全类）": "Thème d'avis : charge sans fil (non sécurité)",
        "风险升级 → SMTP 邮件日报直达 · 差评主题一键转差评改写闭环": "Montée du risque → rapport e-mail SMTP · avis → boucle de réécriture",
    },
    "redline": {
        "安全红线拦截流程": "Flux de filtrage de la couche rouge",
        "政策安全红线层": "Couche de lignes rouges de sécurité",
        "🚨 红线层命中：人身伤害诉求（置信度 0.97）": "🚨 Couche rouge : demande de blessure corporelle (confiance 0,97)",
        '"充电时充电盒冒烟，孩子当时在旁边" — 自动回复已阻止': "« L'étui fumait en charge, l'enfant était à côté » — réponse auto bloquée",
        "1 · 拦截自动回复": "1 · Bloquer la réponse auto",
        "消息标记为安全事件": "Message marqué incident de sécurité",
        "不走 AI 草稿流程": "Échappe au brouillon IA",
        "2 · 安抚 + 转人工": "2 · Apaiser + transfert humain",
        "安抚话术 · 留证要点提示": "Discours d'apaisement · points à tracer",
        "订单号 / 消息原文 / 截图": "N° de commande / message original / capture",
        "3 · GPSR 事件流程": "3 · Flux incident GPSR",
        "停售评估建议": "Conseil d'arrêt de vente",
        "15 天 Safety Gate 提示": "Rappel Safety Gate 15 jours",
        "留证时间线（可审计）": "Chronologie de traçabilité (auditable)",
        "14:02 识别拦截 → 14:02 转人工 → 14:15 GPSR 流程开启 → 上报倒计时 D-15": "14:02 détection → 14:02 transfert humain → 14:15 flux GPSR → compte à rebours signalement J-15",
        "✓ 红线回复同样内嵌 AI Act Art.50 披露 · 合规层无死角 · 高风险 100% 转人工": "✓ Réponses rouges : divulgation Art.50 intégrée · conformité sans angle mort · 100% haut risque transférés",
    },
}
