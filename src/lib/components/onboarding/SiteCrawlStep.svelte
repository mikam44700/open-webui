<script lang="ts">
	// Étape « Collez l'URL de votre site » : SAISIE uniquement. Au clic « Analyser », on délègue au
	// parent (OnboardingFlow) qui bascule sur une PAGE DE CHARGEMENT dédiée puis lance crawl + synthèse.
	// Ce découplage garantit que le dirigeant voit toujours l'écran de chargement (impossible à rater).
	// État TOUJOURS honnête : si le parent renvoie une erreur, on repropose la saisie ou le manuel.
	import { createEventDispatcher, getContext } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Vrai si un contexte a DÉJÀ été produit (retour arrière) : on propose de continuer sans refaire.
	export let hasContext = false;
	// Message d'erreur remonté par le parent (crawl/synthèse échoué) — vide si tout va bien.
	export let error = '';

	let url = '';
	let reanalyze = false; // le dirigeant veut refaire l'analyse malgré un contexte existant

	// Écran « déjà analysé » : contexte présent, pas de ré-analyse demandée, pas d'erreur en cours.
	$: showDone = hasContext && !reanalyze && !error;

	// Ajoute https:// si le dirigeant tape « monsite.fr » sans schéma.
	const normalizeUrl = (raw: string): string => {
		const s = raw.trim();
		if (!s) return '';
		return /^https?:\/\//i.test(s) ? s : `https://${s}`;
	};

	const submit = () => {
		const target = normalizeUrl(url);
		if (!target) return;
		dispatch('analyze', { url: target });
	};
</script>

<div class="min-h-[80vh] w-full flex items-center justify-center p-4 sm:p-8">
	<div
		class="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20"
	>
		<div class="hero-mesh pointer-events-none absolute inset-0"></div>
		<div class="hero-grain pointer-events-none absolute inset-0"></div>

		<div
			class="relative z-20 px-6 py-10 sm:px-10 sm:py-12 flex flex-col text-center items-center min-h-[420px] justify-center"
		>
			{#if showDone}
				<!-- DÉJÀ ANALYSÉ (retour arrière) : on ne refait pas le crawl, on propose de continuer. -->
				<div
					class="h-16 w-16 rounded-full flex items-center justify-center text-2xl text-white bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-[0_0_36px_-6px_rgba(16,185,129,0.5)]"
				>
					✓
				</div>
				<h1 class="mt-5 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
					{$i18n.t('Votre site a déjà été analysé')}
				</h1>
				<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md">
					{$i18n.t('On peut continuer — ou ré-analyser votre site s’il a changé.')}
				</p>
				<button
					type="button"
					class="mt-7 text-sm font-semibold px-7 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950"
					on:click={() => dispatch('continue')}
				>
					{$i18n.t('Continuer')} →
				</button>
				<button
					type="button"
					class="mt-4 text-sm font-medium text-gray-600 dark:text-gray-300 hover:underline"
					on:click={() => (reanalyze = true)}
				>
					{$i18n.t('Ré-analyser mon site')}
				</button>
			{:else}
				<!-- FORMULAIRE : saisie de l'URL. -->
				<div
					class="text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-700/90 dark:text-amber-300/90"
				>
					{$i18n.t('Apprenons à connaître votre entreprise')}
				</div>
				<h1 class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
					{$i18n.t('Collez l’adresse de votre site')}
				</h1>
				<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md">
					{$i18n.t(
						'Je le lis en quelques secondes pour comprendre votre offre, votre ton et votre clientèle — vous validerez ensuite.'
					)}
				</p>

				<form class="mt-7 w-full max-w-md" on:submit|preventDefault={submit}>
					<div class="flex items-center gap-2">
						<input
							type="text"
							inputmode="url"
							bind:value={url}
							placeholder="https://mon-entreprise.fr"
							class="flex-1 px-4 py-3 rounded-xl bg-white/80 dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
						/>
						<button
							type="submit"
							disabled={!url.trim()}
							class="text-sm font-semibold px-5 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 disabled:opacity-50"
						>
							{$i18n.t('Analyser')}
						</button>
					</div>
				</form>

				{#if error}
					<div
						class="mt-6 w-full max-w-md text-left text-sm rounded-xl bg-white/70 dark:bg-white/5 ring-1 ring-inset ring-gray-900/10 dark:ring-white/10 px-4 py-3 text-gray-700 dark:text-gray-200"
					>
						<p>{error}</p>
						<p class="mt-2 text-[13px] text-gray-500 dark:text-gray-400">
							{$i18n.t('Pas de souci — on peut saisir votre contexte à la main.')}
						</p>
						<button
							class="mt-3 text-sm font-medium px-4 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black"
							on:click={() => dispatch('manual')}
						>
							{$i18n.t('Saisir manuellement')}
						</button>
					</div>
				{/if}

				<button
					class="mt-8 text-sm font-medium text-gray-600 dark:text-gray-300 hover:underline"
					on:click={() => dispatch('manual')}
				>
					{$i18n.t('Je préfère saisir moi-même')}
				</button>
			{/if}
		</div>
	</div>
</div>
