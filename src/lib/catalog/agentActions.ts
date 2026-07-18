/**
 * Cartes d'action par agent + résolution de l'agent actif pour l'accueil du chat.
 *
 * Objectif (inspiré de Limova) : quand un agent est actif (ex. Emma), le chat vide affiche
 * son avatar + son prénom + son rôle, et propose SES actions concrètes en cartes cliquables.
 * Honnêteté (D27) : cliquer une carte PRÉ-REMPLIT le chat — l'utilisateur relit et envoie ;
 * aucune exécution automatique n'est promise (c'est l'agent qui agit avec ses outils).
 *
 * Extensible : ajouter une entrée dans AGENT_ACTIONS (clé = identifiant d'avatar) suffit.
 */

import { AGENT_TEMPLATES } from '$lib/components/agents/templates';
import { avatarId, avatarImage, faceFromImage } from '$lib/components/agents/avatars';
import { prettifyName, slugify } from '$lib/components/agents/utils';

// Même forme qu'un Workflow (catalog/workflows.ts) → réutilisable dans la même grille de cartes.
export type ActionCard = {
	id: string;
	label: string;
	description: string;
	/** Pictogramme simple (emoji). */
	icon: string;
	/** Image optionnelle (URL/chemin) — si fournie, remplace l'emoji dans la carte. */
	image?: string;
	/** Prompt pré-rempli dans le chat au clic. */
	prompt: string;
};

// Agent tel que renvoyé par getAgents() (sous-ensemble utile ici).
type AgentDTO = {
	name: string;
	description?: string;
	avatar?: string | null;
	active?: boolean;
	is_default?: boolean;
};

// Vue d'affichage d'un agent dans l'accueil du chat.
export type AgentView = {
	name: string; // identifiant du profil Hermes
	firstName: string; // prénom vedette (ex. « Emma ») ou nom lisible en repli
	role: string; // fonction (sous-titre), vide si inconnu
	description: string;
	avatar: string; // URL d'image corps entier (avec repli /favicon.png géré à l'affichage)
	face: string; // gros plan visage cadré pour les cercles (repli sur avatar puis favicon)
	actions: ActionCard[]; // cartes curées (peut être vide → on retombe sur le catalogue générique)
};

/**
 * Cartes d'action curées PAR AGENT. Clé = identifiant d'avatar (emma, mike, …),
 * car c'est le lien le plus fiable entre un agent (profil Hermes) et son personnage.
 */
export const AGENT_ACTIONS: Record<string, ActionCard[]> = {
	// Mike — l'orchestrateur : suggestions transverses (coordination, vue d'ensemble, délégation).
	mike: [
		{
			id: 'mike-brief',
			label: 'Fais mon brief du matin',
			description: 'Ce qui compte aujourd’hui et les décisions en attente.',
			icon: '☀️',
			prompt:
				'Fais-moi le brief du matin : ce qui demande mon attention aujourd’hui, les décisions en attente, ' +
				'les engagements à tenir et les priorités. Va à l’essentiel, en français.'
		},
		{
			id: 'mike-plan-semaine',
			label: 'Organise mon plan de la semaine',
			description: 'Priorités réalistes, réparties par jour.',
			icon: '✅',
			prompt:
				'Aide-moi à bâtir mon plan d’action de la semaine : à partir de mes objectifs et de ce qui est en cours, ' +
				'propose des priorités réalistes, organisées par jour, avec les actions concrètes à faire.'
		},
		{
			id: 'mike-deleguer',
			label: 'Délègue une tâche à un agent',
			description: 'Confie une mission au bon spécialiste de l’équipe.',
			icon: '🎼',
			prompt:
				'Je veux confier une tâche au bon agent de l’équipe. Demande-moi laquelle et le résultat attendu, ' +
				'puis crée la tâche et assigne-la à l’agent le plus compétent.'
		}
	],
	// Adam — Agent Obsidian : mémoire de l'entreprise (capturer, ranger, retrouver).
	adam: [
		{
			id: 'adam-chercher',
			label: 'Cherche une info dans mes notes',
			description: 'Retrouve ce que tu sais sur un sujet, avec la source.',
			icon: '🔎',
			prompt:
				'Cherche dans mon second cerveau (mes notes) ce que je sais sur un sujet et fais-moi une synthèse claire, ' +
				'avec les points clés et la source. Demande-moi le sujet si besoin.'
		},
		{
			id: 'adam-ranger',
			label: 'Range ce que je viens de te dire',
			description: 'Capture, tague et relie proprement dans le coffre.',
			icon: '🗂️',
			prompt:
				'Je vais te donner des informations à garder. Capture-les proprement dans le coffre : résume, tague, ' +
				'et relie aux notes existantes. Dis-moi ce que tu veux que je te transmette.'
		},
		{
			id: 'adam-point-sujet',
			label: 'Fais le point sur un sujet',
			description: 'Une synthèse de tout ce que le coffre sait déjà.',
			icon: '🧠',
			prompt:
				'Fais-moi le point sur un sujet à partir de tout ce qui est déjà rangé dans le coffre : ce qu’on sait, ' +
				'les décisions prises, et ce qui manque éventuellement. Demande-moi le sujet.'
		}
	],
	// Lina — Comptable / impayés : factures, relances, trésorerie.
	lina: [
		{
			id: 'lina-impayes',
			label: 'Relance mes impayés',
			description: 'Liste priorisée + relances prêtes à valider.',
			icon: '💰',
			prompt:
				'Fais le point sur mes impayés : liste les factures en retard (montant, ancienneté), priorise les plus ' +
				'gros et les plus anciens, et prépare des relances prêtes à valider. N’envoie rien sans ma validation.'
		},
		{
			id: 'lina-treso',
			label: 'Fais le point trésorerie',
			description: 'Vision claire et honnête, tensions signalées tôt.',
			icon: '📊',
			prompt:
				'Donne-moi une vision claire de ma trésorerie : entrées et sorties à venir, tensions éventuelles, ' +
				'et propose des priorités de paiement. Tague chaque chiffre « vérifié / estimé / inconnu ».'
		},
		{
			id: 'lina-factures',
			label: 'Liste mes factures en retard',
			description: 'Qui doit quoi, depuis combien de temps.',
			icon: '🧾',
			prompt:
				'Liste-moi toutes les factures clients en retard : client, montant, date d’échéance, jours de retard, ' +
				'triées de la plus ancienne à la plus récente.'
		}
	],
	// Maxime — Commercial / devis : ventes, relances, préparation de RDV.
	maxime: [
		{
			id: 'maxime-devis',
			label: 'Relance mes devis en attente',
			description: 'Repère ceux qui dorment, propose une relance juste.',
			icon: '🤝',
			prompt:
				'Fais le point sur mes devis envoyés : repère ceux qui dorment, et prépare pour chacun une relance ' +
				'adaptée (courtoise, pas insistante), prête à valider avant envoi.'
		},
		{
			id: 'maxime-rdv',
			label: 'Prépare un rendez-vous client',
			description: 'Brief court : contexte, historique, points à aborder.',
			icon: '📅',
			prompt:
				'Aide-moi à préparer un rendez-vous client : rassemble le contexte (historique et notes), et livre un ' +
				'brief court avec les points à aborder et les questions à poser. Demande-moi de quel client il s’agit.'
		},
		{
			id: 'maxime-prospects',
			label: 'Fais le point sur mes prospects',
			description: 'Qui relancer, qui laisser tomber, prochaines étapes.',
			icon: '🧲',
			prompt:
				'Fais le point sur mes prospects en cours : qualifie l’intérêt de chacun, dis qui relancer en priorité, ' +
				'qui ne vaut pas la peine d’être poursuivi, et propose les prochaines étapes.'
		}
	],
	// Ethan — Finance / prévisionnel : reporting, prévisionnel, marges.
	ethan: [
		{
			id: 'ethan-reporting',
			label: 'Fais mon reporting financier',
			description: 'Chiffres clés consolidés, l’essentiel d’abord.',
			icon: '📈',
			prompt:
				'Fais-moi un reporting financier clair : consolide les chiffres clés (chiffre d’affaires, marge, ' +
				'trésorerie), l’essentiel d’abord. Tague chaque chiffre « vérifié / estimé / inconnu ».'
		},
		{
			id: 'ethan-previsionnel',
			label: 'Construis mon prévisionnel',
			description: 'Un prévisionnel simple et lisible.',
			icon: '🧮',
			prompt:
				'Aide-moi à construire un prévisionnel simple et lisible à partir de mes données réelles et de mes ' +
				'hypothèses. Demande-moi les hypothèses clés si elles manquent.'
		},
		{
			id: 'ethan-marges',
			label: 'Analyse mes marges',
			description: 'Où je gagne, où je perds, et pourquoi.',
			icon: '🔬',
			prompt:
				'Analyse mes marges : où je gagne de l’argent, où j’en perds, et explique les écarts par rapport au ' +
				'prévu. Termine par des recommandations concrètes.'
		}
	],
	// Nathan — Service client / SAV : réponses, suivi des dossiers.
	nathan: [
		{
			id: 'nathan-repondre',
			label: 'Réponds à une demande client',
			description: 'Réponse claire, ton pro et chaleureux.',
			icon: '🎧',
			prompt:
				'Aide-moi à répondre à une demande client : reformule le besoin, propose une réponse claire au ton ' +
				'professionnel et chaleureux, prête à valider. Colle-moi la demande du client.'
		},
		{
			id: 'nathan-dossiers',
			label: 'Fais le point sur les dossiers en cours',
			description: 'Ce qui est réglé, en attente, ou à relancer.',
			icon: '📂',
			prompt:
				'Fais le point sur les dossiers clients en cours : ce qui est résolu, ce qui est en attente, et ce qu’il ' +
				'faut relancer pour ne laisser personne sans réponse.'
		},
		{
			id: 'nathan-reponse-type',
			label: 'Rédige une réponse type',
			description: 'Un modèle réutilisable pour un cas fréquent.',
			icon: '📝',
			prompt:
				'Aide-moi à rédiger une réponse type réutilisable pour une situation client fréquente. Demande-moi le ' +
				'cas concerné, puis propose un modèle clair et adaptable.'
		}
	],
	// Léo — Veille : concurrents, marché, actualités du secteur.
	leo: [
		{
			id: 'leo-veille',
			label: 'Fais une veille sur mon secteur',
			description: 'Tendances, mouvements, opportunités — sourcé.',
			icon: '🔭',
			prompt:
				'Fais une veille sur mon secteur : tendances récentes, mouvements du marché, opportunités et menaces. ' +
				'Cite tes sources et termine par 3 recommandations actionnables.'
		},
		{
			id: 'leo-concurrents',
			label: 'Surveille mes concurrents',
			description: 'Ce qu’ils font, ce qui mérite une réaction.',
			icon: '🕵️',
			prompt:
				'Surveille mes concurrents : ce qu’ils font de nouveau (offres, communication, prix), et signale ce qui ' +
				'mérite une réaction de ma part. Cite tes sources.'
		},
		{
			id: 'leo-actu',
			label: 'Résume l’actualité de mon marché',
			description: 'L’essentiel de la semaine, sans le bruit.',
			icon: '📰',
			prompt:
				'Résume-moi l’actualité importante de mon marché sur la période récente : l’essentiel d’abord, sans le ' +
				'bruit, avec les sources et ce qui pourrait m’impacter.'
		}
	],
	// Emma — Assistante administrative : emails, agenda, rappels.
	emma: [
		{
			id: 'emma-tri-mails',
			label: 'Trier mes emails',
			description: 'Urgent / à répondre / pour info + brouillons prêts à valider.',
			icon: '✉️',
			prompt:
				'Passe en revue mes emails récents non traités et trie-les en « urgent / à répondre / pour info ». ' +
				'Pour chaque email important, résume-le en une ligne et prépare un brouillon de réponse que je pourrai valider.'
		},
		{
			id: 'emma-agenda-semaine',
			label: 'Organiser ma semaine',
			description: 'Point sur l’agenda, conflits repérés, créneaux de concentration protégés.',
			icon: '🗓️',
			prompt:
				'Fais le point sur mon agenda de la semaine : liste mes rendez-vous, repère les conflits ou les journées ' +
				'trop chargées, et propose une organisation qui protège mes créneaux de concentration.'
		},
		{
			id: 'emma-rappels',
			label: 'Préparer mes rappels',
			description: 'Les rendez-vous et échéances à venir, avec les rappels à programmer.',
			icon: '⏰',
			prompt:
				'Prépare la liste de mes rendez-vous et échéances importantes à venir, et propose-moi les rappels ' +
				'à programmer pour ne rien laisser passer.'
		}
	]
};

/**
 * Construit la vue d'accueil d'un agent actif.
 * Retourne null si aucun agent exploitable (ex. profil « default » non personnalisé) →
 * l'accueil générique existant est conservé (zéro régression).
 */
export const resolveAgentView = (agent: AgentDTO | null | undefined): AgentView | null => {
	if (!agent) return null;

	const aid = avatarId(agent.avatar);
	const tpl = AGENT_TEMPLATES.find(
		(t) =>
			(t.image && avatarId(t.image) === aid) || t.id === agent.name || slugify(t.label) === agent.name
	);

	// Profil de base non identifié → on garde l'accueil générique (« Bonjour {prénom} »).
	if (!tpl && agent.is_default) return null;

	const firstName = tpl?.firstName ?? prettifyName(agent.name);
	// Adaptation LunarIA (portage fidèle, source de données différente) : nos agents-modèles
	// portent leur rôle (tagline) et leurs suggestions dans leur méta — replis ci-dessous.
	const role = tpl?.role ?? (agent as { role?: string }).role ?? '';
	const description = agent.description ?? tpl?.description ?? '';
	// Priorité : avatar persisté → image du template → avatar déduit de l'id → favicon.
	const avatar = agent.avatar || tpl?.image || (aid ? avatarImage(aid) : '/favicon.png');
	const face = faceFromImage(avatar) ?? avatar;
	const metaSuggestions = ((agent as { suggestions?: { content: string }[] }).suggestions ?? []).map(
		(s, i) => ({
			id: `${agent.name}-suggestion-${i}`,
			label: s.content,
			description: '',
			icon: '💬',
			prompt: s.content
		})
	);
	const actions = (aid && AGENT_ACTIONS[aid]) || metaSuggestions;

	return { name: agent.name, firstName, role, description, avatar, face, actions };
};
