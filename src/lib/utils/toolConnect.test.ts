import { describe, it, expect } from 'vitest';
import { providerStatus, type Provider } from './toolConnect';

// Fabrique un fournisseur minimal ; on surcharge ce qui compte pour chaque cas.
const makeProvider = (over: Partial<Provider> = {}): Provider => ({
	name: 'Test',
	tag: null,
	badge: null,
	kind: 'key',
	fields: [],
	...over
});

const keyField = (present: boolean) => ({
	key: 'api_key',
	label: 'Clé API',
	default: null,
	url: null,
	secret: true,
	present
});

describe('providerStatus — fournisseur à clé (kind=key)', () => {
	it('sans aucun champ saisi → none', () => {
		expect(providerStatus(makeProvider({ fields: [] }))).toBe('none');
	});

	it('clé saisie mais backend inconnu (active absent) → saved', () => {
		const p = makeProvider({ fields: [keyField(true)] });
		expect(providerStatus(p)).toBe('saved');
	});

	it('clé saisie mais PAS le backend actif (active=false) → saved (prudent)', () => {
		const p = makeProvider({ fields: [keyField(true)], active: false });
		expect(providerStatus(p)).toBe('saved');
	});

	it('clé saisie ET backend web réellement actif (active=true) → key-active', () => {
		const p = makeProvider({ fields: [keyField(true)], active: true });
		expect(providerStatus(p)).toBe('key-active');
	});

	it('clé incomplète → none, même si active=true (on ne ment pas)', () => {
		const p = makeProvider({ fields: [keyField(false)], active: true });
		expect(providerStatus(p)).toBe('none');
	});
});

describe('providerStatus — fournisseur géré (kind=managed) : non-régression', () => {
	it('service en ligne sans clé, non démoté → active', () => {
		const p = makeProvider({ kind: 'managed', slug: 'duckduckgo' });
		expect(providerStatus(p)).toBe('active');
	});

	it('géré mais explicitement pas le backend courant (active=false) → none', () => {
		const p = makeProvider({ kind: 'managed', slug: 'duckduckgo', active: false });
		expect(providerStatus(p)).toBe('none');
	});

	it('géré via OAuth et connecté → detected', () => {
		const p = makeProvider({ kind: 'managed', slug: 'brave', connected: true });
		expect(providerStatus(p)).toBe('detected');
	});
});
