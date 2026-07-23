<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { GOAL_CATALOG, safeId } from '$lib/onboarding-agentos/logic';
	import type { BusinessGoal } from '$lib/onboarding-agentos/types';

	export let goals: BusinessGoal[] = [];

	let selectedGoals: BusinessGoal[] = [...goals];
	let selectedGoalIds: string[] = [];
	let customGoal = '';
	let error = '';

	$: selectedGoalIds = selectedGoals.map((goal) => goal.id);

	const dispatch = createEventDispatcher<{
		back: void;
		continue: { goals: BusinessGoal[] };
	}>();

	const isSelected = (id: string) => selectedGoals.some((goal) => goal.id === id);

	const toggleGoal = (goal: BusinessGoal) => {
		error = '';
		if (isSelected(goal.id)) {
			selectedGoals = selectedGoals.filter((item) => item.id !== goal.id);
			return;
		}
		if (selectedGoals.length >= 3) {
			error = 'Choisissez trois résultats maximum pour que Luna reste concentrée.';
			return;
		}
		selectedGoals = [...selectedGoals, goal];
	};

	const addCustomGoal = () => {
		const label = customGoal.trim();
		if (!label) return;
		if (selectedGoals.length >= 3) {
			error = 'Retirez un résultat avant d’ajouter votre objectif personnalisé.';
			return;
		}
		selectedGoals = [
			...selectedGoals,
			{
				id: `objectif-personnalise-${safeId(label)}`,
				outcomeId: 'personnalise',
				label,
				detail: 'Objectif formulé par l’entreprise.'
			}
		];
		customGoal = '';
		error = '';
	};

	const continueWithGoals = () => {
		if (!selectedGoals.length) {
			error = 'Choisissez au moins un résultat à améliorer.';
			return;
		}
		dispatch('continue', { goals: selectedGoals });
	};
</script>

<section class="m-auto w-full max-w-5xl py-8">
	<div class="text-center">
		<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
			Étape 2 · Vos priorités
		</div>
		<h1 class="mt-4 text-3xl font-medium tracking-[-0.035em] md:text-5xl">
			Que doit améliorer Luna en premier ?
		</h1>
		<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
			Choisissez un à trois résultats pour les 90 prochains jours. Luna utilisera ces priorités
			pour distinguer les informations utiles du simple bruit.
		</p>
	</div>

	<div class="mt-9 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
		{#each GOAL_CATALOG as goal}
			<button
				type="button"
				aria-pressed={selectedGoalIds.includes(goal.id)}
				class="min-h-32 rounded-[1.5rem] border p-5 text-left transition {selectedGoalIds.includes(
					goal.id
				)
					? 'border-[#6b62f2] bg-[#6b62f2]/8 ring-2 ring-[#6b62f2]/10'
					: 'border-black/6 bg-white hover:border-[#6b62f2]/35 dark:border-white/8 dark:bg-[#161616]'}"
				on:click={() => toggleGoal(goal)}
			>
				<div class="flex items-start justify-between gap-3">
					<div class="text-base font-medium">{goal.label}</div>
					<div
						class="flex size-6 shrink-0 items-center justify-center rounded-full border {selectedGoalIds.includes(
							goal.id
						)
							? 'border-[#6b62f2] bg-[#6b62f2] text-white'
							: 'border-gray-300 text-transparent dark:border-gray-700'}"
					>
						✓
					</div>
				</div>
				<div class="mt-3 text-xs leading-5 text-gray-500 dark:text-gray-400">{goal.detail}</div>
			</button>
		{/each}
	</div>

	<div
		class="mt-4 rounded-[1.5rem] border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616]"
	>
		<label for="custom-goal" class="text-sm font-medium">Un autre résultat important ?</label>
		<div class="mt-3 flex flex-col gap-2 sm:flex-row">
			<input
				id="custom-goal"
				bind:value={customGoal}
				placeholder="Écrivez votre objectif avec vos mots"
				class="min-w-0 flex-1 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm outline-none focus:border-[#6b62f2] dark:border-gray-800 dark:bg-[#101010]"
				on:keydown={(event) => event.key === 'Enter' && addCustomGoal()}
			/>
			<button
				type="button"
				class="rounded-2xl border border-gray-200 px-5 py-3 text-sm font-medium hover:border-[#6b62f2] dark:border-gray-700"
				on:click={addCustomGoal}>Ajouter</button
			>
		</div>
	</div>

	<div class="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<div class="text-sm font-medium">{selectedGoals.length}/3 résultat(s) choisi(s)</div>
			{#if error}<div class="mt-1 text-xs text-red-500">{error}</div>{/if}
		</div>
		<div class="flex gap-2">
			<button
				type="button"
				class="rounded-full px-4 py-2.5 text-sm text-gray-500 hover:bg-black/5 dark:hover:bg-white/5"
				on:click={() => dispatch('back')}>Retour</button
			>
			<button
				type="button"
				class="rounded-full bg-[#6b62f2] px-6 py-2.5 text-sm font-medium text-white disabled:opacity-40"
				disabled={!selectedGoals.length}
				on:click={continueWithGoals}>Continuer vers mon entreprise</button
			>
		</div>
	</div>
</section>
