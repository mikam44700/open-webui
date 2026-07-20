<script lang="ts">
	// Page « Compétences » de l'Espace de travail : NOS compétences maison (sur mesure).
	// Distinctes des compétences natives Hermes — ce sont celles qu'on crée pour nos agents.
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getCustomSkills,
		getCustomSkill,
		createCustomSkill,
		deleteCustomSkill
	} from '$lib/apis/capabilities';
	import { getModels } from '$lib/apis';
	import { getModelItems, setModelCompetences } from '$lib/apis/models';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	// Portraits cadrés visage fournis par Michael (dossier VisageAvatars) : les avatars
	// d'origine sont des personnages en pied, illisibles en petite pastille ronde.
	const visage = (id: string) => `${WEBUI_BASE_URL}/static/agents/faces/${id}.png`;
	const replierSurAvatar = (e: Event, id: string) => {
		const img = e.currentTarget as HTMLImageElement;
		const repli = `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${id}`;
		if (img.src.endsWith('/favicon.png')) return;
		img.src = img.src.includes('/faces/') ? repli : '/favicon.png';
	};
	import { getIntegrations } from '$lib/apis/integrations';
	import { getConnectors } from '$lib/apis/connectors';
	import { generateSkill, transformSkill, toRawSkillUrl } from '$lib/skills/skill-generator';
	import { expertMode } from '$lib/stores';
	import { isBridgeDown } from '$lib/apis/isBridgeDown';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import { SKILL_CATEGORIES } from '$lib/skills/skill-generator';

	const i18n = getContext('i18n');

	type CustomSkill = {
		name: string;
		label: string;
		description: string;
		category?: string;
		enabled?: boolean;
	};

	let loading = true;
	let bridgeDown = false;
	let skills: CustomSkill[] = [];
	let search = '';

	// ── Ton équipe et ce qu'elle sait faire ────────────────────────────────
	// meta.outils = ce que l'agent sait déjà faire (livré, non modifiable)
	// meta.competences = les procédures métier que le patron lui confie
	let agents: any[] = [];
	let agentsCharges = false;
	let agentSelectionneId: string | null = null;
	// Vue par defaut : l'equipe. « Toutes les procedures » est un second volet,
	// pour ne pas empiler deux longues listes sur le meme ecran (progressive disclosure).
	let vue: 'equipe' | 'bibliotheque' = 'equipe';

	const chargerAgents = async () => {
		try {
			const res = await getModelItems(localStorage.token, '', null, null, null, null, null);
			const ORDRE = ['luna', 'mike', 'victor', 'lea', 'sacha', 'theo', 'clara'];
			const rang = (a: any) => {
				const i = ORDRE.indexOf(a.id);
				return i === -1 ? ORDRE.length : i;
			};
			agents = (res?.items ?? []).slice().sort((a: any, b: any) => rang(a) - rang(b));
			if (!agentSelectionneId && agents.length) agentSelectionneId = agents[0].id;
		} catch {
			agents = [];
		} finally {
			agentsCharges = true;
		}
	};

	const enregistrerCompetences = async (agent: any, liste: string[]) => {
		try {
			await setModelCompetences(localStorage.token, agent.id, liste);
			// Mise à jour locale immédiate (évite un rechargement complet de la liste)
			agents = agents.map((a) =>
				a.id === agent.id ? { ...a, meta: { ...(a.meta ?? {}), competences: liste } } : a
			);
		} catch (err) {
			toast.error($i18n.t('La modification n’a pas pu être enregistrée.'));
		}
	};

	$: agentSelectionne = agents.find((a) => a.id === agentSelectionneId) ?? null;
	$: competencesDe = (agent: any) =>
		(agent?.meta?.competences ?? [])
			.map((n: string) => skills.find((sk) => sk.name === n))
			.filter(Boolean);
	$: totalConfiees = agents.reduce(
		(n, a) => n + ((a?.meta?.competences ?? []).length ? 1 : 0),
		0
	);

	const ajouterCompetence = (agent: any, nom: string) => {
		const actuelles = agent?.meta?.competences ?? [];
		if (actuelles.includes(nom)) return;
		enregistrerCompetences(agent, [...actuelles, nom]);
	};

	// Retirer une compétence n'efface RIEN : elle reste dans la bibliothèque,
	// elle quitte simplement cet agent. Action réversible d'un clic.
	const retirerCompetence = (agent: any, nom: string) => {
		const actuelles = agent?.meta?.competences ?? [];
		enregistrerCompetences(
			agent,
			actuelles.filter((n: string) => n !== nom)
		);
	};

	// Modale de création
	let showCreate = false;
	let saving = false;
	let formLabel = '';
	let formDescription = '';
	let formInstructions = '';
	let formCategory = 'Autres';

	// Regroupement par catégorie + filtre de recherche.
	$: q = search.trim().toLowerCase();
	$: filtered = q
		? skills.filter(
				(s) =>
					s.label.toLowerCase().includes(q) ||
					(s.description ?? '').toLowerCase().includes(q) ||
					(s.category ?? '').toLowerCase().includes(q)
			)
		: skills;
	$: groups = (() => {
		const map = new Map<string, CustomSkill[]>();
		for (const s of filtered) {
			const cat = s.category || 'Autres';
			if (!map.has(cat)) map.set(cat, []);
			map.get(cat)!.push(s);
		}
		return [...map.keys()]
			.sort((a, b) => a.localeCompare(b))
			.map((cat) => ({ cat, items: map.get(cat)!.slice().sort((x, y) => x.label.localeCompare(y.label)) }));
	})();

	// Génération par l'IA (✨) — réutilise le moteur de l'Atelier d'agents.
	let model = '';
	let genBrief = '';
	let generating = false;
	let genError = '';

	// Import d'une skill existante (URL GitHub) → transformée au niveau 4.
	let showImport = false;
	let importUrl = '';
	let importing = false;
	let importError = '';

	const loadModel = async () => {
		if (model) return;
		try {
			const res = await getModels(localStorage.token);
			const list = res?.data ?? res ?? [];
			model = list?.[0]?.id ?? '';
		} catch {
			/* géré au moment de générer */
		}
	};

	// Outils réellement connectés : la compétence générée les mobilisera nommément.
	const fetchConnectedTools = async (): Promise<string[]> => {
		const out: string[] = [];
		try {
			const res: any = await getIntegrations(localStorage.token);
			const list = Array.isArray(res) ? res : (res?.integrations ?? []);
			for (const it of list) {
				if (it?.state === 'connected') out.push(it.label || it.name || it.id);
			}
		} catch {
			/* tolérant */
		}
		try {
			const res: any = await getConnectors(localStorage.token);
			const list = Array.isArray(res) ? res : (res?.connectors ?? []);
			for (const c of list) {
				if (c?.enabled !== false) out.push(c.label || c.id || c.name);
			}
		} catch {
			/* tolérant */
		}
		return [...new Set(out.filter(Boolean))];
	};

	const doGenerate = async () => {
		if (!genBrief.trim()) {
			toast.error($i18n.t('Décris d’abord ce que la compétence doit faire'));
			return;
		}
		generating = true;
		genError = '';
		try {
			if (!model) await loadModel();
			const tools = await fetchConnectedTools();
			const result = await generateSkill(localStorage.token, model, genBrief.trim(), {
				connectedTools: tools
			});
			// On remplit le formulaire : le dirigeant relit et ajuste avant de créer.
			formLabel = result.label;
			formDescription = result.description;
			formInstructions = result.instructions;
			formCategory = result.category || 'Autres';
		} catch (err: any) {
			genError = err?.message || $i18n.t('La génération a échoué. Réessaie.');
		} finally {
			generating = false;
		}
	};

	// Confirmation de suppression
	let showDelete = false;
	let toDelete: CustomSkill | null = null;

	// Détail d'une compétence (contenu complet, au clic sur une carte)
	let showDetail = false;
	let detailLoading = false;
	let detail: { name: string; label: string; description: string; category: string; instructions: string } | null = null;

	const openDetail = async (skill: CustomSkill) => {
		showDetail = true;
		detailLoading = true;
		detail = null;
		try {
			detail = await getCustomSkill(localStorage.token, skill.name);
		} catch {
			toast.error($i18n.t('Impossible d’ouvrir cette compétence'));
			showDetail = false;
		} finally {
			detailLoading = false;
		}
	};

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getCustomSkills(localStorage.token);
			skills = res?.skills ?? [];
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des compétences'));
			}
		} finally {
			loading = false;
		}
	};

	const openCreate = () => {
		formLabel = '';
		formDescription = '';
		formInstructions = '';
		formCategory = 'Autres';
		genBrief = '';
		genError = '';
		showCreate = true;
		loadModel();
	};

	const openImport = () => {
		importUrl = '';
		importError = '';
		showImport = true;
		loadModel();
	};

	// Récupère le SKILL.md d'une URL GitHub, le transforme au niveau 4, et pré-remplit la création.
	const doImport = async () => {
		if (!importUrl.trim()) {
			toast.error($i18n.t('Colle l’URL d’une skill (GitHub)'));
			return;
		}
		importing = true;
		importError = '';
		try {
			const rawUrl = toRawSkillUrl(importUrl);
			const res = await fetch(rawUrl);
			if (!res.ok) throw new Error('introuvable');
			const sourceMarkdown = await res.text();
			if (!sourceMarkdown.trim() || sourceMarkdown.length < 20) {
				throw new Error('vide');
			}
			if (!model) await loadModel();
			const tools = await fetchConnectedTools();
			const result = await transformSkill(localStorage.token, model, sourceMarkdown, {
				connectedTools: tools
			});
			// On bascule sur la modale de création, pré-remplie : le dirigeant relit et ajuste.
			formLabel = result.label;
			formDescription = result.description;
			formInstructions = result.instructions;
			formCategory = result.category || 'Autres';
			genBrief = '';
			genError = '';
			showImport = false;
			showCreate = true;
		} catch (err: any) {
			const msg = err?.message;
			importError =
				msg === 'introuvable'
					? $i18n.t('SKILL.md introuvable à cette URL. Vérifie le lien (vers le dossier de la skill ou son SKILL.md).')
					: msg === 'vide'
						? $i18n.t('Le fichier récupéré est vide.')
						: $i18n.t('Import impossible. Vérifie l’URL et réessaie.');
		} finally {
			importing = false;
		}
	};

	const submitCreate = async () => {
		if (!formLabel.trim()) {
			toast.error($i18n.t('Donnez un nom à la compétence'));
			return;
		}
		saving = true;
		try {
			await createCustomSkill(
				localStorage.token,
				formLabel.trim(),
				formDescription.trim(),
				formInstructions.trim(),
				formCategory || 'Autres'
			);
			showCreate = false;
			toast.success($i18n.t('Compétence créée'));
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Une compétence porte déjà ce nom'));
			} else {
				toast.error($i18n.t('Impossible de créer la compétence'));
			}
		} finally {
			saving = false;
		}
	};

	const askDelete = (skill: CustomSkill) => {
		toDelete = skill;
		showDelete = true;
	};

	const confirmDelete = async () => {
		if (!toDelete) return;
		try {
			await deleteCustomSkill(localStorage.token, toDelete.name);
			toast.success($i18n.t('Compétence supprimée'));
			await load();
		} catch {
			toast.error($i18n.t('Impossible de supprimer la compétence'));
		} finally {
			toDelete = null;
		}
	};

	onMount(() => {
		load();
		chargerAgents();
	});
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Capacités est injoignable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('Le moteur ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- ── Barre de résumé : l'essentiel en un coup d'œil ──────────────── -->
		<div class="flex flex-wrap items-center gap-x-6 gap-y-2 mb-5">
			<div>
				<div class="text-lg font-medium tabular-nums text-gray-900 dark:text-gray-50">
					{agents.length}
				</div>
				<div class="text-[11px] text-gray-500 dark:text-gray-400">{$i18n.t('agents')}</div>
			</div>
			<div class="h-8 w-px bg-gray-200 dark:bg-white/10"></div>
			<div>
				<div class="text-lg font-medium tabular-nums text-gray-900 dark:text-gray-50">
					{skills.length}
				</div>
				<div class="text-[11px] text-gray-500 dark:text-gray-400">
					{$i18n.t('procédures disponibles')}
				</div>
			</div>
			<div class="h-8 w-px bg-gray-200 dark:bg-white/10"></div>
			<div>
				<div class="text-lg font-medium tabular-nums text-gray-900 dark:text-gray-50">
					{totalConfiees}
				</div>
				<div class="text-[11px] text-gray-500 dark:text-gray-400">
					{$i18n.t('agents équipés')}
				</div>
			</div>

			<div class="flex-1"></div>

			<!-- Deux volets plutôt que deux longues listes empilées -->
			<div
				class="flex items-center gap-1 p-1 rounded-full border border-gray-200/60 dark:border-white/6 bg-gray-50 dark:bg-[#161616]"
			>
				<button
					class="px-3.5 py-1.5 rounded-full text-xs transition {vue === 'equipe'
						? 'bg-white dark:bg-[#0a0a0a] text-gray-900 dark:text-gray-50 ring-1 ring-gray-200/80 dark:ring-white/10 font-medium'
						: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white'}"
					on:click={() => (vue = 'equipe')}
				>
					{$i18n.t('Par agent')}
				</button>
				<button
					class="px-3.5 py-1.5 rounded-full text-xs transition {vue === 'bibliotheque'
						? 'bg-white dark:bg-[#0a0a0a] text-gray-900 dark:text-gray-50 ring-1 ring-gray-200/80 dark:ring-white/10 font-medium'
						: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white'}"
					on:click={() => (vue = 'bibliotheque')}
				>
					{$i18n.t('Toutes les procédures')}
				</button>
			</div>
		</div>

		{#if vue === 'equipe'}
			<!-- ── Maître-détail : la liste à gauche, UN agent détaillé à droite ──
			     Recherche du 2026-07-20 : 5 à 9 éléments visibles par défaut, le reste
			     derrière une interaction. Empiler 7 agents + 16 procédures saturait. -->
			{#if !agentsCharges}
				<div class="flex justify-center py-16"><Spinner className="size-4" /></div>
			{:else}
				<div class="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 items-start pb-8">
					<!-- Colonne gauche : l'équipe -->
					<div
						class="rounded-3xl border border-gray-200/80 dark:border-white/6 bg-white dark:bg-[#161616] p-2"
					>
						{#each agents as agent (agent.id)}
							{@const actif = agentSelectionneId === agent.id}
							{@const nb = (agent?.meta?.competences ?? []).length}
							<button
								class="w-full flex items-center gap-2.5 rounded-2xl px-2.5 py-2 text-left transition {actif
									? 'bg-gray-100 dark:bg-[#1e1e1e]'
									: 'hover:bg-gray-50 dark:hover:bg-[#1a1a1a]'}"
								on:click={() => (agentSelectionneId = agent.id)}
							>
								<img
									src={visage(agent.id)}
									alt={agent.name}
									class="size-8 shrink-0 rounded-full object-cover bg-gray-100 dark:bg-[#0f0f0f]"
									loading="lazy"
									on:error={(e) => replierSurAvatar(e, agent.id)}
								/>
								<span
									class="flex-1 min-w-0 text-sm capitalize truncate {actif
										? 'font-medium text-gray-900 dark:text-gray-50'
										: 'text-gray-600 dark:text-gray-300'}"
								>
									{agent.name}
								</span>
								{#if nb}
									<span
										class="shrink-0 rounded-full bg-violet-100 dark:bg-[#6b62f2]/20 px-1.5 text-[11px] font-medium text-violet-700 dark:text-[#a5a0f7] tabular-nums"
									>
										{nb}
									</span>
								{/if}
							</button>
						{/each}
					</div>

					<!-- Colonne droite : le détail de l'agent choisi -->
					{#if agentSelectionne}
						{@const mes = competencesDe(agentSelectionne)}
						{@const dispo = skills.filter(
							(sk) => !(agentSelectionne?.meta?.competences ?? []).includes(sk.name)
						)}
						<div
							class="rounded-3xl border border-gray-200/80 dark:border-white/6 bg-white dark:bg-[#161616] p-6"
						>
							<div class="flex items-center gap-3.5">
								<img
									src={visage(agentSelectionne.id)}
									alt={agentSelectionne.name}
									class="size-14 shrink-0 rounded-full object-cover bg-gray-100 dark:bg-[#0f0f0f] ring-1 ring-gray-200/70 dark:ring-white/10"
									on:error={(e) => replierSurAvatar(e, agentSelectionne.id)}
								/>
								<div class="min-w-0">
									<div
										class="text-base font-medium capitalize tracking-tight text-gray-900 dark:text-gray-50"
									>
										{agentSelectionne.name}
									</div>
									<div class="text-sm text-gray-500 dark:text-gray-400 truncate">
										{agentSelectionne?.meta?.tagline || ''}
									</div>
								</div>
							</div>

							<!-- Ses outils : livrés, non modifiables -->
							{#if (agentSelectionne?.meta?.outils ?? []).length}
								<div class="mt-6">
									<div
										class="text-[10px] font-medium uppercase tracking-[0.14em] text-gray-400 dark:text-gray-500 mb-2"
									>
										{$i18n.t('Ses outils')}
									</div>
									<div class="flex flex-wrap gap-1.5">
										{#each agentSelectionne.meta.outils as outil}
											<span
												class="rounded-lg bg-gray-50 dark:bg-[#1e1e1e] px-2.5 py-1 text-xs text-gray-600 dark:text-gray-300"
												title={outil}
											>
												{outil.split(' — ')[0]}
											</span>
										{/each}
									</div>
								</div>
							{/if}

							<!-- Ses procédures -->
							<div class="mt-6">
								<div
									class="text-[10px] font-medium uppercase tracking-[0.14em] text-gray-400 dark:text-gray-500 mb-2"
								>
									{$i18n.t('Ses procédures')}
									{#if mes.length}<span class="text-gray-300 dark:text-gray-600">· {mes.length}</span>{/if}
								</div>
								{#if mes.length}
									<div class="flex flex-wrap gap-1.5">
										{#each mes as c}
											<button
												class="group inline-flex items-center gap-1.5 rounded-lg bg-violet-50 dark:bg-[#6b62f2]/12 px-2.5 py-1 text-xs text-violet-700 dark:text-[#a5a0f7] transition hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400"
												title={$i18n.t('Retirer cette procédure')}
												on:click={() => retirerCompetence(agentSelectionne, c.name)}
											>
												{c.label}
												<span class="opacity-0 transition group-hover:opacity-100">✕</span>
											</button>
										{/each}
									</div>
									{#if mes.length >= 15}
										<div class="mt-2 text-xs text-amber-600 dark:text-amber-400">
											{$i18n.t('Beaucoup de procédures — il risque de s’y perdre. Mieux vaut un agent dédié.')}
										</div>
									{/if}
								{:else}
									<div
										class="rounded-2xl border border-dashed border-gray-200 dark:border-white/8 px-4 py-5 text-center"
									>
										<div class="text-sm text-gray-500 dark:text-gray-400">
											{$i18n.t('Aucune procédure confiée')}
										</div>
										<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
											{$i18n.t('Choisis ci-dessous ce que tu veux lui confier.')}
										</div>
									</div>
								{/if}
							</div>

							<!-- À confier : la bibliothèque filtrée sur ce qu'il n'a pas encore -->
							{#if dispo.length}
								<div class="mt-6 pt-5 border-t border-gray-100 dark:border-white/6">
									<div
										class="text-[10px] font-medium uppercase tracking-[0.14em] text-gray-400 dark:text-gray-500 mb-2.5"
									>
										{$i18n.t('À lui confier')}
									</div>
									<div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
										{#each dispo as sk (sk.name)}
											<button
												class="group flex items-start gap-2 rounded-xl border border-gray-100 dark:border-white/6 px-3 py-2 text-left transition hover:border-violet-200 dark:hover:border-[#6b62f2]/40 hover:bg-violet-50/40 dark:hover:bg-[#6b62f2]/8"
												on:click={() => ajouterCompetence(agentSelectionne, sk.name)}
											>
												<span
													class="mt-0.5 text-gray-300 dark:text-gray-600 transition group-hover:text-violet-500"
												>+</span>
												<span class="min-w-0">
													<span
														class="block text-xs font-medium truncate text-gray-800 dark:text-gray-100"
													>{sk.label}</span>
													<span class="block text-[10px] text-gray-400 dark:text-gray-500 truncate">
														{sk.category}
													</span>
												</span>
											</button>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		{:else}
			<!-- ── Volet « Toutes les procédures » ──────────────────────────────── -->
			<div class="flex items-start justify-between gap-3 mb-4">
				<p class="text-xs text-gray-500 dark:text-gray-400 max-w-2xl">
					{$i18n.t('Toutes les procédures disponibles. Livrées avec LunarIA, ou créées par toi pour ta façon de travailler.')}
				</p>
				<div class="flex-none flex items-center gap-2">
					<button
						class="text-xs px-3 py-1.5 rounded-full bg-violet-600 text-white hover:bg-violet-700 transition font-medium"
						on:click={openCreate}
					>
						✨ {$i18n.t('Générer avec l’IA')}
					</button>
					{#if $expertMode}
						<button
							class="text-xs px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={openImport}
							title={$i18n.t('Réservé aux réglages avancés')}
						>
							⬇ {$i18n.t('Importer')}
						</button>
					{/if}
				</div>
			</div>

		{#if skills.length > 0}
			<!-- Barre de recherche (utile dès qu'il y a beaucoup de compétences) -->
			<input
				class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-4"
				placeholder={$i18n.t('Rechercher une compétence (nom, catégorie…)')}
				bind:value={search}
			/>

			{#if groups.length > 0}
				<div class="flex flex-col gap-5">
					{#each groups as group (group.cat)}
						<div>
							<div class="flex items-baseline gap-2 mb-2">
								<div class="text-sm font-semibold">{group.cat}</div>
								<div class="text-xs text-gray-400">{group.items.length}</div>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
								{#each group.items as skill (skill.name)}
									{@const porteurs = agents.filter((a) =>
										(a?.meta?.competences ?? []).includes(skill.name)
									)}
									<div
										role="button"
										tabindex="0"
										class="group flex items-start gap-3 border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3.5 transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm cursor-pointer"
										on:click={() => openDetail(skill)}
										on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openDetail(skill)}
										title={$i18n.t('Voir la compétence en détail')}
									>
										<div class="flex-1 min-w-0">
											<div class="text-sm font-medium truncate text-gray-900 dark:text-gray-50">
												{skill.label}
											</div>
											{#if skill.description}
												<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
													{skill.description}
												</div>
											{/if}
											<!-- Qui porte cette procedure : referme la boucle avec la section equipe -->
											<div class="mt-2 flex items-center gap-1.5">
												{#if porteurs.length}
													<div class="flex -space-x-1.5">
														{#each porteurs.slice(0, 4) as p (p.id)}
															<img
																src={visage(p.id)}
																alt={p.name}
																title={p.name}
																class="size-5 rounded-full object-cover bg-gray-100 dark:bg-[#0f0f0f] ring-2 ring-white dark:ring-[#161616]"
																loading="lazy"
																on:error={(e) => replierSurAvatar(e, p.id)}
															/>
														{/each}
													</div>
													<span class="text-[10px] text-gray-500 dark:text-gray-400 capitalize truncate">
														{porteurs.map((p) => p.name).join(', ')}
													</span>
												{:else}
													<span class="text-[10px] text-gray-400 dark:text-gray-500">
														{$i18n.t('Confiée à personne')}
													</span>
												{/if}
											</div>
										</div>
										<button
											class="flex-none self-center text-xs text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
											title={$i18n.t('Supprimer')}
											on:click|stopPropagation={() => askDelete(skill)}
										>
											{$i18n.t('Supprimer')}
										</button>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center text-xs text-gray-500 py-12">
					{$i18n.t('Aucune compétence ne correspond à votre recherche.')}
				</div>
			{/if}
		{:else}
			<div
				class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Aucune compétence maison pour l’instant')}</div>
				<div class="text-xs text-gray-500 max-w-md">
					{$i18n.t('Créez votre première compétence sur mesure : décrivez un savoir-faire propre à votre entreprise, et vos agents pourront l’utiliser.')}
				</div>
				<button
					class="text-sm px-3.5 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition font-medium"
					on:click={openCreate}
				>
					✨ {$i18n.t('Générer avec l’IA')}
				</button>
			</div>
			{/if}
		{/if}
	{/if}
</div>

<!-- Modale de création -->
<Modal bind:show={showCreate} size="md">
	<div class="p-5">
		<div class="text-base font-semibold mb-1">{$i18n.t('Créer une compétence')}</div>
		<div class="text-xs text-gray-500 mb-4">
			{$i18n.t('Décrivez le savoir-faire en clair. Vos agents pourront s’en servir.')}
		</div>

		<!-- ✨ Génération par l'IA : décris en une phrase, on remplit le formulaire pour toi -->
		<div
			class="rounded-2xl border border-violet-200/70 dark:border-violet-900/40 bg-gradient-to-br from-violet-50/80 to-indigo-50/60 dark:from-violet-950/30 dark:to-indigo-950/20 p-3.5 mb-5"
		>
			<div class="text-xs font-medium text-violet-900 dark:text-violet-200 mb-2">
				✨ {$i18n.t('Générer avec l’IA')}
			</div>
			<textarea
				class="w-full text-sm bg-white/70 dark:bg-gray-900/50 border border-violet-100 dark:border-violet-900/40 rounded-xl px-3 py-2 outline-none min-h-16 resize-y"
				placeholder={$i18n.t('Décris la compétence en une phrase. Ex. : relancer les devis sans réponse après 7 jours, poliment.')}
				bind:value={genBrief}
				disabled={generating}
			></textarea>
			{#if genError}
				<div class="text-xs text-red-500 mt-1">{genError}</div>
			{/if}
			<div class="flex justify-end mt-2">
				<button
					class="text-xs px-3 py-1.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 transition font-medium disabled:opacity-50 flex items-center gap-1.5"
					on:click={doGenerate}
					disabled={generating}
				>
					{#if generating}
						<Spinner className="size-3.5" />
						{$i18n.t('Génération…')}
					{:else}
						✨ {$i18n.t('Générer')}
					{/if}
				</button>
			</div>
			<div class="text-[11px] text-gray-500 dark:text-gray-400 mt-1.5">
				{$i18n.t('L’IA remplit les champs ci-dessous. Vous pouvez tout relire et ajuster avant de créer.')}
			</div>
		</div>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Nom')}
		</label>
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Ex. : Relance de devis')}
			bind:value={formLabel}
		/>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('À quoi ça sert')}
		</label>
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Ex. : Relancer les devis restés sans réponse, poliment.')}
			bind:value={formDescription}
		/>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Catégorie')}
		</label>
		<select
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			bind:value={formCategory}
		>
			{#each SKILL_CATEGORIES as cat}
				<option value={cat}>{cat}</option>
			{/each}
		</select>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Comment faire (la procédure)')}
		</label>
		<textarea
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-4 min-h-32 resize-y"
			placeholder={$i18n.t('Décrivez les étapes, le ton, les règles à respecter…')}
			bind:value={formInstructions}
		></textarea>

		<div class="flex justify-end gap-2">
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => (showCreate = false)}
				disabled={saving}
			>
				{$i18n.t('Annuler')}
			</button>
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition font-medium disabled:opacity-50"
				on:click={submitCreate}
				disabled={saving}
			>
				{saving ? $i18n.t('Création…') : $i18n.t('Créer')}
			</button>
		</div>
	</div>
</Modal>

<!-- Modale de détail : le contenu complet de la compétence -->
<Modal bind:show={showDetail} size="lg">
	<div class="p-5">
		{#if detailLoading}
			<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
		{:else if detail}
			<div class="flex items-start justify-between gap-3 mb-1">
				<div class="text-lg font-semibold">{detail.label}</div>
				<span
					class="flex-none text-[11px] px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
				>
					{detail.category}
				</span>
			</div>
			{#if detail.description}
				<div class="text-xs text-gray-500 mb-4">{detail.description}</div>
			{/if}
			<div
				class="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap leading-relaxed border-t border-gray-100 dark:border-gray-850 pt-4 max-h-[55vh] overflow-y-auto"
			>{detail.instructions}</div>
			<div
				class="text-xs text-gray-500 mt-4 flex items-start gap-1.5 bg-gray-50 dark:bg-gray-850/60 rounded-xl px-3 py-2"
			>
				<span>💡</span>
				<span>
					{$i18n.t('Pour qu’un agent utilise cette compétence, attribuez-la dans sa fiche : Agents → Modifier → « Outils de cet agent ».')}
				</span>
			</div>
			<div class="flex justify-end gap-2 mt-4">
				<button
					class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => (showDetail = false)}
				>
					{$i18n.t('Fermer')}
				</button>
			</div>
		{/if}
	</div>
</Modal>

<!-- Modale d'import d'une skill existante -->
<Modal bind:show={showImport} size="md">
	<div class="p-5">
		<div class="text-base font-semibold mb-1">⬇ {$i18n.t('Importer une skill')}</div>
		<div class="text-xs text-gray-500 mb-4">
			{$i18n.t('Colle l’adresse d’une compétence trouvée sur GitHub. On la récupère et on la transforme automatiquement au niveau LunarIA (en français, branchée à tes outils, avec garde-fous).')}
		</div>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Adresse de la skill (GitHub)')}
		</label>
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-1"
			placeholder="https://github.com/.../skills/relance-impayes"
			bind:value={importUrl}
			disabled={importing}
		/>
		<div class="text-[11px] text-gray-400 mb-3">
			{$i18n.t('Lien vers le dossier de la skill ou directement son fichier SKILL.md.')}
		</div>

		{#if importError}
			<div class="text-xs text-red-500 mb-3">{importError}</div>
		{/if}

		<div class="flex justify-end gap-2">
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => (showImport = false)}
				disabled={importing}
			>
				{$i18n.t('Annuler')}
			</button>
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition font-medium disabled:opacity-50 flex items-center gap-1.5"
				on:click={doImport}
				disabled={importing}
			>
				{#if importing}
					<Spinner className="size-3.5" />
					{$i18n.t('Récupération + transformation…')}
				{:else}
					⬇ {$i18n.t('Récupérer et transformer')}
				{/if}
			</button>
		</div>
	</div>
</Modal>

<!-- Confirmation de suppression -->
<ConfirmDialog
	bind:show={showDelete}
	title={$i18n.t('Supprimer cette compétence ?')}
	message={toDelete
		? $i18n.t('« {{label}} » sera définitivement supprimée. Cette action est irréversible.', {
				label: toDelete.label
			})
		: ''}
	confirmLabel={$i18n.t('Supprimer')}
	cancelLabel={$i18n.t('Annuler')}
	on:confirm={confirmDelete}
/>
