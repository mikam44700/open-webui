<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';

	import { getAgents, setActiveAgent, createAgent } from '$lib/apis/agents';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AgentCreate from './AgentCreate.svelte';
	import AgentEditor from './AgentEditor.svelte';
	import AgentAtelier from './AgentAtelier.svelte';
	import { AGENT_TEMPLATES } from './templates';
	import { gradientFor, initial, prettifyName } from './utils';

	const i18n = getContext('i18n');

	type Agent = {
		name: string;
		description?: string;
		model?: string | null;
		provider?: string | null;
		is_default?: boolean;
		skill_count?: number;
		gateway_running?: boolean;
		active?: boolean;
		avatar?: string | null; // mascotte illustrée (prioritaire sur l'initiale quand fournie)
	};

	let loading = true;
	let bridgeDown = false;
	let agents: Agent[] = [];

	let showCreate = false;
	let showAtelier = false;
	let showEditor = false;
	let editing: Agent | null = null;

	// Recherche dans la galerie « Prêts à l'emploi » (façon marketplace).
	let templateQuery = '';

	// Aperçu de la mission d'un template : ouvre une carte (modale) plutôt qu'un pavé déplié.
	let previewTemplate: (typeof AGENT_TEMPLATES)[number] | null = null;

	$: existingNames = new Set(agents.map((a) => a.name));
	$: availableTemplates = AGENT_TEMPLATES.filter((t) => !existingNames.has(t.id));
	$: filteredTemplates = availableTemplates.filter((t) => {
		const q = templateQuery.trim().toLowerCase();
		if (!q) return true;
		return `${t.label} ${t.description}`.toLowerCase().includes(q);
	});

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getAgents(localStorage.token);
			agents = res?.agents ?? [];
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des agents'));
			}
		} finally {
			loading = false;
		}
	};

	const activate = async (agent: Agent) => {
		try {
			await setActiveAgent(localStorage.token, agent.name);
			toast.success($i18n.t('{{name}} est prêt à discuter', { name: prettifyName(agent.name) }));
			goto('/');
		} catch {
			toast.error($i18n.t('Impossible d’activer cet agent'));
		}
	};

	const edit = (agent: Agent) => {
		editing = agent;
		showEditor = true;
	};

	const installTemplate = async (tpl: (typeof AGENT_TEMPLATES)[number]) => {
		try {
			await createAgent(localStorage.token, {
				name: tpl.label,
				description: tpl.description,
				soul: tpl.soul
			});
			toast.success($i18n.t('{{name}} ajouté', { name: tpl.label }));
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Cet agent existe déjà'));
			} else {
				toast.error($i18n.t('Impossible d’ajouter cet agent'));
			}
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-7xl mx-auto px-4 pt-5 pb-8">
		<!-- Action de création (le grand titre du hub est fourni par le layout « Espace de travail ») -->
		<div class="flex items-center justify-end gap-4 mb-6">
			<div class="flex-none flex flex-col items-end gap-1.5">
				<button
					class="text-sm font-medium px-4 py-2.5 rounded-xl bg-gradient-to-br from-gray-900 to-black text-white dark:from-white dark:to-gray-200 dark:text-black shadow-sm hover:shadow-md hover:-translate-y-px active:translate-y-0 transition-all flex items-center gap-1.5 whitespace-nowrap"
					on:click={() => (showAtelier = true)}
				>
					<span>✨</span>{$i18n.t('Créer un agent')}
				</button>
				<button
					class="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
					on:click={() => (showCreate = true)}
				>
					{$i18n.t('Mode manuel')}
				</button>
			</div>
		</div>

		{#if loading}
			<div class="flex justify-center py-24"><Spinner className="size-6" /></div>
		{:else if bridgeDown}
			<div
				class="flex flex-col items-center justify-center text-center py-20 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Le service Agents est injoignable')}</div>
				<div class="text-xs text-gray-500 max-w-md">
					{$i18n.t('Le pont vers Hermes ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
				</div>
				<button
					class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={load}
				>
					{$i18n.t('Réessayer')}
				</button>
			</div>
		{:else}
			<!-- Mes agents -->
			<section class="mb-11">
				<div class="flex items-baseline gap-2 mb-4">
					<h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
						{$i18n.t('Mes agents')}
					</h2>
					<span class="text-xs font-normal text-gray-400">{agents.length}</span>
				</div>

				{#if agents.length === 0}
					<div
						class="flex flex-col items-center justify-center text-center py-12 px-6 gap-2 rounded-3xl border border-dashed border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/30"
					>
						<div class="text-2xl">🪄</div>
						<div class="text-sm font-medium">{$i18n.t('Aucun agent pour l’instant')}</div>
						<div class="text-xs text-gray-500 max-w-xs">
							{$i18n.t('Créez le vôtre en une phrase, ou activez un modèle prêt à l’emploi ci-dessous.')}
						</div>
					</div>
				{:else}
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
						{#each agents as agent, i (agent.name)}
							<div
								in:fly={{ y: 10, duration: 260, delay: i * 35 }}
								class="group relative flex flex-col rounded-2xl p-4 bg-white dark:bg-gray-900 border transition-all duration-200 hover:-translate-y-0.5 {agent.active
									? 'border-green-400/50 shadow-[0_10px_34px_-14px_rgba(16,185,129,0.5)] bg-gradient-to-b from-green-50/50 to-transparent dark:from-green-500/[0.07]'
									: 'border-gray-100 dark:border-gray-800 shadow-[0_2px_14px_-8px_rgba(0,0,0,0.15)] hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-[0_14px_34px_-16px_rgba(0,0,0,0.25)]'}"
							>
								<button
									class="absolute top-4 right-4 text-gray-300 hover:text-gray-700 dark:text-gray-600 dark:hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100 transition"
									title={$i18n.t('Modifier')}
									on:click={() => edit(agent)}
									aria-label={$i18n.t('Modifier')}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
										<path
											d="M2.695 14.762l-1.262 3.155a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.886L17.5 5.501a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"
										/>
									</svg>
								</button>

								<div class="flex items-center gap-3.5">
									<div class="relative flex-none">
										{#if agent.avatar}
											<img
												src={agent.avatar}
												alt={prettifyName(agent.name)}
												class="size-11 rounded-2xl object-cover shadow-sm ring-1 ring-black/5 {agent.active
													? 'ring-2 ring-green-400/70 ring-offset-2 ring-offset-white dark:ring-offset-gray-900'
													: ''}"
											/>
										{:else}
											<div
												class="size-11 rounded-2xl flex items-center justify-center text-white text-lg font-semibold shadow-sm ring-1 ring-black/5 {agent.active
													? 'ring-2 ring-green-400/70 ring-offset-2 ring-offset-white dark:ring-offset-gray-900'
													: ''}"
												style="background-image: {gradientFor(agent.name)}"
											>
												{initial(prettifyName(agent.name))}
											</div>
										{/if}
										{#if agent.active}
											<span
												class="absolute -bottom-1 -right-1 size-3.5 rounded-full bg-green-500 border-2 border-white dark:border-gray-900"
											></span>
										{/if}
									</div>
									<div class="min-w-0 pr-6">
										<div class="text-[15px] font-semibold truncate">{prettifyName(agent.name)}</div>
										<div class="text-xs truncate mt-0.5 text-gray-400">
											{#if agent.model}{agent.model}{/if}{#if agent.active}{#if agent.model}
													&nbsp;·&nbsp;{/if}<span class="text-green-600 dark:text-green-400 font-medium"
													>{$i18n.t('Actif')}</span
												>{/if}
										</div>
									</div>
								</div>

								<p
									class="text-[13px] leading-relaxed text-gray-500 dark:text-gray-400 mt-4 line-clamp-2 min-h-[2.5rem]"
								>
									{agent.description || $i18n.t('Aucune mission définie pour le moment.')}
								</p>

								<button
									class="mt-4 w-full text-sm font-medium px-3 py-2.5 rounded-xl transition-all {agent.active
										? 'bg-gray-900 text-white dark:bg-white dark:text-black hover:opacity-90'
										: 'bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-800'}"
									on:click={() => activate(agent)}
								>
									{agent.active ? $i18n.t('Continuer') + ' →' : $i18n.t('Discuter')}
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Prêts à l'emploi (templates) -->
			{#if availableTemplates.length > 0}
				<section>
					<div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
						<div>
							<h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
								{$i18n.t('Prêts à l’emploi')}
							</h2>
							<p class="text-xs text-gray-500 mt-0.5">
								{$i18n.t('Des agents préconfigurés par métier — activez-les en un clic.')}
							</p>
						</div>
						<div class="relative w-full sm:w-64">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
								/>
							</svg>
							<input
								bind:value={templateQuery}
								type="text"
								placeholder={$i18n.t('Rechercher un métier…')}
								class="w-full text-sm pl-9 pr-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 focus:border-gray-300 dark:focus:border-gray-600 focus:ring-2 focus:ring-gray-100 dark:focus:ring-gray-800 outline-none transition placeholder:text-gray-400"
							/>
						</div>
					</div>

					{#if filteredTemplates.length === 0}
						<div class="text-sm text-gray-400 text-center py-12 border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl">
							{$i18n.t('Aucun agent ne correspond à votre recherche.')}
						</div>
					{:else}
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
							{#each filteredTemplates as tpl, i (tpl.id)}
								<div
									in:fly={{ y: 10, duration: 240, delay: Math.min(i, 8) * 30 }}
									class="group flex flex-col rounded-2xl p-4 bg-gray-50/60 dark:bg-gray-900/40 border border-gray-100 dark:border-gray-800 hover:bg-white dark:hover:bg-gray-900 hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-[0_14px_34px_-16px_rgba(0,0,0,0.22)] hover:-translate-y-0.5 transition-all duration-200"
								>
									<div class="flex items-center gap-3.5">
										{#if tpl.image}
											<img
												src={tpl.image}
												alt={tpl.label}
												class="flex-none size-11 rounded-2xl object-cover shadow-sm ring-1 ring-black/5 group-hover:scale-105 transition-transform"
											/>
										{:else}
											<div
												class="flex-none size-11 rounded-2xl flex items-center justify-center text-2xl bg-white dark:bg-gray-850 shadow-sm ring-1 ring-black/5 group-hover:scale-105 transition-transform"
											>
												{tpl.emoji}
											</div>
										{/if}
										<div class="min-w-0">
											<div class="text-[15px] font-semibold truncate">{tpl.label}</div>
										</div>
									</div>
									<p
										class="text-[13px] leading-relaxed text-gray-500 dark:text-gray-400 mt-4 line-clamp-2 min-h-[2.5rem]"
									>
										{tpl.description}
									</p>

									<button
										class="mt-2 self-start text-[11px] font-medium text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
										on:click={() => (previewTemplate = tpl)}
									>
										{$i18n.t('Voir la mission')}
									</button>

									<button
										class="mt-4 w-full text-sm font-medium px-3 py-2.5 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-black hover:opacity-90 hover:shadow-md transition-all"
										on:click={() => installTemplate(tpl)}
									>
										{$i18n.t('+ Activer')}
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</section>
			{/if}
		{/if}
</div>

<!-- Carte « mission » (modale) — aperçu du SOUL avant activation -->
{#if previewTemplate}
	<svelte:window on:keydown={(e) => e.key === 'Escape' && (previewTemplate = null)} />
	<div
		class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
		on:click|self={() => (previewTemplate = null)}
		transition:fade={{ duration: 150 }}
		role="presentation"
	>
		<div
			class="relative w-full max-w-lg max-h-[85vh] flex flex-col rounded-3xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-100 dark:border-gray-800"
			in:fly={{ y: 12, duration: 200 }}
			role="dialog"
			aria-modal="true"
		>
			<!-- En-tête -->
			<div class="flex items-center gap-3.5 p-5 border-b border-gray-100 dark:border-gray-800">
				{#if previewTemplate.image}
					<img
						src={previewTemplate.image}
						alt={previewTemplate.label}
						class="flex-none size-11 rounded-2xl object-cover shadow-sm ring-1 ring-black/5"
					/>
				{:else}
					<div
						class="flex-none size-11 rounded-2xl flex items-center justify-center text-2xl bg-gray-50 dark:bg-gray-850 shadow-sm ring-1 ring-black/5"
					>
						{previewTemplate.emoji}
					</div>
				{/if}
				<div class="min-w-0 flex-1">
					<div class="text-base font-semibold truncate">{previewTemplate.label}</div>
					<div class="text-xs text-gray-500 line-clamp-1">{previewTemplate.description}</div>
				</div>
				<button
					class="flex-none p-1.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (previewTemplate = null)}
					aria-label={$i18n.t('Fermer')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
						<path
							d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
						/>
					</svg>
				</button>
			</div>

			<!-- Corps : la mission (SOUL), défilable -->
			<div
				class="flex-1 overflow-y-auto px-5 py-4 text-[13px] leading-relaxed text-gray-600 dark:text-gray-300 whitespace-pre-line"
			>
				{previewTemplate.soul}
			</div>

			<!-- Pied : activer -->
			<div class="p-4 border-t border-gray-100 dark:border-gray-800">
				<button
					class="w-full text-sm font-medium px-3 py-2.5 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-black hover:opacity-90 hover:shadow-md transition-all"
					on:click={() => {
						const t = previewTemplate;
						previewTemplate = null;
						if (t) installTemplate(t);
					}}
				>
					{$i18n.t('+ Activer')}
				</button>
			</div>
		</div>
	</div>
{/if}

<AgentAtelier bind:show={showAtelier} on:created={load} />
<AgentCreate bind:show={showCreate} on:created={load} />
<AgentEditor bind:show={showEditor} agent={editing} on:updated={load} on:deleted={load} />
