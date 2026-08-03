import { describe, expect, it } from 'vitest';

import {
	COLONNES,
	STATUTS_MOTEUR,
	attendLeTemps,
	colonneDe,
	estArchivee,
	estInconnue,
	peutEtreDebloquee,
	repartir,
	type Tache
} from './colonnes';

const tache = (id: string, statut: string, typeBlocage: string | null = null): Tache => ({
	id,
	titre: id,
	statut,
	typeBlocage
});

describe('colonneDe', () => {
	it('range chaque statut du moteur dans une colonne', () => {
		expect(colonneDe('triage')).toBe('trier');
		expect(colonneDe('todo')).toBe('afaire');
		expect(colonneDe('scheduled')).toBe('afaire');
		expect(colonneDe('ready')).toBe('afaire');
		expect(colonneDe('running')).toBe('encours');
		expect(colonneDe('blocked')).toBe('bloque');
		expect(colonneDe('review')).toBe('avalider');
		expect(colonneDe('done')).toBe('termine');
	});

	it('laisse les archivees hors des colonnes', () => {
		expect(colonneDe('archived')).toBe(null);
	});

	// Le defaut exact de hermes-desktop : `scheduled` et `review` tombaient dans
	// « todo » sans que rien ne le signale. Ici un statut inconnu ne prend la
	// place de personne.
	it('ne range pas un statut inconnu dans une colonne au hasard', () => {
		expect(colonneDe('quantum_superposition')).toBe(null);
		expect(colonneDe('')).toBe(null);
	});
});

describe('couverture des statuts du moteur', () => {
	// Liste figee d'apres hermes_cli/kanban_db.py:102. Un statut ajoute cote
	// moteur fait tomber ce test plutot que de disparaitre a l'ecran.
	it('connait les neuf statuts canoniques', () => {
		expect([...STATUTS_MOTEUR].sort()).toEqual(
			[
				'archived',
				'blocked',
				'done',
				'ready',
				'review',
				'running',
				'scheduled',
				'todo',
				'triage'
			].sort()
		);
	});

	it('couvre tous les statuts non archives par une colonne', () => {
		for (const statut of STATUTS_MOTEUR) {
			if (statut === 'archived') continue;
			expect(colonneDe(statut), `${statut} sans colonne`).not.toBe(null);
		}
	});

	it('declare six colonnes, dans l ordre de lecture', () => {
		expect(COLONNES.map((c) => c.cle)).toEqual([
			'trier',
			'afaire',
			'encours',
			'bloque',
			'avalider',
			'termine'
		]);
	});

	it('donne une cle de traduction a chaque colonne', () => {
		for (const colonne of COLONNES) {
			expect(colonne.cleI18n.trim()).not.toBe('');
		}
	});
});

describe('estArchivee / estInconnue', () => {
	it('reconnait une archivee', () => {
		expect(estArchivee('archived')).toBe(true);
		expect(estArchivee('done')).toBe(false);
	});

	it('reconnait un statut que le moteur ne devrait pas produire', () => {
		expect(estInconnue('zzz')).toBe(true);
		expect(estInconnue('running')).toBe(false);
		expect(estInconnue('archived')).toBe(false);
	});

	it('ignore la casse et les espaces', () => {
		expect(colonneDe(' Running ')).toBe('encours');
		expect(estInconnue('RUNNING')).toBe(false);
	});
});

describe('peutEtreDebloquee', () => {
	// Regle centrale : proposer de debloquer une tache qui attend simplement sa
	// dependance inviterait le client a casser l'ordre de travail que
	// l'assistant a lui-meme etabli.
	it('rend vrai quand l assistant attend une decision humaine', () => {
		expect(peutEtreDebloquee(tache('t1', 'blocked', 'needs_input'))).toBe(true);
	});

	it('rend vrai pour un blocage ancien sans type', () => {
		expect(peutEtreDebloquee(tache('t2', 'blocked', null))).toBe(true);
	});

	it('rend faux quand la tache attend une autre tache', () => {
		expect(peutEtreDebloquee(tache('t3', 'blocked', 'dependency'))).toBe(false);
	});

	it('rend faux quand il manque un outil ou un acces', () => {
		expect(peutEtreDebloquee(tache('t4', 'blocked', 'capability'))).toBe(false);
	});

	it('rend faux pour un incident passager', () => {
		expect(peutEtreDebloquee(tache('t5', 'blocked', 'transient'))).toBe(false);
	});

	it('rend faux pour une tache qui n est pas bloquee', () => {
		expect(peutEtreDebloquee(tache('t6', 'running', 'needs_input'))).toBe(false);
		expect(peutEtreDebloquee(tache('t7', 'done'))).toBe(false);
	});

	it('rend faux pour un type de blocage inconnu', () => {
		expect(peutEtreDebloquee(tache('t8', 'blocked', 'zzz'))).toBe(false);
	});
});

describe('attendLeTemps', () => {
	// Le moteur ne stocke aucune date de demarrage (data-model.md) : on peut dire
	// QUE la tache attend le temps, jamais QUAND elle repartira.
	it('reconnait une tache programmee', () => {
		expect(attendLeTemps(tache('t1', 'scheduled'))).toBe(true);
	});

	it('rend faux pour les autres', () => {
		expect(attendLeTemps(tache('t2', 'todo'))).toBe(false);
		expect(attendLeTemps(tache('t3', 'blocked', 'needs_input'))).toBe(false);
	});
});

describe('repartir', () => {
	const liste = [
		tache('a', 'triage'),
		tache('b', 'todo'),
		tache('c', 'scheduled'),
		tache('d', 'ready'),
		tache('e', 'running'),
		tache('f', 'blocked', 'needs_input'),
		tache('g', 'review'),
		tache('h', 'done'),
		tache('i', 'archived'),
		tache('j', 'quantum_superposition')
	];

	it('place chaque tache dans une seule colonne', () => {
		const { colonnes } = repartir(liste);
		const vues = Object.values(colonnes).flatMap((t) => t.map((x) => x.id));
		expect(new Set(vues).size).toBe(vues.length);
	});

	it('regroupe les trois statuts de la colonne « a faire »', () => {
		const { colonnes } = repartir(liste);
		expect(colonnes.afaire.map((t) => t.id)).toEqual(['b', 'c', 'd']);
	});

	it('masque les archivees par defaut', () => {
		const { colonnes, archivees } = repartir(liste);
		const vues = Object.values(colonnes).flatMap((t) => t.map((x) => x.id));
		expect(vues).not.toContain('i');
		expect(archivees.map((t) => t.id)).toEqual(['i']);
	});

	it('montre les archivees sur demande, dans « termine »', () => {
		const { colonnes } = repartir(liste, { inclureArchivees: true });
		expect(colonnes.termine.map((t) => t.id)).toEqual(['h', 'i']);
	});

	it('sort les statuts inconnus a part plutot que de les perdre', () => {
		const { inconnues } = repartir(liste);
		expect(inconnues.map((t) => t.id)).toEqual(['j']);
	});

	// SC-002 : le compte affiche doit egaler le compte du moteur.
	it('ne perd aucune tache', () => {
		const { colonnes, archivees, inconnues } = repartir(liste);
		const total =
			Object.values(colonnes).reduce((n, t) => n + t.length, 0) +
			archivees.length +
			inconnues.length;
		expect(total).toBe(liste.length);
	});

	it('laisse la liste vide intacte', () => {
		const { colonnes, archivees, inconnues } = repartir([]);
		expect(Object.values(colonnes).every((t) => t.length === 0)).toBe(true);
		expect(archivees).toEqual([]);
		expect(inconnues).toEqual([]);
	});
});
