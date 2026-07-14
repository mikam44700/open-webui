import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de l'onglet Mémoire / Second Cerveau (Agent OS). Appelle le router admin
// /api/v1/memory, qui proxifie vers le Providers Bridge (coffre Obsidian — source de vérité).
// Surface distincte de la mémoire native d'OpenWebUI (désactivée). Cf. specs/005-memoire.

export type MemoryNode = {
	name: string;
	path: string;
	type: 'folder' | 'note';
	children: MemoryNode[];
};

export type NoteContent = {
	path: string;
	content: string;
};

export type MemoryStatus = {
	ok: boolean;
	note_count: number;
	local_copy: boolean;
	local_copy_synced_at: number | null;
};

const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memory${path}`, {
		method,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) throw error;
	return res;
};

export const getMemoryTree = (token: string): Promise<{ tree: MemoryNode[] }> =>
	call(token, 'GET', '/tree');

export const getMemoryStatus = (token: string): Promise<MemoryStatus> => call(token, 'GET', '/status');

export const getMemoryNote = (token: string, path: string): Promise<NoteContent> =>
	call(token, 'GET', `/note?path=${encodeURIComponent(path)}`);

export const saveMemoryNote = (token: string, path: string, content: string): Promise<NoteContent> =>
	call(token, 'POST', '/note', { path, content });

// Crée la structure PARA du coffre (00-Réception, 01-Projets, … + INDEX). Idempotent.
export const initMemoryVault = (token: string): Promise<{ created: string[] }> =>
	call(token, 'POST', '/init');

// Crée un dossier dans le coffre (rangement manuel). ``parent`` = "" pour la racine.
export const createFolder = (token: string, parent: string, name: string): Promise<MemoryNode> =>
	call(token, 'POST', '/folder', { parent, name });

// Déplace une note vers un autre dossier (``dest`` = "" pour la racine).
export const moveNote = (token: string, path: string, dest: string): Promise<NoteContent> =>
	call(token, 'POST', '/note/move', { path, dest });

// Renomme un dossier (non structurel ; les dossiers PARA du squelette sont protégés côté serveur).
export const renameFolder = (token: string, path: string, name: string): Promise<MemoryNode> =>
	call(token, 'POST', '/folder/rename', { path, name });

// Déplace un dossier vers un autre parent (`dest` = "" pour la racine ; Réception/PARA protégés).
export const moveFolder = (token: string, path: string, dest: string): Promise<MemoryNode> =>
	call(token, 'POST', '/folder/move', { path, dest });

// Suppression douce d'un dossier (corbeille récupérable).
export const deleteFolder = (token: string, path: string): Promise<DeleteResult> =>
	call(token, 'DELETE', `/folder?path=${encodeURIComponent(path)}`);

// Restaure un dossier supprimé (annulation).
export const restoreFolder = (token: string, trashRef: string, path: string): Promise<MemoryNode> =>
	call(token, 'POST', '/folder/restore', { trash_ref: trashRef, path });

// ─── Recherche serveur (FTS5) : scalable, ne charge pas toutes les notes côté client ───
export type SearchResult = {
	titre: string;
	chemin: string;
	extrait: string;
	score: number;
	source_type: 'note' | 'document';
};
export type SearchResponse = { ok: boolean; query: string; results: SearchResult[]; count: number };

export const searchMemory = (
	token: string,
	query: string,
	limit = 30
): Promise<SearchResponse> => call(token, 'POST', '/search', { query, limit });

// ─── CRUD note : suppression douce (corbeille), restauration (annulation), renommage ───
export type DeleteResult = { ok: boolean; path: string; trash_ref: string };

export const deleteMemoryNote = (token: string, path: string): Promise<DeleteResult> =>
	call(token, 'DELETE', `/note?path=${encodeURIComponent(path)}`);

export const restoreMemoryNote = (
	token: string,
	trashRef: string,
	path: string
): Promise<NoteContent> => call(token, 'POST', '/note/restore', { trash_ref: trashRef, path });

export const renameMemoryNote = (token: string, path: string, title: string): Promise<NoteContent> =>
	call(token, 'POST', '/note/rename', { path, title });

// Dépose une note dans la Boîte de réception (zone d'écriture sûre de l'agent).
export const writeInboxNote = (token: string, title: string, content: string): Promise<NoteContent> =>
	call(token, 'POST', '/inbox', { title, content });

// ─── Réglages du cerveau (feature 017) : Persona / Profil / Souvenirs ───────

export type PersonaContent = { content: string };
export type ProfileContent = { content: string; char_count: number; char_limit: number };
export type MemoryEntry = { index: number; content: string };
export type MemoryEntriesResponse = {
	entries: MemoryEntry[];
	char_count: number;
	char_limit: number;
};

// Persona (SOUL.md) — le caractère de l'assistant.
export const getPersona = (token: string): Promise<PersonaContent> => call(token, 'GET', '/persona');

export const savePersona = (
	token: string,
	content: string,
	allowEmpty = false
): Promise<PersonaContent> => call(token, 'PUT', '/persona', { content, allow_empty: allowEmpty });

// Gabarit FR par défaut à charger dans l'éditeur (n'écrit rien sur disque).
export const resetPersona = (token: string): Promise<PersonaContent> =>
	call(token, 'POST', '/persona/reset');

// Profil (USER.md) — qui est le dirigeant.
export const getProfile = (token: string): Promise<ProfileContent> => call(token, 'GET', '/profile');

export const saveProfile = (token: string, content: string): Promise<ProfileContent> =>
	call(token, 'PUT', '/profile', { content });

// Souvenirs (MEMORY.md) — ce que l'assistant a retenu.
export const getEntries = (token: string): Promise<MemoryEntriesResponse> =>
	call(token, 'GET', '/entries');

export const addEntry = (token: string, content: string): Promise<MemoryEntriesResponse> =>
	call(token, 'POST', '/entries', { content });

export const updateEntry = (
	token: string,
	index: number,
	content: string
): Promise<MemoryEntriesResponse> => call(token, 'PUT', `/entries/${index}`, { content });

export const removeEntry = (token: string, index: number): Promise<MemoryEntriesResponse> =>
	call(token, 'DELETE', `/entries/${index}`);

// Pack de synchronisation du coffre (feature 005 US5) : identité Syncthing pré-appairée que le
// client télécharge → son coffre se connecte tout seul (zéro appairage). Base64 (quelques Ko).
export type SyncPack = { filename: string; content_b64: string; size: number };

export const getSyncPack = (token: string): Promise<SyncPack> => call(token, 'GET', '/sync/pack');

// Déclenche le téléchargement du pack (décode le base64 en fichier zip côté navigateur).
export const downloadSyncPack = (pack: SyncPack): void => {
	const bytes = Uint8Array.from(atob(pack.content_b64), (c) => c.charCodeAt(0));
	const url = URL.createObjectURL(new Blob([bytes], { type: 'application/zip' }));
	const a = document.createElement('a');
	a.href = url;
	a.download = pack.filename;
	a.click();
	URL.revokeObjectURL(url);
};
