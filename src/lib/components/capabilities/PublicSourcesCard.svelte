<script lang="ts">
	import { onMount } from 'svelte';
	import { getPublicSourcesStatus } from '$lib/apis/capabilities';
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConnectorAboutModal from '$lib/components/connectors/ConnectorAboutModal.svelte';
	let status: any = null;
	let aboutOpen = false;
	const actions = [
		'Recherche et lit les informations publiques du web.',
		'Analyse les informations disponibles sur les vidéos YouTube.',
		'Suit les actualités publiées dans les flux RSS.',
		'Recherche les projets et évolutions techniques publics sur GitHub.',
		'Signale clairement une source inaccessible au lieu d’inventer.'
	];
	const tags = ['Web', 'YouTube', 'RSS', 'GitHub'];
	onMount(async () => {
		status = await getPublicSourcesStatus(localStorage.token).catch(() => ({ active: false }));
	});
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 h-full card-lift hover:border-gray-200 dark:hover:border-gray-700">
	<div class="flex flex-wrap items-start gap-2.5 min-w-0">
		<div class="size-12 flex-none rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700 bg-[#050818] flex items-center justify-center">
			<img src="/assets/logos/lunaria/agent-reach.png" alt="Agent Reach" class="w-full h-full object-cover" draggable="false" />
		</div>
		<div class="flex-1 min-w-[10rem] flex flex-col gap-1">
			<div class="flex flex-wrap items-center gap-1.5 min-w-0"><span class="text-sm font-medium leading-tight break-normal">Recherche web et veille multicanale</span>{#if status?.active}<span class="flex-none"><ActiveBadge /></span>{/if}</div>
			<div class="text-xs text-gray-500 leading-snug">Les yeux de Sacha et Lea sur les sources publiques.</div>
		</div>
		{#if status === null}<Spinner className="size-4" />{:else if status.active}<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium text-green-700 bg-green-500/10 dark:text-green-400">Installé</span>{:else}<span class="flex-none text-[11px] px-2 py-0.5 rounded-full text-amber-700 bg-amber-500/10 dark:text-amber-400">Démarrage…</span>{/if}
	</div>
	<div class="flex flex-wrap gap-1">{#each tags as tag}<span class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300">{tag}</span>{/each}</div>
	<button type="button" class="self-start text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline" on:click={() => (aboutOpen = true)}>Voir ce que ça fait ›</button>
	<div class="mt-auto text-[11px] text-gray-500 dark:text-gray-400">Géré par LunarIA · aucune configuration</div>
</div>

<ConnectorAboutModal bind:open={aboutOpen} name="Recherche web et veille multicanale" desc="Agent Reach sélectionne les bonnes sources en coulisses ; LunarIA les vérifie avant de vous les présenter." {actions} {tags} />
