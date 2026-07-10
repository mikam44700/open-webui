<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';

	import { getAgents, setActiveAgent, createAgent, deleteAgent } from '$lib/apis/agents';
	import { getIntegrations } from '$lib/apis/integrations';
	import { getConnectors } from '$lib/apis/connectors';
	import { getToolConnection } from '$lib/apis/capabilities';
	import { INTEGRATION_FR } from '$lib/utils/integrationLabels';
	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
	import {
		INTEGRATION_LOGO,
		INTEGRATION_LOGO_BG,
		INTEGRATION_LOGO_FULL_BLEED
	} from '$lib/utils/integrationLogos';
	import { CONNECTOR_LOGO, CONNECTOR_LOGO_FULL_BLEED } from '$lib/utils/connectorLogos';
	import { LOGO_BY_SLUG, providerStatus, type Provider } from '$lib/utils/toolConnect';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AgentCreate from './AgentCreate.svelte';
	import AgentEditor from './AgentEditor.svelte';
	import AgentAtelier from './AgentAtelier.svelte';
	import MikeHero from './MikeHero.svelte';
	import AgentGradientCard from './AgentGradientCard.svelte';
	import { AGENT_TEMPLATES } from './templates';
	import { initial, prettifyName, slugify } from './utils';
	import { avatarId, faceFromImage } from './avatars';
	import { avatarColor } from './avatar-colors';
	import MissionSections from './MissionSections.svelte';

	const i18n = getContext('i18n');

	type Agent = {
		name: string;
		description?: string;
		model?: string | null;
		provider?: string | null;
		is_default?: boolean;
		skill_count?: number;
		gateway_running?: boolean;
		active?: boolean;
		avatar?: string | null; // mascotte illustrée (prioritaire sur l'initiale quand fournie)
	};

	let loading = true;
	let bridgeDown = false;
	let agents: Agent[] = [];

	let showCreate = false;
	let showAtelier = false;
	let showEditor = false;
	let editing: Agent | null = null;

	// Confirmation de retrait (suppression) d'un agent adopté → renvoyé au catalogue.
	let removingAgent: Agent | null = null;
	let removing = false;

	// Recherche dans la galerie « Prêts à l'emploi » (façon marketplace).
	let templateQuery = '';

	// Aperçu de la mission d'un template : ouvre une carte (modale) plutôt qu'un pavé déplié.
	let previewTemplate: (typeof AGENT_TEMPLATES)[number] | null = null;

	// État réel des intégrations (id → state), pour afficher honnêtement « Connecté » vs « À connecter »
	// dans la fiche agent. Source de vérité = le pont Intégrations ; on ne suppose jamais un état.
	let integrationState: Record<string, string> = {};
	const loadIntegrationState = async () => {
		try {
			const res = await getIntegrations(localStorage.token);
			integrationState = Object.fromEntries(
				(res?.integrations ?? []).map((i: { id: string; state: string }) => [i.id, i.state])
			);
		} catch {
			// Silencieux : la fiche agent reste utile même sans l'état (CTA renvoie vers Intégrations).
		}
	};
	// Même principe pour les connecteurs MCP (réservoir spécialisé : Stripe, QuickBooks, Slack…).
	let connectorState: Record<string, string> = {};
	const loadConnectorState = async () => {
		try {
			const res = await getConnectors(localStorage.token);
			connectorState = Object.fromEntries(
				(res?.connectors ?? []).map((c: { id: string; state: string }) => [c.id, c.state])
			);
		} catch {
			// Silencieux : la fiche reste utile ; le CTA renvoie vers la page Connecteurs.
		}
	};

	// 3e réservoir : moteurs de recherche web (Exa, Brave, Firecrawl, Tavily, Crawl4AI…),
	// gérés par le système « toolConnect » du toolset `web` — état réel via providerStatus.
	let webState: Record<string, string> = {};
	const WEBSEARCH_NAME: Record<string, string> = {
		exa: 'Exa',
		brave: 'Brave Search',
		firecrawl: 'Firecrawl',
		tavily: 'Tavily',
		duckduckgo: 'DuckDuckGo',
		crawl4ai: 'Crawl4AI'
	};
	// Un fournisseur web « branchable » compte comme connecté dès qu'il est utilisable réellement.
	const WEB_CONNECTED = new Set(['saved', 'key-active', 'active', 'subscription', 'detected', 'local']);
	const loadWebState = async () => {
		try {
			const res = await getToolConnection(localStorage.token, 'web');
			for (const p of ((res as { providers?: Provider[] })?.providers ?? []) as Provider[]) {
				if (p.slug) webState[p.slug] = providerStatus(p);
			}
			webState = { ...webState };
		} catch {
			// Silencieux : la fiche reste utile ; le CTA renvoie vers « Recherche & web ».
		}
	};

	// Liste unifiée des intégrations + connecteurs conseillés d'un agent, pour un rendu unique (DRY).
	type Reco = {
		key: string;
		name: string;
		logo: string | undefined;
		bg: string;
		fullBleed: boolean;
		connected: boolean;
		tab: 'integrations' | 'connectors' | 'web-search';
	};
	const buildReco = (
		tpl: (typeof AGENT_TEMPLATES)[number] | null,
		iState: Record<string, string>,
		cState: Record<string, string>,
		wState: Record<string, string>
	): Reco[] => {
		if (!tpl) return [];
		const items: Reco[] = [];
		for (const id of tpl.recommendedIntegrations ?? []) {
			const meta = INTEGRATION_FR[id];
			if (!meta) continue;
			items.push({
				key: `i-${id}`,
				name: meta.name,
				logo: INTEGRATION_LOGO[id],
				bg: INTEGRATION_LOGO_BG[id] ?? 'bg-white',
				fullBleed: INTEGRATION_LOGO_FULL_BLEED.has(id),
				connected: iState[id] === 'connected' || iState[id] === 'key_present',
				tab: 'integrations'
			});
		}
		for (const id of tpl.recommendedConnectors ?? []) {
			items.push({
				key: `c-${id}`,
				name: CONNECTOR_FR[id]?.name ?? id,
				logo: CONNECTOR_LOGO[id],
				bg: 'bg-white',
				fullBleed: CONNECTOR_LOGO_FULL_BLEED.has(id),
				connected: cState[id] === 'connected',
				tab: 'connectors'
			});
		}
		for (const slug of tpl.recommendedWebSearch ?? []) {
			items.push({
				key: `w-${slug}`,
				name: WEBSEARCH_NAME[slug] ?? slug,
				logo: LOGO_BY_SLUG[slug] ?? CONNECTOR_LOGO[slug],
				bg: 'bg-white',
				fullBleed: false,
				connected: WEB_CONNECTED.has(wState[slug]),
				tab: 'web-search'
			});
		}
		return items;
	};
	$: recoItems = buildReco(previewTemplate, integrationState, connectorState, webState);
	// Couleur signature de l'agent affiché dans la fiche (même teinte que sa carte) → cadre coloré.
	$: previewCol = previewTemplate
		? avatarColor(avatarId(previewTemplate.image) || previewTemplate.id)
		: null;

	// Mike, chef d'orchestre — mis en vedette en tête de page (hero premium).
	const mikeTpl = AGENT_TEMPLATES.find((t) => t.id === 'mike-chef-orchestre') ?? null;
	// Repli d'avatar si le PNG n'est pas (encore) présent → jamais d'image cassée.
	let imgError: Record<string, boolean> = {};

	const matchesMike = (a: Agent): boolean =>
		!!mikeTpl &&
		(a.name === mikeTpl.id ||
			a.name === mikeTpl.label ||
			prettifyName(a.name ?? '')
				.toLowerCase()
				.startsWith('mike'));

	// Retrouve le template d'un agent (par identifiant/label/avatar) pour réutiliser SON
	// image et SA couleur de métier dans « Mes agents » — cohérence avec « Prêts à l'emploi »
	// (fini le « A » nu et le changement de teinte entre les deux sections).
	const matchTemplate = (a: Agent): (typeof AGENT_TEMPLATES)[number] | null =>
		AGENT_TEMPLATES.find(
			(x) =>
				x.id === a.name ||
				// le nom d'un agent créé = slug de son libellé de template (identique au bridge)
				slugify(x.label) === a.name ||
				(!!x.image && !!a.avatar && avatarId(x.image) === avatarId(a.avatar))
		) ?? null;

	$: existingNames = new Set(agents.map((a) => a.name));
	// Visages déjà attribués à un agent → grisés dans le sélecteur (pas de doublon).
	$: usedAvatarIds = agents.map((a) => avatarId(a.avatar)).filter(Boolean);
	// Métiers déjà adoptés (résolus de façon fiable, même si le nom du profil diffère de l'id).
	$: adoptedTemplateIds = new Set(agents.map((a) => matchTemplate(a)?.id).filter(Boolean));
	// Mike est déjà en vedette dans le hero → on l'exclut de la galerie ; idem métiers adoptés.
	$: availableTemplates = AGENT_TEMPLATES.filter(
		(t) => t.id !== 'mike-chef-orchestre' && !adoptedTemplateIds.has(t.id)
	);
	// Identité fiable de Mike : on le reconnaît via son template (comme la carte), pas via son nom
	// slugifié — `matchesMike` seul ratait l'agent réel (nom = slug du libellé).
	$: mikeAgent = agents.find((a) => matchTemplate(a)?.id === 'mike-chef-orchestre' || matchesMike(a));
	$: mikeActive = !!mikeAgent?.active;
	// Mike est déjà en vedette dans le hero → on l'exclut de la grille « Mes agents » (fini le doublon).
	$: myAgents = agents.filter((a) => a !== mikeAgent);
	$: filteredTemplates = availableTemplates.filter((t) => {
		const q = templateQuery.trim().toLowerCase();
		if (!q) return true;
		return `${t.label} ${t.description}`.toLowerCase().includes(q);
	});

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getAgents(localStorage.token);
			agents = res?.agents ?? [];
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des agents'));
			}
		} finally {
			loading = false;
		}
	};

	const activate = async (agent: Agent) => {
		try {
			await setActiveAgent(localStorage.token, agent.name);
			toast.success($i18n.t('{{name}} est prêt à discuter', { name: prettifyName(agent.name) }));
			goto('/');
		} catch {
			toast.error($i18n.t('Impossible d’activer cet agent'));
		}
	};

	const edit = (agent: Agent) => {
		editing = agent;
		showEditor = true;
	};

	// Retire un agent (le supprime) après confirmation : son métier réapparaît dans
	// « Prêts à l'emploi » (la galerie ne liste que les métiers non adoptés).
	const confirmRemove = async () => {
		if (!removingAgent || removing) return;
		removing = true;
		try {
			await deleteAgent(localStorage.token, removingAgent.name);
			toast.success(
				$i18n.t('{{name}} retiré de votre équipe', { name: prettifyName(removingAgent.name) })
			);
			removingAgent = null;
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'default') {
				toast.error($i18n.t('L’agent par défaut ne peut pas être retiré'));
			} else {
				toast.error($i18n.t('Impossible de retirer cet agent'));
			}
		} finally {
			removing = false;
		}
	};

	const installTemplate = async (tpl: (typeof AGENT_TEMPLATES)[number]) => {
		try {
			await createAgent(localStorage.token, {
				name: tpl.label,
				description: tpl.description,
				soul: tpl.soul,
				avatar: tpl.image // persiste le visage de l'agent (sinon repli sur l'initiale)
			});
			toast.success($i18n.t('{{name}} ajouté', { name: tpl.label }));
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Cet agent existe déjà'));
			} else {
				toast.error($i18n.t('Impossible d’ajouter cet agent'));
			}
		}
	};

	// « Parler à Mike » : s'il existe déjà, on l'active ; sinon on le crée puis on l'active.
	const talkToMike = async () => {
		if (!mikeTpl) return;
		if (mikeAgent) {
			await activate(mikeAgent);
			return;
		}
		try {
			await createAgent(localStorage.token, {
				name: mikeTpl.label,
				description: mikeTpl.description,
				soul: mikeTpl.soul,
				avatar: mikeTpl.image
			});
			await load();
			const created = agents.find(matchesMike);
			if (created) {
				await activate(created);
			} else {
				toast.success($i18n.t('{{name}} ajouté', { name: 'Mike' }));
			}
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Cet agent existe déjà'));
			} else {
				toast.error($i18n.t('Impossible d’ajouter cet agent'));
			}
		}
	};

	const showMikeMission = () => {
		if (mikeTpl) previewTemplate = mikeTpl;
	};

	onMount(() => {
		load();
		loadIntegrationState();
		loadConnectorState();
		loadWebState();
	});
</script>

<div class="w-full max-w-7xl mx-auto px-4 pt-5 pb-8">
		<!-- Action de création (le grand titre du hub est fourni par le layout « Espace de travail ») -->
		<div class="flex items-center justify-end gap-4 mb-6">
			<div class="flex-none flex flex-col items-end gap-1.5">
				<button
					class="text-sm font-medium px-4 py-2.5 rounded-xl bg-gradient-to-br from-gray-900 to-black text-white dark:from-white dark:to-gray-200 dark:text-black shadow-sm hover:shadow-md hover:-translate-y-px active:translate-y-0 transition-all flex items-center gap-1.5 whitespace-nowrap"
					on:click={() => (showAtelier = true)}
				>
					<span>✨</span>{$i18n.t('Créer un agent')}
				</button>
				<button
					class="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
					on:click={() => (showCreate = true)}
				>
					{$i18n.t('Mode manuel')}
				</button>
			</div>
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
			<!-- Mike, chef d'orchestre — en vedette -->
			{#if mikeTpl}
				<MikeHero
					tpl={mikeTpl}
					active={mikeActive}
					editable={!!mikeAgent}
					on:talk={talkToMike}
					on:mission={showMikeMission}
					on:edit={() => mikeAgent && edit(mikeAgent)}
				/>
			{/if}

			<!-- Mes agents -->
			<section class="mb-11">
				<div class="flex items-baseline gap-2 mb-4">
					<h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
						{$i18n.t('Mes agents')}
					</h2>
					<span class="text-xs font-normal text-gray-400">{myAgents.length}</span>
				</div>

				{#if myAgents.length === 0}
					<div
						class="flex flex-col items-center justify-center text-center py-12 px-6 gap-2 rounded-3xl border border-dashed border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/30"
					>
						<div class="text-2xl">🪄</div>
						<div class="text-sm font-medium">{$i18n.t('Aucun agent pour l’instant')}</div>
						<div class="text-xs text-gray-500 max-w-xs">
							{$i18n.t('Créez le vôtre en une phrase, ou activez un modèle prêt à l’emploi ci-dessous.')}
						</div>
					</div>
				{:else}
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
						{#each myAgents as agent, i (agent.name)}
							{@const tpl = matchTemplate(agent)}
							{@const col = avatarColor(avatarId(agent.avatar ?? tpl?.image) || agent.name)}
							<div in:fly={{ y: 10, duration: 260, delay: i * 35 }}>
								<AgentGradientCard
									gradient={col.gradient}
									onLight={col.light}
									name={tpl?.firstName ?? prettifyName(agent.name)}
									role={tpl?.role ?? ''}
									description={agent.description || $i18n.t('Aucune mission définie pour le moment.')}
									image={agent.avatar ?? tpl?.image ?? null}
									avatarText={initial(prettifyName(agent.name))}
									status="active"
									statusLabel={$i18n.t('Actif')}
									primaryLabel={agent.active ? $i18n.t('Continuer') + ' →' : $i18n.t('Discuter')}
									secondaryLabel={tpl ? $i18n.t('Voir ses compétences') : ''}
									editable={true}
									removable={!agent.is_default}
									on:primary={() => activate(agent)}
									on:secondary={() => tpl && (previewTemplate = tpl)}
									on:edit={() => edit(agent)}
									on:remove={() => (removingAgent = agent)}
								/>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Prêts à l'emploi (templates) -->
			{#if availableTemplates.length > 0}
				<section>
					<div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
						<div>
							<h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
								{$i18n.t('Prêts à l’emploi')}
							</h2>
							<p class="text-xs text-gray-500 mt-0.5">
								{$i18n.t('Des agents préconfigurés par métier — activez-les en un clic.')}
							</p>
						</div>
						<div class="relative w-full sm:w-64">
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
								bind:value={templateQuery}
								type="text"
								placeholder={$i18n.t('Rechercher un métier…')}
								class="w-full text-sm pl-9 pr-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 focus:border-gray-300 dark:focus:border-gray-600 focus:ring-2 focus:ring-gray-100 dark:focus:ring-gray-800 outline-none transition placeholder:text-gray-400"
							/>
						</div>
					</div>

					{#if filteredTemplates.length === 0}
						<div class="text-sm text-gray-400 text-center py-12 border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl">
							{$i18n.t('Aucun agent ne correspond à votre recherche.')}
						</div>
					{:else}
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{#each filteredTemplates as tpl, i (tpl.id)}
								{@const col = avatarColor(avatarId(tpl.image) || tpl.id)}
								<div in:fly={{ y: 10, duration: 240, delay: Math.min(i, 8) * 30 }}>
									<AgentGradientCard
										gradient={col.gradient}
										onLight={col.light}
										name={tpl.firstName ?? tpl.label}
										role={tpl.role ?? ''}
										description={tpl.description}
										image={tpl.image ?? null}
										avatarText={tpl.emoji}
										primaryLabel={$i18n.t('+ Activer')}
										secondaryLabel={$i18n.t('Voir ses compétences')}
										on:primary={() => installTemplate(tpl)}
										on:secondary={() => (previewTemplate = tpl)}
									/>
								</div>
							{/each}
						</div>
					{/if}
				</section>
			{/if}
		{/if}
</div>

<svelte:window
	on:keydown={(e) => {
		if (e.key !== 'Escape') return;
		if (removingAgent && !removing) removingAgent = null;
		else if (previewTemplate) previewTemplate = null;
	}}
/>

<!-- Confirmation de retrait (suppression) d'un agent adopté -->
{#if removingAgent}
	<div
		class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
		on:click|self={() => !removing && (removingAgent = null)}
		transition:fade={{ duration: 150 }}
		role="presentation"
	>
		<div
			class="relative w-full max-w-md flex flex-col rounded-3xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-100 dark:border-gray-800 p-6"
			in:fly={{ y: 12, duration: 200 }}
			role="dialog"
			aria-modal="true"
		>
			<div class="text-base font-semibold">
				{$i18n.t('Retirer {{name}} de votre équipe ?', {
					name: prettifyName(removingAgent.name)
				})}
			</div>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
				{$i18n.t(
					'Son métier réapparaîtra dans « Prêts à l’emploi ». Vous pourrez le réactiver à tout moment.'
				)}
			</p>
			<div class="flex items-center justify-end gap-2 mt-6">
				<button
					class="text-sm font-medium px-4 py-2 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-50"
					on:click={() => (removingAgent = null)}
					disabled={removing}
				>
					{$i18n.t('Annuler')}
				</button>
				<button
					class="text-sm font-semibold px-4 py-2 rounded-xl bg-red-600 text-white shadow-sm hover:bg-red-700 active:translate-y-px transition disabled:opacity-50"
					on:click={confirmRemove}
					disabled={removing}
				>
					{removing ? $i18n.t('Retrait…') : $i18n.t('Retirer')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Carte « mission » (modale) — aperçu du SOUL avant activation -->
{#if previewTemplate}
	<div
		class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
		on:click|self={() => (previewTemplate = null)}
		transition:fade={{ duration: 150 }}
		role="presentation"
	>
		<div
			class="relative w-full max-w-lg max-h-[85vh] flex flex-col rounded-3xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-100 dark:border-gray-800"
			in:fly={{ y: 12, duration: 200 }}
			role="dialog"
			aria-modal="true"
		>
			<!-- En-tête -->
			<div class="flex items-center gap-3.5 p-5 border-b border-gray-100 dark:border-gray-800">
				{#if previewTemplate.image && !imgError[previewTemplate.id]}
					<!-- Gros plan visage cadré, posé sur un fin cadre à la couleur signature de l'agent. -->
					<div
						class="flex-none size-11 rounded-2xl p-[2px] shadow-sm ring-1 ring-black/5"
						style="background-image: {previewCol?.gradient}"
					>
						<img
							src={faceFromImage(previewTemplate.image)}
							alt={previewTemplate.label}
							on:error={() =>
								previewTemplate && (imgError = { ...imgError, [previewTemplate.id]: true })}
							class="size-full rounded-[14px] object-cover"
						/>
					</div>
				{:else}
					<div
						class="flex-none size-11 rounded-2xl flex items-center justify-center text-2xl shadow-sm ring-1 ring-black/5 {previewCol?.light
							? 'text-gray-900'
							: 'text-white'}"
						style="background-image: {previewCol?.gradient}"
					>
						{previewTemplate.emoji}
					</div>
				{/if}
				<div class="min-w-0 flex-1">
					<div class="text-base font-semibold truncate">
						{previewTemplate.firstName ?? previewTemplate.label}
					</div>
					{#if previewTemplate.role}
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">
							{previewTemplate.role}
						</div>
					{/if}
				</div>
				<button
					class="flex-none p-1.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (previewTemplate = null)}
					aria-label={$i18n.t('Fermer')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
						<path
							d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
						/>
					</svg>
				</button>
			</div>

			<!-- Corps : la mission (SOUL) en cartes lisibles, défilable -->
			<div class="flex-1 overflow-y-auto px-5 py-4">
				<MissionSections soul={previewTemplate.soul} animate={false} />

				<!-- Intégrations recommandées : ce qui rend cet agent vraiment utile (état réel, jamais supposé) -->
				{#if recoItems.length}
					<div class="mt-5 pt-4 border-t border-gray-100 dark:border-gray-800">
						<div class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2.5">
							{$i18n.t('Intégrations recommandées')}
						</div>
						<div class="flex flex-col gap-1.5">
							{#each recoItems as it (it.key)}
								<div
									class="flex items-center gap-3 rounded-xl border border-gray-100 dark:border-gray-800 px-3 py-2"
								>
									<div
										class="flex-none size-8 rounded-lg overflow-hidden flex items-center justify-center ring-1 ring-black/5 {it.bg}"
									>
										{#if it.logo}
											<img
												src={it.logo}
												alt={it.name}
												class={it.fullBleed
													? 'h-full w-full object-cover'
													: 'h-5 w-5 object-contain'}
											/>
										{/if}
									</div>
									<div class="min-w-0 flex-1">
										<div class="text-sm font-medium truncate">{it.name}</div>
										<div
											class="text-[11px] {it.connected
												? 'text-emerald-600 dark:text-emerald-400'
												: 'text-gray-400'}"
										>
											{it.connected ? '✓ ' + $i18n.t('Connecté') : $i18n.t('À connecter')}
										</div>
									</div>
									<button
										class="flex-none text-[12px] font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white underline-offset-2 hover:underline transition"
										on:click={() => {
											previewTemplate = null;
											goto(`/connectors?tab=${it.tab}`);
										}}
									>
										{it.connected ? $i18n.t('Gérer') : $i18n.t('Connecter')}
									</button>
								</div>
							{/each}
						</div>
						<p class="text-[11px] text-gray-400 mt-2">
							{$i18n.t('Ces connexions rendent cet agent plus utile — activez-les quand vous voulez.')}
						</p>
					</div>
				{/if}
			</div>

			<!-- Pied : activer -->
			<div class="p-4 border-t border-gray-100 dark:border-gray-800">
				<button
					class="w-full text-sm font-medium px-3 py-2.5 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-black hover:opacity-90 hover:shadow-md transition-all"
					on:click={() => {
						const t = previewTemplate;
						previewTemplate = null;
						if (t) installTemplate(t);
					}}
				>
					{$i18n.t('+ Activer')}
				</button>
			</div>
		</div>
	</div>
{/if}

<AgentAtelier bind:show={showAtelier} used={usedAvatarIds} on:created={load} />
<AgentCreate bind:show={showCreate} on:created={load} />
<AgentEditor
	bind:show={showEditor}
	agent={editing}
	used={usedAvatarIds}
	on:updated={load}
	on:deleted={load}
/>
