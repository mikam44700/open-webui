// Brouillon d'onboarding persisté en localStorage : permet de REPRENDRE le parcours là où on
// s'était arrêté après un rechargement de page (le crawl du site prend jusqu'à ~1 min — le
// reperdre à chaque reload serait frustrant). Reprise côté client uniquement (VPS mono-client) ;
// une reprise multi-appareils demanderait une persistance backend (non nécessaire ici).

import type { CompanyContext } from './companySynthesis';
import type { Answers } from './interview';

export type OnboardingDraft = {
	step: string;
	history: string[];
	context: CompanyContext;
	interviewMode: 'full' | 'complement';
	answers: Answers;
	crawlStatus: string | null;
	pagesRead: number;
};

const KEY = 'lunaria:onboarding-draft';

// Sauvegarde silencieuse (localStorage peut échouer : quota plein, mode privé) — jamais bloquant.
export const saveDraft = (draft: OnboardingDraft): void => {
	try {
		localStorage.setItem(KEY, JSON.stringify(draft));
	} catch {
		/* stockage indisponible : on n'empêche jamais l'onboarding de continuer */
	}
};

// Recharge le brouillon ; null si absent ou illisible (jamais d'exception remontée à l'UI).
export const loadDraft = (): OnboardingDraft | null => {
	try {
		const raw = localStorage.getItem(KEY);
		if (!raw) return null;
		const d = JSON.parse(raw);
		return d && typeof d === 'object' && typeof d.step === 'string' ? (d as OnboardingDraft) : null;
	} catch {
		return null;
	}
};

// Efface le brouillon (parcours terminé ou fermé) — pas de reprise fantôme au prochain chargement.
export const clearDraft = (): void => {
	try {
		localStorage.removeItem(KEY);
	} catch {
		/* ignore */
	}
};
