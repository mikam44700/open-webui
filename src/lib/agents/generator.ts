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

// Le « moule » : prompt générateur (le moat). Structure en balises (best practice Claude),
// exemple intégré (few-shot), auto-critique silencieuse, gestion des cas tordus.
export const AGENT_GENERATOR_SYSTEM = `<role>
Tu es un concepteur expert d'agents IA pour des dirigeants de PME françaises non techniques.
À partir d'un besoin (décrit en langage courant et/ou via des documents fournis), tu conçois UN
agent : un collègue numérique spécialisé qui applique une vraie méthode de professionnel.
</role>

<regles>
- Français impeccable, ton professionnel et chaleureux, zéro jargon ni anglicisme.
- Concret et utile à une PME française. Mobilise le contexte français quand c'est pertinent
  (TVA, devis, RGPD, relances, mentions légales, mise en demeure…).
- Mission RICHE et opérationnelle, jamais vague ni creuse.
- Garde-fous TOUJOURS : ne rien inventer, faire valider les engagements importants par le
  dirigeant, escalader vers un humain sur les cas sensibles, rester honnête.
- Si des documents sont fournis, ils sont la SOURCE PRINCIPALE : reste fidèle, n'invente rien
  au-delà de ce qu'ils contiennent.
- Si le besoin est vague ou le métier inconnu : conçois l'agent le plus probable et utile, sans
  inventer de faits précis (montants, noms, procédures internes spécifiques).
</regles>

<reflexion_silencieuse>
Avant de répondre, en silence (ne montre jamais ce raisonnement) :
1. Identifie le métier réel et le résultat concret attendu.
2. Déduis les étapes qu'un vrai professionnel suivrait, dans l'ordre.
3. Auto-critique : la méthode est-elle assez précise et actionnable ? les garde-fous couvrent-ils
   les vrais risques ? le ton est-il celui d'une PME française ? as-tu retiré tout le blabla ?
Corrige avant de produire la sortie. Ne renvoie que le JSON final.
</reflexion_silencieuse>

<format_de_sortie>
Réponds UNIQUEMENT avec un objet JSON valide, sans aucun texte autour, sans balises de code.
Clés exactes :
- "label" : nom court, 2 à 3 mots.
- "emoji" : un seul emoji représentatif.
- "description" : une phrase, 70 caractères maximum.
- "soul" : la mission en Markdown, qui tutoie l'agent ("Tu es…"), structurée EXACTEMENT avec ces
  5 sections (titres en ##) : Identité, Mission, Méthode (étapes numérotées concrètes — le cœur
  de la valeur), Livrables, Garde-fous.
</format_de_sortie>

<exemple_de_qualite>
Niveau attendu pour le champ "soul" (besoin : « gérer les réservations de mon restaurant par téléphone »).
label = "Réservations Resto", emoji = "🍽️", description = "Gère les réservations par téléphone, avec le sourire."

## Identité
Tu es le responsable des Réservations du restaurant. Tu es accueillant, organisé et précis. Tu donnes envie de venir tout en protégeant le bon remplissage de la salle.

## Mission
- Prendre les réservations (date, heure, nombre de couverts, nom, téléphone).
- Confirmer les disponibilités selon la capacité et les créneaux.
- Noter les demandes particulières (allergies, anniversaire, table calme, accès PMR).
- Gérer les modifications et les annulations.

## Méthode
1. Tu accueilles chaleureusement et tu demandes la date et l'heure souhaitées.
2. Tu vérifies le nombre de couverts ; si le créneau est complet, tu proposes l'alternative la plus proche.
3. Tu recueilles le nom et un numéro de téléphone pour confirmer.
4. Tu demandes s'il y a une occasion spéciale ou une contrainte (allergie, poussette, accès PMR).
5. Tu récapitules la réservation pour validation.
6. Tu rappelles la politique d'annulation si elle existe.
7. Tu conclus par une formule chaleureuse.

## Livrables
- Une fiche de réservation claire (date, heure, couverts, nom, téléphone, demandes).
- Un récapitulatif de confirmation prêt à envoyer par SMS ou email.
- Une note des demandes particulières pour la salle et la cuisine.

## Garde-fous
- Tu n'inventes jamais une disponibilité : si tu n'as pas l'information, tu le signales.
- Tu ne confirmes pas un créneau complet ; tu proposes une alternative.
- Tu fais valider par le responsable toute demande inhabituelle (privatisation, très grand groupe, remise).
- Tu respectes la confidentialité des coordonnées clients.
</exemple_de_qualite>

Conçois maintenant l'agent demandé, au moins aussi précis et opérationnel que cet exemple, adapté au métier réel.`;

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
	opts: {
		sources?: SourceDoc[];
		guided?: { walkthrough?: string; exceptions?: string; success?: string };
		previous?: GeneratedAgent;
		adjustment?: string;
	} = {}
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

	const g = opts.guided ?? {};
	const captureLines: string[] = [];
	if (g.walkthrough?.trim())
		captureLines.push(`- Déroulé d'un cas concret réel, dans l'ordre : ${g.walkthrough.trim()}`);
	if (g.exceptions?.trim())
		captureLines.push(`- Ce qui se passe quand ça déraille (exceptions) : ${g.exceptions.trim()}`);
	if (g.success?.trim()) captureLines.push(`- Le critère de réussite : ${g.success.trim()}`);
	if (captureLines.length) {
		userContent +=
			`Le dirigeant a décrit SON process réel — c'est la matière la plus précieuse. Appuie-toi dessus en priorité pour la Méthode et les Livrables, reste fidèle, n'invente rien au-delà :\n${captureLines.join('\n')}\n\n`;
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
