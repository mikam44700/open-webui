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

	// Onglets Mémoire (mode lien) : actif déduit de l'URL. Métaphore « les tiroirs de la mémoire
	// de mon assistant » — le coffre + les 3 réglages du cerveau (SOUL.md/USER.md/MEMORY.md). Cf. specs/017.
	$: memoryTabs = [
		{ label: $i18n.t('Mes notes'), href: '/memory' },
		{ label: $i18n.t('Mon assistant'), href: '/memory/assistant' },
		{ label: $i18n.t('Mon profil'), href: '/memory/profil' },
		{ label: $i18n.t("Ce qu'il a retenu"), href: '/memory/souvenirs' },
		{ label: $i18n.t('Connaissances'), href: '/memory/knowledge' }
	];
	$: memoryActiveIndex = (() => {
		const p = $page.url.pathname;
		if (p.includes('/memory/assistant')) return 1;
		if (p.includes('/memory/profil')) return 2;
		if (p.includes('/memory/souvenirs')) return 3;
		if (p.includes('/memory/knowledge')) return 4;
		return 0;
	})();

	// Explication sous le titre, spécifique à l'onglet actif (chaque « tiroir » a son rôle).
	$: memoryDescription = (() => {
		const p = $page.url.pathname;
		if (p.includes('/memory/assistant'))
			return $i18n.t(
				"Le caractère de votre assistant : son rôle, son ton, ses règles. Il en tiendra compte dans toutes vos conversations."
			);
		if (p.includes('/memory/profil'))
			return $i18n.t(
				"Qui vous êtes, pour que votre assistant vous connaisse et personnalise ses réponses sans que vous ayez à le répéter."
			);
		if (p.includes('/memory/souvenirs'))
			return $i18n.t(
				"Les faits que votre assistant mémorise au fil de vos échanges. Ce tiroir se remplit surtout tout seul — vous gardez la main."
			);
		if (p.includes('/memory/knowledge'))
			return $i18n.t(
				"Les bases de connaissances que votre assistant peut consulter pour vous répondre."
			);
		return $i18n.t('Tout ce que votre assistant retient pour vous, dans un coffre qui vous appartient.');
	})();

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
					description={memoryDescription}
				/>
				<div class="mt-4">
					<SegmentedTabs items={memoryTabs} activeIndex={memoryActiveIndex} />
				</div>
			</div>
			<slot />
		</div>
	</div>
{/if}
