<script>
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { mobile, showSidebar, user, expertMode } from '$lib/stores';
	import { goto } from '$app/navigation';

	import ConnectorList from '$lib/components/connectors/ConnectorList.svelte';
	import CatalogList from '$lib/components/connectors/CatalogList.svelte';
	import AddConnectorModal from '$lib/components/connectors/AddConnectorModal.svelte';
	import ToolsetList from '$lib/components/capabilities/ToolsetList.svelte';
	import SkillList from '$lib/components/capabilities/SkillList.svelte';
	import IntegrationsList from '$lib/components/integrations/IntegrationsList.svelte';
	import GatewayList from '$lib/components/gateway/GatewayList.svelte';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	let loaded = false;
	// Onglet principal de la page Capacités. Par défaut : Modèles IA (1er onglet).
	let section = 'providers';
	// Sous-vue de l'onglet Connecteurs (existant) : mes connecteurs / catalogue.
	let connectorTab = 'installed';
	let showAddModal = false;

	// Chaque onglet a sa bannière premium : texte d'accroche + palette dégradée distincte.
	// Les classes Tailwind sont écrites en toutes lettres (littéraux) pour être compilées.
	const sections = [
		{
			key: 'providers',
			label: 'Modèles IA',
			desc: 'Choisissez les modèles d’intelligence artificielle qui font tourner votre assistant.',
			banner: {
				lead: 'Choisissez le',
				strong: 'cerveau de votre assistant',
				sub: 'Les modèles d’IA qui le font réfléchir.',
				wrap: 'from-emerald-200/70 via-green-100/50 to-lime-100/60 dark:from-emerald-900/30 dark:via-green-900/20 dark:to-lime-900/20',
				halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
				halo2: 'bg-lime-300/30 dark:bg-lime-500/10'
			}
		},
		{
			key: 'messaging',
			label: 'Messagerie',
			desc: 'Reliez vos canaux (WhatsApp, Telegram, e-mail…) pour échanger avec votre assistant là où vous êtes déjà.',
			banner: {
				lead: 'Parlez à votre assistant depuis',
				strong: 'WhatsApp, Telegram, e-mail et plus',
				sub: 'Retrouvez-le là où vous échangez déjà.',
				wrap: 'from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20',
				halo1: 'bg-orange-300/40 dark:bg-orange-500/20',
				halo2: 'bg-amber-300/30 dark:bg-amber-500/10'
			}
		},
		{
			key: 'integrations',
			label: 'Intégrations',
			desc: 'Connectez vos applications (Google, Notion, GitHub…) pour que votre assistant agisse directement à l’intérieur.',
			banner: {
				lead: 'Connectez votre agent à vos',
				strong: 'e-mails, agendas, fichiers et bien plus',
				sub: 'Il agit directement dans vos applications, à votre place.',
				wrap: 'from-sky-200/70 via-sky-100/50 to-emerald-100/60 dark:from-sky-900/30 dark:via-slate-900/20 dark:to-emerald-900/20',
				halo1: 'bg-indigo-300/40 dark:bg-indigo-500/20',
				halo2: 'bg-sky-300/30 dark:bg-sky-500/10'
			}
		},
		{
			key: 'tools',
			label: 'Outils',
			desc: 'Les capacités natives de votre assistant : recherche web, navigateur, génération d’images, mémoire… Activez ce dont vous avez besoin.',
			banner: {
				lead: 'Donnez des super-pouvoirs à votre assistant :',
				strong: 'recherche web, images, mémoire et plus',
				sub: 'Activez seulement ce dont vous avez besoin.',
				wrap: 'from-violet-200/70 via-indigo-100/50 to-purple-100/60 dark:from-violet-900/30 dark:via-indigo-900/20 dark:to-purple-900/20',
				halo1: 'bg-violet-300/40 dark:bg-violet-500/20',
				halo2: 'bg-indigo-300/30 dark:bg-indigo-500/10'
			}
		},
		{
			key: 'connectors',
			label: 'Connecteurs avancés',
			desc: 'Branchez des serveurs spécialisés (MCP) pour étendre votre assistant à de nouvelles sources et de nouveaux outils.',
			banner: {
				lead: 'Étendez votre assistant avec des',
				strong: 'connecteurs spécialisés (MCP)',
				sub: 'Pour brancher vos sources et outils sur mesure.',
				wrap: 'from-slate-200/70 via-gray-100/50 to-zinc-100/60 dark:from-slate-800/40 dark:via-gray-900/20 dark:to-zinc-900/20',
				halo1: 'bg-slate-300/40 dark:bg-slate-500/20',
				halo2: 'bg-zinc-300/30 dark:bg-zinc-500/10'
			}
		},
		{
			key: 'skills',
			label: 'Compétences',
			desc: 'Le détail des compétences de votre assistant. Réservé aux réglages avancés.',
			banner: {
				lead: 'Le détail des',
				strong: 'compétences de votre assistant',
				sub: 'Réservé aux réglages avancés.',
				wrap: 'from-teal-200/70 via-cyan-100/50 to-emerald-100/60 dark:from-teal-900/30 dark:via-cyan-900/20 dark:to-emerald-900/20',
				halo1: 'bg-teal-300/40 dark:bg-teal-500/20',
				halo2: 'bg-cyan-300/30 dark:bg-cyan-500/10'
			}
		}
	];

	// Mode Expert : « Connecteurs avancés » (MCP) et « Compétences » (panneau technique des
	// skills natives Hermes) n'apparaissent qu'en mode expert. Côté client non-tech, l'assistant
	// a ses compétences activées par défaut — rien à gérer (vision « zéro charge mentale »).
	const expertOnlySections = ['connectors', 'skills'];
	$: visibleSections = $expertMode
		? sections
		: sections.filter((s) => !expertOnlySections.includes(s.key));
	$: if (!$expertMode && expertOnlySections.includes(section)) section = 'providers';
	// Section active (pour afficher son texte d'accroche sous le titre).
	$: activeSection = sections.find((s) => s.key === section);

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
		<!-- Barre fine : zone de glissement fenêtre + bouton sidebar mobile. -->
		<nav class="px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
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
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container">
			<!-- En-tête premium : grand titre + texte d'accroche dynamique + onglets dessous (inspiré Base44). -->
			<div class="w-full max-w-5xl mx-auto px-3 pt-4 sm:pt-6">
				<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-white">
					{$i18n.t('Capacités')}
				</h1>
				{#if activeSection?.desc}
					<p class="mt-1.5 max-w-2xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						{$i18n.t(activeSection.desc)}
					</p>
				{/if}

				<div class="mt-5 flex flex-wrap gap-x-5 gap-y-1 border-b border-gray-200 dark:border-gray-800">
					{#each visibleSections as s}
						<button
							type="button"
							aria-current={section === s.key ? 'page' : null}
							class="relative pb-2.5 text-sm transition {section === s.key
								? 'font-medium text-gray-900 dark:text-white'
								: 'text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'}"
							on:click={() => (section = s.key)}
						>
							{$i18n.t(s.label)}
							{#if section === s.key}
								<span
									class="absolute -bottom-px left-0 right-0 h-0.5 rounded-full bg-gray-900 dark:bg-white"
								></span>
							{/if}
						</button>
					{/each}
				</div>

				<!-- Bannière premium : couleur + texte selon l'onglet actif (inspiré Base44). -->
				{#if activeSection?.banner}
					<div
						class="relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br {activeSection.banner
							.wrap}"
					>
						<div
							class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {activeSection
								.banner.halo1}"
						></div>
						<div
							class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {activeSection
								.banner.halo2}"
						></div>
						<div
							class="relative flex flex-col items-center justify-center gap-2.5 px-6 py-12 text-center"
						>
							<div
								class="rounded-full bg-white/90 px-6 py-2.5 text-base text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
							>
								{$i18n.t(activeSection.banner.lead)}
								<span class="font-semibold text-gray-900 dark:text-white"
									>{$i18n.t(activeSection.banner.strong)}</span
								>
							</div>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{$i18n.t(activeSection.banner.sub)}
							</p>
						</div>
					</div>
				{/if}
			</div>

			{#if section === 'tools'}
				<ToolsetList />
			{:else if section === 'integrations'}
				<IntegrationsList />
			{:else if section === 'messaging'}
				<GatewayList />
			{:else if section === 'providers'}
				<ProviderList />
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
								{$i18n.t('Ajouter un connecteur personnalisé')}
							</button>
						{/if}
					</div>
				</div>

				{#if connectorTab === 'installed'}
					<ConnectorList />
				{:else}
					<div class="w-full max-w-5xl mx-auto px-3 py-3">
						<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Installe un connecteur prêt à l’emploi, validé pour ton assistant.')}
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
