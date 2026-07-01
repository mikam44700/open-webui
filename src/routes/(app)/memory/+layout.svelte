<script>
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { mobile, showSidebar, user } from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SegmentedTabs from '$lib/components/common/SegmentedTabs.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
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
			</div>
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container px-3 md:px-[18px]">
			<!-- En-tête « Mémoire » (style Capacités / Espace de travail) : titre + phrase + onglets soulignés. -->
			<div class="pt-3 sm:pt-4">
				<PageHeader
					eyebrow={$i18n.t('Mémoire')}
					title={$i18n.t('Le second cerveau de votre entreprise')}
					description={$i18n.t(
						'Tout ce que votre assistant retient pour vous, dans un coffre qui vous appartient.'
					)}
				/>
				<div class="mt-4">
					<SegmentedTabs items={memoryTabs} activeIndex={memoryActiveIndex} />
				</div>
			</div>
			<slot />
		</div>
	</div>
{/if}
