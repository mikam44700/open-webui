/**
 * Etat d'un fournisseur de modeles : ce qui autorise a dire « connecte ».
 *
 * Hermes repond « authentifie » des qu'il peut joindre un fournisseur, quelle
 * que soit la voie : une cle API posee ici, une session de compte ouverte
 * ailleurs sur la machine (trousseau du systeme, CLI deja connecte), ou une
 * variable d'environnement heritee de l'hote.
 *
 * Une carte de l'onglet « Cles API » ne parle que de cles. Confondre ces trois
 * voies y produisait un mensonge visible : la carte Anthropic s'affichait
 * « Cle connectee » alors qu'aucune cle n'avait jamais ete saisie, le champ de
 * saisie restait cache — donc impossible de brancher sa propre cle — et
 * « Retirer cette cle » echouait forcement puisqu'il n'y avait aucune cle a
 * retirer. Les sessions de compte se gerent dans l'onglet « Comptes ».
 *
 * D'ou la regle : pour un fournisseur a cle, seule une cle reellement enregistree
 * vaut « connecte ». Pour les autres (serveur local sans cle, compte OAuth,
 * authentification externe), on conserve le signal de Hermes.
 */

export type EtatFournisseur = 'active' | 'configured' | 'not_configured';

export type SignauxFournisseur = {
	/** Le fournisseur se branche par une cle API declaree au catalogue. */
	aCle: boolean;
	/** Une cle est reellement enregistree chez Hermes pour ce fournisseur. */
	cleEnregistree: boolean;
	/** Une session de compte est ouverte pour ce fournisseur. */
	compteConnecte: boolean;
	/** Hermes se declare capable de joindre ce fournisseur, voie non precisee. */
	joignable: boolean;
	/** Ce fournisseur est celui qui fait actuellement reflechir l'assistant. */
	courant: boolean;
};

export type EtatDerive = {
	etat: EtatFournisseur;
	/** Vrai seulement si une cle API est enregistree : ce que la carte annonce. */
	cle: boolean;
};

export const deriverEtat = (signaux: SignauxFournisseur): EtatDerive => {
	const authentifie = signaux.aCle
		? signaux.cleEnregistree
		: signaux.cleEnregistree || signaux.compteConnecte || signaux.joignable;

	return {
		etat: !authentifie ? 'not_configured' : signaux.courant ? 'active' : 'configured',
		cle: signaux.cleEnregistree
	};
};
