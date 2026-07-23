import { describe, expect, it } from 'vitest';

import { destinationAfterSignup, isFirstClientSetup } from './first-client';

describe('sas du premier client', () => {
	it("détecte uniquement une instance qui n'a encore aucun compte", () => {
		expect(isFirstClientSetup({ onboarding: true })).toBe(true);
		expect(isFirstClientSetup({ onboarding: false })).toBe(false);
		expect(isFirstClientSetup(undefined)).toBe(false);
	});

	it("force l'onboarding AgentOS après la création du compte propriétaire", () => {
		expect(destinationAfterSignup(true, null)).toBe('/onboarding');
		expect(destinationAfterSignup(true, '/')).toBe('/onboarding');
	});

	it('conserve la destination demandée pour une inscription non initiale', () => {
		expect(destinationAfterSignup(false, '/workspace')).toBe('/workspace');
		expect(destinationAfterSignup(false, null)).toBeNull();
	});
});
