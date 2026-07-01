<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		setToolKey,
		testToolKey,
		disconnectToolProvider,
		startToolOAuth,
		getToolOAuthStatus
	} from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import {
		type Provider,
		LOGO_BY_SLUG,
		WHITE_BG_SLUGS,
		providerStatus
	} from '$lib/utils/toolConnect';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Le toolset auquel appartient ce fournisseur (web, browser, x_search…) et le fournisseur lui-même.
	export let toolsetName: string;
	export let provider: Provider;

	// Valeurs saisies par clé de champ (jamais pré-remplies pour les secrets déjà présents).
	let values: Record<string, string> = {};
	let initialized = false;
	$: if (provider && !initialized) {
		initialized = true;
		for (const f of provider.fields) {
			if (f.default && !f.present && !f.secret) values[f.key] = f.default;
		}
	}

	let saving = false;
	let testing = false;
	let disconnecting = false;
	let showDisconnectConfirm = false;

	type TestResult = { tested: boolean; ok: boolean; reason: string };
	let testResult: TestResult | null = null;

	// Suivi OAuth (propre à ce fournisseur).
	let oauthRunning = false;
	let oauthAuthUrl: string | null = null;
	let oauthLog = '';
	let oauthTimer: ReturnType<typeof setInterval> | null = null;

	const stopOAuth = () => {
		if (oauthTimer) {
			clearInterval(oauthTimer);
			oauthTimer = null;
		}
	};
	onDestroy(stopOAuth);

	const save = async () => {
		const payload: Record<string, string> = {};
		for (const f of provider.fields) {
			const v = (values[f.key] ?? '').trim();
			if (v) payload[f.key] = v;
			else if (!f.present) {
				toast.error($i18n.t('Renseigne le champ : {{field}}', { field: f.label }));
				return;
			}
		}
		if (Object.keys(payload).length === 0) {
			toast.error($i18n.t('Aucune nouvelle valeur à enregistrer'));
			return;
		}
		saving = true;
		try {
			await setToolKey(localStorage.token, toolsetName, payload);
			// reflète localement les champs enregistrés → pastille « enregistrée » + bouton
			// « Déconnecter » apparaissent aussitôt.
			for (const f of provider.fields) if (payload[f.key]) f.present = true;
			provider = provider;
			toast.success($i18n.t('Connexion enregistrée'));
			dispatch('changed');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Échec de l’enregistrement'));
		} finally {
			saving = false;
		}
	};

	// Test RÉEL : envoie les valeurs saisies (ou vides → clé enregistrée).
	const testKey = async () => {
		const payload: Record<string, string> = {};
		for (const f of provider.fields) payload[f.key] = (values[f.key] ?? '').trim();
		testing = true;
		try {
			const res = await testToolKey(localStorage.token, toolsetName, payload);
			testResult = res;
			if (res?.tested && res?.ok) {
				for (const f of provider.fields) if (payload[f.key]) f.present = true;
				provider = provider;
			}
		} catch (err: any) {
			testResult = {
				tested: false,
				ok: false,
				reason: err?.error?.message ?? $i18n.t('Le test a échoué')
			};
		} finally {
			testing = false;
		}
	};

	// Déconnecte ce SEUL fournisseur : efface ses clés, sans toucher aux autres.
	const disconnect = async () => {
		const keys = provider.fields.map((f) => f.key);
		if (keys.length === 0) return;
		disconnecting = true;
		try {
			await disconnectToolProvider(localStorage.token, toolsetName, keys);
			for (const f of provider.fields) {
				f.present = false;
				values[f.key] = '';
			}
			provider = provider;
			testResult = null;
			toast.success($i18n.t('{{provider}} déconnecté', { provider: provider.name }));
			dispatch('changed');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Échec de la déconnexion'));
		} finally {
			disconnecting = false;
		}
	};

	const pollOAuth = async () => {
		try {
			const s = await getToolOAuthStatus(localStorage.token, toolsetName);
			oauthAuthUrl = s?.auth_url ?? null;
			oauthLog = s?.log ?? '';
			oauthRunning = s?.status === 'running';
			if (s?.status === 'success') {
				stopOAuth();
				toast.success($i18n.t('Connecté avec succès.'));
				dispatch('changed');
			} else if (s?.status === 'error') {
				stopOAuth();
				toast.error($i18n.t('La connexion a échoué. Réessaie.'));
			}
		} catch {
			stopOAuth();
		}
	};

	const startOAuth = async () => {
		try {
			await startToolOAuth(localStorage.token, toolsetName);
			oauthRunning = true;
			oauthAuthUrl = null;
			oauthLog = '';
			stopOAuth();
			pollOAuth();
			oauthTimer = setInterval(pollOAuth, 1500);
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Impossible de démarrer la connexion'));
		}
	};
</script>

<div class="border border-gray-100 dark:border-gray-850 rounded-2xl p-3 mb-3">
	<div class="flex items-center gap-3 mb-2">
		{#if provider.slug && LOGO_BY_SLUG[provider.slug]}
			<img
				src={LOGO_BY_SLUG[provider.slug]}
				alt=""
				class="size-10 rounded-xl flex-none border border-gray-100 dark:border-gray-800 {WHITE_BG_SLUGS.has(
					provider.slug
				)
					? 'bg-white object-contain p-1'
					: 'object-cover'}"
			/>
		{/if}
		<div class="flex items-center gap-2 flex-wrap min-w-0">
			<span class="text-sm font-medium">{provider.name}</span>
			{#if provider.badge}
				<span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-850 text-gray-500"
					>{provider.badge}</span
				>
			{/if}
			{#if providerStatus(provider) === 'saved'}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400"
					>{$i18n.t('Clé enregistrée')}</span
				>
			{:else if providerStatus(provider) === 'detected'}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
					>{$i18n.t('Connecté')}</span
				>
			{:else if providerStatus(provider) === 'disconnected'}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
					>{$i18n.t('Non connecté')}</span
				>
			{:else if providerStatus(provider) === 'active'}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-500"
					>{$i18n.t('Actif sans clé')}</span
				>
			{:else if providerStatus(provider) === 'local'}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
					>{$i18n.t('Sans clé · local')}</span
				>
			{:else if providerStatus(provider) === 'subscription'}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
					>{$i18n.t('Nécessite l’abonnement Nous')}</span
				>
			{/if}
		</div>
	</div>
	{#if provider.tag}
		<div class="text-xs text-gray-500 mb-2">{provider.tag}</div>
	{/if}

	{#if provider.kind === 'oauth'}
		<button
			class="text-xs px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50"
			on:click={startOAuth}
			disabled={oauthRunning}
		>
			{$i18n.t('Autoriser')}
		</button>
		{#if oauthRunning}
			<div class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 mt-2">
				<Spinner className="size-3" />
				{$i18n.t('Autorisation en cours… une fenêtre s’est ouverte sur l’hôte.')}
			</div>
		{/if}
		{#if oauthAuthUrl}
			<div class="text-xs text-gray-500 mt-2">
				{$i18n.t('Si rien ne s’ouvre, ouvre ce lien :')}
				<a
					class="text-sky-600 dark:text-sky-400 underline break-all"
					href={oauthAuthUrl}
					target="_blank"
					rel="noopener">{oauthAuthUrl}</a
				>
			</div>
		{/if}
		{#if oauthLog}
			<pre
				class="mt-2 max-h-32 overflow-y-auto text-[11px] bg-gray-50 dark:bg-gray-850 rounded-lg p-2 whitespace-pre-wrap">{oauthLog}</pre>
		{/if}
	{:else if provider.kind === 'managed'}
		<div class="text-xs text-gray-500">
			{$i18n.t('Aucune clé à saisir pour ce fournisseur.')}
		</div>
	{:else}
		{#each provider.fields as field}
			<label class="block mb-2">
				<span class="text-xs text-gray-600 dark:text-gray-400">{field.label}</span>
				<input
					class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mt-1"
					type={field.secret ? 'password' : 'text'}
					placeholder={field.present
						? $i18n.t('Renseigné — laisse vide pour conserver')
						: (field.default ?? '')}
					bind:value={values[field.key]}
				/>
				{#if field.url}
					<a
						class="text-[11px] text-sky-600 dark:text-sky-400 underline"
						href={field.url}
						target="_blank"
						rel="noopener">{$i18n.t('Obtenir cette valeur')}</a
					>
				{/if}
			</label>
		{/each}
		<div class="flex gap-2 mt-1 items-center">
			<button
				class="text-xs px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50"
				on:click={save}
				disabled={saving}
			>
				{$i18n.t('Enregistrer')}
			</button>
			<button
				class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 flex items-center gap-1.5"
				on:click={testKey}
				disabled={testing}
			>
				{#if testing}<Spinner className="size-3" />{/if}
				{testing ? $i18n.t('Test…') : $i18n.t('Tester')}
			</button>
			{#if providerStatus(provider) === 'saved'}
				<button
					class="text-xs px-3 py-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition disabled:opacity-50 flex items-center gap-1.5 ml-auto"
					on:click={() => (showDisconnectConfirm = true)}
					disabled={disconnecting}
				>
					{#if disconnecting}<Spinner className="size-3" />{/if}
					{$i18n.t('Déconnecter')}
				</button>
			{/if}
		</div>
		{#if testResult}
			<div
				class="text-xs mt-2 {testResult.tested && testResult.ok
					? 'text-green-600 dark:text-green-400'
					: testResult.tested
						? 'text-red-600 dark:text-red-400'
						: 'text-gray-500 dark:text-gray-400'}"
			>
				{testResult.tested ? (testResult.ok ? '✅' : '❌') : 'ℹ️'}
				{testResult.reason}
			</div>
		{/if}
	{/if}
</div>

<ConfirmDialog
	bind:show={showDisconnectConfirm}
	title={$i18n.t('Déconnecter ce fournisseur ?')}
	message={$i18n.t(
		'Les identifiants enregistrés pour ce fournisseur seront effacés. Vous pourrez le reconnecter plus tard.'
	)}
	confirmLabel={$i18n.t('Déconnecter')}
	onConfirm={disconnect}
/>
