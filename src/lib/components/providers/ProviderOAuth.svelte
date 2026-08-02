<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		startProviderOAuth,
		getProviderOAuthStatus,
		logoutProviderOAuth
	} from '$lib/apis/providers';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CopyField from '$lib/components/common/CopyField.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let provider: {
		id: string;
		label: string;
		state: 'active' | 'configured' | 'not_configured';
		disconnectable?: boolean;
		disconnect_hint?: string | null;
		disconnect_command?: string | null;
		source_label?: string | null;
		flow?: string;
		cli_command?: string | null;
	};

	$: isCodex = provider.id === 'openai-codex';
	// Un compte garde hors de Hermes ne peut pas etre retire depuis cet ecran.
	$: detachable = provider.disconnectable !== false;
	// `external` : la connexion passe par une commande sur la machine, pas par un
	// bouton. Proposer quand meme un bouton ne menerait nulle part.
	$: externe = provider.flow === 'external';

	// Le code d'autorisation arrive dans le journal sous la forme « Code : XXXX-YYYY ».
	// On l'en extrait pour le presenter en grand, avec un bouton copier : c'est la
	// seule chose que l'utilisateur doit reporter a la main, et une erreur de saisie
	// oblige a tout recommencer.
	$: codeAutorisation = (log.match(/Code\s*:\s*([A-Z0-9-]+)/i) ?? [])[1] ?? '';
	$: journalRestant = codeAutorisation ? log.replace(/Code\s*:\s*[A-Z0-9-]+/i, '').trim() : log;

	let status: 'idle' | 'running' | 'success' | 'error' = 'idle';
	let log = '';
	let poller: ReturnType<typeof setInterval> | null = null;
	// Déconnexion : confirmation inline (rien ne se retire sans un « oui » explicite).
	let confirming = false;
	let disconnecting = false;

	$: connected = provider.state !== 'not_configured';

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
	{#if isCodex && !connected}
		<button
			type="button"
			class="text-left text-[13px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 underline decoration-dotted underline-offset-2 transition"
			on:click={() => dispatch('help')}
		>
			{$i18n.t('Première connexion ? Voir comment autoriser ChatGPT')}
		</button>
	{/if}

	<div class="flex items-center gap-2 flex-wrap">
		{#if !externe}
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
		{/if}

		{#if connected && detachable && !confirming}
			<button
				type="button"
				class="text-sm px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				on:click={() => (confirming = true)}
			>
				{$i18n.t('Déconnecter')}
			</button>
		{/if}
	</div>

	{#if externe && !connected && provider.cli_command}
		<div
			class="flex flex-col gap-2 rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-900"
		>
			<div class="text-xs text-gray-600 dark:text-gray-300">
				{$i18n.t('Ce compte se connecte depuis votre machine, pas depuis cet écran.')}
			</div>
			<CopyField
				value={provider.cli_command}
				label={$i18n.t('Commande à lancer dans le Terminal pour le connecter')}
				variant="command"
			/>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Rechargez ensuite cette page : le compte sera reconnu automatiquement.')}
			</div>
		</div>
	{/if}

	{#if connected && !detachable}
		<div
			class="flex flex-col gap-2 rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-900"
		>
			<div class="text-xs text-gray-600 dark:text-gray-300">
				{$i18n.t('Ce compte est géré en dehors de Hermes : il ne peut pas être déconnecté ici.')}
				{#if provider.source_label}
					<span class="text-gray-400"> ({provider.source_label})</span>
				{/if}
			</div>
			{#if provider.disconnect_command}
				<CopyField
					value={provider.disconnect_command}
					label={$i18n.t('Commande à lancer dans le Terminal pour le retirer')}
					variant="command"
				/>
			{/if}
		</div>
	{/if}

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

	{#if status === 'running'}
		<div class="text-xs text-amber-600 dark:text-amber-400">
			{$i18n.t('Autorise l’accès dans la fenêtre de navigateur qui vient de s’ouvrir.')}
		</div>
	{:else if status === 'success'}
		<div class="text-xs text-green-600 dark:text-green-400">{$i18n.t('Connecté ✓')}</div>
	{:else if status === 'error'}
		<div class="text-xs text-red-600 dark:text-red-400">
			{$i18n.t('La connexion a échoué. Réessaie.')}
		</div>
	{/if}

	{#if codeAutorisation}
		<CopyField value={codeAutorisation} label={$i18n.t('Code à saisir sur la page ouverte')} />
	{/if}

	{#if journalRestant}
		<pre
			class="text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2 max-h-40 overflow-y-auto whitespace-pre-wrap">{journalRestant}</pre>
	{/if}
</div>
