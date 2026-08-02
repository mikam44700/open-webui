<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import type { CapabilityGroup } from '$lib/engine/health';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let groups: CapabilityGroup[] = [];
	export let skills: Record<string, unknown>[] = [];
	export let toolsets: Record<string, unknown>[] = [];
	export let runtime: { mode?: string; tool_execution?: string; description?: string } | null =
		null;

	const readable = (value: string) => value.replaceAll('_', ' ');

	const itemLabel = (item: Record<string, unknown>) =>
		String(item.label ?? item.name ?? item.id ?? $i18n.t('Unknown'));

	const itemDescription = (item: Record<string, unknown>) => {
		const value = item.description ?? item.summary;
		return typeof value === 'string' ? value : '';
	};

	/** Un outil sans indication est considéré comme configuré : Hermes ne l'aurait pas listé sinon. */
	const isConfigured = (item: Record<string, unknown>) => item.configured !== false;
</script>

<details class="rounded-2xl border border-gray-100 dark:border-gray-850">
	<summary
		class="cursor-pointer select-none px-4 py-3.5 text-sm font-medium text-gray-700 hover:text-gray-950 dark:text-gray-200 dark:hover:text-white"
	>
		{$i18n.t('Technical details')}
	</summary>

	<div class="flex flex-col gap-6 border-t border-gray-100 p-4 dark:border-gray-850">
		{#if runtime?.mode || runtime?.tool_execution}
			<section class="flex flex-wrap gap-x-6 gap-y-2 text-xs text-gray-500 dark:text-gray-400">
				{#if runtime.mode}
					<span
						>{$i18n.t('Runtime mode')}:
						<span class="font-medium">{readable(runtime.mode)}</span></span
					>
				{/if}
				{#if runtime.tool_execution}
					<span>
						{$i18n.t('Tool execution')}:
						<span class="font-medium">{readable(runtime.tool_execution)}</span>
					</span>
				{/if}
			</section>
		{/if}

		<section>
			<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Capabilities')}
			</h3>
			{#if groups.length === 0}
				<p class="mt-2 text-xs text-gray-400">{$i18n.t('No capability data available.')}</p>
			{:else}
				<div class="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
					{#each groups as group (group.titleKey)}
						<div>
							<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t(group.titleKey)}
							</div>
							<div class="mt-2 flex flex-wrap gap-1.5">
								{#each group.items as item (item.name)}
									<span
										class="rounded-lg px-2 py-1 text-xs {item.enabled
											? 'bg-gray-100 text-gray-600 dark:bg-gray-850 dark:text-gray-300'
											: 'text-gray-400 line-through decoration-gray-300 dark:text-gray-500 dark:decoration-gray-700'}"
										title={item.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}
									>
										{readable(item.name)}
									</span>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</section>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<section>
				<div class="flex items-center justify-between text-sm font-medium">
					<span>{$i18n.t('Skills')}</span>
					<span class="tabular-nums text-xs text-gray-400">{skills.length}</span>
				</div>
				{#if skills.length === 0}
					<p class="mt-2 text-xs text-gray-400">—</p>
				{:else}
					<ul class="mt-2 flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
						{#each skills as skill}
							<li class="py-2">
								<div class="truncate text-xs font-medium text-gray-700 dark:text-gray-200">
									{itemLabel(skill)}
								</div>
								{#if itemDescription(skill)}
									<div class="mt-0.5 line-clamp-2 text-pretty text-xs text-gray-500">
										{itemDescription(skill)}
									</div>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</section>

			<section>
				<div class="flex items-center justify-between text-sm font-medium">
					<span>{$i18n.t('Tools')}</span>
					<span class="tabular-nums text-xs text-gray-400">{toolsets.length}</span>
				</div>
				{#if toolsets.length === 0}
					<p class="mt-2 text-xs text-gray-400">—</p>
				{:else}
					<ul class="mt-2 flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
						{#each toolsets as toolset}
							<li class="flex items-center justify-between gap-3 py-2">
								<span class="min-w-0 truncate text-xs text-gray-700 dark:text-gray-200">
									{itemLabel(toolset)}
								</span>
								{#if !isConfigured(toolset)}
									<span class="shrink-0 text-xs text-gray-400">{$i18n.t('Not configured')}</span>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		</div>
	</div>
</details>
