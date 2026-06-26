<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getBriefing, publishBriefing, type Briefing } from '$lib/apis/briefing-hermes';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let unavailable = false;
	let briefing: Briefing | null = null;
	let publishing = false;

	const publish = async () => {
		publishing = true;
		try {
			await publishBriefing(localStorage.token);
			toast.success($i18n.t('Briefing publié dans le canal Agent OS'));
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Publication impossible'));
		} finally {
			publishing = false;
		}
	};

	const load = async () => {
		loading = true;
		unavailable = false;
		try {
			briefing = await getBriefing(localStorage.token);
		} catch (err) {
			unavailable = true;
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

<div class="rounded-3xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-gray-900">
	<div class="flex items-center justify-between mb-3">
		<div class="flex items-center gap-2">
			<span class="text-lg">☀️</span>
			<div>
				<div class="text-sm font-medium">{$i18n.t('Votre briefing du jour')}</div>
				{#if briefing}
					<div class="text-xs text-gray-400">{briefing.date_label}</div>
				{/if}
			</div>
		</div>
		<div class="flex items-center gap-2">
			{#if briefing && !unavailable}
				<button
					class="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 disabled:opacity-50"
					disabled={publishing}
					on:click={publish}
				>
					{$i18n.t('Publier dans Agent OS')}
				</button>
			{/if}
			<button class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-white" on:click={load} aria-label="Rafraîchir">↻</button>
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center py-8"><Spinner className="size-4" /></div>
	{:else if unavailable || !briefing}
		<div class="text-xs text-gray-500 py-4 text-center">
			{$i18n.t('Briefing momentanément indisponible.')}
			<button class="underline ml-1" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		<div class="flex flex-col gap-3 text-sm">
			<!-- Agenda -->
			<div>
				<div class="text-xs font-medium text-gray-500 mb-1">🗓️ {$i18n.t('Agenda du jour')}</div>
				{#if briefing.events_status === 'ok'}
					{#if briefing.events.length}
						{#each briefing.events.slice(0, 5) as e}
							<div class="text-xs flex gap-2">
								<span class="text-gray-400 shrink-0">{e.when_label}</span>
								<span class="truncate">{e.title}{e.location ? ` — ${e.location}` : ''}</span>
							</div>
						{/each}
					{:else}
						<div class="text-xs text-gray-400">{$i18n.t('Rien de prévu aujourd’hui.')}</div>
					{/if}
				{:else if briefing.events_status === 'not_connected'}
					<button class="text-xs text-amber-600 dark:text-amber-400 underline" on:click={() => goto('/connectors')}>
						{$i18n.t('Connectez Google Agenda dans Intégrations')}
					</button>
				{:else}
					<div class="text-xs text-gray-400">{$i18n.t('Agenda momentanément indisponible.')}</div>
				{/if}
			</div>

			<!-- Tâches -->
			<div>
				<div class="text-xs font-medium text-gray-500 mb-1">✅ {$i18n.t('Tâches en cours')}</div>
				{#if briefing.tasks_status === 'ok'}
					{#if briefing.tasks.length}
						{#each briefing.tasks.slice(0, 5) as t}
							<div class="text-xs truncate">• {t.title}</div>
						{/each}
					{:else}
						<div class="text-xs text-gray-400">{$i18n.t('Aucune tâche en cours.')}</div>
					{/if}
				{:else}
					<div class="text-xs text-gray-400">{$i18n.t('Tâches momentanément indisponibles.')}</div>
				{/if}
			</div>

			<!-- Automatisations -->
			<div>
				<div class="text-xs font-medium text-gray-500 mb-1">⚡ {$i18n.t('Automatisations')}</div>
				{#if briefing.automations_status === 'ok'}
					<div class="text-xs text-gray-400">
						{briefing.automations.length}
						{briefing.automations.length > 1 ? $i18n.t('actives') : $i18n.t('active')}
					</div>
				{:else}
					<div class="text-xs text-gray-400">{$i18n.t('Momentanément indisponibles.')}</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
