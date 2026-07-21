<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { getModelItems } from '$lib/apis/models';
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext('i18n');

	let agents = null;
	let total = null;

	// Modale « Voir sa mission » (même recette visuelle que la modale des Intégrations)
	let missionAgent = null;

	// Modale « Règlement intérieur » (chantier Guardrails) : les garde-fous de l'agent,
	// lus depuis meta.reglement (seed) — même recette visuelle que la modale mission.
	let reglementAgent = null;

	// Agents à venir (règle anti-catalogue : montrés, pas construits — activés à la demande client)
	const comingSoon = [
		{
			name: 'Max',
			avatar: `${WEBUI_BASE_URL}/static/agents/max.png`,
			tagline: 'Tes devis en minutes.',
			description: 'Tes devis rédigés en minutes, sur la base de ta grille tarifaire et de ton historique.',
			mission: [
				'Rédaction en minutes — à partir de ta grille tarifaire et de ton historique de devis.',
				'Personnalisation client — le bon prix, les bonnes mentions, le bon ton.',
				'Validation avant envoi — comme toujours, rien ne part sans toi.'
			],
			reglement: [
				"Aucun devis envoyé sans validation — chaque devis est un brouillon jusqu'à ton OK.",
				'Prix uniquement depuis ta grille — jamais un tarif ou une remise inventés.',
				'Remises encadrées — toute remise hors grille remonte vers toi avant d’apparaître sur un devis.'
			]
		},
		{
			name: 'Sam',
			avatar: `${WEBUI_BASE_URL}/static/agents/sam.png`,
			tagline: 'Tes réunions mémorisées.',
			description: 'Tes réunions transcrites et mémorisées — concentre-toi sur la conversation, pas sur les notes.',
			mission: [
				'Transcription automatique — concentre-toi sur la conversation, pas sur les notes.',
				'Tout reste chez toi — l’audio est traité sur TON serveur, jamais envoyé à un tiers.',
				'Mémorisation — décisions et actions rangées dans la mémoire de l’entreprise (Mike).'
			],
			reglement: [
				'Jamais d’enregistrement sans ton accord — chaque réunion enregistrée est une décision explicite de ta part.',
				'Audio traité sur TON serveur — jamais envoyé à un service tiers, jamais conservé au-delà de la transcription.',
				'Mémorisation sous approbation — les décisions extraites passent par la file de validation avant d’entrer dans la mémoire (Mike).'
			]
		}
	];

	const openMission = (name, avatar, description, mission) => {
		missionAgent = { name, avatar, description, mission: mission ?? [] };
	};

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

		// Ordre d'équipe voulu par Michael (2026-07-19) : Luna et Mike d'abord (le cœur),
		// puis les spécialistes ; les agents personnalisés arrivent après l'équipe.
		const TEAM_ORDER = ['luna', 'mike', 'victor', 'lea', 'sacha'];
		const rank = (a) => {
			const i = TEAM_ORDER.indexOf(a.id);
			return i === -1 ? TEAM_ORDER.length : i;
		};
		agents = (res?.items ?? []).slice().sort((a, b) => rank(a) - rank(b));
		total = res?.total ?? agents.length;
	});
</script>

<HeroBanner
	lead="Ton équipe est"
	strong="déjà prête"
	sub="Chaque agent connaît sa mission. Parle-leur directement — et rien ne part jamais sans ta validation."
	wrap="from-violet-200/60 via-slate-100/60 to-violet-100/40 dark:from-[#6b62f2]/25 dark:via-[#161616]/80 dark:to-[#0a0a0a]/90"
	halo1="bg-violet-300/40 dark:bg-[#6b62f2]/25"
	halo2="bg-indigo-200/30 dark:bg-[#6b62f2]/10"
	compact={true}
/>

{#if agents === null}
	<div class="flex justify-center py-16">
		<Spinner className="size-5" />
	</div>
{:else}
	{#if agents.length === 0}
		<!-- Repli : l'équipe n'a pas encore été installée sur cet espace (seed non joué) -->
		<div
			class="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-5 py-16 text-center"
		>
			<div class="font-medium text-gray-900 dark:text-gray-50">
				Ton équipe n'est pas encore installée sur cet espace
			</div>
			<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				L'installation LunarIA la met en place pour toi — tu n'as rien à construire.
			</div>
		</div>
	{:else}
		<div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{total} agent{total > 1 ? 's' : ''} à ton service
			</div>
			<button
				class="inline-flex w-fit items-center gap-2 rounded-full border border-gray-200 px-4 py-1.5 text-sm text-gray-600 transition hover:bg-gray-50 dark:border-gray-800 dark:text-gray-400 dark:hover:bg-gray-850"
				on:click={() => goto('/workspace/models/create')}
			>
				<Plus className="size-4" />
				Créer un agent personnalisé
			</button>
		</div>

		<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			{#each agents as agent (agent.id)}
				<div
					class="rounded-2xl border border-gray-200/80 bg-white p-4 transition-colors hover:border-gray-300 dark:border-white/6 dark:bg-[#161616] dark:hover:border-white/15 {agent.is_active
						? ''
						: 'opacity-60'}"
				>
					<div class="flex flex-col gap-4 sm:flex-row sm:items-center">
						<div
							class="size-20 shrink-0 overflow-hidden rounded-xl bg-white sm:h-28 sm:w-24"
						>
							<img
								src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${agent.id}&lang=${$i18n.language}`}
								alt={agent.name}
								class="size-full object-cover object-top"
								loading="lazy"
								decoding="async"
								on:error={(e) => {
									e.target.src = '/favicon.png';
								}}
							/>
						</div>
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<div
									class="text-lg font-medium tracking-tight text-gray-900 dark:text-gray-50 capitalize line-clamp-1"
								>
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
								{agent?.meta?.tagline || agent?.meta?.description || 'Aucune description pour le moment.'}
							</div>
							<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
								{#if (agent?.meta?.mission ?? []).length}
									<button
										class="whitespace-nowrap text-left text-xs font-medium text-violet-600 hover:underline dark:text-[#a5a0f7]"
										on:click={() =>
											openMission(
												agent.name,
												`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${agent.id}&lang=${$i18n.language}`,
												agent?.meta?.description,
												agent?.meta?.mission
											)}
									>
										Voir sa mission ›
									</button>
								{/if}
								{#if (agent?.meta?.reglement ?? []).length}
									<button
										class="whitespace-nowrap text-left text-xs font-medium text-violet-600 hover:underline dark:text-[#a5a0f7]"
										on:click={() =>
											(reglementAgent = {
												name: agent.name,
												avatar: `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${agent.id}&lang=${$i18n.language}`,
												reglement: agent?.meta?.reglement ?? []
											})}
									>
										🛡 Règlement intérieur ›
									</button>
								{/if}
							</div>
						</div>

						<!-- Actions : côte à côte sur mobile, en colonne stable dès que la carte est horizontale. -->
						<div
							class="grid w-full shrink-0 grid-cols-2 gap-2 sm:flex sm:w-auto sm:min-w-[9.5rem] sm:flex-col sm:items-stretch"
						>
							<a
								draggable="false"
								class="inline-flex items-center justify-center whitespace-nowrap rounded-full bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
								href={`/?models=${encodeURIComponent(agent.id)}`}
							>
								Parler à {agent.name}
							</a>
							{#if agent.write_access ?? true}
								<a
									draggable="false"
									class="inline-flex items-center justify-center whitespace-nowrap rounded-full border border-gray-200 px-4 py-1.5 text-sm text-gray-700 transition hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-850"
									href={`/workspace/models/edit?id=${encodeURIComponent(agent.id)}`}
								>
									Modifier
								</a>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>

		{#if total > agents.length}
			<div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
				{agents.length} agents affichés sur {total} —
				<a class="underline hover:text-gray-700 dark:hover:text-gray-200" href="/workspace/models">
					voir la liste complète dans la Bibliothèque
				</a>
			</div>
		{/if}
	{/if}

	<!-- L'équipe grandit : agents à venir, activés à la demande -->
	<div class="mt-10 pb-8">
		<div
			class="text-xs font-medium uppercase tracking-[0.14em] text-gray-500 dark:text-[#c2c2c2] mb-4"
		>
			Bientôt dans ton équipe
		</div>
		<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			{#each comingSoon as soon (soon.name)}
				<div
					class="rounded-2xl border border-dashed border-gray-200 bg-gray-50/60 p-4 opacity-75 dark:border-white/8 dark:bg-[#111111]/70"
				>
					<div class="flex flex-col gap-4 sm:flex-row sm:items-center">
						<div
							class="size-20 shrink-0 overflow-hidden rounded-xl bg-white sm:h-28 sm:w-24"
						>
							<img
								src={soon.avatar}
								alt={soon.name}
								class="size-full object-cover object-top grayscale"
								loading="lazy"
								decoding="async"
								on:error={(e) => {
									e.target.src = '/favicon.png';
								}}
							/>
						</div>
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<div class="font-medium text-gray-900 dark:text-gray-50">{soon.name}</div>
								<span
									class="shrink-0 rounded-full bg-gray-200/80 dark:bg-gray-800 px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400"
								>
									Bientôt disponible
								</span>
							</div>
							<div class="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">
								{soon.tagline}
							</div>
							<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
								<button
									class="whitespace-nowrap text-left text-xs font-medium text-violet-600 hover:underline dark:text-[#a5a0f7]"
									on:click={() => openMission(soon.name, soon.avatar, soon.description, soon.mission)}
								>
									Voir sa mission ›
								</button>
								{#if (soon.reglement ?? []).length}
									<button
										class="whitespace-nowrap text-left text-xs font-medium text-violet-600 hover:underline dark:text-[#a5a0f7]"
										on:click={() =>
											(reglementAgent = {
												name: soon.name,
												avatar: soon.avatar,
												reglement: soon.reglement
											})}
									>
										🛡 Règlement intérieur ›
									</button>
								{/if}
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

{#if reglementAgent}
	<!-- Modale « Règlement intérieur » : les garde-fous de l'agent, même recette que la
	     modale mission (chantier Guardrails — la Boucle de confiance rendue visible) -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={() => (reglementAgent = null)}
		role="presentation"
	>
		<div
			class="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 shadow-xl p-5"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
		>
			<div class="flex items-center justify-between mb-1">
				<div class="flex items-center gap-2.5">
					<img
						src={reglementAgent.avatar}
						alt={reglementAgent.name}
						class="size-9 rounded-xl object-cover"
						on:error={(e) => {
							e.target.src = '/favicon.png';
						}}
					/>
					<span class="text-base font-medium">{reglementAgent.name}</span>
				</div>
				<button
					class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
					on:click={() => (reglementAgent = null)}
					aria-label="Fermer"
				>
					✕
				</button>
			</div>
			<div class="text-xs text-gray-500 mb-4">
				Les règles gravées dans ses instructions — ce qu'il n'a jamais le droit de faire.
			</div>

			<div
				class="text-[11px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400 mb-2.5"
			>
				🛡 Son règlement intérieur
			</div>
			<ul class="flex flex-col gap-3">
				{#each reglementAgent.reglement as item}
					{@const parts = item.split(' — ')}
					{@const title = parts.length > 1 ? parts[0] : null}
					{@const desc = parts.length > 1 ? parts.slice(1).join(' — ') : item}
					<li class="flex items-start gap-2.5 text-xs text-gray-600 dark:text-gray-300">
						<span
							class="flex-none mt-1.5 size-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400"
						></span>
						<span>
							{#if title}<span class="font-semibold text-gray-800 dark:text-gray-100">{title}</span> —
							{/if}{desc}
						</span>
					</li>
				{/each}
			</ul>

			<div class="mt-4 text-[11px] text-gray-400 dark:text-gray-500">
				Ce règlement fait partie de la Boucle de confiance LunarIA : il n'est modifiable qu'à
				l'installation, jamais en conversation — même si on le lui demande.
			</div>

			<div class="mt-4 flex justify-end">
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (reglementAgent = null)}
				>
					Fermer
				</button>
			</div>
		</div>
	</div>
{/if}

{#if missionAgent}
	<!-- Modale « Voir sa mission » : overlay centré, même style que la modale des Intégrations -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={() => (missionAgent = null)}
		role="presentation"
	>
		<div
			class="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 shadow-xl p-5"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
		>
			<div class="flex items-center justify-between mb-1">
				<div class="flex items-center gap-2.5">
					<img
						src={missionAgent.avatar}
						alt={missionAgent.name}
						class="size-9 rounded-xl object-cover"
						on:error={(e) => {
							e.target.src = '/favicon.png';
						}}
					/>
					<span class="text-base font-medium">{missionAgent.name}</span>
				</div>
				<button
					class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
					on:click={() => (missionAgent = null)}
					aria-label="Fermer"
				>
					✕
				</button>
			</div>
			<div class="text-xs text-gray-500 mb-4">{missionAgent.description}</div>

			<div
				class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2.5"
			>
				Sa mission
			</div>
			<ul class="flex flex-col gap-3">
				{#each missionAgent.mission as item}
					{@const parts = item.split(' — ')}
					{@const title = parts.length > 1 ? parts[0] : null}
					{@const desc = parts.length > 1 ? parts.slice(1).join(' — ') : item}
					<li class="flex items-start gap-2.5 text-xs text-gray-600 dark:text-gray-300">
						<span class="flex-none mt-1.5 size-1.5 rounded-full bg-gray-400 dark:bg-gray-600"></span>
						<span>
							{#if title}<span class="font-semibold text-gray-800 dark:text-gray-100">{title}</span> —
							{/if}{desc}
						</span>
					</li>
				{/each}
			</ul>

			<div class="mt-4 text-[11px] text-gray-400 dark:text-gray-500">
				Les branchements à tes outils (factures, emails, agenda) se font à l'installation — et règle
				d'or : rien ne part jamais sans ta validation.
			</div>

			<div class="mt-4 flex justify-end">
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (missionAgent = null)}
				>
					Fermer
				</button>
			</div>
		</div>
	</div>
{/if}
