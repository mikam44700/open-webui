// État du parcours d'onboarding (fonction PURE, testable). Le parcours est TOUJOURS
// non bloquant : on ne l'affiche que s'il est pertinent, jamais on ne force.

export type OnboardingStatus = 'en_cours' | 'ferme' | 'termine';

export type OnboardingStates = {
	// Le contexte entreprise (USER.md) est-il déjà renseigné ? (dérivé, honnête)
	contextePresent: boolean;
	// Le dirigeant a-t-il fermé le parcours (« Plus tard ») ?
	fermeParUtilisateur: boolean;
	// Le parcours a-t-il été mené jusqu'au bout (contexte validé et persisté) ?
	termine: boolean;
};

// Décide si le parcours d'accueil doit s'afficher au chargement.
// Honnête et non bloquant : on ne le montre que s'il reste utile ET que le dirigeant
// ne l'a ni fermé ni terminé. Si le contexte entreprise existe déjà, on ne l'impose pas.
export const shouldShowOnboarding = (s: OnboardingStates): boolean =>
	!s.termine && !s.fermeParUtilisateur && !s.contextePresent;

// Statut lisible du parcours (pour la reprise via la checklist).
export const onboardingStatus = (s: OnboardingStates): OnboardingStatus => {
	if (s.termine) return 'termine';
	if (s.fermeParUtilisateur) return 'ferme';
	return 'en_cours';
};
