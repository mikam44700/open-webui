<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	import Switch from '$lib/components/common/Switch.svelte';
	import { TOOLSET_FR } from '$lib/utils/toolsetLabels';
	import { expertMode } from '$lib/stores';

	import webLogo from '$lib/assets/toolsets/web.jpg';
	import browserLogo from '$lib/assets/toolsets/browser.jpg';
	import terminalLogo from '$lib/assets/toolsets/terminal.jpg';
	import fileLogo from '$lib/assets/toolsets/file.jpg';
	import codeExecutionLogo from '$lib/assets/toolsets/code_execution.jpg';
	import computerUseLogo from '$lib/assets/toolsets/computer_use.jpg';
	import visionLogo from '$lib/assets/toolsets/vision.jpg';
	import videoLogo from '$lib/assets/toolsets/video.jpg';
	import imageGenLogo from '$lib/assets/toolsets/image_gen.jpg';
	import videoGenLogo from '$lib/assets/toolsets/image_gen_alt.jpg';
	import xSearchLogo from '$lib/assets/toolsets/x_search.jpg';
	import moaLogo from '$lib/assets/toolsets/moa.jpg';
	import ttsLogo from '$lib/assets/toolsets/tts.jpg';
	import skillsLogo from '$lib/assets/toolsets/skills.jpg';
	import todoLogo from '$lib/assets/toolsets/todo.jpg';
	import memoryLogo from '$lib/assets/toolsets/memory.jpg';
	import contextEngineLogo from '$lib/assets/toolsets/context_engine.jpg';
	import sessionSearchLogo from '$lib/assets/toolsets/session_search.jpg';
	import clarifyLogo from '$lib/assets/toolsets/clarify.jpg';
	import delegationLogo from '$lib/assets/toolsets/delegation.jpg';
	import cronjobLogo from '$lib/assets/toolsets/cronjob.jpg';
	import homeassistantLogo from '$lib/assets/toolsets/homeassistant.jpg';
	import spotifyLogo from '$lib/assets/toolsets/spotify.jpg';
	import discordLogo from '$lib/assets/toolsets/discord.jpg';
	import discordAdminLogo from '$lib/assets/toolsets/discord_admin.jpg';
	import yuanbaoLogo from '$lib/assets/toolsets/yuanbao.jpg';

	const LOGO_BY_ID: Record<string, string> = {
		web: webLogo,
		browser: browserLogo,
		terminal: terminalLogo,
		file: fileLogo,
		code_execution: codeExecutionLogo,
		computer_use: computerUseLogo,
		vision: visionLogo,
		video: videoLogo,
		image_gen: imageGenLogo,
		video_gen: videoGenLogo,
		x_search: xSearchLogo,
		moa: moaLogo,
		tts: ttsLogo,
		skills: skillsLogo,
		todo: todoLogo,
		memory: memoryLogo,
		context_engine: contextEngineLogo,
		session_search: sessionSearchLogo,
		clarify: clarifyLogo,
		delegation: delegationLogo,
		cronjob: cronjobLogo,
		homeassistant: homeassistantLogo,
		spotify: spotifyLogo,
		discord: discordLogo,
		discord_admin: discordAdminLogo,
		yuanbao: yuanbaoLogo
	};

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let toolset: {
		name: string;
		label: string;
		description?: string;
		tools?: string[];
		enabled: boolean;
		connection_state?: string;
		providers?: string[];
	};

	let expanded = false;

	$: fr = TOOLSET_FR[toolset.name];
	$: displayLabel = fr?.label ?? toolset.label;
	$: displayDesc = fr?.desc ?? toolset.description ?? '';
	$: providers = toolset.providers ?? [];
	$: logoSrc = LOGO_BY_ID[toolset.name];
	// Avec un logo, on retire l'emoji en tête du libellé pour éviter le doublon.
	$: labelText = logoSrc ? displayLabel.replace(/^\S+\s+/, '') : displayLabel;

	$: needsConnection = toolset.connection_state === 'connection_required';
	$: isConnected = toolset.connection_state === 'connected';
	$: connectable = needsConnection || isConnected;
	// FR-013 : toolset activé mais connexion manquante → avertir.
	$: warnMissing = toolset.enabled && needsConnection;
	// La carte n'est dépliable que si elle a du contenu à montrer.
	$: hasDetails = providers.length > 0 || connectable;
	// « Voir les services » (déplier + détail des fournisseurs) est réservé aux Réglages
	// avancés : le dirigeant non-tech ne voit que la capacité + son interrupteur.
	$: canExpand = hasDetails && $expertMode;
	$: if (!$expertMode) expanded = false;

	const toggle = () => {
		if (canExpand) expanded = !expanded;
	};
</script>

<div
	class="border border-gray-100 dark:border-gray-850 rounded-2xl px-5 py-4 h-full transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm {canExpand
		? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-white/[0.03]'
		: ''}"
	role={canExpand ? 'button' : undefined}
	tabindex={canExpand ? 0 : undefined}
	on:click={toggle}
	on:keydown={(e) => {
		if (canExpand && (e.key === 'Enter' || e.key === ' ')) {
			e.preventDefault();
			toggle();
		}
	}}
>
	<div class="flex items-start gap-4">
		{#if logoSrc}
			<div
				class="size-12 flex-none rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center"
			>
				<img src={logoSrc} alt="" class="w-full h-full object-cover" />
			</div>
		{/if}

		<div class="flex-1 min-w-0">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0 flex items-center gap-2 flex-wrap pt-1">
					<span class="text-base font-medium">{labelText}</span>
					{#if needsConnection}
						<span
							class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400"
							>{$i18n.t('Connexion requise')}</span
						>
					{/if}
				</div>

				<div class="flex items-center gap-2 flex-none pt-0.5">
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div on:click|stopPropagation on:keydown|stopPropagation>
						<Switch state={toolset.enabled} on:change={() => dispatch('toggle')} />
					</div>
				</div>
			</div>

			{#if displayDesc}
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1.5 leading-relaxed">
					{displayDesc}
				</div>
			{/if}

			{#if warnMissing}
				<div class="text-xs text-amber-600 dark:text-amber-400 mt-2">
					{$i18n.t('Activé mais non connecté : configure la connexion pour qu’il fonctionne.')}
				</div>
			{/if}

			{#if canExpand && !expanded}
				<div class="text-xs font-medium text-sky-600 dark:text-sky-400 mt-2.5">
					{$i18n.t('Voir les services')} ›
				</div>
			{/if}

			{#if expanded}
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<div
					class="mt-4 border-t border-gray-100 dark:border-gray-850 pt-4"
					on:click|stopPropagation
					on:keydown|stopPropagation
				>
					{#if providers.length > 0}
						<div class="text-[11px] font-medium text-gray-400 mb-2 uppercase tracking-wide">
							{$i18n.t('Services disponibles')}
						</div>
						<div class="flex flex-wrap gap-1.5">
							{#each providers as provider (provider)}
								<span
									class="text-xs px-2.5 py-1 rounded-lg bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
									>{provider}</span
								>
							{/each}
						</div>
					{/if}

					<div class="flex items-center gap-3 mt-4">
						{#if connectable}
							<button
								type="button"
								class="text-xs px-3.5 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => dispatch('connect')}
							>
								{isConnected ? $i18n.t('Gérer la connexion') : $i18n.t('Connecter')}
							</button>
						{/if}
						<button
							type="button"
							class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
							on:click={() => (expanded = false)}
						>
							{$i18n.t('Masquer')}
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
