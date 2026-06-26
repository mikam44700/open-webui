/**
 * Lancement d'un workflow métier (feature 008).
 *
 * Mécanisme : OpenWebUI pré-remplit un nouveau chat à partir du brouillon stocké dans
 * `sessionStorage['chat-input']` (lu par `Chat.svelte` à l'initialisation). On y écrit le prompt
 * du workflow puis on navigue vers l'accueil (le chat). Le prompt n'est PAS envoyé automatiquement :
 * l'utilisateur garde le contrôle (honnêteté D27). Aucun changement du composant Chat.
 */

/** Clé du brouillon de saisie d'un nouveau chat (cf. Chat.svelte). */
export const NEW_CHAT_INPUT_KEY = 'chat-input';

/**
 * Construit l'objet brouillon attendu par Chat.svelte. Fonction pure (testable).
 */
export const buildChatInput = (prompt: string) => ({
	prompt,
	files: [],
	selectedToolIds: [],
	selectedSkillIds: [],
	selectedFilterIds: [],
	webSearchEnabled: false,
	imageGenerationEnabled: false,
	codeInterpreterEnabled: false
});

/**
 * Démarre un workflow : pré-remplit le nouveau chat avec le prompt, puis ouvre le chat.
 * N'envoie rien automatiquement.
 */
export const startWorkflow = async (prompt: string) => {
	try {
		sessionStorage.setItem(NEW_CHAT_INPUT_KEY, JSON.stringify(buildChatInput(prompt)));
	} catch {
		// sessionStorage indisponible : on ouvre quand même le chat (sans pré-remplissage).
	}
	// Import paresseux : garde le module testable hors environnement SvelteKit.
	const { goto } = await import('$app/navigation');
	goto('/');
};
