<script lang="ts">
	/**
	 * La page Moteur — LunarIA V2.
	 *
	 * Un seul ecran pour piloter Hermes : quel modele le fait reflechir, a quoi
	 * il est relie, ce qu'il sait faire, ce qu'il n'a pas le droit de faire.
	 *
	 * Habillage repris de la page « Capacites » d'AgentOS V1 : en-tete, onglets
	 * a pilule glissante, et une banniere de couleur propre a chaque onglet. La
	 * couleur n'est pas decorative — elle sert de repere : on sait ou l'on est
	 * avant d'avoir lu le libelle.
	 *
	 * Difference de fond avec la V1 : Hermes tourne desormais dans un conteneur
	 * separe. Tout passe par le backend, qui detient seul la cle d'acces — le
	 * navigateur ne joint jamais le moteur directement.
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar, user, expertMode, mobile } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
	import SegmentedTabs from '$lib/components/common/SegmentedTabs.svelte';

	import { getEtatMoteur, type EtatMoteur } from '$lib/apis/hermes';
	import { prefetchTools } from '$lib/apis/capabilities';

	import GardeFous from '$lib/components/moteur/GardeFous.svelte';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import GatewayList from '$lib/components/gateway/GatewayList.svelte';
	import IntegrationsList from '$lib/components/integrations/IntegrationsList.svelte';
	import McpList from '$lib/components/connectors/McpList.svelte';
	import WebSearchList from '$lib/components/capabilities/WebSearchList.svelte';
	import ToolsetList from '$lib/components/capabilities/ToolsetList.svelte';
	import SkillList from '$lib/components/capabilities/SkillList.svelte';
	import mcpLogo from '$lib/assets/connectors/mcp.svg';

	// --- Les onglets ------------------------------------------------------

	/**
	 * Chaque onglet porte sa banniere : une phrase d'accroche en deux morceaux
	 * (le debut leger, la fin en gras), un sous-titre, et sa palette.
	 *
	 * Les classes Tailwind sont ecrites en toutes lettres, jamais assemblees a
	 * la volee : le compilateur ne garde que les classes qu'il voit ecrites. Une
	 * chaine construite du genre `from-${couleur}-200` produirait un fond
	 * transparent en production, sans la moindre erreur pour prevenir.
	 */
	const ONGLETS = [
		{
			cle: 'modeles',
			label: 'Modèles IA',
			desc: "Choisissez le modèle d'intelligence artificielle qui fait réfléchir votre assistant.",
			banniere: {
				debut: 'Choisissez le',
				fort: 'modèle IA de votre assistant',
				sous: 'Le cerveau qui le fait réfléchir.',
				fond: 'from-emerald-200/70 via-green-100/50 to-lime-100/60 dark:from-emerald-900/30 dark:via-green-900/20 dark:to-lime-900/20',
				halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
				halo2: 'bg-lime-300/30 dark:bg-lime-500/10'
			}
		},
		{
			cle: 'messagerie',
			label: 'Messagerie',
			desc: 'Reliez vos canaux — WhatsApp, Telegram, e-mail — pour lui parler là où vous êtes déjà.',
			banniere: {
				debut: 'Parlez à votre assistant depuis',
				fort: 'WhatsApp, Telegram, e-mail et plus',
				sous: 'Retrouvez-le là où vous échangez déjà.',
				fond: 'from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20',
				halo1: 'bg-orange-300/40 dark:bg-orange-500/20',
				halo2: 'bg-amber-300/30 dark:bg-amber-500/10'
			}
		},
		{
			cle: 'integrations',
			label: 'Intégrations',
			desc: 'Connectez vos applications pour qu’il agisse directement à l’intérieur.',
			banniere: {
				debut: 'Connectez votre assistant à vos',
				fort: 'e-mails, agendas, fichiers et bien plus',
				sous: 'Il agit dans vos applications, à votre place.',
				fond: 'from-sky-200/70 via-sky-100/50 to-emerald-100/60 dark:from-sky-900/30 dark:via-slate-900/20 dark:to-emerald-900/20',
				halo1: 'bg-indigo-300/40 dark:bg-indigo-500/20',
				halo2: 'bg-sky-300/30 dark:bg-sky-500/10'
			}
		},
		{
			cle: 'mcp',
			label: 'MCP',
			desc: 'Branchez des serveurs spécialisés pour l’étendre à de nouvelles sources et de nouveaux outils.',
			logo: mcpLogo,
			banniere: {
				debut: 'Étendez votre assistant avec des',
				fort: 'connecteurs spécialisés (MCP)',
				sous: 'Pour brancher vos sources et outils sur mesure.',
				fond: 'from-slate-200/70 via-gray-100/50 to-zinc-100/60 dark:from-slate-800/40 dark:via-gray-900/20 dark:to-zinc-900/20',
				halo1: 'bg-slate-300/40 dark:bg-slate-500/20',
				halo2: 'bg-zinc-300/30 dark:bg-zinc-500/10'
			}
		},
		{
			cle: 'recherche',
			label: 'Recherche & web',
			desc: 'Donnez-lui la recherche et la lecture du web.',
			banniere: {
				debut: 'Donnez à votre assistant la',
				fort: 'recherche et la lecture du web',
				sous: 'Tous les fournisseurs réunis, sans rien chercher.',
				fond: 'from-sky-200/70 via-cyan-100/50 to-blue-100/60 dark:from-sky-900/30 dark:via-cyan-900/20 dark:to-blue-900/20',
				halo1: 'bg-sky-400/30 dark:bg-sky-500/20',
				halo2: 'bg-cyan-300/30 dark:bg-cyan-500/10'
			}
		},
		{
			cle: 'outils',
			label: 'Outils',
			desc: 'Ses capacités natives. Activez seulement ce dont vous avez besoin.',
			banniere: {
				debut: 'Donnez des super-pouvoirs à votre assistant :',
				fort: 'recherche web, images, mémoire et plus',
				sous: 'Activez seulement ce dont vous avez besoin.',
				fond: 'from-violet-200/70 via-indigo-100/50 to-purple-100/60 dark:from-violet-900/30 dark:via-indigo-900/20 dark:to-purple-900/20',
				halo1: 'bg-violet-300/40 dark:bg-violet-500/20',
				halo2: 'bg-indigo-300/30 dark:bg-indigo-500/10'
			}
		},
		{
			cle: 'gardefous',
			label: 'Garde-fous',
			desc: 'Le cadre dans lequel il a le droit d’agir — et ce qu’il ne fera jamais seul.',
			banniere: {
				debut: 'Ce que votre assistant',
				fort: 'ne fera jamais sans votre accord',
				sous: 'Le cadre qui vous protège des mauvaises surprises.',
				fond: 'from-rose-200/70 via-pink-100/50 to-orange-100/60 dark:from-rose-900/30 dark:via-pink-900/20 dark:to-orange-900/20',
				halo1: 'bg-rose-300/40 dark:bg-rose-500/20',
				halo2: 'bg-orange-300/30 dark:bg-orange-500/10'
			}
		},
		{
			cle: 'competences',
			label: 'Compétences',
			desc: 'Le détail de ses compétences. Réservé aux réglages avancés.',
			banniere: {
				debut: 'Le détail des',
				fort: 'compétences de votre assistant',
				sous: 'Réservé aux réglages avancés.',
				fond: 'from-teal-200/70 via-cyan-100/50 to-emerald-100/60 dark:from-teal-900/30 dark:via-cyan-900/20 dark:to-emerald-900/20',
				halo1: 'bg-teal-300/40 dark:bg-teal-500/20',
				halo2: 'bg-cyan-300/30 dark:bg-cyan-500/10'
			}
		}
	] as const;

	type Cle = (typeof ONGLETS)[number]['cle'];

	let ongletActif: Cle = 'modeles';

	/**
	 * Mode Expert (porte de la V1).
	 *
	 * « Competences » est du reglage technique : elles sont actives par defaut,
	 * il n'y a rien a y faire au quotidien. La montrer en permanence, c'est un
	 * onglet de charge mentale pour un dirigeant non technique.
	 *
	 * « Garde-fous » reste visible en permanence, contrairement a ce qui etait
	 * prevu au depart : c'est un argument de confiance, pas un reglage a cacher.
	 *
	 * La bascule ne change QUE la visibilite : rien n'est desactive.
	 */
	const ONGLETS_EXPERTS: Cle[] = ['competences'];
	$: ongletsVisibles = $expertMode
		? [...ONGLETS]
		: ONGLETS.filter((o) => !ONGLETS_EXPERTS.includes(o.cle));

	// Reglages avances coupes alors qu'on est sur un onglet expert : retour au premier.
	$: if (!$expertMode && ONGLETS_EXPERTS.includes(ongletActif)) ongletActif = 'modeles';

	$: sectionActive = ONGLETS.find((o) => o.cle === ongletActif) ?? ONGLETS[0];
	$: indexActif = ongletsVisibles.findIndex((o) => o.cle === ongletActif);

	/** Lien profond : ?tab=… ouvre directement le bon onglet. Cles de la V1 conservees. */
	const TAB_PAR_CLE: Record<string, Cle> = {
		providers: 'modeles',
		models: 'modeles',
		modeles: 'modeles',
		messaging: 'messagerie',
		messagerie: 'messagerie',
		integrations: 'integrations',
		connectors: 'mcp',
		mcp: 'mcp',
		'web-search': 'recherche',
		recherche: 'recherche',
		tools: 'outils',
		outils: 'outils',
		guardrails: 'gardefous',
		gardefous: 'gardefous',
		skills: 'competences',
		competences: 'competences'
	};

	// --- Etat de la page --------------------------------------------------

	let etat: EtatMoteur | null = null;
	let chargementEtat = true;

	// --- Ouverture --------------------------------------------------------

	onMount(async () => {
		// Page reservee a l'administrateur, comme en V1.
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}

		const demande = $page.url.searchParams.get('tab');
		if (demande && TAB_PAR_CLE[demande]) {
			const cible = TAB_PAR_CLE[demande];
			if (ONGLETS_EXPERTS.includes(cible)) expertMode.set(true);
			ongletActif = cible;
		}

		try {
			etat = await getEtatMoteur(localStorage.token);
		} catch (err) {
			etat = { joignable: false, detail: `${err}` };
		} finally {
			chargementEtat = false;
		}
		prefetchTools(localStorage.token);
	});
</script>

<svelte:head>
	<title>Moteur · LunarIA</title>
</svelte:head>

<div
	class="flex h-dvh max-h-[100dvh] w-full max-w-full flex-col transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''}"
>
	<nav class="flex shrink-0 items-center px-3 pb-1 pt-2">
		{#if $mobile || !$showSidebar}
			<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
				<button
					class="flex cursor-pointer rounded-lg p-1.5 transition hover:bg-gray-100 dark:hover:bg-gray-850"
					on:click={() => showSidebar.set(!$showSidebar)}
					aria-label="Basculer la barre latérale"
				>
					<MenuLines />
				</button>
			</div>
		{/if}
	</nav>

	<div class="flex-1 overflow-y-auto">
		<div class="mx-auto w-full max-w-7xl px-4 pb-10 pt-2 sm:px-6">
			<PageHeader
				eyebrow="Moteur"
				title="Ce que votre assistant sait faire"
				description={sectionActive.desc}
			>
				<!-- Interrupteur « Réglages avancés » (ex-Mode Expert, porté de la V1) :
				     dévoile le technique. Discret, avec infobulle, pour ne pas perdre
				     un lecteur non technique. -->
				<svelte:fragment slot="actions">
					<Tooltip
						content="Affiche les options techniques (compétences détaillées). Inutile au quotidien — réservé aux réglages avancés."
						interactive={true}
					>
						<label
							class="flex flex-none cursor-pointer select-none items-center gap-2 text-xs text-gray-400 dark:text-gray-500"
						>
							Réglages avancés
							<Switch state={$expertMode} on:change={() => expertMode.set(!$expertMode)} />
						</label>
					</Tooltip>
				</svelte:fragment>
			</PageHeader>

			<div class="mt-5">
				<SegmentedTabs
					items={ongletsVisibles.map((o) => ({ label: o.label }))}
					activeIndex={indexActif}
					ariaLabel="Sections de la page Moteur"
					on:select={(e) => (ongletActif = ongletsVisibles[e.detail].cle)}
				/>
			</div>

			<!-- Banniere de l'onglet : la couleur sert de repere, on sait ou l'on
			     est avant d'avoir lu le libelle. -->
			<div
				class="hero-modern relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br ring-1 ring-inset ring-white/50 dark:ring-white/10 {sectionActive
					.banniere.fond}"
			>
				<div
					class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {sectionActive
						.banniere.halo1}"
				></div>
				<div
					class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {sectionActive
						.banniere.halo2}"
				></div>
				<div class="hero-mesh pointer-events-none absolute inset-0"></div>
				<div class="hero-grain pointer-events-none absolute inset-0"></div>
				{#if 'logo' in sectionActive && sectionActive.logo}
					<div
						class="pointer-events-none absolute left-6 top-1/2 hidden -translate-y-1/2 sm:left-10 sm:flex"
					>
						<div
							class="flex size-16 items-center justify-center rounded-2xl bg-white/90 p-3 shadow-sm backdrop-blur dark:bg-gray-900/80"
						>
							<img
								src={sectionActive.logo}
								alt={sectionActive.label}
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
						{sectionActive.banniere.debut}
						<span class="font-semibold text-gray-900 dark:text-white">
							{sectionActive.banniere.fort}
						</span>
					</div>
					<p class="text-sm text-gray-500 dark:text-gray-400">{sectionActive.banniere.sous}</p>
				</div>
			</div>

			<div class="mt-5">
				{#if ongletActif === 'modeles'}
					<ProviderList />
				{:else if ongletActif === 'gardefous'}
					<GardeFous />
				{:else if ongletActif === 'messagerie'}
					<GatewayList />
				{:else if ongletActif === 'mcp'}
					<McpList />
				{:else if ongletActif === 'integrations'}
					<IntegrationsList />
				{:else if ongletActif === 'recherche'}
					<WebSearchList />
				{:else if ongletActif === 'outils'}
					<ToolsetList />
				{:else if ongletActif === 'competences'}
					<SkillList />
				{/if}
			</div>
		</div>
	</div>
</div>
