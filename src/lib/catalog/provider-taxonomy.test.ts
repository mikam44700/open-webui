import { describe, it, expect } from 'vitest';
import {
	GROUP_ORDER,
	getProviderGroup,
	getProviderRegion,
	getProviderRegionFlag,
	getProviderRegionName,
	groupProviders
} from './provider-taxonomy';

// Les 30 fournisseurs de la catégorie « api » (source : bridge list_providers).
const API_PROVIDER_IDS = [
	'openrouter',
	'moa',
	'novita',
	'anthropic',
	'openai-api',
	'alibaba',
	'xiaomi',
	'tencent-tokenhub',
	'nvidia',
	'copilot',
	'huggingface',
	'gemini',
	'vertex',
	'deepseek',
	'xai',
	'zai',
	'kimi-coding',
	'kimi-coding-cn',
	'stepfun',
	'minimax',
	'minimax-cn',
	'ollama-cloud',
	'arcee',
	'gmi',
	'kilocode',
	'opencode-zen',
	'opencode-go',
	'azure-foundry',
	'alibaba-coding-plan',
	'custom'
];

describe('provider-taxonomy', () => {
	it('classe chacun des 30 fournisseurs « api » dans un groupe (aucun oublié)', () => {
		const unclassified = API_PROVIDER_IDS.filter((id) => getProviderGroup(id) === null);
		expect(unclassified).toEqual([]);
	});

	it('donne une région à tous sauf « custom » (sur-mesure = origine neutre)', () => {
		const withoutRegion = API_PROVIDER_IDS.filter((id) => getProviderRegion(id) === null);
		expect(withoutRegion).toEqual(['custom']);
	});

	it('affiche le drapeau seul, et le nom complet pour l’infobulle', () => {
		expect(getProviderRegionFlag('anthropic')).toBe('🇺🇸');
		expect(getProviderRegionName('anthropic')).toBe('États-Unis');
		expect(getProviderRegionFlag('alibaba')).toBe('🇨🇳');
		expect(getProviderRegionFlag('openrouter')).toBe('🌍');
		expect(getProviderRegionFlag('custom')).toBeNull();
		expect(getProviderRegionName('custom')).toBeNull();
	});

	it('sépare les deux axes : DeepSeek est un « grand nom » ET d’origine chinoise', () => {
		expect(getProviderGroup('deepseek')).toBe('grands-noms');
		expect(getProviderRegion('deepseek')).toBe('cn');
	});

	it('regroupe dans l’ordre officiel des sections', () => {
		const groups = groupProviders(API_PROVIDER_IDS.map((id) => ({ id })));
		const keys = groups.map((g) => g.key);
		// L'ordre doit suivre GROUP_ORDER (aucun groupe vide ici : les 5 sont peuplés).
		expect(keys).toEqual([...GROUP_ORDER]);
	});

	it('ne perd aucun fournisseur au regroupement', () => {
		const groups = groupProviders(API_PROVIDER_IDS.map((id) => ({ id })));
		const total = groups.reduce((n, g) => n + g.items.length, 0);
		expect(total).toBe(API_PROVIDER_IDS.length);
	});

	it('range les fournisseurs inconnus dans « Autres », en fin de liste', () => {
		const groups = groupProviders([{ id: 'anthropic' }, { id: 'un-provider-du-futur' }]);
		const last = groups[groups.length - 1];
		expect(last.key).toBe('autres');
		expect(last.label).toBe('Autres');
		expect(last.items).toEqual([{ id: 'un-provider-du-futur' }]);
	});

	// --- Onglets Comptes (OAuth), Local, Autres : badges région aussi (pas de sections) ---
	const OTHER_TAB_IDS = [
		'nous',
		'openai-codex',
		'xai-oauth',
		'minimax-oauth',
		'qwen-oauth', // Comptes
		'lmstudio',
		'ollama-local', // Local
		'copilot-acp',
		'bedrock' // Autres
	];

	it('donne une région à tous les fournisseurs des onglets Comptes / Local / Autres', () => {
		const withoutRegion = OTHER_TAB_IDS.filter((id) => getProviderRegion(id) === null);
		expect(withoutRegion).toEqual([]);
	});

	it('marque les modèles locaux comme « Local » (souveraineté maximale)', () => {
		expect(getProviderRegion('lmstudio')).toBe('local');
		expect(getProviderRegion('ollama-local')).toBe('local');
		expect(getProviderRegionFlag('lmstudio')).toBe('💻');
		expect(getProviderRegionName('lmstudio')).toBe('Local');
	});
});
