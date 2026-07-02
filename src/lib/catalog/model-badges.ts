/**
 * Catalogue curé de présentation des modèles IA (anciennement « providers »).
 *
 * Objectif (feature 006, US3) : afficher pour chaque modèle IA un libellé humain
 * et des badges métier qui aident un dirigeant non-tech à choisir selon coût,
 * performance, spécialité ou confidentialité.
 *
 * Règle d'honnêteté (décision D27) : un badge n'est attribué que s'il reflète la
 * nature RÉELLE du modèle. Pas de détection automatique : la qualification est curée
 * ici. Un identifiant inconnu de la table ne reçoit AUCUN badge (repli neutre).
 *
 * Règle d'affichage : MAX 2 badges par fournisseur (au-delà, la carte se surcharge).
 */

export type ModelBadge =
	| 'Rapide'
	| 'Économique'
	| 'Premium'
	| 'Confidentiel'
	| 'Local'
	| 'Open source'
	| 'Code'
	| 'Entreprise'
	| 'Multimodal'
	| 'Contexte long'
	| 'Recherche web'
	| 'Souverain'
	| 'Polyvalent';

export type ModelPresentation = {
	/** Libellé humain optionnel, affiché en complément du nom du fournisseur. */
	humanLabel?: string;
	/** Badges métier justifiables pour ce modèle (max 2). */
	badges: ModelBadge[];
};

/**
 * Fournisseurs tournant en local (sur la machine/serveur du client) : les données
 * ne quittent pas l'infrastructure → légitimement « Local » et « Confidentiel ».
 */
const LOCAL_PROVIDERS = new Set(['ollama', 'ollama-local', 'localai', 'llamacpp', 'llama-cpp', 'lmstudio', 'vllm']);

/**
 * Table curée par identifiant de fournisseur (source : bridge `/providers`).
 * N'ajouter une entrée que si elle est défendable (D27). Max 2 badges.
 */
const PROVIDER_PRESENTATION: Record<string, ModelPresentation> = {
	// ── Les grands noms ──────────────────────────────────────
	openai: { badges: ['Premium', 'Polyvalent'] },
	'openai-api': { badges: ['Premium', 'Polyvalent'] },
	'openai-codex': { humanLabel: 'GPT-5.5 via OpenAI Codex', badges: ['Premium'] },
	anthropic: { badges: ['Premium', 'Code'] },
	google: { badges: ['Rapide', 'Économique'] },
	gemini: { badges: ['Rapide', 'Multimodal'] },
	vertex: { badges: ['Premium', 'Entreprise'] },
	mistral: { badges: ['Souverain', 'Économique'] },
	deepseek: { badges: ['Économique', 'Code'] },
	xai: { badges: ['Recherche web'] },
	cohere: { badges: ['Entreprise'] },
	perplexity: { badges: ['Recherche web'] },
	copilot: { badges: ['Code'] },

	// ── Une seule clé, plein de modèles (passerelles) ────────
	openrouter: { badges: ['Polyvalent', 'Économique'] },
	kilocode: { badges: ['Code', 'Polyvalent'] },
	'opencode-zen': { badges: ['Code'] },
	'opencode-go': { badges: ['Code'] },

	// ── Plateformes d'hébergement ────────────────────────────
	novita: { badges: ['Open source', 'Économique'] },
	nvidia: { badges: ['Open source', 'Rapide'] },
	huggingface: { badges: ['Open source', 'Économique'] },
	'ollama-cloud': { badges: ['Open source'] },
	arcee: { badges: ['Entreprise', 'Économique'] },
	gmi: { badges: ['Open source', 'Économique'] },
	'azure-foundry': { badges: ['Entreprise'] },
	groq: { badges: ['Rapide', 'Économique'] },
	cerebras: { badges: ['Rapide'] },
	together: { badges: ['Open source', 'Économique'] },
	fireworks: { badges: ['Open source', 'Rapide'] },
	bedrock: { badges: ['Premium', 'Entreprise'] },

	// ── Modèles chinois ──────────────────────────────────────
	alibaba: { badges: ['Polyvalent', 'Code'] },
	'alibaba-coding-plan': { badges: ['Code', 'Économique'] },
	xiaomi: { badges: ['Open source', 'Économique'] },
	'tencent-tokenhub': { badges: ['Polyvalent'] },
	zai: { badges: ['Code', 'Économique'] },
	'kimi-coding': { badges: ['Contexte long', 'Code'] },
	'kimi-coding-cn': { badges: ['Contexte long'] },
	minimax: { badges: ['Multimodal', 'Économique'] },
	'minimax-cn': { badges: ['Multimodal'] },
	stepfun: { badges: ['Multimodal'] },
	'baidu-ernie': { badges: ['Polyvalent', 'Économique'] },

	// ── Comptes (OAuth) / Autres ─────────────────────────────
	'xai-oauth': { badges: ['Recherche web'] },
	'minimax-oauth': { badges: ['Multimodal'] },
	'qwen-oauth': { badges: ['Polyvalent'] },
	nous: { badges: ['Open source'] },
	'copilot-acp': { badges: ['Code'] },
	custom: { badges: ['Polyvalent'] },
	// MoA (technique interne du moteur) : combine plusieurs modèles → généraliste, qualité.
	moa: { badges: ['Polyvalent', 'Premium'] }
	// mistral : legacy `mistral` ci-dessus. lmstudio / ollama-local : gérés par LOCAL_PROVIDERS.
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
