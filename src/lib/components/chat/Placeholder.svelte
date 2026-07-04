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
	import { resolveAgentView, type AgentView } from '$lib/catalog/agentActions';
	import { getAgents } from '$lib/apis/agents';
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

	// Raccourcis « Pour démarrer » : le client peut les masquer (choix mémorisé), et les rappeler.
	const STARTERS_HIDDEN_KEY = 'hermes-starters-hidden';
	let startersHidden = false;
	onMount(() => {
		startersHidden = localStorage.getItem(STARTERS_HIDDEN_KEY) === 'true';
	});
	const hideStarters = () => {
		startersHidden = true;
		localStorage.setItem(STARTERS_HIDDEN_KEY, 'true');
	};
	const showStarters = () => {
		startersHidden = false;
		localStorage.removeItem(STARTERS_HIDDEN_KEY);
	};

	// Agent actif (ex. Emma) : son accueil (avatar + prénom + rôle) et ses cartes d'action
	// remplacent l'accueil générique. Repli silencieux si le pont ne répond pas.
	let activeAgent: AgentView | null = null;
	onMount(async () => {
		try {
			const res = await getAgents(localStorage.token);
			const a = (res?.agents ?? []).find((x: any) => x?.active);
			activeAgent = resolveAgentView(a);
		} catch {
			activeAgent = null;
		}
	});

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
						src={activeAgent.avatar}
						alt={activeAgent.firstName}
						class="size-14 rounded-full object-cover border border-gray-100 dark:border-gray-800 shadow-sm shrink-0"
						draggable="false"
						on:error={(e) => {
							e.currentTarget.src = '/favicon.png';
						}}
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
			{#if startersHidden}
				<div class="text-center">
					<button
						type="button"
						class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
						on:click={showStarters}
					>
						{$i18n.t('Afficher les raccourcis')}
					</button>
				</div>
			{:else}
				<div class="flex items-center justify-between mb-2.5">
					<div class="flex items-center gap-1.5 text-xs font-medium text-gray-400 dark:text-gray-500">
						<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"><path d="M11 2.5 4 11h4.2l-1 6.5L15 9h-4.2l1-6.5Z"/></svg>
						{activeAgent && activeAgent.actions.length
							? $i18n.t('Pour démarrer avec {{name}}', { name: activeAgent.firstName })
							: $i18n.t('Pour démarrer')}
					</div>
					<button
						type="button"
						class="p-1 -mr-1 rounded-md text-gray-300 dark:text-gray-600 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						aria-label={$i18n.t('Masquer les raccourcis')}
						title={$i18n.t('Masquer les raccourcis')}
						on:click={hideStarters}
					>
						<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"/></svg>
					</button>
				</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-left">
					{#each cards as w (w.id)}
						<button
							type="button"
							class="group flex items-start gap-2.5 px-3.5 py-3 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:-translate-y-0.5 hover:shadow-[0_2px_10px_rgba(0,0,0,0.05)] hover:border-gray-300 dark:hover:border-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-300 dark:focus-visible:ring-gray-700 transition-all duration-200"
							on:click={() => selectWorkflow(w.prompt)}
						>
							{#if w.image}
								<span
									class="shrink-0 w-7 h-7 mt-0.5 rounded-md overflow-hidden bg-white dark:bg-gray-800 ring-1 ring-gray-100 dark:ring-gray-800 flex items-center justify-center"
								>
									<img src={w.image} alt="" class="w-full h-full object-cover" draggable="false" />
								</span>
							{:else}
								<span class="text-lg leading-none mt-0.5">{w.icon}</span>
							{/if}
							<span class="flex flex-col min-w-0">
								<span class="text-sm font-medium text-gray-900 dark:text-white truncate"
									>{$i18n.t(w.label)}</span
								>
								<span class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 leading-snug"
									>{$i18n.t(w.description)}</span
								>
							</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
