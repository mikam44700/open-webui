<script lang="ts">
	// Page Catalogue : tous les agents hors socle, rangés par métier (comme les Skills). Recherche +
	// sections par catégorie + adoption en un clic. Réutilise la carte, la modale « compétences » et
	// l'état d'adoption (DRY) — cf. AgentList pour la galerie du socle.
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fly } from 'svelte/transition';
	import { toast } from 'svelte-sonner';

	import { getAgents, createAgent } from '$lib/apis/agents';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AgentGradientCard from './AgentGradientCard.svelte';
	import AgentSkillsModal from './AgentSkillsModal.svelte';
	import { AGENT_TEMPLATES, SOCLE_IDS, type AgentTemplate } from './templates';
	import { avatarId } from './avatars';
	import { avatarColor } from './avatar-colors';
	import { adoptedTemplateIds } from './agentMatch';

	const i18n = getContext('i18n');

	// Ordre d'affichage des rubriques (les catégories absentes sont sautées ; extras en fin).
	const CATEGORY_ORDER = [
		'Ventes & Acquisition',
		'Relation client',
		'Opérations & Projets',
		'Finance',
		'Marketing',
		'Ressources Humaines',
		'Achats',
		'Juridique'
	];
	// Rubrique d'affichage d'un agent = sa catégorie métier.
	const catOf = (t: AgentTemplate) => t.category || 'Autres';

	let loading = true;
	let bridgeDown = false;
	let agents: { name: string; avatar?: string | null }[] = [];
	let search = '';
	let previewTemplate: AgentTemplate | null = null;

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getAgents(localStorage.token);
			agents = res?.agents ?? [];
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else toast.error($i18n.t('Échec du chargement des agents'));
		} finally {
			loading = false;
		}
	};

	const installTemplate = async (tpl: AgentTemplate) => {
		try {
			await createAgent(localStorage.token, {
				// L'IDENTITÉ, c'est l'`id` — jamais le `label`. Le bridge slugifie ce champ pour nommer
				// le profil : passer le libellé faisait dépendre l'identité de l'agent du texte affiché.
				// « Recherche & Veille » donnait `recherche-veille` alors que Léo s'appelle `veille` →
				// installer le template créait un SECOND Léo, sans conflit ni message. L'id est déjà un
				// slug valide (test dans templates.test.ts) : il traverse slugify() inchangé.
				name: tpl.id,
				description: tpl.description,
				soul: tpl.soul,
				avatar: tpl.image
			});
			toast.success($i18n.t('{{name}} ajouté', { name: tpl.label }));
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'exists') toast.error($i18n.t('Cet agent existe déjà'));
			else toast.error($i18n.t('Impossible d’ajouter cet agent'));
		}
	};

	onMount(load);

	$: adopted = adoptedTemplateIds(agents);
	// Catalogue = uniquement les agents OPTIONNELS (hors socle). Le socle des 7 est fixe, livré
	// d'office dans « Mes agents » — il n'a rien à faire dans le catalogue. Cf. décision 2026-07-11.
	$: catalogueTemplates = AGENT_TEMPLATES.filter((t) => !SOCLE_IDS.has(t.id));
	$: q = search.trim().toLowerCase();
	$: filtered = q
		? catalogueTemplates.filter((t) =>
				`${t.label} ${t.role ?? ''} ${t.description} ${catOf(t)}`.toLowerCase().includes(q)
			)
		: catalogueTemplates;
	$: presentCats = [...new Set(filtered.map((t) => catOf(t)))];
	$: orderedCats = [
		...CATEGORY_ORDER.filter((c) => presentCats.includes(c)),
		...presentCats.filter((c) => !CATEGORY_ORDER.includes(c))
	];
	$: groups = orderedCats.map((cat) => ({
		cat,
		items: filtered.filter((t) => catOf(t) === cat)
	}));
</script>

<div class="w-full max-w-7xl mx-auto px-4 pt-5 pb-10">
	<!-- En-tête -->
	<div class="mb-6">
		<button
			class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition mb-3 flex items-center gap-1"
			on:click={() => goto('/workspace/agents')}
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
				<path
					fill-rule="evenodd"
					d="M12.79 5.23a.75.75 0 0 1-.02 1.06L8.832 10l3.938 3.71a.75.75 0 1 1-1.04 1.08l-4.5-4.25a.75.75 0 0 1 0-1.08l4.5-4.25a.75.75 0 0 1 1.06.02Z"
					clip-rule="evenodd"
				/>
			</svg>
			{$i18n.t('Retour aux agents')}
		</button>
		<h1 class="text-lg font-semibold text-gray-900 dark:text-white">
			{$i18n.t('Catalogue d’agents')}
		</h1>
		<p class="text-sm text-gray-500 mt-0.5">
			{$i18n.t('Des agents prêts à l’emploi, par métier. Ajoutez-les à votre équipe en un clic.')}
		</p>
	</div>

	{#if loading}
		<div class="flex justify-center py-24"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-20 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Agents est injoignable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('Le pont vers Hermes ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- Recherche -->
		<div class="relative w-full sm:w-80 mb-6">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
				/>
			</svg>
			<input
				bind:value={search}
				type="text"
				placeholder={$i18n.t('Rechercher un agent (nom, métier…)')}
				class="w-full text-sm pl-9 pr-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 focus:border-gray-300 dark:focus:border-gray-600 focus:ring-2 focus:ring-gray-100 dark:focus:ring-gray-800 outline-none transition placeholder:text-gray-400"
			/>
		</div>

		{#if groups.length === 0}
			<div
				class="text-sm text-gray-400 text-center py-12 border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl"
			>
				{$i18n.t('Aucun agent ne correspond à votre recherche.')}
			</div>
		{:else}
			<div class="flex flex-col gap-9">
				{#each groups as group (group.cat)}
					<section>
						<div class="flex items-baseline gap-2 mb-4">
							<h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{group.cat}</h2>
							<span class="text-xs font-normal text-gray-400">{group.items.length}</span>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{#each group.items as tpl, i (tpl.id)}
								{@const col = avatarColor(avatarId(tpl.image) || tpl.id)}
								{@const isAdopted = adopted.has(tpl.id)}
								<div in:fly={{ y: 10, duration: 240, delay: Math.min(i, 8) * 30 }}>
									<AgentGradientCard
										gradient={col.gradient}
										onLight={col.light}
										name={tpl.firstName ?? tpl.label}
										role={tpl.role ?? ''}
										description={tpl.description}
										image={tpl.image ?? null}
										avatarText={tpl.emoji}
										status={isAdopted ? 'active' : 'none'}
										statusLabel={isAdopted ? $i18n.t('Adopté') : ''}
										primaryLabel={isAdopted
											? $i18n.t('Voir dans mes agents')
											: $i18n.t('+ Activer')}
										secondaryLabel={$i18n.t('Voir ses compétences')}
										on:primary={() =>
											isAdopted ? goto('/workspace/agents') : installTemplate(tpl)}
										on:secondary={() => (previewTemplate = tpl)}
									/>
								</div>
							{/each}
						</div>
					</section>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<!-- Fiche « Voir ses compétences » — composant partagé -->
<AgentSkillsModal
	template={previewTemplate}
	on:close={() => (previewTemplate = null)}
	on:adopt={(e) => installTemplate(e.detail)}
/>
