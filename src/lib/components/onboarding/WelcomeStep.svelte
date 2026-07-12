<script lang="ts">
	// Étape 0 de l'onboarding : accueil « Bienvenue sur LunarIA » par Mike.
	// Réutilise le langage visuel de MikeHero (couleur signature Or doré, portrait mike.webp,
	// briques premium hero-modern/mesh/grain, btn-premium). Non bloquant : « Plus tard » possible.
	import { createEventDispatcher, getContext } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let imgError = false;
	const mikeImage = '/assets/agents/mike.webp';
</script>

<div class="min-h-[80vh] w-full flex items-center justify-center p-4 sm:p-8">
	<div
		class="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20"
	>
		<div
			class="pointer-events-none absolute -right-10 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full blur-3xl bg-amber-400/30 dark:bg-amber-500/20"
		></div>
		<div
			class="pointer-events-none absolute -left-16 -top-12 h-44 w-44 rounded-full blur-3xl bg-orange-300/30 dark:bg-orange-500/10"
		></div>
		<div class="hero-mesh pointer-events-none absolute inset-0"></div>
		<div class="hero-grain pointer-events-none absolute inset-0"></div>

		<div class="relative z-20 px-6 py-10 sm:px-10 sm:py-12 flex flex-col items-center text-center">
			{#if !imgError}
				<img
					src={mikeImage}
					alt="Mike"
					on:error={() => (imgError = true)}
					class="h-28 sm:h-36 w-auto object-contain drop-shadow-[0_14px_24px_rgba(0,0,0,0.25)]"
				/>
			{/if}

			<div
				class="mt-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-700/90 dark:text-amber-300/90"
			>
				{$i18n.t('Bienvenue sur LunarIA')}
			</div>
			<h1 class="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight text-gray-900 dark:text-white">
				{$i18n.t('Bonjour, je suis Mike')}
			</h1>
			<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md">
				{$i18n.t(
					'Votre chef d’orchestre. Je suis là pour vous accompagner : en quelques minutes, on va apprendre à connaître votre entreprise pour que votre équipe d’agents travaille vraiment pour vous.'
				)}
			</p>

			<div class="mt-8 flex flex-col items-center gap-3">
				<button
					class="text-sm font-semibold px-7 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950"
					on:click={() => dispatch('next')}
				>
					{$i18n.t('C’est parti')} →
				</button>
				<span class="text-[13px] text-gray-500 dark:text-gray-400">
					{$i18n.t('≈ 2 minutes · vous pouvez tout modifier plus tard')}
				</span>
			</div>
		</div>
	</div>
</div>
