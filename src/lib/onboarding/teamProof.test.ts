import { describe, it, expect } from 'vitest';
import { buildTeamProof, TEAM_PROOF_ORDER } from './teamProof';
import { EMPTY_CONTEXT, type CompanyContext } from './companySynthesis';

const FULL: CompanyContext = {
	...EMPTY_CONTEXT,
	offre: 'Plomberie et chauffage pour particuliers',
	tonDeMarque: 'chaleureux, direct',
	clienteleCible: 'propriétaires de maisons individuelles',
	services: ['Dépannage', 'Installation de chaudières']
};

describe('buildTeamProof', () => {
	it('produit une ligne par agent du socle, dans l’ordre défini', () => {
		const lines = buildTeamProof(FULL);
		expect(lines).toHaveLength(TEAM_PROOF_ORDER.length);
		expect(lines.map((l) => l.id)).toEqual([...TEAM_PROOF_ORDER]);
	});

	it('n’inclut jamais Mike (le narrateur/orchestrateur)', () => {
		const lines = buildTeamProof(FULL);
		expect(lines.some((l) => l.id === 'mike-chef-orchestre')).toBe(false);
	});

	it('résout prénom, rôle et avatar depuis les templates réels', () => {
		const emma = buildTeamProof(FULL).find((l) => l.id === 'assistant-administratif');
		expect(emma?.firstName).toBe('Emma');
		expect(emma?.role).toBe('Assistant administratif');
		expect(emma?.image).toContain('emma');
	});

	it('ancre la preuve sur un vrai bout du contexte quand il est renseigné', () => {
		const lines = buildTeamProof(FULL);
		const maxime = lines.find((l) => l.id === 'commercial-devis');
		const emma = lines.find((l) => l.id === 'assistant-administratif');
		const nicolas = lines.find((l) => l.id === 'redacteur-documents');
		expect(maxime?.proof).toContain('Plomberie');
		expect(emma?.proof).toContain('propriétaires');
		expect(nicolas?.proof).toContain('chaleureux');
	});

	it('retombe sur des phrases de repli honnêtes si le contexte est vide', () => {
		const lines = buildTeamProof(EMPTY_CONTEXT);
		expect(lines).toHaveLength(TEAM_PROOF_ORDER.length);
		const maxime = lines.find((l) => l.id === 'commercial-devis');
		expect(maxime?.proof).toBe('Prêt à suivre vos devis et relances');
		// Aucune preuve ne doit contenir un placeholder vide type « : ».
		expect(lines.every((l) => !/:\s*$/.test(l.proof))).toBe(true);
	});

	it('garde la 1re phrase en entier (virgules incluses), sans ellipse', () => {
		const longCtx: CompanyContext = {
			...EMPTY_CONTEXT,
			offre:
				'Solutions complètes de plomberie, chauffage et climatisation. Nous intervenons aussi en énergies renouvelables pour les particuliers exigeants.'
		};
		const maxime = buildTeamProof(longCtx).find((l) => l.id === 'commercial-devis');
		// Preuve = 1re phrase ENTIÈRE (virgules internes conservées), coupée au 1er point, JAMAIS
		// d'ellipse. La 2e phrase est écartée. L'affichage est court sans rien couper en plein mot.
		expect(maxime?.proof).toBe(
			'Connaît votre offre : Solutions complètes de plomberie, chauffage et climatisation'
		);
		expect(maxime?.proof).not.toContain('…');
		expect(maxime?.proof).not.toContain('énergies renouvelables'); // 2e phrase écartée
	});
});
