import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page « Calendrier » (Agent OS). Appelle le router admin /api/v1/calendar,
// qui proxifie vers le Providers Bridge → la source choisie par le client : Google Agenda,
// Outlook Calendar ou Calendly (RDV, lecture seule). La page s'adapte à ce qui est connecté.

export type CalendarEvent = {
	id: string;
	title: string;
	start: string;
	end: string;
	location: string;
	when_label: string;
	all_day: boolean;
	link: string;
	source?: string;
};

export type CalendarSource = {
	id: string; // google | outlook | calendly
	label: string;
	can_write: boolean;
	connected: boolean;
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

export const getCalendarSources = (
	token: string
): Promise<{ sources: CalendarSource[]; default: string | null }> => call(token, 'GET', '/sources');

export const getEvents = (
	token: string,
	source?: string,
	start?: string,
	end?: string,
	tz?: string
): Promise<{ events: CalendarEvent[] }> => {
	const params = new URLSearchParams();
	if (source) params.set('source', source);
	if (start) params.set('start', start);
	if (end) params.set('end', end);
	if (tz) params.set('tz', tz);
	const q = params.toString();
	return call(token, 'GET', `/events${q ? `?${q}` : ''}`);
};

export const createEvent = (token: string, body: unknown) => call(token, 'POST', '/events', body);

export const deleteEvent = (token: string, id: string, source?: string) => {
	const q = source ? `?source=${encodeURIComponent(source)}` : '';
	return call(token, 'DELETE', `/events/${encodeURIComponent(id)}${q}`);
};
