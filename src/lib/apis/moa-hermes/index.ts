import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API Mixture of Agents (feature 018). Appelle /api/v1/moa (admin), qui proxifie
// vers le Providers Bridge (config + activation du provider natif « moa » du moteur).

export type MoaSlot = { provider: string; model: string };
export type MoaConfig = {
	reference_models: MoaSlot[];
	aggregator: MoaSlot | Record<string, never>;
	enabled: boolean;
	active: boolean;
};

const req = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/moa${path}`, {
		method,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
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

export const getMoaConfig = (token: string): Promise<MoaConfig> => req(token, 'GET', '/config');

export const setMoaConfig = (
	token: string,
	reference_models: MoaSlot[],
	aggregator: MoaSlot
): Promise<MoaConfig> => req(token, 'POST', '/config', { reference_models, aggregator });

export const activateMoa = (token: string): Promise<MoaConfig> => req(token, 'POST', '/activate');

export const deactivateMoa = (token: string): Promise<MoaConfig> => req(token, 'POST', '/deactivate');
