import { describe, expect, it } from 'vitest';

import { CATEGORIES } from './categories';
import { RECOMMANDEES, estRecommandee } from './catalogue';

describe('catalogue recommande', () => {
	it('garde une liste substantielle sans tout reprendre', () => {
		// Trop court, le client ne trouve pas son outil ; trop long, on retombe
		// dans le millier d'entrees qu'on cherche justement a ranger.
		expect(RECOMMANDEES.size).toBeGreaterThan(200);
		expect(RECOMMANDEES.size).toBeLessThan(500);
	});

	it('reconnait les applications metier courantes', () => {
		for (const slug of ['hubspot', 'salesforce', 'stripe', 'zendesk', 'shopify', 'docusign']) {
			expect(estRecommandee(slug), slug).toBe(true);
		}
	});

	// Ce que Mike a explicitement demande de garder : les outils de l'agent
	// lui-meme, pas seulement les applications du client.
	it('garde les outils de recherche et d extraction', () => {
		for (const slug of ['exa', 'firecrawl', 'tavily', 'perplexityai', 'apify']) {
			expect(estRecommandee(slug), slug).toBe(true);
		}
	});

	it('laisse les micro-services techniques derriere la porte', () => {
		for (const slug of ['ip2location', 'screenshotone', 'neverbounce', 'twocaptcha']) {
			expect(estRecommandee(slug), slug).toBe(false);
		}
	});

	it('laisse le hors-sujet derriere la porte', () => {
		for (const slug of ['dungeon_fighter_online', 'rawg_video_games_database', 'seat_geek']) {
			expect(estRecommandee(slug), slug).toBe(false);
		}
	});

	it('ignore la casse', () => {
		expect(estRecommandee('HubSpot'.toLowerCase())).toBe(true);
		expect(estRecommandee('STRIPE')).toBe(true);
	});

	// La vitrine doit rester un sous-ensemble du recommande : une application
	// mise en avant sur la page principale mais absente du catalogue recommande
	// disparaitrait du « Tout parcourir », ce qui n'aurait aucun sens.
	it('contient toute la vitrine', () => {
		const manquantes = CATEGORIES.flatMap((c) => c.applications).filter(
			(slug) => !estRecommandee(slug)
		);
		expect(manquantes).toEqual([]);
	});
});
