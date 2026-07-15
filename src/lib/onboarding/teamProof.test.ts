import { describe, it, expect } from 'vitest';
import { buildTeamProof, TEAM_PROOF_ORDER } from './teamProof';
import { EMPTY_CONTEXT, type CompanyContext } from './companySynthesis';

// Équipe au complet RÉELLEMENT créée (cas nominal après le provisionnement du socle).
const ALL = [...TEAM_PROOF_ORDER];

const FULL: CompanyContext = {
	...EMPTY_CONTEXT,
	offre: 'Plomberie et chauffage pour particuliers',
	tonDeMarque: 'chaleureux, direct',
	clienteleCible: 'propriétaires de maisons individuelles',
	services: ['Dépannage', 'Installation de chaudières']
};

describe('buildTeamProof', () => {
	it('produit une ligne par agent du socle, dans l’ordre défini', () => {
		const lines = buildTeamProof(FULL, ALL);
		expect(lines).toHaveLength(TEAM_PROOF_ORDER.length);
		expect(lines.map((l) => l.id)).toEqual([...TEAM_PROOF_ORDER]);
	});

	it('n’inclut jamais Mike (le narrateur/orchestrateur)', () => {
		const lines = buildTeamProof(FULL, ALL);
		expect(lines.some((l) => l.id === 'mike-chef-orchestre')).toBe(false);
	});

	it('résout prénom, rôle et avatar depuis les templates réels', () => {
		const emma = buildTeamProof(FULL, ALL).find((l) => l.id === 'assistant-administratif');
		expect(emma?.firstName).toBe('Emma');
		expect(emma?.role).toBe('Assistant administratif');
		expect(emma?.image).toContain('emma');
	});

	it('ancre la preuve sur un vrai bout du contexte quand il est renseigné', () => {
		const lines = buildTeamProof(FULL, ALL);
		const maxime = lines.find((l) => l.id === 'commercial-devis');
		const emma = lines.find((l) => l.id === 'assistant-administratif');
		const nicolas = lines.find((l) => l.id === 'redacteur-de-documents');
		expect(maxime?.proof).toContain('Plomberie');
		expect(emma?.proof).toContain('propriétaires');
		expect(nicolas?.proof).toContain('chaleureux');
	});

	it('retombe sur des phrases de repli honnêtes si le contexte est vide', () => {
		const lines = buildTeamProof(EMPTY_CONTEXT, ALL);
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
		const maxime = buildTeamProof(longCtx, ALL).find((l) => l.id === 'commercial-devis');
		// Preuve = 1re phrase ENTIÈRE (virgules internes conservées), coupée au 1er point, JAMAIS
		// d'ellipse. La 2e phrase est écartée. L'affichage est court sans rien couper en plein mot.
		expect(maxime?.proof).toBe(
			'Connaît votre offre : Solutions complètes de plomberie, chauffage et climatisation'
		);
		expect(maxime?.proof).not.toContain('…');
		expect(maxime?.proof).not.toContain('énergies renouvelables'); // 2e phrase écartée
	});
});

// L'écran final est une PREUVE (D27) : il ne montre que des agents qui EXISTENT. Avant le
// provisionnement du socle (2026-07-15), il lisait le catalogue et présentait donc 6 agents à un
// client qui n'en avait aucun — la première promesse du produit était fausse.
describe('buildTeamProof — ne montre que l’équipe réellement créée', () => {
	it('écarte un agent du socle absent du moteur', () => {
		const present = ALL.filter((id) => id !== 'veille'); // Léo n'a pas pu être créé
		const lines = buildTeamProof(FULL, present);

		expect(lines.map((l) => l.id)).not.toContain('veille');
		expect(lines).toHaveLength(TEAM_PROOF_ORDER.length - 1);
	});

	it('ne montre RIEN si aucun agent n’existe — jamais une équipe imaginaire', () => {
		expect(buildTeamProof(FULL, [])).toEqual([]);
	});

	it('garde l’ordre défini, quel que soit l’ordre rendu par le moteur', () => {
		const shuffled = ['veille', 'commercial-devis', 'agent-obsidian'];
		const lines = buildTeamProof(FULL, shuffled);
		expect(lines.map((l) => l.id)).toEqual(['agent-obsidian', 'commercial-devis', 'veille']);
	});

	it('ignore les agents hors socle présents chez le dirigeant (Erik, Sofia…)', () => {
		const lines = buildTeamProof(FULL, [...ALL, 'chasseur-clients', 'conformite-juridique']);
		expect(lines.map((l) => l.id)).toEqual([...TEAM_PROOF_ORDER]);
	});
});
