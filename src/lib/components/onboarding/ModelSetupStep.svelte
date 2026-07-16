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
	import CodexDeviceHelp from '$lib/components/providers/CodexDeviceHelp.svelte';
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
	// ChatGPT/Codex utilise un « device code flow » : le moteur ne peut pas ouvrir le navigateur
	// seul, il génère une URL + un code à recopier. On les extrait du log du process pour les
	// présenter proprement (sinon le client reste bloqué sur « Connexion en cours… »).
	let codexDevice: { url: string; code: string } | null = null;
	let showCodexHelp = false; // modale « comment activer les codes d'appareil ChatGPT »

	// Retire les codes couleur ANSI (le CLI en émet) puis extrait l'URL d'autorisation + le code.
	const parseDeviceFlow = (raw: string): { url: string; code: string } | null => {
		const clean = (raw || '').replace(/\[[0-9;]*m/g, '');
		const url = clean.match(/https?:\/\/\S+/)?.[0] ?? '';
		const code = clean.match(/\b[A-Z0-9]{4}-[A-Z0-9]{4,6}\b/)?.[0] ?? '';
		// Nettoie l'URL d'un éventuel caractère de contrôle résiduel (ESC ANSI non retiré).
		const cleanUrl = url.replace(/[^\x21-\x7e]/g, '');
		return cleanUrl && code ? { url: cleanUrl, code } : null;
	};
	let poller: ReturnType<typeof setInterval> | null = null;
	let oauthPoller: ReturnType<typeof setInterval> | null = null;
	// Délai max de la sonde OAuth Codex (audit 2026-07-15, BASSE) : sans plafond, un flux jamais
	// autorisé (onglet fermé, code expiré côté ChatGPT…) laissait « En attente de votre
	// autorisation… » tourner indéfiniment, sans jamais basculer en erreur.
	const CODEX_OAUTH_TIMEOUT_MS = 5 * 60 * 1000;
	let oauthDeadline = 0;

	let modelPickerOpen = false;
	let switching = false;
	// Référence à la liste de fournisseurs (montée quand showAll) : sert à la resynchroniser
	// après un changement de modèle fait ici, pour éviter un affichage périmé côté carte.
	let providerList: { reload: () => void } | null = null;

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
			// Resynchronise la liste en dessous (si ouverte) pour qu'elle affiche le même modèle.
			providerList?.reload();
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
		codexDevice = null;
		try {
			await startProviderOAuth(localStorage.token, CODEX_ID);
			if (oauthPoller) clearInterval(oauthPoller);
			oauthDeadline = Date.now() + CODEX_OAUTH_TIMEOUT_MS;
			oauthPoller = setInterval(async () => {
				// Plafond de temps : au-delà, on arrête de sonder et on passe en erreur — jamais de
				// « En attente de votre autorisation… » indéfini.
				if (Date.now() > oauthDeadline) {
					clearInterval(oauthPoller!);
					oauthPoller = null;
					codexDevice = null;
					codexState = 'error';
					toast.error($i18n.t('La connexion a expiré. Réessayez.'));
					return;
				}
				const st = await getProviderOAuthStatus(localStorage.token, CODEX_ID).catch(() => null);
				if (!st) return;
				// Tant que le flux tourne : extraire l'URL + le code à recopier (device flow).
				if (st.running) {
					const dev = parseDeviceFlow(st.log ?? '');
					if (dev) codexDevice = dev;
					return;
				}
				if (st.started) {
					clearInterval(oauthPoller!);
					oauthPoller = null;
					codexDevice = null;
					if (st.success) {
						toast.success($i18n.t('Connexion réussie'));
						await refresh();
						providerList?.reload();
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

	// Copie le code d'appairage dans le presse-papier (confort pour le recopier sur la page OpenAI).
	const copyCodexCode = async () => {
		if (!codexDevice?.code) return;
		try {
			await navigator.clipboard.writeText(codexDevice.code);
			toast.success($i18n.t('Code copié'));
		} catch {
			// presse-papier indisponible : le code reste lisible à l'écran, rien de bloquant.
		}
	};

	const cont = () => dispatch('next');
	// Sortie honnête : quitter l'onboarding SANS modèle branché = entrer dans une app qui ne peut pas
	// encore répondre. Plutôt que de lâcher le dirigeant sans un mot, on demande confirmation (choix
	// éclairé). Avec un modèle actif, « Plus tard » sort directement — rien à signaler.
	let showLeaveConfirm = false;
	const skip = () => {
		if (hasRealBrain) dispatch('skip');
		else showLeaveConfirm = true;
	};
	const leaveAnyway = () => {
		showLeaveConfirm = false;
		dispatch('skip');
	};
	// Accessibilité de la modale de confirmation (audit 2026-07-15, BASSE) : focus initial posé sur
	// l'action recommandée dès l'ouverture, et fermeture au clavier (Échap) comme au clic hors modale.
	const focusOnMount = (node: HTMLElement) => {
		node.focus();
	};
	const onWindowKeydown = (e: KeyboardEvent) => {
		if (showLeaveConfirm && e.key === 'Escape') showLeaveConfirm = false;
	};
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
				{codexDevice ? $i18n.t('En attente de votre autorisation…') : $i18n.t('Préparation…')}
			{:else}
				{$i18n.t('Se connecter avec ChatGPT')} →
			{/if}
		</button>

		<!-- Pré-requis (codes d'appareil désactivés par défaut côté ChatGPT) : lien visible AVANT
		     la connexion pour prévenir qu'une activation unique côté ChatGPT peut être nécessaire. -->
		<button
			type="button"
			class="mt-3 w-full text-center text-[13px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 underline decoration-dotted underline-offset-2 transition"
			on:click={() => (showCodexHelp = true)}
		>
			{$i18n.t('Première connexion ? Voir comment autoriser ChatGPT')}
		</button>

		{#if codexState === 'connecting' && codexDevice}
			<!-- Device code flow : ChatGPT ne peut pas ouvrir le navigateur seul. On présente
			     l'URL + le code à recopier proprement, et on attend l'autorisation. -->
			<div
				class="mt-4 rounded-xl bg-amber-50/70 dark:bg-amber-900/15 ring-1 ring-inset ring-amber-500/25 p-4 sm:p-5"
			>
				<div class="text-sm font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Dernière étape : autorisez ChatGPT')}
				</div>
				<div class="mt-3 flex flex-col gap-3">
					<a
						href={codexDevice.url}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center justify-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition hover:opacity-90"
					>
						1. {$i18n.t('Ouvrir la page d’autorisation')} ↗
					</a>
					<div class="flex items-center gap-2 flex-wrap">
						<span class="text-sm text-gray-700 dark:text-gray-200"
							>2. {$i18n.t('Entrez ce code')} :</span
						>
						<code
							class="text-base font-mono font-bold tracking-widest px-2.5 py-1 rounded-md bg-white dark:bg-white/10 ring-1 ring-inset ring-black/10 dark:ring-white/15 text-gray-900 dark:text-white select-all"
							>{codexDevice.code}</code
						>
						<button
							type="button"
							class="text-xs font-medium px-2.5 py-1 rounded-md text-amber-700 dark:text-amber-300 hover:bg-amber-500/10 transition"
							on:click={copyCodexCode}
						>
							{$i18n.t('Copier')}
						</button>
					</div>
				</div>
				<div
					class="mt-3 pt-3 border-t border-amber-500/15 flex items-center gap-2 text-[13px] text-amber-700 dark:text-amber-300"
				>
					<span class="inline-block h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin"
					></span>
					{$i18n.t('En attente de votre autorisation…')}
				</div>
			</div>
		{/if}

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
			<ProviderList
				bind:this={providerList}
				allowedTabs={['oauth', 'api']}
				showModelPicker
				on:changed={refresh}
			/>
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

	{#if showCodexHelp}
		<CodexDeviceHelp on:close={() => (showCodexHelp = false)} />
	{/if}

	{#if showLeaveConfirm}
		<!-- Sortie sans modèle : confirmation honnête (choix éclairé), jamais un mur. Le rappel se
		     poursuit ensuite dans l'app (BrainSelector en alerte tant qu'aucun modèle n'est branché). -->
		<div class="fixed inset-0 z-[70] flex items-center justify-center p-4">
			<button
				class="absolute inset-0 bg-black/40"
				on:click={() => (showLeaveConfirm = false)}
				aria-label={$i18n.t('Fermer')}
			></button>
			<div
				class="relative z-10 w-full max-w-md rounded-2xl bg-white dark:bg-gray-900 ring-1 ring-inset ring-black/10 dark:ring-white/10 shadow-xl p-6 text-center"
				role="dialog"
				aria-modal="true"
				aria-labelledby="leave-confirm-title"
			>
				<div
					class="mx-auto h-11 w-11 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-300 flex items-center justify-center text-xl"
				>
					⚠️
				</div>
				<h2 id="leave-confirm-title" class="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Continuer sans modèle IA ?')}
				</h2>
				<p class="mt-2 text-sm leading-relaxed text-gray-600 dark:text-gray-300">
					{$i18n.t(
						'Sans modèle IA, votre assistant ne pourra pas encore répondre. Vous pourrez le brancher à tout moment depuis les Réglages.'
					)}
				</p>
				<div class="mt-6 flex flex-col gap-2.5">
					<button
						use:focusOnMount
						class="w-full text-sm font-semibold px-5 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950"
						on:click={() => (showLeaveConfirm = false)}
					>
						{$i18n.t('Rester et brancher mon modèle')}
					</button>
					<button
						class="w-full text-sm font-medium px-5 py-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5 transition"
						on:click={leaveAnyway}
					>
						{$i18n.t('Explorer quand même')}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<svelte:window on:keydown={onWindowKeydown} />
