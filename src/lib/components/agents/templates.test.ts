import { describe, it, expect } from 'vitest';
import { AGENT_TEMPLATES, SOCLE_IDS } from './templates';

// L'IDENTITÉ D'UN AGENT EST SON `id`, JAMAIS SON `label`.
//
// Pourquoi ces tests (trou vérifié le 2026-07-15) : le nom du profil Hermes était fabriqué à partir
// du LIBELLÉ (`createAgent({ name: tpl.label })` → `slugify()` côté bridge). Le libellé étant la
// partie la plus cosmétique et la plus volatile, l'identité des agents changeait dans le dos de
// tout le monde :
//   - « Recherche & Veille » → profil `recherche-veille`, alors que Léo s'appelle `veille` sur le
//     disque : installer le template créait un SECOND Léo, sans le moindre conflit ni message.
//   - « Rédacteur de documents » → `redacteur-de-documents`, d'où l'écart avec l'id du template.
//   - Le code portait déjà un pansement (AgentList : « matchesMike seul ratait l'agent réel
//     (nom = slug du libellé) ») — on soignait le symptôme, pas la cause.
//
// Règle verrouillée ici : un `id` est un slug valide, donc `slugify(id) === id`, donc le nom du
// profil est STABLE et le libellé peut être réécrit autant qu'on veut.

// Miroir exact de `profiles_adapter.slugify` (bridge) : tout caractère hors [a-z0-9] devient « - ».
// Un id qui satisfait cette forme traverse slugify() sans être modifié.
const SLUG = /^[a-z0-9][a-z0-9-]*$/;

describe('identité des agents — l’id est la source de vérité', () => {
	it('chaque id est un slug valide (donc utilisable tel quel comme nom de profil)', () => {
		for (const t of AGENT_TEMPLATES) {
			expect(t.id, `id invalide : « ${t.id} »`).toMatch(SLUG);
			expect(t.id.length, `id trop long : « ${t.id} »`).toBeLessThanOrEqual(64);
		}
	});

	it('aucun id en double (deux agents ne peuvent pas se marcher dessus)', () => {
		const ids = AGENT_TEMPLATES.map((t) => t.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('tous les ids du socle existent bien dans le catalogue', () => {
		const ids = new Set(AGENT_TEMPLATES.map((t) => t.id));
		for (const id of SOCLE_IDS) {
			expect(ids.has(id), `SOCLE_IDS cite « ${id} », absent d’AGENT_TEMPLATES`).toBe(true);
		}
	});

	// Le disque fait foi (règle projet) : ces profils existent déjà, leur id ne doit plus bouger,
	// sinon une installation fabrique un doublon à côté de l'agent réel.
	it('les ids du socle collent aux profils réellement déployés', () => {
		const ids = new Set(AGENT_TEMPLATES.map((t) => t.id));
		for (const deploye of [
			'agent-obsidian',
			'assistant-administratif',
			'commercial-devis',
			'comptable-impayes',
			'redacteur-de-documents',
			'veille'
		]) {
			expect(ids.has(deploye), `aucun template n’a l’id « ${deploye} » (profil existant)`).toBe(true);
		}
	});

	it('chaque template a de quoi s’afficher (prénom, image, rôle)', () => {
		for (const t of AGENT_TEMPLATES) {
			expect(t.firstName, `firstName manquant : ${t.id}`).toBeTruthy();
			expect(t.image, `image manquante : ${t.id}`).toBeTruthy();
			expect(t.role, `role manquant : ${t.id}`).toBeTruthy();
		}
	});
});

describe('vocabulaire interdit dans les prompts', () => {
	// « charge mentale » = mot de consultant, pas de dirigeant (recherche positionnement 2026-07-15).
	it('aucun agent ne dit « charge mentale »', () => {
		for (const t of AGENT_TEMPLATES) {
			expect(t.soul.toLowerCase(), `« charge mentale » chez ${t.id}`).not.toContain('charge mentale');
		}
	});

	// Un métier cité en dur devient un agent fantôme dès que l'équipe change : Mike promettait de
	// déléguer à « RH, Support, Juridique » qui ne sont déployés nulle part.
	it('Mike ne cite aucun métier en dur : sa seule référence est sa liste d’équipe', () => {
		const mike = AGENT_TEMPLATES.find((t) => t.id === 'mike-chef-orchestre');
		expect(mike).toBeTruthy();
		const identite = mike!.soul.split('# Ce que tu fais toi-même')[0];
		for (const fantome of ['RH', 'Support', 'Juridique', 'Compta']) {
			expect(identite, `« ${fantome} » cité en dur`).not.toContain(fantome);
		}
	});

	// Ingrid touche au droit du travail et à la paie : sans ce rappel, une réponse ferme et fausse
	// sur un préavis part chez le dirigeant, qui l'applique.
	it('Ingrid (RH) renvoie vers un avocat / un expert-comptable', () => {
		const rh = AGENT_TEMPLATES.find((t) => t.id === 'rh');
		expect(rh).toBeTruthy();
		expect(rh!.soul).toContain('avocat');
		expect(rh!.soul).toContain('expert-comptable');
	});
});
