<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		models,
		knowledge,
		tools
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SegmentedTabs from '$lib/components/common/SegmentedTabs.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	// Capacités natives (Tools/Skills) gérées par Hermes via la page Capacités (/connectors) —
	// on masque les surfaces natives d'OpenWebUI pour éviter le doublon (Hermes seul maître).
	// Rien n'est supprimé : la redirection ci-dessous renvoie tout accès direct vers Capacités.
	const HIDE_NATIVE_CAPABILITIES = true;

	// Page « Prompts » native (raccourcis /slash pour le chat) : reliquat power-user d'OpenWebUI.
	// Inutile pour le dirigeant non-tech — l'Atelier d'agents + le bouton « Clarifier ma demande » (✨)
	// couvrent déjà le besoin. On masque l'onglet et on redirige l'accès direct. Rien n'est supprimé.
	const HIDE_NATIVE_PROMPTS = true;

	// Page « Connaissances » déplacée sous Mémoire (Second Cerveau) : le savoir vit dans la Mémoire,
	// pas dans une surface Workspace séparée. On masque l'onglet ici et on redirige vers /memory/knowledge.
	// Les routes /memory/knowledge* réutilisent les mêmes composants (rien n'est dupliqué ni supprimé).
	const HIDE_NATIVE_KNOWLEDGE = true;

	// Onglets du Workspace désormais rendus dans l'en-tête du contenu (style Capacités : grand titre
	// « Espace de travail » + onglets soulignés). La barre d'onglets de la <nav> reste masquée.
	const HIDE_WORKSPACE_TABS = true;

	// Sous-titre du hub selon l'onglet actif (comme la page Capacités).
	$: workspacePath = $page.url.pathname;
	// Onglets de l'en-tête (mode lien) : actif déduit de l'URL.
	$: workspaceTabs = [
		{ label: $i18n.t('Agents'), href: '/workspace/agents' },
		{ label: $i18n.t('Tâches'), href: '/workspace/tasks' },
		{ label: $i18n.t('Automatisations'), href: '/workspace/automations' },
		{ label: $i18n.t('Compétences'), href: '/workspace/competences' }
	];
	$: workspaceActiveIndex = workspacePath.includes('/workspace/tasks')
		? 1
		: workspacePath.includes('/workspace/automations')
			? 2
			: workspacePath.includes('/workspace/competences')
				? 3
				: 0;
	// L'onglet « Tâches » (Kanban) a besoin d'une hauteur définie (board plein écran + scroll interne
	// des colonnes). Les autres onglets défilent normalement (l'en-tête scrolle avec le contenu).
	$: isWorkspaceBoard = workspacePath.includes('/workspace/tasks');
	// Bannière colorée du hub selon l'onglet actif (esprit Capacités) : explique à quoi sert l'onglet.
	$: workspaceBanner = workspacePath.includes('/workspace/tasks')
		? {
				strong: 'Le tableau de bord du travail',
				sub: 'Suivez d’un coup d’œil ce que vos agents font : à faire, en cours, terminé.',
				wrap: 'from-sky-200/70 via-sky-100/50 to-blue-100/60 dark:from-sky-900/30 dark:via-sky-900/20 dark:to-blue-900/20',
				halo1: 'bg-sky-400/30 dark:bg-sky-500/20',
				halo2: 'bg-blue-300/30 dark:bg-blue-500/10'
			}
		: workspacePath.includes('/workspace/automations')
			? {
					strong: 'Le pilote automatique',
					sub: 'Programmez des actions récurrentes que vos agents exécutent tout seuls, au bon moment.',
					wrap: 'from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20',
					halo1: 'bg-orange-300/40 dark:bg-orange-500/20',
					halo2: 'bg-amber-300/30 dark:bg-amber-500/10'
				}
			: workspacePath.includes('/workspace/competences')
				? {
						strong: 'La boîte à outils de vos agents',
						sub: 'Les savoir-faire que vos agents peuvent utiliser (emails, agenda, documents…). Activez ce dont ils ont besoin.',
						wrap: 'from-emerald-200/70 via-emerald-100/50 to-teal-100/60 dark:from-emerald-900/30 dark:via-emerald-900/20 dark:to-teal-900/20',
						halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
						halo2: 'bg-teal-300/30 dark:bg-teal-500/10'
					}
				: {
						strong: 'Vos collègues numériques',
						sub: 'Créez et activez des agents IA spécialisés — chacun avec sa mission — qui travaillent pour vous.',
						wrap: 'from-violet-200/70 via-violet-100/50 to-indigo-100/60 dark:from-violet-900/30 dark:via-violet-900/20 dark:to-indigo-900/20',
						halo1: 'bg-violet-400/30 dark:bg-violet-500/20',
						halo2: 'bg-indigo-300/30 dark:bg-indigo-500/10'
					};

	onMount(async () => {
		if (HIDE_NATIVE_KNOWLEDGE && $page.url.pathname.includes('/workspace/knowledge')) {
			goto('/memory/knowledge');
			return;
		}

		if (
			HIDE_NATIVE_CAPABILITIES &&
			($page.url.pathname.includes('/workspace/tools') ||
				$page.url.pathname.includes('/workspace/skills'))
		) {
			goto('/connectors');
			return;
		}

		if (HIDE_NATIVE_PROMPTS && $page.url.pathname.includes('/workspace/prompts')) {
			goto('/');
			return;
		}

		if ($user?.role !== 'admin') {
			// La page Agents (et son API /api/v1/agents) est admin-only : tout non-admin est redirigé.
			if ($page.url.pathname.includes('/workspace/agents')) {
				goto('/');
			} else if ($page.url.pathname.includes('/workspace/competences')) {
				// La page Compétences (réglage des savoir-faire) est admin-only, comme Agents.
				goto('/');
			} else if ($page.url.pathname.includes('/models') && !$user?.permissions?.workspace?.models) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/knowledge') &&
				!$user?.permissions?.workspace?.knowledge
			) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/prompts') &&
				!$user?.permissions?.workspace?.prompts
			) {
				goto('/');
			} else if ($page.url.pathname.includes('/tools') && !$user?.permissions?.workspace?.tools) {
				goto('/');
			} else if ($page.url.pathname.includes('/skills') && !$user?.permissions?.workspace?.skills) {
				goto('/');
			}
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav
			class="relative z-10 px-2.5 {!HIDE_WORKSPACE_TABS || $mobile ? 'pt-1.5' : ''} backdrop-blur-xl drag-region select-none"
		>
			<div class=" flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				{#if !HIDE_WORKSPACE_TABS}
				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<!-- Onglet « Modèles » transformé en « Agents » (cerveau dans Hermes, un agent = un profil).
						     L'ancienne route /workspace/models reste accessible mais n'est plus liée ici.
						     Réservé aux admins : l'API /api/v1/agents est admin-only. -->
						{#if $user?.role === 'admin'}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/agents') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/agents')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/agents">{$i18n.t('Agents')}</a
							>
						{/if}

						{#if $user?.role === 'admin'}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/tasks') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/tasks')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/tasks">{$i18n.t('Tâches')}</a
							>
						{/if}

						{#if $user?.role === 'admin'}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/automations') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/automations')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/automations">{$i18n.t('Automatisations')}</a
							>
						{/if}

						{#if !HIDE_NATIVE_KNOWLEDGE && ($user?.role === 'admin' || $user?.permissions?.workspace?.knowledge)}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/knowledge') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/knowledge')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/knowledge"
							>
								{$i18n.t('Knowledge')}
							</a>
						{/if}

						{#if !HIDE_NATIVE_PROMPTS && ($user?.role === 'admin' || $user?.permissions?.workspace?.prompts)}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/prompts') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/prompts')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/prompts">{$i18n.t('Prompts')}</a
							>
						{/if}

						{#if !HIDE_NATIVE_CAPABILITIES && ($user?.role === 'admin' || $user?.permissions?.workspace?.skills)}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/skills') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/skills')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/skills"
							>
								{$i18n.t('Skills')}
							</a>
						{/if}

						{#if !HIDE_NATIVE_CAPABILITIES && ($user?.role === 'admin' || $user?.permissions?.workspace?.tools)}
							<a
								draggable="false"
								aria-current={$page.url.pathname.includes('/workspace/tools') ? 'page' : null}
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/tools')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
								href="/workspace/tools"
							>
								{$i18n.t('Tools')}
							</a>
						{/if}
					</div>
				</div>
				{/if}

				<!-- <div class="flex items-center text-xl font-medium">{$i18n.t('Workspace')}</div> -->
			</div>
		</nav>

		<div
			class="relative z-10 px-3 md:px-[18px] flex-1 max-h-full {isWorkspaceBoard
				? 'flex flex-col overflow-hidden'
				: 'pb-1 overflow-y-auto'}"
			id="workspace-container"
		>
			{#if $user?.role === 'admin'}
				<!-- En-tête du hub « Espace de travail » (style Capacités) : titre + onglets + bannière.
				     Onglets contenu = défile avec le contenu ; onglet Tâches = en-tête figé + board plein écran. -->
				<div class="{isWorkspaceBoard ? 'flex-none ' : ''}w-full max-w-7xl mx-auto px-4 pt-4 sm:pt-6">
					<PageHeader
						eyebrow={$i18n.t('Espace de travail')}
						title={$i18n.t('Vos collègues numériques')}
						description={$i18n.t(
							'Agents, tâches, automatisations et compétences — tout ce que votre assistant sait faire, au même endroit.'
						)}
					/>
					<div class="mt-4">
						<SegmentedTabs items={workspaceTabs} activeIndex={workspaceActiveIndex} />
					</div>

					<!-- Bannière colorée par onglet (même taille/style que Capacités : haute + centrée + halos) -->
					<div
						class="relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 {workspaceBanner.wrap}"
					>
						<div
							class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {workspaceBanner.halo1}"
						></div>
						<div
							class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {workspaceBanner.halo2}"
						></div>
						<!-- Matière moderne (mesh + grain), color-agnostique. -->
						<div class="hero-mesh pointer-events-none absolute inset-0"></div>
						<div class="hero-grain pointer-events-none absolute inset-0"></div>
						<div
							class="relative flex flex-col items-center justify-center gap-2 px-6 py-8 text-center"
						>
							<div
								class="rounded-full bg-white/90 px-5 py-2 text-sm text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
							>
								<span class="font-semibold text-gray-900 dark:text-white"
									>{$i18n.t(workspaceBanner.strong)}</span
								>
							</div>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{$i18n.t(workspaceBanner.sub)}
							</p>
						</div>
					</div>
				</div>
			{/if}
			<div class={isWorkspaceBoard ? 'flex-1 min-h-0 overflow-y-auto pb-1' : 'contents'}>
				<slot />
			</div>
		</div>
	</div>
{/if}
