import { apiCall } from '$lib/apis/apiCall';

// Client API de l'onglet Mémoire / Second Cerveau (Agent OS). Appelle le router admin
// /api/v1/memory, qui proxifie vers le Providers Bridge (coffre Obsidian — source de vérité).
// Surface distincte de la mémoire native d'OpenWebUI (désactivée). Cf. specs/005-memoire.

export type MemoryNode = {
	name: string;
	path: string;
	type: 'folder' | 'note';
	children: MemoryNode[];
	modified?: number | null; // date de dernière modif (epoch, notes)
};

export type NoteContent = {
	path: string;
	content: string;
	modified?: number | null; // date de dernière modif (epoch)
};

export type MemoryStatus = {
	ok: boolean;
	note_count: number;
	local_copy: boolean; // une copie locale Obsidian est reliée (Syncthing détecté)
	local_copy_synced_at: number | null;
	sync_available: boolean; // ce serveur PEUT relier une copie locale (Syncthing provisionné)
};

const call = (token: string, method: string, path: string, body?: unknown) =>
	apiCall(token, '/memory', method, path, body);

export const getMemoryTree = (token: string): Promise<{ tree: MemoryNode[] }> =>
	call(token, 'GET', '/tree');

export const getMemoryStatus = (token: string): Promise<MemoryStatus> => call(token, 'GET', '/status');

export const getMemoryNote = (token: string, path: string): Promise<NoteContent> =>
	call(token, 'GET', `/note?path=${encodeURIComponent(path)}`);

// ``expectedModified`` = le ``modified`` (mtime epoch) vu au dernier ``getMemoryNote`` pour ce
// chemin (concurrence optimiste, même principe que ``updateEntry``/``removeEntry`` des souvenirs).
// Si la note a changé depuis (autre éditeur ouvert, l'agent via la skill obsidian, une synchro
// Syncthing…), le serveur répond 409 (``note_conflict``) plutôt que d'écraser silencieusement.
// Omis = comportement rétro-compatible (nouvelle note, jamais lue au préalable).
export const saveMemoryNote = (
	token: string,
	path: string,
	content: string,
	expectedModified?: number | null
): Promise<NoteContent> =>
	call(token, 'POST', '/note', {
		path,
		content,
		expected_modified: expectedModified ?? null
	});

// Crée la structure PARA du coffre (00-Réception, 01-En cours, … + INDEX). Idempotent.
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

// Corbeille : notes/dossiers supprimés dans LunarIA, récupérables.
export type TrashItem = {
	ref: string;
	path: string;
	name: string;
	type: 'folder' | 'note';
	deleted_at: number;
	size: number; // octets occupés (la place récupérée en supprimant définitivement)
};

export const getTrash = (token: string): Promise<{ items: TrashItem[] }> =>
	call(token, 'GET', '/trash');

// Suppression DÉFINITIVE d'un élément de la corbeille. Irréversible : toujours confirmer avant.
export const purgeTrashItem = (token: string, ref: string): Promise<{ ok: boolean; ref: string }> =>
	call(token, 'DELETE', `/trash/item?ref=${encodeURIComponent(ref)}`);

// Vide la corbeille (définitif). Ne touche que les éléments visibles dans LunarIA.
export const emptyTrash = (token: string): Promise<{ ok: boolean; purged: number }> =>
	call(token, 'DELETE', '/trash');

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

// Crée ou met à jour une note GÉRÉE, identifiée par noteId (frontmatter lunaria-id).
// Idempotent : un rejeu réécrit la note sur place, où que le dirigeant l'ait rangée — jamais de
// doublon. À utiliser pour toute note que le produit réécrit (fiche entreprise de l'onboarding).
export const upsertManagedNote = (
	token: string,
	noteId: string,
	title: string,
	content: string
): Promise<NoteContent> => call(token, 'POST', '/managed-note', { note_id: noteId, title, content });

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

// ``expectedContent`` = le contenu vu par le dirigeant au dernier ``getEntries`` pour cet
// index (concurrence optimiste). Si l'entrée a changé entre-temps (le moteur écrit aussi dans
// MEMORY.md, par contenu — pas par position), le serveur répond 409 ``entry_conflict`` plutôt
// que d'écraser/supprimer une autre entrée que celle affichée à l'écran.
export const updateEntry = (
	token: string,
	index: number,
	content: string,
	expectedContent?: string
): Promise<MemoryEntriesResponse> =>
	call(token, 'PUT', `/entries/${index}`, { content, expected_content: expectedContent ?? null });

export const removeEntry = (
	token: string,
	index: number,
	expectedContent?: string
): Promise<MemoryEntriesResponse> =>
	call(
		token,
		'DELETE',
		expectedContent !== undefined
			? `/entries/${index}?expected_content=${encodeURIComponent(expectedContent)}`
			: `/entries/${index}`
	);

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
