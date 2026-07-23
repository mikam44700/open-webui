<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import {
		EXECUTIVE_GROUPS,
		buildExternalBusinessSignals,
		factsBySection,
		provenanceLabel,
		sourceDomain,
		sourceQualityLabel,
		statusLabel
	} from '$lib/onboarding-agentos/logic';
	import type { EvidenceFact, OperationalMap } from '$lib/onboarding-agentos/types';

	export let map: OperationalMap;
	export let executiveFacts: EvidenceFact[] = [];
	export let pagesRead = 0;
	export let externalSourcesRetained = 0;
	export let webProvider = '';
	export let questionCount = 0;

	let understandingConfirmed = false;
	let editingFactId = '';

	const dispatch = createEventDispatcher<{
		update: { id: string; value: string };
		remove: { id: string };
		back: void;
		continue: void;
	}>();

	$: groupedEvidence = factsBySection(map.facts);
	$: executiveGroups = EXECUTIVE_GROUPS.map((group) => ({
		...group,
		facts: executiveFacts.filter((fact) => group.sections.includes(fact.section))
	})).filter((group) => group.facts.length);
	$: siteFacts = map.facts.filter((fact) => fact.sourceType === 'site').length;
	$: webFacts = map.facts.filter((fact) => fact.sourceType === 'web').length;
	$: businessSignals = buildExternalBusinessSignals(map.facts, map.goals ?? [], 5);
	$: webProviderLabel =
		({ exa: 'Exa', brave: 'Brave Search', tavily: 'Tavily' } as Record<string, string>)[
			webProvider.toLowerCase()
		] ||
		webProvider ||
		'la recherche Web';
	const signalLabel = (kind = '') =>
		(
			({
				opportunite: 'Opportunité',
				risque: 'Risque',
				besoin_client: 'Besoin client',
				mouvement_concurrent: 'Mouvement concurrent',
				signal_marche: 'Signal marché'
			}) as Record<string, string>
		)[kind] ?? 'Signal extérieur';
	const goalLabel = (goalId = '') =>
		map.goals?.find((goal) => goal.id === goalId)?.label ?? 'Priorité à préciser';
</script>

<section class="w-full py-8">
	<div class="mx-auto max-w-4xl text-center">
		<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
			Étape 4 · Compréhension
		</div>
		<h1 class="mt-3 text-3xl font-medium tracking-[-0.04em] md:text-5xl">
			Voici l’essentiel pour {map.companyName || 'votre entreprise'}.
		</h1>
		<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
			Luna conserve toutes les preuves, mais vous montre d’abord ce qui peut réellement éclairer une
			décision, alimenter un workflow ou mesurer un progrès.
		</p>
		{#if map.goals?.length}
			<div class="mt-5 flex flex-wrap justify-center gap-2">
				{#each map.goals as goal}
					<span
						class="rounded-full border border-[#6b62f2]/25 bg-[#6b62f2]/7 px-3 py-1.5 text-xs font-medium text-[#5b52dd] dark:text-[#aaa4ff]"
					>
						{goal.label}
					</span>
				{/each}
			</div>
		{/if}
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
			<div class="mt-1 text-xs text-gray-500">preuves conservées en profondeur</div>
		</div>
		<div class="rounded-2xl border border-[#6b62f2]/30 bg-[#6b62f2]/6 p-4 dark:bg-[#6b62f2]/10">
			<div class="text-2xl font-medium text-[#5b52dd] dark:text-[#aaa4ff]">
				{executiveFacts.length}
			</div>
			<div class="mt-1 text-xs text-gray-500">conclusions prioritaires</div>
		</div>
	</div>

	{#if businessSignals.length}
		<section
			class="mx-auto mt-7 max-w-5xl overflow-hidden rounded-[2rem] border border-[#6b62f2]/30 bg-gradient-to-br from-[#6b62f2]/12 via-white to-white dark:from-[#6b62f2]/18 dark:via-[#161616] dark:to-[#111]"
		>
			<div class="border-b border-[#6b62f2]/15 px-5 py-5 md:px-7">
				<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
					Intelligence extérieure
				</div>
				<div class="mt-2 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
					<div>
						<h2 class="text-2xl font-medium tracking-[-0.03em]">
							Ce que {webProviderLabel} apporte à votre entreprise
						</h2>
						<p class="mt-2 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
							Des signaux extérieurs reliés à vos priorités, avec la décision suivante déjà cadrée.
							Ce sont des hypothèses à vérifier, pas encore des vérités internes.
						</p>
					</div>
					<div class="text-xs text-gray-400">
						{externalSourcesRetained} domaine(s) extérieur(s) retenu(s)
					</div>
				</div>
			</div>

			<div class="grid gap-3 p-4 md:p-6 lg:grid-cols-2">
				{#each businessSignals as fact, index}
					<article
						class="rounded-2xl border border-black/6 bg-white/85 p-4 shadow-sm dark:border-white/8 dark:bg-[#101010]/90"
					>
						<div class="flex flex-wrap items-center justify-between gap-2">
							<div class="flex items-center gap-2">
								<span
									class="flex size-6 items-center justify-center rounded-full bg-[#6b62f2] text-[11px] font-semibold text-white"
								>
									{index + 1}
								</span>
								<span
									class="rounded-full bg-[#6b62f2]/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#5b52dd] dark:text-[#aaa4ff]"
								>
									{signalLabel(fact.businessSignal?.kind)}
								</span>
							</div>
							<span class="text-[11px] text-gray-400">
								Fiabilité {Math.round(fact.confidence * 100)} %
							</span>
						</div>

						<h3 class="mt-4 text-base font-medium">{fact.label}</h3>
						<p class="mt-2 text-sm leading-6 text-gray-700 dark:text-gray-200">{fact.value}</p>

						<div class="mt-4 grid gap-2">
							<div class="rounded-xl bg-gray-50 p-3 dark:bg-[#181818]">
								<div class="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
									Priorité à 90 jours
								</div>
								<div class="mt-1 text-xs font-medium">
									{goalLabel(fact.businessSignal?.goalId)}
								</div>
							</div>
							<div class="rounded-xl bg-gray-50 p-3 dark:bg-[#181818]">
								<div class="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
									Pourquoi cela compte
								</div>
								<div class="mt-1 text-xs leading-5 text-gray-700 dark:text-gray-200">
									{fact.businessSignal?.whyItMatters}
								</div>
							</div>
							<div class="rounded-xl border border-[#6b62f2]/15 bg-[#6b62f2]/5 p-3">
								<div
									class="text-[10px] font-semibold uppercase tracking-wide text-[#5b52dd] dark:text-[#aaa4ff]"
								>
									Prochaine décision ou action
								</div>
								<div class="mt-1 text-xs leading-5 text-gray-700 dark:text-gray-200">
									{fact.businessSignal?.nextAction}
								</div>
							</div>
						</div>

						{#if fact.sourceUrl}
							<div class="mt-4 flex min-w-0 items-center gap-2 text-[11px]">
								<span
									class="shrink-0 rounded-full bg-gray-100 px-2 py-1 text-gray-500 dark:bg-gray-800"
								>
									{sourceDomain(fact.sourceUrl)}
								</span>
								<a
									href={fact.sourceUrl}
									target="_blank"
									rel="noreferrer"
									class="min-w-0 truncate text-[#5b52dd] hover:underline dark:text-[#aaa4ff]"
								>
									{fact.sourceTitle || 'Voir la preuve'}
								</a>
							</div>
						{/if}
					</article>
				{/each}
			</div>
		</section>
	{/if}

	<div class="mx-auto mt-7 max-w-5xl space-y-5">
		{#each executiveGroups as group}
			<section
				class="rounded-[1.75rem] border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616] md:p-6"
			>
				<div class="flex items-center justify-between gap-3">
					<h2 class="text-lg font-medium">{group.label}</h2>
					<span class="text-xs text-gray-400">{group.facts.length} conclusion(s)</span>
				</div>
				<div class="mt-4 grid gap-3 lg:grid-cols-2">
					{#each group.facts as fact}
						<article
							class="rounded-2xl border border-gray-100 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-[#101010]"
						>
							<div class="flex flex-wrap items-start justify-between gap-2">
								<div class="text-sm font-medium">{fact.label}</div>
								<span
									class="rounded-full bg-gray-200/70 px-2 py-0.5 text-[10px] text-gray-600 dark:bg-gray-800 dark:text-gray-300"
								>
									{sourceQualityLabel(fact, map.siteUrl)}
								</span>
							</div>
							<p class="mt-3 text-sm leading-6 text-gray-700 dark:text-gray-200">{fact.value}</p>
							<div
								class="mt-4 rounded-xl border border-[#6b62f2]/12 bg-[#6b62f2]/5 p-3 text-xs leading-5"
							>
								<div class="font-medium text-[#5b52dd] dark:text-[#aaa4ff]">
									Pourquoi c’est utile
								</div>
								<div class="mt-1 text-gray-600 dark:text-gray-300">
									{fact.utility?.purpose ??
										'Cette information aide Luna à mieux contextualiser ses actions.'}
								</div>
							</div>
							<div class="mt-3 text-[11px] text-gray-400">
								Décision : {fact.utility?.decision ?? 'À préciser avec vous'}
							</div>
							{#if fact.sourceUrl}
								<a
									href={fact.sourceUrl}
									target="_blank"
									rel="noreferrer"
									class="mt-2 block truncate text-[11px] text-[#5b52dd] hover:underline dark:text-[#aaa4ff]"
								>
									{fact.sourceTitle || fact.sourceUrl}
								</a>
							{/if}
						</article>
					{/each}
				</div>
			</section>
		{/each}
	</div>

	<details
		class="group mx-auto mt-6 max-w-5xl rounded-[1.75rem] border border-black/6 bg-white dark:border-white/8 dark:bg-[#161616]"
	>
		<summary class="flex cursor-pointer list-none items-center justify-between gap-4 p-5 md:px-6">
			<div>
				<h2 class="text-base font-medium">Voir les {map.facts.length} preuves et sources</h2>
				<div class="mt-1 text-xs text-gray-400">
					{siteFacts} issues du site · {webFacts} issues du Web · {externalSourcesRetained}
					sources extérieures
				</div>
			</div>
			<div
				class="flex size-8 items-center justify-center rounded-full bg-gray-100 text-gray-500 transition group-open:rotate-180 dark:bg-gray-800"
			>
				⌄
			</div>
		</summary>

		<div class="space-y-4 border-t border-gray-100 p-4 dark:border-gray-800 md:p-6">
			{#each groupedEvidence as group}
				<details class="rounded-2xl border border-gray-100 dark:border-gray-800">
					<summary class="flex cursor-pointer list-none justify-between gap-3 p-4">
						<span class="text-sm font-medium">{group.section}</span>
						<span class="text-xs text-gray-400">{group.facts.length}</span>
					</summary>
					<div class="space-y-3 border-t border-gray-100 p-3 dark:border-gray-800">
						{#each group.facts as fact}
							<div class="rounded-xl bg-gray-50 p-4 dark:bg-[#101010]">
								<div class="flex flex-wrap items-start justify-between gap-3">
									<div>
										<div class="text-sm font-medium">{fact.label}</div>
										<div class="mt-2 flex flex-wrap gap-1.5 text-[10px]">
											<span class="rounded-full bg-gray-200 px-2 py-0.5 dark:bg-gray-800">
												{provenanceLabel(fact)}
											</span>
											<span class="rounded-full bg-gray-200 px-2 py-0.5 dark:bg-gray-800">
												{statusLabel(fact)}
											</span>
										</div>
									</div>
									<div class="flex gap-2">
										<button
											type="button"
											class="text-xs font-medium text-[#5b52dd] hover:underline dark:text-[#aaa4ff]"
											on:click={() => (editingFactId = editingFactId === fact.id ? '' : fact.id)}
										>
											{editingFactId === fact.id ? 'Fermer' : 'Corriger'}
										</button>
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
										rows="4"
										class="mt-3 w-full resize-y rounded-xl border border-[#6b62f2]/40 bg-white px-3 py-2 text-sm leading-6 outline-none dark:bg-[#161616]"
										on:input={(event) =>
											dispatch('update', { id: fact.id, value: event.currentTarget.value })}
									></textarea>
								{:else}
									<p class="mt-3 text-sm leading-6 text-gray-700 dark:text-gray-200">
										{fact.value}
									</p>
								{/if}
								<div class="mt-3 flex flex-wrap gap-2 text-[11px] text-gray-400">
									<span>{sourceQualityLabel(fact, map.siteUrl)}</span>
									{#if fact.sourceUrl}
										<span>·</span>
										<span class="font-medium text-gray-500 dark:text-gray-300">
											{sourceDomain(fact.sourceUrl)}
										</span>
									{/if}
									<span>·</span>
									<span>Consulté le {fact.observedAt}</span>
									{#if fact.sourceUrl}
										<span>·</span>
										<a
											href={fact.sourceUrl}
											target="_blank"
											rel="noreferrer"
											class="max-w-full truncate text-[#5b52dd] hover:underline dark:text-[#aaa4ff]"
										>
											{fact.sourceTitle || fact.sourceUrl}
										</a>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</details>
			{/each}
		</div>
	</details>

	<div
		class="mx-auto mt-6 max-w-5xl rounded-[1.75rem] border border-amber-200 bg-amber-50 p-5 dark:border-amber-900/40 dark:bg-amber-950/20"
	>
		<div class="text-sm font-medium text-amber-900 dark:text-amber-200">
			Ce que le Web ne peut pas savoir
		</div>
		<p class="mt-2 text-sm leading-6 text-amber-800/80 dark:text-amber-100/70">
			Vos vrais résultats, processus internes, pertes, responsabilités, sources de vérité et limites
			d’autonomie. Luna vous posera seulement {questionCount} questions pour les apprendre.
		</p>
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
				<span class="font-medium">Ces conclusions décrivent correctement mon entreprise.</span>
				<span class="mt-0.5 block text-xs text-gray-500">
					Les autres preuves restent disponibles sans devenir automatiquement des vérités internes.
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
				disabled={!understandingConfirmed}
				on:click={() => dispatch('continue')}
			>
				Continuer avec {questionCount} questions utiles
			</button>
		</div>
	</div>
</section>
