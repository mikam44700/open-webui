// Mini-interview d'onboarding (spec 019) — logique PURE, testable (Vitest).
//
// Après le crawl (ou en repli sans site), Mike pose quelques questions COURTES que le site web ne
// révèle JAMAIS : qui dirige, comment il travaille, ses priorités, ce qui l'agace. Ces réponses
// affinent le profil (USER.md) — en particulier la « façon de travailler » qui CALIBRE l'autonomie
// des agents (valider vs agir). Une question par écran ; tout est skippable sauf le prénom.
//
// Principes issus de la recherche (Typeform / Gojiberry / discovery interview) : questions concrètes
// et non-techniques, chips pour le catégorisable, champ libre limité, anti-paralysie.

import { EMPTY_CONTEXT, type CompanyContext } from './companySynthesis';

export type Answers = Record<string, string | string[]>;

export type Question =
	| { key: string; kind: 'text'; title: string; placeholder: string; optional?: boolean }
	| { key: string; kind: 'textarea'; title: string; placeholder: string; optional?: boolean }
	| {
			key: string;
			kind: 'chips';
			title: string;
			options: string[];
			optional?: boolean;
			// Sous-titre explicatif affiché sous la question (ex. concret) — pour les choix pas
			// évidents (niveau d'autonomie…). Optionnel : sans lui, la question reste seule.
			hint?: string;
			// Descriptions par option : quand présent, les choix s'affichent en CARTES (libellé +
			// explication) au lieu de pastilles — pour un choix important à expliciter au dirigeant.
			optionHints?: Record<string, string>;
			// Si présent et que cette option est choisie, un champ libre « Précisez… » s'affiche ;
			// sa valeur (clé compagnon `${key}Autre`) REMPLACE le marqueur dans le profil final.
			otherOption?: string;
			otherPlaceholder?: string;
	  }
	| {
			key: string;
			kind: 'chipsMulti';
			title: string;
			options: string[];
			optional?: boolean;
			otherOption?: string;
			otherPlaceholder?: string;
	  };

// Questions de COMPLÉMENT (cas « avec site ») : ce que le crawl ne trouve pas. Ordre = du plus
// facile/engageant (prénom) vers le plus impliquant, dernière question chaleureuse.
export const COMPLEMENT_QUESTIONS: Question[] = [
	{ key: 'prenom', kind: 'text', title: 'Quel est votre prénom ?', placeholder: 'Votre prénom' },
	{
		key: 'role',
		kind: 'chips',
		title: 'Quel est votre rôle dans l’entreprise ?',
		options: [
			'Gérant(e)',
			'Président(e)',
			'Fondateur(trice)',
			'Associé(e)',
			'Directeur(trice)',
			'Indépendant(e) / Auto-entrepreneur',
			'Artisan / Commerçant',
			'Autre'
		],
		optional: true,
		otherOption: 'Autre',
		otherPlaceholder: 'Précisez votre rôle'
	},
	{
		key: 'tailleEquipe',
		kind: 'chips',
		title: 'Quelle est la taille de votre équipe ?',
		options: ['Seul(e)', '2 à 10', '11 à 50', '51 à 100', 'Plus de 100'],
		optional: true
	},
	{
		key: 'outils',
		kind: 'chipsMulti',
		title: 'Avec quoi travaillez-vous au quotidien ?',
		options: [
			'E-mail',
			'WhatsApp',
			'Réseaux sociaux',
			'Agenda / Calendrier',
			'Excel / Google Sheets',
			'Logiciel de compta',
			'Facturation / devis',
			'CRM',
			'Autre'
		],
		optional: true,
		otherOption: 'Autre',
		otherPlaceholder: 'Précisez l’outil'
	},
	{
		key: 'priorite',
		kind: 'textarea',
		title: 'Votre priorité n°1 des prochains mois ?',
		placeholder: 'Ex. décrocher plus de clients, gagner du temps sur l’administratif…',
		optional: true
	},
	{
		key: 'faconTravailler',
		kind: 'chips',
		title: 'Jusqu’où votre assistant peut-il agir seul ?',
		hint: 'Par exemple pour envoyer un e-mail ou relancer un client à votre place.',
		options: ['Je valide avant', 'Il agit et me prévient', 'Un mix selon l’importance'],
		optionHints: {
			'Je valide avant': 'Il prépare, vous approuvez, puis il exécute. Vous gardez la main sur tout.',
			'Il agit et me prévient': 'Il fait les tâches lui-même et vous tient au courant après.',
			'Un mix selon l’importance':
				'Il agit seul sur les petites choses, et vous demande pour les décisions importantes.'
		},
		optional: true
	},
	{
		key: 'tacheAgacante',
		kind: 'textarea',
		title: 'Quelle tâche répétitive aimeriez-vous déléguer en premier ?',
		placeholder: 'Ex. relancer les impayés, trier mes mails, faire les devis…',
		optional: true
	}
];

// Questions SUPPLÉMENTAIRES pour le cas « sans site » : elles REMPLACENT le crawl en captant tout ce
// que la lecture du site aurait donné (les 10 blocs de la fiche entreprise), pas seulement les bases.
// Le crawl Facebook a été écarté (anti-bot Meta + CGU) → l'interview guidée est le chemin robuste,
// qui marche à 100 % pour un dirigeant non-tech. Le reste (profil dirigeant) vient des COMPLÉMENTS.
// Insérées juste après le prénom. Toutes optionnelles sauf le nom : on n'impose rien, on invite.
export const NO_SITE_QUESTIONS: Question[] = [
	{
		key: 'nomEntreprise',
		kind: 'text',
		title: 'Le nom de votre entreprise ?',
		placeholder: 'Le nom de votre entreprise'
	},
	{
		key: 'secteur',
		kind: 'text',
		title: 'En une phrase, que faites-vous ?',
		placeholder: 'Ex. plomberie et chauffage pour particuliers'
	},
	{
		key: 'offre',
		kind: 'textarea',
		title: 'Que vendez-vous, et comment ?',
		placeholder: 'Ex. abonnement mensuel, forfait, à l’unité, prestation sur devis…',
		optional: true
	},
	{
		key: 'services',
		kind: 'textarea',
		title: 'Vos principaux services ou produits ?',
		placeholder: 'Un par ligne — ex. dépannage, installation de chaudières, entretien annuel',
		optional: true
	},
	{
		key: 'clienteleCible',
		kind: 'textarea',
		title: 'Qui sont vos clients, en général ?',
		placeholder: 'Ex. propriétaires de maisons, petites entreprises du coin…',
		optional: true
	},
	{
		key: 'problemesResolus',
		kind: 'textarea',
		title: 'Quel problème réglez-vous pour eux ?',
		placeholder: 'Ce que vous leur apportez concrètement',
		optional: true
	},
	{
		key: 'tonDeMarque',
		kind: 'chips',
		title: 'Comment parlez-vous à vos clients ?',
		hint: 'Le style que vos agents adopteront pour écrire à votre place.',
		options: ['Chaleureux', 'Professionnel', 'Direct', 'Convivial', 'Expert'],
		optional: true
	},
	{
		key: 'vocabulaire',
		kind: 'textarea',
		title: 'Des mots ou expressions « maison » ?',
		placeholder: 'Vos termes métier, le nom de vos offres… un par ligne (facultatif)',
		optional: true
	},
	{
		key: 'preuveSociale',
		kind: 'textarea',
		title: 'Un chiffre ou un avis dont vous êtes fier ?',
		placeholder: 'Un par ligne — ex. 20 ans d’expérience, 4,8/5 sur Google, 500 clients',
		optional: true
	},
	{
		key: 'coordonnees',
		kind: 'textarea',
		title: 'Vos coordonnées ?',
		placeholder: 'Téléphone, e-mail, adresse, horaires…',
		optional: true
	}
];

// Construit la séquence PLATE de questions selon le contexte (site déjà lu ou non). Conservée pour la
// logique/les tests ; l'affichage, lui, passe par buildPages (regroupement thématique).
export const buildQuestions = (hasSite: boolean): Question[] => {
	if (hasSite) return COMPLEMENT_QUESTIONS;
	// Sans site : prénom, puis les bases (entreprise), puis le reste des compléments.
	const [prenom, ...rest] = COMPLEMENT_QUESTIONS;
	return [prenom, ...NO_SITE_QUESTIONS, ...rest];
};

// Regroupement en PAGES thématiques (3-4 questions) pour alléger le rythme : au lieu d'un écran par
// question (15 sans site), le dirigeant remplit un petit bloc cohérent à la fois (~5 pages). L'ordre
// commence par lui (engagement : prénom en 1er), puis l'entreprise, puis le quotidien.
export type Page = { title: string; questions: Question[] };

const ALL_BY_KEY: Record<string, Question> = Object.fromEntries(
	[...COMPLEMENT_QUESTIONS, ...NO_SITE_QUESTIONS].map((q) => [q.key, q])
);
const pageOf = (title: string, keys: string[]): Page => ({
	title,
	questions: keys.map((k) => ALL_BY_KEY[k]).filter(Boolean)
});

export const buildPages = (hasSite: boolean): Page[] =>
	hasSite
		? [
				pageOf('Faisons connaissance', ['prenom', 'role', 'tailleEquipe']),
				pageOf('Votre quotidien', ['outils', 'priorite', 'faconTravailler', 'tacheAgacante'])
			]
		: [
				pageOf('Faisons connaissance', ['prenom', 'role', 'tailleEquipe']),
				pageOf('Votre entreprise', ['nomEntreprise', 'secteur', 'offre', 'services']),
				pageOf('Vos clients', ['clienteleCible', 'problemesResolus', 'tonDeMarque']),
				pageOf('Votre réputation', ['preuveSociale', 'coordonnees', 'vocabulaire']),
				pageOf('Votre quotidien', ['outils', 'priorite', 'faconTravailler', 'tacheAgacante'])
			];

export const EMPTY_ANSWERS: Answers = {};

// Normalise une réponse scalaire (trim ; '' si vide).
const str = (v: string | string[] | undefined): string => {
	if (Array.isArray(v)) return v.map((x) => x.trim()).filter(Boolean).join(', ');
	return (v ?? '').trim();
};

// Remplace le marqueur « Autre » par la précision libre saisie (clé compagnon `${key}Autre`).
// Ex. role='Autre' + roleAutre='Consultant' → 'Consultant'. Sans précision : valeur inchangée.
const resolveOther = (key: string, a: Answers): string | string[] => {
	const v = a[key] ?? '';
	const custom = str(a[`${key}Autre`]);
	if (!custom) return v;
	if (Array.isArray(v)) return v.map((x) => (x === 'Autre' ? custom : x));
	return v === 'Autre' ? custom : v;
};

// Vrai si l'interview n'a produit aucune réponse exploitable. Les clés compagnon `*Autre` seules
// (sans que « Autre » soit coché) ne comptent pas comme réponse.
export const isInterviewEmpty = (a: Answers): boolean =>
	Object.keys(a)
		.filter((k) => !k.endsWith('Autre'))
		.every((k) => str(resolveOther(k, a)) === '');

// Met en forme les réponses en une section USER.md « profil & façon de travailler ». Omet les
// champs vides. Les clés qui appartiennent au contexte entreprise (nom, secteur…) sont exclues ici
// (elles rejoignent la fiche entreprise) — cf. mergeIntoContext. Contexte vide → chaîne vide.
const PROFILE_LABELS: Record<string, string> = {
	prenom: 'Prénom du dirigeant',
	role: 'Rôle',
	tailleEquipe: 'Taille de l’équipe',
	outils: 'Outils du quotidien',
	priorite: 'Priorité actuelle',
	faconTravailler: 'Façon de travailler souhaitée',
	tacheAgacante: 'Tâche à déléguer en priorité'
};

// Découpe une réponse libre en liste : par LIGNE uniquement (jamais par virgule, pour préserver
// « 4,8/5 » et les adresses). Une réponse déjà en tableau (chipsMulti) est nettoyée telle quelle.
const toList = (v: string | string[] | undefined): string[] => {
	if (Array.isArray(v)) return v.map((x) => x.trim()).filter(Boolean);
	return (v ?? '')
		.split('\n')
		.map((x) => x.trim())
		.filter(Boolean);
};

// Résumé (ADN) : avec site, le modèle le RÉDIGE à partir du crawl. Sans site, on le COMPOSE depuis les
// réponses clés (nom + « ce que vous faites ») pour que USER.md ait toujours une phrase d'accroche — le
// champ le plus injecté dans chaque agent. Vide si ni nom ni activité (rien à résumer, jamais d'invention).
const buildResume = (nom: string, secteur: string): string => {
	const activite = secteur.replace(/\s*\.\s*$/, '').trim();
	if (nom && activite) return `${nom} — ${activite}.`;
	if (activite) return `${activite}.`;
	if (nom) return `${nom}.`;
	return '';
};

// Cas « sans site » : l'interview guidée a capté la fiche entreprise à la place du crawl. PARITÉ avec la
// synthèse du site (11 blocs) : chaque bloc a SA question (offre distincte du secteur), « quel problème »
// alimente les problèmes résolus, le résumé est généré. Les blocs non renseignés restent vides (D27).
export const answersToContext = (a: Answers): CompanyContext => {
	const nom = str(a.nomEntreprise);
	const secteur = str(a.secteur);
	return {
		...EMPTY_CONTEXT,
		nomEntreprise: nom,
		secteur,
		coordonnees: str(a.coordonnees),
		resume: buildResume(nom, secteur),
		offre: str(a.offre), // question dédiée « Que vendez-vous, et comment ? » (distincte du secteur)
		services: toList(a.services),
		tonDeMarque: str(a.tonDeMarque),
		vocabulaire: toList(a.vocabulaire),
		clienteleCible: str(a.clienteleCible),
		problemesResolus: str(a.problemesResolus),
		preuveSociale: toList(a.preuveSociale)
	};
};

export const formatInterviewForProfile = (a: Answers): string => {
	const lines: string[] = [];
	for (const [key, label] of Object.entries(PROFILE_LABELS)) {
		const v = str(resolveOther(key, a));
		if (v) lines.push(`- ${label} : ${v}`);
	}
	if (lines.length === 0) return '';
	return ['## Mon profil & ma façon de travailler', '', ...lines].join('\n');
};
