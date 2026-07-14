// Diff PUR ligne à ligne pour l'édition assistée (feature 022).
// Sert à montrer un avant/après lisible : ajouts (vert) / retraits (rouge) / lignes conservées.
// Aucune I/O — testable. L'appel modèle et l'écriture de note vivent dans l'UI.

export type DiffSegment = { type: 'same' | 'add' | 'del'; text: string };

const toLines = (s: string): string[] => (s.length ? s.split('\n') : []);

/**
 * Diff ligne à ligne (LCS). Retourne la séquence de segments dans l'ordre de lecture :
 * lignes conservées (`same`), retirées de l'original (`del`), ajoutées par la proposition (`add`).
 */
export function diffLines(before: string, after: string): DiffSegment[] {
	const a = toLines(before);
	const b = toLines(after);
	const n = a.length;
	const m = b.length;

	// Table LCS.
	const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
	for (let i = n - 1; i >= 0; i--) {
		for (let j = m - 1; j >= 0; j--) {
			lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
		}
	}

	// Backtrack pour produire les segments.
	const out: DiffSegment[] = [];
	let i = 0;
	let j = 0;
	while (i < n && j < m) {
		if (a[i] === b[j]) {
			out.push({ type: 'same', text: a[i] });
			i++;
			j++;
		} else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
			out.push({ type: 'del', text: a[i] });
			i++;
		} else {
			out.push({ type: 'add', text: b[j] });
			j++;
		}
	}
	while (i < n) out.push({ type: 'del', text: a[i++] });
	while (j < m) out.push({ type: 'add', text: b[j++] });
	return out;
}

/** Normalise pour comparer le fond : fins de ligne, espaces en fin de ligne, lignes vides finales. */
const normalize = (s: string): string =>
	s
		.replace(/\r\n/g, '\n')
		.split('\n')
		.map((l) => l.replace(/\s+$/, ''))
		.join('\n')
		.replace(/\n+$/, '')
		.trim();

/** Vrai s'il y a une VRAIE différence de contenu (ignore les seuls écarts d'espaces/lignes vides). */
export function hasChanges(before: string, after: string): boolean {
	return normalize(before) !== normalize(after);
}
