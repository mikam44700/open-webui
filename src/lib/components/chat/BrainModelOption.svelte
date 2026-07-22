<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let model: {
		id: string;
		label: string;
		available?: boolean;
		unavailable_reason?: string | null;
	};
	export let active = false;
	export let recommended = false;

	// Modèle présent au catalogue mais refusé par l'abonnement de la clé (ex. Kimi
	// HighSpeed hors forfait Allegretto) : grisé, non cliquable, raison affichée.
	$: verrouille = model.available === false;

	const dispatch = createEventDispatcher<{ select: { id: string } }>();
</script>

<button
	type="button"
	role="menuitemradio"
	aria-checked={active}
	aria-disabled={verrouille}
	disabled={verrouille}
	title={verrouille && model.unavailable_reason
		? `Réservé aux forfaits supérieurs (${model.unavailable_reason})`
		: undefined}
	class="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left transition {verrouille
		? 'cursor-not-allowed'
		: active
			? 'bg-gray-100 dark:bg-gray-800'
			: 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
	on:click={() => {
		if (!verrouille) dispatch('select', { id: model.id });
	}}
>
	<span class="flex min-w-0 items-center gap-1.5">
		<span
			class="truncate text-sm {verrouille
				? 'text-gray-400 dark:text-gray-500'
				: 'text-gray-900 dark:text-white'}">{model.label}</span
		>
		{#if recommended}
			<span
				class="shrink-0 rounded-full bg-gray-100 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-gray-500 dark:bg-gray-800 dark:text-gray-400"
				>Recommandé</span
			>
		{/if}
		{#if verrouille && model.unavailable_reason}
			<span
				class="shrink-0 rounded-full bg-amber-50 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-amber-600 dark:bg-amber-500/10 dark:text-amber-400"
				>{model.unavailable_reason}</span
			>
		{/if}
	</span>
	{#if active}
		<svg class="size-4 shrink-0 text-gray-900 dark:text-white" viewBox="0 0 20 20" fill="currentColor"
			><path
				fill-rule="evenodd"
				d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0l-3.5-3.5a1 1 0 111.4-1.4l2.8 2.79 6.8-6.79a1 1 0 011.4 0z"
				clip-rule="evenodd"
			/></svg
		>
	{/if}
</button>
