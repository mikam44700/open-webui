<script lang="ts">
	// Carte d'agent "bloc dégradé" façon Agensio : fond coloré + rôle/nom/description
	// + badge d'état + avatar (portrait détouré qui déborde, ou emoji en pastille givrée).
	// Réutilisée pour « Mes agents » et « Prêts à l'emploi ». Cf. Avatar.md.
	import { createEventDispatcher, getContext } from 'svelte';
	import { webpUrl } from '$lib/components/agents/avatars';

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
	export let removable = false; // « Retirer de mon équipe » (renvoie au catalogue)
	export let onLight = false; // fond clair -> texte foncé (contraste)

	let imgError = false;
	$: showImage = !!image && !imgError;

	let menuOpen = false; // menu d'actions (⋮) — évite de poser des icônes sur l'avatar

	// Couleurs de texte selon la clarté du fond.
	$: ink = onLight ? 'text-gray-900' : 'text-white';
	$: eyebrowCls = onLight ? 'text-gray-900/60' : 'text-white/75';
	$: descCls = onLight ? 'text-gray-900/70' : 'text-white/85';
	$: menuBtnCls = onLight
		? 'text-gray-900/70 hover:text-gray-900 hover:bg-black/10'
		: 'text-white/80 hover:text-white hover:bg-white/20';
	$: menuBtnOpenBg = onLight ? 'bg-black/10' : 'bg-white/20';
	$: primaryBtnCls = onLight ? 'bg-gray-900 text-white' : 'bg-white text-gray-900';
	$: secondaryBtnCls = onLight
		? 'text-gray-900/70 hover:text-gray-900'
		: 'text-white/85 hover:text-white';
	$: dotRingCls = onLight ? 'ring-black/25' : 'ring-white/40';
</script>

<div
	class="group relative flex flex-col overflow-hidden rounded-2xl p-5 min-h-[238px] {ink} shadow-lg card-lift"
	style="background-image: {gradient}"
	on:mouseleave={() => (menuOpen = false)}
	role="presentation"
>
	<!-- lueur douce -->
	<div class="pointer-events-none absolute -right-8 -top-12 h-36 w-36 rounded-full bg-white/15 blur-2xl"></div>

	<!-- coin haut-droit : menu d'actions (⋮) seul — l'état actif est un point vert en haut à gauche -->
	<div class="absolute top-3.5 right-3.5 z-30 flex items-center gap-2">
		{#if editable || removable}
			<div class="relative">
				<button
					class="p-1 rounded-lg {menuBtnCls} opacity-0 group-hover:opacity-100 focus:opacity-100 transition {menuOpen
						? 'opacity-100 ' + menuBtnOpenBg
						: ''}"
					title={$i18n.t('Options')}
					aria-label={$i18n.t('Options')}
					aria-haspopup="menu"
					aria-expanded={menuOpen}
					on:click|stopPropagation={() => (menuOpen = !menuOpen)}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
						<path
							d="M10 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm0 5.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm0 5.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z"
						/>
					</svg>
				</button>

				{#if menuOpen}
					<div
						class="absolute right-0 top-full mt-1 z-50 min-w-[172px] rounded-xl bg-white dark:bg-gray-900 shadow-xl ring-1 ring-black/5 dark:ring-white/10 py-1 text-gray-700 dark:text-gray-200"
						role="menu"
					>
						{#if editable}
							<button
								class="w-full flex items-center gap-2.5 px-3.5 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								role="menuitem"
								on:click|stopPropagation={() => {
									menuOpen = false;
									dispatch('edit');
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-4 text-gray-400"
								>
									<path
										d="M2.695 14.762l-1.262 3.155a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.886L17.5 5.501a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"
									/>
								</svg>
								{$i18n.t('Modifier')}
							</button>
						{/if}
						{#if removable}
							<button
								class="w-full flex items-center gap-2.5 px-3.5 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition"
								role="menuitem"
								on:click|stopPropagation={() => {
									menuOpen = false;
									dispatch('remove');
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-4"
								>
									<path
										fill-rule="evenodd"
										d="M8.75 1a1 1 0 0 0-.96.725L7.42 3H4a1 1 0 0 0 0 2v9a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V5a1 1 0 1 0 0-2h-3.42l-.37-1.275A1 1 0 0 0 11.25 1h-2.5ZM7.5 7a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0v-5.5A.75.75 0 0 1 7.5 7Zm5 0a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0v-5.5A.75.75 0 0 1 12.5 7Z"
										clip-rule="evenodd"
									/>
								</svg>
								{$i18n.t('Retirer de mon équipe')}
							</button>
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Avatar : portrait détouré qui monte jusqu'en haut de la carte, ou emoji en pastille -->
	<div class="pointer-events-none absolute inset-y-0 right-0 z-0 w-[152px]">
		{#if showImage}
			<img
				src={webpUrl(image)}
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
		{#if role || status === 'active'}
			<div
				class="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] {eyebrowCls}"
			>
				{#if status === 'active'}
					<span class="relative flex size-2" title={$i18n.t('Actif')} aria-label={$i18n.t('Actif')}>
						<span
							class="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-80 motion-safe:animate-ping"
						></span>
						<span
							class="relative inline-flex size-2 rounded-full bg-emerald-400 ring-2 {dotRingCls}"
						></span>
					</span>
				{/if}
				{#if role}<span>{role}</span>{/if}
			</div>
		{/if}
		<h3 class="text-lg font-bold tracking-tight mt-0.5 truncate">{name}</h3>
		{#if description}
			<p class="text-[12.5px] leading-snug {descCls} mt-1.5 line-clamp-3">{description}</p>
		{/if}
	</div>

	<!-- Actions -->
	{#if primaryLabel || secondaryLabel}
		<div class="relative z-10 mt-auto flex items-center gap-3 pt-4 pr-36">
			{#if primaryLabel}
				<button
					class="text-[13px] font-semibold px-4 py-2 rounded-xl {primaryBtnCls} shadow-sm hover:shadow-md hover:-translate-y-px active:translate-y-0 transition-all whitespace-nowrap"
					on:click={() => dispatch('primary')}
				>
					{primaryLabel}
				</button>
			{/if}
			{#if secondaryLabel}
				<button
					class="text-[12px] font-medium {secondaryBtnCls} underline-offset-2 hover:underline transition whitespace-nowrap"
					on:click={() => dispatch('secondary')}
				>
					{secondaryLabel}
				</button>
			{/if}
		</div>
	{/if}
</div>
