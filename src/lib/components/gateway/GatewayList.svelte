<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getGatewayStatus,
		getMessagingPlatforms,
		updateMessagingPlatform,
		testMessagingPlatform,
		generateApiServerKey,
		restartGateway,
		startTelegramPairing,
		pollTelegramPairing,
		applyTelegramPairing,
		cancelTelegramPairing,
		listPlatformUsers,
		approvePlatformUser,
		revokePlatformUser,
		disconnectPlatform,
		getTelegramBotInfo,
		type GatewayStatus,
		type MessagingPlatform,
		type MessagingEnvVar,
		type TelegramPairingStart,
		type MessagingUser,
		type TelegramBotInfo
	} from '$lib/apis/gateway';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { expertMode } from '$lib/stores';
	import { CHANNEL_FR, CHANNEL_TAGS } from '$lib/utils/channelLabels';

	// Déroulant « Voir ce que ça fait » ouvert, par canal (id → booléen).
	let aboutOpen: Record<string, boolean> = {};

	let showRestartConfirm = false;
	let showRegenConfirm = false;

	import telegramLogo from '$lib/assets/messaging/telegram.png';
	import discordLogo from '$lib/assets/messaging/discord.jpg';
	import slackLogo from '$lib/assets/messaging/slack.png';
	import whatsappLogo from '$lib/assets/messaging/whatsapp.png';
	import signalLogo from '$lib/assets/messaging/signal.png';
	import emailLogo from '$lib/assets/messaging/email.svg';
	import smsLogo from '$lib/assets/messaging/sms.jpg';
	import imessageLogo from '$lib/assets/messaging/imessage.jpg';

	const i18n = getContext('i18n');

	// Vrais logos des canaux ; fallback sur l'emoji si l'id n'est pas mappé.
	const LOGO_BY_ID: Record<string, string> = {
		telegram: telegramLogo,
		discord: discordLogo,
		slack: slackLogo,
		whatsapp_cloud: whatsappLogo,
		signal: signalLogo,
		email: emailLogo,
		sms: smsLogo,
		bluebubbles: imessageLogo
	};
	// Logos « carré plein » (fond intégré) → affichés bord à bord pour remplir le carré.
	const LOGO_FULL_BLEED = new Set(['discord', 'signal', 'whatsapp_cloud', 'sms', 'bluebubbles']);
	// Fond de couleur de marque pour les logos dont les coins sont transparents (sinon on
	// verrait le blanc de la carte). WhatsApp = carré arrondi vert sur fond transparent.
	const LOGO_BG: Record<string, string> = { whatsapp_cloud: 'bg-[#25D366]' };

	let loading = true;
	let bridgeDown = false;

	let status: GatewayStatus | null = null;
	let platforms: MessagingPlatform[] = [];
	let gatewayRunning = false;

	let restarting = false;
	let generatingKey = false;

	// état par plateforme
	let busy: string | null = null;
	let messages: Record<string, { ok: boolean; message: string } | null> = {};
	let drafts: Record<string, Record<string, string>> = {};
	let cleared: Record<string, string[]> = {};
	let visibleKeys: Record<string, boolean> = {};

	// modale de configuration
	let modalPlatform: MessagingPlatform | null = null;
	let showAdvanced = false;
	let showTokenForm = false; // Telegram : « méthode avancée » (coller un token brut)

	// Onboarding Telegram « managed bot » (QR) — état de la modale ouverte.
	type PairStatus = 'idle' | 'waiting' | 'applying' | 'error';
	let pairing: TelegramPairingStart | null = null;
	let pairLinkCopied = false; // « Copier le lien » (parcours mobile)
	let pairStatus: PairStatus = 'idle';
	let pairError = '';
	let pairTimer: ReturnType<typeof setInterval> | null = null;

	// Accès & partage (allowlist) — utilisateurs de la plateforme ouverte.
	let approvedUsers: MessagingUser[] = [];
	let pendingUsers: MessagingUser[] = [];
	let usersBusy = false;
	let botInfo: TelegramBotInfo | null = null; // nom + lien du bot (à partager)
	let botLinkCopied = false;

	// Déconnexion
	let showDisconnectConfirm = false;
	let disconnecting = false;

	let refreshTimer: ReturnType<typeof setInterval> | null = null;

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	// Canaux non prêts (available === false) : masqués au client, visibles en mode expert
	// (pour la config/livraison). Réactivation = passer available:true → réapparaît pour tous.
	$: filtered = $expertMode ? platforms : platforms.filter((p) => p.available !== false);

	// Garde la modale ouverte synchronisée avec la liste rafraîchie (état « connecté »
	// après un redémarrage du gateway, toggle, etc.) — sinon elle reste figée.
	$: if (modalPlatform) {
		const fresh = platforms.find((x) => x.id === modalPlatform.id);
		if (fresh && fresh !== modalPlatform) modalPlatform = fresh;
	}

	const load = async (silent = false) => {
		if (!silent) loading = true;
		bridgeDown = false;
		try {
			const token = localStorage.token;
			const [st, pl] = await Promise.all([
				getGatewayStatus(token),
				getMessagingPlatforms(token)
			]);
			status = st;
			platforms = pl?.platforms ?? [];
			gatewayRunning = pl?.gateway_running ?? false;
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else if (!silent) {
				toast.error($i18n.t('Échec du chargement'));
			}
		} finally {
			loading = false;
		}
	};

	const stateLabel = (s: string) => {
		switch (s) {
			case 'connected':
				return { label: $i18n.t('Connecté'), tone: 'ok' };
			case 'needs_setup':
				return { label: $i18n.t('À configurer'), tone: 'warn' };
			case 'ready':
				return { label: $i18n.t('Prêt'), tone: 'muted' };
			default:
				// « Désactivé » : redondant avec l'interrupteur on/off → pas de chip.
				return { label: '', tone: 'muted' };
		}
	};

	const draftKey = (id: string, key: string) => `${id}:${key}`;

	const hasDraft = (p: MessagingPlatform) => {
		const d = drafts[p.id] ?? {};
		const anyValue = Object.values(d).some((v) => v.trim());
		const anyCleared = (cleared[p.id] ?? []).length > 0;
		return anyValue || anyCleared;
	};

	const handleChange = (id: string, key: string, value: string) => {
		drafts = { ...drafts, [id]: { ...(drafts[id] ?? {}), [key]: value } };
		if (value.trim()) {
			cleared = { ...cleared, [id]: (cleared[id] ?? []).filter((k) => k !== key) };
		}
	};

	const clearField = (id: string, key: string) => {
		drafts = { ...drafts, [id]: { ...(drafts[id] ?? {}), [key]: '' } };
		const list = cleared[id] ?? [];
		if (!list.includes(key)) cleared = { ...cleared, [id]: [...list, key] };
	};

	const toggleVisibility = (id: string, key: string) => {
		const k = draftKey(id, key);
		visibleKeys = { ...visibleKeys, [k]: !visibleKeys[k] };
	};

	const toggleEnable = async (p: MessagingPlatform) => {
		busy = p.id;
		messages = { ...messages, [p.id]: null };
		try {
			await updateMessagingPlatform(localStorage.token, p.id, { enabled: !p.enabled });
			await load(true);
		} catch (err) {
			toast.error($i18n.t('Action impossible'));
		} finally {
			busy = null;
		}
	};

	const savePlatform = async (p: MessagingPlatform) => {
		const d = drafts[p.id] ?? {};
		const env: Record<string, string> = {};
		for (const [k, v] of Object.entries(d)) {
			if (v.trim()) env[k] = v;
		}
		const clear_env = cleared[p.id] ?? [];
		if (Object.keys(env).length === 0 && clear_env.length === 0) return;

		busy = p.id;
		messages = { ...messages, [p.id]: null };
		try {
			await updateMessagingPlatform(localStorage.token, p.id, { env, clear_env });
			drafts = { ...drafts, [p.id]: {} };
			cleared = { ...cleared, [p.id]: [] };
			toast.success($i18n.t('Configuration enregistrée'));
			await load(true);
			// rafraîchir la plateforme ouverte dans la modale
			if (modalPlatform?.id === p.id) {
				modalPlatform = platforms.find((x) => x.id === p.id) ?? null;
			}
		} catch (err) {
			toast.error($i18n.t('Échec de l’enregistrement'));
		} finally {
			busy = null;
		}
	};

	const testPlatform = async (p: MessagingPlatform) => {
		busy = p.id;
		try {
			const res = await testMessagingPlatform(localStorage.token, p.id);
			messages = { ...messages, [p.id]: res };
		} catch (err) {
			messages = { ...messages, [p.id]: { ok: false, message: $i18n.t('Test impossible') } };
		} finally {
			busy = null;
		}
	};

	const onGenerateKey = async () => {
		generatingKey = true;
		try {
			await generateApiServerKey(localStorage.token);
			toast.success($i18n.t('Clé API générée'));
			await load(true);
		} catch (err) {
			toast.error($i18n.t('Échec de la génération'));
		} finally {
			generatingKey = false;
		}
	};

	const onRestart = async () => {
		restarting = true;
		try {
			const res = await restartGateway(localStorage.token);
			if (res?.ok) {
				toast.success($i18n.t('Gateway redémarré'));
			} else {
				toast.error(res?.error || $i18n.t('Échec du redémarrage'));
			}
			setTimeout(() => load(true), 4000);
		} catch (err) {
			toast.error($i18n.t('Échec du redémarrage'));
		} finally {
			restarting = false;
		}
	};

	const isTelegram = (p: MessagingPlatform | null) => p?.id === 'telegram';

	// Canal affiché mais pas encore branchable (ex. WhatsApp en attente de config Meta).
	const isUnavailable = (p: MessagingPlatform | null) => p?.available === false;

	const stopPairPolling = () => {
		if (pairTimer) {
			clearInterval(pairTimer);
			pairTimer = null;
		}
	};

	const resetPairing = () => {
		stopPairPolling();
		if (pairing) {
			// on oublie le pairing côté serveur (best-effort)
			cancelTelegramPairing(localStorage.token, pairing.pairing_id).catch(() => {});
		}
		pairing = null;
		pairStatus = 'idle';
		pairError = '';
		pairLinkCopied = false;
	};

	// Lance le parcours : crée le pairing (lien à ouvrir dans Telegram), démarre le polling.
	// NB : le lien de création de bot s'ouvre en CLIQUANT (desktop ou mobile), pas en scannant
	// un QR — le scan passe par le navigateur et n'aboutit pas. On n'affiche donc pas de QR.
	const startPairing = async () => {
		pairStatus = 'waiting';
		pairError = '';
		try {
			pairing = await startTelegramPairing(localStorage.token);
			stopPairPolling();
			pairTimer = setInterval(pollPairingOnce, 2500);
		} catch (err) {
			pairStatus = 'error';
			pairError = $i18n.t('Impossible de démarrer la connexion. Réessaie.');
		}
	};

	const copyPairLink = async () => {
		if (!pairing?.deep_link) return;
		try {
			await navigator.clipboard.writeText(pairing.deep_link);
			pairLinkCopied = true;
			setTimeout(() => (pairLinkCopied = false), 1800);
		} catch (err) {
			toast.error($i18n.t('Copie impossible'));
		}
	};

	// Un tour de polling : quand le bot est créé (ready), on applique automatiquement.
	const pollPairingOnce = async () => {
		if (!pairing || pairStatus === 'applying') return;
		try {
			const st = await pollTelegramPairing(localStorage.token, pairing.pairing_id);
			if (st.status === 'ready') {
				stopPairPolling();
				pairStatus = 'applying';
				const res = await applyTelegramPairing(localStorage.token, pairing.pairing_id);
				if (res?.ok) {
					toast.success($i18n.t('Telegram connecté !'));
					pairing = null;
					// Le gateway redémarre (quelques secondes) : on reste en « applying »
					// (« Connexion en cours… ») et on rafraîchit jusqu'à l'état « connecté ».
					for (let i = 0; i < 8; i++) {
						await load(true);
						const fresh = platforms.find((x) => x.id === modalPlatform?.id);
						if (fresh) modalPlatform = fresh;
						if (fresh?.state === 'connected') break;
						await new Promise((r) => setTimeout(r, 2000));
					}
					pairStatus = 'idle';
					if (modalPlatform) loadUsers(modalPlatform);
				} else {
					pairStatus = 'error';
					pairError = res?.restart_error || res?.error || $i18n.t('La connexion a échoué.');
				}
			}
		} catch (err) {
			// pairing expiré / introuvable → on invite à relancer
			stopPairPolling();
			pairStatus = 'error';
			pairError = $i18n.t('Le code a expiré. Relance la connexion.');
		}
	};

	// --- Accès & partage -----------------------------------------------------

	const loadUsers = async (p: MessagingPlatform | null) => {
		if (!p || !isTelegram(p)) return;
		usersBusy = true;
		try {
			const [res, info] = await Promise.all([
				listPlatformUsers(localStorage.token, p.id),
				getTelegramBotInfo(localStorage.token).catch(() => null)
			]);
			approvedUsers = res?.approved ?? [];
			pendingUsers = res?.pending ?? [];
			botInfo = info;
		} catch (err) {
			// silencieux : la section reste vide
		} finally {
			usersBusy = false;
		}
	};

	const copyBotLink = async () => {
		if (!botInfo?.link) return;
		try {
			await navigator.clipboard.writeText(botInfo.link);
			botLinkCopied = true;
			setTimeout(() => (botLinkCopied = false), 1800);
		} catch (err) {
			toast.error($i18n.t('Copie impossible'));
		}
	};

	const approveUser = async (p: MessagingPlatform, u: MessagingUser) => {
		usersBusy = true;
		try {
			await approvePlatformUser(localStorage.token, p.id, {
				code: u.pending_code ?? undefined,
				user_id: u.user_id,
				user_name: u.user_name
			});
			toast.success($i18n.t('Accès autorisé'));
			await loadUsers(p);
		} catch (err) {
			toast.error($i18n.t('Action impossible'));
		} finally {
			usersBusy = false;
		}
	};

	const revokeUser = async (p: MessagingPlatform, u: MessagingUser) => {
		usersBusy = true;
		try {
			await revokePlatformUser(localStorage.token, p.id, u.user_id);
			toast.success($i18n.t('Accès retiré'));
			await loadUsers(p);
		} catch (err) {
			toast.error($i18n.t('Action impossible'));
		} finally {
			usersBusy = false;
		}
	};

	// --- Déconnexion ---------------------------------------------------------

	const onDisconnect = async () => {
		if (!modalPlatform) return;
		const p = modalPlatform;
		disconnecting = true;
		try {
			const res = await disconnectPlatform(localStorage.token, p.id);
			if (res?.ok) {
				toast.success($i18n.t('Déconnecté'));
				await load(true);
				closeModal();
			} else {
				toast.error(res?.error || $i18n.t('Échec de la déconnexion'));
			}
		} catch (err) {
			toast.error($i18n.t('Échec de la déconnexion'));
		} finally {
			disconnecting = false;
		}
	};

	const openModal = (p: MessagingPlatform) => {
		modalPlatform = p;
		showAdvanced = false;
		showTokenForm = false;
		resetPairing();
		approvedUsers = [];
		pendingUsers = [];
		botInfo = null;
		botLinkCopied = false;
		if (isTelegram(p) && p.state === 'connected') {
			loadUsers(p);
		}
	};
	const closeModal = () => {
		resetPairing();
		modalPlatform = null;
	};

	onMount(() => {
		load();
		refreshTimer = setInterval(() => load(true), 10000);
	});
	onDestroy(() => {
		if (refreshTimer) clearInterval(refreshTimer);
		stopPairPolling();
	});

	const toneClass = (tone: string) =>
		tone === 'ok'
			? 'bg-green-500/10 text-green-600 dark:text-green-400'
			: tone === 'warn'
				? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
				: 'bg-gray-500/10 text-gray-500 dark:text-gray-400';
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed rounded-2xl border-gray-200 dark:border-gray-800"
		>
			<div class="text-sm font-medium">
				{$i18n.t('Le service Gateway est injoignable.')}
			</div>
			<button
				class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => load()}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- Supervision technique (serveur + clé API) : Mode Expert uniquement. -->
		{#if $expertMode}
		<!-- Bloc statut gateway -->
		<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 mb-3">
			<div class="flex items-center justify-between gap-3 flex-wrap">
				<div class="flex items-center gap-3">
					<span
						class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium {gatewayRunning
							? 'bg-green-500/10 text-green-600 dark:text-green-400'
							: 'bg-gray-500/10 text-gray-500'}"
					>
						<span class="relative flex size-2">
							<span
								class="relative inline-flex rounded-full size-2 {gatewayRunning
									? 'bg-green-500'
									: 'bg-gray-400'}"
							/>
						</span>
						{gatewayRunning ? $i18n.t('Démarré') : $i18n.t('Arrêté')}
					</span>
					{#if status}
						<span class="text-xs text-gray-500">
							{$i18n.t('API')} : 127.0.0.1:{status.port}
						</span>
					{/if}
				</div>
				<button
					class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50"
					on:click={() => (showRestartConfirm = true)}
					disabled={restarting}
				>
					{restarting ? $i18n.t('Redémarrage…') : $i18n.t('Redémarrer')}
				</button>
			</div>
			<div class="text-xs text-gray-500 mt-2">
				{$i18n.t(
					'Le démarrage/arrêt est géré automatiquement par la supervision. Redémarre après un changement de configuration.'
				)}
			</div>
		</div>

		<!-- Bloc clé API serveur -->
		{#if status}
			<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 mb-3">
				<div class="flex items-center justify-between gap-3 flex-wrap">
					<div class="flex items-center gap-3">
						<span class="text-sm font-medium">{$i18n.t('Clé API du serveur')}</span>
						<span
							class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium {status.api_key_present
								? 'bg-green-500/10 text-green-600 dark:text-green-400'
								: 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}"
						>
							{status.api_key_present ? $i18n.t('Configurée') : $i18n.t('Manquante')}
						</span>
					</div>
					<button
						class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50"
						on:click={() => (status?.api_key_present ? (showRegenConfirm = true) : onGenerateKey())}
						disabled={generatingKey}
					>
						{generatingKey
							? $i18n.t('Génération…')
							: status.api_key_present
								? $i18n.t('Régénérer')
								: $i18n.t('Générer')}
					</button>
				</div>
				<div class="text-xs text-gray-500 mt-2">
					{$i18n.t(
						'Jeton d’authentification utilisé par l’interface pour parler au moteur. La régénérer invalide l’ancienne.'
					)}
				</div>
			</div>
		{/if}
		{/if}

		<!-- Grille des plateformes -->
		<div class="flex items-center justify-between mb-3">
			<div class="text-sm font-medium">{$i18n.t('Canaux de messagerie')}</div>
			<button
				type="button"
				class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 dark:hover:text-gray-200 transition"
				title={$i18n.t('Rafraîchir')}
				aria-label={$i18n.t('Rafraîchir')}
				on:click={() => load()}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.8"
					stroke="currentColor"
					class="size-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M16.023 9.348h4.992V4.356M3 3.75v4.5m0 0h4.5m-4.5 0 3.181-3.183a8.25 8.25 0 0 1 11.667 0l3.181 3.183m0 6.75v4.5m0 0h-4.5m4.5 0-3.182-3.182a8.25 8.25 0 0 1-11.667 0L3 16.5"
					/>
				</svg>
			</button>
		</div>
		{#if filtered.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each filtered as p (p.id)}
					{@const st = stateLabel(p.state)}
					<div
						class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm {isUnavailable(
							p
						)
							? 'opacity-60 saturate-0'
							: ''}"
					>
						<div class="flex items-start justify-between gap-2">
							<div class="flex items-start gap-3 min-w-0">
								{#if LOGO_BY_ID[p.id]}
									{@const fb = LOGO_FULL_BLEED.has(p.id)}
									<div
										class="size-12 flex-none rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {LOGO_BG[
											p.id
										] ?? (fb ? '' : 'bg-white')} {fb ? '' : 'p-0.5'}"
									>
										<img
											src={LOGO_BY_ID[p.id]}
											alt={p.name}
											class={fb
												? 'w-full h-full object-cover'
												: 'max-w-full max-h-full object-contain'}
										/>
									</div>
								{:else}
									<div
										class="size-12 flex-none rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-850 flex items-center justify-center text-2xl select-none"
									>
										{p.emoji}
									</div>
								{/if}
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<span class="text-sm font-medium">{p.name}</span>
										{#if isUnavailable(p)}
											<span
												class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
											>
												{$i18n.t('Bientôt')}
											</span>
										{:else if st.label}
											<span
												class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium {toneClass(
													st.tone
												)}"
											>
												{st.label}
											</span>
										{/if}
									</div>
									<div class="text-xs text-gray-500 mt-0.5">
										{CHANNEL_FR[p.id]?.desc ?? p.description}
									</div>
								</div>
							</div>
							<!-- toggle activer/désactiver -->
							<button
								type="button"
								class="shrink-0 relative inline-flex h-5 w-9 items-center rounded-full transition {p.enabled
									? 'bg-green-500'
									: 'bg-gray-300 dark:bg-gray-700'} disabled:opacity-50"
								title={isUnavailable(p)
									? p.unavailable_reason || $i18n.t('Bientôt disponible')
									: !p.configured && !p.enabled
										? $i18n.t('Configure d’abord la plateforme')
										: $i18n.t('Activer / désactiver')}
								disabled={busy === p.id || isUnavailable(p) || (!p.configured && !p.enabled)}
								on:click={() => toggleEnable(p)}
							>
								<span
									class="inline-block size-4 transform rounded-full bg-white transition {p.enabled
										? 'translate-x-4'
										: 'translate-x-1'}"
								/>
							</button>
						</div>

						{#if CHANNEL_TAGS[p.id]?.length}
							<div class="mt-2 flex flex-wrap gap-1">
								{#each CHANNEL_TAGS[p.id] as t}
									<span
										class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
										>{$i18n.t(t)}</span
									>
								{/each}
							</div>
						{/if}

						{#if CHANNEL_FR[p.id]?.actions?.length}
							<div class="mt-2">
								{#if !aboutOpen[p.id]}
									<button
										type="button"
										class="text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline"
										on:click={() => (aboutOpen = { ...aboutOpen, [p.id]: true })}
									>
										{$i18n.t('Voir ce que ça fait')} ›
									</button>
								{:else}
									<div class="flex flex-col gap-1.5">
										<div
											class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
										>
											{$i18n.t('Ce que ça fait')}
										</div>
										<ul class="flex flex-col gap-1 pl-0.5">
											{#each CHANNEL_FR[p.id].actions as action}
												<li class="flex items-start gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
													<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
													<span>{$i18n.t(action)}</span>
												</li>
											{/each}
										</ul>
										<button
											type="button"
											class="self-start text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
											on:click={() => (aboutOpen = { ...aboutOpen, [p.id]: false })}
										>
											{$i18n.t('Masquer')}
										</button>
									</div>
								{/if}
							</div>
						{/if}

						{#if isUnavailable(p) && p.unavailable_reason}
							<div class="mt-3 text-[11px] text-gray-400 dark:text-gray-500">
								{p.unavailable_reason}
							</div>
						{/if}

						<div
							class="flex items-center gap-1 mt-3 pt-3 border-t border-gray-50 dark:border-gray-850"
						>
							{#if p.docs_url}
								<a
									class="px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-500"
									href={p.docs_url}
									target="_blank"
									rel="noopener noreferrer"
								>
									{$i18n.t('Docs')}
								</a>
							{/if}
							<button
								class="px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
								on:click={() => testPlatform(p)}
								disabled={busy === p.id || isUnavailable(p)}
							>
								{$i18n.t('Tester')}
							</button>
							<div class="flex-1"></div>
							<button
								class="px-3 py-2 text-xs font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black disabled:opacity-50 disabled:cursor-not-allowed"
								on:click={() => openModal(p)}
								disabled={isUnavailable(p)}
							>
								{#if isUnavailable(p)}
									{$i18n.t('Bientôt')}
								{:else}
									{p.configured ? $i18n.t('Détails') : $i18n.t('Configurer')}
								{/if}
							</button>
						</div>

						{#if messages[p.id]}
							<div
								class="mt-2 text-xs px-2 py-1.5 rounded-lg {messages[p.id]?.ok
									? 'bg-green-500/10 text-green-600 dark:text-green-400'
									: 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}"
							>
								{messages[p.id]?.message}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{:else}
			<div class="text-sm text-gray-500 py-10 text-center">
				{$i18n.t('Aucun canal disponible pour le moment.')}
			</div>
		{/if}
	{/if}
</div>

<!-- Modale de configuration -->
{#if modalPlatform}
	{@const p = modalPlatform}
	{@const hasHideableAdvanced = p.env_vars.some((f) => f.advanced && !f.is_set)}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={closeModal}
		role="presentation"
	>
		<div
			class="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 shadow-xl p-5"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
		>
			<div class="flex items-center justify-between mb-1">
				<div class="flex items-center gap-2">
					{#if LOGO_BY_ID[p.id]}
						<div
							class="size-7 rounded-md border border-gray-100 dark:border-gray-700 bg-white flex items-center justify-center p-1"
						>
							<img
								src={LOGO_BY_ID[p.id]}
								alt={p.name}
								class="max-w-full max-h-full object-contain"
							/>
						</div>
					{:else}
						<span class="text-xl">{p.emoji}</span>
					{/if}
					<span class="text-base font-medium">{p.name}</span>
				</div>
				<button
					class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
					on:click={closeModal}
					aria-label={$i18n.t('Fermer')}
				>
					✕
				</button>
			</div>
			<div class="text-xs text-gray-500 mb-4">{p.description}</div>

			{#if messages[p.id]}
				<div
					class="mb-3 text-xs px-2 py-1.5 rounded-lg {messages[p.id]?.ok
						? 'bg-green-500/10 text-green-600 dark:text-green-400'
						: 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}"
				>
					{messages[p.id]?.message}
				</div>
			{/if}

			<!-- TELEGRAM : parcours 1-clic (QR) ou résumé connecté + partage -->
			{#if isTelegram(p)}
				{#if p.state === 'connected'}
					<!-- Connecté : résumé + Accès & partage -->
					<div class="flex flex-col gap-4">
						<div
							class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 text-sm"
						>
							<span>✓</span>
							<span>{$i18n.t('Telegram est connecté. Vous pouvez écrire à votre assistant.')}</span>
						</div>

						<div>
							<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
								{$i18n.t('Accès & partage')}
							</div>

							{#if pendingUsers.length}
								<div class="flex flex-col gap-1.5 mb-2">
									<div class="text-[11px] text-gray-500">
										{$i18n.t('En attente d’autorisation')}
									</div>
									{#each pendingUsers as u (u.user_id + (u.pending_code ?? ''))}
										<div
											class="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/20"
										>
											<span class="text-sm truncate">{u.user_name || u.user_id}</span>
											<div class="flex items-center gap-1.5 flex-none">
												<button
													class="px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 disabled:opacity-50"
													on:click={() => revokeUser(p, u)}
													disabled={usersBusy}
												>
													{$i18n.t('Refuser')}
												</button>
												<button
													class="px-2.5 py-1 text-xs font-medium rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-50"
													on:click={() => approveUser(p, u)}
													disabled={usersBusy}
												>
													{$i18n.t('Autoriser')}
												</button>
											</div>
										</div>
									{/each}
								</div>
							{/if}

							<div class="flex flex-col gap-1.5">
								{#each approvedUsers as u, i (u.user_id)}
									<div
										class="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850"
									>
										<span class="text-sm truncate">
											{#if i === 0}
												👑 {$i18n.t('Vous')}
												<span class="text-[11px] text-gray-400">({$i18n.t('propriétaire')})</span>
											{:else}
												👤 {u.user_name || u.user_id}
											{/if}
										</span>
										{#if i !== 0}
											<button
												class="px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 disabled:opacity-50 flex-none"
												on:click={() => revokeUser(p, u)}
												disabled={usersBusy}
											>
												{$i18n.t('Retirer')}
											</button>
										{/if}
									</div>
								{/each}
								{#if !approvedUsers.length && !usersBusy}
									<div class="text-[11px] text-gray-400">
										{$i18n.t('Personne d’autre n’a accès pour l’instant.')}
									</div>
								{/if}
							</div>
														{#if botInfo?.link}
								<div class="mt-3 flex flex-col gap-1.5">
									<div class="text-[11px] font-medium text-gray-500">
										{$i18n.t('Inviter quelqu’un')}
									</div>
									<div class="flex items-center gap-1.5">
										<code class="flex-1 truncate px-2.5 py-1.5 text-xs rounded-lg bg-gray-50 dark:bg-gray-850 text-gray-600 dark:text-gray-300">
											{botInfo.link}
										</code>
										<button
											class="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition flex-none"
											on:click={copyBotLink}
										>
											{botLinkCopied ? $i18n.t('Copié ✓') : $i18n.t('Copier')}
										</button>
									</div>
									<div class="text-[11px] text-gray-400">
										{$i18n.t(
											'Partagez ce lien à la personne (WhatsApp, e-mail…). Dès qu’elle écrira à votre bot, sa demande apparaîtra ici — vous n’aurez qu’à l’autoriser.'
										)}
									</div>
								</div>
							{:else}
	<div class="text-[11px] text-gray-400 mt-2">
									{$i18n.t(
										'Pour donner accès à quelqu’un : partagez-lui le lien de votre bot ci-dessous. Dès qu’il écrira, autorisez-le ici.'
									)}
								</div>
							{/if}
						</div>
					</div>
				{:else}
					<!-- Écran de connexion 1-clic (QR) -->
					<div class="flex flex-col items-center text-center gap-3 py-2">
						{#if pairStatus === 'idle'}
							<div class="text-sm text-gray-600 dark:text-gray-300 max-w-xs">
								{$i18n.t('Connectez votre assistant à Telegram en une étape, sans rien installer.')}
							</div>
							<button
								class="px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
								on:click={startPairing}
							>
								{$i18n.t('Connecter Telegram')}
							</button>
							<div class="text-[11px] text-gray-400 max-w-xs">
								{$i18n.t('Un bot personnel sera créé pour vous. Aucune manipulation technique.')}
							</div>
						{:else if pairStatus === 'waiting'}
							<div class="text-sm font-medium">
								{$i18n.t('Connectez votre assistant à Telegram')}
							</div>
							{#if pairing}
								<a
									href={pairing.deep_link}
									target="_blank"
									rel="noopener noreferrer"
									class="px-4 py-2.5 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
								>
									📲 {$i18n.t('Ouvrir dans Telegram')} ↗
								</a>
								<div class="text-[11px] text-gray-500 max-w-xs">
									{$i18n.t(
										'Votre bot se crée dans Telegram : confirmez, et tout se configure automatiquement.'
									)}
								</div>
								<div class="w-full max-w-xs border-t border-gray-100 dark:border-gray-800 my-1"></div>
								<div class="text-[11px] text-gray-500">
									{$i18n.t('Vous utilisez Telegram sur votre téléphone ?')}
								</div>
								<button
									class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
									on:click={copyPairLink}
								>
									{pairLinkCopied ? $i18n.t('Lien copié ✓') : $i18n.t('Copier le lien')}
								</button>
								<div class="text-[11px] text-gray-400 max-w-xs">
									{$i18n.t('Ouvrez ce lien dans Telegram sur votre téléphone, puis confirmez.')}
								</div>
							{/if}
							<div class="flex items-center gap-1.5 text-[11px] text-gray-400 mt-1">
								<Spinner className="size-3" />
								{$i18n.t('En attente de confirmation…')}
							</div>
							{:else if pairStatus === 'applying'}
							<div class="py-4"><Spinner /></div>
							<div class="text-sm">{$i18n.t('Connexion en cours…')}</div>
						{:else if pairStatus === 'error'}
							<div class="text-sm text-amber-600 dark:text-amber-400 max-w-xs">{pairError}</div>
							<button
								class="px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
								on:click={startPairing}
							>
								{$i18n.t('Réessayer')}
							</button>
						{/if}
					</div>
				{/if}
			{/if}

			<!-- Formulaire clés & secrets : autres canaux, + Telegram en « méthode avancée » -->
			{#if !isTelegram(p) || (p.state !== 'connected' && showTokenForm)}
				<div class="flex items-center justify-between mb-2 {isTelegram(p) ? 'mt-4' : ''}">
					<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
						{isTelegram(p) ? $i18n.t('Coller un token manuellement') : $i18n.t('Clés & secrets')}
					</div>
					{#if hasHideableAdvanced}
						<label class="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
							<input type="checkbox" bind:checked={showAdvanced} />
							{$i18n.t('Réglages avancés')}
						</label>
					{/if}
				</div>

				<div class="flex flex-col gap-3">
					{#each p.env_vars.filter((f) => showAdvanced || !f.advanced || f.is_set) as field (field.key)}
					{@const vkey = draftKey(p.id, field.key)}
					{@const isCleared = (cleared[p.id] ?? []).includes(field.key)}
					<div>
						<label class="flex items-center justify-between text-xs mb-1">
							<span class="font-medium">
								{field.prompt}
								{#if field.required}<span class="text-red-500">*</span>{/if}
							</span>
							<code class="text-[10px] text-gray-400">{field.key}</code>
						</label>
						<div class="flex items-center gap-1.5">
							<input
								class="flex-1 px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
								type={field.is_password && !visibleKeys[vkey] ? 'password' : 'text'}
								value={drafts[p.id]?.[field.key] ?? ''}
								placeholder={isCleared
									? $i18n.t('effacé à l’enregistrement')
									: field.redacted_value || field.prompt}
								on:input={(e) => handleChange(p.id, field.key, e.currentTarget.value)}
							/>
							{#if field.is_password}
								<button
									class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 text-xs"
									on:click={() => toggleVisibility(p.id, field.key)}
									title={visibleKeys[vkey] ? $i18n.t('Masquer') : $i18n.t('Afficher')}
								>
									{visibleKeys[vkey] ? '🙈' : '👁'}
								</button>
							{/if}
							{#if field.is_set}
								<button
									class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 text-xs"
									on:click={() => clearField(p.id, field.key)}
									title={$i18n.t('Effacer la valeur enregistrée')}
								>
									🗑
								</button>
							{/if}
						</div>
						{#if field.description}
							<div class="text-[11px] text-gray-400 mt-1">{field.description}</div>
						{/if}
					</div>
					{/each}
				</div>
			{/if}

			<!-- Telegram non connecté : proposer la méthode avancée (token brut) -->
			{#if isTelegram(p) && p.state !== 'connected' && !showTokenForm}
				<button
					class="mt-3 text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
					on:click={() => (showTokenForm = true)}
				>
					{$i18n.t('Méthode avancée : coller un token @BotFather')}
				</button>
			{/if}

			<!-- Pied de modale -->
			<div class="flex items-center gap-2 mt-5">
				{#if p.state === 'connected'}
					<button
						class="px-3 py-1.5 text-sm rounded-lg text-red-600 dark:text-red-400 hover:bg-red-500/10 transition disabled:opacity-50"
						on:click={() => (showDisconnectConfirm = true)}
						disabled={disconnecting}
					>
						{disconnecting ? $i18n.t('Déconnexion…') : $i18n.t('Déconnecter')}
					</button>
				{:else if !isTelegram(p) || showTokenForm}
					<button
						class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50"
						on:click={() => testPlatform(p)}
						disabled={busy === p.id}
					>
						{$i18n.t('Tester')}
					</button>
				{/if}
				<div class="flex-1"></div>
				<button
					class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={closeModal}
				>
					{$i18n.t('Fermer')}
				</button>
				{#if p.state !== 'connected' && (!isTelegram(p) || showTokenForm)}
					<button
						class="px-3 py-1.5 text-sm rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
						on:click={() => savePlatform(p)}
						disabled={!hasDraft(p) || busy === p.id}
					>
						{$i18n.t('Enregistrer')}
					</button>
				{/if}
			</div>
		</div>
	</div>
{/if}

<ConfirmDialog
	bind:show={showRestartConfirm}
	title={$i18n.t('Redémarrer la messagerie ?')}
	message={$i18n.t(
		'La messagerie va redémarrer. Les canaux seront brièvement interrompus, puis reconnectés.'
	)}
	confirmLabel={$i18n.t('Redémarrer')}
	onConfirm={onRestart}
/>

<ConfirmDialog
	bind:show={showRegenConfirm}
	title={$i18n.t('Régénérer la clé API ?')}
	message={$i18n.t(
		'Une nouvelle clé sera générée et l’ancienne cessera de fonctionner. Les connexions qui utilisaient l’ancienne clé devront être mises à jour.'
	)}
	confirmLabel={$i18n.t('Régénérer')}
	onConfirm={onGenerateKey}
/>

<ConfirmDialog
	bind:show={showDisconnectConfirm}
	title={$i18n.t('Déconnecter ce canal ?')}
	message={$i18n.t(
		'Le canal sera déconnecté et vos agents cesseront d’y répondre. Les personnes autorisées perdront l’accès. Vous pourrez reconnecter à tout moment.'
	)}
	confirmLabel={$i18n.t('Déconnecter')}
	onConfirm={onDisconnect}
/>
