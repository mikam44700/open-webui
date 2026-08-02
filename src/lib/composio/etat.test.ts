import { describe, expect, it } from 'vitest';

import { cleAPoser, composerApplications, etatDeConnexion, messageEtat } from './etat';

const app = (slug: string, nom = slug) => ({ slug, nom });

describe('etatDeConnexion', () => {
	it('reconnait un compte actif', () => {
		expect(etatDeConnexion('ACTIVE')).toBe('connectee');
		expect(etatDeConnexion('active')).toBe('connectee');
	});

	it('reconnait une autorisation en chemin', () => {
		expect(etatDeConnexion('INITIATED')).toBe('en_cours');
	});

	it('reconnait une connexion perdue', () => {
		expect(etatDeConnexion('EXPIRED')).toBe('echouee');
	});

	// Un etat inconnu ne doit pas etre presente comme une panne (D27).
	it('retombe sur non connectee pour un etat inconnu', () => {
		expect(etatDeConnexion('QUELQUE_CHOSE')).toBe('non_connectee');
		expect(etatDeConnexion('')).toBe('non_connectee');
	});
});

describe('cleAPoser', () => {
	it('demande la cle quand rien n est pose', () => {
		expect(cleAPoser({ cle: false, etat: 'absente' })).toBe(true);
		expect(cleAPoser(null)).toBe(true);
	});

	it('demande une nouvelle cle quand Composio la refuse', () => {
		expect(cleAPoser({ cle: true, etat: 'refusee' })).toBe(true);
	});

	it('ne redemande rien quand la cle marche', () => {
		expect(cleAPoser({ cle: true, etat: 'ok' })).toBe(false);
	});

	// Composio muet n'est pas une cle fausse : on ne renvoie pas le client
	// chercher une nouvelle cle pour une panne passagere.
	it('ne redemande rien quand Composio est seulement injoignable', () => {
		expect(cleAPoser({ cle: true, etat: 'injoignable' })).toBe(false);
	});
});

describe('messageEtat', () => {
	it('ne dit rien quand tout va bien', () => {
		expect(messageEtat({ cle: true, etat: 'ok' })).toBeNull();
		expect(messageEtat({ cle: false, etat: 'absente' })).toBeNull();
	});

	it('distingue la cle refusee de la source muette', () => {
		expect(messageEtat({ cle: true, etat: 'refusee' })).toContain('refusée');
		expect(messageEtat({ cle: true, etat: 'injoignable' })).toContain('ne répond pas');
	});
});

describe('composerApplications', () => {
	it('marque connectee une application qui a un compte actif', () => {
		const resultat = composerApplications(
			[app('gmail', 'Gmail')],
			[{ id: 'c1', application: 'gmail', etat: 'ACTIVE' }]
		);
		expect(resultat[0]).toMatchObject({ slug: 'gmail', etat: 'connectee', connexionId: 'c1' });
	});

	it('laisse non connectee une application sans compte', () => {
		const resultat = composerApplications([app('drive', 'Drive')], []);
		expect(resultat[0]).toMatchObject({ etat: 'non_connectee', connexionId: null });
	});

	it('remonte les applications connectees en tete, puis par ordre alphabetique', () => {
		const resultat = composerApplications(
			[app('slack', 'Slack'), app('drive', 'Drive'), app('gmail', 'Gmail')],
			[{ id: 'c1', application: 'slack', etat: 'ACTIVE' }]
		);
		expect(resultat.map((a) => a.slug)).toEqual(['slack', 'drive', 'gmail']);
	});

	// Une tentative abandonnee ne doit pas masquer une connexion qui marche.
	it('prefere le compte actif quand plusieurs existent pour une application', () => {
		const resultat = composerApplications(
			[app('gmail', 'Gmail')],
			[
				{ id: 'abandon', application: 'gmail', etat: 'INITIATED' },
				{ id: 'bon', application: 'gmail', etat: 'ACTIVE' }
			]
		);
		expect(resultat[0]).toMatchObject({ etat: 'connectee', connexionId: 'bon' });
	});

	it('ignore une connexion sans application', () => {
		const resultat = composerApplications(
			[app('gmail', 'Gmail')],
			[{ id: 'vide', application: '', etat: 'ACTIVE' }]
		);
		expect(resultat[0]).toMatchObject({ etat: 'non_connectee', connexionId: null });
	});

	it('compare les identifiants sans tenir compte de la casse', () => {
		const resultat = composerApplications(
			[app('GMAIL', 'Gmail')],
			[{ id: 'c1', application: 'gmail', etat: 'ACTIVE' }]
		);
		expect(resultat[0]).toMatchObject({ etat: 'connectee', connexionId: 'c1' });
	});
});
