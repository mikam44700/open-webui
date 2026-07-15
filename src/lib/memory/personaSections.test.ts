import { describe, it, expect } from 'vitest';
import { applyTone, extractRoster, resetToFactory, TONE_BEGIN, TONE_END } from './personaSections';

// Un SOUL réaliste : de la prose du dirigeant + le bloc d'équipe auto-géré par le bridge.
const ROSTER = `<!-- AGENTS:DEBUT -->
## Ton équipe

- \`veille\` — Il surveille pour vous.
<!-- AGENTS:FIN -->`;

const SOUL = `Tu es Mike.

# Méthode
1. Comprendre.

${ROSTER}

${TONE_BEGIN}
## Ton
- Tu vas droit au but.
${TONE_END}

# Garde-fous
- Tu es honnête.`;

describe('extractRoster', () => {
	it('renvoie le bloc d’équipe, marqueurs compris', () => {
		expect(extractRoster(SOUL)).toBe(ROSTER);
	});

	it('renvoie null quand le bloc est absent', () => {
		expect(extractRoster('Tu es Mike, sans équipe.')).toBeNull();
	});

	it('renvoie null quand un seul marqueur est présent (bloc tronqué)', () => {
		expect(extractRoster('<!-- AGENTS:DEBUT -->\n- `veille`')).toBeNull();
	});
});

describe('applyTone', () => {
	it('remplace le ton sans toucher au reste', () => {
		const out = applyTone(SOUL, '## Ton\n- Tu es chaleureux.');
		expect(out).toContain('- Tu es chaleureux.');
		expect(out).not.toContain('- Tu vas droit au but.');
		// Le reste du prompt survit intégralement.
		expect(out).toContain('Tu es Mike.');
		expect(out).toContain('# Méthode');
		expect(out).toContain('# Garde-fous');
	});

	// LE test qui compte : c'est le bug qui cassait Mike définitivement.
	it('préserve le bloc d’équipe (sinon la synchro du bridge ne répare plus jamais)', () => {
		const out = applyTone(SOUL, '## Ton\n- Tu es formel.');
		expect(extractRoster(out)).toBe(ROSTER);
	});

	it('insère le ton à la fin quand les marqueurs sont absents', () => {
		const sansTon = `Tu es Mike.\n\n${ROSTER}`;
		const out = applyTone(sansTon, '## Ton\n- Tu es direct.');
		expect(out).toContain('- Tu es direct.');
		expect(extractRoster(out)).toBe(ROSTER);
		expect(out.indexOf(TONE_BEGIN)).toBeGreaterThan(out.indexOf('<!-- AGENTS:FIN -->'));
	});

	it('est idempotent : appliquer deux fois le même ton ne duplique rien', () => {
		const once = applyTone(SOUL, '## Ton\n- Tu es direct.');
		const twice = applyTone(once, '## Ton\n- Tu es direct.');
		expect(twice).toBe(once);
	});

	it('reste stable quand un ton en remplace un autre (pas d’empilement)', () => {
		const a = applyTone(SOUL, '## Ton\n- A.');
		const b = applyTone(a, '## Ton\n- B.');
		expect(b.match(new RegExp(TONE_BEGIN, 'g'))?.length).toBe(1);
		expect(b).toContain('- B.');
		expect(b).not.toContain('- A.');
	});
});

describe('resetToFactory', () => {
	const FACTORY = `Tu es Mike, version d’usine.

<!-- AGENTS:DEBUT -->
## Ton équipe

_Liste tenue à jour automatiquement._
<!-- AGENTS:FIN -->

# Garde-fous
- Tu es honnête.`;

	it('restaure le prompt d’usine', () => {
		const out = resetToFactory(SOUL, FACTORY);
		expect(out).toContain('Tu es Mike, version d’usine.');
		expect(out).not.toContain('# Méthode');
	});

	it('garde l’équipe RÉELLE plutôt que la liste vide d’usine', () => {
		const out = resetToFactory(SOUL, FACTORY);
		expect(extractRoster(out)).toBe(ROSTER);
		expect(out).toContain('`veille`');
	});

	it('retombe sur l’équipe d’usine quand le SOUL courant n’en a pas', () => {
		const out = resetToFactory('Prompt bricolé sans équipe.', FACTORY);
		expect(out).toBe(FACTORY);
	});
});
