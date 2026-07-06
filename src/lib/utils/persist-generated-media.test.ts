import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { extractExpiringMediaUrls, persistGeneratedMedia } from './persist-generated-media';

describe('extractExpiringMediaUrls', () => {
	it('détecte une image x.ai (URL nue)', () => {
		expect(extractExpiringMediaUrls('https://files-cdn.x.ai/a/img_1.png')).toEqual([
			'https://files-cdn.x.ai/a/img_1.png'
		]);
	});

	it('détecte une vidéo x.ai en markdown', () => {
		expect(extractExpiringMediaUrls('![media](https://files-cdn.x.ai/a/v.mp4)')).toEqual([
			'https://files-cdn.x.ai/a/v.mp4'
		]);
	});

	it('détecte un sous-domaine fal.media', () => {
		expect(extractExpiringMediaUrls('voir https://v3.fal.media/files/x.webp ok')).toEqual([
			'https://v3.fal.media/files/x.webp'
		]);
	});

	it("ignore un hôte NON expirable (image permanente collée)", () => {
		expect(extractExpiringMediaUrls('https://example.com/logo.png')).toEqual([]);
	});

	it('ignore une URL déjà locale (idempotence)', () => {
		expect(extractExpiringMediaUrls('![m](/api/v1/files/abc/content)')).toEqual([]);
	});

	it('déduplique les occurrences répétées', () => {
		const c = 'https://files-cdn.x.ai/a.png et encore https://files-cdn.x.ai/a.png';
		expect(extractExpiringMediaUrls(c)).toEqual(['https://files-cdn.x.ai/a.png']);
	});

	it('renvoie vide sans URL', () => {
		expect(extractExpiringMediaUrls('bonjour frérot')).toEqual([]);
	});
});

describe('persistGeneratedMedia', () => {
	beforeEach(() => {
		vi.stubGlobal('localStorage', { token: 'test-token' });
	});
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('réécrit les URLs expirables vers les URLs locales', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => ({ ok: true, json: async () => ({ url: '/api/v1/files/xyz/content' }) }))
		);
		const out = await persistGeneratedMedia('![media](https://files-cdn.x.ai/a/v.mp4)');
		expect(out).toBe('![media](/api/v1/files/xyz/content)');
	});

	it('garde l URL d origine si le rapatriement échoue (repli gracieux)', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => ({ ok: false, json: async () => ({}) }))
		);
		const original = 'https://files-cdn.x.ai/a/img.png';
		expect(await persistGeneratedMedia(original)).toBe(original);
	});

	it('ne fait aucun appel réseau sans média expirable', async () => {
		const spy = vi.fn();
		vi.stubGlobal('fetch', spy);
		const out = await persistGeneratedMedia('juste du texte https://example.com/page');
		expect(out).toBe('juste du texte https://example.com/page');
		expect(spy).not.toHaveBeenCalled();
	});
});
