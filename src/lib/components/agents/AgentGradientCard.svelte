<script lang="ts">
	// Carte d'agent "bloc dégradé" façon Agensio : fond coloré + rôle/nom/description
	// + badge d'état + avatar (portrait détouré qui déborde, ou emoji en pastille givrée).
	// Réutilisée pour « Mes agents » et « Prêts à l'emploi ». Cf. Avatar.md.
	import { createEventDispatcher, getContext } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let gradient: string;
	export let role = '';
	export let name: string;
	export let description = '';
	export let image: string | null = null;
	export let avatarText = ''; // emoji ou initiale, affiché quand pas d'image
	export let status: 'active' | 'locked' | 'ready' | 'none' = 'none';
	export let statusLabel = '';
	export let primaryLabel = '';
	export let secondaryLabel = '';
	export let editable = false;

	let imgError = false;
	$: showImage = !!image && !imgError;
</script>

<div
	class="group relative flex flex-col overflow-hidden rounded-2xl p-5 min-h-[238px] text-white shadow-lg card-lift"
	style="background-image: {gradient}"
>
	<!-- lueur douce -->
	<div class="pointer-events-none absolute -right-8 -top-12 h-36 w-36 rounded-full bg-white/15 blur-2xl"></div>

	<!-- coin haut-droit : édition (au survol) + badge d'état -->
	<div class="absolute top-3.5 right-3.5 z-20 flex items-center gap-2">
		{#if editable}
			<button
				class="p-1 rounded-lg text-white/70 hover:text-white hover:bg-white/15 opacity-0 group-hover:opacity-100 focus:opacity-100 transition"
				title={$i18n.t('Modifier')}
				aria-label={$i18n.t('Modifier')}
				on:click={() => dispatch('edit')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
					<path
						d="M2.695 14.762l-1.262 3.155a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.886L17.5 5.501a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"
					/>
				</svg>
			</button>
		{/if}
		{#if status !== 'none'}
			<span
				class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10.5px] font-bold uppercase tracking-wide {status ===
				'active'
					? 'bg-white/95 text-emerald-700'
					: status === 'locked'
						? 'bg-black/25 text-white ring-1 ring-white/25'
						: 'bg-white/20 text-white ring-1 ring-white/30'}"
			>
				{#if status === 'active'}<span class="size-1.5 rounded-full bg-emerald-500 motion-safe:animate-pulse"></span>{/if}
				{statusLabel}
			</span>
		{/if}
	</div>

	<!-- Avatar : portrait détouré qui monte jusqu'en haut de la carte, ou emoji en pastille -->
	<div class="pointer-events-none absolute inset-y-0 right-0 z-0 w-[152px]">
		{#if showImage}
			<img
				src={image}
				alt={name}
				on:error={() => (imgError = true)}
				style="filter: drop-shadow(0 14px 20px rgba(0,0,0,0.38));"
				class="absolute bottom-0 right-0 h-full w-auto object-contain object-bottom"
			/>
		{:else}
			<div
				class="absolute bottom-4 right-3 size-[76px] rounded-full flex items-center justify-center text-4xl bg-white/15 backdrop-blur-sm ring-1 ring-white/25 shadow-inner"
			>
				{avatarText}
			</div>
		{/if}
	</div>

	<!-- Texte (marge droite pour dégager l'avatar) -->
	<div class="relative z-10 pr-36">
		{#if role}
			<div class="text-[11px] font-semibold uppercase tracking-[0.12em] text-white/75">{role}</div>
		{/if}
		<h3 class="text-lg font-bold tracking-tight mt-0.5 truncate">{name}</h3>
		{#if description}
			<p class="text-[12.5px] leading-snug text-white/85 mt-1.5 line-clamp-3">{description}</p>
		{/if}
	</div>

	<!-- Actions -->
	{#if primaryLabel || secondaryLabel}
		<div class="relative z-10 mt-auto flex items-center gap-3 pt-4 pr-36">
			{#if primaryLabel}
				<button
					class="text-[13px] font-semibold px-4 py-2 rounded-xl bg-white text-gray-900 shadow-sm hover:shadow-md hover:-translate-y-px active:translate-y-0 transition-all whitespace-nowrap"
					on:click={() => dispatch('primary')}
				>
					{primaryLabel}
				</button>
			{/if}
			{#if secondaryLabel}
				<button
					class="text-[12px] font-medium text-white/85 hover:text-white underline-offset-2 hover:underline transition whitespace-nowrap"
					on:click={() => dispatch('secondary')}
				>
					{secondaryLabel}
				</button>
			{/if}
		</div>
	{/if}
</div>
