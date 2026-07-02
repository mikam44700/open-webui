<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { INTEGRATION_LOGO, INTEGRATION_LOGO_BG, INTEGRATION_LOGO_FULL_BLEED, GOOGLE_SERVICE_LOGO, MICROSOFT_SERVICE_LOGO } from '$lib/utils/integrationLogos';
	import { INTEGRATION_FR, ACCESS_LABEL, STATE_LABEL } from '$lib/utils/integrationLabels';
	import {
		disconnectIntegration,
		setIntegrationKey,
		testIntegration,
		getOAuthAuthUrl,
		disconnectOAuth
	} from '$lib/apis/integrations';
	import { tick } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import GoogleConnectModal from './GoogleConnectModal.svelte';
	import EmailConnectModal from './EmailConnectModal.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let integration: {
		id: string;
		auth_mode: 'account' | 'key' | 'credentials' | 'path' | 'local';
		state: 'not_connected' | 'key_present' | 'connected' | 'error' | 'unavailable';
		secret_state?: 'present' | 'absent' | null;
		subservices?: string[];
		visible?: boolean;
		local_only?: boolean;
		reason?: string | null;
	};

	// Couleur du badge d'état (honnête : « Clé enregistrée » ≠ « Connecté »).
	const STATE_CLS: Record<string, string> = {
		connected: 'text-green-700 bg-green-500/10 dark:text-green-400',
		key_present: 'text-sky-700 bg-sky-500/10 dark:text-sky-400',
		not_connected: 'text-gray-600 bg-gray-500/10 dark:text-gray-400',
		error: 'text-red-700 bg-red-500/10 dark:text-red-400',
		unavailable: 'text-gray-500 bg-gray-500/10 dark:text-gray-500'
	};

	$: fr = INTEGRATION_FR[integration.id];
	$: name = fr?.name ?? integration.id;
	$: desc = fr?.desc ?? '';
	$: logo = INTEGRATION_LOGO[integration.id];
	$: logoBg = INTEGRATION_LOGO_BG[integration.id] ?? 'bg-white';
	$: logoFullBleed = INTEGRATION_LOGO_FULL_BLEED.has(integration.id);
	$: access = ACCESS_LABEL[integration.auth_mode] ?? '';
	$: stateLabel = STATE_LABEL[integration.state] ?? integration.state;
	$: stateCls = STATE_CLS[integration.state] ?? STATE_CLS.not_connected;
	$: subservices = integration.subservices ?? [];

	// Modes de connexion : compte (Google), clé/chemin (Notion/GitHub/Airtable/Obsidian).
	$: isGoogle = integration.auth_mode === 'account' && integration.id === 'google-workspace';
	$: isEmail = integration.auth_mode === 'credentials' && integration.id === 'email';

	// Mapping logo de sous-service selon l'espace (Google Workspace ou Microsoft 365).
	// null = pas de mapping, les sous-services s'affichent en pills texte simples.
	const SERVICE_LOGO_BY_ID: Record<string, Record<string, string>> = {
		'google-workspace': GOOGLE_SERVICE_LOGO,
		'microsoft-365': MICROSOFT_SERVICE_LOGO
	};
	$: serviceLogoMap = SERVICE_LOGO_BY_ID[integration.id] ?? null;
	$: isKeyLike = integration.auth_mode === 'key' || integration.auth_mode === 'path';
	$: isPath = integration.auth_mode === 'path';
	$: isConnected = integration.state === 'connected';
	$: keyPresent = integration.state === 'key_present';

	// OAuth centralisé 1 clic — Microsoft 365, Notion, GitHub, Airtable et futurs providers.
	// Ajouter ici les ids des intégrations qui utilisent l'OAuth bridge (pas de clé manuelle).
	const CENTRAL_OAUTH_IDS = new Set([
		'google-workspace',
		'microsoft-365',
		'notion',
		'github',
		'airtable',
		'calendly',
		'box',
		'dropbox',
		'salesforce',
		'clickup',
		'google-meet',
		'google-slides',
		'google-analytics',
		'google-search-console'
	]);
	$: isCentralOAuth = CENTRAL_OAUTH_IDS.has(integration.id);

	// Services Google pilotés par notre bridge (Chemin A) : intégrations distinctes mais
	// qui s'activent avec le MÊME compte Google. La connexion/déconnexion passe donc par le
	// fournisseur « google-workspace » (un seul google_token.json), pas par un OAuth propre.
	const GOOGLE_DIRECT_IDS = new Set([
		'google-meet',
		'google-slides',
		'google-analytics',
		'google-search-console'
	]);
	$: isGoogleDirect = GOOGLE_DIRECT_IDS.has(integration.id);
	$: oauthProviderId = isGoogleDirect ? 'google-workspace' : integration.id;

	let googleOpen = false;
	let emailOpen = false;
	let aboutExpanded = false;
	let confirmDisconnect = false;
	let busy = false;
	let showField = false;
	let fieldValue = '';
	let fieldEl: HTMLInputElement | undefined;

	const openField = async () => {
		showField = true;
		await tick();
		fieldEl?.focus();
	};

	// Enregistre la clé (ou le chemin pour Obsidian).
	const onSave = async () => {
		if (!fieldValue.trim()) return;
		busy = true;
		try {
			await setIntegrationKey(localStorage.token, integration.id, fieldValue.trim());
			fieldValue = '';
			showField = false;
			toast.success(isPath ? $i18n.t('Dossier enregistré.') : $i18n.t('Clé enregistrée.'));
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Échec de l’enregistrement.'));
		} finally {
			busy = false;
		}
	};

	// Test d'accès réel.
	const onTest = async () => {
		busy = true;
		try {
			const res = await testIntegration(localStorage.token, integration.id);
			if (res?.state === 'connected') toast.success($i18n.t('Connexion réussie !'));
			else toast.error($i18n.t('Échec de la connexion') + (res?.reason ? ` : ${res.reason}` : ''));
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible de tester.'));
		} finally {
			busy = false;
		}
	};

	const onDisconnect = async () => {
		busy = true;
		try {
			await disconnectIntegration(localStorage.token, integration.id);
			toast.success($i18n.t('Déconnecté.'));
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible de déconnecter.'));
		} finally {
			busy = false;
			confirmDisconnect = false;
		}
	};

	// Connexion OAuth centralisée : enregistre le provider dans sessionStorage puis redirige
	// vers l'URL d'autorisation du fournisseur. Le callback /integrations/oauth/callback
	// se charge de l'échange automatique du code.
	const onConnectOAuth = async () => {
		busy = true;
		try {
			const res = await getOAuthAuthUrl(localStorage.token, oauthProviderId);
			if (!res?.auth_url) {
				toast.error($i18n.t('Impossible de démarrer la connexion.'));
				return;
			}
			sessionStorage.setItem('oauth_provider', oauthProviderId);
			window.location.href = res.auth_url;
		} catch {
			toast.error($i18n.t('Impossible de démarrer la connexion.'));
			busy = false;
		}
		// Ne pas remettre busy = false : la page va se rediriger.
	};

	// Déconnexion OAuth centralisée (révocation des tokens bridge).
	const onDisconnectOAuth = async () => {
		busy = true;
		try {
			await disconnectOAuth(localStorage.token, integration.id);
			toast.success($i18n.t('Déconnecté.'));
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible de déconnecter.'));
		} finally {
			busy = false;
			confirmDisconnect = false;
		}
	};
</script>

<div
	class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 h-full transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm"
>
	<div class="flex items-start gap-2.5">
		{#if logo}
			<div
				class="size-12 flex-none rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {logoFullBleed ? '' : `${logoBg} p-0.5`}"
			>
				<img
					src={logo}
					alt={name}
					class={logoFullBleed ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
					draggable="false"
				/>
			</div>
		{/if}
		<div class="flex-1 min-w-0 flex flex-col gap-1">
			<div class="text-sm font-medium leading-tight line-clamp-1">{name}</div>
			{#if desc}
				<div class="text-xs text-gray-500 leading-snug">{desc}</div>
			{/if}
		</div>
		{#if isConnected}
			<span class="flex-none"><ActiveBadge /></span>
		{:else if integration.state !== 'not_connected'}
			<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium {stateCls}">
				{$i18n.t(stateLabel)}
			</span>
		{/if}
	</div>

	{#if subservices.length > 0}
		{#if serviceLogoMap}
			<!-- Espace a sous-logos (Google Workspace, Microsoft 365, etc.) : chaque service avec son propre logo -->
			<div class="flex flex-wrap gap-1.5">
				{#each subservices as s}
					<div
						class="flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-850/50"
					>
						{#if serviceLogoMap[s]}
							<img src={serviceLogoMap[s]} alt={s} class="size-4 object-contain" draggable="false" />
						{/if}
						<span class="text-gray-700 dark:text-gray-300">{s}</span>
					</div>
				{/each}
			</div>
		{:else}
			<div class="flex flex-wrap gap-1">
				{#each subservices as s}
					<span
						class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
					>
						{s}
					</span>
				{/each}
			</div>
		{/if}
	{/if}

	{#if fr?.actions?.length}
		{#if !aboutExpanded}
			<button
				type="button"
				class="self-start text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline"
				on:click={() => (aboutExpanded = true)}
			>
				{$i18n.t('Voir ce que ça fait')} ›
			</button>
		{:else}
			<div class="flex flex-col gap-1.5">
				<div class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
					{$i18n.t('Ce que ça fait')}
				</div>
				<ul class="flex flex-col gap-1 pl-0.5">
					{#each fr.actions as action}
						<li class="flex items-start gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
							<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
							<span>{$i18n.t(action)}</span>
						</li>
					{/each}
				</ul>
				<button
					type="button"
					class="self-start text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
					on:click={() => (aboutExpanded = false)}
				>
					{$i18n.t('Masquer')}
				</button>
			</div>
		{/if}
	{/if}

	<div class="mt-auto flex flex-col gap-2 pt-1">
		{#if isKeyLike && !isCentralOAuth && showField}
			<input
				bind:this={fieldEl}
				type={isPath ? 'text' : 'password'}
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				placeholder={isPath ? $i18n.t('Chemin du dossier (ex. ~/Documents/Mon coffre)') : $i18n.t('Colle ta clé / ton token')}
				bind:value={fieldValue}
				autocomplete="off"
				on:keydown={(e) => e.key === 'Enter' && onSave()}
			/>
		{/if}

		<div class="flex items-center justify-between gap-2">
			<span class="text-[11px] text-gray-500 dark:text-gray-400">{$i18n.t(access)}</span>

			<div class="flex items-center gap-1.5">
				{#if isKeyLike && !isCentralOAuth && showField}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
						disabled={busy || !fieldValue.trim()}
						on:click={onSave}
					>
						{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Enregistrer')}{/if}
					</button>
					<button
						type="button"
						class="text-xs px-2.5 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
						on:click={() => {
							showField = false;
							fieldValue = '';
						}}
					>
						{$i18n.t('Annuler')}
					</button>
				{:else if confirmDisconnect}
					<button
						type="button"
						class="text-xs px-2.5 py-1 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-500/10 transition disabled:opacity-40"
						disabled={busy}
						on:click={isCentralOAuth ? onDisconnectOAuth : onDisconnect}
					>
						{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Confirmer')}{/if}
					</button>
					<button
						type="button"
						class="text-xs px-2.5 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
						on:click={() => (confirmDisconnect = false)}
					>
						{$i18n.t('Annuler')}
					</button>
				{:else if isConnected && isGoogleDirect}
					<!-- Service Google piloté par le bridge : activé via le compte Google ;
					     la déconnexion se fait depuis la carte Google Workspace (un seul compte). -->
					<span class="text-[11px] text-green-700 dark:text-green-400">{$i18n.t('Activé avec votre compte Google')}</span>
				{:else if isConnected && isCentralOAuth}
					<!-- Intégration OAuth centralisée connectée : déconnexion via bridge OAuth -->
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => (confirmDisconnect = true)}
					>
						{$i18n.t('Déconnecter')}
					</button>
				{:else if isConnected}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => (confirmDisconnect = true)}
					>
						{$i18n.t('Déconnecter')}
					</button>
				{:else if keyPresent}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
						disabled={busy}
						on:click={onTest}
					>
						{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Tester')}{/if}
					</button>
					<button
						type="button"
						class="text-xs px-2.5 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
						on:click={() => (confirmDisconnect = true)}
					>
						{$i18n.t('Déconnecter')}
					</button>
				{:else if isCentralOAuth}
					<!-- Intégration OAuth centralisée non connectée : 1 clic → redirection fournisseur -->
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
						disabled={busy}
						on:click={onConnectOAuth}
					>
						{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Se connecter')}{/if}
					</button>
				{:else if isGoogle}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition"
						on:click={() => (googleOpen = true)}
					>
						{$i18n.t('Connecter')}
					</button>
				{:else if isEmail}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition"
						on:click={() => (emailOpen = true)}
					>
						{$i18n.t('Connecter')}
					</button>
				{:else if isKeyLike && !isCentralOAuth}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition"
						on:click={openField}
					>
						{$i18n.t('Connecter')}
					</button>
				{:else if integration.local_only}
					<span class="text-[11px] text-gray-400">{$i18n.t('Nécessite un poste local')}</span>
				{/if}
			</div>
		</div>
	</div>
</div>

{#if isGoogle}
	<GoogleConnectModal bind:open={googleOpen} on:connected={() => dispatch('changed')} />
{/if}
{#if isEmail}
	<EmailConnectModal bind:open={emailOpen} on:connected={() => dispatch('changed')} />
{/if}
