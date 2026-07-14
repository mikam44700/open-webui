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
		applyDiscord,
		getDiscordBotInfo,
		applySlack,
		getSlackBotInfo,
		applyEmail,
		type GatewayStatus,
		type MessagingPlatform,
		type MessagingEnvVar,
		type TelegramPairingStart,
		type MessagingUser,
		type TelegramBotInfo,
		type DiscordBotInfo,
		type SlackBotInfo
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

	// Onboarding Discord (parcours guidé : coller le token → branché + invite 1-clic).
	const DISCORD_PORTAL = 'https://discord.com/developers/applications';
	type DiscordStatus = 'idle' | 'applying' | 'error';
	let discordToken = ''; // token collé depuis le portail (jamais persisté côté front)
	let discordStatus: DiscordStatus = 'idle';
	let discordError = '';
	let discordInfo: DiscordBotInfo | null = null; // nom du bot + URL d'invitation
	let discordInviteCopied = false;
	let discordShowRestrict = false; // « Restreindre l'accès (avancé) »

	// Onboarding Slack (parcours guidé : 2 tokens → branché). Pas de vrai 1-clic :
	// le Socket Mode impose un app-level token (xapp-) que l'OAuth ne fournit jamais.
	// On simplifie au maximum : un manifest pré-configure l'app, le client colle 2 clés.
	type SlackStatus = 'idle' | 'applying' | 'error';
	let slackBotToken = ''; // xoxb- (jamais persisté côté front)
	let slackAppToken = ''; // xapp- (Socket Mode)
	let slackStatus: SlackStatus = 'idle';
	let slackError = '';
	let slackInfo: SlackBotInfo | null = null; // workspace + nom du bot
	let slackShowRestrict = false; // « Restreindre l'accès (avancé) »

	// Manifest qui pré-configure l'app Slack (nom + scopes + Socket Mode + événements) :
	// le client n'a rien à régler dans le tableau de bord, il clique et installe.
	const SLACK_MANIFEST = {
		display_information: { name: 'LunarIA' },
		features: { bot_user: { display_name: 'LunarIA', always_online: true } },
		oauth_config: {
			scopes: {
				bot: [
					'app_mentions:read',
					'channels:history',
					'groups:history',
					'im:history',
					'im:read',
					'im:write',
					'chat:write',
					'users:read'
				]
			}
		},
		settings: {
			event_subscriptions: {
				bot_events: ['app_mention', 'message.channels', 'message.groups', 'message.im']
			},
			socket_mode_enabled: true
		}
	};
	const slackManifestUrl =
		'https://api.slack.com/apps?new_app=1&manifest_json=' +
		encodeURIComponent(JSON.stringify(SLACK_MANIFEST));

	// Déconnexion
	let showDisconnectConfirm = false;
	let disconnecting = false;

	let refreshTimer: ReturnType<typeof setInterval> | null = null;

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	// Canaux masqués au client, visibles seulement en mode expert :
	//  • available === false  → grisé « Bientôt » (ex. WhatsApp, attente config Meta)
	//  • expert_only === true  → pleinement configurable mais réservé aux techniciens
	//    (ex. Signal, BlueBubbles : self-hébergement requis)
	$: filtered = $expertMode
		? platforms
		: platforms.filter((p) => p.available !== false && !p.expert_only);

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
	const isDiscord = (p: MessagingPlatform | null) => p?.id === 'discord';
	const isSlack = (p: MessagingPlatform | null) => p?.id === 'slack';
	const isEmail = (p: MessagingPlatform | null) => p?.id === 'email';
	const isSms = (p: MessagingPlatform | null) => p?.id === 'sms';
	const isSignal = (p: MessagingPlatform | null) => p?.id === 'signal';
	const isBlueBubbles = (p: MessagingPlatform | null) => p?.id === 'bluebubbles';

	// Email : auto-détection des serveurs IMAP/SMTP depuis le domaine de l'adresse, pour
	// que le client ne saisisse QUE son adresse + un mot de passe (2 champs au lieu de 4).
	type EmailProvider = {
		imap: string;
		smtp: string;
		label: string;
		appPasswordUrl?: string;
		warning?: string;
	};
	const EMAIL_PROVIDERS: Record<string, EmailProvider> = {
		'gmail.com': {
			imap: 'imap.gmail.com',
			smtp: 'smtp.gmail.com',
			label: 'Gmail',
			appPasswordUrl: 'https://myaccount.google.com/apppasswords'
		},
		'googlemail.com': {
			imap: 'imap.gmail.com',
			smtp: 'smtp.gmail.com',
			label: 'Gmail',
			appPasswordUrl: 'https://myaccount.google.com/apppasswords'
		},
		'outlook.com': {
			imap: 'outlook.office365.com',
			smtp: 'smtp.office365.com',
			label: 'Outlook',
			warning:
				'Microsoft a restreint la connexion par mot de passe sur les comptes Outlook/Hotmail personnels : ce canal risque de ne pas fonctionner.'
		},
		'hotmail.com': {
			imap: 'outlook.office365.com',
			smtp: 'smtp.office365.com',
			label: 'Hotmail',
			warning:
				'Microsoft a restreint la connexion par mot de passe sur les comptes Outlook/Hotmail personnels : ce canal risque de ne pas fonctionner.'
		},
		'live.com': {
			imap: 'outlook.office365.com',
			smtp: 'smtp.office365.com',
			label: 'Live',
			warning:
				'Microsoft a restreint la connexion par mot de passe sur les comptes personnels : ce canal risque de ne pas fonctionner.'
		},
		'yahoo.com': {
			imap: 'imap.mail.yahoo.com',
			smtp: 'smtp.mail.yahoo.com',
			label: 'Yahoo',
			appPasswordUrl: 'https://login.yahoo.com/account/security'
		},
		'icloud.com': {
			imap: 'imap.mail.me.com',
			smtp: 'smtp.mail.me.com',
			label: 'iCloud',
			appPasswordUrl: 'https://account.apple.com/account/manage'
		},
		'me.com': {
			imap: 'imap.mail.me.com',
			smtp: 'smtp.mail.me.com',
			label: 'iCloud',
			appPasswordUrl: 'https://account.apple.com/account/manage'
		}
	};
	let emailProvider: EmailProvider | null = null; // fournisseur détecté (aide dynamique)
	let emailShowHosts = false; // déplier les serveurs (domaine inconnu ou réglage manuel)
	// Validation réelle Email (login IMAP+SMTP → auto-activation), façon Discord/Slack.
	type EmailStatus = 'idle' | 'applying' | 'error';
	let emailStatus: EmailStatus = 'idle';
	let emailError = '';
	let emailInfo: { address: string; count: number | null } | null = null; // preuve de connexion

	// À chaque frappe dans l'adresse : détecte le fournisseur et pré-remplit les serveurs.
	const onEmailAddressChange = (p: MessagingPlatform, value: string) => {
		handleChange(p.id, 'EMAIL_ADDRESS', value);
		const at = value.lastIndexOf('@');
		const domain = at >= 0 ? value.slice(at + 1).trim().toLowerCase() : '';
		emailProvider = EMAIL_PROVIDERS[domain] ?? null;
		if (emailProvider) {
			handleChange(p.id, 'EMAIL_IMAP_HOST', emailProvider.imap);
			handleChange(p.id, 'EMAIL_SMTP_HOST', emailProvider.smtp);
			emailShowHosts = false;
		} else if (domain.includes('.')) {
			emailShowHosts = true; // domaine non reconnu → laisser saisir les serveurs
		}
	};

	// Branche Email en testant réellement la connexion (login IMAP+SMTP côté bridge) :
	// si OK, le canal s'active tout seul → on attend l'état « connecté » et on affiche
	// une confirmation honnête (« connecté », + nb de mails vus). Sinon message d'erreur.
	const connectEmail = async (p: MessagingPlatform) => {
		const address = (drafts[p.id]?.['EMAIL_ADDRESS'] ?? '').trim();
		const password = drafts[p.id]?.['EMAIL_PASSWORD'] ?? '';
		const imap = drafts[p.id]?.['EMAIL_IMAP_HOST'] ?? '';
		const smtp = drafts[p.id]?.['EMAIL_SMTP_HOST'] ?? '';
		if (!address || !password || !imap || !smtp) return;
		emailStatus = 'applying';
		emailError = '';
		try {
			const res = await applyEmail(localStorage.token, address, password, imap, smtp);
			if (res?.ok) {
				emailInfo = { address: res.address ?? address, count: res.mailbox_count ?? null };
				toast.success($i18n.t('Email connecté !'));
				// Le gateway redémarre (quelques secondes) : on rafraîchit jusqu'à « connecté ».
				for (let i = 0; i < 8; i++) {
					await load(true);
					const fresh = platforms.find((x) => x.id === modalPlatform?.id);
					if (fresh) modalPlatform = fresh;
					if (fresh?.state === 'connected') break;
					await new Promise((r) => setTimeout(r, 2000));
				}
				emailStatus = 'idle';
			} else {
				emailStatus = 'error';
				emailError = res?.error || res?.restart_error || $i18n.t('La connexion a échoué.');
			}
		} catch (err) {
			emailStatus = 'error';
			emailError = $i18n.t('Impossible de connecter l’email. Réessaie.');
		}
	};

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

	// --- Onboarding Discord (parcours guidé) ---------------------------------

	const resetDiscord = () => {
		discordToken = '';
		discordStatus = 'idle';
		discordError = '';
		discordInfo = null;
		discordInviteCopied = false;
		discordShowRestrict = false;
	};

	// Récupère nom du bot + URL d'invitation (« Ajouter à mon serveur »).
	const loadDiscordInfo = async (p: MessagingPlatform | null) => {
		if (!p || !isDiscord(p)) return;
		try {
			discordInfo = await getDiscordBotInfo(localStorage.token);
		} catch (err) {
			discordInfo = null; // silencieux : l'invite reste indisponible
		}
	};

	// Branche Discord : valide le token, active + redémarre, puis attend l'état « connecté ».
	const connectDiscord = async () => {
		const token = discordToken.trim();
		if (!token) return;
		discordStatus = 'applying';
		discordError = '';
		try {
			const res = await applyDiscord(localStorage.token, token);
			if (res?.ok) {
				discordToken = '';
				toast.success($i18n.t('Discord connecté !'));
				// Le gateway redémarre (quelques secondes) : on rafraîchit jusqu'à « connecté ».
				for (let i = 0; i < 8; i++) {
					await load(true);
					const fresh = platforms.find((x) => x.id === modalPlatform?.id);
					if (fresh) modalPlatform = fresh;
					if (fresh?.state === 'connected') break;
					await new Promise((r) => setTimeout(r, 2000));
				}
				discordStatus = 'idle';
				if (modalPlatform) loadDiscordInfo(modalPlatform);
			} else {
				discordStatus = 'error';
				discordError = res?.error || res?.restart_error || $i18n.t('La connexion a échoué.');
			}
		} catch (err) {
			discordStatus = 'error';
			discordError = $i18n.t('Impossible de connecter Discord. Réessaie.');
		}
	};

	const copyDiscordInvite = async () => {
		if (!discordInfo?.invite_url) return;
		try {
			await navigator.clipboard.writeText(discordInfo.invite_url);
			discordInviteCopied = true;
			setTimeout(() => (discordInviteCopied = false), 1800);
		} catch (err) {
			toast.error($i18n.t('Copie impossible'));
		}
	};

	// --- Onboarding Slack (parcours guidé, 2 tokens) -------------------------

	const resetSlack = () => {
		slackBotToken = '';
		slackAppToken = '';
		slackStatus = 'idle';
		slackError = '';
		slackInfo = null;
		slackShowRestrict = false;
	};

	// Récupère le workspace + le nom du bot (à afficher une fois connecté).
	const loadSlackInfo = async (p: MessagingPlatform | null) => {
		if (!p || !isSlack(p)) return;
		try {
			slackInfo = await getSlackBotInfo(localStorage.token);
		} catch (err) {
			slackInfo = null; // silencieux
		}
	};

	// Branche Slack : valide les 2 tokens, active + redémarre, puis attend « connecté ».
	const connectSlack = async () => {
		const bot = slackBotToken.trim();
		const appToken = slackAppToken.trim();
		if (!bot || !appToken) return;
		slackStatus = 'applying';
		slackError = '';
		try {
			const res = await applySlack(localStorage.token, bot, appToken);
			if (res?.ok) {
				slackBotToken = '';
				slackAppToken = '';
				toast.success($i18n.t('Slack connecté !'));
				// Le gateway redémarre (quelques secondes) : on rafraîchit jusqu'à « connecté ».
				for (let i = 0; i < 8; i++) {
					await load(true);
					const fresh = platforms.find((x) => x.id === modalPlatform?.id);
					if (fresh) modalPlatform = fresh;
					if (fresh?.state === 'connected') break;
					await new Promise((r) => setTimeout(r, 2000));
				}
				slackStatus = 'idle';
				if (modalPlatform) loadSlackInfo(modalPlatform);
			} else {
				slackStatus = 'error';
				slackError = res?.error || res?.restart_error || $i18n.t('La connexion a échoué.');
			}
		} catch (err) {
			slackStatus = 'error';
			slackError = $i18n.t('Impossible de connecter Slack. Réessaie.');
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
		resetDiscord();
		resetSlack();
		emailProvider = null;
		emailShowHosts = false;
		emailStatus = 'idle';
		emailError = '';
		emailInfo = null;
		approvedUsers = [];
		pendingUsers = [];
		botInfo = null;
		botLinkCopied = false;
		if (isTelegram(p) && p.state === 'connected') {
			loadUsers(p);
		}
		if (isDiscord(p) && p.state === 'connected') {
			loadDiscordInfo(p);
		}
		if (isSlack(p) && p.state === 'connected') {
			loadSlackInfo(p);
		}
		if (isEmail(p) && p.state === 'connected') {
			// déjà branché : afficher l'adresse (non secrète) en confirmation
			const f = p.env_vars.find((x) => x.key === 'EMAIL_ADDRESS');
			emailInfo = { address: f?.redacted_value || '', count: null };
		}
	};
	const closeModal = () => {
		resetPairing();
		resetDiscord();
		resetSlack();
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
										{#if p.recommended && !isUnavailable(p)}
											<span
												class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-green-500/10 text-green-600 dark:text-green-400"
											>
												{$i18n.t('Recommandé')}
											</span>
										{/if}
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
								{$i18n.t('Vérifier')}
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

			<!-- DISCORD : parcours guidé (token → branché) ou écran connecté + invite -->
			{#if isDiscord(p)}
				{#if p.state === 'connected'}
					{@const allowedField = p.env_vars.find((f) => f.key === 'DISCORD_ALLOWED_USERS')}
					<div class="flex flex-col gap-4">
						<div
							class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 text-sm"
						>
							<span>✓</span>
							<span>
								{$i18n.t('Discord est connecté.')}
								{#if discordInfo?.name}<span class="opacity-70">({discordInfo.name})</span>{/if}
							</span>
						</div>

						<!-- Ajouter le bot à un serveur (1 clic) -->
						<div class="flex flex-col gap-2">
							<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
								{$i18n.t('Ajouter à un serveur')}
							</div>
							{#if discordInfo?.invite_url}
								<a
									href={discordInfo.invite_url}
									target="_blank"
									rel="noopener noreferrer"
									class="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg btn-premium bg-[#5865F2] text-white hover:opacity-90 transition"
								>
									➕ {$i18n.t('Ajouter à mon serveur')} ↗
								</a>
								<div class="flex items-center gap-1.5">
									<code
										class="flex-1 truncate px-2.5 py-1.5 text-xs rounded-lg bg-gray-50 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
									>
										{discordInfo.invite_url}
									</code>
									<button
										class="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition flex-none"
										on:click={copyDiscordInvite}
									>
										{discordInviteCopied ? $i18n.t('Copié ✓') : $i18n.t('Copier')}
									</button>
								</div>
								<div class="text-[11px] text-gray-400">
									{$i18n.t(
										'Ouvrez ce lien, choisissez votre serveur Discord, et confirmez. Votre assistant y répondra aussitôt.'
									)}
								</div>
							{:else}
								<div class="text-[11px] text-gray-400">
									{$i18n.t('Lien d’invitation indisponible pour le moment.')}
								</div>
							{/if}
						</div>

						<!-- Accès : tout le serveur par défaut, restriction en option -->
						<div class="flex flex-col gap-2">
							<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
								{$i18n.t('Accès')}
							</div>
							<div class="text-[11px] text-gray-500">
								{$i18n.t(
									'Par défaut, toute personne présente sur votre serveur Discord peut écrire à votre assistant.'
								)}
							</div>
							{#if allowedField}
								<button
									class="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition text-left"
									on:click={() => (discordShowRestrict = !discordShowRestrict)}
								>
									{discordShowRestrict
										? $i18n.t('Masquer')
										: $i18n.t('Restreindre l’accès (avancé)')}
								</button>
								{#if discordShowRestrict}
									<input
										class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
										type="text"
										value={drafts[p.id]?.[allowedField.key] ?? ''}
										placeholder={allowedField.redacted_value || allowedField.prompt}
										on:input={(e) => handleChange(p.id, allowedField.key, e.currentTarget.value)}
									/>
									<div class="text-[11px] text-gray-400">
										{$i18n.t(
											'Identifiants Discord autorisés, séparés par des virgules. Laissez vide pour autoriser tout le serveur.'
										)}
									</div>
									<button
										class="self-start px-3 py-1.5 text-sm rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
										on:click={() => savePlatform(p)}
										disabled={!hasDraft(p) || busy === p.id}
									>
										{$i18n.t('Enregistrer')}
									</button>
								{/if}
							{/if}
						</div>
					</div>
				{:else if discordStatus === 'applying'}
					<div class="flex flex-col items-center text-center gap-3 py-4">
						<Spinner />
						<div class="text-sm">{$i18n.t('Connexion en cours…')}</div>
					</div>
				{:else}
					<!-- Écran de connexion guidée (3 étapes) -->
					<div class="flex flex-col gap-4">
						<div class="text-sm text-gray-600 dark:text-gray-300">
							{$i18n.t(
								'Créez votre bot Discord en 3 étapes (environ 2 minutes). Le portail Discord est en anglais : les boutons à cliquer sont indiqués ci-dessous.'
							)}
						</div>

						<div class="flex gap-3">
							<div
								class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
							>
								1
							</div>
							<div class="flex flex-col gap-1.5 text-sm">
								<div class="font-medium">{$i18n.t('Créez votre application')}</div>
								<div class="text-[13px] text-gray-500">
									{$i18n.t(
										'Ouvrez le portail, cliquez « New Application » (en haut à droite), donnez un nom, puis « Create ».'
									)}
								</div>
								<a
									href={DISCORD_PORTAL}
									target="_blank"
									rel="noopener noreferrer"
									class="self-start px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								>
									{$i18n.t('Ouvrir le portail Discord')} ↗
								</a>
							</div>
						</div>

						<div class="flex gap-3">
							<div
								class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
							>
								2
							</div>
							<div class="flex flex-col gap-1.5 text-sm">
								<div class="font-medium">
									{$i18n.t('Récupérez la clé + activez la lecture des messages')}
								</div>
								<div class="text-[13px] text-gray-500">
									{$i18n.t(
										'Menu de gauche → « Bot ». Cliquez « Reset Token » puis « Copy ». Juste en dessous, activez l’interrupteur « MESSAGE CONTENT INTENT » (sinon votre assistant ne verra aucun message).'
									)}
								</div>
							</div>
						</div>

						<div class="flex gap-3">
							<div
								class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
							>
								3
							</div>
							<div class="flex flex-col gap-1.5 text-sm w-full">
								<div class="font-medium">{$i18n.t('Collez la clé ici')}</div>
								<input
									class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
									type="password"
									autocomplete="off"
									placeholder={$i18n.t('Collez le token du bot')}
									bind:value={discordToken}
								/>
							</div>
						</div>

						{#if discordStatus === 'error'}
							<div
								class="text-xs px-2 py-1.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400"
							>
								{discordError}
							</div>
						{/if}

						<button
							class="px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
							on:click={connectDiscord}
							disabled={!discordToken.trim()}
						>
							{$i18n.t('Connecter')}
						</button>
						<div class="text-[11px] text-gray-400">
							{$i18n.t(
								'Astuce : il vous faut un serveur Discord où vous êtes administrateur pour y ajouter le bot ensuite.'
							)}
						</div>
					</div>
				{/if}
			{/if}

			{#if isSlack(p)}
				{#if p.state === 'connected'}
					{@const allowedField = p.env_vars.find((f) => f.key === 'SLACK_ALLOWED_USERS')}
					<div class="flex flex-col gap-4">
						<div
							class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 text-sm"
						>
							<span>✓</span>
							<span>
								{$i18n.t('Slack est connecté.')}
								{#if slackInfo?.team_name}<span class="opacity-70">({slackInfo.team_name})</span>{/if}
							</span>
						</div>

						<!-- Espace de travail où l'app est installée -->
						{#if slackInfo?.workspace_url}
							<div class="flex flex-col gap-2">
								<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
									{$i18n.t('Espace de travail')}
								</div>
								<a
									href={slackInfo.workspace_url}
									target="_blank"
									rel="noopener noreferrer"
									class="inline-flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
								>
									{slackInfo.workspace_url} ↗
								</a>
								<div class="text-[11px] text-gray-400">
									{$i18n.t(
										'Invitez votre assistant dans un canal avec « /invite @LunarIA », puis écrivez-lui.'
									)}
								</div>
							</div>
						{/if}

						<!-- Accès : tout l'espace par défaut, restriction en option -->
						<div class="flex flex-col gap-2">
							<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
								{$i18n.t('Accès')}
							</div>
							<div class="text-[11px] text-gray-500">
								{$i18n.t(
									'Par défaut, toute personne de votre espace Slack peut écrire à votre assistant.'
								)}
							</div>
							{#if allowedField}
								<button
									class="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition text-left"
									on:click={() => (slackShowRestrict = !slackShowRestrict)}
								>
									{slackShowRestrict ? $i18n.t('Masquer') : $i18n.t('Restreindre l’accès (avancé)')}
								</button>
								{#if slackShowRestrict}
									<input
										class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
										type="text"
										value={drafts[p.id]?.[allowedField.key] ?? ''}
										placeholder={allowedField.redacted_value || allowedField.prompt}
										on:input={(e) => handleChange(p.id, allowedField.key, e.currentTarget.value)}
									/>
									<div class="text-[11px] text-gray-400">
										{$i18n.t(
											'Identifiants Slack autorisés, séparés par des virgules. Laissez vide pour autoriser tout l’espace.'
										)}
									</div>
									<button
										class="self-start px-3 py-1.5 text-sm rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
										on:click={() => savePlatform(p)}
										disabled={!hasDraft(p) || busy === p.id}
									>
										{$i18n.t('Enregistrer')}
									</button>
								{/if}
							{/if}
						</div>
					</div>
				{:else if slackStatus === 'applying'}
					<div class="flex flex-col items-center text-center gap-3 py-4">
						<Spinner />
						<div class="text-sm">{$i18n.t('Connexion en cours…')}</div>
					</div>
				{:else}
					<!-- Écran de connexion guidée (3 étapes) -->
					<div class="flex flex-col gap-4">
						<div class="text-sm text-gray-600 dark:text-gray-300">
							{$i18n.t(
								'Branchez votre espace Slack en 3 étapes (environ 3 minutes). Le tableau de bord Slack est en anglais : les boutons à cliquer sont indiqués ci-dessous.'
							)}
						</div>

						<div class="flex gap-3">
							<div
								class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
							>
								1
							</div>
							<div class="flex flex-col gap-1.5 text-sm">
								<div class="font-medium">{$i18n.t('Créez votre app Slack (pré-configurée)')}</div>
								<div class="text-[13px] text-gray-500">
									{$i18n.t(
										'Ouvrez le lien : l’app arrive déjà configurée (nom, permissions, Socket Mode). Choisissez votre espace de travail, vérifiez, puis cliquez « Create ».'
									)}
								</div>
								<a
									href={slackManifestUrl}
									target="_blank"
									rel="noopener noreferrer"
									class="self-start px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								>
									{$i18n.t('Créer mon app Slack')} ↗
								</a>
							</div>
						</div>

						<div class="flex gap-3">
							<div
								class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
							>
								2
							</div>
							<div class="flex flex-col gap-1.5 text-sm">
								<div class="font-medium">{$i18n.t('Installez l’app et récupérez vos 2 clés')}</div>
								<div class="text-[13px] text-gray-500">
									{$i18n.t(
										'Menu « Install App » → « Install to Workspace » → « Allow » : copiez le « Bot User OAuth Token » (commence par xoxb-). Puis menu « Basic Information » → « App-Level Tokens » → « Generate Token and Scopes », ajoutez le scope « connections:write », et copiez le token (commence par xapp-).'
									)}
								</div>
							</div>
						</div>

						<div class="flex gap-3">
							<div
								class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
							>
								3
							</div>
							<div class="flex flex-col gap-2 text-sm w-full">
								<div class="font-medium">{$i18n.t('Collez vos 2 clés ici')}</div>
								<input
									class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
									type="password"
									autocomplete="off"
									placeholder={$i18n.t('Bot token (xoxb-…)')}
									bind:value={slackBotToken}
								/>
								<input
									class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
									type="password"
									autocomplete="off"
									placeholder={$i18n.t('App token (xapp-…)')}
									bind:value={slackAppToken}
								/>
							</div>
						</div>

						{#if slackStatus === 'error'}
							<div
								class="text-xs px-2 py-1.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400"
							>
								{slackError}
							</div>
						{/if}

						<button
							class="px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
							on:click={connectSlack}
							disabled={!slackBotToken.trim() || !slackAppToken.trim()}
						>
							{$i18n.t('Connecter')}
						</button>
						<div class="text-[11px] text-gray-400">
							{$i18n.t(
								'Astuce : il vous faut un espace Slack où vous êtes administrateur pour y installer l’app.'
							)}
						</div>
					</div>
				{/if}
			{/if}

			{#if isEmail(p)}
				{#if p.state === 'connected'}
					<!-- Écran connecté : confirmation honnête (connexion prouvée) -->
					<div class="flex flex-col gap-3">
						<div
							class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 text-sm"
						>
							<span>✓</span>
							<span>
								{$i18n.t('Votre boîte mail est connectée.')}
								{#if emailInfo?.address}<span class="opacity-70">({emailInfo.address})</span>{/if}
							</span>
						</div>
						{#if emailInfo?.count != null}
							<div class="text-[11px] text-gray-400">
								{$i18n.t('Connexion vérifiée')} — {emailInfo.count}
								{$i18n.t('e-mail(s) dans votre boîte de réception.')}
							</div>
						{/if}
						<div class="text-[13px] text-gray-500">
							{$i18n.t(
								'Votre assistant lit vos e-mails entrants et y répond. Envoyez-vous un message pour tester.'
							)}
						</div>
					</div>
				{:else if emailStatus === 'applying'}
					<div class="flex flex-col items-center text-center gap-3 py-4">
						<Spinner />
						<div class="text-sm">{$i18n.t('Test de la connexion à votre boîte mail…')}</div>
					</div>
				{:else}
					{@const addr = drafts[p.id]?.['EMAIL_ADDRESS'] ?? ''}
					<div class="flex flex-col gap-4">
						<div class="text-sm text-gray-600 dark:text-gray-300">
							{$i18n.t(
								'Connectez votre boîte mail : votre assistant lit vos e-mails et y répond. Indiquez votre adresse et un mot de passe — le reste est détecté automatiquement.'
							)}
						</div>

						<div
							class="text-[12px] px-3 py-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 flex gap-2"
						>
							<span class="flex-none">💡</span>
							<span>
								{$i18n.t(
									'Cette boîte sert uniquement à discuter avec votre assistant : il répond aux e-mails reçus ici. Conseil : utilisez une adresse dédiée à l’assistant, pas votre boîte personnelle principale.'
								)}
							</span>
						</div>

						<div class="flex flex-col gap-1.5">
							<label class="text-sm font-medium" for="email-addr">{$i18n.t('Votre adresse e-mail')}</label>
							<input
								id="email-addr"
								class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
								type="email"
								autocomplete="off"
								placeholder="vous@exemple.com"
								value={addr}
								on:input={(e) => onEmailAddressChange(p, e.currentTarget.value)}
							/>
							{#if emailProvider}
								<div class="text-[11px] text-gray-400">
									{$i18n.t('Fournisseur détecté')} : {emailProvider.label} — {$i18n.t(
										'serveurs configurés automatiquement.'
									)}
								</div>
							{/if}
						</div>

						{#if emailProvider?.warning}
							<div class="text-xs px-3 py-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
								⚠ {$i18n.t(emailProvider.warning)}
							</div>
						{:else if emailProvider?.appPasswordUrl}
							<div
								class="text-xs px-3 py-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 flex flex-col gap-1.5"
							>
								<span
									>{$i18n.t('Pour')} {emailProvider.label}, {$i18n.t(
										'utilisez un mot de passe d’application (pas votre mot de passe habituel). Nécessite la validation en 2 étapes activée.'
									)}</span
								>
								<a
									href={emailProvider.appPasswordUrl}
									target="_blank"
									rel="noopener noreferrer"
									class="underline self-start font-medium"
								>
									{$i18n.t('Créer un mot de passe d’application')} ↗
								</a>
							</div>
						{/if}

						<div class="flex flex-col gap-1.5">
							<label class="text-sm font-medium" for="email-pwd">{$i18n.t('Mot de passe')}</label>
							<input
								id="email-pwd"
								class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
								type="password"
								autocomplete="off"
								placeholder={emailProvider?.appPasswordUrl
									? $i18n.t('Mot de passe d’application')
									: $i18n.t('Mot de passe de la boîte')}
								value={drafts[p.id]?.['EMAIL_PASSWORD'] ?? ''}
								on:input={(e) => handleChange(p.id, 'EMAIL_PASSWORD', e.currentTarget.value)}
							/>
						</div>

						<!-- Serveurs IMAP/SMTP : cachés si auto-détectés, dépliables sinon -->
						<div class="flex flex-col gap-1.5">
							<button
								class="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition text-left"
								on:click={() => (emailShowHosts = !emailShowHosts)}
							>
								{emailShowHosts ? $i18n.t('Masquer les serveurs') : $i18n.t('Serveurs (avancé)')}
							</button>
							{#if emailShowHosts}
								<input
									class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
									type="text"
									placeholder={$i18n.t('Serveur de réception (IMAP)')}
									value={drafts[p.id]?.['EMAIL_IMAP_HOST'] ?? ''}
									on:input={(e) => handleChange(p.id, 'EMAIL_IMAP_HOST', e.currentTarget.value)}
								/>
								<input
									class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
									type="text"
									placeholder={$i18n.t('Serveur d’envoi (SMTP)')}
									value={drafts[p.id]?.['EMAIL_SMTP_HOST'] ?? ''}
									on:input={(e) => handleChange(p.id, 'EMAIL_SMTP_HOST', e.currentTarget.value)}
								/>
							{/if}
						</div>

						{#if emailStatus === 'error'}
							<div
								class="text-xs px-2 py-1.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400"
							>
								{emailError}
							</div>
						{/if}

						<button
							class="self-start px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
							on:click={() => connectEmail(p)}
							disabled={!(
								drafts[p.id]?.['EMAIL_ADDRESS'] &&
								drafts[p.id]?.['EMAIL_PASSWORD'] &&
								drafts[p.id]?.['EMAIL_IMAP_HOST'] &&
								drafts[p.id]?.['EMAIL_SMTP_HOST']
							) || busy === p.id}
						>
							{$i18n.t('Connecter')}
						</button>
					</div>
				{/if}
			{/if}

			{#if isSms(p)}
				<div class="flex flex-col gap-4">
					<div class="text-sm text-gray-600 dark:text-gray-300">
						{$i18n.t(
							'Envoyez et recevez des SMS via Twilio. Récupérez vos identifiants dans la console Twilio (2 minutes).'
						)}
					</div>

					<div class="text-xs px-3 py-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
						⚠ {$i18n.t(
							'Twilio est payant : environ 1 $/mois pour le numéro + un coût par SMS. Un compte d’essai n’envoie qu’à des numéros vérifiés.'
						)}
					</div>

					<div class="flex flex-wrap gap-2">
						<a
							href="https://console.twilio.com"
							target="_blank"
							rel="noopener noreferrer"
							class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						>
							{$i18n.t('Ouvrir la console Twilio')} ↗
						</a>
						<a
							href="https://console.twilio.com/us1/develop/phone-numbers/manage/search"
							target="_blank"
							rel="noopener noreferrer"
							class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						>
							{$i18n.t('Acheter un numéro')} ↗
						</a>
					</div>

					{#each p.env_vars.filter((f) => !f.advanced) as field (field.key)}
						<div class="flex flex-col gap-1.5">
							<label class="text-sm font-medium">
								{field.prompt}{#if field.required}<span class="text-red-500"> *</span>{/if}
							</label>
							<input
								class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
								type={field.is_password ? 'password' : 'text'}
								autocomplete="off"
								placeholder={field.redacted_value || field.prompt}
								value={drafts[p.id]?.[field.key] ?? ''}
								on:input={(e) => handleChange(p.id, field.key, e.currentTarget.value)}
							/>
							{#if field.description}
								<div class="text-[11px] text-gray-400">{field.description}</div>
							{/if}
						</div>
					{/each}

					<button
						class="self-start px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
						on:click={() => savePlatform(p)}
						disabled={!hasDraft(p) || busy === p.id}
					>
						{p.state === 'connected' ? $i18n.t('Enregistrer') : $i18n.t('Connecter')}
					</button>
				</div>
			{/if}

			{#if isSignal(p)}
				<div class="flex flex-col gap-4">
					<div class="text-sm text-gray-600 dark:text-gray-300">
						{$i18n.t(
							'Signal fonctionne via un petit serveur technique (signal-cli REST). Réservé à une configuration avancée.'
						)}
					</div>
					<div class="text-xs px-3 py-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
						⚠ {$i18n.t(
							'Étape technique : il faut héberger le service signal-cli REST et y lier un numéro dédié (idéalement pas votre numéro personnel).'
						)}
					</div>

					<div class="flex gap-3">
						<div
							class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
						>
							1
						</div>
						<div class="flex flex-col gap-1.5 text-sm">
							<div class="font-medium">{$i18n.t('Lancez le serveur signal-cli REST')}</div>
							<div class="text-[13px] text-gray-500">
								{$i18n.t(
									'Déployez le conteneur signal-cli-rest-api (Docker) et liez votre numéro (device-link ou enregistrement d’un numéro dédié).'
								)}
							</div>
							<a
								href="https://github.com/bbernhard/signal-cli-rest-api"
								target="_blank"
								rel="noopener noreferrer"
								class="self-start px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							>
								{$i18n.t('Voir la documentation')} ↗
							</a>
						</div>
					</div>

					<div class="flex gap-3">
						<div
							class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
						>
							2
						</div>
						<div class="flex flex-col gap-2 text-sm w-full">
							<div class="font-medium">{$i18n.t('Renseignez votre numéro et l’adresse du serveur')}</div>
							{#each p.env_vars.filter((f) => !f.advanced) as field (field.key)}
								<div class="flex flex-col gap-1">
									<input
										class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
										type={field.is_password ? 'password' : 'text'}
										autocomplete="off"
										placeholder={field.redacted_value || field.prompt}
										value={drafts[p.id]?.[field.key] ?? ''}
										on:input={(e) => handleChange(p.id, field.key, e.currentTarget.value)}
									/>
									{#if field.description}
										<div class="text-[11px] text-gray-400">{field.description}</div>
									{/if}
								</div>
							{/each}
						</div>
					</div>

					<button
						class="self-start px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
						on:click={() => savePlatform(p)}
						disabled={!hasDraft(p) || busy === p.id}
					>
						{p.state === 'connected' ? $i18n.t('Enregistrer') : $i18n.t('Connecter')}
					</button>
				</div>
			{/if}

			{#if isBlueBubbles(p)}
				<div class="flex flex-col gap-4">
					<div class="text-sm text-gray-600 dark:text-gray-300">
						{$i18n.t(
							'iMessage fonctionne via un serveur BlueBubbles installé sur un Mac. Réservé à une configuration avancée.'
						)}
					</div>
					<div class="text-xs px-3 py-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
						⚠ {$i18n.t(
							'Nécessite un Mac dédié allumé en permanence, connecté à iMessage avec un Apple ID.'
						)}
					</div>

					<div class="flex gap-3">
						<div
							class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
						>
							1
						</div>
						<div class="flex flex-col gap-1.5 text-sm">
							<div class="font-medium">{$i18n.t('Installez BlueBubbles sur votre Mac')}</div>
							<div class="text-[13px] text-gray-500">
								{$i18n.t(
									'Installez le serveur BlueBubbles, connectez-le à iMessage, accordez les permissions macOS et définissez un mot de passe serveur.'
								)}
							</div>
							<a
								href="https://bluebubbles.app/install/"
								target="_blank"
								rel="noopener noreferrer"
								class="self-start px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							>
								{$i18n.t('Guide d’installation')} ↗
							</a>
						</div>
					</div>

					<div class="flex gap-3">
						<div
							class="flex-none size-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-semibold"
						>
							2
						</div>
						<div class="flex flex-col gap-2 text-sm w-full">
							<div class="font-medium">{$i18n.t('Renseignez l’adresse du serveur et le mot de passe')}</div>
							{#each p.env_vars.filter((f) => !f.advanced) as field (field.key)}
								<div class="flex flex-col gap-1">
									<input
										class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
										type={field.is_password ? 'password' : 'text'}
										autocomplete="off"
										placeholder={field.redacted_value || field.prompt}
										value={drafts[p.id]?.[field.key] ?? ''}
										on:input={(e) => handleChange(p.id, field.key, e.currentTarget.value)}
									/>
									{#if field.description}
										<div class="text-[11px] text-gray-400">{field.description}</div>
									{/if}
								</div>
							{/each}
						</div>
					</div>

					<button
						class="self-start px-4 py-2 text-sm font-medium rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
						on:click={() => savePlatform(p)}
						disabled={!hasDraft(p) || busy === p.id}
					>
						{p.state === 'connected' ? $i18n.t('Enregistrer') : $i18n.t('Connecter')}
					</button>
				</div>
			{/if}

			<!-- Formulaire clés & secrets : fallback (WhatsApp expert, Telegram méthode avancée) -->
			{#if (!isTelegram(p) && !isDiscord(p) && !isSlack(p) && !isEmail(p) && !isSms(p) && !isSignal(p) && !isBlueBubbles(p)) || (isTelegram(p) && p.state !== 'connected' && showTokenForm)}
				<div class="flex items-center justify-between mb-2 {isTelegram(p) ? 'mt-4' : ''}">
					<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
						{isTelegram(p)
							? $i18n.t('Coller un token manuellement')
							: $i18n.t('Vos identifiants de connexion')}
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
							{#if $expertMode}
								<code class="text-[10px] text-gray-400">{field.key}</code>
							{/if}
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
				{:else if (!isTelegram(p) && !isDiscord(p) && !isSlack(p) && !isEmail(p) && !isSms(p) && !isSignal(p) && !isBlueBubbles(p)) || showTokenForm}
					<button
						class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50"
						on:click={() => testPlatform(p)}
						disabled={busy === p.id}
					>
						{$i18n.t('Vérifier')}
					</button>
				{/if}
				<div class="flex-1"></div>
				<button
					class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={closeModal}
				>
					{$i18n.t('Fermer')}
				</button>
				{#if p.state !== 'connected' && ((!isTelegram(p) && !isDiscord(p) && !isSlack(p) && !isEmail(p) && !isSms(p) && !isSignal(p) && !isBlueBubbles(p)) || showTokenForm)}
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
