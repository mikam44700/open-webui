<script lang="ts">
	import { getContext } from 'svelte';
	import { WORKFLOWS } from '$lib/catalog/workflows';
	import { startWorkflow } from '$lib/workflows/launch';

	const i18n = getContext('i18n');
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="text-sm font-medium">{$i18n.t('Que puis-je faire ?')}</div>
	<div class="text-xs text-gray-500">
		{$i18n.t('Lancez une action — l’assistant ouvre une conversation prête à envoyer.')}
	</div>

	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mt-1">
		{#each WORKFLOWS as w (w.id)}
			<button
				type="button"
				class="flex items-start gap-2.5 text-left px-3 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={() => startWorkflow(w.prompt)}
			>
				<span class="text-lg leading-none mt-0.5">{w.icon}</span>
				<span class="flex flex-col min-w-0">
					<span class="text-sm font-medium truncate">{$i18n.t(w.label)}</span>
					<span class="text-xs text-gray-500 line-clamp-2">{$i18n.t(w.description)}</span>
				</span>
			</button>
		{/each}
	</div>
</div>
