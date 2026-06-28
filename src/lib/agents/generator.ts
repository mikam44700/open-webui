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

// Un document fourni par le dirigeant (procédure existante), texte déjà extrait.
export type SourceDoc = { name: string; content: string };

// Garde-fous qualité : 1 agent = 1 métier. Au-delà, c'est plusieurs agents.
export const MAX_DOCS = 3;
// Budget de texte total (~18-20 pages) avant condensation, pour garder l'IA focalisée.
const MAX_TOTAL_CHARS = 24000;
// Au-delà, un document est condensé individuellement avant génération.
const CONDENSE_THRESHOLD = 8000;

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

// Condense un document volumineux en sa procédure essentielle (fidèle, sans invention).
const condenseDocument = async (
	token: string,
	model: string,
	name: string,
	text: string
): Promise<string> => {
	try {
		const res = await generateOpenAIChatCompletion(token, {
			model,
			stream: false,
			temperature: 0.2,
			messages: [
				{
					role: 'system',
					content:
						'Tu extrais l’essentiel d’un document de procédure métier. Restitue UNIQUEMENT la procédure : son déclencheur, ses étapes dans l’ordre, ses règles, ses cas particuliers. Reste strictement fidèle au document, n’invente rien, n’ajoute rien. Réponds en points clairs, 400 mots maximum.'
				},
				{ role: 'user', content: `Document « ${name} » :\n\n${text}` }
			]
		});
		return res?.choices?.[0]?.message?.content?.trim() || text;
	} catch {
		// En cas d'échec de condensation, on garde le texte tronqué plutôt que de bloquer.
		return text.slice(0, CONDENSE_THRESHOLD);
	}
};

// Prépare le bloc « documents » : condense si l'ensemble dépasse le budget de contexte.
const prepareSources = async (
	token: string,
	model: string,
	sources: SourceDoc[]
): Promise<string> => {
	let docs = (sources ?? [])
		.map((s) => ({ name: s.name, content: (s.content ?? '').trim() }))
		.filter((s) => s.content);

	if (!docs.length) return '';

	const total = docs.reduce((n, d) => n + d.content.length, 0);
	if (total > MAX_TOTAL_CHARS) {
		docs = await Promise.all(
			docs.map(async (d) =>
				d.content.length > CONDENSE_THRESHOLD
					? { name: d.name, content: await condenseDocument(token, model, d.name, d.content) }
					: d
			)
		);
	}

	return docs.map((d) => `--- Document : ${d.name} ---\n${d.content}`).join('\n\n');
};

// Génère un agent depuis une phrase et/ou des documents.
// `adjustment` + `previous` permettent d'affiner sans repartir de zéro.
export const generateAgent = async (
	token: string,
	model: string,
	brief: string,
	opts: { sources?: SourceDoc[]; previous?: GeneratedAgent; adjustment?: string } = {}
): Promise<GeneratedAgent> => {
	if (!model) {
		throw new Error('Aucun modèle disponible pour générer l’agent.');
	}

	const sourcesBlock = await prepareSources(token, model, opts.sources ?? []);

	let userContent = '';
	if (brief.trim()) {
		userContent += `Besoin du dirigeant : ${brief.trim()}\n\n`;
	}
	if (sourcesBlock) {
		userContent +=
			`Documents fournis par le dirigeant (procédures existantes — utilise-les comme source principale, reste fidèle, n'invente pas) :\n\n${sourcesBlock}\n\n`;
	}
	if (!userContent) {
		userContent = 'Conçois un assistant généraliste utile pour une PME.';
	}

	if (opts.previous && opts.adjustment && opts.adjustment.trim()) {
		userContent +=
			`Voici l'agent généré précédemment :\n` +
			JSON.stringify(opts.previous) +
			`\n\nAjuste-le selon cette demande, en gardant ce qui est bon : ${opts.adjustment.trim()}`;
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
