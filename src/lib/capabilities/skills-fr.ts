// Traduction FR de l'affichage des compétences Hermes (page Capacités › Compétences).
// On ne touche PAS à Hermes : les skills gardent leurs noms techniques côté moteur,
// on traduit uniquement l'AFFICHAGE (titre + description + catégorie).
// Fallback : toute compétence absente d'ici retombe sur son nom/description d'origine
// (honnêteté : jamais de blanc, jamais de fausse traduction).

export type SkillFr = { title: string; description: string };

// Catégories Hermes → libellé FR. L'ordre du tableau ORDER définit l'ordre d'affichage
// (les plus utiles à un dirigeant en premier).
export const skillCategoriesFr: Record<string, string> = {
	email: 'Email',
	'note-taking': 'Notes (second cerveau)',
	productivity: 'Productivité',
	business: 'Business',
	github: 'GitHub',
	research: 'Recherche & veille',
	creative: 'Création',
	media: 'Média',
	'social-media': 'Réseaux sociaux',
	'smart-home': 'Maison connectée',
	apple: 'Apple',
	'software-development': 'Développement',
	'autonomous-ai-agents': 'Agents de code',
	'data-science': 'Data science',
	mlops: 'IA / MLOps',
	dogfood: 'Test qualité',
	yuanbao: 'Yuanbao'
};

export const skillCategoryOrder: string[] = [
	'email',
	'note-taking',
	'productivity',
	'business',
	'github',
	'research',
	'creative',
	'media',
	'social-media',
	'smart-home',
	'apple',
	'software-development',
	'autonomous-ai-agents',
	'data-science',
	'mlops',
	'dogfood',
	'yuanbao'
];

export const skillsFr: Record<string, SkillFr> = {
	// apple
	'apple-notes': { title: 'Notes Apple', description: 'Gérer Notes Apple : créer, rechercher, modifier.' },
	'apple-reminders': { title: 'Rappels Apple', description: 'Gérer Rappels Apple : ajouter, lister, cocher.' },
	findmy: { title: 'Localiser (FindMy)', description: 'Localiser tes appareils Apple et AirTags.' },
	imessage: { title: 'iMessage', description: 'Envoyer et recevoir des iMessages / SMS depuis le Mac.' },
	'macos-computer-use': { title: 'Contrôle du Mac', description: 'Piloter le Mac (clic, clavier, écran) comme un humain.' },

	// autonomous-ai-agents
	'claude-code': { title: 'Claude Code', description: 'Déléguer du développement à Claude Code (features, PR).' },
	codex: { title: 'OpenAI Codex', description: 'Déléguer du développement à Codex (features, PR).' },
	'hermes-agent': { title: 'Hermes Agent', description: 'Configurer, étendre ou contribuer à Hermes.' },
	opencode: { title: 'OpenCode', description: 'Déléguer du développement à OpenCode (features, revue de PR).' },

	// business
	'market-sizing-and-niche-strategy': {
		title: 'Étude de marché & niche',
		description: 'Évaluer une niche, estimer la taille du marché et en tirer un positionnement.'
	},

	// creative
	'architecture-diagram': { title: "Schémas d'architecture", description: "Diagrammes d'architecture / cloud en SVG (HTML)." },
	'ascii-art': { title: 'Art ASCII', description: "Créer de l'art ASCII (figlet, cowsay, image → ASCII)." },
	'ascii-video': { title: 'Vidéo ASCII', description: 'Convertir une vidéo en ASCII couleur (MP4 / GIF).' },
	'baoyu-infographic': { title: 'Infographies', description: 'Créer des infographies (21 mises en page × 21 styles).' },
	'claude-design': { title: 'Design HTML', description: 'Concevoir une page HTML unique (landing, deck, prototype).' },
	comfyui: { title: 'ComfyUI', description: 'Générer images, vidéos et audio avec ComfyUI.' },
	'design-md': { title: 'DESIGN.md', description: 'Rédiger / valider / exporter les specs de design Google (tokens).' },
	excalidraw: { title: 'Excalidraw', description: 'Diagrammes dessinés à la main (archi, flux, séquence).' },
	humanizer: { title: 'Humaniser un texte', description: "Enlever le style « IA » et donner une vraie voix au texte." },
	'manim-video': { title: 'Vidéos Manim', description: 'Animations mathématiques style 3Blue1Brown.' },
	p5js: { title: 'p5.js', description: 'Croquis génératifs, shaders, interactif, 3D.' },
	'popular-web-designs': { title: 'Design systems connus', description: '54 design systems réels (Stripe, Linear, Vercel) en HTML/CSS.' },
	pretext: { title: 'Pretext', description: 'Mise en page texte sans DOM : art ASCII, typographie, jeux texte.' },
	sketch: { title: 'Maquettes jetables', description: 'Maquettes HTML rapides : 2-3 variantes à comparer.' },
	'songwriting-and-ai-music': { title: 'Écriture de chansons & IA musicale', description: 'Composer des paroles et générer de la musique (Suno).' },
	'touchdesigner-mcp': { title: 'TouchDesigner', description: 'Piloter TouchDesigner pour des visuels temps réel.' },

	// data-science
	'jupyter-live-kernel': { title: 'Jupyter en direct', description: 'Exécuter du Python pas à pas dans un noyau Jupyter.' },

	// dogfood
	dogfood: { title: "QA d'applis web", description: 'Tester une appli web : trouver des bugs, preuves, rapports.' },

	// email
	himalaya: { title: 'Email (Himalaya)', description: 'Gérer tes emails (IMAP / SMTP) depuis le terminal.' },

	// github
	'codebase-inspection': { title: 'Inspection de code', description: 'Analyser un projet : lignes, langages, ratios.' },
	'github-auth': { title: 'Connexion GitHub', description: "Configurer l'accès GitHub (tokens, SSH, gh)." },
	'github-code-review': { title: 'Revue de PR', description: 'Relire des pull requests : diffs, commentaires en ligne.' },
	'github-issues': { title: 'Tickets GitHub', description: 'Créer, trier, étiqueter, assigner des issues.' },
	'github-pr-workflow': { title: 'Cycle des PR', description: 'Gérer une PR : branche, commit, CI, merge.' },
	'github-repo-management': { title: 'Gestion de dépôts', description: 'Cloner / créer / forker des dépôts, gérer remotes et releases.' },

	// media
	'gif-search': { title: 'Recherche de GIF', description: 'Chercher et télécharger des GIF (Tenor).' },
	heartmula: { title: 'HeartMuLa', description: 'Générer une chanson à partir de paroles et de tags.' },
	songsee: { title: 'Analyse audio', description: 'Spectrogrammes et caractéristiques audio (mel, chroma, MFCC).' },
	'youtube-content': { title: 'Contenu YouTube', description: 'Transformer des transcriptions YouTube en résumés, threads, articles.' },

	// mlops
	'audiocraft-audio-generation': { title: 'AudioCraft', description: 'Générer musique et sons à partir de texte.' },
	'evaluating-llms-harness': { title: 'Évaluation de LLM', description: 'Benchmarker des modèles (MMLU, GSM8K…).' },
	'huggingface-hub': { title: 'Hugging Face Hub', description: 'Chercher / télécharger / téléverser modèles et datasets.' },
	'llama-cpp': { title: 'llama.cpp', description: 'Inférence locale de modèles GGUF.' },
	'segment-anything-model': { title: 'SAM (segmentation)', description: 'Segmenter une image sans entraînement (points, boîtes).' },
	'serving-llms-vllm': { title: 'Serveur vLLM', description: 'Servir des LLM à haut débit (API OpenAI).' },
	'weights-and-biases': { title: 'Weights & Biases', description: 'Suivre des expériences ML, sweeps, registre de modèles.' },

	// note-taking
	obsidian: { title: 'Obsidian', description: 'Lire, chercher, créer et modifier les notes du coffre Obsidian.' },

	// productivity
	airtable: { title: 'Airtable', description: 'Gérer des bases Airtable (création, filtres, mises à jour).' },
	'google-workspace': { title: 'Google Workspace', description: 'Connecter ton compte Google (Gmail, Drive, Agenda…).' },
	maps: { title: 'Cartes & itinéraires', description: "Géocodage, points d'intérêt, itinéraires, fuseaux (OSM)." },
	'nano-pdf': { title: 'Édition de PDF', description: 'Corriger texte, fautes et titres d’un PDF en langage naturel.' },
	notion: { title: 'Notion', description: 'Gérer pages et bases Notion (markdown, API).' },
	'ocr-and-documents': { title: 'OCR & documents', description: 'Extraire le texte de PDF et de scans.' },
	powerpoint: { title: 'PowerPoint', description: 'Créer, lire et modifier des présentations .pptx.' },
	'teams-meeting-pipeline': { title: 'Réunions Teams', description: 'Résumer les réunions Teams et gérer le pipeline.' },

	// research
	arxiv: { title: 'arXiv', description: 'Chercher des articles scientifiques (mot-clé, auteur, ID).' },
	blogwatcher: { title: 'Veille de blogs', description: 'Surveiller des blogs et flux RSS / Atom.' },
	'llm-wiki': { title: 'Wiki LLM', description: 'Construire / interroger une base de connaissances markdown.' },
	polymarket: { title: 'Polymarket', description: 'Consulter les marchés Polymarket (prix, carnets, historique).' },
	'product-market-research': { title: 'Étude produit-marché', description: 'Évaluer un produit, choisir une niche, mesurer la concurrence.' },
	'research-paper-writing': { title: "Rédaction d'articles ML", description: 'Écrire des papiers pour NeurIPS / ICML / ICLR.' },

	// smart-home
	openhue: { title: 'Philips Hue', description: 'Piloter les lumières, scènes et pièces Philips Hue.' },

	// social-media
	xurl: { title: 'X / Twitter', description: 'Publier, chercher, envoyer des DM sur X (API v2).' },

	// software-development
	'hermes-agent-skill-authoring': { title: 'Création de compétences', description: 'Écrire une compétence Hermes (SKILL.md, validation, structure).' },
	'node-inspect-debugger': { title: 'Débogage Node.js', description: 'Déboguer Node.js via Chrome DevTools.' },
	plan: { title: 'Mode Plan', description: "Écrire un plan d'action markdown détaillé, sans exécuter." },
	'python-debugpy': { title: 'Débogage Python', description: 'Déboguer du Python (pdb + debugpy).' },
	'requesting-code-review': { title: 'Revue avant commit', description: 'Scan sécurité, contrôle qualité, corrections automatiques.' },
	'simplify-code': { title: 'Simplifier le code', description: 'Nettoyage des changements récents par 3 agents en parallèle.' },
	spike: { title: 'Spike (essai)', description: 'Expériences jetables pour valider une idée avant de construire.' },
	'systematic-debugging': { title: 'Débogage méthodique', description: 'Trouver la cause racine en 4 phases avant de corriger.' },
	'test-driven-development': { title: 'TDD', description: 'Imposer RED-GREEN-REFACTOR : tests avant le code.' },

	// yuanbao
	yuanbao: { title: 'Yuanbao', description: 'Groupes Yuanbao : mentionner des membres, interroger des infos.' }
};
