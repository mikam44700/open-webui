<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { getConnectorOAuthStatus } from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let connectorId: string;
	export let open = false;

	let running = false;
	let success: boolean | null = null;
	let authUrl: string | null = null;
	let log = '';
	let timer: ReturnType<typeof setInterval> | null = null;

	const stop = () => {
		if (timer) {
			clearInterval(timer);
			timer = null;
		}
	};

	const poll = async () => {
		try {
			const s = await getConnectorOAuthStatus(localStorage.token, connectorId);
			running = s?.running ?? false;
			authUrl = s?.auth_url ?? null;
			log = s?.log ?? '';
			if (s && s.started && !s.running) {
				success = s.success ?? false;
				stop();
				if (success) dispatch('connected');
			}
		} catch {
			stop();
			success = false;
		}
	};

	// Démarre/arrête le polling selon l'ouverture du modal.
	$: if (open && !timer) {
		running = true;
		success = null;
		authUrl = null;
		log = '';
		poll();
		timer = setInterval(poll, 1500);
	} else if (!open) {
		stop();
	}

	onDestroy(stop);

	const close = () => {
		stop();
		dispatch('close');
	};
</script>

{#if open}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" on:click|self={close}>
		<div class="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-xl">
			<div class="flex items-center justify-between mb-3">
				<div class="text-sm font-medium">
					{$i18n.t('Connexion OAuth')} — {connectorId}
				</div>
				<button class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" on:click={close}>✕</button>
			</div>

			{#if success === true}
				<div class="text-sm text-green-600 dark:text-green-400 py-3">
					{$i18n.t('Connecté avec succès.')}
				</div>
			{:else if success === false}
				<div class="text-sm text-red-600 dark:text-red-400 py-3">
					{$i18n.t('La connexion a échoué. Réessaie depuis le catalogue.')}
				</div>
			{:else}
				<div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 py-1">
					<Spinner className="size-4" />
					{$i18n.t('Autorisation en cours… une fenêtre de navigateur s’est ouverte sur l’hôte.')}
				</div>
				{#if authUrl}
					<div class="text-xs text-gray-500 mt-2">
						{$i18n.t('Si rien ne s’ouvre, ouvre ce lien manuellement :')}
						<a class="text-sky-600 dark:text-sky-400 underline break-all" href={authUrl} target="_blank" rel="noopener">
							{authUrl}
						</a>
					</div>
				{/if}
			{/if}

			{#if log}
				<pre class="mt-3 max-h-40 overflow-y-auto text-[11px] bg-gray-50 dark:bg-gray-850 rounded-lg p-2 whitespace-pre-wrap">{log}</pre>
			{/if}

			<div class="flex justify-end mt-4">
				<button
					class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={close}
				>
					{$i18n.t('Fermer')}
				</button>
			</div>
		</div>
	</div>
{/if}
