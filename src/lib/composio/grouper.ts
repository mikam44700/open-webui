/**
 * Mise en ordre de l'ecran Integrations.
 *
 * Trois regles, dans cet ordre :
 *
 *  1. ce que le client a deja connecte passe devant tout le reste ;
 *  2. les applications du quotidien sont rangees par usage (cf. categories.ts) ;
 *  3. le reste du catalogue n'apparait qu'a la demande, ou par la recherche.
 *
 * La recherche, elle, porte sur le catalogue ENTIER : ranger ne doit jamais
 * revenir a cacher.
 */

import { CATEGORIE_PAR_APPLICATION, CATEGORIES, nomAffiche } from './categories';
import type { ApplicationAffichee } from './etat';

export type Section = {
	id: string;
	libelle: string;
	applications: ApplicationAffichee[];
};

/** Enleve accents et casse : « Réseaux » se trouve en tapant « reseaux ». */
export const normaliser = (texte: string): string =>
	`${texte ?? ''}`.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();

/**
 * Filtre sur le nom affiche ET sur l'identifiant Composio.
 *
 * Chercher « agenda » doit trouver Google Calendar, dont le nom d'origine ne
 * contient pas le mot — d'ou la recherche sur le nom francais aussi.
 */
export const filtrer = (
	applications: ApplicationAffichee[],
	recherche: string
): ApplicationAffichee[] => {
	const terme = normaliser(recherche);
	if (!terme) return applications;
	return applications.filter((application) => {
		const slug = normaliser(application.slug);
		return (
			normaliser(nomAffiche(application.slug, application.nom)).includes(terme) ||
			normaliser(application.nom).includes(terme) ||
			slug.includes(terme)
		);
	});
};

/**
 * Range les applications en sections presentables.
 *
 * `connectees` vient toujours en premier, meme si l'application appartient par
 * ailleurs a une categorie : le client cherche d'abord ce qui marche deja.
 * Une section vide n'est jamais rendue.
 */
export const grouper = (applications: ApplicationAffichee[]): Section[] => {
	const parSlug = new Map(applications.map((a) => [`${a.slug}`.toLowerCase(), a]));
	const sections: Section[] = [];

	const connectees = applications.filter((a) => a.etat === 'connectee');
	if (connectees.length) {
		sections.push({ id: 'connectees', libelle: 'Connectées', applications: connectees });
	}

	for (const categorie of CATEGORIES) {
		const contenu = categorie.applications
			.map((slug) => parSlug.get(slug))
			.filter((a): a is ApplicationAffichee => a !== undefined && a.etat !== 'connectee');
		if (contenu.length) {
			sections.push({ id: categorie.id, libelle: categorie.libelle, applications: contenu });
		}
	}

	return sections;
};

/** Le reste du catalogue : ni connecte, ni range dans une categorie. */
export const horsCategories = (applications: ApplicationAffichee[]): ApplicationAffichee[] =>
	applications.filter(
		(application) =>
			application.etat !== 'connectee' &&
			!CATEGORIE_PAR_APPLICATION.has(`${application.slug}`.toLowerCase())
	);
