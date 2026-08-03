import { describe, expect, it } from 'vitest';

import { alerteChapeau, etatDeLecture, lectureDepuisErreur, type Lecture } from './etat';

const ok = <T>(donnees: T): Lecture<T> => ({ etat: 'ok', donnees });

describe('lectureDepuisErreur', () => {
	// Deux non-reponses de nature opposee : un moteur coupe (temporaire, ca
	// revient) et un registre non installe (permanent, ca se regle par une
	// installation). Les confondre ferait afficher « le moteur ne repond pas » a
	// quelqu'un dont le moteur va parfaitement bien.
	it('lit un 404 comme un registre absent', () => {
		expect(lectureDepuisErreur({ status: 404 }).etat).toBe('absent');
	});

	it('lit un 503 comme un moteur injoignable', () => {
		expect(lectureDepuisErreur({ status: 503 }).etat).toBe('injoignable');
	});

	it('lit un 504 comme un moteur injoignable', () => {
		expect(lectureDepuisErreur({ status: 504 }).etat).toBe('injoignable');
	});

	// Regle D27 : dans le doute on ne crie pas a la panne.
	it('lit une erreur sans code comme un etat inconnu', () => {
		expect(lectureDepuisErreur({}).etat).toBe('inconnu');
		expect(lectureDepuisErreur(new Error('boom')).etat).toBe('inconnu');
		expect(lectureDepuisErreur(null).etat).toBe('inconnu');
	});

	it('lit les autres codes comme un etat inconnu', () => {
		expect(lectureDepuisErreur({ status: 500 }).etat).toBe('inconnu');
		expect(lectureDepuisErreur({ status: 403 }).etat).toBe('inconnu');
	});

	it('accepte un code niche dans la reponse', () => {
		expect(lectureDepuisErreur({ response: { status: 503 } }).etat).toBe('injoignable');
	});
});

describe('etatDeLecture', () => {
	it('rend ok quand tout repond', () => {
		expect(etatDeLecture([ok(1), ok(2)])).toBe('ok');
	});

	// Le registre absent prime : c'est la reponse la plus precise qu'on ait, et
	// elle explique tout le reste.
	it('rend absent des qu une source dit que le registre n est pas la', () => {
		expect(etatDeLecture([ok(1), { etat: 'absent' }])).toBe('absent');
	});

	it('rend injoignable quand le moteur ne repond pas', () => {
		expect(etatDeLecture([ok(1), { etat: 'injoignable' }])).toBe('injoignable');
	});

	it('fait primer absent sur injoignable', () => {
		expect(etatDeLecture([{ etat: 'injoignable' }, { etat: 'absent' }])).toBe('absent');
	});

	it('rend inconnu plutot que de conclure', () => {
		expect(etatDeLecture([ok(1), { etat: 'inconnu' }])).toBe('inconnu');
	});

	it('fait primer injoignable sur inconnu', () => {
		expect(etatDeLecture([{ etat: 'inconnu' }, { etat: 'injoignable' }])).toBe('injoignable');
	});

	it('rend ok sur une liste vide', () => {
		expect(etatDeLecture([])).toBe('ok');
	});
});

describe('alerteChapeau', () => {
	it('ne dit rien quand tout va bien', () => {
		expect(alerteChapeau([ok(1), ok(2)])).toBe(null);
	});

	// Corollaire de D27 : quand plusieurs sources dependent d'un meme pont et que
	// ce pont est coupe, une seule alerte, pas une pile d'« indisponible ».
	it('ne rend qu une seule alerte quand trois sources tombent ensemble', () => {
		const alerte = alerteChapeau([
			{ etat: 'injoignable' },
			{ etat: 'injoignable' },
			{ etat: 'injoignable' }
		]);
		expect(alerte).not.toBe(null);
		expect(alerte?.etat).toBe('injoignable');
	});

	it('ne leve pas d alerte pour un registre absent', () => {
		// Ce n'est pas une panne : c'est une fonction non installee. La page
		// l'explique, elle ne la signale pas en rouge.
		const alerte = alerteChapeau([{ etat: 'absent' }]);
		expect(alerte?.etat).toBe('absent');
		expect(alerte?.gravite).toBe('information');
	});

	it('signale une injoignabilite comme un avertissement, pas une panne', () => {
		expect(alerteChapeau([{ etat: 'injoignable' }])?.gravite).toBe('avertissement');
	});

	it('signale un etat inconnu sans dramatiser', () => {
		expect(alerteChapeau([{ etat: 'inconnu' }])?.gravite).toBe('avertissement');
	});

	it('donne une cle de traduction a chaque alerte', () => {
		for (const lectures of [[{ etat: 'absent' as const }], [{ etat: 'injoignable' as const }]]) {
			expect(alerteChapeau(lectures)?.cleI18n.trim()).not.toBe('');
		}
	});
});
