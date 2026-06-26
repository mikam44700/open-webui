import { describe, it, expect } from 'vitest';
import { getModelPresentation } from './model-badges';

describe('getModelPresentation', () => {
	it('renvoie le libellé humain et les badges pour un identifiant connu', () => {
		const p = getModelPresentation('openai-codex');
		expect(p.humanLabel).toBe('GPT-5.5 via OpenAI Codex');
		expect(p.badges).toContain('Premium');
	});

	it('attribue Local + Confidentiel aux fournisseurs locaux', () => {
		const p = getModelPresentation('ollama');
		expect(p.badges).toContain('Local');
		expect(p.badges).toContain('Confidentiel');
	});

	it('repli D27 : aucun badge pour un identifiant inconnu', () => {
		const p = getModelPresentation('fournisseur-inexistant-xyz');
		expect(p.badges).toEqual([]);
		expect(p.humanLabel).toBeUndefined();
	});

	it('repli sûr pour une entrée vide', () => {
		expect(getModelPresentation('').badges).toEqual([]);
		expect(getModelPresentation(null).badges).toEqual([]);
		expect(getModelPresentation(undefined).badges).toEqual([]);
	});
});
