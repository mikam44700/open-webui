<script lang="ts">
	import { getContext, createEventDispatcher, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import {
		installConnector,
		setConnectorKey,
		startConnectorOAuth,
		getInstallStatus,
		addCustomConnector,
		installFromRegistry
	} from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import OAuthProgressModal from './OAuthProgressModal.svelte';
	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
	import { CONNECTOR_LOGO, CONNECTOR_LOGO_FULL_BLEED } from '$lib/utils/connectorLogos';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let entry: {
		name: string;
		description?: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		installed: boolean;
		source_url?: string | null;
		// Enrichissement « registre des 55 » : libellé/logo distant + classement + installabilité.
		label?: string;
		icon_url?: string | null;
		category?: string;
		visibility?: 'visible' | 'expert';
		installable?: boolean;
		url?: string | null;
		install_method?: string; // "engine" | "registry" | ""
		// Champs à renseigner avant install (MCP stdio à clé du registre).
		config_fields?: { key: string; label?: string; type?: string; secret?: boolean; required?: boolean }[];
		// Connecteur hors catalogue Hermes (ex. HubSpot) : on l'ajoute en « custom »
		// (http/OAuth) au lieu de passer par `hermes mcp install`.
		preset?: { transport: 'http' | 'sse'; url: string; auth_type: 'none' | 'key' | 'oauth' };
	};

	// MCP du registre à champs (stdio à clé) : on demande les valeurs avant d'installer.
	$: fields = entry.config_fields ?? [];
	$: needsFields = entry.install_method === 'registry' && fields.length > 0 && !entry.installed;
	let fieldValues: Record<string, string> = {};
	let showFields = false;

	// Config d'ajout « custom » (http + OAuth) pour les connecteurs distants : preset maison
	// (HubSpot) OU MCP remote du registre (Stripe, Asana…). Même chemin que HubSpot.
	$: remoteConfig =
		entry.preset ??
		(entry.install_method === 'registry' && entry.url
			? {
					transport: (entry.transport === 'sse' ? 'sse' : 'http') as 'http' | 'sse',
					url: entry.url,
					auth_type: entry.auth_type
				}
			: null);

	// Un MCP du registre non encore installable en 1 clic (manifest/auth à câbler ultérieurement).
	// On l'affiche honnêtement (pas de bouton « Installer » trompeur).
	$: comingSoon = entry.installable === false && !entry.installed && !entry.preset;

	// Accès en langage client (pas de jargon : ni transport http/stdio, ni « OAuth »).
	const ACCESS_LABEL: Record<string, string> = {
		none: 'Prêt à l’emploi',
		key: 'Clé API requise',
		oauth: 'Connexion par compte'
	};

	// Nom d'affichage + description FR + actions du connecteur (fallback sur les valeurs du
	// registre/Hermes brutes : libellé puis nom technique).
	$: fr = CONNECTOR_FR[entry.name];
	$: displayName = fr?.name ?? entry.label ?? entry.name;
	$: displayDesc = fr?.desc ?? entry.description ?? '';
	$: actions = fr?.actions ?? [];
	// Logo : local prioritaire (qualité maîtrisée), sinon logo distant du registre.
	$: logoSrc = CONNECTOR_LOGO[entry.name] ?? entry.icon_url ?? '';
	// Bord-à-bord seulement pour nos logos locaux « carré plein » ; les logos distants
	// (icônes SVG du registre) s'affichent en `contain` sur fond blanc.
	$: fullBleed = CONNECTOR_LOGO_FULL_BLEED.has(entry.name);

	let keyValue = '';
	let working = false;
	let oauthOpen = false;
	let showKeyInput = false;
	let keyInputEl: HTMLInputElement | undefined;
	// « Ce que ça fait » replié par défaut (cartes compactes) : déplié au clic sur le
	// lien bleu, comme l'onglet Outils. Évite les gros blocs quand la liste est longue.
	let expanded = false;

	// Champ clé API replié par défaut (cartes compactes et de même hauteur).
	// Au clic, on révèle l'emplacement de saisie et on y place le curseur.
	const toggleKeyInput = async () => {
		showKeyInput = !showKeyInput;
		if (showKeyInput) {
			await tick();
			keyInputEl?.focus();
		}
	};

	// Attend la fin de l'installation asynchrone (git clone + bootstrap côté Hermes).
	const waitInstall = async () => {
		for (let i = 0; i < 60; i++) {
			await new Promise((r) => setTimeout(r, 1500));
			const s = await getInstallStatus(localStorage.token, entry.name).catch(() => null);
			if (s && s.started && !s.running) return s.success ?? false;
		}
		return false;
	};

	const install = async () => {
		working = true;
		// Preset à clé (ex. Apify) : exiger le token avant d'ajouter le connecteur.
		if (remoteConfig?.auth_type === 'key' && !keyValue) {
			if (!showKeyInput) await toggleKeyInput();
			toast.error($i18n.t('Saisis la clé API d’abord'));
			working = false;
			return;
		}
		try {
			// Connecteur distant (preset maison HubSpot OU MCP remote du registre) : on l'ajoute
			// en custom (http/OAuth) puis on lance directement la connexion par compte.
			if (remoteConfig) {
				try {
					await addCustomConnector(localStorage.token, {
						name: entry.name,
						transport: remoteConfig.transport,
						url: remoteConfig.url,
						auth_type: remoteConfig.auth_type
					});
				} catch (err: any) {
					// Déjà ajouté précédemment (clic répété) : on poursuit vers l'OAuth.
					if (err?.error?.code !== 'name_conflict') throw err;
				}
				if (remoteConfig.auth_type === 'oauth') {
					await startConnectorOAuth(localStorage.token, entry.name);
					oauthOpen = true;
				} else if (remoteConfig.auth_type === 'key') {
					// La clé (token) est posée après l'ajout : remplit la variable d'env
					// référencée par l'en-tête Authorization du connecteur.
					await setConnectorKey(localStorage.token, entry.name, keyValue);
					keyValue = '';
					toast.success($i18n.t('Connecteur installé.'));
					dispatch('changed');
				} else {
					toast.success($i18n.t('Connecteur installé.'));
					dispatch('changed');
				}
				return;
			}

			// MCP du registre (stdio) : le bridge résout le manifest. Avec champs → on les demande
			// (révélés au 1er clic), sinon installation directe.
			if (entry.install_method === 'registry') {
				if (needsFields) {
					if (!showFields) {
						showFields = true;
						working = false;
						return;
					}
					const missing = fields.find((f) => f.required && !fieldValues[f.key]?.trim());
					if (missing) {
						toast.error($i18n.t('Renseigne les champs requis'));
						working = false;
						return;
					}
				}
				// Champs `array` (ex. dossiers autorisés) : séparés par virgule ou retour à la ligne.
				const values: Record<string, string | string[]> = {};
				for (const f of fields) {
					const raw = fieldValues[f.key]?.trim();
					if (!raw) continue;
					values[f.key] =
						f.type === 'array' ? raw.split(/[\n,]/).map((s) => s.trim()).filter(Boolean) : raw;
				}
				await installFromRegistry(localStorage.token, entry.name, values);
				fieldValues = {};
				showFields = false;
				toast.success($i18n.t('Connecteur installé.'));
				dispatch('changed');
				return;
			}
			// 1) clé API d'abord (pour une install non-interactive)
			if (entry.auth_type === 'key') {
				if (!keyValue) {
					// Révèle le champ replié et guide la saisie au lieu d'un simple message.
					if (!showKeyInput) await toggleKeyInput();
					toast.error($i18n.t('Saisis la clé API d’abord'));
					working = false;
					return;
				}
				await setConnectorKey(localStorage.token, entry.name, keyValue);
				keyValue = '';
			}
			// 2) installation
			await installConnector(localStorage.token, entry.name);
			const ok = await waitInstall();
			if (!ok) {
				toast.error($i18n.t('L’installation a échoué.'));
				return;
			}
			// 3) OAuth si nécessaire
			if (entry.auth_type === 'oauth') {
				await startConnectorOAuth(localStorage.token, entry.name);
				oauthOpen = true;
			} else {
				toast.success($i18n.t('Connecteur installé.'));
				dispatch('changed');
			}
		} catch {
			toast.error($i18n.t('Impossible d’installer ce connecteur.'));
		} finally {
			working = false;
		}
	};
</script>

<div
	class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 h-full transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm"
>
	<div class="flex items-start gap-2.5">
		{#if logoSrc}
			<div
				class="size-12 flex-none rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {fullBleed
					? ''
					: 'bg-white p-0.5'}"
			>
				<img
					src={logoSrc}
					alt={entry.name}
					class={fullBleed ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
					draggable="false"
				/>
			</div>
		{/if}
		<div class="flex-1 min-w-0 flex flex-col gap-1">
			<div class="text-sm font-medium leading-tight line-clamp-1">{displayName}</div>
			{#if displayDesc}
				<div class="text-xs text-gray-500 leading-snug line-clamp-2">{displayDesc}</div>
			{/if}
		</div>
		{#if entry.installed}
			<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium text-green-700 bg-green-500/10 dark:text-green-400">
				{$i18n.t('Installé')}
			</span>
		{/if}
	</div>

	{#if actions.length > 0}
		{#if !expanded}
			<button
				type="button"
				class="self-start text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline"
				on:click={() => (expanded = true)}
			>
				{$i18n.t('Voir ce que ça fait')} ›
			</button>
		{:else}
			<div class="flex flex-col gap-1.5">
				<div class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
					{$i18n.t('Ce que ça fait')}
				</div>
				<ul class="flex flex-col gap-1 pl-0.5">
					{#each actions as action}
						<li class="flex items-start gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
							<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
							<span>{$i18n.t(action)}</span>
						</li>
					{/each}
				</ul>
				<button
					type="button"
					class="self-start text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
					on:click={() => (expanded = false)}
				>
					{$i18n.t('Masquer')}
				</button>
			</div>
		{/if}
	{/if}

	{#if comingSoon}
		<!-- MCP du registre pas encore branché en 1 clic : état honnête, pas de faux bouton. -->
		<div class="mt-auto flex justify-between items-center gap-2 pt-1">
			<span class="text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Bientôt connectable en 1 clic')}
			</span>
			{#if entry.source_url}
				<a
					class="text-[11px] text-gray-500 hover:text-gray-900 dark:hover:text-white transition inline-flex items-center gap-0.5"
					href={entry.source_url}
					target="_blank"
					rel="noopener noreferrer"
				>
					{$i18n.t('En savoir plus')} ↗
				</a>
			{/if}
		</div>
	{:else if !entry.installed}
		<div class="mt-auto flex flex-col gap-2.5">
			<!-- MCP du registre à champs (clé/dossier…) : révélés au 1er clic sur Installer. -->
			{#if needsFields && showFields}
				<div class="flex flex-col gap-2 mb-0.5">
					{#each fields as f (f.key)}
						<label class="flex flex-col gap-1 text-[11px] text-gray-500 dark:text-gray-400">
							<span>{f.label || f.key}{f.required ? ' *' : ''}</span>
							<input
								class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
								type={f.secret ? 'password' : 'text'}
								placeholder={f.type === 'array' ? $i18n.t('séparés par des virgules') : ''}
								bind:value={fieldValues[f.key]}
								autocomplete="off"
							/>
						</label>
					{/each}
				</div>
			{/if}
			{#if entry.auth_type === 'key' && entry.install_method !== 'registry' && showKeyInput}
				<input
					bind:this={keyInputEl}
					class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
					type="password"
					placeholder={displayName + ' — ' + $i18n.t('clé API')}
					bind:value={keyValue}
					autocomplete="off"
				/>
			{/if}
			<div class="flex justify-between items-center gap-2">
				<span class="text-[11px] text-gray-500 dark:text-gray-400 truncate">
					{$i18n.t(ACCESS_LABEL[entry.auth_type] ?? '')}
				</span>
				<div class="flex items-center gap-2 flex-none">
				{#if entry.auth_type === 'key' && entry.install_method !== 'registry'}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg border transition flex items-center gap-1.5 {showKeyInput
							? 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200'
							: 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850'}"
						on:click={toggleKeyInput}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
							<path fill-rule="evenodd" d="M8 7a5 5 0 1 1 3.61 4.804l-1.903 1.903A1 1 0 0 1 9 14H8v1a1 1 0 0 1-1 1H6v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-2a1 1 0 0 1 .293-.707L8.196 8.39A5.002 5.002 0 0 1 8 7Zm5-3a.75.75 0 0 0 0 1.5A1.5 1.5 0 0 1 14.5 7 .75.75 0 0 0 16 7a3 3 0 0 0-3-3Z" clip-rule="evenodd" />
						</svg>
						{showKeyInput ? $i18n.t('Masquer') : $i18n.t('Clé API')}
					</button>
				{/if}
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
					disabled={working}
					on:click={install}
				>
					{#if working}
						<Spinner className="size-3.5" />
					{:else if entry.auth_type === 'oauth'}
						{$i18n.t('Installer & connecter')}
					{:else}
						{$i18n.t('Installer')}
					{/if}
				</button>
			</div>
		</div>
		</div>
	{/if}
</div>

<OAuthProgressModal
	connectorId={entry.name}
	bind:open={oauthOpen}
	on:connected={() => {
		oauthOpen = false;
		dispatch('changed');
	}}
	on:close={() => {
		oauthOpen = false;
		dispatch('changed');
	}}
/>
