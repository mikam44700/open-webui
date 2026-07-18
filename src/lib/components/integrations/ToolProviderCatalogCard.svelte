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
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import {
		type Provider,
		LOGO_BY_SLUG,
		WHITE_BG_SLUGS,
		LOGO_TIGHT_SLUGS,
		providerStatus,
		PROVIDER_ABOUT,
		PROVIDER_SHORT,
		PROVIDER_TAGS
	} from '$lib/utils/toolConnect';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Carte compacte de catalogue (même look que IntegrationCard) pour un fournisseur d'un toolset
	// Hermes. Gère les 3 types : clé (Se connecter → champ), sans-clé/abonnement (badge seul),
	// et OAuth par compte (bouton Autoriser). Branché sur le vrai mécanisme du toolset.
	export let toolsetName: string;
	export let provider: Provider;

	let showField = false;
	let fieldValue = '';
	let busy = false;
	let fieldEl: HTMLInputElement | undefined;

	// « Ce que ça fait » : puces dédiées si dispo, sinon la description courte → le lien
	// apparaît sur toutes les cartes.
	let aboutExpanded = false;
	$: about =
		(provider.slug && PROVIDER_ABOUT[provider.slug]) || (provider.tag ? [provider.tag] : []);
	// Phrase grise courte (non coupée) : version dédiée si dispo, sinon la description du bridge.
	$: shortDesc = (provider.slug && PROVIDER_SHORT[provider.slug]) || provider.tag || '';
	// Tags de capacités (pastilles courtes) — d'un coup d'œil, ce que fait le fournisseur.
	$: tags = (provider.slug && PROVIDER_TAGS[provider.slug]) || [];

	$: field = provider.fields?.[0] ?? null;
	$: status = providerStatus(provider);
	$: saved = status === 'saved';
	$: isKey = provider.kind === 'key';
	$: isOAuth = provider.kind === 'oauth';

	// Badge d'état (honnête, mêmes libellés que la carte dépliée).
	const BADGE: Record<string, { label: string; cls: string }> = {
		saved: { label: 'Clé enregistrée', cls: 'text-sky-700 bg-sky-500/10 dark:text-sky-400' },
		detected: { label: 'Connecté', cls: 'text-green-700 bg-green-500/10 dark:text-green-400' },
		disconnected: { label: 'Non connecté', cls: 'text-amber-700 bg-amber-500/10 dark:text-amber-400' },
		active: { label: 'Actif sans clé', cls: 'text-green-700 bg-green-500/10 dark:text-green-400' },
		local: { label: 'Sans clé · local', cls: 'text-gray-600 bg-gray-500/10 dark:text-gray-400' },
		subscription: {
			label: 'Abonnement Nous',
			cls: 'text-indigo-700 bg-indigo-500/10 dark:text-indigo-400'
		},
		none: { label: 'Non connecté', cls: 'text-gray-600 bg-gray-500/10 dark:text-gray-400' }
	};
	$: badge = BADGE[status] ?? BADGE.none;
	// Actif = réellement connecté/vérifié → pastille verte clignotante « Actif ».
	$: connectedActive = status === 'detected' || status === 'active';
	// Non connecté = redondant (le bouton « Se connecter » suffit) → pas de chip.
	$: hideBadge = status === 'disconnected' || status === 'none';

	// Suivi OAuth (propre à ce fournisseur).
	let oauthRunning = false;
	let oauthAuthUrl: string | null = null;
	let oauthTimer: ReturnType<typeof setInterval> | null = null;
	const stopOAuth = () => {
		if (oauthTimer) {
			clearInterval(oauthTimer);
			oauthTimer = null;
		}
	};
	onDestroy(stopOAuth);

	const openField = async () => {
		showField = true;
		await Promise.resolve();
		fieldEl?.focus();
	};

	const onSave = async () => {
		if (!field || !fieldValue.trim()) return;
		busy = true;
		try {
			await setToolKey(localStorage.token, toolsetName, { [field.key]: fieldValue.trim() });
			for (const f of provider.fields) if (f.key === field.key) f.present = true;
			provider = provider;
			fieldValue = '';
			showField = false;
			toast.success($i18n.t('Clé enregistrée.'));
			dispatch('changed');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Échec de l’enregistrement.'));
		} finally {
			busy = false;
		}
	};

	const onTest = async () => {
		busy = true;
		try {
			const res = await testToolKey(localStorage.token, toolsetName, {});
			if (res?.tested && res?.ok) toast.success($i18n.t('Connexion réussie !'));
			else toast.error($i18n.t('Échec de la connexion') + (res?.reason ? ` : ${res.reason}` : ''));
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Impossible de tester.'));
		} finally {
			busy = false;
		}
	};

	const onDisconnect = async () => {
		busy = true;
		try {
			await disconnectToolProvider(localStorage.token, toolsetName, provider.fields.map((f) => f.key));
			for (const f of provider.fields) f.present = false;
			provider = provider;
			toast.success($i18n.t('Déconnecté.'));
			dispatch('changed');
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Impossible de déconnecter.'));
		} finally {
			busy = false;
		}
	};

	const pollOAuth = async () => {
		try {
			const s = await getToolOAuthStatus(localStorage.token, toolsetName);
			oauthAuthUrl = s?.auth_url ?? null;
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
		busy = true;
		try {
			await startToolOAuth(localStorage.token, toolsetName);
			oauthRunning = true;
			oauthAuthUrl = null;
			stopOAuth();
			pollOAuth();
			oauthTimer = setInterval(pollOAuth, 1500);
		} catch (err: any) {
			toast.error(err?.error?.message ?? $i18n.t('Impossible de démarrer la connexion'));
		} finally {
			busy = false;
		}
	};
</script>

<div
	class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 h-full card-lift hover:border-gray-200 dark:hover:border-gray-700"
>
	<div class="flex items-start gap-2.5">
		{#if provider.slug && LOGO_BY_SLUG[provider.slug]}
			<div
				class="size-12 flex-none rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {WHITE_BG_SLUGS.has(
					provider.slug
				)
					? LOGO_TIGHT_SLUGS.has(provider.slug)
						? 'bg-white'
						: 'bg-white p-1'
					: ''}"
			>
				<img
					src={LOGO_BY_SLUG[provider.slug]}
					alt={provider.name}
					class={WHITE_BG_SLUGS.has(provider.slug)
						? 'max-w-full max-h-full object-contain'
						: 'w-full h-full object-cover'}
					draggable="false"
				/>
			</div>
		{/if}
		<div class="flex-1 min-w-0 flex flex-col gap-1">
			<div class="text-sm font-medium leading-tight">{provider.name}</div>
			{#if shortDesc}
				<div class="text-xs text-gray-500 leading-snug">{shortDesc}</div>
			{/if}
		</div>
		{#if connectedActive}
			<span class="flex-none"><ActiveBadge /></span>
		{:else if !hideBadge}
			<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium {badge.cls}">
				{$i18n.t(badge.label)}
			</span>
		{/if}
	</div>

	{#if tags.length > 0}
		<div class="flex flex-wrap gap-1">
			{#each tags as t}
				<span
					class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
					>{$i18n.t(t)}</span
				>
			{/each}
		</div>
	{/if}

	{#if about.length > 0}
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
					{#each about as line}
						<li class="flex items-start gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
							<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
							<span>{$i18n.t(line)}</span>
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
		{#if isKey && showField && field}
			<input
				bind:this={fieldEl}
				type="password"
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				placeholder={$i18n.t('Colle ta clé / ton token')}
				bind:value={fieldValue}
				autocomplete="off"
				on:keydown={(e) => e.key === 'Enter' && onSave()}
			/>
			{#if field.url}
				<a
					class="text-[11px] text-sky-600 dark:text-sky-400 underline"
					href={field.url}
					target="_blank"
					rel="noopener">{$i18n.t('Obtenir cette valeur')}</a
				>
			{/if}
		{/if}

		<div class="flex items-center justify-between gap-2">
			<span class="text-[11px] text-gray-500 dark:text-gray-400">
				{provider.badge ?? (isKey ? $i18n.t('Clé requise') : '')}
			</span>

			<div class="flex items-center gap-1.5">
				{#if isKey && showField}
					<button
						type="button"
						class="text-xs px-3 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black btn-premium disabled:opacity-40"
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
				{:else if isKey && saved}
					<button
						type="button"
						class="text-xs px-3 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black btn-premium disabled:opacity-40"
						disabled={busy}
						on:click={onTest}
					>
						{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Tester')}{/if}
					</button>
					<button
						type="button"
						class="text-xs px-2.5 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition disabled:opacity-40"
						disabled={busy}
						on:click={onDisconnect}
					>
						{$i18n.t('Déconnecter')}
					</button>
				{:else if isKey}
					<button
						type="button"
						class="text-xs px-3 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black btn-premium"
						on:click={openField}
					>
						{$i18n.t('Se connecter')}
					</button>
				{:else if isOAuth && status !== 'detected'}
					<button
						type="button"
						class="text-xs px-3 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black btn-premium disabled:opacity-40"
						disabled={busy || oauthRunning}
						on:click={startOAuth}
					>
						{#if oauthRunning}<Spinner className="size-3.5" />{:else}{$i18n.t('Autoriser')}{/if}
					</button>
				{/if}
			</div>
		</div>

		{#if isOAuth && oauthRunning}
			<div class="text-[11px] text-gray-500 dark:text-gray-400">
				{$i18n.t('Autorisation en cours… une fenêtre s’est ouverte sur l’hôte.')}
			</div>
			{#if oauthAuthUrl}
				<a
					class="text-[11px] text-sky-600 dark:text-sky-400 underline break-all"
					href={oauthAuthUrl}
					target="_blank"
					rel="noopener">{oauthAuthUrl}</a
				>
			{/if}
		{/if}
	</div>
</div>
