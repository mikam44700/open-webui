<script lang="ts">
	// Étape « brancher votre modèle IA » — PRÉALABLE au crawl (sans modèle actif, pas de synthèse).
	// Design validé : ChatGPT Codex mis en avant (connexion via le compte ChatGPT, sans clé API), mais
	// JAMAIS bloquant — tous les autres comptes et clés API restent accessibles directement en dessous
	// (on réutilise ProviderList, la vraie page Modèles IA). Le cerveau s'active automatiquement à la
	// 1re connexion valide : on sonde getActiveProvider pour débloquer « Continuer » dès qu'il apparaît.
	import { createEventDispatcher, getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		getActiveProvider,
		getProviders,
		setActiveProvider,
		startProviderOAuth,
		getProviderOAuthStatus
	} from '$lib/apis/providers';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import ModelSelect from '$lib/components/providers/ModelSelect.svelte';
	import { providerLogoUrl, PROVIDER_LOGO_FALLBACK } from '$lib/utils/providerLogos';
	import { getProviderName } from '$lib/catalog/provider-info';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Slug technique du fournisseur Codex (connexion OAuth via le compte ChatGPT).
	const CODEX_ID = 'openai-codex';
	// Vrai logo Codex (mêmes assets que la page Modèles IA), pas un glyphe générique.
	const codexLogo = providerLogoUrl({ id: CODEX_ID, logo: 'codex' });

	let active: { provider_id: string; model_id: string } | null = null;
	let providers: any[] = [];
	let checking = true;
	let showAll = false; // « ou choisissez un autre modèle » : replié par défaut (Codex mis en avant)
	let codexState: 'idle' | 'connecting' | 'error' = 'idle';
	let poller: ReturnType<typeof setInterval> | null = null;
	let oauthPoller: ReturnType<typeof setInterval> | null = null;

	let modelPickerOpen = false;
	let switching = false;

	// VRAI cerveau connecté vs défaut d'usine « auto/gpt-5.5 ». Le moteur retombe sur ce
	// pseudo-fournisseur « auto » dès qu'aucune clé/compte n'est branché — mais « auto »
	// n'existe PAS dans la liste des fournisseurs. On ne considère donc un modèle « prêt »
	// que si le fournisseur actif existe réellement ET n'est pas « not_configured » (déconnecté).
	// Couvre d'un seul test les deux cas : défaut d'usine ET déconnexion a posteriori.
	$: activeProvider = active
		? (providers.find((p: any) => p.id === active.provider_id) ?? null)
		: null;
	$: hasRealBrain = !!active && !!activeProvider && activeProvider.state !== 'not_configured';
	// Modèles du fournisseur actif (pour choisir/changer directement dans le cadre « prêt »).
	$: activeModels = (activeProvider?.models ?? []) as { id: string; label: string }[];

	// Nom lisible + libellé du modèle actif (jamais le slug brut si on a mieux).
	$: activeProviderName = active ? getProviderName(active.provider_id, active.provider_id) : '';
	$: activeModelLabel = (() => {
		const a = active;
		if (!a) return '';
		return activeModels.find((m) => m.id === a.model_id)?.label ?? a.model_id;
	})();

	const refresh = async () => {
		try {
			const [a, provRes] = await Promise.all([
				getActiveProvider(localStorage.token).catch(() => null),
				getProviders(localStorage.token).catch(() => null)
			]);
			active = a;
			providers = provRes?.providers ?? [];
		} finally {
			checking = false;
		}
	};

	// Changement de modèle depuis le cadre « prêt » : bascule le cerveau + resynchronise l'affichage.
	const chooseModel = async (id: string) => {
		if (!id || !active || switching) return;
		switching = true;
		try {
			await setActiveProvider(localStorage.token, active.provider_id, id);
			modelPickerOpen = false;
			await refresh();
			toast.success($i18n.t('Modèle sélectionné'));
		} catch {
			toast.error($i18n.t('Impossible de sélectionner ce modèle'));
		} finally {
			switching = false;
		}
	};

	onMount(async () => {
		await refresh();
		// Sonde en continu : capte AUSSI BIEN un branchement qu'une déconnexion faite ailleurs
		// (page Clés API, autre onglet…), pour que l'état « prêt / à connecter » reste honnête
		// en temps réel. Écran d'onboarding transitoire → coût négligeable.
		poller = setInterval(refresh, 3000);
	});
	onDestroy(() => {
		if (poller) clearInterval(poller);
		if (oauthPoller) clearInterval(oauthPoller);
	});

	// Connexion Codex : ouvre le flux OAuth du moteur puis sonde son issue (comme ProviderOAuth).
	const connectCodex = async () => {
		codexState = 'connecting';
		try {
			await startProviderOAuth(localStorage.token, CODEX_ID);
			if (oauthPoller) clearInterval(oauthPoller);
			oauthPoller = setInterval(async () => {
				const st = await getProviderOAuthStatus(localStorage.token, CODEX_ID).catch(() => null);
				if (st && st.running === false && st.started) {
					clearInterval(oauthPoller!);
					oauthPoller = null;
					if (st.success) {
						toast.success($i18n.t('Connexion réussie'));
						await refresh();
						codexState = 'idle';
					} else {
						codexState = 'error';
						toast.error($i18n.t('Échec de la connexion'));
					}
				}
			}, 1500);
		} catch {
			codexState = 'error';
			toast.error($i18n.t('Impossible de démarrer la connexion'));
		}
	};

	const cont = () => dispatch('next');
	const skip = () => dispatch('skip');
</script>

<div class="w-full max-w-5xl mx-auto px-5 py-8 sm:py-10">
	<!-- Colonne « lecture » (en-tête, cerveau actif, Codex, nav) : centrée étroite pour rester
	     lisible et premium. Le catalogue de fournisseurs, lui, s'élargit plus bas (pleine largeur
	     du conteneur) pour que les cartes respirent au lieu d'être tassées au centre. -->
	<div class="max-w-2xl mx-auto">
	<!-- En-tête : le pourquoi, avant tout -->
	<div class="text-center">
		<div
			class="text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-600 dark:text-amber-300/90"
		>
			{$i18n.t('Le moteur de votre assistant')}
		</div>
		<h1
			class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white"
		>
			{$i18n.t('Branchez votre modèle IA')}
		</h1>
		<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-lg mx-auto">
			{$i18n.t(
				'C’est le cerveau de vos agents. On le connecte d’abord — ensuite je pourrai lire votre site et comprendre votre entreprise.'
			)}
		</p>
	</div>

	{#if hasRealBrain}
		<!-- Cerveau actif : on confirme honnêtement + on laisse choisir le modèle ICI (se met à jour
		     en direct quand le client change de modèle, ici ou dans une carte plus bas). -->
		<div
			class="mt-6 rounded-2xl bg-emerald-50/80 dark:bg-emerald-900/20 ring-1 ring-inset ring-emerald-500/20 px-5 py-4"
		>
			<div class="flex items-center gap-3">
				<span
					class="flex-none h-8 w-8 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 flex items-center justify-center text-lg"
					>✓</span
				>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Votre modèle IA est prêt.')}
					</div>
					<div class="text-[13px] text-gray-600 dark:text-gray-300 truncate">
						{activeProviderName}{activeModelLabel ? ` · ${activeModelLabel}` : ''}
					</div>
				</div>
				{#if activeModels.length > 1}
					<button
						type="button"
						class="flex-none text-xs font-medium px-3 py-1.5 rounded-lg text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/10 transition disabled:opacity-50"
						on:click={() => (modelPickerOpen = !modelPickerOpen)}
						disabled={switching}
					>
						{modelPickerOpen ? $i18n.t('Fermer') : $i18n.t('Changer de modèle')}
					</button>
				{/if}
			</div>
			{#if modelPickerOpen && activeModels.length > 1}
				<div class="mt-3 pt-3 border-t border-emerald-500/15">
					<ModelSelect
						models={activeModels}
						value={active.model_id}
						on:change={(e) => chooseModel(e.detail)}
					/>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Carte Codex : l'option recommandée (sans clé API) -->
	<div
		class="mt-6 rounded-2xl bg-white dark:bg-white/[0.03] ring-1 ring-inset ring-amber-500/20 p-5 sm:p-6"
	>
		<div class="flex items-center gap-3.5">
			<span
				class="flex-none h-12 w-12 rounded-xl bg-white ring-1 ring-inset ring-black/5 dark:ring-white/10 overflow-hidden flex items-center justify-center"
			>
				<img
					src={codexLogo}
					alt="ChatGPT Codex"
					class="h-9 w-9 object-contain"
					on:error={(e) => ((e.currentTarget as HTMLImageElement).src = PROVIDER_LOGO_FALLBACK)}
				/>
			</span>
			<div>
				<div
					class="font-semibold text-lg tracking-tight text-gray-900 dark:text-white flex items-center gap-2.5 flex-wrap"
				>
					{$i18n.t('ChatGPT Codex')}
					<span
						class="text-[11px] font-bold uppercase tracking-wide text-amber-600 dark:text-amber-300"
						>{$i18n.t('Recommandé')}</span
					>
				</div>
				<div class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">
					{$i18n.t('Utilisez le compte ChatGPT que vous avez déjà — rien de nouveau à créer.')}
				</div>
			</div>
		</div>

		<ul class="mt-4 grid gap-2.5">
			{#each ['Aucune clé technique à créer ou à coller', 'Aucun coût en plus : votre abonnement ChatGPT suffit', 'Connexion en un clic, sécurisée'] as perk}
				<li class="flex items-center gap-2.5 text-sm text-gray-800 dark:text-gray-100">
					<span class="text-emerald-500 font-bold">✓</span>
					{$i18n.t(perk)}
				</li>
			{/each}
		</ul>

		<button
			class="mt-5 w-full text-sm font-semibold px-5 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 disabled:opacity-60"
			on:click={connectCodex}
			disabled={codexState === 'connecting'}
		>
			{#if codexState === 'connecting'}
				{$i18n.t('Connexion en cours…')}
			{:else}
				{$i18n.t('Se connecter avec ChatGPT')} →
			{/if}
		</button>
		{#if codexState === 'error'}
			<p class="mt-2 text-[13px] text-red-600 dark:text-red-400">
				{$i18n.t('La connexion n’a pas abouti. Réessayez, ou choisissez un autre modèle ci-dessous.')}
			</p>
		{/if}
	</div>

	<!-- Repli : Codex est mis en avant ; « ou choisissez un autre modèle » ouvre le catalogue complet
	     (comptes 1-clic + clés API + local) à la demande, via la flèche. Fermé par défaut. -->
	<button
		type="button"
		on:click={() => (showAll = !showAll)}
		aria-expanded={showAll}
		class="my-6 w-full flex items-center gap-3.5 text-[12.5px] text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
	>
		<span class="flex-1 h-px bg-gray-200 dark:bg-white/10"></span>
		<span class="flex items-center gap-1.5 font-medium">
			{$i18n.t('ou choisissez un autre modèle')}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4 transition-transform duration-200 {showAll ? 'rotate-180' : ''}"
			>
				<path
					fill-rule="evenodd"
					d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
					clip-rule="evenodd"
				/>
			</svg>
		</span>
		<span class="flex-1 h-px bg-gray-200 dark:bg-white/10"></span>
	</button>

	</div>
	<!-- Catalogue restreint à Comptes + Clés API (pas de « Moteur » ni « Local » : on n'embrouille
	     pas le dirigeant avec l'état technique du moteur). Affiché à la demande, non bloquant.
	     Hors de la colonne étroite : prend la pleine largeur du conteneur pour aérer les cartes. -->
	{#if showAll}
		<div class="rounded-2xl ring-1 ring-inset ring-black/5 dark:ring-white/10 overflow-hidden">
			<ProviderList allowedTabs={['oauth', 'api']} showModelPicker on:changed={refresh} />
		</div>
	{/if}

	<div class="max-w-2xl mx-auto">
	<!-- Navigation -->
	<div class="mt-8 flex flex-wrap items-center justify-center gap-3">
		<button
			disabled={!hasRealBrain}
			class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black disabled:opacity-40 disabled:cursor-not-allowed"
			on:click={cont}
		>
			{hasRealBrain ? $i18n.t('Continuer') : $i18n.t('Connectez un modèle pour continuer')} →
		</button>
		<button
			class="text-sm font-medium px-5 py-3 rounded-xl bg-white/70 dark:bg-white/10 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-900/10 dark:ring-white/15"
			on:click={skip}
		>
			{$i18n.t('Plus tard')}
		</button>
	</div>
	{#if !hasRealBrain && !checking}
		<p class="mt-3 text-center text-[13px] text-gray-500 dark:text-gray-400">
			🔒 {$i18n.t('Connexion à votre compte. Aucune donnée partagée.')}
		</p>
	{/if}
	</div>
</div>
