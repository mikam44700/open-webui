<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import {
		getCrawl4aiStatus,
		installCrawl4ai,
		uninstallCrawl4ai,
		checkCrawl4aiUpdate,
		startCrawl4aiUpdate,
		getCrawl4aiUpdateStatus
	} from '$lib/apis/capabilities';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import UpdateButton from './UpdateButton.svelte';
	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
	import { CONNECTOR_LOGO, CONNECTOR_LOGO_FULL_BLEED } from '$lib/utils/connectorLogos';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	// Badge « MCP » : affiché seulement dans « Recherche & web » (redondant dans l'onglet MCP).
	export let showMcpBadge = false;

	const NAME = 'crawl4ai';

	// Libellés FR + logo, comme les cartes du catalogue (cohérence visuelle).
	$: fr = CONNECTOR_FR[NAME];
	$: displayName = fr?.name ?? 'Crawl4AI';
	// Phrase grise courte (non coupée) — le détail est dans la liste dépliable de la carte.
	const SHORT_DESC = 'Lecture web approfondie, souveraine et gratuite.';
	$: displayDesc = SHORT_DESC;
	$: actions = fr?.actions ?? [];
	$: logoSrc = CONNECTOR_LOGO[NAME] ?? '';
	$: fullBleed = CONNECTOR_LOGO_FULL_BLEED.has(NAME);

	// État renvoyé par le bridge : { installed, running, active }.
	// `active` = conteneur en marche ET connecteur MCP enregistré dans Hermes.
	let status: { installed: boolean; running: boolean; active: boolean } | null = null;
	let busy = false;
	let expanded = false;

	$: installed = status?.active ?? false;

	const refresh = async () => {
		status = await getCrawl4aiStatus(localStorage.token).catch(() => null);
	};

	onMount(refresh);

	const install = async () => {
		busy = true;
		// Le 1er démarrage télécharge une image lourde (navigateur embarqué) → message honnête.
		toast.info(
			$i18n.t('Installation de Crawl4AI… le premier téléchargement peut prendre quelques minutes.')
		);
		try {
			status = await installCrawl4ai(localStorage.token);
			if (status?.active) {
				toast.success($i18n.t('Crawl4AI est installé et prêt.'));
				dispatch('changed');
			} else {
				toast.error($i18n.t('Crawl4AI a démarré mais n’est pas encore actif.'));
			}
		} catch (err: any) {
			toast.error(err?.detail ?? $i18n.t('Impossible d’installer Crawl4AI.'));
		} finally {
			busy = false;
		}
	};

	const uninstall = async () => {
		busy = true;
		try {
			status = await uninstallCrawl4ai(localStorage.token);
			toast.success($i18n.t('Crawl4AI a été désinstallé (espace disque libéré).'));
			dispatch('changed');
		} catch (err: any) {
			toast.error(err?.detail ?? $i18n.t('Impossible de désinstaller Crawl4AI.'));
		} finally {
			busy = false;
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
					alt={NAME}
					class={fullBleed ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
					draggable="false"
				/>
			</div>
		{/if}
		<div class="flex-1 min-w-0 flex flex-col gap-1">
			<div class="flex items-center gap-1.5 min-w-0">
				<span class="text-sm font-medium leading-tight line-clamp-1">{displayName}</span>
				{#if showMcpBadge}
					<span
						class="flex-none text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-850 text-gray-500"
						>{$i18n.t('MCP')}</span
					>
				{/if}
			</div>
			{#if displayDesc}
				<div class="text-xs text-gray-500 leading-snug">{displayDesc}</div>
			{/if}
		</div>
		{#if installed}
			<span
				class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium text-green-700 bg-green-500/10 dark:text-green-400"
			>
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
				<div
					class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
				>
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

	<div class="mt-auto flex justify-between items-center gap-2 pt-1">
		<span class="text-[11px] text-gray-500 dark:text-gray-400 truncate">
			{#if installed}
				{$i18n.t('Souverain · actif')}
			{:else}
				{$i18n.t('Souverain · gratuit')}
			{/if}
		</span>
		<div class="flex items-center gap-2 flex-none">
			{#if installed}
				<UpdateButton
					enabled={installed}
					toolLabel={displayName}
					check={() => checkCrawl4aiUpdate(localStorage.token)}
					start={() => startCrawl4aiUpdate(localStorage.token)}
					poll={() => getCrawl4aiUpdateStatus(localStorage.token)}
					on:updated={refresh}
				/>
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-40 flex items-center gap-1.5"
					disabled={busy}
					on:click={uninstall}
				>
					{#if busy}
						<Spinner className="size-3.5" />
					{:else}
						{$i18n.t('Désinstaller')}
					{/if}
				</button>
			{:else}
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40 flex items-center gap-1.5"
					disabled={busy}
					on:click={install}
				>
					{#if busy}
						<Spinner className="size-3.5" />
						{$i18n.t('Installation…')}
					{:else}
						{$i18n.t('Installer')}
					{/if}
				</button>
			{/if}
		</div>
	</div>
</div>
