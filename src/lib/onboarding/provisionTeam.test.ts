import { describe, it, expect, vi } from 'vitest';
import {
	socleSpecialists,
	provisionSocleTeam,
	MIKE_TEMPLATE_ID,
	type CreateFn
} from './provisionTeam';

// Un `create` qui réussit toujours et note ce qu'on lui a demandé.
const spyCreate = () => {
	const calls: string[] = [];
	const fn: CreateFn = async (tpl) => {
		calls.push(tpl.id);
	};
	return { fn, calls };
};

describe('socleSpecialists', () => {
	it('rend les 6 spécialistes du socle', () => {
		expect(socleSpecialists().map((t) => t.id)).toEqual([
			'agent-obsidian',
			'assistant-administratif',
			'commercial-devis',
			'comptable-impayes',
			'redacteur-de-documents',
			'veille'
		]);
	});

	it('EXCLUT Mike : il est le profil `default`, le créer ferait un second orchestrateur', () => {
		expect(socleSpecialists().some((t) => t.id === MIKE_TEMPLATE_ID)).toBe(false);
	});

	it('chaque spécialiste part avec sa mission, sa description et son visage', () => {
		for (const t of socleSpecialists()) {
			expect(t.soul.trim(), `${t.id} sans mission`).not.toBe('');
			expect(t.description.trim(), `${t.id} sans description`).not.toBe('');
			expect(t.image, `${t.id} sans visage`).toBeTruthy();
		}
	});
});

describe('provisionSocleTeam', () => {
	it('crée les 6 spécialistes quand le client est neuf', async () => {
		const { fn, calls } = spyCreate();
		const res = await provisionSocleTeam([], fn);

		expect(calls).toHaveLength(6);
		expect(res.created).toHaveLength(6);
		expect(res.failed).toEqual([]);
	});

	it('crée l’agent avec son IDENTIFIANT, jamais son libellé affiché', async () => {
		// Le bridge slugifie `name` : passer « Recherche & Veille » créerait `recherche-veille`,
		// un SECOND Léo à côté de `veille`. Même piège que le catalogue (cf. AgentCatalogue).
		const seen: Array<{ name: string; soul: string }> = [];
		await provisionSocleTeam([], async (tpl) => {
			seen.push({ name: tpl.id, soul: tpl.soul });
		});
		expect(seen.map((s) => s.name)).toContain('veille');
		expect(seen.every((s) => s.name === s.name.toLowerCase())).toBe(true);
	});

	it('est idempotent : ne recrée pas un agent déjà présent', async () => {
		const { fn, calls } = spyCreate();
		const res = await provisionSocleTeam(['agent-obsidian', 'veille'], fn);

		expect(calls).not.toContain('agent-obsidian');
		expect(calls).not.toContain('veille');
		expect(calls).toHaveLength(4);
		expect(res.alreadyThere).toEqual(['agent-obsidian', 'veille']);
	});

	it('ne touche à rien quand toute l’équipe est déjà là', async () => {
		const { fn, calls } = spyCreate();
		const ids = socleSpecialists().map((t) => t.id);
		const res = await provisionSocleTeam(ids, fn);

		expect(calls).toEqual([]);
		expect(res.created).toEqual([]);
		expect(res.alreadyThere).toHaveLength(6);
	});

	it('un échec n’arrête pas les autres — et il est rapporté, jamais avalé', async () => {
		const create: CreateFn = async (tpl) => {
			if (tpl.id === 'commercial-devis') throw new Error('moteur indisponible');
		};
		const res = await provisionSocleTeam([], create);

		expect(res.failed).toEqual(['commercial-devis']);
		expect(res.created).toHaveLength(5);
	});

	it('« existe déjà » côté bridge n’est PAS un échec (course entre deux onglets)', async () => {
		const create: CreateFn = async (tpl) => {
			if (tpl.id === 'veille') throw { error: { code: 'exists' } };
		};
		const res = await provisionSocleTeam([], create);

		expect(res.failed).toEqual([]);
		expect(res.alreadyThere).toContain('veille');
	});

	it('crée les agents un par un : le moteur clone la config à chaque naissance', async () => {
		// Six `create_profile` en parallèle se marchent dessus (même config.yaml source).
		let running = 0;
		let maxParallel = 0;
		await provisionSocleTeam([], async () => {
			running += 1;
			maxParallel = Math.max(maxParallel, running);
			await new Promise((r) => setTimeout(r, 1));
			running -= 1;
		});
		expect(maxParallel).toBe(1);
	});

	it('ne crée JAMAIS Mike, même si l’appelant prétend qu’il manque', async () => {
		const { fn, calls } = spyCreate();
		await provisionSocleTeam([], fn);
		expect(calls).not.toContain(MIKE_TEMPLATE_ID);
	});

	it('encaisse la liste RÉELLE du moteur, où Mike s’appelle `default`', async () => {
		// Vérifié sur le bridge le 2026-07-15 : GET /agents rend `default` + les spécialistes.
		// Mike n'apparaît JAMAIS sous son id de template — chercher `mike-chef-orchestre` dans
		// cette liste ne le trouve pas et ferait conclure à tort qu'il manque.
		const { fn, calls } = spyCreate();
		const res = await provisionSocleTeam(['default'], fn);

		expect(calls).toHaveLength(6); // `default` n'est pas un spécialiste : les 6 sont à créer
		expect(res.failed).toEqual([]);
		expect(calls).not.toContain('default');
	});
});
