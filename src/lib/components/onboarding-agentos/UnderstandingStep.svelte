<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { factsBySection, provenanceLabel, statusLabel } from '$lib/onboarding-agentos/logic';
	import type { EvidenceFact, OperationalMap } from '$lib/onboarding-agentos/types';

	export let map: OperationalMap;
	export let pagesRead = 0;
	export let externalSourcesRetained = 0;
	export let questionCount = 0;

	let generalUnderstandingConfirmed = false;
	let editingFactId = '';

	const dispatch = createEventDispatcher<{
		update: { id: string; value: string };
		remove: { id: string };
		back: void;
		continue: void;
	}>();

	$: groupedFacts = factsBySection(map.facts).filter((group) => group.facts.length);
	$: siteFacts = map.facts.filter((fact) => fact.sourceType === 'site').length;
	$: webFacts = map.facts.filter((fact) => fact.sourceType === 'web').length;

	const confidenceLabel = (fact: EvidenceFact) => {
		if (fact.status === 'corrige' || fact.status === 'confirme') return 'Confirmé';
		if (fact.confidence >= 0.8) return 'Confiance élevée';
		if (fact.confidence >= 0.6) return 'À vérifier';
		return 'Hypothèse fragile';
	};
</script>

<section class="w-full py-8">
	<div class="mx-auto max-w-4xl text-center">
		<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
			Étape 3 · Compréhension
		</div>
		<h1 class="mt-3 text-3xl font-medium tracking-[-0.04em] md:text-5xl">
			Voici ce que Luna a compris de {map.companyName || 'votre entreprise'}.
		</h1>
		<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
			J’ai croisé votre site avec des sources extérieures. Vérifiez ma compréhension avant que je
			vous pose uniquement les questions auxquelles le Web ne peut pas répondre.
		</p>
	</div>

	<div class="mx-auto mt-7 grid max-w-4xl gap-3 sm:grid-cols-3">
		<div
			class="rounded-2xl border border-black/6 bg-white p-4 dark:border-white/8 dark:bg-[#161616]"
		>
			<div class="text-2xl font-medium">{pagesRead}</div>
			<div class="mt-1 text-xs text-gray-500">pages utiles lues</div>
		</div>
		<div
			class="rounded-2xl border border-black/6 bg-white p-4 dark:border-white/8 dark:bg-[#161616]"
		>
			<div class="text-2xl font-medium">{externalSourcesRetained}</div>
			<div class="mt-1 text-xs text-gray-500">sources extérieures retenues</div>
		</div>
		<div class="rounded-2xl border border-[#6b62f2]/30 bg-[#6b62f2]/6 p-4 dark:bg-[#6b62f2]/10">
			<div class="text-2xl font-medium text-[#5b52dd] dark:text-[#aaa4ff]">
				{questionCount}
			</div>
			<div class="mt-1 text-xs text-gray-500">questions internes encore utiles</div>
		</div>
	</div>

	<div class="mx-auto mt-7 max-w-5xl space-y-4">
		{#each groupedFacts as group, groupIndex}
			<details
				open={groupIndex < 4}
				class="group rounded-[1.75rem] border border-black/6 bg-white dark:border-white/8 dark:bg-[#161616]"
			>
				<summary
					class="flex cursor-pointer list-none items-center justify-between gap-4 p-5 md:px-6"
				>
					<div>
						<h2 class="text-base font-medium">{group.section}</h2>
						<div class="mt-1 text-xs text-gray-400">{group.facts.length} élément(s) trouvé(s)</div>
					</div>
					<div
						class="flex size-8 items-center justify-center rounded-full bg-gray-100 text-gray-500 transition group-open:rotate-180 dark:bg-gray-800"
					>
						⌄
					</div>
				</summary>

				<div class="space-y-3 border-t border-gray-100 p-4 dark:border-gray-800 md:p-6">
					{#each group.facts as fact}
						<div
							class="rounded-2xl border border-gray-100 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-[#101010]"
						>
							<div class="flex flex-wrap items-start justify-between gap-3">
								<div class="min-w-0 flex-1">
									<div class="text-sm font-medium">{fact.label}</div>
									<div class="mt-2 flex flex-wrap gap-1.5 text-[11px]">
										<span
											class="rounded-full bg-gray-200/70 px-2 py-0.5 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
											>{provenanceLabel(fact)}</span
										>
										<span
											class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
											>{confidenceLabel(fact)}</span
										>
										<span
											class="rounded-full bg-gray-200/70 px-2 py-0.5 text-gray-500 dark:bg-gray-800"
										>
											{statusLabel(fact)}
										</span>
									</div>
								</div>
								<div class="flex gap-2">
									<button
										type="button"
										class="text-xs font-medium text-[#5b52dd] hover:underline dark:text-[#aaa4ff]"
										on:click={() => (editingFactId = editingFactId === fact.id ? '' : fact.id)}
										>{editingFactId === fact.id ? 'Fermer' : 'Corriger'}</button
									>
									<button
										type="button"
										class="text-xs text-red-500 hover:underline"
										on:click={() => dispatch('remove', { id: fact.id })}>Retirer</button
									>
								</div>
							</div>

							{#if editingFactId === fact.id}
								<textarea
									value={fact.value}
									rows={Math.min(6, Math.max(3, fact.value.split('\n').length))}
									class="mt-3 w-full resize-y rounded-xl border border-[#6b62f2]/40 bg-white px-3 py-2 text-sm leading-6 outline-none dark:bg-[#161616]"
									on:input={(event) =>
										dispatch('update', { id: fact.id, value: event.currentTarget.value })}
								></textarea>
							{:else}
								<p class="mt-3 text-sm leading-6 text-gray-700 dark:text-gray-200">{fact.value}</p>
							{/if}

							<div class="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
								{#if fact.sourceUrl}
									<a
										href={fact.sourceUrl}
										target="_blank"
										rel="noreferrer"
										class="max-w-full truncate text-[#5b52dd] hover:underline dark:text-[#aaa4ff]"
										>{fact.sourceTitle || fact.sourceUrl}</a
									>
									<span>·</span>
								{/if}
								<span>Consulté le {fact.observedAt}</span>
							</div>
						</div>
					{/each}
				</div>
			</details>
		{/each}
	</div>

	<div
		class="mx-auto mt-6 max-w-5xl rounded-[1.75rem] border border-amber-200 bg-amber-50 p-5 dark:border-amber-900/40 dark:bg-amber-950/20"
	>
		<div class="text-sm font-medium text-amber-900 dark:text-amber-200">
			Ce que Luna doit encore apprendre avec vous
		</div>
		<p class="mt-2 text-sm leading-6 text-amber-800/80 dark:text-amber-100/70">
			Vos priorités réelles, vos pertes de temps ou d’argent, vos processus internes, vos outils,
			les responsables, vos indicateurs et les actions qui exigent toujours votre validation.
		</p>
	</div>

	<div
		class="sticky bottom-4 mx-auto mt-6 flex max-w-5xl flex-col gap-4 rounded-2xl border border-black/8 bg-white/95 p-4 shadow-lg backdrop-blur dark:border-white/10 dark:bg-[#161616]/95 sm:flex-row sm:items-center sm:justify-between"
	>
		<label class="flex cursor-pointer items-start gap-3 text-sm">
			<input
				type="checkbox"
				bind:checked={generalUnderstandingConfirmed}
				class="mt-0.5 size-4 accent-[#6b62f2]"
			/>
			<span>
				<span class="font-medium">La compréhension générale est juste.</span>
				<span class="mt-0.5 block text-xs text-gray-500">
					Les éléments Web restent des hypothèses jusqu’à la Carte finale.
				</span>
			</span>
		</label>
		<div class="flex shrink-0 flex-wrap gap-2">
			<button
				type="button"
				class="rounded-full px-4 py-2.5 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
				on:click={() => dispatch('back')}>Relancer l’analyse</button
			>
			<button
				type="button"
				class="rounded-full bg-[#6b62f2] px-5 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
				disabled={!generalUnderstandingConfirmed}
				on:click={() => dispatch('continue')}
			>
				Continuer avec {questionCount} question{questionCount > 1 ? 's' : ''} utile{questionCount >
				1
					? 's'
					: ''}
			</button>
		</div>
	</div>

	<div class="mx-auto mt-4 max-w-5xl text-center text-[11px] text-gray-400">
		{siteFacts} fait(s) issu(s) du site · {webFacts} fait(s) issu(s) du Web
	</div>
</section>
