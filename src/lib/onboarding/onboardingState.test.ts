import { describe, it, expect } from 'vitest';
import { shouldShowOnboarding, onboardingStatus, type OnboardingStates } from './onboardingState';

const base: OnboardingStates = {
	contextePresent: false,
	fermeParUtilisateur: false,
	termine: false
};

describe('shouldShowOnboarding — non bloquant, pertinent seulement', () => {
	it('affiche le parcours pour un nouveau dirigeant sans contexte', () => {
		expect(shouldShowOnboarding(base)).toBe(true);
	});

	it("ne l'affiche pas si le dirigeant l'a fermé (« Plus tard »)", () => {
		expect(shouldShowOnboarding({ ...base, fermeParUtilisateur: true })).toBe(false);
	});

	it("ne l'affiche pas si le parcours est terminé", () => {
		expect(shouldShowOnboarding({ ...base, termine: true })).toBe(false);
	});

	it("ne l'impose pas si le contexte entreprise existe déjà", () => {
		expect(shouldShowOnboarding({ ...base, contextePresent: true })).toBe(false);
	});
});

describe('onboardingStatus', () => {
	it('terminé prime sur tout', () => {
		expect(onboardingStatus({ ...base, termine: true, fermeParUtilisateur: true })).toBe('termine');
	});
	it('fermé si non terminé mais fermé par l’utilisateur', () => {
		expect(onboardingStatus({ ...base, fermeParUtilisateur: true })).toBe('ferme');
	});
	it('en cours par défaut', () => {
		expect(onboardingStatus(base)).toBe('en_cours');
	});
});
