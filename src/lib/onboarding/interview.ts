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
	| { key: string; kind: 'chips'; title: string; options: string[]; optional?: boolean }
	| { key: string; kind: 'chipsMulti'; title: string; options: string[]; optional?: boolean };

// Questions de COMPLÉMENT (cas « avec site ») : ce que le crawl ne trouve pas. Ordre = du plus
// facile/engageant (prénom) vers le plus impliquant, dernière question chaleureuse.
export const COMPLEMENT_QUESTIONS: Question[] = [
	{ key: 'prenom', kind: 'text', title: 'Comment vous appelez-vous ?', placeholder: 'Votre prénom' },
	{
		key: 'role',
		kind: 'chips',
		title: 'Quel est votre rôle dans l’entreprise ?',
		options: ['Gérant(e)', 'Fondateur(trice)', 'Associé(e)', 'Directeur(trice)', 'Autre'],
		optional: true
	},
	{
		key: 'tailleEquipe',
		kind: 'chips',
		title: 'Vous êtes combien dans l’équipe ?',
		options: ['Seul(e)', '2 à 5', '6 à 15', '16 et plus'],
		optional: true
	},
	{
		key: 'outils',
		kind: 'chipsMulti',
		title: 'Avec quoi travaillez-vous au quotidien ?',
		options: ['E-mail', 'WhatsApp', 'Excel / Google Sheets', 'Logiciel de compta', 'CRM', 'Autre'],
		optional: true
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
		title: 'Comment préférez-vous qu’on vous aide ?',
		options: ['Je valide tout', 'Agissez et prévenez-moi', 'Un mix des deux'],
		optional: true
	},
	{
		key: 'tacheAgacante',
		kind: 'textarea',
		title: 'Quelle tâche répétitive aimeriez-vous ne plus jamais faire ?',
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

// Vrai si l'interview n'a produit aucune réponse exploitable.
export const isInterviewEmpty = (a: Answers): boolean =>
	Object.values(a).every((v) => str(v) === '');

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
		const v = str(a[key]);
		if (v) lines.push(`- ${label} : ${v}`);
	}
	if (lines.length === 0) return '';
	return ['## Mon profil & ma façon de travailler', '', ...lines].join('\n');
};
