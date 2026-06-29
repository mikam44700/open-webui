// Générateur de compétences « maison » : transforme un besoin décrit en langage courant
// en une compétence (SKILL.md) de qualité. Jumeau du générateur d'agents (lib/agents/generator.ts),
// mais appliqué aux compétences, en suivant la recette du skill-creator officiel d'Anthropic
// (description bien déclenchante, procédure claire, divulgation progressive, garde-fous).

import { generateOpenAIChatCompletion } from '$lib/apis/openai';

export type GeneratedSkill = {
	label: string; // nom court lisible
	description: string; // ce que ça fait + QUAND l'utiliser (mécanisme de déclenchement)
	instructions: string; // la procédure (corps du SKILL.md)
	category: string; // catégorie de rangement (Vente, Finance, SAV…)
};

// Catégories proposées pour ranger les compétences (le moule s'y réfère).
export const SKILL_CATEGORIES = [
	'Vente',
	'Finance & Compta',
	'Service client',
	'Marketing',
	'Quotidien',
	'Pilotage',
	'Rédaction & Documents',
	'RH',
	'Juridique',
	'Achats',
	'Veille',
	'Process & SOP',
	'Mémoire & Coffre',
	'Autres'
];

// Le « moule » : prompt générateur. Structure en balises (best practice Claude), exemple intégré
// (few-shot), auto-critique silencieuse. La qualité de ce prompt = la qualité des compétences.
export const SKILL_GENERATOR_SYSTEM = `<role>
Tu es un concepteur expert de « compétences » pour agents IA, au service de dirigeants de PME
françaises non techniques. Une compétence = un savoir-faire réutilisable (une procédure métier
précise) qu'un agent applique au bon moment. Tu transformes un besoin décrit en langage courant
en UNE compétence claire, fiable et opérationnelle.
</role>

<regles>
- Français impeccable, ton professionnel et clair, zéro jargon ni anglicisme.
- Concret et utile à une PME française (TVA, devis, relances, RGPD, mise en demeure…).
- LA DESCRIPTION est le point le plus important : elle dit ce que fait la compétence ET QUAND
  l'utiliser. Sois explicite sur les situations de déclenchement (liste les cas concrets), un peu
  « insistant », pour que l'agent l'active dès que c'est pertinent — sans la rendre vague.
- LA PROCÉDURE (instructions) : des étapes numérotées claires et actionnables, dans l'ordre. Explique
  le POURQUOI quand c'est utile (l'agent décide mieux). Reste concise et lisible (l'essentiel ;
  pas de remplissage). Si la compétence mobilise des outils (email, agenda, CRM, documents), dis-le
  nommément ; appuie-toi sur le coffre (mémoire) pour le contexte et le rangement.
- GARDE-FOUS TOUJOURS : ne jamais inventer (si l'info manque, le dire) ; tout chiffre tagué
  vérifié / estimé / inconnu ; aucune action externe engageante (envoi, dépense, suppression) sans
  validation du dirigeant ; citer ses sources (« d'après [[fiche-client-Roux]] ») ; escalade humaine
  sur les cas sensibles.
- Si le besoin est vague : conçois la compétence la plus probable et utile, sans inventer de faits
  précis (montants, noms, procédures internes spécifiques).
</regles>

<reflexion_silencieuse>
Avant de répondre, en silence (ne montre jamais ce raisonnement) :
1. Quel est le savoir-faire réel et le résultat concret attendu ?
2. Quand un agent doit-il déclencher cette compétence ? (situations, mots-clés, demandes types)
3. Quelles étapes un vrai professionnel suivrait, dans l'ordre ? quels outils + quel usage du coffre ?
4. Auto-critique : la description déclenche-t-elle au bon moment ? la procédure est-elle précise et
   actionnable ? les garde-fous couvrent-ils les vrais risques ? as-tu retiré tout le blabla ?
Corrige avant de produire la sortie. Ne renvoie que le JSON final.
</reflexion_silencieuse>

<format_de_sortie>
Réponds UNIQUEMENT avec un objet JSON valide, sans aucun texte autour, sans balises de code.
Clés exactes :
- "label" : nom court de la compétence, 2 à 4 mots.
- "description" : 1 à 2 phrases — ce que fait la compétence ET quand l'agent doit l'utiliser
  (situations concrètes de déclenchement). 280 caractères maximum.
- "instructions" : la procédure en Markdown — étapes numérotées concrètes, puis une courte section
  « Garde-fous » (titre ##). C'est le cœur de la valeur.
- "category" : UNE seule catégorie parmi exactement : Vente, Finance & Compta, Service client,
  Marketing, Quotidien, Pilotage, Rédaction & Documents, RH, Juridique, Achats, Veille,
  Process & SOP, Mémoire & Coffre, Autres.
</format_de_sortie>

<exemple_de_qualite>
Niveau attendu (besoin : « relancer les devis restés sans réponse, poliment, après une semaine »).
label = "Relance de devis"
description = "Relance les devis envoyés restés sans réponse. À utiliser dès qu'un devis dépasse 7 jours sans retour, ou quand le dirigeant demande de relancer un prospect ou de faire le point sur les devis en attente."
instructions =
"1. Repère les devis envoyés il y a plus de 7 jours sans réponse (via le suivi des devis et le coffre).
2. Pour chacun, consulte le coffre : historique du client, échanges passés, montant, objet du devis.
3. Rédige une relance courte, courtoise et personnalisée — rappelle l'objet et propose de répondre aux questions. Jamais de ton insistant.
4. Récapitule au dirigeant la liste des relances prêtes (client, devis, message proposé) pour validation.
5. Après validation, envoie, puis range le suivi dans le coffre (date de relance, statut).

## Garde-fous
- Tu n'envoies jamais une relance sans validation du dirigeant.
- Tu n'inventes aucun montant ni échéance : si l'info manque, tu le signales.
- Tu restes courtois et non agressif ; au 2e rappel sans réponse, tu proposes d'arrêter plutôt que d'insister."
</exemple_de_qualite>

Conçois maintenant la compétence demandée, au moins aussi précise et opérationnelle que cet exemple.`;

// Extrait l'objet JSON de la réponse du modèle (tolère les balises de code éventuelles).
const parseSkill = (raw: string): GeneratedSkill => {
	let s = (raw ?? '').trim();

	const fence = s.match(/```(?:json)?\s*([\s\S]*?)```/i);
	if (fence) s = fence[1].trim();

	const start = s.indexOf('{');
	const end = s.lastIndexOf('}');
	if (start >= 0 && end > start) s = s.slice(start, end + 1);

	const obj = JSON.parse(s);

	const label = String(obj.label ?? '').trim() || 'Nouvelle compétence';
	const description = String(obj.description ?? '').trim();
	const instructions = String(obj.instructions ?? '').trim();
	const rawCat = String(obj.category ?? '').trim();
	const category = SKILL_CATEGORIES.includes(rawCat) ? rawCat : 'Autres';

	if (!instructions) {
		throw new Error('Procédure vide générée.');
	}

	return { label, description, instructions, category };
};

// Génère une compétence depuis une phrase. `previous` + `adjustment` permettent d'affiner.
export const generateSkill = async (
	token: string,
	model: string,
	brief: string,
	opts: {
		previous?: GeneratedSkill;
		adjustment?: string;
		connectedTools?: string[];
	} = {}
): Promise<GeneratedSkill> => {
	if (!model) {
		throw new Error('Aucun modèle disponible pour générer la compétence.');
	}

	let userContent = '';
	if (brief.trim()) {
		userContent += `Besoin du dirigeant : ${brief.trim()}\n\n`;
	}

	const tools = (opts.connectedTools ?? []).filter(Boolean);
	if (tools.length) {
		userContent +=
			`Outils réellement connectés dans cette entreprise (mobilise-les NOMMÉMENT dans la procédure quand c'est pertinent ; ne suppose aucun outil absent de cette liste) : ${tools.join(', ')}.\nLe coffre (second cerveau) est toujours disponible pour la mémoire et le contexte.\n\n`;
	}

	if (!userContent) {
		userContent = 'Conçois une compétence utile et générale pour une PME.';
	}

	if (opts.previous && opts.adjustment && opts.adjustment.trim()) {
		userContent +=
			`Voici la compétence générée précédemment :\n` +
			JSON.stringify(opts.previous) +
			`\n\nAjuste-la selon cette demande, en gardant ce qui est bon : ${opts.adjustment.trim()}`;
	}

	const res = await generateOpenAIChatCompletion(token, {
		model,
		stream: false,
		temperature: 0.7,
		messages: [
			{ role: 'system', content: SKILL_GENERATOR_SYSTEM },
			{ role: 'user', content: userContent }
		]
	});

	const content = res?.choices?.[0]?.message?.content ?? '';
	return parseSkill(content);
};

// Transforme une compétence EXISTANTE (souvent anglaise, liée à un produit/personne, ou non branchée)
// en une compétence de qualité « niveau 4 » pour Agent OS : généralisée, en français, branchée aux
// outils réellement connectés + au coffre, avec garde-fous. C'est le cœur du bouton « Importer une skill ».
export const transformSkill = async (
	token: string,
	model: string,
	sourceMarkdown: string,
	opts: { connectedTools?: string[] } = {}
): Promise<GeneratedSkill> => {
	if (!model) {
		throw new Error('Aucun modèle disponible pour transformer la compétence.');
	}
	if (!sourceMarkdown.trim()) {
		throw new Error('Compétence source vide.');
	}

	let userContent =
		`Voici une compétence existante (issue d'un dépôt public). Elle est souvent en anglais, liée à ` +
		`un produit, une personne ou un prix précis, et rarement branchée à de vrais outils. ` +
		`TRANSFORME-la en compétence « niveau 4 » pour Agent OS :\n` +
		`- garde l'OSSATURE utile (frameworks, étapes, critères) ;\n` +
		`- GÉNÉRALISE : retire tout nom de produit, de personne, de prix ou de marque spécifique ;\n` +
		`- traduis et peaufine en français impeccable, ton PME ;\n` +
		`- BRANCHE-la : dis quels outils connectés elle mobilise et comment elle s'appuie sur le coffre ;\n` +
		`- ajoute les garde-fous Agent OS (validation avant action externe, jamais inventer, citer ses sources).\n\n`;

	const tools = (opts.connectedTools ?? []).filter(Boolean);
	if (tools.length) {
		userContent +=
			`Outils réellement connectés (mobilise-les NOMMÉMENT quand c'est pertinent ; n'en suppose aucun absent de la liste) : ${tools.join(', ')}.\nLe coffre (second cerveau) est toujours disponible.\n\n`;
	}

	userContent += `Compétence source à transformer :\n\n${sourceMarkdown.trim()}`;

	const res = await generateOpenAIChatCompletion(token, {
		model,
		stream: false,
		temperature: 0.6,
		messages: [
			{ role: 'system', content: SKILL_GENERATOR_SYSTEM },
			{ role: 'user', content: userContent }
		]
	});

	const content = res?.choices?.[0]?.message?.content ?? '';
	return parseSkill(content);
};

// Normalise une URL GitHub (page blob/tree ou raw) vers l'URL brute du SKILL.md.
export const toRawSkillUrl = (url: string): string => {
	let u = (url ?? '').trim();
	if (!u) return u;
	u = u
		.replace('https://github.com/', 'https://raw.githubusercontent.com/')
		.replace('/blob/', '/')
		.replace('/tree/', '/');
	// Si l'URL ne pointe pas déjà sur un fichier .md, on vise le SKILL.md du dossier.
	if (!/\.md(\?.*)?$/i.test(u)) {
		u = u.replace(/\/+$/, '') + '/SKILL.md';
	}
	return u;
};
