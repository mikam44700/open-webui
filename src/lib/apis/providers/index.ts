import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page Providers (Agent OS). Appelle le router admin /api/v1/providers,
// qui proxifie vers le Providers Bridge (gestion des cerveaux Hermes).

export const getProviders = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
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

export const getActiveProvider = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/active`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
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

export const setActiveProvider = async (token: string, providerId: string, modelId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/active`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ provider_id: providerId, model_id: modelId })
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

// US2 — enregistre/remplace la clé API d'un provider (la valeur n'est jamais relue).
export const setProviderKey = async (token: string, providerId: string, value: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/key`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ value })
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

// US2 — teste une clé (probe réseau) AVANT enregistrement.
export const validateProviderKey = async (token: string, providerId: string, value: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/validate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ value })
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
