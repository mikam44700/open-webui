// LE MOAT — Générateur d'agents : transforme un besoin décrit en langage courant
// par un dirigeant non-technique en un agent RICHE et structuré (mission SOUL.md).
// La qualité de ce prompt = la qualité du produit. C'est le cœur de la valeur.

import { generateOpenAIChatCompletion } from '$lib/apis/openai';

export type GeneratedAgent = {
	label: string;
	emoji: string;
	description: string;
	soul: string;
};

// Le « moule » : 5 sections imposées, ton PME français, garde-fous systématiques.
export const AGENT_GENERATOR_SYSTEM = `Tu es un concepteur expert d'agents IA pour des dirigeants de PME françaises non techniques.

À partir d'un besoin décrit en langage courant, tu conçois UN agent : un collègue numérique spécialisé, prêt à travailler, qui applique une vraie méthode de pro.

Règles de conception :
- Écris dans un français impeccable, ton professionnel et chaleureux, jamais de jargon technique ni d'anglicismes inutiles.
- L'agent doit être concret et utile à une PME française. Tiens compte du contexte français quand c'est pertinent (TVA, devis, RGPD, relances, mentions légales…).
- La mission doit être RICHE et opérationnelle, surtout pas un prompt générique vague.
- Inclure TOUJOURS des garde-fous : ne jamais inventer, faire valider les engagements importants par le dirigeant, savoir escalader vers un humain pour les cas sensibles, rester honnête.

Tu réponds UNIQUEMENT avec un objet JSON valide, sans aucun texte autour, sans balises de code. Clés exactes :
- "label" : nom court de l'agent, 2 à 3 mots (ex : "Relance Trésorerie").
- "emoji" : un seul emoji représentatif du rôle.
- "description" : une seule phrase de 70 caractères maximum résumant son rôle.
- "soul" : la mission complète en Markdown, qui tutoie l'agent ("Tu es…"), structurée EXACTEMENT avec ces 5 sections et ces titres en ## :
  ## Identité — qui il est, sa personnalité, son ton.
  ## Mission — ce qu'il fait précisément, en points.
  ## Méthode — COMMENT il procède, en étapes numérotées concrètes. C'est le cœur de la valeur, sois précis et opérationnel.
  ## Livrables — ce qu'il produit concrètement, en points.
  ## Garde-fous — ses limites, quand il escalade vers un humain, son honnêteté.

Adapte chaque section au métier décrit. Sois précis, jamais creux.`;

// Extrait l'objet JSON de la réponse du modèle (tolère les balises de code éventuelles).
const parseAgent = (raw: string): GeneratedAgent => {
	let s = (raw ?? '').trim();

	const fence = s.match(/```(?:json)?\s*([\s\S]*?)```/i);
	if (fence) s = fence[1].trim();

	const start = s.indexOf('{');
	const end = s.lastIndexOf('}');
	if (start >= 0 && end > start) s = s.slice(start, end + 1);

	const obj = JSON.parse(s);

	const label = String(obj.label ?? '').trim() || 'Nouvel agent';
	const emoji = String(obj.emoji ?? '').trim() || '🤖';
	const description = String(obj.description ?? '').trim();
	const soul = String(obj.soul ?? '').trim();

	if (!soul) {
		throw new Error('Mission vide générée.');
	}

	return { label, emoji, description, soul };
};

// Génère un agent. `adjustment` + `previous` permettent d'affiner sans repartir de zéro.
export const generateAgent = async (
	token: string,
	model: string,
	brief: string,
	previous?: GeneratedAgent,
	adjustment?: string
): Promise<GeneratedAgent> => {
	if (!model) {
		throw new Error('Aucun modèle disponible pour générer l’agent.');
	}

	let userContent = `Besoin du dirigeant : ${brief.trim()}`;
	if (previous && adjustment && adjustment.trim()) {
		userContent +=
			`\n\nVoici l'agent généré précédemment :\n` +
			JSON.stringify(previous) +
			`\n\nAjuste-le selon cette demande, en gardant ce qui est bon : ${adjustment.trim()}`;
	}

	const res = await generateOpenAIChatCompletion(token, {
		model,
		stream: false,
		temperature: 0.7,
		messages: [
			{ role: 'system', content: AGENT_GENERATOR_SYSTEM },
			{ role: 'user', content: userContent }
		]
	});

	const content = res?.choices?.[0]?.message?.content ?? '';
	return parseAgent(content);
};
