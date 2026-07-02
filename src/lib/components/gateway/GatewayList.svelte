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
		type GatewayStatus,
		type MessagingPlatform,
		type MessagingEnvVar
	} from '$lib/apis/gateway';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { expertMode } from '$lib/stores';
	import { CHANNEL_FR } from '$lib/utils/channelLabels';

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

	let refreshTimer: ReturnType<typeof setInterval> | null = null;

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	$: filtered = platforms;

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

	const openModal = (p: MessagingPlatform) => {
		modalPlatform = p;
		showAdvanced = false;
	};
	const closeModal = () => {
		modalPlatform = null;
	};

	onMount(() => {
		load();
		refreshTimer = setInterval(() => load(true), 10000);
	});
	onDestroy(() => {
		if (refreshTimer) clearInterval(refreshTimer);
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
						class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm"
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
										<span class="text-sm font-medium truncate">{p.name}</span>
										{#if st.label}
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
								title={!p.configured && !p.enabled
									? $i18n.t('Configure d’abord la plateforme')
									: $i18n.t('Activer / désactiver')}
								disabled={busy === p.id || (!p.configured && !p.enabled)}
								on:click={() => toggleEnable(p)}
							>
								<span
									class="inline-block size-4 transform rounded-full bg-white transition {p.enabled
										? 'translate-x-4'
										: 'translate-x-1'}"
								/>
							</button>
						</div>

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
								class="px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-500 disabled:opacity-50"
								on:click={() => testPlatform(p)}
								disabled={busy === p.id}
							>
								{$i18n.t('Tester')}
							</button>
							<div class="flex-1"></div>
							<button
								class="px-2.5 py-1 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => openModal(p)}
							>
								{p.configured ? $i18n.t('Détails') : $i18n.t('Configurer')}
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

			<!-- Champs (clés & secrets) -->
			<div class="flex items-center justify-between mb-2">
				<div class="text-xs font-semibold uppercase tracking-wide text-gray-400">
					{$i18n.t('Clés & secrets')}
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

			<!-- Pied de modale -->
			<div class="flex items-center gap-2 mt-5">
				<button
					class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50"
					on:click={() => testPlatform(p)}
					disabled={busy === p.id}
				>
					{$i18n.t('Tester')}
				</button>
				<div class="flex-1"></div>
				<button
					class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={closeModal}
				>
					{$i18n.t('Fermer')}
				</button>
				<button
					class="px-3 py-1.5 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40"
					on:click={() => savePlatform(p)}
					disabled={!hasDraft(p) || busy === p.id}
				>
					{$i18n.t('Enregistrer')}
				</button>
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
