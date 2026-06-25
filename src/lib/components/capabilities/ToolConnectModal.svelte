<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getToolConnection,
		setToolKey,
		testToolConnection,
		disconnectTool,
		startToolOAuth,
		getToolOAuthStatus
	} from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { TOOLSET_FR } from '$lib/utils/toolsetLabels';

	// Logos des fournisseurs de recherche web (mappés par `slug` renvoyé par le bridge).
	import duckduckgoLogo from '$lib/assets/web-providers/duckduckgo.png';
	import exaLogo from '$lib/assets/web-providers/exa.jpeg';
	import firecrawlLogo from '$lib/assets/web-providers/firecrawl.png';
	import braveLogo from '$lib/assets/web-providers/brave.webp';
	import tavilyLogo from '$lib/assets/web-providers/tavily.png';
	import parallelLogo from '$lib/assets/web-providers/parallel.svg';
	import searxngLogo from '$lib/assets/web-providers/searxng.png';
	import xaiLogo from '$lib/assets/web-providers/xai.png';
	import nousLogo from '$lib/assets/providers/nousresearch.png';
	// Navigateur automatisé (toolset « browser »)
	import chromiumLogo from '$lib/assets/web-providers/chromium.png';
	import camofoxLogo from '$lib/assets/web-providers/camofox.png';
	import browserUseLogo from '$lib/assets/web-providers/browser-use.png';
	import browserbaseLogo from '$lib/assets/web-providers/browserbase.png';
	// Recherche X (x_search) + Computer Use (computer_use)
	import cuaLogo from '$lib/assets/web-providers/cua.png';

	const LOGO_BY_SLUG: Record<string, string> = {
		duckduckgo: duckduckgoLogo,
		exa: exaLogo,
		firecrawl: firecrawlLogo,
		brave: braveLogo,
		tavily: tavilyLogo,
		parallel: parallelLogo,
		searxng: searxngLogo,
		xai: xaiLogo,
		nous: nousLogo,
		chromium: chromiumLogo,
		camofox: camofoxLogo,
		'browser-use': browserUseLogo,
		browserbase: browserbaseLogo,
		cua: cuaLogo
	};

	// Logos au tracé sombre/transparent : illisibles sur fond sombre → fond blanc.
	const WHITE_BG_SLUGS = new Set(['tavily', 'parallel', 'xai', 'camofox', 'chromium']);

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;
	export let toolset: { name: string; label: string } | null = null;

	type Field = {
		key: string;
		label: string;
		default: string | null;
		url: string | null;
		secret: boolean;
		present: boolean;
	};
	type Provider = {
		name: string;
		tag: string | null;
		badge: string | null;
		kind: string;
		fields: Field[];
		slug?: string | null;
		advanced?: boolean;
		category?: string | null;
	};

	// Regroupement des fournisseurs avancés (mode Expert) par catégorie, dans cet ordre.
	const CATEGORY_ORDER = ['free', 'self_hosted', 'paid'];
	const CATEGORY_LABEL: Record<string, string> = {
		free: 'Gratuit',
		self_hosted: 'Auto-hébergé · serveur à lancer',
		paid: 'Payant'
	};

	// Fournisseurs « gérés » qui dépendent d'un abonnement payant (pas actifs d'office).
	const SUBSCRIPTION_SLUGS = new Set(['nous']);

	// État affiché par fournisseur. On n'affirme QUE ce qu'on sait avec certitude :
	// - saved       : kind=key avec toutes ses clés saisies (saisie ≠ clé valide : « Tester »
	//                 ne vérifie que la présence, pas un vrai appel API → on ne dit pas « connecté »)
	// - active      : gratuit/local, marche sans rien (DuckDuckGo, cua, Chromium local)
	// - subscription: géré, nécessite un abonnement Nous actif (état réel non vérifiable ici)
	const providerStatus = (p: Provider): 'saved' | 'active' | 'subscription' | 'none' => {
		if (p.kind === 'managed')
			return p.slug && SUBSCRIPTION_SLUGS.has(p.slug) ? 'subscription' : 'active';
		if (p.kind === 'key' && p.fields.length > 0 && p.fields.every((f) => f.present))
			return 'saved';
		return 'none';
	};

	let loading = false;
	let saving = false;
	let connected = false;
	let providers: Provider[] = [];
	// Fournisseurs techniques (clé API ou serveur à lancer) repliés sous « Options avancées ».
	let showAdvanced = false;
	$: standardProviders = providers.filter((p) => !p.advanced);
	$: advancedProviders = providers.filter((p) => p.advanced);
	// Avancés regroupés par catégorie (gratuit → auto-hébergé → payant), groupes vides masqués.
	$: advancedByCategory = CATEGORY_ORDER.map((cat) => ({
		cat,
		items: advancedProviders.filter((p) => (p.category ?? 'paid') === cat)
	})).filter((g) => g.items.length > 0);
	// Valeurs saisies par clé de champ (jamais pré-remplies pour les secrets déjà présents).
	let values: Record<string, string> = {};

	// Suivi OAuth
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

	const load = async () => {
		if (!toolset) return;
		loading = true;
		try {
			const res = await getToolConnection(localStorage.token, toolset.name);
			connected = res?.connected ?? false;
			providers = res?.providers ?? [];
			showAdvanced = false;
			values = {};
			for (const p of providers) {
				for (const f of p.fields) {
					// pré-remplit le défaut seulement si non sensible et non déjà renseigné
					if (f.default && !f.present && !f.secret) values[f.key] = f.default;
				}
			}
		} catch {
			toast.error($i18n.t('Impossible de charger la connexion de cet outil'));
		} finally {
			loading = false;
		}
	};

	$: if (open && toolset) {
		load();
	} else if (!open) {
		stopOAuth();
	}

	onDestroy(stopOAuth);

	const save = async (provider: Provider) => {
		if (!toolset) return;
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
			const res = await setToolKey(localStorage.token, toolset.name, payload);
			connected = res?.connection_state === 'connected';
			toast.success($i18n.t('Connexion enregistrée'));
			dispatch('connected');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Échec de l’enregistrement'));
		} finally {
			saving = false;
		}
	};

	const test = async () => {
		if (!toolset) return;
		try {
			const res = await testToolConnection(localStorage.token, toolset.name);
			if (res?.ok) toast.success($i18n.t('Connexion valide'));
			else toast.error(res?.reason ?? $i18n.t('Connexion incomplète'));
		} catch {
			toast.error($i18n.t('Le test a échoué'));
		}
	};

	const disconnect = async () => {
		if (!toolset) return;
		try {
			await disconnectTool(localStorage.token, toolset.name);
			connected = false;
			toast.success($i18n.t('Outil déconnecté'));
			dispatch('disconnected');
			close();
		} catch {
			toast.error($i18n.t('Échec de la déconnexion'));
		}
	};

	const pollOAuth = async () => {
		if (!toolset) return;
		try {
			const s = await getToolOAuthStatus(localStorage.token, toolset.name);
			oauthAuthUrl = s?.auth_url ?? null;
			oauthLog = s?.log ?? '';
			oauthRunning = s?.status === 'running';
			if (s?.status === 'success') {
				stopOAuth();
				connected = true;
				toast.success($i18n.t('Connecté avec succès.'));
				dispatch('connected');
			} else if (s?.status === 'error') {
				stopOAuth();
				toast.error($i18n.t('La connexion a échoué. Réessaie.'));
			}
		} catch {
			stopOAuth();
		}
	};

	const startOAuth = async () => {
		if (!toolset) return;
		try {
			await startToolOAuth(localStorage.token, toolset.name);
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

	const close = () => {
		stopOAuth();
		dispatch('close');
	};
</script>

{#if open && toolset}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click|self={close}
	>
		<div
			class="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-xl"
		>
			<div class="flex items-center justify-between mb-3">
				<div class="text-sm font-medium">
					{$i18n.t('Connecter')} — {TOOLSET_FR[toolset.name]?.label ?? toolset.label}
				</div>
				<button
					class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
					on:click={close}>✕</button
				>
			</div>

			{#if loading}
				<div class="flex justify-center py-10"><Spinner className="size-5" /></div>
			{:else}
				{#snippet providerCard(provider: Provider)}
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
								{:else if providerStatus(provider) === 'active'}
									<span
										class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-500"
										>{$i18n.t('Actif sans clé')}</span
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
							<div class="flex gap-2 mt-1">
								<button
									class="text-xs px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50"
									on:click={() => save(provider)}
									disabled={saving}
								>
									{$i18n.t('Enregistrer')}
								</button>
							</div>
						{/if}
					</div>
				{/snippet}

				{#each standardProviders as provider}
					{@render providerCard(provider)}
				{/each}

				{#if advancedProviders.length > 0}
					<button
						type="button"
						class="w-full flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition mb-3"
						on:click={() => (showAdvanced = !showAdvanced)}
					>
						<span class="font-medium"
							>{$i18n.t('Options avancées (Expert)')} · {advancedProviders.length}</span
						>
						<span aria-hidden="true">{showAdvanced ? '▴' : '▾'}</span>
					</button>
					{#if showAdvanced}
						<div class="text-[11px] text-gray-400 mb-3 -mt-1 px-1">
							{$i18n.t(
								'Pour utilisateurs avancés : nécessite une clé API ou un serveur à lancer soi-même.'
							)}
						</div>
						{#each advancedByCategory as group (group.cat)}
							<div
								class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2 px-1"
							>
								{CATEGORY_LABEL[group.cat]}
							</div>
							{#each group.items as provider}
								{@render providerCard(provider)}
							{/each}
						{/each}
					{/if}
				{/if}

				{#if providers.length === 0}
					<div class="text-xs text-gray-500 py-4">
						{$i18n.t('Aucune connexion requise pour cet outil.')}
					</div>
				{/if}

				{#if oauthLog}
					<pre
						class="mt-1 max-h-32 overflow-y-auto text-[11px] bg-gray-50 dark:bg-gray-850 rounded-lg p-2 whitespace-pre-wrap">{oauthLog}</pre>
				{/if}

				<div class="flex justify-between mt-4">
					<div>
						{#if connected}
							<button
								class="text-xs px-3 py-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition"
								on:click={disconnect}
							>
								{$i18n.t('Déconnecter')}
							</button>
						{/if}
					</div>
					<div class="flex gap-2">
						<button
							class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={test}
						>
							{$i18n.t('Tester')}
						</button>
						<button
							class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={close}
						>
							{$i18n.t('Fermer')}
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
