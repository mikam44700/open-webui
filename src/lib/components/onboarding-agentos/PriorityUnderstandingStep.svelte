<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import {
		buildPriorityInsights,
		provenanceLabel,
		sourceDomain
	} from '$lib/onboarding-agentos/logic';
	import type {
		OperationalMap,
		PreparedActionDraft,
		PriorityInsight
	} from '$lib/onboarding-agentos/types';

	export let map: OperationalMap;
	export let preparedActions: PreparedActionDraft[] = [];
	export let pagesRead = 0;
	export let externalSourcesRetained = 0;
	export let questionCount = 0;

	let understandingConfirmed = false;
	let openDraftId = '';

	const dispatch = createEventDispatcher<{
		prepare: { insight: PriorityInsight };
		updateDraft: { id: string; field: keyof PreparedActionDraft; value: string };
		back: void;
		continue: void;
	}>();

	$: insights = buildPriorityInsights(map.facts, map.goals ?? [], 5);
	const goalLabel = (goalId: string) =>
		map.goals?.find((goal) => goal.id === goalId)?.label ?? 'Priorité à préciser';
	const factById = (id: string) => map.facts.find((fact) => fact.id === id);
	const draftFor = (insightId: string) =>
		preparedActions.find((draft) => draft.insightId === insightId);
	const urgencyLabel = (urgency: PriorityInsight['urgency']) =>
		({ haute: 'Haute', moyenne: 'Moyenne', faible: 'Faible' })[urgency];
	const updateDraft = (
		draft: PreparedActionDraft,
		field: keyof PreparedActionDraft,
		value: string
	) => dispatch('updateDraft', { id: draft.id, field, value });
</script>

<section class="w-full py-8">
	<div class="mx-auto max-w-4xl text-center">
		<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
			Étape 4 · Compréhension
		</div>
		<h1 class="mt-3 text-3xl font-medium tracking-[-0.04em] md:text-5xl">
			Voici ce qui mérite votre attention.
		</h1>
		<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
			3 à 5 conclusions capables de changer une décision ou une question d’entretien. Le reste
			nourrira la mémoire de votre entreprise.
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
			<div class="text-2xl font-medium">{map.facts.length}</div>
			<div class="mt-1 text-xs text-gray-500">preuves conservées</div>
		</div>
		<div class="rounded-2xl border border-[#6b62f2]/30 bg-[#6b62f2]/6 p-4">
			<div class="text-2xl font-medium text-[#5b52dd] dark:text-[#aaa4ff]">{insights.length}</div>
			<div class="mt-1 text-xs text-gray-500">cartes prioritaires</div>
		</div>
	</div>

	<div class="mx-auto mt-7 grid max-w-5xl gap-4 lg:grid-cols-2">
		{#each insights as insight, index}
			{@const draft = draftFor(insight.id)}
			<article
				class="rounded-[1.75rem] border border-black/6 bg-white p-5 shadow-sm dark:border-white/8 dark:bg-[#161616]"
			>
				<div class="flex flex-wrap items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						<span
							class="flex size-7 items-center justify-center rounded-full bg-[#6b62f2] text-xs font-semibold text-white"
						>
							{index + 1}
						</span>
						<span
							class="rounded-full bg-[#6b62f2]/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#5b52dd] dark:text-[#aaa4ff]"
						>
							{goalLabel(insight.goalId)}
						</span>
					</div>
					<span class="text-[11px] text-gray-400">
						Fiabilité {Math.round(insight.confidence * 100)} %
					</span>
				</div>

				<h2 class="mt-4 text-lg font-medium">{insight.title}</h2>
				<p class="mt-2 text-sm leading-6 text-gray-700 dark:text-gray-200">{insight.finding}</p>

				<div class="mt-4 grid gap-2 sm:grid-cols-2">
					<div class="rounded-xl bg-gray-50 p-3 dark:bg-[#101010]">
						<div class="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
							Impact attendu
						</div>
						<div class="mt-1 text-xs leading-5">{insight.impact}</div>
					</div>
					<div class="rounded-xl bg-gray-50 p-3 dark:bg-[#101010]">
						<div class="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
							Urgence
						</div>
						<div class="mt-1 text-xs font-medium">{urgencyLabel(insight.urgency)}</div>
					</div>
				</div>

				<div class="mt-2 rounded-xl bg-gray-50 p-3 dark:bg-[#101010]">
					<div class="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
						Pourquoi cela compte
					</div>
					<div class="mt-1 text-xs leading-5">{insight.whyItMatters}</div>
				</div>

				{#if insight.contradictionFactIds.length}
					<div
						class="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
					>
						<strong>Point à vérifier :</strong> les sources ne donnent pas la même information. LunarIA
						ne tranche pas silencieusement.
					</div>
				{/if}

				<details class="mt-3 rounded-xl border border-gray-100 dark:border-gray-800">
					<summary class="cursor-pointer list-none p-3 text-xs font-medium">
						{insight.evidenceFactIds.length} preuve(s) associée(s)
					</summary>
					<div class="space-y-2 border-t border-gray-100 p-3 dark:border-gray-800">
						{#each insight.evidenceFactIds as factId}
							{@const fact = factById(factId)}
							{#if fact}
								<div class="text-xs leading-5">
									<div>{fact.value}</div>
									<div class="mt-1 text-[11px] text-gray-400">
										{provenanceLabel(fact)}
										{#if fact.sourceUrl}
											· <a
												class="text-[#5b52dd] hover:underline"
												href={fact.sourceUrl}
												target="_blank"
												rel="noreferrer"
											>
												{fact.sourceTitle || sourceDomain(fact.sourceUrl)}
											</a>
										{/if}
									</div>
								</div>
							{/if}
						{/each}
					</div>
				</details>

				<div class="mt-4 rounded-xl border border-[#6b62f2]/15 bg-[#6b62f2]/5 p-3">
					<div
						class="text-[10px] font-semibold uppercase tracking-wide text-[#5b52dd] dark:text-[#aaa4ff]"
					>
						Prochaine action
					</div>
					<div class="mt-1 text-xs leading-5">{insight.nextAction}</div>
					<button
						type="button"
						class="mt-3 rounded-full bg-[#6b62f2] px-4 py-2 text-xs font-medium text-white"
						on:click={() => {
							dispatch('prepare', { insight });
							openDraftId = insight.id;
						}}
					>
						{draft ? 'Voir le brouillon' : insight.actionLabel}
					</button>
				</div>

				{#if draft && openDraftId === insight.id}
					<div
						class="mt-3 space-y-3 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4 dark:border-emerald-900/50 dark:bg-emerald-950/20"
					>
						<div class="flex items-center justify-between">
							<div class="text-sm font-medium">Brouillon d’action</div>
							<span
								class="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-semibold text-amber-800"
							>
								{draft.status}
							</span>
						</div>
						<label class="block text-xs">
							<span class="text-gray-500">Livrable attendu</span>
							<textarea
								class="mt-1 w-full rounded-xl border bg-white p-2.5 dark:bg-[#101010]"
								rows="2"
								value={draft.deliverable}
								on:input={(event) => updateDraft(draft, 'deliverable', event.currentTarget.value)}
							></textarea>
						</label>
						<div class="grid gap-3 sm:grid-cols-2">
							<label class="text-xs">
								<span class="text-gray-500">Responsable</span>
								<input
									class="mt-1 w-full rounded-xl border bg-white p-2.5 dark:bg-[#101010]"
									value={draft.owner}
									on:input={(event) => updateDraft(draft, 'owner', event.currentTarget.value)}
								/>
							</label>
							<label class="text-xs">
								<span class="text-gray-500">Échéance</span>
								<input
									class="mt-1 w-full rounded-xl border bg-white p-2.5 dark:bg-[#101010]"
									value={draft.deadline}
									on:input={(event) => updateDraft(draft, 'deadline', event.currentTarget.value)}
								/>
							</label>
						</div>
						<label class="block text-xs">
							<span class="text-gray-500">Indicateur de réussite</span>
							<textarea
								class="mt-1 w-full rounded-xl border bg-white p-2.5 dark:bg-[#101010]"
								rows="2"
								value={draft.successMetric}
								on:input={(event) => updateDraft(draft, 'successMetric', event.currentTarget.value)}
							></textarea>
						</label>
						<p class="text-[11px] leading-5 text-gray-500">
							Aucune action externe n’est déclenchée. Ce brouillon reste modifiable et attend votre
							validation.
						</p>
					</div>
				{/if}
			</article>
		{/each}
	</div>

	<div
		class="mx-auto mt-6 flex max-w-5xl items-center justify-between gap-4 rounded-[1.75rem] border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616] md:px-6"
	>
			<div>
				<h2 class="text-base font-medium">Mémoire profonde · {map.facts.length} preuves</h2>
				<div class="mt-1 text-xs text-gray-400">
					Éléments faibles conservés · {externalSourcesRetained} domaine(s) extérieur(s)
				</div>
			</div>
			<a
				href="/memoire"
				class="shrink-0 rounded-full border border-black/10 px-4 py-2 text-xs font-medium hover:bg-gray-50 dark:border-white/10 dark:hover:bg-gray-800"
			>
				Consulter la mémoire
			</a>
	</div>

	<div
		class="mx-auto mt-6 flex max-w-5xl flex-col gap-4 rounded-2xl border border-black/8 bg-white p-4 dark:border-white/10 dark:bg-[#161616] sm:flex-row sm:items-center sm:justify-between"
	>
		<label class="flex cursor-pointer items-start gap-3 text-sm">
			<input
				type="checkbox"
				bind:checked={understandingConfirmed}
				class="mt-0.5 size-4 accent-[#6b62f2]"
			/>
			<span>
				<span class="font-medium">Ces conclusions sont suffisamment justes pour continuer.</span>
				<span class="mt-0.5 block text-xs text-gray-500"
					>Les hypothèses et contradictions restent explicitement à vérifier.</span
				>
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
				disabled={!understandingConfirmed || !insights.length}
				on:click={() => dispatch('continue')}
			>
				Continuer avec {questionCount} questions utiles
			</button>
		</div>
	</div>
</section>
