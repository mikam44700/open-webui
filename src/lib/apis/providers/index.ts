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

// Capacités d'un modèle (reasoning/vision/tools/context_window). Champs null si inconnu.
export const getModelCapabilities = async (token: string, providerId: string, modelId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/model-capabilities`, {
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

// Niveau d'intelligence (effort de raisonnement) global du moteur. Renvoie { effort }.
export const getReasoning = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/reasoning`, {
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

export const setReasoning = async (token: string, effort: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/reasoning`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ effort })
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

// Bedrock — enregistre les credentials AWS (Access Key + Secret + Région).
export const setAwsCredentials = async (
	token: string,
	providerId: string,
	creds: { access_key_id: string; secret_access_key: string; region?: string }
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/aws`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(creds)
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

// US3 — démarre le flow OAuth (le navigateur s'ouvre sur l'hôte).
export const startProviderOAuth = async (token: string, providerId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/oauth/start`, {
		method: 'POST',
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

// US3 — état du flow OAuth en cours (polling).
export const getProviderOAuthStatus = async (token: string, providerId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/oauth/status`, {
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

// US3 — déconnecte un compte OAuth (retire les identifiants côté moteur Hermes).
export const logoutProviderOAuth = async (token: string, providerId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/oauth`, {
		method: 'DELETE',
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

// Agent Hermes — helper générique pour les appels /hermes/*
const hermesCall = async (token: string, method: string, path: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/providers/hermes/${path}`, {
		method,
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

export const getHermesStatus = (token: string) => hermesCall(token, 'GET', 'status');
export const checkHermesUpdate = (token: string) => hermesCall(token, 'POST', 'update/check');
export const startHermesUpdate = (token: string) => hermesCall(token, 'POST', 'update/start');
export const getHermesUpdateStatus = (token: string) => hermesCall(token, 'GET', 'update/status');
