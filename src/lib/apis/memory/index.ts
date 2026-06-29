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
