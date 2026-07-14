// Logique PURE du rangement assisté par Adam (feature 021).
// Construit la liste des dossiers cibles, le prompt de suggestion, et parse/valide la réponse
// du modèle. Aucune I/O ici (testable) : l'appel modèle et l'application (moveNote) vivent dans l'UI.
//
// Garde-fous encodés ici : on ne suggère QUE des dossiers réels, jamais la Réception, jamais plus
// de 3 options, et toute réponse douteuse (non-JSON, dossier inconnu) donne 0 suggestion.

import type { MemoryNode } from '$lib/apis/memory';

// Dossier d'entrée : jamais une destination de rangement (on ne « range » pas vers la Réception).
export const INBOX_DIR = '00-Réception';
const MAX_OPTIONS = 3;

export type FolderRef = { path: string; label: string };

export type FilingSuggestion = {
	folder: string; // chemin relatif d'un dossier RÉEL du coffre
	label: string; // libellé lisible (langage dirigeant)
	reason: string; // justification courte
	rank: number; // 1 = plus probable
};

export type NoteSuggestions = {
	notePath: string;
	suggestions: FilingSuggestion[]; // 0 à 3, classées
};

/** Aplatit l'arbre en liste de dossiers cibles (exclut la Réception et ses sous-dossiers). */
export function buildFolderList(
	tree: MemoryNode[],
	friendlyFolder: (name: string) => string = (n) => n
): FolderRef[] {
	const acc: FolderRef[] = [];
	const walk = (nodes: MemoryNode[]) => {
		for (const n of nodes) {
			if (n.type !== 'folder') continue;
			if (n.path === INBOX_DIR || n.path.startsWith(`${INBOX_DIR}/`)) continue;
			acc.push({ path: n.path, label: friendlyFolder(n.name) });
			walk(n.children ?? []);
		}
	};
	walk(tree);
	return acc;
}

/** Prompt demandant au modèle des destinations de rangement (JSON strict), bornées aux dossiers réels. */
export function buildSuggestPrompt(
	notes: Array<{ path: string; content: string }>,
	folders: FolderRef[]
): string {
	const folderLines = folders.map((f) => `- ${f.path} (${f.label})`).join('\n');
	const noteBlocks = notes
		.map((n) => `### Note: ${n.path}\n${(n.content ?? '').slice(0, 1500)}`)
		.join('\n\n');
	return [
		"Tu es Adam, bibliothécaire du coffre. Pour chaque note ci-dessous (actuellement dans la boîte de réception), propose où la ranger PARMI les dossiers existants listés — jamais ailleurs.",
		'',
		'Dossiers disponibles (utilise EXACTEMENT le chemin de gauche comme "folder") :',
		folderLines,
		'',
		'Règles STRICTES :',
		'- "folder" doit être un chemin EXACT de la liste ci-dessus. Jamais la réception, jamais un dossier inventé.',
		'- Au plus 3 options par note, classées de la plus à la moins probable.',
		'- Chaque option a une "reason" courte (une phrase, sans jargon), en français.',
		'- Si aucune destination fiable, renvoie "options": [] pour cette note.',
		'- Ne modifie ni ne supprime rien : tu proposes seulement un emplacement.',
		'',
		'Réponds UNIQUEMENT en JSON, sans texte autour, au format :',
		'{"suggestions":[{"notePath":"<chemin>","options":[{"folder":"<chemin>","reason":"<phrase>"}]}]}',
		'',
		'Notes à classer :',
		noteBlocks
	].join('\n');
}

/** Extrait le premier objet JSON plausible d'une chaîne (le modèle peut l'entourer de texte). */
function extractJson(raw: string): unknown | null {
	if (!raw) return null;
	const start = raw.indexOf('{');
	const end = raw.lastIndexOf('}');
	if (start === -1 || end === -1 || end <= start) return null;
	try {
		return JSON.parse(raw.slice(start, end + 1));
	} catch {
		return null;
	}
}

/**
 * Parse la réponse brute du modèle en suggestions SÛRES :
 * - "folder" doit correspondre à un dossier réel (par chemin OU libellé) ; sinon écarté.
 * - jamais la Réception ; dédup par dossier ; max 3 ; classées par ordre d'apparition.
 * - toute anomalie (non-JSON, structure inattendue) → [].
 */
export function parseSuggestions(raw: string, validFolders: FolderRef[]): NoteSuggestions[] {
	const data = extractJson(raw) as { suggestions?: unknown } | null;
	if (!data || !Array.isArray(data.suggestions)) return [];

	// Index de résolution : chemin OU libellé (insensible à la casse/espaces) → FolderRef réel.
	const norm = (s: string) => s.trim().toLowerCase();
	const byKey = new Map<string, FolderRef>();
	for (const f of validFolders) {
		byKey.set(norm(f.path), f);
		byKey.set(norm(f.label), f);
	}

	const result: NoteSuggestions[] = [];
	for (const entry of data.suggestions as Array<Record<string, unknown>>) {
		if (!entry || typeof entry.notePath !== 'string') continue;
		const options = Array.isArray(entry.options) ? entry.options : [];
		const seen = new Set<string>();
		const suggestions: FilingSuggestion[] = [];
		for (const opt of options as Array<Record<string, unknown>>) {
			if (!opt || typeof opt.folder !== 'string') continue;
			const match = byKey.get(norm(opt.folder));
			if (!match) continue; // dossier inconnu → écarté (anti-hallucination)
			if (match.path === INBOX_DIR) continue; // jamais la Réception
			if (seen.has(match.path)) continue; // dédup
			seen.add(match.path);
			suggestions.push({
				folder: match.path,
				label: match.label,
				reason: typeof opt.reason === 'string' ? opt.reason.trim() : '',
				rank: suggestions.length + 1
			});
			if (suggestions.length >= MAX_OPTIONS) break;
		}
		result.push({ notePath: entry.notePath, suggestions });
	}
	return result;
}
