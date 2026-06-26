import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page « Automatisations » (Agent OS). Appelle le router admin
// /api/v1/automations, qui proxifie vers le Providers Bridge → planificateur (cron) natif
// de Hermes (source de vérité unique). Les automatisations natives OpenWebUI sont masquées.

export type Automation = {
	id: string;
	name: string;
	instruction: string;
	rhythm_label: string;
	rhythm_kind: 'recurrent' | 'once';
	status: 'active' | 'paused' | 'done' | 'error';
	next_run_label: string | null;
	last_run_label: string | null;
	last_status: 'ok' | 'error' | null;
	last_error_short: string | null;
	// Mode Expert (présents seulement si demandé avec expert=true)
	schedule_raw?: string;
	repeat?: { times: number | null; completed: number } | null;
	skills?: string[];
	deliver?: string | null;
};

const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations${path}`, {
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

	if (error) {
		throw error;
	}

	return res;
};

const q = (expert: boolean) => (expert ? '?expert=true' : '');

export const getAutomations = (token: string, expert = false): Promise<{ automations: Automation[] }> =>
	call(token, 'GET', `/${q(expert)}`);

export const createAutomation = (token: string, body: unknown, expert = false) =>
	call(token, 'POST', `/${q(expert)}`, body);

export const updateAutomation = (token: string, id: string, body: unknown, expert = false) =>
	call(token, 'PATCH', `/${encodeURIComponent(id)}${q(expert)}`, body);

export const pauseAutomation = (token: string, id: string) =>
	call(token, 'POST', `/${encodeURIComponent(id)}/pause`);

export const resumeAutomation = (token: string, id: string) =>
	call(token, 'POST', `/${encodeURIComponent(id)}/resume`);

export const runAutomation = (token: string, id: string) =>
	call(token, 'POST', `/${encodeURIComponent(id)}/run`);

export const deleteAutomation = (token: string, id: string) =>
	call(token, 'DELETE', `/${encodeURIComponent(id)}`);
