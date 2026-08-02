<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { mobile, showSidebar, user, WEBUI_NAME } from '$lib/stores';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import {
		getHermesCapabilities,
		getHermesSkills,
		getHermesStatus,
		getHermesToolsets,
		type HermesCapabilities,
		type HermesStatus
	} from '$lib/apis/hermes';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import EngineIcon from '$lib/components/layout/Sidebar/icons/Engine.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	type DisplayState = 'ok' | 'warning' | 'down' | 'unknown';
	/** `overall` marks the engine itself, as opposed to one of its components. */
	type HealthRow = { label: string; state: DisplayState; detail?: string; overall?: boolean };
	type EngineIssue = { title: string; description: string; hint?: string };
	type ReadinessCheck = {
		status?: string;
		state?: string;
		active_api_runs?: number;
		active_delegations?: number;
		process_completions?: number;
	};

	let loaded = false;
	let loading = true;
	let status: HermesStatus | null = null;
	let capabilities: HermesCapabilities | null = null;
	let skills: Record<string, unknown> | null = null;
	let toolsets: Record<string, unknown> | null = null;
	let lastChecked: Date | null = null;
	let engineDisplayState: DisplayState = 'unknown';
	let healthRows: HealthRow[] = [];

	const listFrom = (value: Record<string, unknown> | null, keys: string[]) => {
		if (!value) return [];
		for (const key of keys) {
			if (Array.isArray(value[key])) return value[key] as Record<string, unknown>[];
		}
		return [];
	};

	const checkState = (check?: ReadinessCheck): DisplayState => {
		const value = String(check?.status ?? check?.state ?? '').toLowerCase();
		if (['ok', 'ready', 'healthy', 'running', 'connected'].includes(value)) return 'ok';
		if (['warning', 'degraded', 'busy'].includes(value)) return 'warning';
		if (['error', 'failed', 'down', 'stopped', 'disconnected'].includes(value)) return 'down';
		return 'unknown';
	};

	const displayMeta = (state: DisplayState) => {
		switch (state) {
			case 'ok':
				return {
					label: $i18n.t('Operational'),
					dot: 'bg-emerald-500',
					text: 'text-emerald-700 dark:text-emerald-300'
				};
			case 'warning':
				return {
					label: $i18n.t('Needs attention'),
					dot: 'bg-amber-500',
					text: 'text-amber-700 dark:text-amber-300'
				};
			case 'down':
				return {
					label: $i18n.t('Unavailable'),
					dot: 'bg-red-500',
					text: 'text-red-700 dark:text-red-300'
				};
			default:
				return {
					label: $i18n.t('Unknown'),
					dot: 'bg-gray-400',
					text: 'text-gray-500 dark:text-gray-400'
				};
		}
	};

	const itemLabel = (item: Record<string, unknown>) =>
		String(item.label ?? item.name ?? item.id ?? $i18n.t('Unknown'));

	/** Turn the state reported by the backend into an actionable message. */
	const describeIssue = (
		state: string | undefined,
		components: string[],
		i18nInstance: I18nType
	): EngineIssue => {
		const t = (key: string, options?: Record<string, unknown>) => i18nInstance.t(key, options);

		switch (state) {
			case 'not_configured':
				return {
					title: t('Hermes Agent is not configured'),
					description: t('Open WebUI does not know where to reach the engine yet.'),
					hint: t('Set HERMES_API_URL on the server, then restart Open WebUI.')
				};
			case 'authentication_failed':
				return {
					title: t('Hermes Agent refused the credentials'),
					description: t('The engine answered, but rejected the configured API key.'),
					hint: t('Check HERMES_API_KEY, or the key stored in the Hermes configuration file.')
				};
			case 'unavailable':
				return {
					title: t('Hermes Agent is unreachable'),
					description: t('The engine did not answer. It may be stopped, or the address may be wrong.'),
					hint: t('Make sure Hermes Agent is running and that HERMES_API_URL points to it.')
				};
			case 'upstream_error':
			case 'invalid_response':
				return {
					title: t('Hermes Agent returned an unexpected response'),
					description: t('The engine answered, but Open WebUI could not read the result.'),
					hint: t('Check the Hermes Agent logs and confirm both versions are compatible.')
				};
			case 'request_failed':
				return {
					title: t('Engine status could not be retrieved'),
					description: t('Open WebUI could not complete the request. Your session may have expired.'),
					hint: t('Reload the page, then sign in again if the problem persists.')
				};
			case 'degraded':
				return {
					title: t('Hermes Agent is degraded'),
					description: components.length
						? t('Affected components: {{components}}', { components: components.join(', ') })
						: t('The engine is running, but at least one component is not healthy.'),
					hint: t('Open the technical details below to identify the cause.')
				};
			default:
				return {
					title: t('Hermes Agent needs attention'),
					description: t(
						'Hermes Agent needs attention. Check the service connection and try again.'
					)
				};
		}
	};

	$: readinessChecks =
		(status?.readiness?.checks as Record<string, ReadinessCheck> | undefined) ?? {};
	$: backgroundQueues = readinessChecks.background_queues ?? {};
	$: skillItems = listFrom(skills, ['data', 'skills', 'items']);
	$: toolsetItems = listFrom(toolsets, ['data', 'toolsets', 'items']);
	$: configuredToolsets = toolsetItems.filter((item) => item.configured !== false);
	$: enabledFeatures = Object.entries(capabilities?.features ?? {}).filter(
		([, enabled]) => enabled === true
	);
	$: engineDisplayState =
		status?.state === 'operational'
			? 'ok'
			: status?.state === 'degraded'
				? 'warning'
				: status?.state
					? 'down'
					: 'unknown';
	$: engineMeta = displayMeta(engineDisplayState);
	$: healthRows = [
		{
			label: $i18n.t('Hermes Agent'),
			state: engineDisplayState,
			detail: status?.version ? `v${status.version}` : undefined,
			overall: true
		},
		{
			label: $i18n.t('AI model'),
			state: checkState(readinessChecks.model),
			detail: status?.model ?? capabilities?.model ?? undefined
		},
		{
			label: $i18n.t('Gateway'),
			state: checkState(readinessChecks.gateway),
			detail: status?.gateway_state ?? undefined
		},
		{
			label: $i18n.t('Internal storage'),
			state: checkState(readinessChecks.state_db)
		}
	];
	$: failingComponents = healthRows
		.filter((row) => !row.overall && (row.state === 'warning' || row.state === 'down'))
		.map((row) => row.label);
	$: engineIssue = describeIssue(status?.state, failingComponents, $i18n);

	const loadEngine = async () => {
		loading = true;
		capabilities = null;
		skills = null;
		toolsets = null;

		try {
			status = await getHermesStatus(localStorage.token);
			if (status.state === 'operational' || status.state === 'degraded') {
				[capabilities, skills, toolsets] = await Promise.all([
					getHermesCapabilities(localStorage.token).catch(() => null),
					getHermesSkills(localStorage.token).catch(() => null),
					getHermesToolsets(localStorage.token).catch(() => null)
				]);
			}
		} catch {
			// The backend answers 200 with a state even when Hermes is down, so a
			// failure here comes from Open WebUI itself, not from the engine.
			status = {
				configured: true,
				state: 'request_failed',
				version: null,
				model: null,
				active_agents: 0
			};
		} finally {
			lastChecked = new Date();
			loading = false;
		}
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
			<div class="mx-auto flex w-full max-w-5xl flex-col gap-4 py-4 sm:py-7">
				<header class="flex flex-col gap-4 px-1 sm:flex-row sm:items-start sm:justify-between">
					<div class="min-w-0">
						<div class="mb-2 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
							<EngineIcon className="size-4" strokeWidth="1.5" />
							<span>{$i18n.t('Engine')}</span>
						</div>
						<h1
							class="text-balance text-2xl font-medium text-gray-900 dark:text-gray-100 sm:text-3xl"
						>
							{$i18n.t('Your engine at a glance')}
						</h1>
						<p class="mt-2 max-w-2xl text-pretty text-sm text-gray-500 dark:text-gray-400">
							{$i18n.t('The essentials of Hermes Agent and its current activity, gathered here.')}
						</p>
					</div>

					<button
						class="flex h-9 shrink-0 items-center justify-center rounded-xl border border-gray-200 px-3 text-sm text-gray-700 transition hover:bg-gray-50 disabled:cursor-wait disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
						on:click={loadEngine}
						disabled={loading}
					>
						{#if loading}<Spinner className="mr-2 size-3.5" />{/if}
						{$i18n.t('Refresh')}
					</button>
				</header>

				{#if loading}
					<div class="rounded-2xl border border-gray-200 p-4 dark:border-gray-800">
						<div class="h-4 w-32 rounded bg-gray-100 dark:bg-gray-800"></div>
						<div class="mt-3 h-3 w-64 max-w-full rounded bg-gray-100 dark:bg-gray-800"></div>
					</div>
				{:else if engineDisplayState === 'ok'}
					<div
						class="flex flex-col gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950/30 sm:flex-row sm:items-center sm:justify-between"
					>
						<div class="flex items-start gap-3">
							<span class="mt-1 size-2.5 shrink-0 rounded-full bg-emerald-500"></span>
							<div>
								<div class="font-medium text-emerald-800 dark:text-emerald-200">
									{$i18n.t('Everything is operational')}
								</div>
								<div class="mt-0.5 text-pretty text-sm text-emerald-700 dark:text-emerald-300">
									{$i18n.t('Hermes Agent is ready. No action is required.')}
								</div>
							</div>
						</div>
						{#if lastChecked}
							<div class="shrink-0 text-xs text-emerald-700 dark:text-emerald-300">
								{$i18n.t('Last checked')}: {lastChecked.toLocaleTimeString()}
							</div>
						{/if}
					</div>
				{:else}
					<div
						class="flex flex-col gap-3 rounded-2xl border {engineDisplayState === 'warning'
							? 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'
							: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200'} p-4 sm:flex-row sm:items-start sm:justify-between"
					>
						<div class="flex items-start gap-3">
							<span class="mt-1 size-2.5 shrink-0 rounded-full {engineMeta.dot}"></span>
							<div>
								<div class="font-medium">{engineIssue.title}</div>
								<div class="mt-0.5 text-pretty text-sm">{engineIssue.description}</div>
								{#if engineIssue.hint}
									<div class="mt-2 text-pretty text-xs opacity-80">{engineIssue.hint}</div>
								{/if}
							</div>
						</div>
						{#if lastChecked}
							<div class="shrink-0 text-xs opacity-80">
								{$i18n.t('Last checked')}: {lastChecked.toLocaleTimeString()}
							</div>
						{/if}
					</div>
				{/if}

				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<section class="rounded-2xl border border-gray-200 p-5 dark:border-gray-800">
						<h2 class="text-balance text-sm font-medium text-gray-900 dark:text-gray-100">
							{$i18n.t('Engine health')}
						</h2>
						<div class="mt-3 divide-y divide-gray-100 dark:divide-gray-850">
							{#each healthRows as row (row.label)}
								{@const meta = displayMeta(row.state)}
								<div class="flex items-center justify-between gap-4 py-2.5 text-sm">
									<span class="text-gray-700 dark:text-gray-200">{row.label}</span>
									<div class="flex min-w-0 items-center gap-2">
										{#if row.detail}
											<span class="max-w-36 truncate text-xs text-gray-400" title={row.detail}>
												{row.detail}
											</span>
										{/if}
										<span class="size-2 shrink-0 rounded-full {meta.dot}"></span>
										<span class="shrink-0 text-xs {meta.text}">{meta.label}</span>
									</div>
								</div>
							{/each}
						</div>
					</section>

					<section class="rounded-2xl border border-gray-200 p-5 dark:border-gray-800">
						<div class="flex items-center justify-between gap-3">
							<h2 class="text-balance text-sm font-medium text-gray-900 dark:text-gray-100">
								{$i18n.t('What is connected')}
							</h2>
							<a
								href="/workspace"
								class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white"
							>
								{$i18n.t('Manage')} →
							</a>
						</div>
						<div class="mt-3 divide-y divide-gray-100 dark:divide-gray-850">
							<div class="flex items-center justify-between gap-3 py-2.5 text-sm">
								<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Active model')}</span>
								<span class="max-w-52 truncate text-xs font-medium" title={status?.model ?? ''}>
									{status?.model ?? capabilities?.model ?? '—'}
								</span>
							</div>
							<div class="flex items-center justify-between gap-3 py-2.5 text-sm">
								<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Installed skills')}</span>
								<span class="tabular-nums text-xs font-medium">{skillItems.length}</span>
							</div>
							<div class="flex items-center justify-between gap-3 py-2.5 text-sm">
								<span class="text-gray-700 dark:text-gray-200"
									>{$i18n.t('Configured toolsets')}</span
								>
								<span class="tabular-nums text-xs font-medium">{configuredToolsets.length}</span>
							</div>
						</div>
					</section>

					<section class="rounded-2xl border border-gray-200 p-5 dark:border-gray-800">
						<h2 class="text-balance text-sm font-medium text-gray-900 dark:text-gray-100">
							{$i18n.t('Current activity')}
						</h2>
						<div class="mt-4 grid grid-cols-3 gap-3">
							{#each [{ label: $i18n.t('Active agents'), value: status?.active_agents ?? 0 }, { label: $i18n.t('API runs'), value: backgroundQueues.active_api_runs ?? 0 }, { label: $i18n.t('Delegations'), value: backgroundQueues.active_delegations ?? 0 }] as metric}
								<div class="min-w-0 rounded-xl bg-gray-50 p-3 dark:bg-gray-850">
									<div class="tabular-nums text-xl font-medium text-gray-900 dark:text-gray-100">
										{metric.value}
									</div>
									<div class="mt-1 text-pretty text-xs text-gray-500">{metric.label}</div>
								</div>
							{/each}
						</div>
						<p class="mt-4 text-pretty text-xs text-gray-500 dark:text-gray-400">
							{status?.gateway_busy
								? $i18n.t('Hermes is currently working on a request.')
								: $i18n.t('Hermes is ready for a new request.')}
						</p>
					</section>

					<section class="rounded-2xl border border-gray-200 p-5 dark:border-gray-800">
						<h2 class="text-balance text-sm font-medium text-gray-900 dark:text-gray-100">
							{$i18n.t('Quick actions')}
						</h2>
						<a
							href="/"
							class="mt-4 flex items-center justify-center rounded-xl bg-black px-3 py-2 text-sm font-medium text-white hover:opacity-90 dark:bg-white dark:text-black"
						>
							{$i18n.t('New chat')}
						</a>
						<div class="mt-2 grid grid-cols-3 gap-2">
							<a
								href="/workspace/models"
								class="rounded-xl border border-gray-200 px-2 py-2 text-center text-xs hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-850"
								>{$i18n.t('Models')}</a
							>
							<a
								href="/workspace/skills"
								class="rounded-xl border border-gray-200 px-2 py-2 text-center text-xs hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-850"
								>{$i18n.t('Skills')}</a
							>
							<a
								href="/workspace/tools"
								class="rounded-xl border border-gray-200 px-2 py-2 text-center text-xs hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-850"
								>{$i18n.t('Tools')}</a
							>
						</div>
					</section>
				</div>

				<details class="rounded-2xl border border-gray-200 dark:border-gray-800">
					<summary
						class="cursor-pointer select-none px-5 py-4 text-sm font-medium text-gray-700 hover:text-gray-950 dark:text-gray-200 dark:hover:text-white"
					>
						{$i18n.t('Technical details')}
					</summary>
					<div
						class="grid grid-cols-1 gap-4 border-t border-gray-100 p-5 dark:border-gray-850 lg:grid-cols-3"
					>
						<section>
							<div class="flex items-center justify-between text-sm font-medium">
								<span>{$i18n.t('Capabilities')}</span>
								<span class="tabular-nums text-xs text-gray-400">{enabledFeatures.length}</span>
							</div>
							<div class="mt-3 flex flex-wrap gap-1.5">
								{#each enabledFeatures.slice(0, 12) as [key]}
									<span
										class="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300"
									>
										{key.replaceAll('_', ' ')}
									</span>
								{/each}
								{#if enabledFeatures.length === 0}<span class="text-xs text-gray-400">—</span>{/if}
							</div>
						</section>

						{#each [{ title: $i18n.t('Skills'), items: skillItems }, { title: $i18n.t('Tools'), items: toolsetItems }] as group}
							<section>
								<div class="flex items-center justify-between text-sm font-medium">
									<span>{group.title}</span>
									<span class="tabular-nums text-xs text-gray-400">{group.items.length}</span>
								</div>
								<div class="mt-3 flex flex-wrap gap-1.5">
									{#each group.items.slice(0, 12) as item}
										<span
											class="max-w-full truncate rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300"
										>
											{itemLabel(item)}
										</span>
									{/each}
									{#if group.items.length === 0}<span class="text-xs text-gray-400">—</span>{/if}
								</div>
							</section>
						{/each}
					</div>
				</details>
			</div>
		</main>
	</div>
{/if}
