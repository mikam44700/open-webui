import { WEBUI_API_BASE_URL } from '$lib/constants';

// Pont Connaissances → coffre Hermes (feature 015). Rend les documents d'une base de
// connaissances lisibles par Agent OS (Hermes). La recherche sémantique reste côté OpenWebUI.

export const syncKnowledgeToAgent = async (
	token: string,
	knowledgeId: string
): Promise<{ ok: boolean; synced: number; skipped: number; folder: string }> => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/knowledge-agent/${encodeURIComponent(knowledgeId)}/sync-agent`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
		}
	)
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
