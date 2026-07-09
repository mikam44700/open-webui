<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	import { getChatList } from '$lib/apis/chats';
	import { updateFolderById } from '$lib/apis/folders';

	import {
		config,
		user,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		chats,
		currentChatPage
	} from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import { WORKFLOWS } from '$lib/catalog/workflows';
	import { resolveAgentView, type AgentView, type ActionCard } from '$lib/catalog/agentActions';
	import { getAgents } from '$lib/apis/agents';
	import { activeAgent as activeAgentStore } from '$lib/stores/agent';
	import { avatarColor } from '$lib/components/agents/avatar-colors';
	import { avatarImgFallback } from '$lib/utils/agentIdentity';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import FolderTitle from './Placeholder/FolderTitle.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Clic sur une carte d'action : pré-remplit le chat avec le prompt (l'utilisateur relit puis
	// envoie — honnêteté D27). `setText` est LA méthode qui met à jour l'éditeur (idem clic natif) ;
	// on n'appelle PAS submit, donc aucun envoi automatique.
	const selectWorkflow = (p: string) => {
		if (messageInput?.setText) {
			messageInput.setText(p);
		} else {
			prompt = p; // repli : au moins le brouillon est posé
		}
	};

	// « Votre équipe » : le client peut masquer la section (choix mémorisé), et la rappeler
	// via une petite puce « + Votre équipe ».
	const TEAM_HIDDEN_KEY = 'lunaria-team-hidden';
	let teamHidden = false;
	onMount(() => {
		teamHidden = localStorage.getItem(TEAM_HIDDEN_KEY) === 'true';
	});
	const hideTeam = () => {
		teamHidden = true;
		localStorage.setItem(TEAM_HIDDEN_KEY, 'true');
	};
	const showTeam = () => {
		teamHidden = false;
		localStorage.removeItem(TEAM_HIDDEN_KEY);
	};

	// Agent actif (ex. Emma) : son accueil (avatar + prénom + rôle) et ses cartes d'action
	// remplacent l'accueil générique. Repli silencieux si le pont ne répond pas.
	let activeAgent: AgentView | null = null;

	// « Votre équipe » : chaque agent activé, incarné (visage + couleur propre) AVEC ses suggestions
	// de tâches (tirées de sa mission). Cliquer une suggestion pré-remplit le chat (Mike orchestre).
	type TeamCard = {
		name: string;
		firstName: string;
		role: string;
		avatar: string; // corps entier (repli)
		face: string; // gros plan visage pour le cercle du header
		gradient: string;
		active: boolean;
		actions: ActionCard[];
	};
	let teamCards: TeamCard[] = [];

	// (Re)charge l'accueil incarné : agent actif + « Votre équipe ». Appelé au montage ET à
	// chaque changement d'agent actif (via le sélecteur de la barre) pour rester synchrone.
	const loadTeam = async () => {
		try {
			const res = await getAgents(localStorage.token);
			const list = (res?.agents ?? []) as any[];
			activeAgent = resolveAgentView(list.find((x) => x?.active));
			teamCards = list
				.map((ag): TeamCard | null => {
					const v = resolveAgentView(ag);
					if (!v) return null;
					return {
						name: v.name,
						firstName: v.firstName,
						role: v.role,
						avatar: v.avatar,
						face: v.face,
						gradient: avatarColor(v.avatar || v.name).gradient,
						active: !!ag?.active,
						actions: v.actions
					};
				})
				.filter((c): c is TeamCard => c !== null)
				// N'afficher que les agents qui ont des suggestions à proposer (honnêteté).
				.filter((c) => c.actions.length > 0)
				// Agent actif d'abord, puis Mike (orchestrateur, profil « default »), puis le reste.
				.sort(
					(a, b) =>
						Number(b.active) - Number(a.active) ||
						Number(b.name === 'default') - Number(a.name === 'default')
				);
		} catch {
			activeAgent = null;
			teamCards = [];
		}
	};

	onMount(loadTeam);

	// Réagit au changement d'agent actif (sélecteur de la barre) : on recharge l'accueil pour
	// que « Bonjour, je suis … » et l'ordre de « Votre équipe » suivent le nouvel interlocuteur.
	let lastActiveName: string | null | undefined = undefined;
	$: {
		const n = $activeAgentStore?.name ?? null;
		if (lastActiveName !== undefined && n !== lastActiveName) {
			void loadTeam();
		}
		lastActiveName = n;
	}

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];
	export let messageInput = null;

	export let selectedToolIds = [];
	export let selectedSkillIds = [];
	export let selectedFilterIds = [];
	export let pendingOAuthTools = [];

	export let showCommands = false;

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let onUpload: Function = (e) => {};
	export let onSelect = (e) => {};
	export let onChange = (e) => {};

	export let toolServers = [];

	export let dragged = false;

	let models = [];
	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));

	// Cartes affichées : celles de l'agent actif si disponibles, sinon le catalogue générique.
	$: cards = activeAgent && activeAgent.actions.length ? activeAgent.actions : WORKFLOWS;

	// Dégradé de couleur de l'agent actif : posé en fond du cercle d'accueil (le visage est
	// détouré) pour le mettre en valeur comme sur sa carte « Votre équipe ».
	$: activeGradient = activeAgent ? avatarColor(activeAgent.avatar || activeAgent.name).gradient : '';
</script>

<div class="m-auto w-full max-w-6xl px-2 @2xl:px-20 translate-y-6 py-24 text-center">
	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
			className="w-full flex justify-center mb-0.5"
			placement="top"
		>
			<div class="flex items-center gap-2 text-gray-500 text-base my-2 w-fit">
				<EyeSlash strokeWidth="2.5" className="size-4" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div
		class="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary"
	>
		<div class="w-full flex flex-col justify-center items-center">
			{#if $selectedFolder}
				<FolderTitle
					folder={$selectedFolder}
					onUpdate={async (folder) => {
						await chats.set(await getChatList(localStorage.token, $currentChatPage));
						currentChatPage.set(1);
					}}
					onDelete={async () => {
						await chats.set(await getChatList(localStorage.token, $currentChatPage));
						currentChatPage.set(1);

						selectedFolder.set(null);
					}}
				/>
			{:else if activeAgent}
				<!-- Accueil personnalisé par l'agent actif (ex. Emma) : avatar + rôle + prénom. -->
				<div
					class="flex flex-row justify-center items-center gap-3 w-fit px-5 max-w-xl"
					in:fade={{ duration: 100 }}
				>
					<img
						src={activeAgent.face}
						alt={activeAgent.firstName}
						style="background-image: {activeGradient}"
						class="size-14 rounded-full object-cover ring-2 ring-white/30 shadow-sm shrink-0"
						draggable="false"
						on:error={(e) => avatarImgFallback(e, activeAgent?.avatar)}
					/>
					<div class="text-left min-w-0">
						{#if activeAgent.role}
							<div
								class="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400 dark:text-gray-500"
							>
								{activeAgent.role}
							</div>
						{/if}
						<div
							class="text-2xl @sm:text-3xl font-medium tracking-tight text-gray-800 dark:text-gray-100 line-clamp-1"
						>
							{$i18n.t('Bonjour, je suis {{name}}', { name: activeAgent.firstName })}
						</div>
					</div>
				</div>

				{#if activeAgent.description}
					<div class="flex mt-1.5 mb-2" in:fade={{ duration: 100, delay: 50 }}>
						<p
							class="px-2 text-sm font-normal text-gray-500 dark:text-gray-400 line-clamp-2 max-w-xl text-center"
						>
							{activeAgent.description}
						</p>
					</div>
				{/if}
			{:else}
				<div class="flex flex-row justify-center gap-2.5 @sm:gap-3 w-fit px-5 max-w-xl">
					<div class="flex shrink-0 justify-center">
						<div class="flex -space-x-4 mb-0.5" in:fade={{ duration: 100 }}>
							{#each models as model, modelIdx}
								<Tooltip
									content={(models[modelIdx]?.info?.meta?.tags ?? [])
										.map((tag) => tag.name.toUpperCase())
										.join(', ')}
									placement="top"
								>
									<button
										aria-hidden={models.length <= 1}
										aria-label={$i18n.t('Get information on {{name}} in the UI', {
											name: models[modelIdx]?.name
										})}
										on:click={() => {
											selectedModelIdx = modelIdx;
										}}
									>
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}`}
											class=" size-9 @sm:size-10 rounded-full border-[1px] border-gray-100 dark:border-none"
											aria-hidden="true"
											draggable="false"
											on:error={(e) => {
												e.currentTarget.src = '/favicon.png';
											}}
										/>
									</button>
								</Tooltip>
							{/each}
						</div>
					</div>

					<div
						class=" text-3xl @sm:text-3xl line-clamp-1 flex items-center"
						in:fade={{ duration: 100 }}
					>
						{$i18n.t('Hello, {{name}}', { name: ($user?.name ?? '').split(' ')[0] })}
					</div>
				</div>

				<div class="flex mt-1 mb-2">
					<div in:fade={{ duration: 100, delay: 50 }}>
						{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
							<Tooltip
								className=" w-fit"
								content={DOMPurify.sanitize(
									marked.parse(
										sanitizeResponseContent(
											models[selectedModelIdx]?.info?.meta?.description ?? ''
										).replaceAll('\n', '<br>')
									)
								)}
								placement="top"
							>
								<div
									class="mt-0.5 px-2 text-sm font-normal text-gray-500 dark:text-gray-400 line-clamp-2 max-w-xl markdown"
								>
									{@html DOMPurify.sanitize(
										marked.parse(
											sanitizeResponseContent(
												models[selectedModelIdx]?.info?.meta?.description ?? ''
											).replaceAll('\n', '<br>')
										)
									)}
								</div>
							</Tooltip>

						{/if}
					</div>
				</div>
			{/if}

			<div class="text-base font-normal @md:max-w-3xl w-full py-3 {atSelectedModel ? 'mt-2' : ''}">
				<MessageInput
					bind:this={messageInput}
					{history}
					{selectedModels}
					bind:files
					bind:prompt
					bind:autoScroll
					bind:selectedToolIds
					bind:selectedSkillIds
					bind:selectedFilterIds
					bind:imageGenerationEnabled
					bind:codeInterpreterEnabled
					bind:webSearchEnabled
					bind:atSelectedModel
					bind:showCommands
					bind:dragged
					{pendingOAuthTools}
					{toolServers}
					{stopResponse}
					{createMessagePair}
					placeholder={$i18n.t('How can I help you today?')}
					{onChange}
					{onUpload}
					on:submit={(e) => {
						dispatch('submit', e.detail);
					}}
				/>
			</div>
		</div>
	</div>

	{#if $selectedFolder}
		<div
			class="mx-auto px-4 md:max-w-3xl md:px-6 font-primary min-h-62"
			in:fade={{ duration: 200, delay: 200 }}
		>
			<FolderPlaceholder folder={$selectedFolder} />
		</div>
	{:else}
		<!-- Cartes d'action (catalogue métier) : pré-remplissent le chat au clic. Remplace l'ancienne
		     boîte « Je peux vous aider » + les suggestions natives. Masquables (choix mémorisé). -->
		<div class="mx-auto max-w-3xl font-primary mt-3 px-5" in:fade={{ duration: 200, delay: 200 }}>
			<!-- « Votre équipe » : les agents activés, incarnés (visage + couleur). Clic = amorce Mike-first.
			     Masquable via la croix (choix mémorisé) → rappelable par la puce « + Votre équipe ». -->
			{#if teamCards.length && teamHidden}
				<div class="flex justify-center">
					<button
						type="button"
						class="flex items-center gap-1.5 text-xs font-medium text-gray-400 dark:text-gray-500 px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={showTeam}
					>
						<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"
							><path
								d="M7 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7-1.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM1.5 16.2C1.5 13.4 4 12 7 12s5.5 1.4 5.5 4.2c0 .4-.3.8-.8.8H2.3c-.5 0-.8-.4-.8-.8Zm12.2.8c.2-.5.3-1 .3-1.8 0-1.3-.5-2.4-1.2-3.2.3-.1.6-.1 1-.1 2.3 0 4.2 1.1 4.2 3.3 0 .5-.3.9-.8.9h-2.9c-.1 0-.2 0-.3-.1l-.3-.6Z"
							/></svg
						>
						{$i18n.t('Votre équipe')}
					</button>
				</div>
			{:else if teamCards.length}
				<div class="mb-4">
					<div
						class="flex items-center justify-between gap-1.5 text-xs font-medium text-gray-400 dark:text-gray-500 mb-2.5"
					>
						<span class="flex items-center gap-1.5">
							<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"
								><path
									d="M7 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7-1.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM1.5 16.2C1.5 13.4 4 12 7 12s5.5 1.4 5.5 4.2c0 .4-.3.8-.8.8H2.3c-.5 0-.8-.4-.8-.8Zm12.2.8c.2-.5.3-1 .3-1.8 0-1.3-.5-2.4-1.2-3.2.3-.1.6-.1 1-.1 2.3 0 4.2 1.1 4.2 3.3 0 .5-.3.9-.8.9h-2.9c-.1 0-.2 0-.3-.1l-.3-.6Z"
								/></svg
							>
							{$i18n.t('Votre équipe')}
						</span>
						<button
							type="button"
							class="flex-none p-1 -mr-1 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={hideTeam}
							title={$i18n.t('Masquer votre équipe')}
							aria-label={$i18n.t('Masquer votre équipe')}
						>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
								<path
									d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
								/>
							</svg>
						</button>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-left">
						{#each teamCards as c (c.name)}
							<div
								class="rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm"
							>
								<!-- En-tête neutre : la couleur de l'agent est portée par le cercle seul. -->
								<div
									class="flex items-center gap-2.5 px-3 py-2.5 border-b border-gray-100 dark:border-gray-800"
								>
									<img
										src={c.face}
										alt={c.firstName}
										style="background-image: {c.gradient}"
										class="size-9 rounded-full object-cover ring-1 ring-black/5 dark:ring-white/10 shrink-0"
										draggable="false"
										on:error={(e) => avatarImgFallback(e, c.avatar)}
									/>
									<span class="flex flex-col min-w-0">
										<span class="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate"
											>{c.firstName}</span
										>
										{#if c.role}<span class="text-[11px] text-gray-500 dark:text-gray-400 truncate"
												>{c.role}</span
											>{/if}
									</span>
								</div>
								<!-- Ses suggestions (tirées de sa mission) : clic = pré-remplit le chat. -->
								<div class="p-1.5 flex flex-col">
									{#each c.actions as a (a.id)}
										<button
											type="button"
											class="flex items-center gap-1.5 text-left text-sm px-2.5 py-1.5 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-300 dark:focus-visible:ring-gray-700 transition"
											on:click={() => selectWorkflow(a.prompt)}
										>
											<span class="text-gray-300 dark:text-gray-600">›</span>
											<span class="truncate">{$i18n.t(a.label)}</span>
										</button>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
