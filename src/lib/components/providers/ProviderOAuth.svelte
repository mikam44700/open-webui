<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { startProviderOAuth, getProviderOAuthStatus } from '$lib/apis/providers';
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

	onDestroy(stopPolling);
</script>

<div class="flex flex-col gap-2">
	<div class="text-xs text-gray-500">
		{#if connected}
			{$i18n.t('Ce provider est connecté. Tu peux te reconnecter si besoin.')}
		{:else}
			{$i18n.t('Connecte ce provider avec ton compte. Une fenêtre de navigateur va s’ouvrir pour autoriser l’accès.')}
		{/if}
	</div>

	<div>
		<button
			type="button"
			class="text-sm px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-50 inline-flex items-center gap-2"
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
	</div>

	{#if status === 'running'}
		<div class="text-xs text-amber-600 dark:text-amber-400">
			{$i18n.t('Autorise l’accès dans la fenêtre de navigateur qui vient de s’ouvrir.')}
		</div>
	{:else if status === 'success'}
		<div class="text-xs text-green-600 dark:text-green-400">{$i18n.t('Connecté ✓')}</div>
	{:else if status === 'error'}
		<div class="text-xs text-red-600 dark:text-red-400">{$i18n.t('La connexion a échoué. Réessaie.')}</div>
	{/if}

	{#if log}
		<pre class="text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2 max-h-40 overflow-y-auto whitespace-pre-wrap">{log}</pre>
	{/if}
</div>
