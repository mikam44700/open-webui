<script lang="ts">
	// Panneau de revue de l'édition assistée (feature 022) : avant/après surligné + Appliquer / Rejeter.
	// N'écrit RIEN : il affiche la proposition et délègue la décision (le contenu enregistré ne change
	// qu'au clic « Appliquer », côté parent). Diff pur (noteDiff).
	import { diffLines } from '$lib/memory/noteDiff';

	export let before: string;
	export let after: string;
	export let status: 'ready' | 'nochange' = 'ready';
	export let onApply: () => void;
	export let onReject: () => void;

	$: segments = status === 'ready' ? diffLines(before, after) : [];
	$: addCount = segments.filter((s) => s.type === 'add').length;
	$: delCount = segments.filter((s) => s.type === 'del').length;
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 backdrop-blur-[2px] p-4"
	on:click={onReject}
>
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl bg-white dark:bg-gray-900 ring-1 ring-black/10 dark:ring-white/10 shadow-2xl overflow-hidden"
		on:click|stopPropagation
	>
		<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center gap-2">
			<img
				src="/assets/agents/adam.webp"
				alt="Adam"
				on:error={(e) => ((e.currentTarget as HTMLImageElement).src = '/favicon.png')}
				class="h-7 w-7 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15"
			/>
			<div class="min-w-0 flex-1">
				<div class="text-sm font-semibold text-gray-900 dark:text-white">
					Adam propose une amélioration
				</div>
				{#if status === 'ready'}
					<div class="text-[11.5px] text-gray-500 dark:text-gray-400">
						<span class="text-emerald-600 dark:text-emerald-400">+{addCount} ajout(s)</span>
						·
						<span class="text-red-500 dark:text-red-400">−{delCount} retrait(s)</span>
						· vous validez avant tout changement
					</div>
				{/if}
			</div>
		</div>

		{#if status === 'nochange'}
			<div class="px-4 py-8 text-center">
				<div class="text-sm text-gray-700 dark:text-gray-200">Rien à améliorer.</div>
				<div class="mt-1 text-[12.5px] text-gray-500 dark:text-gray-400">
					Cette note est déjà claire — Adam ne propose aucun changement.
				</div>
				<button
					class="mt-4 px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium transition"
					on:click={onReject}
				>
					Fermer
				</button>
			</div>
		{:else}
			<div class="flex-1 overflow-auto px-3 py-2 font-mono text-[12.5px] leading-relaxed">
				{#each segments as seg, i (i)}
					<div
						class="flex gap-2 px-2 rounded {seg.type === 'add'
							? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-200'
							: seg.type === 'del'
								? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
								: 'text-gray-600 dark:text-gray-300'}"
					>
						<span
							class="shrink-0 w-3 select-none {seg.type === 'add'
								? 'text-emerald-500'
								: seg.type === 'del'
									? 'text-red-400'
									: 'text-gray-300 dark:text-gray-600'}"
							>{seg.type === 'add' ? '+' : seg.type === 'del' ? '−' : ''}</span
						>
						<span class="whitespace-pre-wrap wrap-break-word">{seg.text || ' '}</span>
					</div>
				{/each}
			</div>

			<div
				class="px-4 py-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-end gap-2"
			>
				<button
					class="px-3 py-1.5 rounded-lg text-[13px] text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 transition"
					on:click={onReject}
				>
					Rejeter
				</button>
				<button
					class="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[13px] font-medium transition"
					on:click={onApply}
				>
					Appliquer
				</button>
			</div>
		{/if}
	</div>
</div>
