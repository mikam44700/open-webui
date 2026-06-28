<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { getAgents, setActiveAgent, createAgent } from '$lib/apis/agents';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AgentCreate from './AgentCreate.svelte';
	import AgentEditor from './AgentEditor.svelte';
	import AgentAtelier from './AgentAtelier.svelte';
	import { AGENT_TEMPLATES } from './templates';
	import { colorFor, initial, prettifyName } from './utils';

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
	};

	let loading = true;
	let bridgeDown = false;
	let agents: Agent[] = [];

	let showCreate = false;
	let showAtelier = false;
	let showEditor = false;
	let editing: Agent | null = null;

	// Aperçu de la mission d'un template avant activation (déplie le soul complet).
	let expandedTemplate: string | null = null;
	const toggleTemplate = (id: string) => {
		expandedTemplate = expandedTemplate === id ? null : id;
	};

	$: existingNames = new Set(agents.map((a) => a.name));
	$: availableTemplates = AGENT_TEMPLATES.filter((t) => !existingNames.has(t.id));

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

<div class="w-full max-w-5xl mx-auto px-3 py-3">
	<div class="flex items-start justify-between gap-3 mb-5">
		<div>
			<div class="text-xl font-medium">{$i18n.t('Agents')}</div>
			<div class="text-sm text-gray-600 dark:text-gray-400">
				{$i18n.t('Vos collègues numériques, prêts à travailler.')}
			</div>
		</div>
		<div class="flex-none flex flex-col items-end gap-1">
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
				on:click={() => (showAtelier = true)}
			>
				✨ {$i18n.t('Créer un agent')}
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
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
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
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
			{#each agents as agent (agent.name)}
				<div
					class="relative flex flex-col rounded-2xl px-4 py-4 border transition {agent.active
						? 'border-green-500/60 shadow-[0_0_0_1px_rgba(34,197,94,0.25)]'
						: 'border-gray-100 dark:border-gray-850 hover:border-gray-200 dark:hover:border-gray-800'}"
				>
					<button
						class="absolute top-3 right-3 text-gray-300 hover:text-gray-700 dark:hover:text-white transition"
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

					{#if agent.active}
						<div
							class="absolute top-3 right-10 flex items-center gap-1 text-[11px] text-green-600 dark:text-green-400"
						>
							<span class="size-2 rounded-full bg-green-500"></span>{$i18n.t('Actif')}
						</div>
					{/if}

					<div class="flex items-center gap-3">
						<div
							class="flex-none size-11 rounded-2xl flex items-center justify-center text-white text-lg font-semibold"
							style="background-color: {colorFor(agent.name)}"
						>
							{initial(prettifyName(agent.name))}
						</div>
						<div class="min-w-0">
							<div class="text-sm font-medium truncate">{prettifyName(agent.name)}</div>
							{#if agent.model}
								<div class="text-[11px] text-gray-400 truncate">{agent.model}</div>
							{/if}
						</div>
					</div>

					<div class="text-xs text-gray-500 mt-3 line-clamp-2 min-h-[2rem]">
						{agent.description || $i18n.t('Aucune mission définie pour le moment.')}
					</div>

					<div class="mt-3">
						<button
							class="w-full text-sm px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={() => activate(agent)}
						>
							{agent.active ? $i18n.t('Continuer') : $i18n.t('Discuter')}
						</button>
					</div>
				</div>
			{/each}
		</div>

		<!-- Prêts à l'emploi (templates) -->
		{#if availableTemplates.length > 0}
			<div class="mt-8 mb-3">
				<div class="text-sm font-medium">{$i18n.t('Prêts à l’emploi')}</div>
				<div class="text-xs text-gray-500">
					{$i18n.t('Des agents préconfigurés par métier — activez-les en un clic.')}
				</div>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each availableTemplates as tpl (tpl.id)}
					<div class="flex flex-col rounded-2xl px-4 py-4 border border-dashed border-gray-200 dark:border-gray-800">
						<div class="flex items-center gap-3">
							<div class="flex-none size-11 rounded-2xl flex items-center justify-center text-xl bg-gray-50 dark:bg-gray-850">
								{tpl.emoji}
							</div>
							<div class="min-w-0">
								<div class="text-sm font-medium truncate">{tpl.label}</div>
							</div>
						</div>
						<div
							class="text-xs text-gray-500 mt-3 {expandedTemplate === tpl.id
								? ''
								: 'line-clamp-2 min-h-[2rem]'}"
						>
							{tpl.description}
						</div>

						{#if expandedTemplate === tpl.id}
							<div
								class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-300 whitespace-pre-line"
							>
								{tpl.soul}
							</div>
						{/if}

						<button
							class="mt-2 self-start text-[11px] text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
							on:click={() => toggleTemplate(tpl.id)}
							aria-expanded={expandedTemplate === tpl.id}
						>
							{expandedTemplate === tpl.id
								? $i18n.t('Masquer la mission')
								: $i18n.t('Voir la mission')}
						</button>

						<div class="mt-3">
							<button
								class="w-full text-sm px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => installTemplate(tpl)}
							>
								{$i18n.t('+ Activer')}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<AgentAtelier bind:show={showAtelier} on:created={load} />
<AgentCreate bind:show={showCreate} on:created={load} />
<AgentEditor bind:show={showEditor} agent={editing} on:updated={load} on:deleted={load} />
