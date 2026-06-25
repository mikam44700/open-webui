// Libellés + descriptions FR des toolsets natifs Hermes (orientés client, sans jargon).
// Source unique partagée par ToolsetCard (liste) et ToolConnectModal (titre de la fenêtre)
// pour éviter toute divergence FR.

export const TOOLSET_FR: Record<string, { label: string; desc: string }> = {
	web: { label: '🔍 Recherche & web', desc: 'Cherche sur le web et extrait le contenu des pages.' },
	browser: { label: '🌐 Navigateur automatisé', desc: 'Pilote un navigateur : naviguer, cliquer, remplir, faire défiler.' },
	terminal: { label: '💻 Terminal & processus', desc: 'Exécute des commandes et gère des processus système.' },
	file: { label: '📁 Fichiers', desc: 'Lit, écrit, modifie et recherche dans des fichiers.' },
	code_execution: { label: '⚡ Exécution de code', desc: 'Exécute du code dans un environnement isolé.' },
	vision: { label: '👁️ Vision / analyse d’image', desc: 'Analyse et décrit des images.' },
	video: { label: '🎬 Analyse vidéo', desc: 'Analyse et comprend des vidéos (modèle compatible requis).' },
	image_gen: { label: '🎨 Génération d’images', desc: 'Crée des images à partir d’une description.' },
	video_gen: { label: '🎬 Génération de vidéos', desc: 'Crée des vidéos à partir d’un texte ou d’une image.' },
	x_search: { label: '🐦 Recherche X (Twitter)', desc: 'Recherche des posts et fils sur X (Twitter).' },
	moa: { label: '🧠 Mélange d’agents', desc: 'Combine plusieurs modèles pour de meilleures réponses.' },
	tts: { label: '🔊 Synthèse vocale', desc: 'Convertit du texte en voix.' },
	skills: { label: '📚 Compétences', desc: 'Liste, consulte et gère les compétences de l’agent.' },
	todo: { label: '📋 Planification de tâches', desc: 'Crée et suit une liste de tâches.' },
	memory: { label: '💾 Mémoire', desc: 'Mémoire persistante entre les sessions.' },
	context_engine: { label: '🧩 Moteur de contexte', desc: 'Outils dynamiques du moteur de contexte actif.' },
	session_search: { label: '🔎 Recherche de sessions', desc: 'Recherche dans les conversations passées.' },
	clarify: { label: '❓ Questions de clarification', desc: 'Pose des questions pour lever les ambiguïtés.' },
	delegation: { label: '👥 Délégation de tâches', desc: 'Délègue des tâches à des sous-agents.' },
	cronjob: { label: '⏰ Tâches planifiées', desc: 'Programme des tâches récurrentes (cron).' },
	homeassistant: { label: '🏠 Maison connectée', desc: 'Pilote des appareils domotiques via Home Assistant.' },
	spotify: { label: '🎵 Spotify', desc: 'Lecture, recherche, playlists et bibliothèque Spotify.' },
	discord: { label: '💬 Discord', desc: 'Lit et participe aux conversations Discord.' },
	discord_admin: { label: '🛡️ Administration Discord', desc: 'Gère salons, rôles et messages d’un serveur Discord.' },
	yuanbao: { label: '🤖 Yuanbao', desc: 'Infos de groupe, membres et messages privés Yuanbao.' },
	computer_use: { label: '🖱️ Contrôle de l’ordinateur', desc: 'Contrôle le bureau : souris, clavier, captures d’écran.' }
};
