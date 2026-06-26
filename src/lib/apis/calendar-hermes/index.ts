import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page « Calendrier » (Agent OS). Appelle le router admin /api/v1/calendar,
// qui proxifie vers le Providers Bridge → Google Agenda piloté par Hermes (script
// google_api.py). Source de vérité = Google. Le calendrier natif OpenWebUI est masqué.

export type CalendarEvent = {
	id: string;
	title: string;
	start: string;
	end: string;
	location: string;
	when_label: string;
	all_day: boolean;
	link: string;
};

const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendar${path}`, {
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

export const getCalendarStatus = (token: string): Promise<{ connected: boolean }> =>
	call(token, 'GET', '/status');

export const getEvents = (
	token: string,
	start?: string,
	end?: string
): Promise<{ events: CalendarEvent[] }> => {
	const params = new URLSearchParams();
	if (start) params.set('start', start);
	if (end) params.set('end', end);
	const q = params.toString();
	return call(token, 'GET', `/events${q ? `?${q}` : ''}`);
};

export const createEvent = (token: string, body: unknown) =>
	call(token, 'POST', '/events', body);

export const deleteEvent = (token: string, id: string) =>
	call(token, 'DELETE', `/events/${encodeURIComponent(id)}`);
