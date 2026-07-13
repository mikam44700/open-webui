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
