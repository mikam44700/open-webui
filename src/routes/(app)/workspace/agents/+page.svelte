<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getModelItems } from '$lib/apis/models';
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext('i18n');

	let agents = null;
	let total = null;

	onMount(async () => {
		const res = await getModelItems(
			localStorage.token,
			'',
			null,
			null,
			null,
			null,
			null
		).catch(() => null);

		agents = res?.items ?? [];
		total = res?.total ?? agents.length;
	});
</script>

<HeroBanner
	lead="Créez et activez des"
	strong="agents IA spécialisés"
	sub="Chacun avec sa mission, ses outils et sa personnalité."
	wrap="from-violet-200/70 via-indigo-100/50 to-purple-100/60 dark:from-violet-900/30 dark:via-indigo-900/20 dark:to-purple-900/20"
	halo1="bg-violet-300/40 dark:bg-violet-500/20"
	halo2="bg-indigo-300/30 dark:bg-indigo-500/10"
/>

{#if agents === null}
	<div class="flex justify-center py-16">
		<Spinner className="size-5" />
	</div>
{:else if agents.length === 0}
	<!-- État vide : premier agent à créer -->
	<div
		class="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-5 py-16 text-center"
	>
		<div class="font-medium text-gray-900 dark:text-gray-50">Aucun agent pour le moment</div>
		<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
			Créez votre premier collègue numérique : donnez-lui un nom, une mission et des outils.
		</div>
		<button
			class="mt-5 inline-flex items-center gap-2 rounded-full bg-gray-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
			on:click={() => goto('/workspace/models/create')}
		>
			<Plus className="size-4" />
			Créer mon premier agent
		</button>
	</div>
{:else}
	<div class="flex items-center justify-between mb-3">
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{total} agent{total > 1 ? 's' : ''}
		</div>
		<button
			class="inline-flex items-center gap-2 rounded-full bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
			on:click={() => goto('/workspace/models/create')}
		>
			<Plus className="size-4" />
			Nouvel agent
		</button>
	</div>

	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 pb-6">
		{#each agents as agent (agent.id)}
			<div
				class="flex flex-col rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900 p-5 transition hover:shadow-md {agent.is_active
					? ''
					: 'opacity-60'}"
			>
				<div class="flex items-start gap-4">
					<div class="flex bg-white rounded-2xl shrink-0">
						<img
							src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${agent.id}&lang=${$i18n.language}`}
							alt={agent.name}
							class="rounded-2xl size-14 object-cover"
							loading="lazy"
							decoding="async"
							on:error={(e) => {
								e.target.src = '/favicon.png';
							}}
						/>
					</div>
					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<div class="font-medium text-gray-900 dark:text-gray-50 capitalize line-clamp-1">
								{agent.name}
							</div>
							{#if !agent.is_active}
								<span
									class="shrink-0 rounded-full bg-gray-100 dark:bg-gray-850 px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400"
								>
									Désactivé
								</span>
							{/if}
						</div>
						<div class="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">
							{agent?.meta?.description ?? 'Aucune description pour le moment.'}
						</div>
					</div>
				</div>

				<div class="mt-4 flex items-center gap-2">
					<a
						draggable="false"
						class="inline-flex items-center rounded-full bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
						href={`/?models=${encodeURIComponent(agent.id)}`}
					>
						Parler à {agent.name}
					</a>
					{#if agent.write_access ?? true}
						<a
							draggable="false"
							class="inline-flex items-center rounded-full border border-gray-200 dark:border-gray-800 px-4 py-1.5 text-sm text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-850"
							href={`/workspace/models/edit?id=${encodeURIComponent(agent.id)}`}
						>
							Modifier
						</a>
					{/if}
				</div>
			</div>
		{/each}
	</div>

	{#if total > agents.length}
		<div class="pb-6 -mt-2 text-sm text-gray-500 dark:text-gray-400">
			{agents.length} agents affichés sur {total} —
			<a class="underline hover:text-gray-700 dark:hover:text-gray-200" href="/workspace/models">
				voir la liste complète dans la Bibliothèque
			</a>
		</div>
	{/if}
{/if}
