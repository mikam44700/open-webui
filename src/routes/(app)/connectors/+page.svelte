<script>
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { mobile, showSidebar, user, expertMode } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import McpList from '$lib/components/connectors/McpList.svelte';
	import mcpLogo from '$lib/assets/connectors/mcp.svg';
	import ToolsetList from '$lib/components/capabilities/ToolsetList.svelte';
	import WebSearchList from '$lib/components/capabilities/WebSearchList.svelte';
	import SkillList from '$lib/components/capabilities/SkillList.svelte';
	import IntegrationsList from '$lib/components/integrations/IntegrationsList.svelte';
	import GatewayList from '$lib/components/gateway/GatewayList.svelte';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import SegmentedTabs from '$lib/components/common/SegmentedTabs.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	let loaded = false;
	// Onglet principal de la page Capacités. Par défaut : Modèles IA (1er onglet).
	let section = 'providers';

	// Lien profond : ?tab=integrations|connectors|tools|… ouvre directement le bon onglet
	// (ex. « Gérer mes connexions » du chat atterrit sur Intégrations). Validé contre la
	// liste des onglets connus pour éviter un onglet fantôme.
	$: {
		const requested = $page.url.searchParams.get('tab');
		if (requested && sections.some((s) => s.key === requested)) {
			section = requested;
		}
	}

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
			key: 'connectors',
			label: 'MCP',
			desc: 'Branchez des serveurs spécialisés (MCP) pour étendre votre assistant à de nouvelles sources et de nouveaux outils.',
			logo: mcpLogo,
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
			key: 'web-search',
			label: 'Recherche & web',
			desc: 'Tous les services de recherche et de navigation web, visibles d’un coup d’œil. Activez et connectez ceux que vous voulez.',
			banner: {
				lead: 'Donnez à votre assistant la',
				strong: 'recherche et la lecture du web',
				sub: 'Tous les fournisseurs réunis, sans rien chercher.',
				wrap: 'from-sky-200/70 via-cyan-100/50 to-blue-100/60 dark:from-sky-900/30 dark:via-cyan-900/20 dark:to-blue-900/20',
				halo1: 'bg-sky-400/30 dark:bg-sky-500/20',
				halo2: 'bg-cyan-300/30 dark:bg-cyan-500/10'
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

	// Mode Expert : « Compétences » (panneau technique des skills natives Hermes) n'apparaît
	// qu'en mode expert. Côté client non-tech, l'assistant a ses compétences activées par
	// défaut — rien à gérer (vision « zéro charge mentale »). L'onglet « MCP » est, lui,
	// visible en permanence (page à part entière, esprit Intégrations).
	const expertOnlySections = ['skills'];
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
			<div class="w-full max-w-7xl mx-auto px-3 pt-4 sm:pt-6">
				<PageHeader
					eyebrow={$i18n.t('Capacités')}
					title={$i18n.t('Ce que votre assistant sait faire')}
					description={activeSection?.desc ? $i18n.t(activeSection.desc) : ''}
				>
					<!-- Interrupteur global « Réglages avancés » (ex-Mode Expert) : dévoile le technique
					     sur toute la page (Compétences, supervision Messagerie, outils techniques).
					     Discret + infobulle pour ne pas perdre le dirigeant non-technique. -->
					<svelte:fragment slot="actions">
						<Tooltip
							content={$i18n.t(
								'Affiche les options techniques (serveurs, clés API, compétences détaillées). Inutile au quotidien — réservé aux réglages avancés.'
							)}
							interactive={true}
						>
							<label
								class="flex-none flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 cursor-pointer select-none"
							>
								{$i18n.t('Réglages avancés')}
								<Switch state={$expertMode} on:change={() => expertMode.set(!$expertMode)} />
							</label>
						</Tooltip>
					</svelte:fragment>
				</PageHeader>

				<!-- Segmented control premium partagé (SegmentedTabs) : pilule glissante + a11y. -->
				<div class="mt-5">
					<SegmentedTabs
						items={visibleSections.map((s) => ({ label: $i18n.t(s.label) }))}
						activeIndex={visibleSections.findIndex((s) => s.key === section)}
						on:select={(e) => (section = visibleSections[e.detail].key)}
					/>
				</div>

				<!-- Bannière premium : couleur + texte selon l'onglet actif (inspiré Base44). -->
				{#if activeSection?.banner}
					<div
						class="relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 {activeSection
							.banner.wrap}"
					>
						<div
							class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {activeSection
								.banner.halo1}"
						></div>
						<div
							class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {activeSection
								.banner.halo2}"
						></div>
						<!-- Matière moderne (mesh + grain), color-agnostique — tous les onglets. -->
						<div class="hero-mesh pointer-events-none absolute inset-0"></div>
						<div class="hero-grain pointer-events-none absolute inset-0"></div>
						{#if activeSection?.logo}
							<div
								class="pointer-events-none absolute left-6 top-1/2 hidden -translate-y-1/2 sm:left-10 sm:flex"
							>
								<div
									class="flex size-16 items-center justify-center rounded-2xl bg-white/90 p-3 shadow-sm backdrop-blur dark:bg-gray-900/80"
								>
									<img
										src={activeSection.logo}
										alt={activeSection.label}
										class="max-h-full max-w-full object-contain dark:invert"
										draggable="false"
									/>
								</div>
							</div>
						{/if}
						<div
							class="relative flex flex-col items-center justify-center gap-2 px-6 py-8 text-center"
						>
							<div
								class="rounded-full bg-white/90 px-5 py-2 text-sm text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
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

			{#if section === 'web-search'}
				<WebSearchList />
			{:else if section === 'tools'}
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
				<!-- MCP : page à part entière, esprit Intégrations (vedettes + parcourir + installés) -->
				<McpList />
			{/if}
		</div>
	</div>
{/if}
