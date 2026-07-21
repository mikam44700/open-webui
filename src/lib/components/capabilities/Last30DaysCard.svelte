<script lang="ts">
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import ConnectorAboutModal from '$lib/components/connectors/ConnectorAboutModal.svelte';

	let aboutOpen = false;
	const actions = [
		'Repère les sujets et tendances qui ont émergé pendant les 30 derniers jours.',
		'Explore les conversations publiques sur Reddit et Hacker News.',
		'Analyse les vidéos YouTube et leurs transcriptions disponibles.',
		'Croise les signaux récents avant de produire une synthèse sourcée.',
		'Distingue les faits observés des tendances et des interprétations.'
	];
	const tags = ['30 derniers jours', 'Reddit', 'YouTube', 'Hacker News'];
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 h-full card-lift hover:border-gray-200 dark:hover:border-gray-700">
	<div class="flex items-start gap-2.5">
		<div class="size-12 flex-none rounded-xl bg-orange-500/10 text-orange-600 dark:text-orange-400 flex items-center justify-center" aria-hidden="true">
			<svg viewBox="0 0 24 24" fill="none" class="size-7" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16M7 3v4m10-4v4M5 11h4m2 0h4m2 0h2M5 15h4m2 0h4m2 0h2M5 19h4m2 0h4" /><rect x="3" y="5" width="18" height="16" rx="2" /></svg>
		</div>
		<div class="flex-1 min-w-0 flex flex-col gap-1">
			<div class="flex items-center gap-1.5"><span class="text-sm font-medium leading-tight">Tendances des 30 derniers jours</span><ActiveBadge /></div>
			<div class="text-xs text-gray-500 leading-snug">Ce qui bouge maintenant sur votre marché.</div>
		</div>
		<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium text-green-700 bg-green-500/10 dark:text-green-400">Installé</span>
	</div>
	<div class="flex flex-wrap gap-1">{#each tags as tag}<span class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300">{tag}</span>{/each}</div>
	<button type="button" class="self-start text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline" on:click={() => (aboutOpen = true)}>Voir ce que ça fait ›</button>
	<div class="mt-auto text-[11px] text-gray-500 dark:text-gray-400">Géré par LunarIA · aucune configuration</div>
</div>

<ConnectorAboutModal bind:open={aboutOpen} name="Tendances des 30 derniers jours" desc="Last30Days aide Sacha à comprendre les conversations et signaux récents avant de les croiser avec les autres sources de LunarIA." {actions} {tags} />
