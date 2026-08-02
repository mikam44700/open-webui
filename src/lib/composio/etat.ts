/**
 * Ce que l'ecran Integrations a le droit d'affirmer sur Composio.
 *
 * Deux regles heritees de la page Moteur :
 *
 *  - une carte ne se dit branchee que sur une preuve, jamais sur un signal
 *    approchant (cf. lib/providers/etat.ts) ;
 *  - une source injoignable n'est pas une panne. `injoignable` et `refusee`
 *    sont deux choses differentes : la premiere se retente, la seconde demande
 *    une nouvelle cle (regle D27).
 */

import type { ApplicationComposio, ConnexionComposio, EtatComposio } from '$lib/apis/composio';

export type EtatApplication = 'connectee' | 'non_connectee' | 'en_cours' | 'echouee';

export type ApplicationAffichee = ApplicationComposio & {
	etat: EtatApplication;
	connexionId: string | null;
};

/** Etats que Composio donne a un compte connecte, ramenes aux notres. */
const ETATS: Record<string, EtatApplication> = {
	ACTIVE: 'connectee',
	INITIATED: 'en_cours',
	INITIALIZING: 'en_cours',
	PENDING: 'en_cours',
	EXPIRED: 'echouee',
	FAILED: 'echouee',
	INACTIVE: 'echouee',
	DISABLED: 'echouee'
};

export const etatDeConnexion = (brut: string): EtatApplication =>
	ETATS[`${brut ?? ''}`.toUpperCase()] ?? 'non_connectee';

/** Le bloc de saisie de la cle doit-il rester ouvert ? */
export const cleAPoser = (etat: EtatComposio | null): boolean =>
	!etat || !etat.cle || etat.etat === 'refusee';

/**
 * Message d'entete, ou null quand tout va bien. On distingue explicitement la
 * cle refusee (action a faire) de Composio muet (rien a faire, ca revient).
 */
export const messageEtat = (etat: EtatComposio | null): string | null => {
	if (!etat || etat.etat === 'absente') return null;
	if (etat.etat === 'refusee')
		return 'Cette clé est refusée par Composio. Vérifiez la clé du projet de ce client.';
	if (etat.etat === 'injoignable')
		return 'Composio ne répond pas pour le moment. Les applications déjà connectées continuent de fonctionner.';
	return null;
};

/**
 * Croise le catalogue et les connexions du client.
 *
 * Une application connectee remonte en tete : c'est ce que le client cherche
 * en premier quand il revient sur l'ecran.
 */
export const composerApplications = (
	applications: ApplicationComposio[],
	connexions: ConnexionComposio[]
): ApplicationAffichee[] => {
	const parApplication = new Map<string, ConnexionComposio>();
	for (const connexion of connexions) {
		const slug = `${connexion.application ?? ''}`.toLowerCase();
		if (!slug) continue;
		const connue = parApplication.get(slug);
		// Une connexion active prime sur une tentative restee en chemin : sinon une
		// autorisation abandonnee masquerait une connexion qui marche.
		if (!connue || etatDeConnexion(connexion.etat) === 'connectee') {
			parApplication.set(slug, connexion);
		}
	}

	return applications
		.map((application) => {
			const connexion = parApplication.get(`${application.slug ?? ''}`.toLowerCase());
			return {
				...application,
				etat: connexion ? etatDeConnexion(connexion.etat) : ('non_connectee' as EtatApplication),
				connexionId: connexion?.id ?? null
			};
		})
		.sort(
			(a, b) =>
				Number(b.etat === 'connectee') - Number(a.etat === 'connectee') ||
				a.nom.localeCompare(b.nom, 'fr')
		);
};
