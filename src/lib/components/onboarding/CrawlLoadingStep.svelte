<script lang="ts">
	// Page de chargement DÉDIÉE (étape à part entière du parcours) : s'affiche entre « coller l'URL »
	// et « le résultat ». Le crawl + la synthèse prennent ~15 s ; ici le dirigeant voit l'IA travailler
	// (gros cercle animé + étapes qui se cochent + rassurance), impossible à rater. Le parent pilote
	// `phase` (reading → thinking) au fil du traitement.
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let phase: 'reading' | 'thinking' = 'reading';
</script>

<div class="min-h-[80vh] w-full flex items-center justify-center p-4 sm:p-8">
	<div
		class="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20"
	>
		<div class="hero-mesh pointer-events-none absolute inset-0"></div>
		<div class="hero-grain pointer-events-none absolute inset-0"></div>

		<div
			class="relative z-20 px-6 py-12 sm:px-10 sm:py-16 flex flex-col text-center items-center min-h-[440px] justify-center"
		>
			<div class="loader-ring" aria-hidden="true"></div>

			<h1 class="mt-7 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
				{phase === 'reading' ? $i18n.t('Je lis votre site…') : $i18n.t('J’analyse votre entreprise…')}
			</h1>
			<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md">
				{$i18n.t(
					'Cela prend une quinzaine de secondes — je parcours vos pages pour comprendre votre offre, votre ton et votre clientèle. Restez là, j’y suis presque.'
				)}
			</p>

			<!-- Étapes qui se cochent au fil de l'eau -->
			<div class="mt-8 w-full max-w-sm flex flex-col gap-2.5 text-left">
				<div
					class="flex items-center gap-3 rounded-xl ring-1 ring-inset ring-amber-500/20 bg-white/60 dark:bg-black/20 px-4 py-3"
				>
					{#if phase === 'thinking'}
						<span
							class="flex-none h-5 w-5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-xs font-bold"
							>✓</span
						>
					{:else}
						<span class="loader-dot flex-none" aria-hidden="true"></span>
					{/if}
					<span class="text-sm text-gray-800 dark:text-gray-100">{$i18n.t('Lecture de votre site')}</span>
				</div>
				<div
					class="flex items-center gap-3 rounded-xl ring-1 ring-inset px-4 py-3 transition {phase === 'thinking'
						? 'ring-amber-500/20 bg-white/60 dark:bg-black/20'
						: 'ring-transparent opacity-50'}"
				>
					{#if phase === 'thinking'}
						<span class="loader-dot flex-none" aria-hidden="true"></span>
					{:else}
						<span class="flex-none h-5 w-5 rounded-full border border-gray-300 dark:border-gray-600"></span>
					{/if}
					<span
						class="text-sm {phase === 'thinking'
							? 'text-gray-800 dark:text-gray-100'
							: 'text-gray-400 dark:text-gray-500'}"
						>{$i18n.t('Analyse de l’offre, du ton et de la clientèle')}</span
					>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	/* Gros cercle de chargement (l'IA travaille sous les yeux du dirigeant). */
	.loader-ring {
		height: 76px;
		width: 76px;
		border-radius: 9999px;
		border: 4px solid rgba(240, 178, 62, 0.22);
		border-top-color: rgba(240, 178, 62, 0.95);
		animation: loader-spin 0.9s linear infinite;
	}
	/* Petit spinner d'étape (en cours). */
	.loader-dot {
		height: 1.25rem;
		width: 1.25rem;
		border-radius: 9999px;
		border: 2px solid rgba(240, 178, 62, 0.25);
		border-top-color: rgba(240, 178, 62, 0.9);
		animation: loader-spin 0.8s linear infinite;
	}
	@keyframes loader-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.loader-ring,
		.loader-dot {
			animation-duration: 2.4s;
		}
	}
</style>
