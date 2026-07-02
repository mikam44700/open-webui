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

	it('donne une région à tous les fournisseurs « api » (custom = 🌍, pas un pays)', () => {
		const withoutRegion = API_PROVIDER_IDS.filter((id) => getProviderRegion(id) === null);
		expect(withoutRegion).toEqual([]);
		expect(getProviderRegion('custom')).toBe('intl');
	});

	it('affiche le drapeau seul, et le nom complet pour l’infobulle', () => {
		expect(getProviderRegionFlag('anthropic')).toBe('🇺🇸');
		expect(getProviderRegionName('anthropic')).toBe('États-Unis');
		expect(getProviderRegionFlag('alibaba')).toBe('🇨🇳');
		expect(getProviderRegionFlag('openrouter')).toBe('🌍');
		expect(getProviderRegionFlag('custom')).toBe('🌍');
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

	// --- Fournisseurs natifs ajoutés (plugins model-provider) ---
	const NEW_NATIVE_IDS = [
		'mistral',
		'groq',
		'cerebras',
		'together',
		'fireworks',
		'cohere',
		'perplexity',
		'baidu-ernie'
	];

	it('classe les 8 nouveaux fournisseurs natifs (groupe + région)', () => {
		const noGroup = NEW_NATIVE_IDS.filter((id) => getProviderGroup(id) === null);
		const noRegion = NEW_NATIVE_IDS.filter((id) => getProviderRegion(id) === null);
		expect(noGroup).toEqual([]);
		expect(noRegion).toEqual([]);
	});

	it('place Mistral en 🇫🇷 France et Cohere en 🇨🇦', () => {
		expect(getProviderGroup('mistral')).toBe('grands-noms');
		expect(getProviderRegion('mistral')).toBe('fr');
		expect(getProviderRegionFlag('mistral')).toBe('🇫🇷');
		expect(getProviderRegionName('mistral')).toBe('France');
		expect(getProviderRegionFlag('cohere')).toBe('🇨🇦');
		expect(getProviderRegionName('cohere')).toBe('Canada');
	});
});
