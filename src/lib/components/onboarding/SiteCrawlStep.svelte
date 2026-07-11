<script lang="ts">
	// Étape 1 de l'onboarding : « Colle l'URL de ton site » → lecture (Crawl4AI) + synthèse (modèle
	// actif) → offre/ton/clientèle/services. Victoire + capture de contexte en un geste. État TOUJOURS
	// honnête (réussi/partiel/échec, jamais « compris » non vérifié) ; repli si pas de bon site.
	import { createEventDispatcher, getContext } from 'svelte';
	import { crawlSite, synthesizeContext, type CrawlResult } from '$lib/apis/onboarding';
	import { isContextEmpty, type CompanyContext } from '$lib/onboarding/companySynthesis';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Modèle actif (résolu par le parent) : nécessaire à la synthèse. Vide → on lit quand même le
	// site mais on bascule sur la saisie manuelle.
	export let model = '';

	type Phase = 'idle' | 'reading' | 'thinking' | 'error';
	let phase: Phase = 'idle';
	let url = '';
	let errorMessage = '';

	// Ajoute https:// si le dirigeant tape « monsite.fr » sans schéma.
	const normalizeUrl = (raw: string): string => {
		const s = raw.trim();
		if (!s) return '';
		return /^https?:\/\//i.test(s) ? s : `https://${s}`;
	};

	const run = async () => {
		const target = normalizeUrl(url);
		if (!target) return;
		errorMessage = '';
		phase = 'reading';

		const crawl: CrawlResult = await crawlSite(localStorage.token, target);
		if (crawl.status === 'echec' || !crawl.markdown.trim()) {
			errorMessage = crawl.message || $i18n.t('Le site n’a pas pu être lu.');
			phase = 'error';
			return;
		}

		phase = 'thinking';
		const context: CompanyContext = await synthesizeContext(
			localStorage.token,
			model,
			crawl.markdown
		);

		if (isContextEmpty(context)) {
			// Site lu mais rien d'exploitable (ou pas de modèle) : on n'invente pas, on passe en manuel.
			errorMessage = $i18n.t(
				'J’ai lu le site mais je n’en ai pas tiré assez d’éléments fiables. On peut les saisir ensemble.'
			);
			phase = 'error';
			return;
		}

		// Le parent enchaîne sur la relecture/validation avec ce contexte + le statut honnête du crawl.
		dispatch('synthesized', { context, crawl });
	};

	const busy = () => phase === 'reading' || phase === 'thinking';
</script>

<div class="min-h-[80vh] w-full flex items-center justify-center p-4 sm:p-8">
	<div
		class="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20"
	>
		<div class="hero-mesh pointer-events-none absolute inset-0"></div>
		<div class="hero-grain pointer-events-none absolute inset-0"></div>

		<div class="relative z-20 px-6 py-10 sm:px-10 sm:py-12 flex flex-col text-center items-center">
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

			<form class="mt-7 w-full max-w-md" on:submit|preventDefault={run}>
				<div class="flex items-center gap-2">
					<input
						type="text"
						inputmode="url"
						bind:value={url}
						disabled={busy()}
						placeholder="https://mon-entreprise.fr"
						class="flex-1 px-4 py-3 rounded-xl bg-white/80 dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60 disabled:opacity-60"
					/>
					<button
						type="submit"
						disabled={busy() || !url.trim()}
						class="text-sm font-medium px-5 py-3 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
					>
						{$i18n.t('Analyser')}
					</button>
				</div>
			</form>

			{#if busy()}
				<div class="mt-6 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
					<span
						class="h-4 w-4 rounded-full border-2 border-amber-500/70 border-t-transparent animate-spin"
					></span>
					{phase === 'reading' ? $i18n.t('Je lis votre site…') : $i18n.t('Je résume ce que j’ai compris…')}
				</div>
			{/if}

			{#if phase === 'error'}
				<div
					class="mt-6 w-full max-w-md text-left text-sm rounded-xl bg-white/70 dark:bg-white/5 ring-1 ring-inset ring-gray-900/10 dark:ring-white/10 px-4 py-3 text-gray-700 dark:text-gray-200"
				>
					<p>{errorMessage}</p>
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

			<div class="mt-8 flex flex-wrap items-center justify-center gap-3">
				<button
					class="text-sm font-medium text-gray-600 dark:text-gray-300 hover:underline"
					on:click={() => dispatch('manual')}
				>
					{$i18n.t('Je préfère saisir moi-même')}
				</button>
				<span class="text-gray-300 dark:text-gray-600">·</span>
				<button
					class="text-sm font-medium text-gray-500 dark:text-gray-400 hover:underline"
					on:click={() => dispatch('skip')}
				>
					{$i18n.t('Plus tard')}
				</button>
			</div>
		</div>
	</div>
</div>
