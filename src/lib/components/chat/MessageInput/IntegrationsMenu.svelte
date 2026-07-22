<script lang="ts">
	import { getContext } from 'svelte';
	import { fly } from 'svelte/transition';

	import { getToolConnection } from '$lib/apis/capabilities';
	import { getMessagingPlatforms, type MessagingPlatform } from '$lib/apis/gateway';
	import { getIntegrations } from '$lib/apis/integrations';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { INTEGRATION_FR } from '$lib/utils/integrationLabels';
	import { INTEGRATION_LOGO } from '$lib/utils/integrationLogos';
	import { LOGO_BY_SLUG, providerStatus, type Provider } from '$lib/utils/toolConnect';

	const i18n = getContext('i18n');

	// Ces propriétés restent exportées car MessageInput partage encore le contrat
	// OpenWebUI. Le menu client ne montre plus les outils/skills/réglages techniques.
	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];
	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];
	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];
	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;
	export let onShowValves: Function;
	export let onClose: Function;
	export let onWebSearchToggle: Function = () => {};
	export let closeOnOutsideClick = true;

	type CategoryId = 'web' | 'messaging' | 'applications';
	type ConnectedService = {
		id: string;
		name: string;
		category: CategoryId;
		icon?: string | null;
		emoji?: string | null;
	};
	type IntegrationState = {
		id: string;
		state: 'not_connected' | 'key_present' | 'connected' | 'error' | 'unavailable';
		visible?: boolean;
	};

	let show = false;
	let loading = false;
	let loaded = false;
	let tab: '' | CategoryId = '';
	let services: ConnectedService[] = [];

	$: webServices = services.filter((service) => service.category === 'web');
	$: messagingServices = services.filter((service) => service.category === 'messaging');
	$: applicationServices = services.filter((service) => service.category === 'applications');
	$: activeServices = tab === 'web'
		? webServices
		: tab === 'messaging'
			? messagingServices
			: tab === 'applications'
				? applicationServices
				: [];

	$: if (show && !loaded && !loading) {
		void loadConnectedServices();
	}

	const uniqueServices = (items: ConnectedService[]) => {
		const seen = new Set<string>();
		return items.filter((item) => {
			const key = `${item.category}:${item.id}`;
			if (seen.has(key)) return false;
			seen.add(key);
			return true;
		});
	};

	const loadConnectedServices = async () => {
		loading = true;
		const token = localStorage.token;
		const [webResults, integrationsResult, messagingResult] = await Promise.all([
			Promise.all(
				['web', 'browser', 'x_search'].map(async (toolsetName) => {
					try {
						return await getToolConnection(token, toolsetName);
					} catch {
						return null;
					}
				})
			),
			getIntegrations(token).catch(() => null),
			getMessagingPlatforms(token).catch(() => null)
		]);

		const connectedWeb = webResults.flatMap((result) =>
			((result?.providers ?? []) as Provider[])
				// Seulement une clé réellement saisie par le client. Les fournisseurs
				// locaux/détectés/abonnements et Crawl4AI restent invisibles ici.
				.filter((provider) => ['saved', 'key-active'].includes(providerStatus(provider)))
				.map((provider) => ({
					id: provider.slug ?? provider.name,
					name: provider.name,
					category: 'web' as const,
					icon: provider.slug ? (LOGO_BY_SLUG[provider.slug] ?? null) : null
				}))
		);

		const connectedApplications = ((integrationsResult?.integrations ?? []) as IntegrationState[])
			.filter(
				(integration) =>
					integration.visible !== false &&
					(integration.state === 'connected' || integration.state === 'key_present')
			)
			.map((integration) => ({
				id: integration.id,
				name: INTEGRATION_FR[integration.id]?.name ?? integration.id,
				category: 'applications' as const,
				icon: INTEGRATION_LOGO[integration.id] ?? null
			}));

		const connectedMessaging = ((messagingResult?.platforms ?? []) as MessagingPlatform[])
			.filter(
				(platform) =>
					platform.available !== false &&
					platform.configured &&
					platform.enabled &&
					(platform.state === 'ready' || platform.state === 'connected')
			)
			.map((platform) => ({
				id: platform.id,
				name: platform.name,
				category: 'messaging' as const,
				emoji: platform.emoji
			}));

		services = uniqueServices([
			...connectedWeb,
			...connectedMessaging,
			...connectedApplications
		]);
		loaded = true;
		loading = false;
	};

	const openCategory = (category: CategoryId) => {
		tab = category;
	};

	const categoryLabel = (category: CategoryId) =>
		category === 'web'
			? 'Recherche & web'
			: category === 'messaging'
				? 'Messagerie'
				: 'Applications';
</script>

<Dropdown
	bind:show
	onOpenChange={(state) => {
		if (state === true) {
			// Rafraîchit l'état à chaque ouverture : une connexion faite depuis
			// Moteur apparaît immédiatement au retour dans le chat.
			loaded = false;
			tab = '';
		} else {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Integrations')} placement="top">
		<slot />
	</Tooltip>
	<div slot="content">
		<div
			class="min-w-70 max-w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
		>
			{#if loading}
				<div class="flex justify-center py-4" aria-label="Chargement des intégrations">
					<Spinner className="size-5" />
				</div>
			{:else if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }}>
					{#if showWebSearchButton && webServices.length > 0}
						<div
							class="flex w-full items-center gap-1 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						>
							<button
								type="button"
								class="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-sm"
								on:click={() => openCategory('web')}
							>
								<GlobeAlt />
								<span class="flex-1 truncate text-left">Recherche &amp; web</span>
								<span class="text-xs text-gray-500 tabular-nums">{webServices.length}</span>
								<span class="text-gray-500"><ChevronRight /></span>
							</button>
							<div class="shrink-0 pr-2">
								<Switch
									state={webSearchEnabled}
									on:change={(event) => {
										webSearchEnabled = event.detail;
										onWebSearchToggle(webSearchEnabled);
									}}
								/>
							</div>
						</div>
					{/if}

					{#if messagingServices.length > 0}
						<button
							type="button"
							class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={() => openCategory('messaging')}
						>
							<ChatBubbles className="size-4" />
							<span class="flex-1 truncate text-left">Messagerie</span>
							<span class="text-xs text-gray-500 tabular-nums">{messagingServices.length}</span>
							<span class="text-gray-500"><ChevronRight /></span>
						</button>
					{/if}

					{#if applicationServices.length > 0}
						<button
							type="button"
							class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={() => openCategory('applications')}
						>
							<Cube className="size-4" />
							<span class="flex-1 truncate text-left">Applications</span>
							<span class="text-xs text-gray-500 tabular-nums">{applicationServices.length}</span>
							<span class="text-gray-500"><ChevronRight /></span>
						</button>
					{/if}

					{#if (!showWebSearchButton || webServices.length === 0) && messagingServices.length === 0 && applicationServices.length === 0}
						<div class="px-3 py-4 text-center">
							<div class="text-sm font-medium">Aucune intégration connectée</div>
							<div class="mt-1 text-xs text-gray-500">Connecte tes services depuis la page Moteur.</div>
						</div>
					{/if}
				</div>
			{:else}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						type="button"
						class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => (tab = '')}
					>
						<ChevronLeft />
						<span class="flex-1 truncate text-left font-medium">{categoryLabel(tab)}</span>
						<span class="text-xs text-gray-500 tabular-nums">{activeServices.length}</span>
					</button>

					<div class="my-1 border-t border-gray-100 dark:border-gray-800" />

					{#each activeServices as service (service.category + ':' + service.id)}
						<div class="flex w-full items-center gap-2 px-3 py-2 text-sm">
							<div class="flex size-5 shrink-0 items-center justify-center overflow-hidden rounded">
								{#if service.icon}
									<img src={service.icon} alt="" class="size-5 object-contain" />
								{:else if service.emoji}
									<span aria-hidden="true">{service.emoji}</span>
								{:else}
									<span class="size-2 rounded-full bg-gray-400" />
								{/if}
							</div>
							<span class="min-w-0 flex-1 truncate">{service.name}</span>
							<span class="shrink-0 text-xs text-green-600 dark:text-green-400">Connecté</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
