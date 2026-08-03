<script lang="ts">
	/**
	 * Les derniers traitements, en clair.
	 *
	 * La colonne « source » n'est pas decorative : c'est elle qui repond a la
	 * question que pose un dirigeant devant l'ecran — « ca vient d'ou, ca ? ».
	 * Un traitement declenche depuis Telegram a 6 h du matin par une tache
	 * planifiee doit se lire comme tel, sinon l'assistant a l'air de faire des
	 * choses sans qu'on sache pourquoi.
	 */
	import { getContext } from 'svelte';

	import type { Traitement } from '$lib/apis/journal';

	const i18n = getContext('i18n');

	export let traitements: Traitement[] = [];

	const sources: Record<string, string> = {
		interface: 'journal.source.interface',
		telegram: 'journal.source.telegram',
		scheduled: 'journal.source.planifie',
		api: 'journal.source.api'
	};

	const pastilles: Record<string, string> = {
		ok: 'bg-emerald-500',
		pending: 'bg-amber-500',
		error: 'bg-red-500',
		unknown: 'bg-gray-400'
	};

	const heure = (horodatage: number) =>
		new Date(horodatage * 1000).toLocaleString($i18n.language, {
			day: '2-digit',
			month: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
</script>

<ul class="flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
	{#each traitements as traitement (traitement.id)}
		<li class="flex items-start gap-3 py-3">
			<span
				class="mt-1.5 size-2 shrink-0 rounded-full {pastilles[traitement.status] ?? pastilles.unknown}"
				aria-hidden="true"
			></span>

			<div class="flex min-w-0 flex-1 flex-col">
				<div class="truncate text-sm text-gray-800 dark:text-gray-200">
					{traitement.summary || traitement.action}
				</div>

				<div class="flex flex-wrap items-center gap-x-2 text-xs text-gray-500 dark:text-gray-400">
					<span>{$i18n.t(sources[traitement.source] ?? 'journal.source.api')}</span>
					{#if traitement.reference}
						<span aria-hidden="true">·</span>
						<span class="font-mono">{traitement.reference}</span>
					{/if}
					<span aria-hidden="true">·</span>
					<time datetime={new Date(traitement.created_at * 1000).toISOString()}>
						{heure(traitement.created_at)}
					</time>
				</div>

				{#if traitement.status === 'error' && traitement.error}
					<div class="mt-1 text-xs text-red-600 dark:text-red-400">
						{traitement.error}
					</div>
				{/if}
			</div>
		</li>
	{/each}
</ul>
