<script lang="ts">
	// Page « Automatisations » d'Agent OS — pilotée par Hermes (feature 013).
	// Remplace la surface native OpenWebUI (conservée dans l'historique + composants natifs
	// intacts) : Hermes est désormais le seul maître des automatisations (cron natif).
	// Admin-only (l'API /api/v1/automations est admin-only).
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, showSidebar, mobile, user } from '$lib/stores';

	import AutomationsHermes from '$lib/components/automations/AutomationsHermes.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	let loaded = false;

	onMount(() => {
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Automatisations')} • {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex-1 max-h-full overflow-y-auto">
		{#if loaded}
			<div class="pb-1 px-3 md:px-[18px] pt-2 w-full">
				{#if $mobile}
					<div class="mb-2">
						<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
							<button
								id="sidebar-toggle-button"
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => showSidebar.set(!$showSidebar)}
							>
								<div class="self-center p-1.5"><SidebarIcon /></div>
							</button>
						</Tooltip>
					</div>
				{/if}
				<AutomationsHermes />
			</div>
		{:else}
			<div class="w-full h-full flex justify-center items-center"><Spinner className="size-5" /></div>
		{/if}
	</div>
</div>
