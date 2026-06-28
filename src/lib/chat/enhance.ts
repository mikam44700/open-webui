// « Améliorer ma demande » — reformule le message d'un dirigeant pour qu'il soit clair et
// actionnable par son agent, SANS changer l'intention ni inventer d'information.
// L'utilisateur voit toujours le résultat dans le champ avant d'envoyer (membrane humaine).

import { generateOpenAIChatCompletion } from '$lib/apis/openai';

const ENHANCE_SYSTEM = `Tu reformules la demande d'un dirigeant de PME pour qu'elle soit claire, précise et facile à exécuter par son assistant IA.

Règles strictes :
- Garde EXACTEMENT son intention et sa langue (français).
- Clarifie l'objectif et la structure (qui, quoi, format attendu) seulement si c'est implicite.
- N'invente JAMAIS de faits absents : ni nom, ni montant, ni date, ni détail non fourni.
- Reste concis et naturel, pas de jargon.
- Réponds UNIQUEMENT avec la demande reformulée : aucun préambule, aucun guillemet, aucune explication.`;

export const enhancePrompt = async (
	token: string,
	model: string,
	text: string
): Promise<string> => {
	if (!model) {
		throw new Error('Aucun modèle disponible.');
	}

	const res = await generateOpenAIChatCompletion(token, {
		model,
		stream: false,
		temperature: 0.3,
		messages: [
			{ role: 'system', content: ENHANCE_SYSTEM },
			{ role: 'user', content: text }
		]
	});

	let out = (res?.choices?.[0]?.message?.content ?? '').trim();

	// Retire d'éventuels guillemets enveloppants ajoutés par le modèle.
	if (
		(out.startsWith('"') && out.endsWith('"')) ||
		(out.startsWith('«') && out.endsWith('»')) ||
		(out.startsWith('“') && out.endsWith('”'))
	) {
		out = out.slice(1, -1).trim();
	}

	return out || text;
};
