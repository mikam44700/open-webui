<script lang="ts">
	// Étape « second cerveau » (juste après l'interview, avant l'écran final). Adam — l'agent mémoire
	// (coffre Obsidian) — vient RÉELLEMENT de ranger le contexte de l'entreprise (persisté à la fin de
	// l'interview via writeInboxNote). On le rend tangible : ce qu'il fait + comment le dirigeant
	// retrouve sa mémoire (dans l'app tout de suite, et sur son PC via Obsidian synchronisé au coffre).
	// La synchro PC ↔ coffre (Syncthing) est un chantier ops séparé ; ici on présente + on donne le lien.
	import { createEventDispatcher, getContext } from 'svelte';
	import { faceFromImage, avatarId } from '$lib/components/agents/avatars';
	import { avatarColor } from '$lib/components/agents/avatar-colors';
	import { avatarImgFallback } from '$lib/utils/agentIdentity';
	import { AGENT_TEMPLATES } from '$lib/components/agents/templates';
	import obsidianLogo from '$lib/assets/integrations/obsidian.svg';
	import { getSyncPack, downloadSyncPack } from '$lib/apis/memory';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Page de téléchargement officielle (Mac/Windows/Linux détectés automatiquement par Obsidian).
	const OBSIDIAN_DOWNLOAD = 'https://obsidian.md/download';

	// Étape 2 : télécharger « LunarIA Sync » = le pack Syncthing PRÉ-APPAIRÉ. Le client le lance et
	// son coffre se connecte tout seul (zéro appairage). Généré à la demande par le bridge ; 503 tant
	// que la synchro n'est pas provisionnée sur le serveur (ex. dev mono-machine sans coffre distant).
	let syncing = false;
	let syncError = '';
	const connectVault = async () => {
		syncing = true;
		syncError = '';
		try {
			const pack = await getSyncPack(localStorage.token);
			downloadSyncPack(pack);
		} catch {
			syncError = $i18n.t(
				'La connexion du coffre n’est pas encore disponible ici. Votre mémoire reste consultable dans l’onglet Mémoire.'
			);
		} finally {
			syncing = false;
		}
	};

	// Adam = l'agent Obsidian (source unique : le template du socle). Fond du cercle = sa couleur signature.
	const adam = AGENT_TEMPLATES.find((t) => t.id === 'agent-obsidian');
	const adamImage = adam?.image ?? '/assets/agents/adam.webp';
	const adamName = adam?.firstName ?? 'Adam';
	const adamGradient = avatarColor(avatarId(adamImage) || adamName).gradient;
</script>

<div class="w-full max-w-2xl mx-auto px-5 py-9 sm:py-10">
	<!-- Présentation d'Adam -->
	<div class="text-center">
		<img
			src={faceFromImage(adamImage) ?? '/favicon.png'}
			alt={adamName}
			on:error={(e) => avatarImgFallback(e, adamImage)}
			style="background: {adamGradient}"
			class="mx-auto h-16 w-16 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15 shadow-[0_0_44px_-10px_rgba(120,80,220,0.45)]"
		/>
		<div
			class="mt-5 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-600 dark:text-amber-300/90"
		>
			{$i18n.t('Votre second cerveau')}
		</div>
		<h1 class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
			{$i18n.t('Adam se souvient de tout')}
		</h1>
		<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md mx-auto">
			{$i18n.t(
				'Adam vient de ranger le contexte de votre entreprise dans votre coffre. Tout ce que vous confierez à votre équipe, il s’en souviendra — pour toujours.'
			)}
		</p>
	</div>

	<!-- Ce qu'Adam fait, concrètement -->
	<div
		class="mt-7 rounded-2xl bg-white dark:bg-white/[0.03] ring-1 ring-inset ring-black/5 dark:ring-white/10 px-5 py-4"
	>
		<div class="grid gap-2.5 sm:grid-cols-3 text-[13px] text-gray-600 dark:text-gray-300">
			<div class="flex items-start gap-2">
				<span class="text-emerald-500 font-bold leading-none mt-[3px]">✓</span>
				<span>{$i18n.t('Capture ce qui compte, sans que vous ayez à y penser')}</span>
			</div>
			<div class="flex items-start gap-2">
				<span class="text-emerald-500 font-bold leading-none mt-[3px]">✓</span>
				<span>{$i18n.t('Range et relie tout dans un coffre clair')}</span>
			</div>
			<div class="flex items-start gap-2">
				<span class="text-emerald-500 font-bold leading-none mt-[3px]">✓</span>
				<span>{$i18n.t('Le retrouve à la demande, pour vous et vos agents')}</span>
			</div>
		</div>
	</div>

	<!-- Retrouver sa mémoire : dans l'app (déjà) + sur son PC via Obsidian (synchronisé au coffre) -->
	<div
		class="mt-4 rounded-2xl border border-amber-500/30 bg-amber-50/40 dark:bg-amber-400/[0.04] px-5 py-4"
	>
		<div class="text-sm font-semibold text-gray-900 dark:text-white">
			{$i18n.t('Votre mémoire, sur votre ordinateur')}
		</div>
		<p class="mt-1.5 text-[14px] leading-relaxed text-gray-600 dark:text-gray-300">
			{$i18n.t(
				'En 2 étapes, retrouvez votre coffre dans Obsidian sur votre PC — déjà rempli par Adam et synchronisé avec votre assistant.'
			)}
		</p>
		<div class="mt-4 flex flex-col sm:flex-row justify-center gap-2.5">
			<!-- Étape 1 : installer Obsidian -->
			<a
				href={OBSIDIAN_DOWNLOAD}
				target="_blank"
				rel="noopener noreferrer"
				class="inline-flex items-center justify-center gap-2.5 text-sm font-semibold px-5 py-2.5 rounded-xl bg-[#0f0f10] text-white ring-1 ring-inset ring-white/10 shadow-sm hover:ring-violet-400/50 transition"
			>
				<span class="inline-flex h-6 w-6 flex-none items-center justify-center rounded-lg bg-white">
					<img src={obsidianLogo} alt="Obsidian" class="h-4 w-4" />
				</span>
				<span class="text-left leading-tight">
					<span class="block text-[11px] font-medium text-white/50">{$i18n.t('Étape 1')}</span>
					{$i18n.t('Télécharger Obsidian')}
				</span>
			</a>
			<!-- Étape 2 : connecter le coffre (pack LunarIA Sync pré-appairé, zéro manip) -->
			<button
				type="button"
				on:click={connectVault}
				disabled={syncing}
				class="inline-flex items-center justify-center gap-2.5 text-sm font-semibold px-5 py-2.5 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 shadow-sm hover:brightness-105 disabled:opacity-60 transition"
			>
				<span class="text-left leading-tight">
					<span class="block text-[11px] font-medium text-amber-900/70">{$i18n.t('Étape 2')}</span>
					{syncing ? $i18n.t('Préparation…') : $i18n.t('Connecter mon coffre')}
				</span>
			</button>
		</div>
		{#if syncError}
			<p class="mt-2.5 text-[13px] text-gray-500 dark:text-gray-400">{syncError}</p>
		{/if}
		<p class="mt-3 text-[13px] text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'Pas envie d’installer ? Votre mémoire est déjà consultable dans l’onglet Mémoire de LunarIA.'
			)}
		</p>
	</div>

	<!-- Navigation : Retour (revient au questionnaire, réponses conservées) + Continuer -->
	<div class="mt-7 flex items-center justify-between gap-3">
		<button
			class="text-sm font-medium px-4 py-2 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
			on:click={() => dispatch('back')}
		>
			← {$i18n.t('Retour')}
		</button>
		<button
			class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950"
			on:click={() => dispatch('next')}
		>
			{$i18n.t('Continuer')} →
		</button>
	</div>
</div>
