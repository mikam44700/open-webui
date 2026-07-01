<script>
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { mobile, showArchivedChats, showSidebar, user } from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SegmentedTabs from '$lib/components/common/SegmentedTabs.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Onglets Mémoire (mode lien) : actif déduit de l'URL.
	$: memoryTabs = [
		{ label: $i18n.t('Mémoire'), href: '/memory' },
		{ label: $i18n.t('Knowledge'), href: '/memory/knowledge' }
	];
	$: memoryActiveIndex = $page.url.pathname.includes('/memory/knowledge') ? 1 : 0;

	let loaded = false;

	onMount(async () => {
		// Section admin-only (cohérent avec les autres surfaces Agent OS). Cf. specs/005-memoire.
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
		<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
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

				<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
					<div></div>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="w-[240px]"
								role={$user?.role}
								help={true}
								on:show={(e) => {
									if (e.detail === 'archived-chat') {
										showArchivedChats.set(true);
									}
								}}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="Menu utilisateur"
								>
									<div class=" self-center">
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-6 object-cover rounded-full"
											alt="Profil utilisateur"
											draggable="false"
										/>
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container px-3 md:px-[18px]">
			<!-- En-tête « Mémoire » (style Capacités / Espace de travail) : titre + phrase + onglets soulignés. -->
			<div class="pt-3 sm:pt-4">
				<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-white">
					{$i18n.t('Mémoire')}
				</h1>
				<p class="mt-1.5 max-w-2xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">
					{$i18n.t('Le second cerveau de votre entreprise : tout ce que votre assistant retient pour vous.')}
				</p>
				<div class="mt-4">
					<SegmentedTabs items={memoryTabs} activeIndex={memoryActiveIndex} />
				</div>
			</div>
			<slot />
		</div>
	</div>
{/if}
