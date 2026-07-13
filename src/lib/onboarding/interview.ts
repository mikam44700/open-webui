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

// Questions SUPPLÉMENTAIRES pour le cas « sans site » : elles remplacent le crawl en captant les
// bases de l'entreprise (le reste vient des COMPLÉMENTS). Insérées juste après le prénom.
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
		key: 'clienteleCible',
		kind: 'textarea',
		title: 'Qui sont vos clients, en général ?',
		placeholder: 'Ex. propriétaires de maisons, petites entreprises du coin…',
		optional: true
	},
	{
		key: 'offre',
		kind: 'textarea',
		title: 'Quel problème réglez-vous pour eux ?',
		placeholder: 'Ce que vous leur apportez concrètement',
		optional: true
	}
];

// Construit la séquence de questions selon le contexte (site déjà lu ou non).
export const buildQuestions = (hasSite: boolean): Question[] => {
	if (hasSite) return COMPLEMENT_QUESTIONS;
	// Sans site : prénom, puis les bases (entreprise), puis le reste des compléments.
	const [prenom, ...rest] = COMPLEMENT_QUESTIONS;
	return [prenom, ...NO_SITE_QUESTIONS, ...rest];
};

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

// Cas « sans site » : l'interview complète a capté les bases de l'entreprise. On les reverse dans
// une fiche entreprise (les autres champs restent vides — le dirigeant n'a pas de site à lire).
export const answersToContext = (a: Answers): CompanyContext => ({
	...EMPTY_CONTEXT,
	nomEntreprise: str(a.nomEntreprise),
	secteur: str(a.secteur),
	clienteleCible: str(a.clienteleCible),
	offre: str(a.offre)
});

export const formatInterviewForProfile = (a: Answers): string => {
	const lines: string[] = [];
	for (const [key, label] of Object.entries(PROFILE_LABELS)) {
		const v = str(resolveOther(key, a));
		if (v) lines.push(`- ${label} : ${v}`);
	}
	if (lines.length === 0) return '';
	return ['## Mon profil & ma façon de travailler', '', ...lines].join('\n');
};
