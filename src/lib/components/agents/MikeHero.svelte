<script lang="ts">
	// Hero premium mettant en vedette Mike, le chef d'orchestre, en tête de la page Agents.
	// Réutilise les briques hero existantes (hero-modern/mesh/grain, btn-premium, ActiveBadge)
	// et les helpers d'avatar (avatarColor/initial). Couleur signature Or doré (cf. avatar-colors.ts).
	import { createEventDispatcher, getContext } from 'svelte';
	import type { AgentTemplate } from './templates';
	import { initial } from './utils';
	import { avatarColor } from './avatar-colors';
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let tpl: AgentTemplate;
	export let active = false;

	// Repli si le PNG n'est pas (encore) présent → jamais d'image cassée.
	let imgError = false;

	$: firstName = tpl.firstName ?? tpl.label.split(',')[0].trim();
	$: role =
		tpl.role ?? (tpl.label.includes(',') ? tpl.label.split(',').slice(1).join(',').trim() : '');
	$: showImage = !!tpl.image && !imgError;
</script>

<div
	class="relative mt-4 mb-11 overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20 min-h-[240px] sm:min-h-[320px]"
>
	<div
		class="pointer-events-none absolute -right-10 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full blur-3xl bg-amber-400/30 dark:bg-amber-500/20"
	></div>
	<div
		class="pointer-events-none absolute -left-16 -top-12 h-44 w-44 rounded-full blur-3xl bg-orange-300/30 dark:bg-orange-500/10"
	></div>
	<div class="hero-mesh pointer-events-none absolute inset-0"></div>
	<div class="hero-grain pointer-events-none absolute inset-0"></div>

	<!-- Portrait de Mike : déborde, ancré en bas -->
	{#if showImage}
		<!-- Desktop : grand, à droite, bord-à-bord en bas -->
		<img
			src={tpl.image}
			alt={firstName}
			on:error={() => (imgError = true)}
			class="hidden sm:block pointer-events-none absolute bottom-0 right-6 lg:right-14 z-10 h-full max-h-[360px] w-auto object-contain object-bottom drop-shadow-[0_18px_30px_rgba(0,0,0,0.28)]"
		/>
		<!-- Mobile : centré au-dessus du texte -->
		<img
			src={tpl.image}
			alt={firstName}
			on:error={() => (imgError = true)}
			class="sm:hidden mx-auto mt-6 h-40 w-auto object-contain drop-shadow-[0_14px_24px_rgba(0,0,0,0.25)]"
		/>
	{/if}

	<!-- Texte -->
	<div
		class="relative z-20 px-6 pb-7 pt-5 sm:px-9 sm:py-9 sm:pr-72 text-center sm:text-left flex flex-col justify-center min-h-[inherit]"
	>
		<div
			class="text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-700/90 dark:text-amber-300/90"
		>
			{role || $i18n.t('Chef d’orchestre')}
		</div>
		<div class="mt-1 flex items-center justify-center sm:justify-start gap-2.5">
			<h2 class="text-3xl sm:text-4xl font-semibold tracking-tight text-gray-900 dark:text-white">
				{firstName}
			</h2>
			{#if active}
				<ActiveBadge label={$i18n.t('Actif')} />
			{/if}
			{#if !showImage}
				<div
					class="ml-1 size-11 rounded-2xl flex items-center justify-center text-2xl text-white shadow-md ring-1 ring-white/50"
					style="background-image: {avatarColor('mike').gradient}"
				>
					{tpl.emoji || initial(firstName)}
				</div>
			{/if}
		</div>
		<p
			class="mt-2 text-[14px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md mx-auto sm:mx-0"
		>
			{tpl.description}
		</p>

		<div class="mt-5 flex flex-wrap items-center justify-center sm:justify-start gap-2.5">
			<button
				class="text-sm font-medium px-5 py-2.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black"
				on:click={() => dispatch('talk')}
			>
				{active ? $i18n.t('Continuer avec Mike') + ' →' : $i18n.t('Parler à Mike')}
			</button>
			<button
				class="text-sm font-medium px-5 py-2.5 rounded-xl bg-white/70 dark:bg-white/10 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 hover:bg-white dark:hover:bg-white/15 transition"
				on:click={() => dispatch('mission')}
			>
				{$i18n.t('Voir la mission')}
			</button>
		</div>
	</div>
</div>
