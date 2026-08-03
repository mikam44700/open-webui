/**
 * Les cerveaux du moteur — LunarIA V2.
 *
 * Hermes n'annonce qu'un seul modele sur `/v1/models` : `hermes-agent`, le nom
 * de la plateforme. Le modele qui reflechit vraiment (`gpt-5.6-sol` et ses
 * voisins) se choisit dans le moteur, jamais dans la requete de conversation :
 * le champ `model` du corps OpenAI est accepte puis ignore, et renvoye en echo.
 *
 * Un menu construit sur `/v1/models` afficherait donc une seule ligne, et un
 * menu construit sur des identifiants ecrits en dur mentirait sur ce qui repond.
 * D'ou ce module : il met a plat le catalogue reel du moteur
 * (`/api/v1/hermes/models/options`), seul endroit ou le choix a un effet.
 *
 * Fonctions pures, sans appel reseau : la page Moteur et le selecteur du chat
 * partagent la meme lecture du catalogue, et elle se teste seule.
 */

export type Cerveau = {
	/** Identifiant transmis au moteur, ex. `gpt-5.6-sol`. */
	id: string;
	/** Libelle affiche. Vaut l'identifiant a defaut de mieux. */
	titre: string;
	/** Fournisseur, ex. `openai-codex`. Absent sur les formes anciennes. */
	fournisseur?: string;
	/** Nom lisible du fournisseur, ex. « OpenAI Codex ». */
	nomFournisseur?: string;
	/** Faux quand le fournisseur est au catalogue mais sans compte branche. */
	connecte: boolean;
	/** Origine declaree par le moteur : `hermes`, `canonical`, `virtual`… */
	source?: string;
};

/** Couple actif tel que le moteur le declare — il fait foi, on ne le deduit pas. */
export type CerveauActif = {
	modele: string | null;
	fournisseur: string | null;
};

/**
 * Met le catalogue du moteur a plat.
 *
 * Forme principale observee sur Hermes 0.19 :
 *   { providers: [ { slug, name, models: [...], authenticated } ],
 *     model: "gpt-5.6-sol", provider: "openai-codex" }
 *
 * Les deux autres formes (tableau simple, objet indexe par fournisseur)
 * existent sur d'autres versions et ne coutent rien a garder.
 */
export const listerCerveaux = (reponse: any): Cerveau[] => {
	if (!reponse) return [];

	if (Array.isArray(reponse.providers)) {
		return reponse.providers.flatMap((fournisseur: any) => {
			const slug = `${fournisseur?.slug ?? fournisseur?.id ?? ''}`;
			const liste = Array.isArray(fournisseur?.models) ? fournisseur.models : [];
			return liste
				.map((entree: any) => {
					const id = typeof entree === 'string' ? entree : `${entree?.id ?? entree?.name ?? ''}`;
					return {
						id,
						titre: id,
						fournisseur: slug,
						nomFournisseur: `${fournisseur?.name ?? slug}`,
						connecte: fournisseur?.authenticated !== false,
						source: fournisseur?.source
					};
				})
				.filter((cerveau: Cerveau) => cerveau.id);
		});
	}

	const source = reponse.options ?? reponse.models ?? reponse.data ?? reponse;

	if (Array.isArray(source)) {
		return source
			.map((entree: any) =>
				typeof entree === 'string'
					? { id: entree, titre: entree, connecte: true }
					: {
							id: `${entree?.id ?? entree?.model ?? entree?.name ?? ''}`,
							titre: `${entree?.title ?? entree?.label ?? entree?.id ?? entree?.model ?? entree?.name ?? ''}`,
							fournisseur: entree?.provider ?? entree?.owned_by,
							connecte: entree?.authenticated !== false
						}
			)
			.filter((cerveau: Cerveau) => cerveau.id);
	}

	if (typeof source === 'object') {
		return Object.entries(source)
			.flatMap(([fournisseur, liste]) =>
				(Array.isArray(liste) ? liste : []).map((entree: any) => {
					const id = typeof entree === 'string' ? entree : `${entree?.id ?? entree?.model ?? ''}`;
					return { id, titre: id, fournisseur, connecte: true };
				})
			)
			.filter((cerveau: Cerveau) => cerveau.id);
	}

	return [];
};

/** Le couple actif declare par le moteur, sans deduction. */
export const cerveauActif = (reponse: any): CerveauActif => ({
	modele: reponse?.model ?? null,
	fournisseur: reponse?.provider ?? null
});

/** Actif seulement si le nom ET le fournisseur correspondent. */
export const estActif = (cerveau: Cerveau, actif: CerveauActif): boolean =>
	cerveau.id === actif.modele &&
	(!actif.fournisseur || !cerveau.fournisseur || cerveau.fournisseur === actif.fournisseur);

/**
 * Etat des comptes, indexe par fournisseur : `true` = compte connecte.
 *
 * Lu sur `/providers/oauth`, qui est la seule surface a distinguer un compte
 * appartenant au fournisseur d'un jeton emprunte a un autre outil. Le
 * catalogue, lui, se contente d'un `authenticated: true` global.
 */
export const comptesParFournisseur = (reponse: any): Record<string, boolean> => {
	const liste = Array.isArray(reponse?.providers) ? reponse.providers : [];
	const comptes: Record<string, boolean> = {};

	for (const entree of liste) {
		const id = `${entree?.id ?? entree?.slug ?? ''}`;
		if (!id) continue;
		comptes[id] = Boolean(entree?.status?.logged_in);
	}

	return comptes;
};

/**
 * Les cerveaux reellement utilisables, groupes par fournisseur.
 *
 * Trois ecartements, tous fondes sur ce que le moteur declare — jamais sur un
 * nom de fournisseur ecrit en dur, sans quoi brancher une cle demain ne
 * suffirait pas a faire reapparaitre son groupe :
 *
 *   1. `connecte: false` — au catalogue, mais rien de branche derriere.
 *   2. `source: 'virtual'` — les agregateurs (« moa ») ne sont pas des modeles.
 *   3. un compte declare NON connecte dans `comptes`. C'est le cas d'Anthropic
 *      tant que ses modeles ne viennent que de la session de Claude Code : le
 *      catalogue le dit authentifie, mais Hermes repond `logged_in: false` sur
 *      son compte a lui. Poser une vraie cle le fait passer a `true` et le
 *      groupe revient de lui-meme.
 *
 * Un fournisseur absent de `comptes` est conserve : les fournisseurs a cle API
 * pure n'ont pas d'entree de compte, et `comptes` vide (moteur injoignable sur
 * cette route) ne doit rien masquer — on prefere trop montrer que mentir.
 *
 * Le fournisseur actif passe en tete : c'est celui que l'on relit le plus.
 */
export const cerveauxDisponibles = (
	cerveaux: Cerveau[],
	actif: CerveauActif,
	comptes: Record<string, boolean> = {}
): { fournisseur: string; nom: string; cerveaux: Cerveau[] }[] => {
	const groupes = new Map<string, { fournisseur: string; nom: string; cerveaux: Cerveau[] }>();

	for (const cerveau of cerveaux) {
		if (!cerveau.connecte) continue;
		if (cerveau.source === 'virtual') continue;
		if (cerveau.fournisseur && comptes[cerveau.fournisseur] === false) continue;
		const cle = cerveau.fournisseur ?? '';
		if (!groupes.has(cle)) {
			groupes.set(cle, { fournisseur: cle, nom: cerveau.nomFournisseur ?? cle, cerveaux: [] });
		}
		groupes.get(cle)!.cerveaux.push(cerveau);
	}

	return [...groupes.values()].sort((a, b) => {
		if (a.fournisseur === actif.fournisseur) return -1;
		if (b.fournisseur === actif.fournisseur) return 1;
		return a.nom.localeCompare(b.nom);
	});
};
