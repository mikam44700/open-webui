<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		startProviderOAuth,
		getProviderOAuthStatus,
		logoutProviderOAuth
	} from '$lib/apis/providers';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let provider: {
		id: string;
		label: string;
		state: 'active' | 'configured' | 'not_configured';
	};

	let status: 'idle' | 'running' | 'success' | 'error' = 'idle';
	let log = '';
	let poller: ReturnType<typeof setInterval> | null = null;
	// Déconnexion : confirmation inline (rien ne se retire sans un « oui » explicite).
	let confirming = false;
	let disconnecting = false;

	$: connected = provider.state !== 'not_configured';
	// ChatGPT/Codex : seul fournisseur dont la connexion exige un réglage préalable côté
	// compte ChatGPT (les codes d'appareil sont désactivés par défaut).
	$: isCodex = provider.id === 'openai-codex';

	// Connexion par code d'appareil (ChatGPT/Codex, xAI…). L'application tourne dans un
	// conteneur — sur le VPS du client, pas sur son poste : AUCUNE fenêtre ne peut s'ouvrir
	// chez lui. Le dirigeant doit donc ouvrir l'adresse lui-même et recopier un code.
	// Ces deux informations sont dans le journal technique du moteur, noyées au milieu de
	// codes de couleur de terminal (constaté le 2026-07-21 : « [94mI53B-1Z57N [0m » — le
	// patron ne pouvait même pas copier son code). On les extrait pour les présenter en clair.
	const SANS_COULEURS = /\[[0-9;]*m|\[\d{1,3}m/g;
	$: journalPropre = (log || '').replace(SANS_COULEURS, '');
	$: adresseAppareil = (journalPropre.match(/https?:\/\/\S*device\S*/i) || [])[0]?.replace(/[.,;)]+$/, '') ?? '';
	$: codeAppareil = (journalPropre.match(/\b[A-Z0-9]{4,6}-[A-Z0-9]{4,6}\b/) || [])[0] ?? '';
	$: connexionParCode = Boolean(adresseAppareil && codeAppareil);

	const copierCode = async () => {
		try {
			await navigator.clipboard.writeText(codeAppareil);
			toast.success($i18n.t('Code copié'));
		} catch {
			toast.error($i18n.t('Copie impossible — sélectionne le code à la main.'));
		}
	};

	const stopPolling = () => {
		if (poller) {
			clearInterval(poller);
			poller = null;
		}
	};

	const poll = async () => {
		try {
			const st = await getProviderOAuthStatus(localStorage.token, provider.id);
			log = st?.log ?? log;
			if (st && st.running === false && st.started) {
				stopPolling();
				if (st.success) {
					status = 'success';
					toast.success($i18n.t('Connexion réussie'));
					dispatch('connected');
				} else {
					status = 'error';
					toast.error($i18n.t('Échec de la connexion'));
				}
			}
		} catch (err) {
			stopPolling();
			status = 'error';
		}
	};

	const connect = async () => {
		status = 'running';
		log = '';
		try {
			await startProviderOAuth(localStorage.token, provider.id);
			stopPolling();
			poller = setInterval(poll, 1500);
		} catch (err) {
			status = 'error';
			toast.error($i18n.t('Impossible de démarrer la connexion'));
		}
	};

	const disconnect = async () => {
		disconnecting = true;
		try {
			await logoutProviderOAuth(localStorage.token, provider.id);
			toast.success($i18n.t('Compte déconnecté'));
			confirming = false;
			dispatch('changed');
		} catch (err) {
			toast.error($i18n.t('Impossible de déconnecter ce compte.'));
		} finally {
			disconnecting = false;
		}
	};

	onDestroy(stopPolling);
</script>

<div class="flex flex-col gap-2">
	<!-- Explications déplacées dans la popup « Voir ce que ça fait » de la carte
	     (SPEC-cartes-modeles-ia) : ici, seuls le bouton et le feedback d'action.
	     EXCEPTION Codex : ChatGPT exige d'activer les codes d'appareil dans SES réglages
	     avant que la connexion puisse aboutir. Enterré dans la popup, ce prérequis n'est
	     jamais vu et le patron reste bloqué sans comprendre (constaté le 2026-07-21).
	     Le lien était visible sur la carte en V1 : on le remet là où il sert. -->
	{#if isCodex && !connected && status !== 'success'}
		<button
			type="button"
			class="text-left text-[13px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 underline decoration-dotted underline-offset-2 transition"
			on:click={() => dispatch('help')}
		>
			{$i18n.t('Première connexion ? Voir comment autoriser ChatGPT')}
		</button>
	{/if}

	<div class="flex items-center gap-2 flex-wrap">
		<button
			type="button"
			class="text-sm px-3 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-50 inline-flex items-center gap-2"
			disabled={status === 'running'}
			on:click={connect}
		>
			{#if status === 'running'}
				<Spinner className="size-4" />
				{$i18n.t('Connexion en cours…')}
			{:else}
				{connected ? $i18n.t('Se reconnecter') : $i18n.t('Se connecter')}
			{/if}
		</button>

		{#if connected && !confirming}
			<button
				type="button"
				class="text-sm px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				on:click={() => (confirming = true)}
			>
				{$i18n.t('Déconnecter')}
			</button>
		{/if}
	</div>

	{#if confirming}
		<div class="flex items-center gap-2 flex-wrap text-xs">
			<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Déconnecter ce compte ?')}</span>
			<button
				type="button"
				class="px-2.5 py-1 rounded-lg bg-red-600 text-white hover:bg-red-700 transition disabled:opacity-50 inline-flex items-center gap-1.5"
				disabled={disconnecting}
				on:click={disconnect}
			>
				{#if disconnecting}<Spinner className="size-3.5" />{/if}
				{$i18n.t('Oui, déconnecter')}
			</button>
			<button
				type="button"
				class="px-2.5 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
				disabled={disconnecting}
				on:click={() => (confirming = false)}
			>
				{$i18n.t('Annuler')}
			</button>
		</div>
	{/if}

	{#if status === 'running' && connexionParCode}
		<!-- Marche à suivre en clair : le patron ouvre l'adresse et recopie le code. -->
		<div class="rounded-xl border border-amber-300/60 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 p-3 flex flex-col gap-2.5">
			<div class="text-xs font-medium text-amber-800 dark:text-amber-300">
				{$i18n.t('Deux étapes pour autoriser l’accès :')}
			</div>

			<div class="flex flex-col gap-1">
				<div class="text-[11px] text-gray-600 dark:text-gray-400">
					{$i18n.t('1. Ouvre cette adresse')}
				</div>
				<a
					href={adresseAppareil}
					target="_blank"
					rel="noopener noreferrer"
					class="text-[13px] font-medium text-blue-600 dark:text-blue-400 hover:underline break-all"
				>
					{adresseAppareil}
				</a>
			</div>

			<div class="flex flex-col gap-1">
				<div class="text-[11px] text-gray-600 dark:text-gray-400">
					{$i18n.t('2. Entre ce code')}
				</div>
				<div class="flex items-center gap-2">
					<code class="text-base font-mono font-semibold tracking-widest select-all text-gray-900 dark:text-gray-100">
						{codeAppareil}
					</code>
					<button
						type="button"
						class="px-2 py-0.5 rounded-lg text-[11px] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
						on:click={copierCode}
					>
						{$i18n.t('Copier')}
					</button>
				</div>
			</div>

			<div class="text-[11px] text-gray-500 dark:text-gray-400">
				{$i18n.t('Cette fenêtre se met à jour toute seule dès que l’accès est autorisé.')}
			</div>
		</div>
	{:else if status === 'running'}
		<div class="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-2">
			<Spinner className="size-3.5" />
			{$i18n.t('Connexion en cours… la marche à suivre s’affiche dans un instant.')}
		</div>
	{:else if status === 'success'}
		<div class="text-xs text-green-600 dark:text-green-400">{$i18n.t('Connecté ✓')}</div>
	{:else if status === 'error'}
		<div class="text-xs text-red-600 dark:text-red-400">{$i18n.t('La connexion a échoué. Réessaie.')}</div>
	{/if}

	{#if journalPropre && !connexionParCode}
		<!-- Journal technique : montré uniquement quand on n'a pas su en extraire la marche
		     à suivre — sinon il fait doublon et noie le patron. Débarrassé de ses codes
		     de couleur de terminal dans tous les cas. -->
		<pre class="text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2 max-h-40 overflow-y-auto whitespace-pre-wrap">{journalPropre}</pre>
	{/if}
</div>
