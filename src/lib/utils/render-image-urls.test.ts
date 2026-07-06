import { describe, it, expect } from 'vitest';
import { renderBareImageUrls } from './render-image-urls';

describe('renderBareImageUrls', () => {
	it('convertit une URL image nue en markdown image', () => {
		const out = renderBareImageUrls('https://files-cdn.x.ai/abc/file_123.png');
		expect(out).toBe('![image](https://files-cdn.x.ai/abc/file_123.png)');
	});

	it('gère une URL en fin de phrase', () => {
		const out = renderBareImageUrls('Voilà ton image : https://cdn.test/a.jpg');
		expect(out).toBe('Voilà ton image : ![image](https://cdn.test/a.jpg)');
	});

	it('gère les query params', () => {
		const out = renderBareImageUrls('https://cdn.test/a.webp?w=800&h=600');
		expect(out).toBe('![image](https://cdn.test/a.webp?w=800&h=600)');
	});

	it('ne double PAS une image déjà en markdown', () => {
		const md = '![chat](https://cdn.test/a.png)';
		expect(renderBareImageUrls(md)).toBe(md);
	});

	it('ne touche PAS un lien markdown', () => {
		const md = '[voir](https://cdn.test/a.png)';
		expect(renderBareImageUrls(md)).toBe(md);
	});

	it('ne touche pas une URL non-image', () => {
		const t = 'Va sur https://exemple.com/page';
		expect(renderBareImageUrls(t)).toBe(t);
	});

	it('gère une URL suivie de ponctuation', () => {
		const out = renderBareImageUrls('image https://cdn.test/a.png.');
		expect(out).toBe('image ![image](https://cdn.test/a.png).');
	});

	it('convertit plusieurs URLs', () => {
		const out = renderBareImageUrls('https://a.test/1.png et https://b.test/2.jpg');
		expect(out).toBe('![image](https://a.test/1.png) et ![image](https://b.test/2.jpg)');
	});

	it('laisse le texte sans URL intact', () => {
		expect(renderBareImageUrls('bonjour frérot')).toBe('bonjour frérot');
	});
});
