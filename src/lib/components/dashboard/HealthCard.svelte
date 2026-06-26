<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import type { DisplayStatus } from '$lib/dashboard/alerts';

	const i18n = getContext('i18n');

	// Chaque brique : libellé dirigeant + statut honnête + détail optionnel (version, modèle…).
	export let bricks: { label: string; status: DisplayStatus; detail?: string }[] = [];
	export let loading = false;

	const dotClass: Record<DisplayStatus, string> = {
		ok: 'bg-green-500',
		down: 'bg-red-500',
		unknown: 'bg-gray-400 dark:bg-gray-600'
	};
	const statusLabel: Record<DisplayStatus, string> = {
		ok: 'Opérationnel',
		down: 'En panne',
		unknown: 'Indisponible'
	};
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="text-sm font-medium">{$i18n.t('Mon Agent OS')}</div>

	{#if loading}
		<div class="flex justify-center py-6"><Spinner className="size-5" /></div>
	{:else}
		<div class="flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
			{#each bricks as b (b.label)}
				<div class="flex items-center justify-between py-2 text-sm">
					<span class="text-gray-700 dark:text-gray-200">{$i18n.t(b.label)}</span>
					<span class="flex items-center gap-2">
						{#if b.detail}
							<span class="text-xs text-gray-400">{b.detail}</span>
						{/if}
						<span class="inline-block size-2 rounded-full {dotClass[b.status]}"></span>
						<span
							class="text-xs {b.status === 'ok'
								? 'text-green-600 dark:text-green-400'
								: b.status === 'down'
									? 'text-red-600 dark:text-red-400'
									: 'text-gray-500'}">{$i18n.t(statusLabel[b.status])}</span
						>
					</span>
				</div>
			{/each}
		</div>
	{/if}
</div>
