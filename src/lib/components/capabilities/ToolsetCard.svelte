<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let toolset: {
		name: string;
		label: string;
		description?: string;
		tools?: string[];
		enabled: boolean;
		connection_state?: string;
	};

	let expanded = false;

	$: needsConnection = toolset.connection_state === 'connection_required';
	$: isConnected = toolset.connection_state === 'connected';
	$: connectable = needsConnection || isConnected;
	// FR-013 : toolset activé mais connexion manquante → avertir.
	$: warnMissing = toolset.enabled && needsConnection;
</script>

<div class="border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3">
	<div class="flex items-start gap-3">
		<button
			type="button"
			class="flex-1 min-w-0 text-left"
			on:click={() => (expanded = !expanded)}
			aria-expanded={expanded}
		>
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-400">{expanded ? '▾' : '▸'}</span>
				<span class="text-sm font-medium truncate">{toolset.label}</span>
				{#if isConnected}
					<span
						class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
						>{$i18n.t('Connecté')}</span
					>
				{:else if needsConnection}
					<span
						class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400"
						>{$i18n.t('Connexion requise')}</span
					>
				{/if}
			</div>
			{#if toolset.description}
				<div class="text-xs text-gray-500 mt-0.5 line-clamp-2 pl-5">{toolset.description}</div>
			{/if}
			{#if toolset.tools && toolset.tools.length > 0}
				<div class="text-[11px] text-gray-400 mt-1 pl-5">
					{toolset.tools.length}
					{toolset.tools.length > 1 ? $i18n.t('outils') : $i18n.t('outil')}
				</div>
			{/if}
		</button>
		<div class="flex-none self-center">
			<Switch state={toolset.enabled} on:change={() => dispatch('toggle')} />
		</div>
	</div>

	{#if warnMissing}
		<div class="text-[11px] text-amber-600 dark:text-amber-400 mt-2 pl-5">
			{$i18n.t('Activé mais non connecté : configure la connexion pour qu’il fonctionne.')}
		</div>
	{/if}

	{#if expanded}
		<div class="mt-3 pl-5 border-t border-gray-100 dark:border-gray-850 pt-3">
			{#if toolset.tools && toolset.tools.length > 0}
				<div class="flex flex-wrap gap-1.5">
					{#each toolset.tools as tool (tool)}
						<span
							class="text-[11px] px-2 py-0.5 rounded-lg bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300 font-mono"
							>{tool}</span
						>
					{/each}
				</div>
			{:else}
				<div class="text-[11px] text-gray-400">{$i18n.t('Aucun outil listé')}</div>
			{/if}

			{#if connectable}
				<div class="mt-3">
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => dispatch('connect')}
					>
						{isConnected ? $i18n.t('Gérer la connexion') : $i18n.t('Connecter')}
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
