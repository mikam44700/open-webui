<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';

	import { getAgents, setActiveAgent, createAgent, deleteAgent } from '$lib/apis/agents';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AgentCreate from './AgentCreate.svelte';
	import AgentEditor from './AgentEditor.svelte';
	import AgentAtelier from './AgentAtelier.svelte';
	import MikeHero from './MikeHero.svelte';
	import AgentGradientCard from './AgentGradientCard.svelte';
	import AgentSkillsModal from './AgentSkillsModal.svelte';
	import { AGENT_TEMPLATES, SOCLE_IDS } from './templates';
	import { initial, prettifyName } from './utils';
	import { avatarId } from './avatars';
	import { avatarColor } from './avatar-colors';
	import { matchTemplate } from './agentMatch';

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

	// Aperçu de la mission d'un template : ouvre une carte (modale) plutôt qu'un pavé déplié.
	let previewTemplate: (typeof AGENT_TEMPLATES)[number] | null = null;

	// La fiche « Voir ses compétences » (mission + intégrations recommandées à état réel) est rendue
	// par le composant partagé AgentSkillsModal, qui charge lui-même l'état des trois réservoirs.

	// Mike, chef d'orchestre — mis en vedette en tête de page (hero premium).
	const mikeTpl = AGENT_TEMPLATES.find((t) => t.id === 'mike-chef-orchestre') ?? null;

	const matchesMike = (a: Agent): boolean =>
		!!mikeTpl &&
		(a.name === mikeTpl.id ||
			a.name === mikeTpl.label ||
			prettifyName(a.name ?? '')
				.toLowerCase()
				.startsWith('mike'));

	$: existingNames = new Set(agents.map((a) => a.name));
	// Visages déjà attribués à un agent → grisés dans le sélecteur (pas de doublon).
	$: usedAvatarIds = agents.map((a) => avatarId(a.avatar)).filter(Boolean);
	// Identité fiable de Mike : on le reconnaît via son template (comme la carte), pas via son nom
	// slugifié — `matchesMike` seul ratait l'agent réel (nom = slug du libellé).
	$: mikeAgent = agents.find((a) => matchTemplate(a)?.id === 'mike-chef-orchestre' || matchesMike(a));
	$: mikeActive = !!mikeAgent?.active;
	// Mike est déjà en vedette dans le hero → on l'exclut de la grille « Mes agents » (fini le doublon).
	$: myAgents = agents.filter((a) => a !== mikeAgent);
	// Nombre d'agents optionnels (hors socle) présentés dans le catalogue — pour le badge du bloc.
	const catalogueCount = AGENT_TEMPLATES.filter((t) => !SOCLE_IDS.has(t.id)).length;

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
				// L'identité, c'est l'`id`, jamais le `label` (cf. AgentCatalogue + templates.test.ts).
				name: tpl.id,
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
		// Filet : depuis le 2026-07-15, Mike est LIVRÉ comme profil `default` (deploy/hermes-defaults).
		// On ne devrait donc jamais passer ici — `mikeAgent` le trouve via son avatar. Si on y passe,
		// c'est une instance antérieure à cette livraison : on crée Mike sous son `id` (jamais son
		// libellé, qui donnait `mike-chef-dorchestre`).
		try {
			await createAgent(localStorage.token, {
				name: mikeTpl.id,
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

			<!-- Accès au catalogue complet : tous les agents prêts à l'emploi, rangés par métier -->
			<button
				class="group relative mb-8 w-full overflow-hidden rounded-3xl border border-gray-200/80 dark:border-white/10 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-950 px-5 py-4 sm:px-6 sm:py-5 text-left shadow-sm hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
				on:click={() => goto('/workspace/agents/catalogue')}
			>
				<!-- halo décoratif révélé au survol -->
				<div
					class="pointer-events-none absolute -right-12 -top-12 size-44 rounded-full bg-gradient-to-br from-violet-500/25 to-indigo-500/10 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
				></div>

				<div class="relative flex items-center gap-4">
					<!-- icône premium (dégradé + ombre colorée) -->
					<div
						class="flex-none size-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-violet-500/25 ring-1 ring-white/20 group-hover:scale-105 transition-transform duration-300"
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6">
							<path
								d="M3.75 3h4.5A1.5 1.5 0 0 1 9.75 4.5v4.5a1.5 1.5 0 0 1-1.5 1.5h-4.5A1.5 1.5 0 0 1 2.25 9V4.5A1.5 1.5 0 0 1 3.75 3Zm12 0h4.5a1.5 1.5 0 0 1 1.5 1.5v4.5a1.5 1.5 0 0 1-1.5 1.5h-4.5a1.5 1.5 0 0 1-1.5-1.5V4.5A1.5 1.5 0 0 1 15.75 3Zm-12 12h4.5a1.5 1.5 0 0 1 1.5 1.5v4.5a1.5 1.5 0 0 1-1.5 1.5h-4.5a1.5 1.5 0 0 1-1.5-1.5V16.5A1.5 1.5 0 0 1 3.75 15Zm12 0h4.5a1.5 1.5 0 0 1 1.5 1.5v4.5a1.5 1.5 0 0 1-1.5 1.5h-4.5a1.5 1.5 0 0 1-1.5-1.5V16.5a1.5 1.5 0 0 1 1.5-1.5Z"
							/>
						</svg>
					</div>

					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<span class="text-[15px] font-semibold text-gray-900 dark:text-white">
								{$i18n.t('Explorer le catalogue')}
							</span>
							<span
								class="flex-none text-[11px] font-semibold px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300 ring-1 ring-violet-500/20"
							>
								{catalogueCount}
								{$i18n.t('agents')}
							</span>
						</div>
						<div class="text-[13px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">
							{$i18n.t('Des agents prêts à l’emploi, rangés par métier — activez-les en un clic.')}
						</div>
					</div>

					<!-- flèche dans un cercle qui se colore au survol -->
					<div
						class="flex-none size-9 rounded-full flex items-center justify-center bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-300 group-hover:bg-violet-600 group-hover:text-white group-hover:shadow-md group-hover:shadow-violet-500/30 transition-all duration-300"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-4 group-hover:translate-x-0.5 transition-transform duration-300"
						>
							<path
								fill-rule="evenodd"
								d="M7.21 14.77a.75.75 0 0 1 .02-1.06L11.168 10 7.23 6.29a.75.75 0 1 1 1.04-1.08l4.5 4.25a.75.75 0 0 1 0 1.08l-4.5 4.25a.75.75 0 0 1-1.06-.02Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</div>
			</button>

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
		{/if}
</div>

<svelte:window
	on:keydown={(e) => {
		if (e.key !== 'Escape') return;
		if (removingAgent && !removing) removingAgent = null;
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

<!-- Fiche « Voir ses compétences » (mission + intégrations recommandées) — composant partagé -->
<AgentSkillsModal
	template={previewTemplate}
	on:close={() => (previewTemplate = null)}
	on:adopt={(e) => installTemplate(e.detail)}
/>

<AgentAtelier bind:show={showAtelier} used={usedAvatarIds} on:created={load} />
<AgentCreate bind:show={showCreate} on:created={load} />
<AgentEditor
	bind:show={showEditor}
	agent={editing}
	used={usedAvatarIds}
	on:updated={load}
	on:deleted={load}
/>
