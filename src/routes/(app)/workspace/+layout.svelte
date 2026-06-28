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

	// Barre d'onglets du Workspace masquée : il ne reste que « Agents » (Knowledge/Prompts/Tools/Skills
	// déjà masqués), redondant avec le titre de la page Agents. On garde le bouton sidebar (mobile).
	const HIDE_WORKSPACE_TABS = true;

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
			class="   px-2.5 {!HIDE_WORKSPACE_TABS || $mobile ? 'pt-1.5' : ''} backdrop-blur-xl drag-region select-none"
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
			class="  pb-1 px-3 md:px-[18px] flex-1 max-h-full overflow-y-auto"
			id="workspace-container"
		>
			<slot />
		</div>
	</div>
{/if}
