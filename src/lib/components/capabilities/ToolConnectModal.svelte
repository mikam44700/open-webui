<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getToolConnection,
		setToolKey,
		testToolKey,
		disconnectToolProvider,
		startToolOAuth,
		getToolOAuthStatus,
		getSearxngStatus,
		installSearxng,
		uninstallSearxng,
		checkSearxngUpdate,
		startSearxngUpdate,
		getSearxngUpdateStatus
	} from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import UpdateButton from '$lib/components/connectors/UpdateButton.svelte';
	import { TOOLSET_FR } from '$lib/utils/toolsetLabels';

	let showDisconnectConfirm = false;
	let pendingDisconnect: Provider | null = null;

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
	// Vision (vision)
	import openrouterLogo from '$lib/assets/providers/openrouter.svg';
	// Génération d'images (image_gen)
	import falLogo from '$lib/assets/web-providers/fal.jpg';
	import kreaLogo from '$lib/assets/web-providers/krea.png';
	import openaiLogo from '$lib/assets/providers/openai.svg';
	import codexLogo from '$lib/assets/providers/codex.png';
	import grokLogo from '$lib/assets/providers/grok.svg';
	// Synthèse vocale (tts)
	import edgeLogo from '$lib/assets/web-providers/edge.jpg';
	import elevenlabsLogo from '$lib/assets/web-providers/elevenlabs.png';
	import kittenLogo from '$lib/assets/web-providers/kitten.webp';
	import piperLogo from '$lib/assets/web-providers/piper.svg';
	import mistralLogo from '$lib/assets/providers/mistral-color.svg';
	import geminiLogo from '$lib/assets/providers/gemini-color.svg';
	// Automatisation & intégrations (homeassistant, spotify)
	import homeassistantLogo from '$lib/assets/web-providers/homeassistant.png';
	import spotifyLogo from '$lib/assets/web-providers/spotify.png';

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
		cua: cuaLogo,
		openrouter: openrouterLogo,
		fal: falLogo,
		krea: kreaLogo,
		openai: openaiLogo,
		codex: codexLogo,
		grok: grokLogo,
		edge: edgeLogo,
		elevenlabs: elevenlabsLogo,
		kitten: kittenLogo,
		piper: piperLogo,
		mistral: mistralLogo,
		gemini: geminiLogo,
		homeassistant: homeassistantLogo,
		spotify: spotifyLogo
	};

	// Logos au tracé sombre/transparent : illisibles sur fond sombre → fond blanc.
	const WHITE_BG_SLUGS = new Set([
		'tavily',
		'parallel',
		'xai',
		'camofox',
		'chromium',
		'openrouter',
		'krea',
		'openai',
		'grok',
		'piper',
		'elevenlabs',
		'mistral',
		'gemini'
	]);

	// Fournisseurs qui tournent en local (modèle téléchargé à la 1re utilisation) : pas de clé,
	// mais pas « actif » d'office non plus → libellé neutre « Sans clé · local ».
	const LOCAL_SLUGS = new Set(['kitten', 'piper']);

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
		connected?: boolean | null;
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
	// - detected    : géré via compte/OAuth et réellement connecté (Codex, xAI Grok détectés)
	// - disconnected: géré via compte/OAuth mais PAS connecté → action requise ailleurs
	// - active      : service en ligne sans clé, marche tout de suite (DuckDuckGo, Edge TTS…)
	// - local       : tourne en local sans clé, mais modèle téléchargé à la 1re utilisation
	// - subscription: géré, nécessite un abonnement Nous actif (état réel non vérifiable ici)
	const providerStatus = (
		p: Provider
	): 'saved' | 'detected' | 'disconnected' | 'active' | 'local' | 'subscription' | 'none' => {
		if (p.kind === 'managed') {
			if (p.slug && SUBSCRIPTION_SLUGS.has(p.slug)) return 'subscription';
			if (p.slug && LOCAL_SLUGS.has(p.slug)) return 'local';
			if (p.connected === true) return 'detected';
			if (p.connected === false) return 'disconnected';
			return 'active';
		}
		if (p.kind === 'key' && p.fields.length > 0 && p.fields.every((f) => f.present))
			return 'saved';
		return 'none';
	};

	let loading = false;
	let saving = false;
	let connected = false;
	let providers: Provider[] = [];
	// Encart d'information optionnel affiché en haut (ex. vision : « si ton modèle gère les images… »).
	let note: string | null = null;
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

	// SearXNG : recherche web souveraine installée à la demande (1 clic).
	let searxngStatus: { installed: boolean; running: boolean; active: boolean } = {
		installed: false,
		running: false,
		active: false
	};
	let searxngBusy = false;
	// Un provider est « SearXNG » s'il déclare le champ SEARXNG_URL (robuste, indépendant du libellé).
	const isSearxng = (p: Provider) => (p.fields ?? []).some((f) => f.key === 'SEARXNG_URL');
	$: hasSearxng = providers.some(isSearxng);

	const refreshSearxngStatus = async () => {
		try {
			searxngStatus = await getSearxngStatus(localStorage.token);
		} catch {
			/* statut indisponible : on laisse les valeurs par défaut */
		}
	};

	const installSearxngNow = async () => {
		searxngBusy = true;
		try {
			searxngStatus = await installSearxng(localStorage.token);
			if (searxngStatus.active) {
				toast.success($i18n.t('Recherche avancée installée et activée'));
				dispatch('connected');
			} else {
				toast.error($i18n.t('Installation terminée mais non active — réessaie'));
			}
		} catch (e) {
			toast.error($i18n.t('Échec de l’installation de la recherche avancée'));
		} finally {
			searxngBusy = false;
		}
	};

	const uninstallSearxngNow = async () => {
		searxngBusy = true;
		try {
			searxngStatus = await uninstallSearxng(localStorage.token);
			toast.success($i18n.t('Recherche avancée désinstallée'));
			dispatch('disconnected');
		} catch (e) {
			toast.error($i18n.t('Échec de la désinstallation'));
		} finally {
			searxngBusy = false;
		}
	};

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
			note = res?.note ?? null;
			showAdvanced = false;
			testing = {};
			testResults = {};
			values = {};
			for (const p of providers) {
				for (const f of p.fields) {
					// pré-remplit le défaut seulement si non sensible et non déjà renseigné
					if (f.default && !f.present && !f.secret) values[f.key] = f.default;
				}
			}
			// Si l'outil propose SearXNG, on récupère son état d'installation (conteneur).
			if (providers.some((p) => (p.fields ?? []).some((f) => f.key === 'SEARXNG_URL'))) {
				await refreshSearxngStatus();
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
			// reflète localement les champs enregistrés → la pastille « enregistrée » et le
			// bouton « Déconnecter » apparaissent aussitôt, sans rouvrir la fenêtre.
			for (const f of provider.fields) if (payload[f.key]) f.present = true;
			providers = providers;
			toast.success($i18n.t('Connexion enregistrée'));
			dispatch('connected');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Échec de l’enregistrement'));
		} finally {
			saving = false;
		}
	};

	// Test RÉEL par fournisseur : envoie les valeurs saisies (ou vides → clé enregistrée).
	type TestResult = { tested: boolean; ok: boolean; reason: string };
	let testing: Record<string, boolean> = {};
	let testResults: Record<string, TestResult> = {};

	const testKey = async (provider: Provider) => {
		if (!toolset) return;
		const payload: Record<string, string> = {};
		for (const f of provider.fields) payload[f.key] = (values[f.key] ?? '').trim();
		testing = { ...testing, [provider.name]: true };
		try {
			const res = await testToolKey(localStorage.token, toolset.name, payload);
			testResults = { ...testResults, [provider.name]: res };
			if (res?.tested && res?.ok) {
				// clé valide → reflète l'enregistrement dans la pastille
				for (const f of provider.fields) if (payload[f.key]) f.present = true;
				providers = providers;
			}
		} catch (err: any) {
			testResults = {
				...testResults,
				[provider.name]: {
					tested: false,
					ok: false,
					reason: err?.error?.message ?? $i18n.t('Le test a échoué')
				}
			};
		} finally {
			testing = { ...testing, [provider.name]: false };
		}
	};

	// Déconnecte un SEUL fournisseur : efface ses clés, sans toucher aux autres ni à l'outil.
	let disconnecting: Record<string, boolean> = {};

	const disconnectProvider = async (provider: Provider) => {
		if (!toolset) return;
		const keys = provider.fields.map((f) => f.key);
		if (keys.length === 0) return;
		disconnecting = { ...disconnecting, [provider.name]: true };
		try {
			await disconnectToolProvider(localStorage.token, toolset.name, keys);
			// reflète la déconnexion localement (clés effacées) sans recharger toute la fenêtre
			for (const f of provider.fields) {
				f.present = false;
				values[f.key] = '';
			}
			providers = providers;
			testResults = { ...testResults, [provider.name]: undefined as never };
			toast.success($i18n.t('{{provider}} déconnecté', { provider: provider.name }));
			dispatch('disconnected');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Échec de la déconnexion'));
		} finally {
			disconnecting = { ...disconnecting, [provider.name]: false };
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

						{#if isSearxng(provider)}
							<!-- Recherche souveraine : installation/désinstallation en 1 clic (conteneur Docker). -->
							<div class="mb-3 rounded-xl border border-gray-100 dark:border-gray-850 p-3">
								{#if searxngStatus.active}
									<div class="flex items-center justify-between gap-2 flex-wrap">
										<span class="text-xs text-green-600 dark:text-green-500 flex items-center gap-1.5">
											● {$i18n.t('Recherche avancée installée et active')}
										</span>
										<div class="flex items-center gap-2 flex-none">
											<UpdateButton
												enabled={searxngStatus.active}
												toolLabel={$i18n.t('La recherche web')}
												check={() => checkSearxngUpdate(localStorage.token)}
												start={() => startSearxngUpdate(localStorage.token)}
												poll={() => getSearxngUpdateStatus(localStorage.token)}
												on:updated={refreshSearxngStatus}
											/>
											<button
												class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 flex items-center gap-1.5"
												on:click={uninstallSearxngNow}
												disabled={searxngBusy}
											>
												{#if searxngBusy}<Spinner className="size-3" />{/if}
												{$i18n.t('Désinstaller')}
											</button>
										</div>
									</div>
								{:else}
									<div class="text-xs text-gray-500 mb-2">
										{$i18n.t('Recherche web souveraine, installée en un clic — rien à configurer.')}
									</div>
									<button
										class="text-xs px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50 flex items-center gap-1.5"
										on:click={installSearxngNow}
										disabled={searxngBusy}
									>
										{#if searxngBusy}<Spinner className="size-3" />{/if}
										{searxngBusy ? $i18n.t('Installation en cours…') : $i18n.t('Installer')}
									</button>
								{/if}
							</div>
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
						{:else if !isSearxng(provider)}
							<!-- SearXNG : pas de champ manuel — le bouton « Installer » ci-dessus suffit. -->
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
									on:click={() => save(provider)}
									disabled={saving}
								>
									{$i18n.t('Enregistrer')}
								</button>
								<button
									class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 flex items-center gap-1.5"
									on:click={() => testKey(provider)}
									disabled={testing[provider.name]}
								>
									{#if testing[provider.name]}<Spinner className="size-3" />{/if}
									{testing[provider.name] ? $i18n.t('Test…') : $i18n.t('Tester')}
								</button>
								{#if providerStatus(provider) === 'saved'}
									<button
										class="text-xs px-3 py-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition disabled:opacity-50 flex items-center gap-1.5 ml-auto"
										on:click={() => {
											pendingDisconnect = provider;
											showDisconnectConfirm = true;
										}}
										disabled={disconnecting[provider.name]}
									>
										{#if disconnecting[provider.name]}<Spinner className="size-3" />{/if}
										{$i18n.t('Déconnecter')}
									</button>
								{/if}
							</div>
							{#if testResults[provider.name]}
								{@const r = testResults[provider.name]}
								<div
									class="text-xs mt-2 {r.tested && r.ok
										? 'text-green-600 dark:text-green-400'
										: r.tested
											? 'text-red-600 dark:text-red-400'
											: 'text-gray-500 dark:text-gray-400'}"
								>
									{r.tested ? (r.ok ? '✅' : '❌') : 'ℹ️'}
									{r.reason}
								</div>
							{/if}
						{/if}
					</div>
				{/snippet}

				{#if note}
					<div
						class="text-xs leading-relaxed text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-900/40 rounded-xl px-3 py-2.5 mb-3"
					>
						{note}
					</div>
				{/if}

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

				<div class="flex justify-end mt-4">
					<button
						class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						on:click={close}
					>
						{$i18n.t('Fermer')}
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}

<ConfirmDialog
	bind:show={showDisconnectConfirm}
	title={$i18n.t('Déconnecter ce fournisseur ?')}
	message={$i18n.t(
		'Les identifiants enregistrés pour ce fournisseur seront effacés. Vous pourrez le reconnecter plus tard.'
	)}
	confirmLabel={$i18n.t('Déconnecter')}
	onConfirm={() => {
		if (pendingDisconnect) disconnectProvider(pendingDisconnect);
	}}
/>
