import { describe, it, expect } from 'vitest';
import { buildChatInput } from './launch';
import { WORKFLOWS } from '../catalog/workflows';

describe('buildChatInput', () => {
	it('place le prompt et les champs attendus par Chat.svelte', () => {
		const input = buildChatInput('Bonjour');
		expect(input.prompt).toBe('Bonjour');
		expect(input.files).toEqual([]);
		expect(input.selectedToolIds).toEqual([]);
		expect(input.selectedSkillIds).toEqual([]);
		expect(input.selectedFilterIds).toEqual([]);
		expect(input.webSearchEnabled).toBe(false);
		expect(input.imageGenerationEnabled).toBe(false);
		expect(input.codeInterpreterEnabled).toBe(false);
	});

	it('est sérialisable en JSON (stocké dans sessionStorage)', () => {
		expect(() => JSON.stringify(buildChatInput('test'))).not.toThrow();
	});
});

describe('catalogue WORKFLOWS', () => {
	it('propose au moins 6 workflows métier avec libellé, description et prompt', () => {
		expect(WORKFLOWS.length).toBeGreaterThanOrEqual(6);
		for (const w of WORKFLOWS) {
			expect(w.label.length).toBeGreaterThan(0);
			expect(w.description.length).toBeGreaterThan(0);
			expect(w.prompt.length).toBeGreaterThan(20);
		}
	});

	it('a des identifiants uniques', () => {
		const ids = WORKFLOWS.map((w) => w.id);
		expect(new Set(ids).size).toBe(ids.length);
	});
});
