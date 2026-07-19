<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, user, mobile } from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	// Permissions des 5 sections open-webui d'origine (regroupées dans la Bibliothèque).
	$: perms = $user?.permissions?.workspace ?? {};
	$: isAdmin = $user?.role === 'admin';
	$: canAgents = isAdmin || !!perms.models;
	$: canLibrary =
		isAdmin || !!(perms.models || perms.knowledge || perms.prompts || perms.skills || perms.tools);

	// Onglets V1 « Vos collègues numériques ». La Bibliothèque reste active quand on
	// navigue dans une de ses 5 sections (routes historiques conservées).
	const LIBRARY_PATHS = [
		'/workspace/library',
		'/workspace/models',
		'/workspace/knowledge',
		'/workspace/prompts',
		'/workspace/skills',
		'/workspace/tools',
		'/workspace/functions'
	];
	$: onglets = [
		...(canAgents ? [{ label: 'Agents', href: '/workspace/agents', paths: ['/workspace/agents'] }] : []),
		{ label: 'Tâches', href: '/workspace/tasks', paths: ['/workspace/tasks'] },
		{
			label: 'Automatisations',
			href: '/workspace/automations',
			paths: ['/workspace/automations']
		},
		...(canLibrary ? [{ label: 'Bibliothèque', href: '/workspace/library', paths: LIBRARY_PATHS }] : [])
	];
	$: estActif = (paths: string[]) => paths.some((p) => $page.url.pathname.startsWith(p));

	onMount(async () => {
		if ($user?.role !== 'admin') {
			const pathname = $page.url.pathname;
			const workspacePerms = $user?.permissions?.workspace ?? {};
			const anyPerm = !!(
				workspacePerms.models ||
				workspacePerms.knowledge ||
				workspacePerms.prompts ||
				workspacePerms.skills ||
				workspacePerms.tools
			);

			if (
				(pathname.includes('/models') || pathname.includes('/agents')) &&
				!workspacePerms.models
			) {
				goto('/');
			} else if (pathname.includes('/knowledge') && !workspacePerms.knowledge) {
				goto('/');
			} else if (pathname.includes('/prompts') && !workspacePerms.prompts) {
				goto('/');
			} else if (pathname.includes('/tools') && !workspacePerms.tools) {
				goto('/');
			} else if (pathname.includes('/skills') && !workspacePerms.skills) {
				goto('/');
			} else if (pathname.includes('/library') && !anyPerm) {
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
		<!-- En-tête V1 : « Vos collègues numériques » + onglets pilule (même recette que Capacités) -->
		<div class="px-6 md:px-10 pt-4 shrink-0 drag-region select-none">
			<div class="flex items-start gap-1">
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center pt-1">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class="cursor-pointer p-1.5 flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<Sidebar />
						</button>
					</Tooltip>
				</div>

				<div>
					<div
						class="text-xs font-semibold tracking-widest text-gray-500 dark:text-gray-400 uppercase"
					>
						Espace de travail
					</div>
					<h1 class="text-2xl font-medium tracking-tight text-gray-900 dark:text-gray-50 mt-1">
						Vos collègues numériques
					</h1>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						Créez et pilotez des agents IA spécialisés — chacun avec sa mission, ses outils et sa
						personnalité.
					</p>
				</div>
			</div>

			<!-- Barre d'onglets -->
			<div
				class="flex flex-wrap items-center gap-1 mt-4 mb-2 p-1 rounded-full border border-gray-200/60 dark:border-white/6 bg-gray-50 dark:bg-[#161616] w-fit"
				role="tablist"
			>
				{#each onglets as onglet}
					<a
						draggable="false"
						role="tab"
						aria-selected={estActif(onglet.paths)}
						aria-current={estActif(onglet.paths) ? 'page' : null}
						class="px-4 py-1.5 rounded-full text-sm transition select-none {estActif(onglet.paths)
							? 'bg-white dark:bg-[#0a0a0a] text-gray-900 dark:text-gray-50 ring-1 ring-gray-200/80 dark:ring-white/10 font-medium'
							: 'text-gray-500 dark:text-[#c2c2c2] hover:text-gray-700 dark:hover:text-white'}"
						href={onglet.href}
					>
						{onglet.label}
					</a>
				{/each}
			</div>
		</div>

		<div
			class="  pb-1 px-6 md:px-10 pt-2 flex-1 max-h-full overflow-y-auto"
			id="workspace-container"
		>
			<slot />
		</div>
	</div>
{/if}
