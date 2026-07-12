// Preuve tangible de fin d'onboarding (spec 019, design Gojiberry — « temps 9 : preuve avant
// engagement »). Après la validation du contexte, on ne montre PAS une démo scriptée (interdit,
// D27) : on montre l'ÉQUIPE RÉELLE qui a REÇU ce contexte. C'est vrai et vérifiable — le contexte
// a été propagé au profil (USER.md write-through), donc chaque agent le connaît vraiment.
//
// Logique PURE, testable : à partir du CompanyContext validé, produire pour chaque agent du socle
// une « preuve » honnête, ancrée quand c'est possible sur un vrai bout du contexte du dirigeant.

import type { CompanyContext } from './companySynthesis';
import { AGENT_TEMPLATES, type AgentTemplate } from '$lib/components/agents/templates';

export type TeamProofLine = {
	id: string;
	firstName: string;
	role: string;
	image?: string;
	proof: string; // phrase honnête (état réel), personnalisée si le contexte le permet
};

// Ordre d'affichage des spécialistes du socle sur l'écran final. Mike (chef d'orchestre) est le
// narrateur de l'onboarding : il n'est pas listé ici, il « briefe » l'équipe (cf. DoneStep).
export const TEAM_PROOF_ORDER: readonly string[] = [
	'agent-obsidian', // Adam — mémoire
	'assistant-administratif', // Emma — administratif
	'commercial-devis', // Maxime — commercial
	'redacteur-documents', // Nicolas — documents
	'comptable-impayes', // Lina — comptable
	'veille' // Léo — veille
];

// Tronque une valeur libre du contexte pour l'insérer dans une phrase courte, sans casser la mise
// en page. On coupe au mot le plus proche sous la limite (pas en plein milieu).
const clip = (value: string, max = 64): string => {
	const s = (value ?? '').trim();
	if (s.length <= max) return s;
	const cut = s.slice(0, max);
	const lastSpace = cut.lastIndexOf(' ');
	return `${(lastSpace > max * 0.5 ? cut.slice(0, lastSpace) : cut).trim()}…`;
};

// Preuve par agent : ancrée sur le champ du contexte le plus pertinent pour son rôle quand il est
// renseigné (prouve que le contexte est bien passé), sinon repli honnête sur ce qu'il est prêt à
// faire. Jamais de sur-promesse : on décrit ce qui est vrai maintenant.
const proofFor = (id: string, ctx: CompanyContext): string => {
	const offre = clip(ctx.offre);
	const clientele = clip(ctx.clienteleCible);
	const ton = clip(ctx.tonDeMarque, 40);
	switch (id) {
		case 'agent-obsidian':
			return 'A rangé le contexte de votre entreprise dans la mémoire';
		case 'assistant-administratif':
			return clientele
				? `Sait à qui vous vous adressez : ${clientele}`
				: 'Prête à gérer votre agenda et vos mails';
		case 'commercial-devis':
			return offre ? `Connaît votre offre : ${offre}` : 'Prêt à suivre vos devis et relances';
		case 'redacteur-documents':
			return ton ? `Écrira dans votre ton : ${ton}` : 'Prêt à rédiger vos documents';
		case 'comptable-impayes':
			return 'Prête à suivre vos factures et impayés';
		case 'veille':
			return 'Prêt à surveiller votre marché et vos concurrents';
		default:
			return 'Connaît le contexte de votre entreprise';
	}
};

const byId = (id: string): AgentTemplate | undefined =>
	AGENT_TEMPLATES.find((t) => t.id === id);

// Construit les lignes de preuve d'équipe, dans l'ordre défini, en ignorant tout id introuvable
// (robuste si le socle évolue). `context` peut être vide (onboarding en saisie manuelle sautée) :
// on retombe alors proprement sur les phrases de repli.
export const buildTeamProof = (context: CompanyContext): TeamProofLine[] =>
	TEAM_PROOF_ORDER.map((id): TeamProofLine | null => {
		const t = byId(id);
		if (!t) return null;
		return {
			id,
			firstName: t.firstName ?? t.label,
			role: t.role ?? '',
			image: t.image,
			proof: proofFor(id, context)
		};
	}).filter((l): l is TeamProofLine => l !== null);
