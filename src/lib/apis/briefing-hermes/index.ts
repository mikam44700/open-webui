import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API du « Briefing du jour » (Agent OS). Appelle le router admin /api/v1/briefing,
// qui proxifie vers le bridge → briefing assemblé par Hermes (agenda + tâches + automatisations).

export type BriefingEvent = { title: string; when_label: string; location: string };
export type BriefingTask = { title: string; status: string };

export type Briefing = {
	date_label: string;
	events_status: 'ok' | 'not_connected' | 'unavailable';
	events: BriefingEvent[];
	tasks_status: 'ok' | 'unavailable';
	tasks: BriefingTask[];
	automations_status: 'ok' | 'unavailable';
	automations: { name: string; status: string }[];
	text: string;
};

export const getBriefing = async (token: string): Promise<Briefing | null> => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/briefing/`, {
		method: 'GET',
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});
	if (error) throw error;
	return res;
};

// Publie le briefing du jour dans le canal « Agent OS ».
export const publishBriefing = async (token: string): Promise<{ ok: boolean; channel_id: string }> => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/agent-channel/publish-briefing`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});
	if (error) throw error;
	return res;
};
