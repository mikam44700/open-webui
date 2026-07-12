// Banc d'essai « golden set » de l'onboarding — mesure le TAUX DE REMPLISSAGE de la fiche entreprise
// sur de VRAIS sites, avec le VRAI pipeline (crawl bridge → même prompt → même parser). C'est le filet
// anti-régression que les tests unitaires ne donnent pas : eux valident le parsing sur du JSON fabriqué ;
// LUI valide que crawl + prompt remplissent réellement les cases. À relancer après toute modif du prompt
// ou du crawl — si un champ chute, on le voit AVANT le client.
//
// Inerte par défaut (skip) : il tape le réseau (bridge + modèle). Pour le lancer :
//
//   1. Récupère ton token : dans le navigateur sur http://localhost:3000, console → `localStorage.token`
//   2. Récupère la clé du bridge : `docker exec agentos-open-webui printenv BRIDGE_KEY`
//   3. Lance :
//        cd app/web
//        EVAL_TOKEN="<jwt>" EVAL_BRIDGE_KEY="<clé>" npx vitest run fillRate.eval
//
// Sites : édite SITES ci-dessous. Le meilleur golden set = TES vrais sites prospects/clients.

import { describe, it } from 'vitest';
import {
	SYNTHESIS_SYSTEM_PROMPT,
	buildSynthesisUserContent,
	parseSynthesis,
	type CompanyContext
} from './companySynthesis';

const TOKEN = process.env.EVAL_TOKEN ?? '';
const BRIDGE_KEY = process.env.EVAL_BRIDGE_KEY ?? '';
const WEBUI = process.env.EVAL_WEBUI ?? 'http://localhost:3000';
const BRIDGE = process.env.EVAL_BRIDGE ?? 'http://localhost:8650';
const MODEL = process.env.EVAL_MODEL ?? 'Agent Hermes';

// Sites réels, secteurs variés (SaaS, banque, santé). Ajoute TES prospects — c'est là que le banc
// prend toute sa valeur. Des sites tiers peuvent évoluer : ce banc est un indicateur manuel, pas un CI.
const SITES: string[] = [
	'https://www.zelty.fr',
	'https://qonto.com/fr',
	'https://www.doctolib.fr'
];

// Les 10 blocs de la fiche + un libellé court, dans l'ordre d'affichage.
const FIELDS: { key: keyof CompanyContext; label: string }[] = [
	{ key: 'nomEntreprise', label: 'Nom' },
	{ key: 'secteur', label: 'Secteur' },
	{ key: 'coordonnees', label: 'Coordonnées' },
	{ key: 'offre', label: 'Offre' },
	{ key: 'services', label: 'Services' },
	{ key: 'tonDeMarque', label: 'Ton' },
	{ key: 'vocabulaire', label: 'Vocabulaire' },
	{ key: 'clienteleCible', label: 'Clientèle' },
	{ key: 'problemesResolus', label: 'Problèmes' },
	{ key: 'preuveSociale', label: 'Preuves' }
];

const isFilled = (v: string | string[]): boolean =>
	Array.isArray(v) ? v.length > 0 : v.trim() !== '';

// Crawl multi-pages via le bridge (même endpoint que l'app, appelé en direct).
const crawl = async (url: string): Promise<{ markdown: string; pages: number }> => {
	const res = await fetch(`${BRIDGE}/onboarding/crawl`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', 'X-Bridge-Key': BRIDGE_KEY },
		body: JSON.stringify({ url })
	});
	if (!res.ok) throw new Error(`crawl HTTP ${res.status}`);
	const data = await res.json();
	return { markdown: data.markdown ?? '', pages: (data.pages ?? []).length };
};

// Synthèse via le modèle actif (même prompt, même endpoint que l'app).
const synthesize = async (markdown: string): Promise<CompanyContext> => {
	const res = await fetch(`${WEBUI}/api/chat/completions`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
		body: JSON.stringify({
			model: MODEL,
			stream: false,
			temperature: 0.2,
			messages: [
				{ role: 'system', content: SYNTHESIS_SYSTEM_PROMPT },
				{ role: 'user', content: buildSynthesisUserContent(markdown) }
			]
		})
	});
	if (!res.ok) throw new Error(`synthèse HTTP ${res.status}`);
	const data = await res.json();
	return parseSynthesis(data?.choices?.[0]?.message?.content ?? '');
};

describe.skipIf(!TOKEN || !BRIDGE_KEY)('golden set — taux de remplissage onboarding', () => {
	it(
		'mesure le remplissage de la fiche sur des sites réels',
		async () => {
			const rows: { url: string; filled: number; pages: number; missing: string[] }[] = [];

			for (const url of SITES) {
				try {
					const { markdown, pages } = await crawl(url);
					const ctx = await synthesize(markdown);
					const missing = FIELDS.filter((f) => !isFilled(ctx[f.key])).map((f) => f.label);
					rows.push({ url, filled: FIELDS.length - missing.length, pages, missing });
				} catch (err) {
					rows.push({ url, filled: 0, pages: 0, missing: [`ERREUR: ${(err as Error).message}`] });
				}
			}

			// Rapport lisible.
			const line = '─'.repeat(72);
			console.log(`\n${line}\n  BANC D'ESSAI ONBOARDING — taux de remplissage (10 blocs)\n${line}`);
			for (const r of rows) {
				const pct = Math.round((r.filled / FIELDS.length) * 100);
				console.log(
					`  ${r.filled}/10 (${pct}%)  ${r.pages}p  ${r.url}` +
						(r.missing.length ? `\n        manquants : ${r.missing.join(', ')}` : '  ✓ complet')
				);
			}
			const totalFilled = rows.reduce((s, r) => s + r.filled, 0);
			const avg = Math.round((totalFilled / (rows.length * FIELDS.length)) * 100);
			// Champ le plus faible (celui qui manque le plus souvent) → la prochaine cible d'amélioration.
			const missCount: Record<string, number> = {};
			for (const r of rows) for (const m of r.missing) missCount[m] = (missCount[m] ?? 0) + 1;
			const weakest = Object.entries(missCount).sort((a, b) => b[1] - a[1])[0];
			console.log(line);
			console.log(`  MOYENNE : ${avg}% de remplissage sur ${rows.length} site(s)`);
			if (weakest) console.log(`  Champ le plus faible : ${weakest[0]} (manque ${weakest[1]}×)`);
			console.log(`${line}\n`);
		},
		120_000 * (SITES.length + 1)
	);
});
