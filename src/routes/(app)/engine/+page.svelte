<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import { mobile, showSidebar, user, WEBUI_NAME } from '$lib/stores';
	import { formatFileSize } from '$lib/utils';
	import {
		getHermesCapabilities,
		getHermesSkills,
		getHermesStatus,
		getHermesToolsets,
		type HermesCapabilities,
		type HermesStatus
	} from '$lib/apis/hermes';
	import {
		buildActivity,
		buildHealthRows,
		buildPlatformRows,
		deriveAlerts,
		groupCapabilities,
		listFrom
	} from '$lib/engine/health';

	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
	import AlertsBanner from '$lib/components/engine/AlertsBanner.svelte';
	import HealthCard from '$lib/components/engine/HealthCard.svelte';
	import PlatformsCard from '$lib/components/engine/PlatformsCard.svelte';
	import ActivityCard from '$lib/components/engine/ActivityCard.svelte';
	import ResourcesCard from '$lib/components/engine/ResourcesCard.svelte';
	import QuickActionsCard from '$lib/components/engine/QuickActionsCard.svelte';
	import TechnicalDetails from '$lib/components/engine/TechnicalDetails.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	let loaded = false;
	let loading = true;
	let lastChecked: Date | null = null;

	// `null` signifie « source non joignable », jamais « vide » : les compteurs affichent
	// alors un tiret plutôt qu'un zéro trompeur.
	let status: HermesStatus | null = null;
	let capabilities: HermesCapabilities | null = null;
	let skills: Record<string, unknown> | null = null;
	let toolsets: Record<string, unknown> | null = null;

	$: healthRows = buildHealthRows(status, formatFileSize);
	$: platforms = buildPlatformRows(status);
	$: alerts = deriveAlerts(status, healthRows, platforms);
	$: activity = buildActivity(status);
	$: capabilityGroups = groupCapabilities(capabilities?.features);
	$: skillItems = listFrom(skills, ['data', 'skills', 'items']);
	$: toolsetItems = listFrom(toolsets, ['data', 'toolsets', 'items']);
	$: configuredToolsets = toolsetItems.filter((item) => item.configured !== false);

	const loadStatus = async () => {
		try {
			status = await getHermesStatus(localStorage.token);
		} catch {
			// Le proxy répond 200 avec un état même quand Hermes est éteint : un échec ici
			// vient d'Open WebUI, pas du moteur.
			status = {
				configured: true,
				state: 'request_failed',
				version: null,
				model: null,
				active_agents: 0
			};
		}
	};

	const loadEngine = async () => {
		loading = true;

		// Chaque source est interrogée indépendamment : la panne de l'une n'empêche pas
		// les autres de s'afficher.
		await Promise.all([
			loadStatus(),
			getHermesCapabilities(localStorage.token)
				.then((value) => (capabilities = value))
				.catch(() => (capabilities = null)),
			getHermesSkills(localStorage.token)
				.then((value) => (skills = value))
				.catch(() => (skills = null)),
			getHermesToolsets(localStorage.token)
				.then((value) => (toolsets = value))
				.catch(() => (toolsets = null))
		]);

		lastChecked = new Date();
		loading = false;
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/', { replaceState: true });
			return;
		}

		loaded = true;
		await loadEngine();
	});
</script>

<svelte:head>
	<title>{$i18n.t('Engine')} / {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div
		class="flex h-dvh w-full min-w-0 flex-1 flex-col transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: 'md:max-w-[calc(100%-42px)]'}"
	>
		<nav class="drag-region select-none px-2.5 pb-1 pt-2">
			<div class="flex items-center">
				{#if $mobile}
					<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
						<button
							class="flex cursor-pointer rounded-lg transition hover:bg-gray-100 dark:hover:bg-gray-850"
							on:click={() => showSidebar.set(!$showSidebar)}
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						>
							<div class="p-1.5"><Sidebar className="size-4" /></div>
						</button>
					</Tooltip>
				{/if}
			</div>
		</nav>

		<main class="flex-1 overflow-y-auto px-3 pb-8">
			<div class="mx-auto flex w-full max-w-5xl flex-col gap-3 py-3 sm:py-6">
				<div class="px-1 pt-1">
					<PageHeader
						eyebrow={$i18n.t('Engine')}
						title={$i18n.t('Your engine at a glance')}
						description={$i18n.t(
							'The essentials of Hermes Agent and its current activity, gathered here.'
						)}
					>
						<button
							slot="actions"
							class="flex h-9 shrink-0 items-center justify-center rounded-xl border border-gray-100 px-3 text-sm text-gray-700 transition hover:bg-gray-50 disabled:cursor-wait disabled:opacity-60 dark:border-gray-850 dark:text-gray-200 dark:hover:bg-gray-850"
							on:click={loadEngine}
							disabled={loading}
						>
							{#if loading}<Spinner className="mr-2 size-3.5" />{/if}
							{$i18n.t('Refresh')}
						</button>
					</PageHeader>
				</div>

				<AlertsBanner {alerts} {loading} {lastChecked} />

				<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
					<HealthCard rows={healthRows} {loading} />
					<PlatformsCard {platforms} {loading} />
				</div>

				<ActivityCard counters={activity} busy={status?.gateway_busy ?? false} {loading} />

				<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
					<ResourcesCard
						model={status?.model ?? capabilities?.model ?? null}
						skillCount={skills ? skillItems.length : null}
						toolsetCount={toolsets ? configuredToolsets.length : null}
						{loading}
					/>
					<QuickActionsCard />
				</div>

				<TechnicalDetails
					groups={capabilityGroups}
					skills={skillItems}
					toolsets={toolsetItems}
					runtime={capabilities?.runtime ?? null}
				/>
			</div>
		</main>
	</div>
{/if}
