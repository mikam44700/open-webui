<script lang="ts">
	import Spinner from '$lib/components/common/Spinner.svelte';

	/**
	 * Conteneur de carte partagé. Reprend le langage visuel « monochrome restreint » :
	 * bordure très légère, coins généreux, titre discret, chargement par spinner centré.
	 */
	export let title = '';
	export let loading = false;
</script>

<div class="flex flex-col gap-2.5 rounded-2xl border border-gray-100 p-4 dark:border-gray-850">
	<div class="flex items-center justify-between gap-3">
		<div class="text-sm font-medium">{title}</div>
		{#if $$slots.action}
			<div class="shrink-0"><slot name="action" /></div>
		{/if}
	</div>

	{#if loading}
		<div class="flex justify-center py-6"><Spinner className="size-5" /></div>
	{:else}
		<slot />
	{/if}
</div>
