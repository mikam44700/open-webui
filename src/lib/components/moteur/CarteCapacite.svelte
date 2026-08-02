<script context="module" lang="ts">
	export type Capacite = {
		id: string;
		titre: string;
		description?: string;
		detail?: string;
		actif?: boolean;
		connecte?: boolean;
		disponible?: boolean;
		logo?: string | null;
		categorie?: string;
	};
</script>

<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import {
		initiales,
		LOGO_PAR_DEFAUT,
		urlLogoCapacite,
		type FamilleLogo
	} from './logos';

	export let capacite: Capacite;
	export let famille: FamilleLogo = 'outil';
	export let actionLabel = '';
	export let basculable = false;
	export let enCours = false;
	export let secondaire = '';

	const dispatch = createEventDispatcher<{
		action: Capacite;
		toggle: { capacite: Capacite; actif: boolean };
		secondary: Capacite;
	}>();

	$: logo = capacite.logo ?? urlLogoCapacite(famille, capacite.id, capacite.titre);
	$: etatActif = capacite.connecte ?? capacite.actif ?? false;

	const imageEnErreur = (event: Event) => {
		const image = event.currentTarget as HTMLImageElement;
		if (!image.src.endsWith('api.svg')) image.src = LOGO_PAR_DEFAUT;
	};
</script>

<article
	class="card-lift flex min-h-32 flex-col rounded-2xl border border-gray-100 bg-white p-4 dark:border-gray-850 dark:bg-gray-900"
>
	<div class="flex min-w-0 items-start gap-3">
		<div
			class="flex size-11 flex-none items-center justify-center overflow-hidden rounded-xl border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-850"
		>
			{#if logo}
				<img
					src={logo}
					alt=""
					class="size-full object-contain p-1.5"
					draggable="false"
					on:error={imageEnErreur}
				/>
			{:else}
				<span class="text-xs font-semibold text-gray-400">{initiales(capacite.titre)}</span>
			{/if}
		</div>

		<div class="min-w-0 flex-1">
			<div class="flex items-start justify-between gap-2">
				<h3 class="truncate text-sm font-medium text-gray-900 dark:text-gray-50">
					{capacite.titre}
				</h3>
				{#if enCours}
					<Spinner className="size-4" />
				{:else if basculable}
					<Switch
						state={Boolean(capacite.actif)}
						ariaLabel={`${capacite.actif ? 'Désactiver' : 'Activer'} ${capacite.titre}`}
						on:change={() =>
							dispatch('toggle', { capacite, actif: !Boolean(capacite.actif) })}
					/>
				{:else if etatActif}
					<span
						class="inline-flex flex-none items-center gap-1.5 whitespace-nowrap text-xs font-medium text-emerald-600 dark:text-emerald-400"
					>
						<span class="size-1.5 rounded-full bg-emerald-500"></span>
						Connecté
					</span>
				{:else if capacite.disponible === false}
					<span class="flex-none text-xs text-gray-400">Bientôt</span>
				{/if}
			</div>

			{#if capacite.description}
				<p class="mt-1 line-clamp-2 text-pretty text-xs leading-relaxed text-gray-500 dark:text-gray-400">
					{capacite.description}
				</p>
			{/if}
			{#if capacite.detail}
				<p class="mt-1 text-pretty text-[11px] text-gray-400 dark:text-gray-500">
					{capacite.detail}
				</p>
			{/if}
		</div>
	</div>

	{#if actionLabel || secondaire}
		<div class="mt-auto flex items-center gap-2 pt-4">
			{#if actionLabel}
				<button
					type="button"
					disabled={capacite.disponible === false || enCours}
					class="btn-premium rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-gray-900"
					on:click={() => dispatch('action', capacite)}
				>
					{actionLabel}
				</button>
			{/if}
			{#if secondaire}
				<button
					type="button"
					disabled={enCours}
					class="rounded-lg px-2.5 py-1.5 text-xs text-gray-500 transition-colors duration-150 hover:bg-gray-100 hover:text-gray-800 disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-gray-100"
					on:click={() => dispatch('secondary', capacite)}
				>
					{secondaire}
				</button>
			{/if}
		</div>
	{/if}
</article>
