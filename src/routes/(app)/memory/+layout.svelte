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

	// Bannière colorée par onglet (même style que Espace de travail / Capacités) : une couleur
	// par « tiroir » de la mémoire (pastille blanche + sous-titre + halos flous).
	$: memoryBanner = (() => {
		const p = $page.url.pathname;
		if (p.includes('/memory/assistant'))
			return {
				strong: 'Le caractère de votre assistant',
				sub: "Décrivez son rôle, son ton, ses règles — il en tiendra compte dans toutes vos conversations.",
				wrap: 'from-violet-200/70 via-violet-100/50 to-indigo-100/60 dark:from-violet-900/30 dark:via-violet-900/20 dark:to-indigo-900/20',
				halo1: 'bg-violet-400/30 dark:bg-violet-500/20',
				halo2: 'bg-indigo-300/30 dark:bg-indigo-500/10'
			};
		if (p.includes('/memory/profil'))
			return {
				strong: 'Qui vous êtes',
				sub: 'Décrivez qui vous êtes pour que votre assistant vous connaisse et personnalise ses réponses.',
				wrap: 'from-rose-200/70 via-rose-100/50 to-orange-100/60 dark:from-rose-900/30 dark:via-rose-900/20 dark:to-orange-900/20',
				halo1: 'bg-rose-400/30 dark:bg-rose-500/20',
				halo2: 'bg-orange-300/30 dark:bg-orange-500/10'
			};
		if (p.includes('/memory/souvenirs'))
			return {
				strong: "Ce qu'il a retenu",
				sub: 'Les faits que votre assistant mémorise au fil de vos échanges. Ce tiroir se remplit surtout tout seul.',
				wrap: 'from-amber-200/70 via-amber-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-amber-900/20 dark:to-yellow-900/20',
				halo1: 'bg-amber-400/30 dark:bg-amber-500/20',
				halo2: 'bg-yellow-300/30 dark:bg-yellow-500/10'
			};
		if (p.includes('/memory/knowledge'))
			return {
				strong: 'Vos bases de connaissances',
				sub: 'Les documents que votre assistant peut consulter pour vous répondre.',
				wrap: 'from-emerald-200/70 via-emerald-100/50 to-teal-100/60 dark:from-emerald-900/30 dark:via-emerald-900/20 dark:to-teal-900/20',
				halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
				halo2: 'bg-teal-300/30 dark:bg-teal-500/10'
			};
		return {
			strong: 'Votre coffre de notes',
			// Le prénom se lit dans la phrase (plutôt qu'en étiquette posée sur l'image) : « votre
			// assistant » présente Adam à qui découvre la page — l'image juste à côté fait le lien.
			sub: 'Tout ce que votre assistant Adam retient pour vous, dans un coffre qui vous appartient.',
			wrap: 'from-sky-200/70 via-sky-100/50 to-blue-100/60 dark:from-sky-900/30 dark:via-sky-900/20 dark:to-blue-900/20',
			halo1: 'bg-sky-400/30 dark:bg-sky-500/20',
			halo2: 'bg-blue-300/30 dark:bg-blue-500/10',
			// Adam incarne le coffre : plan complet (fond transparent) posé à même la bannière — on le
			// veut avec le cristal entre les mains, sa signature, pas un simple visage.
			// Seul cet onglet a un gardien — les autres tiroirs n'en affichent pas.
			avatar: '/assets/agents/adam.webp'
		};
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
					description={$i18n.t(
						'La mémoire de votre assistant, rangée en tiroirs clairs — et un coffre de notes qui vous appartient.'
					)}
				/>
				<div class="mt-4">
					<SegmentedTabs items={memoryTabs} activeIndex={memoryActiveIndex} />
					</div>

					<!-- Bannière colorée par onglet (style Espace de travail / Capacités : pastille + halos flous) -->
					<div
						class="relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 {memoryBanner.wrap}"
					>
						<div
							class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {memoryBanner.halo1}"
						></div>
						<div
							class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {memoryBanner.halo2}"
						></div>
						<!-- Matière moderne (mesh + grain), color-agnostique. -->
						<div class="hero-mesh pointer-events-none absolute inset-0"></div>
						<div class="hero-grain pointer-events-none absolute inset-0"></div>
						{#if memoryBanner.avatar}
							<!-- HORS DU FLUX : la bannière garde EXACTEMENT la hauteur des autres onglets. Adam est
							     rogné par son overflow-hidden (cadrage tête → mains + cristal), il ne l'étire pas. -->
							<img
								src={memoryBanner.avatar}
								alt="Adam"
								class="pointer-events-none absolute left-6 top-0 h-48 w-auto object-contain drop-shadow-md"
							/>
						{/if}
						<div class="relative flex flex-col items-center justify-center gap-2 px-6 py-8 text-center">
							<div
								class="rounded-full bg-white/90 px-5 py-2 text-sm text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
							>
								<span class="font-semibold text-gray-900 dark:text-white">{$i18n.t(memoryBanner.strong)}</span>
							</div>
							<p class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t(memoryBanner.sub)}</p>
						</div>
					</div>
			</div>
			<slot />
		</div>
	</div>
{/if}
