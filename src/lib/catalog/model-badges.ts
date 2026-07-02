/**
 * Catalogue curé de présentation des modèles IA (anciennement « providers »).
 *
 * Objectif (feature 006, US3) : afficher pour chaque modèle IA un libellé humain
 * et des badges métier (Rapide / Économique / Confidentiel / Premium / Local) qui
 * aident un dirigeant non-tech à choisir selon coût / performance / confidentialité.
 *
 * Règle d'honnêteté (décision D27) : un badge n'est attribué que s'il reflète la
 * nature RÉELLE du modèle. Pas de détection automatique : la qualification est curée
 * ici. Un identifiant inconnu de la table ne reçoit AUCUN badge (repli neutre).
 */

export type ModelBadge = 'Rapide' | 'Économique' | 'Confidentiel' | 'Premium' | 'Local';

export type ModelPresentation = {
	/** Libellé humain optionnel, affiché en complément du nom du fournisseur. */
	humanLabel?: string;
	/** Badges métier justifiables pour ce modèle. */
	badges: ModelBadge[];
};

/**
 * Fournisseurs tournant en local (sur la machine/serveur du client) : les données
 * ne quittent pas l'infrastructure → légitimement « Local » et « Confidentiel ».
 */
const LOCAL_PROVIDERS = new Set(['ollama', 'ollama-local', 'localai', 'llamacpp', 'llama-cpp', 'lmstudio', 'vllm']);

/**
 * Table curée par identifiant de fournisseur (source : bridge `/providers`).
 * N'ajouter une entrée que si elle est défendable (D27).
 */
const PROVIDER_PRESENTATION: Record<string, ModelPresentation> = {
	openai: { badges: ['Premium', 'Rapide'] },
	// L'onglet « Clés API » expose OpenAI sous l'id `openai-api` (et non `openai`) :
	// on qualifie donc explicitement cet id, sinon la carte n'avait aucun badge.
	'openai-api': { badges: ['Premium', 'Rapide'] },
	'openai-codex': { humanLabel: 'GPT-5.5 via OpenAI Codex', badges: ['Premium'] },
	anthropic: { badges: ['Premium'] },
	google: { badges: ['Rapide'] },
	gemini: { badges: ['Rapide'] },
	vertex: { badges: ['Premium'] },
	mistral: { badges: ['Économique', 'Rapide'] },
	openrouter: { badges: ['Économique'] },
	groq: { badges: ['Rapide', 'Économique'] },
	bedrock: { badges: ['Premium'] },
	// Réputés économiques (bon rapport qualité/prix, défendable — D27).
	deepseek: { badges: ['Économique'] },
	alibaba: { badges: ['Économique'] },
	zai: { badges: ['Économique'] },
	minimax: { badges: ['Économique'] },
	'kimi-coding': { badges: ['Économique'] },
	'kimi-coding-cn': { badges: ['Économique'] },
	huggingface: { badges: ['Économique'] },
	novita: { badges: ['Économique'] },
	gmi: { badges: ['Économique'] }
};

/** Présentation neutre (repli) : aucun badge, pas de libellé humain. */
const EMPTY_PRESENTATION: ModelPresentation = { badges: [] };

/**
 * Renvoie la présentation curée d'un modèle IA à partir de son identifiant.
 * Repli (D27) : identifiant inconnu → aucun badge, pas de libellé humain.
 */
export const getModelPresentation = (providerId: string | null | undefined): ModelPresentation => {
	if (!providerId) return EMPTY_PRESENTATION;

	const entry = PROVIDER_PRESENTATION[providerId];
	if (entry) return entry;

	if (LOCAL_PROVIDERS.has(providerId)) {
		return { badges: ['Local', 'Confidentiel'] };
	}

	return EMPTY_PRESENTATION;
};
