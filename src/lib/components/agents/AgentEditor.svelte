<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		getAgentSoul,
		updateAgentSoul,
		updateAgentDescription,
		deleteAgent,
		getAgentTools,
		setAgentSkill,
		setAgentMcp
	} from '$lib/apis/agents';
	import { getCustomSkills } from '$lib/apis/capabilities';
	import { colorFor, initial, prettifyName } from './utils';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let agent: {
		name: string;
		description?: string;
		model?: string | null;
		is_default?: boolean;
		active?: boolean;
	} | null = null;

	let loading = false;
	let soul = '';
	let description = '';
	let savedFlag = false;
	let confirmDelete = false;
	let loadedFor = '';
	let soulTimer: ReturnType<typeof setTimeout>;
	let descTimer: ReturnType<typeof setTimeout>;

	// Outils PAR AGENT (compétences + MCP), avec leur état pour cet agent.
	type Tool = {
		name: string;
		enabled: boolean;
		description?: string;
		category?: string;
		label?: string;
		isMaison?: boolean;
	};
	let toolsLoading = false;
	let skills: Tool[] = [];
	let mcps: Tool[] = [];
	let toolQuery = '';

	$: filteredSkills = toolQuery.trim()
		? skills.filter((s) =>
				`${s.label ?? ''} ${s.name} ${s.description ?? ''}`
					.toLowerCase()
					.includes(toolQuery.toLowerCase())
			)
		: skills;

	const loadTools = async () => {
		if (!agent) return;
		toolsLoading = true;
		try {
			// On charge en parallèle les outils de l'agent ET nos compétences maison
			// (pour afficher leur libellé lisible plutôt que l'identifiant technique).
			const [res, customRes] = await Promise.all([
				getAgentTools(localStorage.token, agent.name),
				getCustomSkills(localStorage.token).catch(() => ({ skills: [] }))
			]);
			const maison = new Map(
				(customRes?.skills ?? []).map((c: any) => [c.name, c])
			);
			skills = (res?.skills ?? [])
				.map((s) => {
					const custom: any = maison.get(s.name);
					return {
						name: s.name,
						enabled: s.enabled,
						description: custom?.description ?? s.description,
						category: custom?.category ?? s.category,
						isMaison: !!custom,
						label: custom ? custom.label : prettifyName(s.name)
					};
				})
				// Compétences maison (les vôtres) d'abord, puis le reste, par libellé.
				.sort((a, b) => {
					if (a.isMaison !== b.isMaison) return a.isMaison ? -1 : 1;
					return (a.label ?? a.name).localeCompare(b.label ?? b.name);
				});
			mcps = (res?.mcps ?? []).map((m) => ({ name: m.id, enabled: m.enabled }));
		} catch {
			skills = [];
			mcps = [];
		}
		toolsLoading = false;
	};

	const toggleSkill = async (s: Tool) => {
		if (!agent) return;
		const next = !s.enabled;
		s.enabled = next;
		skills = skills; // maj optimiste
		try {
			await setAgentSkill(localStorage.token, agent.name, s.name, next);
		} catch {
			s.enabled = !next;
			skills = skills;
			toast.error($i18n.t('Échec de la mise à jour'));
		}
	};

	const toggleMcp = async (m: Tool) => {
		if (!agent) return;
		const next = !m.enabled;
		m.enabled = next;
		mcps = mcps;
		try {
			await setAgentMcp(localStorage.token, agent.name, m.name, next);
		} catch {
			m.enabled = !next;
			mcps = mcps;
			toast.error($i18n.t('Échec de la mise à jour'));
		}
	};

	const inputClass =
		'w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none';

	const load = async () => {
		if (!agent || loadedFor === agent.name) return;
		loadedFor = agent.name;
		loading = true;
		description = agent.description ?? '';
		try {
			const res = await getAgentSoul(localStorage.token, agent.name);
			soul = res?.content ?? '';
		} catch {
			soul = '';
		}
		loading = false;
		loadTools();
	};

	$: if (show && agent) load();
	$: if (!show) {
		loadedFor = '';
		confirmDelete = false;
	}

	const flashSaved = () => {
		savedFlag = true;
		setTimeout(() => (savedFlag = false), 1500);
	};

	const onSoul = () => {
		clearTimeout(soulTimer);
		soulTimer = setTimeout(async () => {
			if (!agent) return;
			try {
				await updateAgentSoul(localStorage.token, agent.name, soul);
				flashSaved();
				dispatch('updated');
			} catch {
				toast.error($i18n.t('Échec de l’enregistrement'));
			}
		}, 600);
	};

	const onDesc = () => {
		clearTimeout(descTimer);
		descTimer = setTimeout(async () => {
			if (!agent) return;
			try {
				await updateAgentDescription(localStorage.token, agent.name, description);
				flashSaved();
				dispatch('updated');
			} catch {
				toast.error($i18n.t('Échec de l’enregistrement'));
			}
		}, 600);
	};

	const remove = async () => {
		if (!agent) return;
		try {
			await deleteAgent(localStorage.token, agent.name);
			toast.success($i18n.t('Agent supprimé'));
			show = false;
			confirmDelete = false;
			loadedFor = '';
			dispatch('deleted');
		} catch (err) {
			if (err?.error?.code === 'default') {
				toast.error($i18n.t('L’agent par défaut ne peut pas être supprimé'));
			} else {
				toast.error($i18n.t('Impossible de supprimer cet agent'));
			}
		}
	};
</script>

<Modal bind:show size="lg">
	{#if agent}
		<div class="p-5">
			<div class="flex items-center justify-between mb-5">
				<div class="flex items-center gap-3 min-w-0">
					<div
						class="flex-none size-11 rounded-2xl flex items-center justify-center text-white text-lg font-semibold"
						style="background-color: {colorFor(agent.name)}"
					>
						{initial(prettifyName(agent.name))}
					</div>
					<div class="min-w-0">
						<div class="text-lg font-medium truncate">{prettifyName(agent.name)}</div>
						{#if agent.model}
							<div class="text-[11px] text-gray-400 truncate">{agent.model}</div>
						{/if}
					</div>
				</div>
				<button
					class="text-gray-400 hover:text-gray-700 dark:hover:text-white"
					on:click={() => (show = false)}>✕</button
				>
			</div>

			{#if loading}
				<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
			{:else}
				<div class="space-y-4">
					<div>
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('En une phrase, à quoi sert-il ?')}</div>
						<input
							bind:value={description}
							on:input={onDesc}
							placeholder={$i18n.t('Ex : Gère les congés et les contrats')}
							class={inputClass}
						/>
					</div>

					<div>
						<div class="flex items-center justify-between mb-1">
							<div class="text-xs text-gray-500">{$i18n.t('Sa mission — que doit-il faire ?')}</div>
							{#if savedFlag}
								<div class="text-[11px] text-green-600 dark:text-green-400">
									{$i18n.t('Enregistré ✓')}
								</div>
							{/if}
						</div>
						<textarea
							bind:value={soul}
							on:input={onSoul}
							rows="10"
							placeholder={$i18n.t('Décris en langage normal ce qu’il doit faire, son ton, ses règles…')}
							class="{inputClass} resize-none leading-relaxed"
						></textarea>
						<div class="text-[11px] text-gray-400 mt-1">
							{$i18n.t('Enregistrement automatique. Cette mission guide l’agent à chaque conversation.')}
						</div>
					</div>

					<div class="border-t border-gray-100 dark:border-gray-850 pt-4">
						<div class="text-xs text-gray-500 mb-0.5">{$i18n.t('Outils de cet agent')}</div>
						<div class="text-[11px] text-gray-400 mb-2">
							{$i18n.t('Ce que cet agent a le droit d’utiliser. Décochez pour le restreindre.')}
						</div>
						{#if toolsLoading}
							<div class="flex justify-center py-6"><Spinner className="size-4" /></div>
						{:else}
							{#if mcps.length}
								<div class="text-[11px] font-medium text-gray-500 mb-1">
									{$i18n.t('Connecteurs MCP')}
								</div>
								<div class="space-y-0.5 mb-3">
									{#each mcps as m}
										<label
											class="flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 cursor-pointer"
										>
											<span class="text-sm truncate">{m.name}</span>
											<input
												type="checkbox"
												class="accent-black dark:accent-white size-4 shrink-0"
												checked={m.enabled}
												on:change={() => toggleMcp(m)}
											/>
										</label>
									{/each}
								</div>
							{/if}

							<div class="flex items-center justify-between gap-2 mb-1">
								<div class="text-[11px] font-medium text-gray-500">
									{$i18n.t('Compétences')}
									<span class="text-gray-400">
										({skills.filter((s) => s.enabled).length}/{skills.length})
									</span>
								</div>
							</div>
							{#if skills.length > 8}
								<input
									bind:value={toolQuery}
									placeholder={$i18n.t('Filtrer les compétences…')}
									class="{inputClass} mb-1"
								/>
							{/if}
							<div class="max-h-56 overflow-y-auto space-y-0.5 pr-1">
								{#each filteredSkills as s}
									<label
										class="flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 cursor-pointer"
									>
										<span class="text-sm truncate flex items-center gap-1.5" title={s.description ?? ''}>
											{#if s.isMaison}<span class="text-[10px]" title={$i18n.t('Compétence maison')}>✨</span>{/if}
											{s.label ?? s.name}
										</span>
										<input
											type="checkbox"
											class="accent-black dark:accent-white size-4 shrink-0"
											checked={s.enabled}
											on:change={() => toggleSkill(s)}
										/>
									</label>
								{/each}
								{#if filteredSkills.length === 0}
									<div class="text-xs text-gray-400 py-3 text-center">
										{$i18n.t('Aucune compétence à afficher.')}
									</div>
								{/if}
							</div>
						{/if}
					</div>

					{#if !agent.is_default}
						<div class="border-t border-gray-100 dark:border-gray-850 pt-4">
							{#if !confirmDelete}
								<button
									class="text-xs text-red-600 dark:text-red-400 hover:underline"
									on:click={() => (confirmDelete = true)}
								>
									{$i18n.t('Supprimer cet agent')}
								</button>
							{:else}
								<div class="flex items-center gap-2">
									<span class="text-xs text-gray-600 dark:text-gray-300"
										>{$i18n.t('Confirmer la suppression ?')}</span
									>
									<button
										class="text-xs px-3 py-1.5 rounded-xl bg-red-600 text-white hover:bg-red-700 transition"
										on:click={remove}>{$i18n.t('Supprimer')}</button
									>
									<button
										class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
										on:click={() => (confirmDelete = false)}>{$i18n.t('Annuler')}</button
									>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</Modal>
