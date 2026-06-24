<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	import Switch from '$lib/components/common/Switch.svelte';

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

	// Libellés + descriptions FR (orientés client, sans jargon technique). Source de vérité
	// = Hermes pour les capacités ; ici on ne fait que présenter clairement en français.
	const FR: Record<string, { label: string; desc: string }> = {
		web: { label: '🔍 Recherche & web', desc: 'Cherche sur le web et extrait le contenu des pages.' },
		browser: { label: '🌐 Navigateur automatisé', desc: 'Pilote un navigateur : naviguer, cliquer, remplir, faire défiler.' },
		terminal: { label: '💻 Terminal & processus', desc: 'Exécute des commandes et gère des processus système.' },
		file: { label: '📁 Fichiers', desc: 'Lit, écrit, modifie et recherche dans des fichiers.' },
		code_execution: { label: '⚡ Exécution de code', desc: 'Exécute du code dans un environnement isolé.' },
		vision: { label: '👁️ Vision / analyse d’image', desc: 'Analyse et décrit des images.' },
		video: { label: '🎬 Analyse vidéo', desc: 'Analyse et comprend des vidéos (modèle compatible requis).' },
		image_gen: { label: '🎨 Génération d’images', desc: 'Crée des images à partir d’une description.' },
		video_gen: { label: '🎬 Génération de vidéos', desc: 'Crée des vidéos à partir d’un texte ou d’une image.' },
		x_search: { label: '🐦 Recherche X (Twitter)', desc: 'Recherche des posts et fils sur X (Twitter).' },
		moa: { label: '🧠 Mélange d’agents', desc: 'Combine plusieurs modèles pour de meilleures réponses.' },
		tts: { label: '🔊 Synthèse vocale', desc: 'Convertit du texte en voix.' },
		skills: { label: '📚 Compétences', desc: 'Liste, consulte et gère les compétences de l’agent.' },
		todo: { label: '📋 Planification de tâches', desc: 'Crée et suit une liste de tâches.' },
		memory: { label: '💾 Mémoire', desc: 'Mémoire persistante entre les sessions.' },
		context_engine: { label: '🧩 Moteur de contexte', desc: 'Outils dynamiques du moteur de contexte actif.' },
		session_search: { label: '🔎 Recherche de sessions', desc: 'Recherche dans les conversations passées.' },
		clarify: { label: '❓ Questions de clarification', desc: 'Pose des questions pour lever les ambiguïtés.' },
		delegation: { label: '👥 Délégation de tâches', desc: 'Délègue des tâches à des sous-agents.' },
		cronjob: { label: '⏰ Tâches planifiées', desc: 'Programme des tâches récurrentes (cron).' },
		homeassistant: { label: '🏠 Maison connectée', desc: 'Pilote des appareils domotiques via Home Assistant.' },
		spotify: { label: '🎵 Spotify', desc: 'Lecture, recherche, playlists et bibliothèque Spotify.' },
		discord: { label: '💬 Discord', desc: 'Lit et participe aux conversations Discord.' },
		discord_admin: { label: '🛡️ Administration Discord', desc: 'Gère salons, rôles et messages d’un serveur Discord.' },
		yuanbao: { label: '🤖 Yuanbao', desc: 'Infos de groupe, membres et messages privés Yuanbao.' },
		computer_use: { label: '🖱️ Contrôle de l’ordinateur', desc: 'Contrôle le bureau : souris, clavier, captures d’écran.' }
	};

	$: fr = FR[toolset.name];
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
</script>

<div class="border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3">
	<div class="flex items-start gap-3">
		<button
			type="button"
			class="flex-1 min-w-0 text-left"
			on:click={() => (expanded = !expanded)}
			aria-expanded={expanded}
		>
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-400">{expanded ? '▾' : '▸'}</span>
				{#if logoSrc}
					<img src={logoSrc} alt="" class="size-5 rounded object-contain flex-none" />
				{/if}
				<span class="text-sm font-medium truncate">{labelText}</span>
				{#if isConnected}
					<span
						class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
						>{$i18n.t('Connecté')}</span
					>
				{:else if needsConnection}
					<span
						class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400"
						>{$i18n.t('Connexion requise')}</span
					>
				{/if}
			</div>
			{#if displayDesc}
				<div class="text-xs text-gray-500 mt-0.5 line-clamp-2 pl-5">{displayDesc}</div>
			{/if}
		</button>
		<div class="flex-none self-center">
			<Switch state={toolset.enabled} on:change={() => dispatch('toggle')} />
		</div>
	</div>

	{#if warnMissing}
		<div class="text-[11px] text-amber-600 dark:text-amber-400 mt-2 pl-5">
			{$i18n.t('Activé mais non connecté : configure la connexion pour qu’il fonctionne.')}
		</div>
	{/if}

	{#if expanded}
		<div class="mt-3 pl-5 border-t border-gray-100 dark:border-gray-850 pt-3">
			{#if providers.length > 0}
				<div class="text-[11px] font-medium text-gray-400 mb-1.5 uppercase tracking-wide">
					{$i18n.t('Services disponibles')}
				</div>
				<div class="flex flex-wrap gap-1.5">
					{#each providers as provider (provider)}
						<span
							class="text-[11px] px-2 py-0.5 rounded-lg bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
							>{provider}</span
						>
					{/each}
				</div>
			{/if}

			{#if connectable}
				<div class="mt-3">
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => dispatch('connect')}
					>
						{isConnected ? $i18n.t('Gérer la connexion') : $i18n.t('Connecter')}
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
