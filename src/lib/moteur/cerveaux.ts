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
						connecte: fournisseur?.authenticated !== false
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
 * Les cerveaux reellement utilisables, groupes par fournisseur.
 *
 * Le catalogue contient une cinquantaine de fournisseurs, dont la plupart sans
 * compte branche : les proposer dans le selecteur du chat serait promettre un
 * choix qui echouerait. Ils restent visibles dans la page Moteur, ou l'on
 * branche justement les comptes.
 *
 * Le fournisseur actif passe en tete : c'est celui que l'on relit le plus.
 */
export const cerveauxDisponibles = (
	cerveaux: Cerveau[],
	actif: CerveauActif
): { fournisseur: string; nom: string; cerveaux: Cerveau[] }[] => {
	const groupes = new Map<string, { fournisseur: string; nom: string; cerveaux: Cerveau[] }>();

	for (const cerveau of cerveaux) {
		if (!cerveau.connecte) continue;
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
