<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';

	import {
		config,
		user,
		tools as _tools,
		skills as _skills,
		mobile,
		settings,
		toolServers,
		terminalServers
	} from '$lib/stores';

	import { getOAuthClientAuthorizationUrl } from '$lib/apis/configs';
	import { deleteOAuthSession } from '$lib/apis/auths';
	import { goto } from '$app/navigation';
	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';
	import { getIntegrations } from '$lib/apis/integrations';
	import { getConnectors } from '$lib/apis/connectors';
	import { INTEGRATION_FR } from '$lib/utils/integrationLabels';
	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';

	import { toast } from 'svelte-sonner';

	import Knobs from '$lib/components/icons/Knobs.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import Keyframes from '$lib/components/icons/Keyframes.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LinkSlash from '$lib/components/icons/LinkSlash.svelte';

	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onShowValves: Function;
	export let onClose: Function;
	export let closeOnOutsideClick = true;

	let show = false;
	let tab = '';

	let tools = null;
	let skills = null;

	// Récapitulatif « Mes connexions » (lecture seule) : QUELLES intégrations et quels
	// connecteurs MCP sont branchés, par leur NOM (plus parlant qu'un compteur pour un
	// dirigeant non-tech). Chargé à l'ouverture du menu ; masqué sans bruit si l'API
	// échoue (droits insuffisants, etc.).
	let connectionsLoaded = false;
	let integrationsConnected = 0;
	let integrationsTotal = 0;
	let mcpConnected = 0;
	let mcpTotal = 0;
	let integrationsConnectedNames: string[] = [];
	let mcpConnectedNames: string[] = [];

	$: if (show) {
		init();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const init = async () => {
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		if ($_tools) {
			tools = $_tools.reduce((a, tool, i, arr) => {
				a[tool.id] = {
					name: tool.name,
					description: tool.meta.description,
					enabled: selectedToolIds.includes(tool.id),
					...tool
				};
				return a;
			}, {});
		}

		if ($toolServers) {
			for (const serverIdx in $toolServers) {
				const server = $toolServers[serverIdx];
				if (server.info) {
					tools[`direct_server:${serverIdx}`] = {
						name: server?.info?.title ?? server.url,
						description: server.info.description ?? '',
						enabled: selectedToolIds.includes(`direct_server:${serverIdx}`)
					};
				}
			}
		}

		selectedToolIds = selectedToolIds.filter((id) => Object.keys(tools).includes(id));

		if ($_skills === null) {
			await _skills.set(await getSkills(localStorage.token));
		}

		if ($_skills) {
			skills = $_skills
				.filter((skill) => skill.is_active)
				.reduce((a, skill) => {
					a[skill.id] = {
						name: skill.name,
						description: skill.description,
						enabled: selectedSkillIds.includes(skill.id),
						...skill
					};
					return a;
				}, {});
		}

		selectedSkillIds = selectedSkillIds.filter((id) => Object.keys(skills ?? {}).includes(id));

		// État « Mes connexions » : mêmes sources de vérité que la page Capacités
		// (intégrations + connecteurs MCP). Non bloquant — en cas d'erreur on masque la section.
		try {
			const intRes = await getIntegrations(localStorage.token);
			const intList = Array.isArray(intRes) ? intRes : (intRes?.integrations ?? []);
			const intVisible = intList.filter((i) => i?.visible !== false);
			integrationsTotal = intVisible.length;
			const intConnected = intVisible.filter(
				(i) => i?.state === 'connected' || i?.state === 'key_present'
			);
			integrationsConnected = intConnected.length;
			// Nom francisé (« Google », « Notion »…) plutôt que l'id technique.
			integrationsConnectedNames = intConnected.map(
				(i) => INTEGRATION_FR[i.id]?.name ?? i.name ?? i.id
			);

			const connRes = await getConnectors(localStorage.token);
			const connList = connRes?.connectors ?? [];
			mcpTotal = connList.length;
			const connConnected = connList.filter((c) => c?.state === 'connected');
			mcpConnected = connConnected.length;
			mcpConnectedNames = connConnected.map((c) => CONNECTOR_FR[c.id]?.name ?? c.name ?? c.id);

			connectionsLoaded = true;
		} catch (e) {
			connectionsLoaded = false;
		}
	};
</script>

<Dropdown
	bind:show
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Capacités')} placement="top">
		<slot />
	</Tooltip>
	<div slot="content">
		<div
			class="min-w-70 max-w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
		>
			{#if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }}>
					{#if tools}
						{#if Object.keys(tools).length > 0}
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									tab = 'tools';
								}}
							>
								<Wrench />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Outils')}
										<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
									</div>

									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>
						{/if}

						{#if skills && Object.keys(skills).length > 0}
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									tab = 'skills';
								}}
							>
								<Keyframes className="size-4" strokeWidth="1.75" />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Compétences')}
										<span class="ml-0.5 text-gray-500">{Object.keys(skills).length}</span>
									</div>

									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>
						{/if}
					{:else}
						<div class="py-4">
							<Spinner />
						</div>
					{/if}

					{#if toggleFilters && toggleFilters.length > 0}
						{#each toggleFilters.sort( (a, b) => a.name.localeCompare( b.name, undefined, { sensitivity: 'base' } ) ) as filter, filterIdx (filter.id)}
							<Tooltip content={filter?.description} placement="top-start">
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									on:click={() => {
										if (selectedFilterIds.includes(filter.id)) {
											selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
										} else {
											selectedFilterIds = [...selectedFilterIds, filter.id];
										}
									}}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												{#if filter?.icon}
													<div class="size-4 items-center flex justify-center">
														<img
															src={filter.icon}
															class="size-3.5 {filter.icon.includes('data:image/svg')
																? 'dark:invert-[80%]'
																: ''}"
															style="fill: currentColor;"
															alt={filter.name}
														/>
													</div>
												{:else}
													<Sparkles className="size-4" strokeWidth="1.75" />
												{/if}
											</div>

											<div class=" truncate">{filter?.name}</div>
										</div>
									</div>

									{#if filter?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
										<div class=" shrink-0">
											<Tooltip content={$i18n.t('Réglages')}>
												<button
													class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
													type="button"
													on:click={(e) => {
														e.stopPropagation();
														e.preventDefault();
														onShowValves({
															type: 'function',
															id: filter.id
														});
													}}
												>
													<Knobs />
												</button>
											</Tooltip>
										</div>
									{/if}

									<div class=" shrink-0">
										<Switch
											state={selectedFilterIds.includes(filter.id)}
											on:change={async (e) => {
												const state = e.detail;
												await tick();
											}}
										/>
									</div>
								</button>
							</Tooltip>
						{/each}
					{/if}

					{#if showWebSearchButton}
						<Tooltip content={$i18n.t('Rechercher sur Internet')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									webSearchEnabled = !webSearchEnabled;
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<GlobeAlt />
										</div>

										<div class=" truncate">{$i18n.t('Recherche web')}</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={webSearchEnabled}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if showImageGenerationButton}
						<Tooltip content={$i18n.t("Générer une image")} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									imageGenerationEnabled = !imageGenerationEnabled;
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Photo className="size-4" strokeWidth="1.5" />
										</div>

										<div class=" truncate">{$i18n.t("Génération d'image")}</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={imageGenerationEnabled}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if showCodeInterpreterButton}
						<Tooltip content={$i18n.t('Exécuter du code pour analyser des données')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								aria-pressed={codeInterpreterEnabled}
								aria-label={codeInterpreterEnabled
									? $i18n.t("Désactiver l'exécution de code")
									: $i18n.t("Activer l'exécution de code")}
								on:click={() => {
									codeInterpreterEnabled = !codeInterpreterEnabled;
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Terminal className="size-3.5" strokeWidth="1.75" />
										</div>

										<div class=" truncate">{$i18n.t('Exécution de code')}</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={codeInterpreterEnabled}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>
					{/if}

					<!-- Mes connexions : état (branché / non branché) des intégrations et des
					     connecteurs MCP, en lecture seule, avec un raccourci vers la page complète. -->
					{#if connectionsLoaded && (integrationsTotal > 0 || mcpTotal > 0)}
						<div class="mx-2 my-1 border-t border-gray-100 dark:border-gray-800"></div>
						<div
							class="px-3 pt-1 pb-1 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500"
						>
							{$i18n.t('Mes connexions')}
						</div>

						<!-- Intégrations : titre cliquable (→ onglet) puis la LISTE des noms branchés
						     (Google, Notion…), ou un état honnête si rien n'est branché. -->
						{#if integrationsTotal > 0}
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									show = false;
									goto('/connectors?tab=integrations');
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<span
											class="shrink-0 size-2 rounded-full {integrationsConnected > 0
												? 'bg-green-500'
												: 'bg-gray-300 dark:bg-gray-600'}"
										></span>
										<div class=" truncate">{$i18n.t('Intégrations')}</div>
									</div>
								</div>
								<ChevronRight className="size-3 text-gray-400" />
							</button>

							{#if integrationsConnectedNames.length > 0}
								{#each integrationsConnectedNames as name}
									<button
										class="flex w-full items-center gap-2 pl-8 pr-3 py-1 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
										on:click={() => {
											show = false;
											goto('/connectors?tab=integrations');
										}}
									>
										<span class="shrink-0 size-1.5 rounded-full bg-green-500"></span>
										<span class=" truncate text-gray-700 dark:text-gray-200">{name}</span>
									</button>
								{/each}
							{:else}
								<div class="pl-8 pr-3 py-1 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('Aucune branchée pour l’instant')}
								</div>
							{/if}
						{/if}

						{#if mcpTotal > 0}
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									show = false;
									goto('/connectors?tab=connectors');
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<span
											class="shrink-0 size-2 rounded-full {mcpConnected > 0
												? 'bg-green-500'
												: 'bg-gray-300 dark:bg-gray-600'}"
										></span>
										<div class=" truncate">{$i18n.t('Connecteurs MCP')}</div>
									</div>
								</div>
								<ChevronRight className="size-3 text-gray-400" />
							</button>

							{#if mcpConnectedNames.length > 0}
								{#each mcpConnectedNames as name}
									<button
										class="flex w-full items-center gap-2 pl-8 pr-3 py-1 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
										on:click={() => {
											show = false;
											goto('/connectors?tab=connectors');
										}}
									>
										<span class="shrink-0 size-1.5 rounded-full bg-green-500"></span>
										<span class=" truncate text-gray-700 dark:text-gray-200">{name}</span>
									</button>
								{/each}
							{:else}
								<div class="pl-8 pr-3 py-1 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('Aucun branché pour l’instant')}
								</div>
							{/if}
						{/if}

						<button
							class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={() => {
								show = false;
								goto('/connectors?tab=integrations');
							}}
						>
							<span class=" truncate">{$i18n.t('Gérer mes connexions')}</span>
							<ChevronRight className="size-3" />
						</button>
					{/if}
				</div>
			{:else if tab === 'tools' && tools}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Outils')}
								<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
							</div>
						</div>
					</button>

					{#each Object.keys(tools) as toolId}
						<button
							class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={async (e) => {
								if (!(tools[toolId]?.authenticated ?? true)) {
									e.preventDefault();

									let parts = toolId.split(':');
									let serverId = parts?.at(-1) ?? toolId;

									// Persist the tool ID so we can re-enable it after OAuth redirect
									sessionStorage.setItem('pendingOAuthToolId', toolId);

									const authUrl = getOAuthClientAuthorizationUrl(serverId, 'mcp');
									window.open(authUrl, '_self', 'noopener');
								} else {
									tools[toolId].enabled = !tools[toolId].enabled;

									const state = tools[toolId].enabled;
									await tick();

									if (state) {
										selectedToolIds = [...selectedToolIds, toolId];
									} else {
										selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
									}
								}
							}}
						>
							{#if !(tools[toolId]?.authenticated ?? true)}
								<!-- make it slighly darker and not clickable -->
								<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10" />
							{/if}
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<Tooltip content={tools[toolId]?.name ?? ''} placement="top">
										<div class="shrink-0">
											<Wrench />
										</div>
									</Tooltip>
									<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
										<div class=" truncate">{tools[toolId].name}</div>
									</Tooltip>
								</div>
							</div>

							{#if (tools[toolId]?.authenticated ?? true) && toolId.startsWith('server:mcp:')}
								<div class="shrink-0">
									<Tooltip content={$i18n.t('Disconnect OAuth')}>
										<button
											class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
											type="button"
											on:click={async (e) => {
												e.stopPropagation();
												e.preventDefault();

												const parts = toolId.split(':');
												const serverId = parts.at(-1) ?? toolId;
												const provider = `mcp:${serverId}`;

												try {
													await deleteOAuthSession(localStorage.token, provider);
													toast.success($i18n.t('OAuth session disconnected'));

													// Refresh tools to update authenticated state
													_tools.set(await getTools(localStorage.token));
													selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
													await init();
												} catch (err) {
													toast.error(err ?? $i18n.t('Failed to disconnect'));
												}
											}}
										>
											<LinkSlash className="size-3.5" />
										</button>
									</Tooltip>
								</div>
							{/if}

							{#if tools[toolId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
								<div class=" shrink-0">
									<Tooltip content={$i18n.t('Réglages')}>
										<button
											class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
											type="button"
											on:click={(e) => {
												e.stopPropagation();
												e.preventDefault();
												onShowValves({
													type: 'tool',
													id: toolId
												});
											}}
										>
											<Knobs />
										</button>
									</Tooltip>
								</div>
							{/if}

							<div class=" shrink-0">
								<Switch state={tools[toolId].enabled} />
							</div>
						</button>
					{/each}
				</div>
			{:else if tab === 'skills' && skills}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Compétences')}
								<span class="ml-0.5 text-gray-500">{Object.keys(skills).length}</span>
							</div>
						</div>
					</button>

					{#each Object.keys(skills) as skillId}
						<button
							class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={async () => {
								skills[skillId].enabled = !skills[skillId].enabled;

								const state = skills[skillId].enabled;
								await tick();

								if (state) {
									selectedSkillIds = [...selectedSkillIds, skillId];
								} else {
									selectedSkillIds = selectedSkillIds.filter((id) => id !== skillId);
								}
							}}
						>
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<Tooltip content={skills[skillId]?.name ?? ''} placement="top">
										<div class="shrink-0">
											<Keyframes className="size-4" strokeWidth="1.75" />
										</div>
									</Tooltip>
									<Tooltip content={skills[skillId]?.description ?? ''} placement="top-start">
										<div class=" truncate">{skills[skillId].name}</div>
									</Tooltip>
								</div>
							</div>

							<div class=" shrink-0">
								<Switch state={skills[skillId].enabled} />
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
