import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MemoireEntry = {
	name: string;
	path: string;
	type: 'dossier' | 'fiche';
	children?: MemoireEntry[];
};

const headers = (token: string) => ({
	Accept: 'application/json',
	'Content-Type': 'application/json',
	authorization: `Bearer ${token}`
});

const handle = async (res: Response) => {
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getMemoireTree = async (token: string): Promise<{ tree: MemoireEntry[] }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/memoire/tree`, {
		method: 'GET',
		headers: headers(token)
	});
	return handle(res);
};

export const getFiche = async (
	token: string,
	path: string
): Promise<{ path: string; content: string }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/memoire/fiche?path=${encodeURIComponent(path)}`, {
		method: 'GET',
		headers: headers(token)
	});
	return handle(res);
};

export const saveFiche = async (
	token: string,
	path: string,
	content: string
): Promise<{ path: string; indexed: boolean }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/memoire/fiche`, {
		method: 'POST',
		headers: headers(token),
		body: JSON.stringify({ path, content })
	});
	return handle(res);
};

export const createDossier = async (token: string, path: string): Promise<{ path: string }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/memoire/dossier`, {
		method: 'POST',
		headers: headers(token),
		body: JSON.stringify({ path })
	});
	return handle(res);
};
