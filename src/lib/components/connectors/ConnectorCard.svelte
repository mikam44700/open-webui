<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { setConnectorEnabled, testConnector, deleteConnector } from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
	import { CONNECTOR_LOGO, CONNECTOR_LOGO_FULL_BLEED } from '$lib/utils/connectorLogos';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let connector: {
		id: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		enabled: boolean;
		state: 'connected' | 'disconnected' | 'error' | 'disabled' | 'incomplete' | 'auth_required';
		endpoint?: string;
		secret_state?: 'present' | 'absent';
		source?: string | null;
	};

	let busy = ''; // '' | 'toggle' | 'test' | 'delete'
	let confirmDelete = false;
	// « Ce que ça fait » replié par défaut, comme dans le catalogue : on garde la liste
	// des capacités accessible même une fois le connecteur installé.
	let expanded = false;

	const toggle = async () => {
		busy = 'toggle';
		try {
			await setConnectorEnabled(localStorage.token, connector.id, !connector.enabled);
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible de modifier ce connecteur'));
		} finally {
			busy = '';
		}
	};

	const test = async () => {
		busy = 'test';
		try {
			const r = await testConnector(localStorage.token, connector.id);
			if (r?.ok)
				toast.success($i18n.t('Connexion réussie') + (r.tools_count != null ? ` (${r.tools_count} outils)` : ''));
			else toast.error($i18n.t('Échec de la connexion') + (r?.reason ? ` : ${r.reason}` : ''));
		} catch {
			toast.error($i18n.t('Impossible de tester ce connecteur'));
		} finally {
			busy = '';
		}
	};

	const remove = async () => {
		busy = 'delete';
		try {
			await deleteConnector(localStorage.token, connector.id);
			toast.success($i18n.t('Connecteur supprimé'));
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible de supprimer ce connecteur'));
		} finally {
			busy = '';
			confirmDelete = false;
		}
	};

	// Libellé + couleur de l'état (cf. data-model ConnectorState).
	const STATE_META: Record<string, { label: string; cls: string }> = {
		connected: { label: 'Connecté', cls: 'text-green-700 bg-green-500/10 dark:text-green-400' },
		disconnected: { label: 'Configuré', cls: 'text-sky-700 bg-sky-500/10 dark:text-sky-400' },
		error: { label: 'Erreur', cls: 'text-red-700 bg-red-500/10 dark:text-red-400' },
		disabled: { label: 'Désactivé', cls: 'text-gray-600 bg-gray-500/10 dark:text-gray-400' },
		incomplete: {
			label: 'Configuration incomplète',
			cls: 'text-amber-700 bg-amber-500/10 dark:text-amber-400'
		},
		auth_required: {
			label: 'Authentification requise',
			cls: 'text-amber-700 bg-amber-500/10 dark:text-amber-400'
		}
	};

	// Accès en langage client (pas de jargon : ni transport http/stdio, ni « OAuth »).
	const ACCESS_LABEL: Record<string, string> = {
		none: 'Prêt à l’emploi',
		key: 'Clé API requise',
		oauth: 'Connexion par compte'
	};

	$: state = STATE_META[connector.state] ?? STATE_META['disconnected'];
	// Logo + nom d'affichage partagés avec le Catalogue (même visuel partout).
	$: logoSrc = CONNECTOR_LOGO[connector.id];
	$: fullBleed = CONNECTOR_LOGO_FULL_BLEED.has(connector.id);
	$: displayName = CONNECTOR_FR[connector.id]?.name ?? connector.id;
	// Capacités (mêmes données FR que le catalogue) — affichées sur demande.
	$: actions = CONNECTOR_FR[connector.id]?.actions ?? [];
</script>

<div
	class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm {connector.enabled
		? ''
		: 'opacity-60'}"
>
	<!-- En-tête : logo connecteur (ou icône générique) + nom + état -->
	<div class="flex items-center gap-2.5">
		{#if logoSrc}
			<div
				class="flex-none size-12 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {fullBleed
					? ''
					: 'bg-white p-0.5'}"
			>
				<img
					src={logoSrc}
					alt={displayName}
					class={fullBleed ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
					draggable="false"
				/>
			</div>
		{:else}
			<div
				class="flex-none size-12 rounded-xl flex items-center justify-center bg-gray-100 dark:bg-gray-850 ring-1 ring-gray-200/70 dark:ring-gray-700/60"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.6"
					stroke="currentColor"
					class="size-4 text-gray-500"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
					/>
				</svg>
			</div>
		{/if}
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium line-clamp-1">{displayName}</div>
			{#if connector.endpoint}
				<div class="text-xs text-gray-500 line-clamp-1">{connector.endpoint}</div>
			{/if}
		</div>
		<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium {state.cls}">
			{$i18n.t(state.label)}
		</span>
	</div>

	<!-- Type d'accès, en langage client (pas de jargon technique) -->
	<div class="flex items-center gap-1.5">
		<span
			class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
		>
			{$i18n.t(ACCESS_LABEL[connector.auth_type] ?? connector.auth_type)}
		</span>
	</div>

	<!-- Ce que ça fait : replié par défaut, déployé au clic (comme le catalogue + l'onglet Outils) -->
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

	<!-- Actions : tester / activer-désactiver / supprimer -->
	<div class="flex items-center justify-end gap-2 pt-2 border-t border-gray-100 dark:border-gray-850">
		<button
			type="button"
			class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition disabled:opacity-40"
			disabled={busy !== ''}
			on:click={test}
		>
			{#if busy === 'test'}<Spinner className="size-3.5" />{:else}{$i18n.t('Tester')}{/if}
		</button>
		<button
			type="button"
			class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition disabled:opacity-40"
			disabled={busy !== ''}
			on:click={toggle}
		>
			{#if busy === 'toggle'}
				<Spinner className="size-3.5" />
			{:else if connector.enabled}
				{$i18n.t('Désactiver')}
			{:else}
				{$i18n.t('Activer')}
			{/if}
		</button>
		{#if confirmDelete}
			<button
				type="button"
				class="text-xs px-2 py-1 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-500/10 transition disabled:opacity-40"
				disabled={busy !== ''}
				on:click={remove}
			>
				{#if busy === 'delete'}<Spinner className="size-3.5" />{:else}{$i18n.t('Confirmer')}{/if}
			</button>
			<button
				type="button"
				class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
				on:click={() => (confirmDelete = false)}
			>
				{$i18n.t('Annuler')}
			</button>
		{:else}
			<button
				type="button"
				class="text-xs px-2 py-1 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-500/10 transition disabled:opacity-40"
				disabled={busy !== ''}
				on:click={() => (confirmDelete = true)}
			>
				{$i18n.t('Supprimer')}
			</button>
		{/if}
	</div>
</div>
