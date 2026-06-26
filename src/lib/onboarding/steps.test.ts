import { describe, it, expect } from 'vitest';
import { deriveOnboardingSteps, onboardingProgress, onboardingComplete } from './steps';

const empty = {
	activeBrain: false as const,
	connectedIntegrations: 0,
	memory: 'down' as const,
	messaging: 'down' as const,
	taskCount: 0
};

const full = {
	activeBrain: true as const,
	connectedIntegrations: 2,
	memory: 'ok' as const,
	messaging: 'ok' as const,
	taskCount: 5
};

describe('deriveOnboardingSteps', () => {
	it('5 étapes, aucune faite sur une config vide', () => {
		const steps = deriveOnboardingSteps(empty);
		expect(steps).toHaveLength(5);
		expect(onboardingProgress(steps)).toBe(0);
		expect(onboardingComplete(steps)).toBe(false);
	});

	it('toutes faites sur une config complète', () => {
		const steps = deriveOnboardingSteps(full);
		expect(onboardingProgress(steps)).toBe(5);
		expect(onboardingComplete(steps)).toBe(true);
	});

	it('progression partielle correcte', () => {
		const steps = deriveOnboardingSteps({ ...empty, activeBrain: true, memory: 'ok' });
		expect(onboardingProgress(steps)).toBe(2);
		expect(steps.find((s) => s.id === 'brain')?.done).toBe(true);
		expect(steps.find((s) => s.id === 'memory')?.done).toBe(true);
		expect(steps.find((s) => s.id === 'tools')?.done).toBe(false);
	});

	it('honnêteté D27 : états unknown ne cochent aucune étape', () => {
		const steps = deriveOnboardingSteps({
			activeBrain: 'unknown',
			connectedIntegrations: 'unknown',
			memory: 'unknown',
			messaging: 'unknown',
			taskCount: 'unknown'
		});
		expect(onboardingProgress(steps)).toBe(0);
	});

	it('chaque étape a un lien de réalisation', () => {
		for (const s of deriveOnboardingSteps(empty)) {
			expect(s.href.startsWith('/')).toBe(true);
		}
	});
});
