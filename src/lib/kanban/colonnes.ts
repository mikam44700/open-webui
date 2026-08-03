/**
 * Des neuf etats du moteur aux six colonnes de l'ecran.
 *
 * Le moteur distingue neuf etats (hermes_cli/kanban_db.py:102). Les montrer tels
 * quels a un dirigeant serait illisible ; les fondre au hasard ferait revenir le
 * defaut de hermes-desktop, ou `scheduled` et `review` tombaient dans « todo »
 * sans que rien ne le signale — une tache programmee pour la semaine prochaine
 * s'affichait comme a faire maintenant.
 *
 * D'ou la regle qui tient tout ce fichier : on regroupe pour la lecture, on ne
 * perd jamais. Un etat que ce module ne connait pas ressort dans `inconnues`
 * plutot que d'aller grossir une colonne au hasard.
 */

/** Les etats que le moteur sait produire. Figes d'apres kanban_db.VALID_STATUSES. */
export const STATUTS_MOTEUR = [
	'triage',
	'todo',
	'scheduled',
	'ready',
	'running',
	'blocked',
	'review',
	'done',
	'archived'
] as const;

export type StatutMoteur = (typeof STATUTS_MOTEUR)[number];

export type CleColonne = 'trier' | 'afaire' | 'encours' | 'bloque' | 'avalider' | 'termine';

/**
 * Les motifs de blocage typés du moteur (kanban_db.VALID_BLOCK_KINDS).
 *
 * « Bloque » ne veut pas dire la meme chose selon le motif, et un seul appelle
 * une action du client.
 */
export const TYPES_BLOCAGE = ['needs_input', 'dependency', 'capability', 'transient'] as const;

export type TypeBlocage = (typeof TYPES_BLOCAGE)[number];

export type Tache = {
	id: string;
	titre: string;
	statut: string;
	typeBlocage?: string | null;
};

export type Colonne = {
	cle: CleColonne;
	/** Cle de traduction : le libelle se resout dans le composant, pas ici. */
	cleI18n: string;
	statuts: StatutMoteur[];
};

/** L'ordre du tableau est l'ordre de lecture, de gauche a droite. */
export const COLONNES: Colonne[] = [
	{ cle: 'trier', cleI18n: 'À trier', statuts: ['triage'] },
	{ cle: 'afaire', cleI18n: 'À faire', statuts: ['todo', 'scheduled', 'ready'] },
	{ cle: 'encours', cleI18n: 'En cours', statuts: ['running'] },
	{ cle: 'bloque', cleI18n: 'Bloqué', statuts: ['blocked'] },
	{ cle: 'avalider', cleI18n: 'À valider', statuts: ['review'] },
	{ cle: 'termine', cleI18n: 'Terminé', statuts: ['done'] }
];

const normaliser = (valeur: string | null | undefined): string =>
	`${valeur ?? ''}`.trim().toLowerCase();

const PAR_STATUT = new Map<string, CleColonne>(
	COLONNES.flatMap((colonne) => colonne.statuts.map((statut) => [statut, colonne.cle] as const))
);

/**
 * La colonne d'un statut, ou `null`.
 *
 * `null` couvre deux cas volontairement distincts pour l'appelant : une tache
 * archivee (rangee ailleurs) et un statut inconnu (signale). C'est `repartir`
 * qui les separe.
 */
export const colonneDe = (statut: string): CleColonne | null =>
	PAR_STATUT.get(normaliser(statut)) ?? null;

export const estArchivee = (statut: string): boolean => normaliser(statut) === 'archived';

/** Un etat que le moteur ne devrait pas produire — donc a montrer, pas a ranger. */
export const estInconnue = (statut: string): boolean =>
	!(STATUTS_MOTEUR as readonly string[]).includes(normaliser(statut));

/**
 * Le client peut-il relancer cette tache ?
 *
 * Vrai seulement quand l'assistant attend une decision humaine, ou pour un
 * blocage ancien sans type — dans le doute on montre la porte plutot que de la
 * cacher.
 *
 * Faux pour `dependency` : proposer de debloquer une tache qui attend
 * simplement qu'une autre se termine inviterait le client a casser l'ordre de
 * travail que l'assistant a lui-meme etabli.
 */
export const peutEtreDebloquee = (tache: Tache): boolean => {
	if (normaliser(tache.statut) !== 'blocked') return false;

	const type = normaliser(tache.typeBlocage);
	if (!type) return true;

	return type === 'needs_input';
};

/**
 * La tache attend le temps, pas une reponse.
 *
 * Le moteur ne stocke aucune date de demarrage : `schedule_task` gare la tache
 * en attendant qu'un cron externe ou une action la reveille. On peut donc dire
 * QU'elle attend, jamais QUAND elle repartira.
 */
export const attendLeTemps = (tache: Tache): boolean => normaliser(tache.statut) === 'scheduled';

export type Repartition<T extends Tache> = {
	colonnes: Record<CleColonne, T[]>;
	archivees: T[];
	inconnues: T[];
};

const colonnesVides = <T extends Tache>(): Record<CleColonne, T[]> =>
	Object.fromEntries(COLONNES.map((colonne) => [colonne.cle, [] as T[]])) as Record<
		CleColonne,
		T[]
	>;

/**
 * Range les taches par colonne, sans en perdre une seule.
 *
 * Trois sorties plutot qu'une : les colonnes, les archivees (masquees par
 * defaut) et les inconnues. La somme des trois egale toujours l'entree — c'est
 * ce que verifie le test, et c'est le critere SC-002.
 */
export const repartir = <T extends Tache>(
	taches: T[],
	options: { inclureArchivees?: boolean } = {}
): Repartition<T> => {
	const colonnes = colonnesVides<T>();
	const archivees: T[] = [];
	const inconnues: T[] = [];

	for (const tache of taches) {
		if (estArchivee(tache.statut)) {
			archivees.push(tache);
			// Une archivee demandee rejoint « Termine » : c'est la ou le client va
			// la chercher, et lui donner sa propre colonne n'apprendrait rien.
			if (options.inclureArchivees) colonnes.termine.push(tache);
			continue;
		}

		const cle = colonneDe(tache.statut);
		if (cle) colonnes[cle].push(tache);
		else inconnues.push(tache);
	}

	return { colonnes, archivees, inconnues };
};
