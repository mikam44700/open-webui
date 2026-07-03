<script lang="ts">
	// Hero premium mettant en vedette Mike, le chef d'orchestre, en tête de la page Agents.
	// Réutilise les briques hero existantes (hero-modern/mesh/grain, btn-premium, ActiveBadge)
	// et les helpers d'avatar (gradientFor/initial). Cf. Avatar.md.
	import { createEventDispatcher, getContext } from 'svelte';
	import type { AgentTemplate } from './templates';
	import { gradientFor, initial } from './utils';
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
	class="relative mt-4 mb-11 overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 from-indigo-200/70 via-violet-100/50 to-purple-100/60 dark:from-indigo-900/30 dark:via-violet-900/20 dark:to-purple-900/20"
>
	<div
		class="pointer-events-none absolute -right-10 top-1/2 h-48 w-48 -translate-y-1/2 rounded-full blur-3xl bg-indigo-400/30 dark:bg-indigo-500/20"
	></div>
	<div
		class="pointer-events-none absolute -left-16 -top-12 h-44 w-44 rounded-full blur-3xl bg-violet-300/30 dark:bg-violet-500/10"
	></div>
	<div class="hero-mesh pointer-events-none absolute inset-0"></div>
	<div class="hero-grain pointer-events-none absolute inset-0"></div>

	<div class="relative flex flex-col sm:flex-row items-center gap-6 px-6 py-7 sm:px-9 sm:py-8">
		<!-- Portrait -->
		<div class="flex-none order-first sm:order-last">
			<div class="relative">
				{#if showImage}
					<img
						src={tpl.image}
						alt={firstName}
						on:error={() => (imgError = true)}
						class="size-24 sm:size-28 rounded-3xl object-cover bg-white/60 dark:bg-white/10 shadow-xl ring-1 ring-white/60 dark:ring-white/15"
					/>
				{:else}
					<div
						class="size-24 sm:size-28 rounded-3xl flex items-center justify-center text-4xl text-white shadow-xl ring-1 ring-white/60 dark:ring-white/15"
						style="background-image: {gradientFor(tpl.id)}"
					>
						{tpl.emoji || initial(firstName)}
					</div>
				{/if}
				{#if active}
					<span
						class="absolute -bottom-1.5 -right-1.5 size-5 rounded-full bg-green-500 border-[3px] border-white dark:border-gray-900 shadow"
					></span>
				{/if}
			</div>
		</div>

		<!-- Texte -->
		<div class="flex-1 min-w-0 text-center sm:text-left">
			<div
				class="text-[11px] font-semibold uppercase tracking-[0.14em] text-indigo-500/90 dark:text-indigo-300/90"
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
			</div>
			<p
				class="mt-2 text-[14px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-xl mx-auto sm:mx-0"
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
</div>
