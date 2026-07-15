import { apiCall } from '$lib/apis/apiCall';

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

const call = (token: string, method: string, path: string, body?: unknown) =>
	apiCall(token, '/calendar', method, path, body);

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
