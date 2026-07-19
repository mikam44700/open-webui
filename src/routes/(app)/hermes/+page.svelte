<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar, expertMode, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import GatewayList from '$lib/components/gateway/GatewayList.svelte';
	import IntegrationsList from '$lib/components/integrations/IntegrationsList.svelte';
	import McpList from '$lib/components/connectors/McpList.svelte';
	import WebSearchList from '$lib/components/capabilities/WebSearchList.svelte';
	import ToolsetList from '$lib/components/capabilities/ToolsetList.svelte';
	import SkillList from '$lib/components/capabilities/SkillList.svelte';
	import GuardrailsPanel from '$lib/components/capabilities/GuardrailsPanel.svelte';
	import { prefetchTools } from '$lib/apis/capabilities';
	import mcpLogo from '$lib/assets/connectors/mcp.svg';

	// --- Onglets de l'espace de travail ---
	// « Compétences » (panneau technique des skills natives Hermes, porté de la v1)
	// n'apparaît qu'en Réglages avancés : côté client non-tech, les compétences sont
	// activées par défaut — rien à gérer (zéro charge mentale).
	const ONGLETS = [
		'Modèles IA',
		'Messagerie',
		'Intégrations',
		'MCP',
		'Recherche & web',
		'Outils',
		'Garde-fous',
		'Compétences'
	] as const;
	type Onglet = (typeof ONGLETS)[number];
	let ongletActif: Onglet = 'Modèles IA';

	const ONGLETS_EXPERTS: Onglet[] = ['Compétences'];
	$: ongletsVisibles = $expertMode
		? [...ONGLETS]
		: ONGLETS.filter((o) => !ONGLETS_EXPERTS.includes(o));
	// Réglages avancés désactivés pendant qu'on est sur un onglet expert → retour Modèles IA.
	$: if (!$expertMode && ONGLETS_EXPERTS.includes(ongletActif)) ongletActif = 'Modèles IA';

	// Lien profond (porté de la v1) : ?tab=providers|messaging|integrations|connectors|
	// web-search|tools|skills ouvre directement le bon onglet (clés v1 conservées pour ne
	// casser aucun lien existant).
	const TAB_PAR_CLE: Record<string, Onglet> = {
		providers: 'Modèles IA',
		messaging: 'Messagerie',
		integrations: 'Intégrations',
		connectors: 'MCP',
		mcp: 'MCP',
		'web-search': 'Recherche & web',
		tools: 'Outils',
		guardrails: 'Garde-fous',
		skills: 'Compétences'
	};

	// Bannières premium par onglet (portées de la v1) : accroche + palette dégradée.
	// Classes Tailwind en toutes lettres (littéraux) pour être compilées.
	type Banniere = {
		lead: string;
		strong: string;
		sub: string;
		wrap: string;
		halo1: string;
		halo2: string;
	};
	const SECTIONS: Record<string, { desc: string; logo?: string; banner: Banniere }> = {
		'Modèles IA': {
			desc: "Choisissez les modèles d'intelligence artificielle qui font tourner votre assistant.",
			banner: {
				lead: 'Choisissez le',
				strong: 'modèle IA de votre assistant',
				sub: "Les modèles d'IA qui le font réfléchir.",
				wrap: 'from-emerald-200/70 via-green-100/50 to-lime-100/60 dark:from-emerald-900/30 dark:via-green-900/20 dark:to-lime-900/20',
				halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
				halo2: 'bg-lime-300/30 dark:bg-lime-500/10'
			}
		},
		Messagerie: {
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
		Intégrations: {
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
		MCP: {
			desc: 'Branchez des serveurs spécialisés (MCP) pour étendre votre assistant à de nouvelles sources et de nouveaux outils.',
			logo: mcpLogo,
			banner: {
				lead: 'Étendez votre assistant avec des',
				strong: 'connecteurs spécialisés (MCP)',
				sub: 'Pour brancher vos sources et outils sur mesure.',
				wrap: 'from-rose-200/70 via-pink-100/50 to-fuchsia-100/60 dark:from-rose-900/30 dark:via-pink-900/20 dark:to-fuchsia-900/20',
				halo1: 'bg-rose-400/30 dark:bg-rose-500/20',
				halo2: 'bg-fuchsia-300/30 dark:bg-fuchsia-500/10'
			}
		},
		'Recherche & web': {
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
		Outils: {
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
		'Garde-fous': {
			desc: 'Les protections de la Boucle de confiance : disjoncteur anti-dérapage et mémoire sous votre approbation.',
			banner: {
				lead: 'Vos agents sont',
				strong: 'encadrés, vérifiés, sous votre contrôle',
				sub: 'Rien d’important ne se fait sans votre feu vert — c’est la Boucle de confiance.',
				wrap: 'from-emerald-200/70 via-teal-100/50 to-amber-100/60 dark:from-emerald-900/30 dark:via-teal-900/20 dark:to-amber-900/20',
				halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
				halo2: 'bg-amber-300/30 dark:bg-amber-500/10'
			}
		},
		Compétences: {
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
	};
	$: sectionActive = SECTIONS[ongletActif];

	onMount(() => {
		// Page admin-only (FR-002, porté de la v1) : un compte « user » n'a rien à faire ici.
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}
		// Lien profond ?tab=… (porté de la v1).
		const demande = $page.url.searchParams.get('tab');
		if (demande && TAB_PAR_CLE[demande]) ongletActif = TAB_PAR_CLE[demande];
		// L'onglet Outils charge /tools (~2,5 s côté bridge) : préchargé en fond dès
		// l'ouverture de la page pour un affichage instantané (recette v1).
		prefetchTools(localStorage.token);
	});
</script>

<svelte:head>
	<title>Espace de travail · Hermes</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<nav class="px-3 pt-2 pb-1 shrink-0 flex items-center">
		<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
			<button
				id="sidebar-toggle-button"
				class="cursor-pointer p-1.5 flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={() => showSidebar.set(!$showSidebar)}
				aria-label="Basculer la barre latérale"
			>
				<Sidebar />
			</button>
		</div>
	</nav>

	<div class="flex flex-col w-full px-6 md:px-10 py-4 overflow-y-auto">
		<div class="mb-5 flex items-start justify-between gap-4">
			<div>
				<div
					class="text-xs font-semibold tracking-widest text-gray-500 dark:text-gray-400 uppercase"
				>
					Espace de travail
				</div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-50 mt-1">Hermes Agent</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					{sectionActive?.desc}
				</p>
			</div>

			<!-- Interrupteur global « Réglages avancés » (ex-Mode Expert, porté de la v1) :
			     dévoile le technique sur toute la page. Discret + infobulle pour ne pas
			     perdre le dirigeant non-technique. -->
			<Tooltip
				content="Affiche les options techniques (serveurs, clés API, compétences détaillées). Inutile au quotidien — réservé aux réglages avancés."
				interactive={true}
			>
				<label
					class="flex-none flex items-center gap-2 pt-1 text-xs text-gray-400 dark:text-gray-500 cursor-pointer select-none"
				>
					Réglages avancés
					<Switch state={$expertMode} on:change={() => expertMode.set(!$expertMode)} />
				</label>
			</Tooltip>
		</div>

		<!-- Barre d'onglets -->
		<div
			class="flex flex-wrap items-center gap-1 mb-5 p-1 rounded-full bg-gray-50 dark:bg-gray-850 w-fit"
			role="tablist"
		>
			{#each ongletsVisibles as onglet}
				<button
					role="tab"
					aria-selected={ongletActif === onglet}
					class="px-4 py-1.5 rounded-full text-sm transition {ongletActif === onglet
						? 'bg-white dark:bg-gray-900 font-semibold text-gray-900 dark:text-gray-50 shadow-sm'
						: 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => (ongletActif = onglet)}
				>
					{onglet}
				</button>
			{/each}
		</div>

		<!-- Bannière premium : couleur + texte selon l'onglet actif (portée de la v1) -->
		{#if sectionActive?.banner}
			<!-- shrink-0 : enfant d'un flex-col a hauteur d'ecran, l'overflow-hidden ramene sa
			     taille minimale de flex item a 0 - sans lui le bandeau est ecrase a 0px des que
			     le contenu de l'onglet depasse l'ecran. -->
			<div
				class="relative mb-5 shrink-0 overflow-hidden rounded-3xl bg-linear-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 {sectionActive
					.banner.wrap}"
			>
				<div
					class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {sectionActive
						.banner.halo1}"
				></div>
				<div
					class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {sectionActive
						.banner.halo2}"
				></div>
				<div class="hero-mesh pointer-events-none absolute inset-0"></div>
				<div class="hero-grain pointer-events-none absolute inset-0"></div>
				{#if sectionActive?.logo}
					<div
						class="pointer-events-none absolute left-6 top-1/2 hidden -translate-y-1/2 sm:left-10 sm:flex"
					>
						<div
							class="flex size-16 items-center justify-center rounded-2xl bg-white/90 p-3 shadow-sm backdrop-blur dark:bg-gray-900/80"
						>
							<img
								src={sectionActive.logo}
								alt={ongletActif}
								class="max-h-full max-w-full object-contain dark:invert"
								draggable="false"
							/>
						</div>
					</div>
				{/if}
				<div class="relative flex flex-col items-center justify-center gap-2 px-6 py-8 text-center">
					<div
						class="rounded-full bg-white/90 px-5 py-2 text-sm text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
					>
						{sectionActive.banner.lead}
						<span class="font-semibold text-gray-900 dark:text-white"
							>{sectionActive.banner.strong}</span
						>
					</div>
					<p class="text-sm text-gray-500 dark:text-gray-400">{sectionActive.banner.sub}</p>
				</div>
			</div>
		{/if}

		{#if ongletActif === 'Messagerie'}
			<!-- Canaux de messagerie (porté de la v1) -->
			<div class="-mx-3">
				<GatewayList />
			</div>
		{:else if ongletActif === 'Intégrations'}
			<!-- Applications connectées (porté de la v1) -->
			<div class="-mx-3">
				<IntegrationsList />
			</div>
		{:else if ongletActif === 'MCP'}
			<!-- Connecteurs MCP (porté de la v1) -->
			<div class="-mx-3">
				<McpList />
			</div>
		{:else if ongletActif === 'Recherche & web'}
			<!-- Recherche web, navigateur, X, extraction (porté de la v1) -->
			<div class="-mx-3">
				<WebSearchList />
			</div>
		{:else if ongletActif === 'Outils'}
			<!-- Capacités de l'assistant : toolsets Hermes (porté de la v1) -->
			<div class="-mx-3">
				<ToolsetList />
			</div>
		{:else if ongletActif === 'Garde-fous'}
			<!-- Protections de la Boucle de confiance (chantier Guardrails) -->
			<div class="-mx-3">
				<GuardrailsPanel />
			</div>
		{:else if ongletActif === 'Compétences'}
			<!-- Skills natives Hermes, panneau expert (porté de la v1) -->
			<div class="-mx-3">
				<SkillList />
			</div>
		{:else if ongletActif !== 'Modèles IA'}
			<!-- Onglets à venir -->
			<div
				class="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-5 py-16 text-center"
			>
				<div class="font-medium text-gray-900 dark:text-gray-50">Bientôt disponible</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					L'onglet « {ongletActif} » arrive dans un prochain chantier.
				</div>
			</div>
		{:else}
			<!-- Modèles IA : ProviderList v1 entier, non bridé (conformité v1) — il porte
			     lui-même la ligne « Modèle IA actif », les puces Moteur/Comptes/Clés API/Local
			     (+ « Modèles IA combinés » et « Autres » en Réglages avancés), les compteurs
			     et l'onglet Moteur complet (HermesStatus : état fin + mise à jour du moteur). -->
			<div class="-mx-3">
				<ProviderList />
			</div>
		{/if}
	</div>
</div>
