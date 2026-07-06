import { describe, it, expect } from 'vitest';
import { renderBareImageUrls, isVideoUrl } from './render-image-urls';

describe('renderBareImageUrls', () => {
	it('convertit une URL image nue en markdown média', () => {
		const out = renderBareImageUrls('https://files-cdn.x.ai/abc/file_123.png');
		expect(out).toBe('![media](https://files-cdn.x.ai/abc/file_123.png)');
	});

	it('convertit une URL vidéo nue (mp4)', () => {
		const out = renderBareImageUrls('https://files-cdn.x.ai/abc/file_9.mp4');
		expect(out).toBe('![media](https://files-cdn.x.ai/abc/file_9.mp4)');
	});

	it('gère une URL en fin de phrase', () => {
		const out = renderBareImageUrls('Voilà ton image : https://cdn.test/a.jpg');
		expect(out).toBe('Voilà ton image : ![media](https://cdn.test/a.jpg)');
	});

	it('gère les query params', () => {
		const out = renderBareImageUrls('https://cdn.test/a.webp?w=800&h=600');
		expect(out).toBe('![media](https://cdn.test/a.webp?w=800&h=600)');
	});

	it('ne double PAS un média déjà en markdown', () => {
		const md = '![chat](https://cdn.test/a.png)';
		expect(renderBareImageUrls(md)).toBe(md);
	});

	it('ne touche PAS un lien markdown', () => {
		const md = '[voir](https://cdn.test/a.png)';
		expect(renderBareImageUrls(md)).toBe(md);
	});

	it('ne touche pas une URL non-média', () => {
		const t = 'Va sur https://exemple.com/page';
		expect(renderBareImageUrls(t)).toBe(t);
	});

	it('gère une URL suivie de ponctuation', () => {
		const out = renderBareImageUrls('image https://cdn.test/a.png.');
		expect(out).toBe('image ![media](https://cdn.test/a.png).');
	});

	it('convertit plusieurs URLs (image + vidéo)', () => {
		const out = renderBareImageUrls('https://a.test/1.png et https://b.test/2.mp4');
		expect(out).toBe('![media](https://a.test/1.png) et ![media](https://b.test/2.mp4)');
	});

	it('laisse le texte sans URL intact', () => {
		expect(renderBareImageUrls('bonjour frérot')).toBe('bonjour frérot');
	});
});

describe('isVideoUrl', () => {
	it('détecte les extensions vidéo', () => {
		expect(isVideoUrl('https://x/a.mp4')).toBe(true);
		expect(isVideoUrl('https://x/a.webm?token=1')).toBe(true);
		expect(isVideoUrl('https://x/a.mov')).toBe(true);
	});
	it('rejette les images', () => {
		expect(isVideoUrl('https://x/a.png')).toBe(false);
		expect(isVideoUrl('https://x/a.jpg')).toBe(false);
	});
});
