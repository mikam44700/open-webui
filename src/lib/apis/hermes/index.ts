import { WEBUI_API_BASE_URL } from '$lib/constants';

export type HermesActiveModel = {
	provider: string | null;
	model: string | null;
};

export type HermesStatus = {
	installed: boolean;
	version: string | null;
	last_update: string | null;
	active: HermesActiveModel | null;
	api_server: {
		port: number;
		reachable: boolean;
	};
};

export type HermesUpdateCheck = {
	up_to_date: boolean | null;
	output: string;
};

export const getHermesStatus = async (token: string): Promise<HermesStatus | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/hermes/status`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const checkHermesUpdate = async (token: string): Promise<HermesUpdateCheck | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/hermes/update/check`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
