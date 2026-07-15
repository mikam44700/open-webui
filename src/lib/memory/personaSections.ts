// Sections délimitées d'un SOUL.md (le caractère d'un agent).
//
// POURQUOI CE MODULE : le SOUL de l'orchestrateur contient un bloc d'équipe que le bridge tient à
// jour tout seul (`<!-- AGENTS:DEBUT -->…<!-- AGENTS:FIN -->`). Côté moteur, `replace_roster_block`
// est un NO-OP si les marqueurs manquent (profiles_adapter.py) : un texte qui les efface casse la
// synchro DÉFINITIVEMENT — l'agent perd son équipe et ne la retrouve jamais. Toute écriture
// proposée depuis l'UI doit donc traverser ces fonctions, jamais remplacer le SOUL en bloc.
//
// On applique ici le même patron que le moteur : on ne touche QU'À la zone entre marqueurs, et ce
// que le dirigeant a rédigé autour survit.

export const ROSTER_BEGIN = '<!-- AGENTS:DEBUT -->';
export const ROSTER_END = '<!-- AGENTS:FIN -->';
export const TONE_BEGIN = '<!-- TON:DEBUT -->';
export const TONE_END = '<!-- TON:FIN -->';

/** Bloc délimité (marqueurs compris), ou null si absent/tronqué/inversé. */
const section = (soul: string, begin: string, end: string): string | null => {
	const start = soul.indexOf(begin);
	const stop = soul.indexOf(end);
	if (start === -1 || stop === -1 || stop < start) return null;
	return soul.slice(start, stop + end.length);
};

/** Remplace un bloc délimité par `block`. No-op si les marqueurs manquent. */
const replaceSection = (soul: string, begin: string, end: string, block: string): string => {
	const current = section(soul, begin, end);
	if (current === null) return soul;
	return soul.replace(current, block);
};

/** Le bloc d'équipe du SOUL (marqueurs compris), ou null s'il n'en a pas. */
export const extractRoster = (soul: string): string | null => section(soul, ROSTER_BEGIN, ROSTER_END);

/**
 * Pose le ton `body` dans le SOUL sans rien détruire d'autre.
 *
 * Marqueurs présents → la zone de ton est remplacée. Absents → le ton est ajouté À LA FIN (choix
 * volontaire : prévisible, et il n'y a pas d'ancre fiable dans un prompt rédigé à la main).
 * Le bloc d'équipe n'est jamais touché dans un cas comme dans l'autre.
 */
export const applyTone = (soul: string, body: string): string => {
	const block = `${TONE_BEGIN}\n${body}\n${TONE_END}`;
	if (section(soul, TONE_BEGIN, TONE_END) !== null) {
		return replaceSection(soul, TONE_BEGIN, TONE_END, block);
	}
	return `${soul.replace(/\s+$/, '')}\n\n${block}\n`;
};

/**
 * Repart du prompt d'usine en gardant l'équipe RÉELLE (celle du SOUL courant, tenue à jour par le
 * bridge) plutôt que la liste d'exemple figée dans le template. Sans équipe courante, l'usine
 * s'applique telle quelle : ses marqueurs laisseront la synchro reprendre la main.
 */
export const resetToFactory = (current: string, factory: string): string => {
	const roster = extractRoster(current);
	if (roster === null) return factory;
	return replaceSection(factory, ROSTER_BEGIN, ROSTER_END, roster);
};
