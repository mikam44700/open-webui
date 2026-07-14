<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { CALENDAR_SOURCE_LOGO } from '$lib/utils/integrationLogos';
	import calendarHero from '$lib/assets/calendar/calendar-hero.jpg';

	const i18n = getContext('i18n');

	// Sources réellement branchées à la page Calendrier (mêmes id que le bridge).
	// Chaque carte est cliquable : elle mène à l'onglet Intégrations pour connecter.
	// Seuls les vrais calendriers (lecture + écriture) : Google et Outlook couvrent
	// l'écrasante majorité des entreprises françaises. Calendly (guichet de réservation,
	// lecture seule) est volontairement écarté de la page Calendrier.
	const sources = [
		{ id: 'google', label: 'Google Agenda', sub: 'Google Workspace' },
		{ id: 'outlook', label: 'Outlook Calendar', sub: 'Microsoft 365' }
	];

	const openIntegrations = () => goto('/connectors?tab=integrations');
</script>

<div class="w-full py-6">
	<!-- Bloc dégradé « arc-en-ciel » pastel qui entoure tout l'appel à connexion (pleine largeur) -->
	<div
		class="relative w-full rounded-[28px] overflow-hidden px-6 py-14 text-center
			border border-white/70 dark:border-white/5 shadow-sm
			bg-gradient-to-br from-rose-100 via-violet-100 to-sky-100
			dark:from-rose-950/30 dark:via-violet-950/25 dark:to-sky-950/30"
	>
		<!-- Halos doux pour la profondeur -->
		<div class="pointer-events-none absolute -top-16 -left-10 w-56 h-56 rounded-full blur-3xl bg-fuchsia-200/40 dark:bg-fuchsia-500/10"></div>
		<div class="pointer-events-none absolute -bottom-16 -right-10 w-56 h-56 rounded-full blur-3xl bg-sky-200/40 dark:bg-sky-500/10"></div>

		<div class="relative flex flex-col items-center">
			<!-- Image calendrier (asset local) dans une tuile blanche arrondie (bords doux) -->
			<div class="w-[84px] h-[84px] rounded-[22px] overflow-hidden bg-white shadow-lg ring-1 ring-black/5">
				<img src={calendarHero} alt={$i18n.t('Calendrier')} class="w-full h-full object-cover scale-[1.06]" />
			</div>

			<h2 class="mt-5 text-2xl font-semibold text-gray-900 dark:text-gray-50">
				{$i18n.t('Connectez votre agenda')}
			</h2>
			<p class="mt-1.5 text-sm text-gray-600 dark:text-gray-300 max-w-md">
				{$i18n.t('Choisissez le calendrier que vous utilisez — LunarIA s’occupe du reste.')}
			</p>

			<!-- Cartes cliquables : un logo par calendrier -->
			<div class="mt-7 grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-xl mx-auto">
				{#each sources as s (s.id)}
					<button
						type="button"
						on:click={openIntegrations}
						class="group flex flex-col items-center gap-3 p-5 rounded-2xl bg-white/90 dark:bg-gray-900/70 backdrop-blur-sm
							border border-white/80 dark:border-gray-800 shadow-sm
							hover:shadow-lg hover:-translate-y-0.5 hover:bg-white dark:hover:bg-gray-900
							transition-all duration-200"
					>
						<div class="size-12 rounded-xl bg-white dark:bg-gray-850 shadow-sm flex items-center justify-center p-2">
							<img src={CALENDAR_SOURCE_LOGO[s.id]} alt={s.label} class="max-w-full max-h-full object-contain" />
						</div>
						<div class="flex flex-col items-center gap-0.5">
							<span class="text-sm font-medium text-gray-900 dark:text-gray-100">{s.label}</span>
							<span class="text-[11px] text-gray-400">{s.sub}</span>
						</div>
						<span class="text-xs font-medium text-gray-500 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors inline-flex items-center gap-1">
							{$i18n.t('Connecter')}
							<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="group-hover:translate-x-0.5 transition-transform">
								<path d="M5 12h14M13 6l6 6-6 6" />
							</svg>
						</span>
					</button>
				{/each}
			</div>

			<p class="mt-6 text-[11px] text-gray-500 dark:text-gray-400">
				{$i18n.t('Plusieurs calendriers ? Connectez-les tous, un sélecteur apparaîtra ici.')}
			</p>
		</div>
	</div>
</div>
