<script>
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { mobile, showSidebar, user } from '$lib/stores';
	import { goto } from '$app/navigation';

	import ConnectorList from '$lib/components/connectors/ConnectorList.svelte';
	import CatalogList from '$lib/components/connectors/CatalogList.svelte';
	import AddConnectorModal from '$lib/components/connectors/AddConnectorModal.svelte';
	import ToolsetList from '$lib/components/capabilities/ToolsetList.svelte';
	import SkillList from '$lib/components/capabilities/SkillList.svelte';
	import IntegrationsList from '$lib/components/integrations/IntegrationsList.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	let loaded = false;
	// Onglet principal de la page Capacités : outils natifs / connecteurs MCP / compétences.
	let section = 'tools';
	// Sous-vue de l'onglet Connecteurs (existant) : mes connecteurs / catalogue.
	let connectorTab = 'installed';
	let showAddModal = false;

	const sections = [
		{ key: 'tools', label: 'Outils' },
		{ key: 'connectors', label: 'Connecteurs MCP' },
		{ key: 'integrations', label: 'Intégrations' },
		{ key: 'skills', label: 'Compétences' }
	];

	onMount(async () => {
		// FR-002 : page admin-only
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}
		loaded = true;
	});
</script>

{#if loaded}
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav class="px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
			<div class=" flex items-center">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => showSidebar.set(!$showSidebar)}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="ml-2 py-0.5 self-center flex items-center w-full gap-3">
					<span class="text-sm font-medium">{$i18n.t('Capacités')}</span>
					<div class="flex gap-1 text-sm font-medium">
						{#each sections as s}
							<button
								type="button"
								class="px-2.5 py-1 rounded-lg transition {section === s.key
									? 'bg-gray-100 dark:bg-gray-850'
									: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
								on:click={() => (section = s.key)}
							>
								{$i18n.t(s.label)}
							</button>
						{/each}
					</div>
				</div>
			</div>
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container">
			{#if section === 'tools'}
				<ToolsetList />
			{:else if section === 'integrations'}
				<IntegrationsList />
			{:else if section === 'skills'}
				<SkillList />
			{:else}
				<!-- Connecteurs MCP : sous-vues existantes (mes connecteurs / catalogue) -->
				<div class="w-full max-w-5xl mx-auto px-3 pt-3">
					<div class="flex items-center justify-between gap-2">
						<div class="flex gap-1 text-sm font-medium">
							<button
								type="button"
								class="px-2.5 py-1 rounded-lg transition {connectorTab === 'installed'
									? 'bg-gray-100 dark:bg-gray-850'
									: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
								on:click={() => (connectorTab = 'installed')}
							>
								{$i18n.t('Mes connecteurs')}
							</button>
							<button
								type="button"
								class="px-2.5 py-1 rounded-lg transition {connectorTab === 'catalog'
									? 'bg-gray-100 dark:bg-gray-850'
									: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
								on:click={() => (connectorTab = 'catalog')}
							>
								{$i18n.t('Catalogue')}
							</button>
						</div>
						{#if connectorTab === 'catalog'}
							<button
								type="button"
								class="flex-none text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => (showAddModal = true)}
							>
								{$i18n.t('Ajouter un MCP custom')}
							</button>
						{/if}
					</div>
				</div>

				{#if connectorTab === 'installed'}
					<ConnectorList />
				{:else}
					<div class="w-full max-w-5xl mx-auto px-3 py-3">
						<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Installe un connecteur prêt à l’emploi, validé pour Hermes.')}
						</div>
						<CatalogList on:changed={() => (connectorTab = 'installed')} />
					</div>
				{/if}
			{/if}
		</div>
	</div>

	<AddConnectorModal
		bind:open={showAddModal}
		on:added={() => {
			showAddModal = false;
			connectorTab = 'installed';
		}}
		on:close={() => (showAddModal = false)}
	/>
{/if}
