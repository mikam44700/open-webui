/**
 * Mise en forme des reponses du moteur — LunarIA V2.
 *
 * Hermes expose 195 routes ecrites a des moments differents : certaines rendent
 * un tableau, d'autres un objet indexe par nom, et les cles ne portent pas
 * toujours le meme nom (`enabled`, `active`, `is_enabled`…).
 *
 * Plutot que de disperser ces tolerances dans chaque onglet, tout est ramene
 * ici a une seule forme, celle que `ListeBasculable` sait afficher.
 */

import type { Element } from './ListeBasculable.svelte';

/** Premiere valeur non vide parmi une liste de cles possibles. */
const premiere = (source: Record<string, any>, cles: string[]): any => {
	for (const cle of cles) {
		const valeur = source?.[cle];
		if (valeur !== undefined && valeur !== null && valeur !== '') return valeur;
	}
	return undefined;
};

/**
 * Ramene la reponse du moteur a un tableau d'entrees `[nom, contenu]`,
 * qu'elle soit un tableau, un objet indexe, ou emballee dans une cle.
 */
const enEntrees = (reponse: any): [string, any][] => {
	if (!reponse) return [];

	// Certaines routes emballent la liste : { toolsets: [...] }, { servers: {...} }
	if (!Array.isArray(reponse) && typeof reponse === 'object') {
		for (const cle of ['toolsets', 'servers', 'skills', 'platforms', 'items', 'data']) {
			if (reponse[cle]) return enEntrees(reponse[cle]);
		}
	}

	if (Array.isArray(reponse)) {
		return reponse.map((entree, index) => [
			`${premiere(entree, ['name', 'id', 'slug', 'key']) ?? index}`,
			entree
		]);
	}

	if (typeof reponse === 'object') {
		return Object.entries(reponse).filter(([, v]) => v && typeof v === 'object');
	}

	return [];
};

/** Traduit une entree du moteur en element affichable. */
export const enElements = (reponse: any): Element[] =>
	enEntrees(reponse).map(([nom, contenu]) => {
		const source = typeof contenu === 'object' ? contenu : {};
		return {
			nom,
			titre: `${premiere(source, ['title', 'display_name', 'label', 'name']) ?? nom}`,
			description: premiere(source, ['description', 'summary', 'desc', 'detail']),
			actif: Boolean(
				premiere(source, ['enabled', 'active', 'is_enabled', 'installed', 'connected']) ?? false
			),
			detail: premiere(source, ['status', 'state', 'version', 'transport'])
		};
	});

/**
 * Familles d'outils. Hermes renvoie un seul inventaire ; la page en fait trois
 * onglets. Le classement se fait sur le nom, seule information stable d'une
 * version d'Hermes a l'autre.
 */
const MOTS_RECHERCHE = ['search', 'web', 'browser', 'crawl', 'fetch', 'scrape', 'http'];
const MOTS_INTEGRATION = [
	'google',
	'gmail',
	'calendar',
	'drive',
	'notion',
	'github',
	'slack',
	'linear',
	'jira',
	'discord',
	'telegram',
	'whatsapp',
	'mail',
	'smtp'
];

const correspond = (element: Element, mots: string[]) => {
	const texte = `${element.nom} ${element.titre}`.toLowerCase();
	return mots.some((mot) => texte.includes(mot));
};

export const familleRecherche = (elements: Element[]) =>
	elements.filter((e) => correspond(e, MOTS_RECHERCHE));

export const familleIntegrations = (elements: Element[]) =>
	elements.filter((e) => correspond(e, MOTS_INTEGRATION));

/** Les outils natifs : tout ce qui n'est ni recherche web ni integration. */
export const familleOutils = (elements: Element[]) =>
	elements.filter((e) => !correspond(e, MOTS_RECHERCHE) && !correspond(e, MOTS_INTEGRATION));
