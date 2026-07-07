<script lang="ts">
	// Sélecteur de « cerveau » dans l'en-tête du chat (Agent OS).
	// Remplace le sélecteur de modèle natif (cosmétique : Hermes ignore le champ `model`).
	// Affiche le VRAI modèle actif de Hermes + laisse choisir :
	//   - le niveau d'intelligence (effort de raisonnement, global — agent.reasoning_effort)
	//   - le modèle (parmi les fournisseurs CONNECTÉS — pilote model.provider/model.default)
	// Les changements sont GLOBAUX (un dirigeant = un assistant) et s'appliquent aux
	// nouvelles conversations. On ne touche jamais au moteur.
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		getActiveProvider,
		getProviders,
		setActiveProvider,
		getReasoning,
		setReasoning,
		getModelCapabilities
	} from '$lib/apis/providers';
	import { getProviderName } from '$lib/catalog/provider-info';
	import { isHiddenProvider } from '$lib/catalog/provider-taxonomy';

	const i18n = getContext('i18n');

	// Niveaux d'intelligence exposés au dirigeant (mappés sur l'effort moteur Hermes).
	const LEVELS = [
		{ effort: 'low', label: 'Rapide', desc: 'Réponses vives' },
		{ effort: 'medium', label: 'Équilibré', desc: 'Le bon compromis' },
		{ effort: 'high', label: 'Approfondi', desc: 'Réflexion poussée' },
		{ effort: 'xhigh', label: 'Maximum', desc: 'Raisonnement maximal' }
	];

	let open = false;
	let loading = true;
	let unavailable = false;

	// Sections pliables du menu (Fournisseur + Intelligence + Modèle). Ouvertes par défaut.
	let providersOpen = true;
	let intelligenceOpen = true;
	let modelOpen = true;

	// Recherche de modèle : indispensable pour les passerelles (OpenRouter expose 256+
	// modèles). La barre n'apparaît qu'au-delà d'un seuil (inutile pour 3-5 modèles).
	let modelQuery = '';
	const MODEL_SEARCH_THRESHOLD = 12;

	// Le menu est rendu en position FIXE (calculée sous le bouton) pour échapper au
	// conteneur `overflow-hidden` de la barre du chat, sinon il serait clippé/invisible.
	let triggerEl: HTMLButtonElement;
	let menuStyle = '';

	const toggle = () => {
		open = !open;
		if (open && triggerEl) {
			const r = triggerEl.getBoundingClientRect();
			menuStyle = `top:${Math.round(r.bottom + 6)}px; left:${Math.round(r.left)}px;`;
		}
	};

	let active: { provider_id: string; model_id: string } | null = null;
	let effort = 'medium';
	let providers: {
		id: string;
		label: string;
		state: string;
		models: { id: string; label: string; provider_id: string }[];
	}[] = [];

	// Capacités du modèle ACTIF (reasoning/vision/outils/contexte). null = inconnu → on
	// affiche tout par défaut (repli gracieux). Le menu s'adapte quand elles arrivent.
	let caps: {
		reasoning: boolean | null;
		vision: boolean | null;
		tools: boolean | null;
		context_window: number | null;
		// Niveaux d'intelligence réellement honorés par le fournisseur actif (le reste est
		// grisé). Absent/null = inconnu → on autorise tout (repli gracieux).
		supported_efforts?: string[] | null;
	} | null = null;

	$: connected = providers.filter(
		(p) => p.state !== 'not_configured' && (p.models?.length ?? 0) > 0 && !isHiddenProvider(p.id)
	);
	// Liste triée par ordre alphabétique (nom affiché) pour un menu net et prévisible.
	$: connectedSorted = [...connected].sort((a, b) =>
		getProviderName(a.id, a.label).localeCompare(getProviderName(b.id, b.label), 'fr')
	);
	// Fournisseur actuellement aux commandes (sa card complète est affichée dans le menu).
	$: activeProvider = connected.find((p) => p.id === active?.provider_id) ?? connected[0] ?? null;
	$: activeProviderLabel = (() => {
		const p = providers.find((pp) => pp.id === active?.provider_id);
		return p ? getProviderName(p.id, p.label) : '';
	})();
	// Un modèle IA est-il vraiment connecté ? (au moins un fournisseur branché avec modèles)
	$: hasBrain = connected.length > 0;
	// Nom lisible du modèle IA actif : on montre le NOM DU FOURNISSEUR (« OpenAI Codex »,
	// « Mixture of Agents »), pas le modèle technique (« gpt-5.5 »). Repli sur l'id du modèle
	// si le fournisseur n'a pas de label (ex. mode « auto »).
	$: activeBrainName = !active ? '' : activeProviderLabel || active.model_id;
	// Nom du modèle exact (technique, ex. « gemini-3.1-pro-preview ») affiché en second,
	// discret, sous le nom lisible du fournisseur. Repli sur l'id si pas de label.
	$: activeModelLabel = (() => {
		if (!active) return '';
		const m = activeProvider?.models?.find((mm) => mm.id === active.model_id);
		return m?.label || active.model_id;
	})();

	// Type de sortie d'un modèle. models.dev (output_modalities) est souvent vide pour les
	// modèles récents → repli par motif de nom (comme la table de secours des capacités).
	// Un générateur d'image/vidéo N'EST PAS un cerveau de chat : on ne le liste pas comme
	// modèle sélectionnable, on l'annonce comme capacité (image/vidéo dans le chat).
	const modelKind = (id: string): 'chat' | 'image' | 'video' => {
		const s = (id || '').toLowerCase();
		if (/imagine-video|(^|[-_])(video|veo|sora)([-_.]|$)/.test(s)) return 'video';
		if (/imagine-image|dall-?e|gpt-image|(^|[-_])flux|stable-?diffusion|sdxl|(^|[-_])image([-_.]|$)/.test(s))
			return 'image';
		return 'chat';
	};
	// Modèles de CONVERSATION du fournisseur actif, RECOMMANDÉ en tête (le reste garde son
	// ordre : on ne devine pas la « puissance » depuis un nom, ça mentirait). Le curé porte
	// un badge « Recommandé » — seul classement honnête et durable.
	$: recommendedModelId =
		activeProvider && !NO_RECOMMENDED_BADGE.has(activeProvider.id)
			? defaultModelId(activeProvider)
			: undefined;
	$: chatModels = (() => {
		const items = (activeProvider?.models ?? []).filter((m) => modelKind(m.id) === 'chat');
		if (!recommendedModelId) return items;
		const rec = items.filter((m) => m.id === recommendedModelId);
		const rest = items.filter((m) => m.id !== recommendedModelId);
		return [...rec, ...rest];
	})();
	// Barre de recherche affichée seulement si le fournisseur a beaucoup de modèles.
	$: showModelSearch = chatModels.length > MODEL_SEARCH_THRESHOLD;
	// Filtre typeahead : cherche dans le nom lisible ET l'id technique (« gpt », « llama »…).
	$: filteredModels = (() => {
		const q = modelQuery.trim().toLowerCase();
		if (!q) return chatModels;
		return chatModels.filter(
			(m) => m.label.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
		);
	})();
	// Le fournisseur actif sait-il AUSSI générer images / vidéos ? On ne les liste pas comme
	// des cerveaux (grisés = « cassé ») : on l'annonce comme une capacité, générable en
	// langage naturel dans le chat (plugins). Cf. [[generation-image-video-chat]].
	// EXCLUSION : les passerelles (OpenRouter) exposent des modèles image/vidéo dans leur
	// catalogue, mais notre pipeline de génération n'est branché que sur les plugins natifs
	// (xAI). Annoncer la capacité ici serait TROMPEUR (le client ne pourrait pas générer).
	const GEN_MEDIA_UNSUPPORTED = new Set(['openrouter']);
	$: genMediaSupported = !GEN_MEDIA_UNSUPPORTED.has(activeProvider?.id ?? '');
	$: canGenImage =
		genMediaSupported && (activeProvider?.models ?? []).some((m) => modelKind(m.id) === 'image');
	$: canGenVideo =
		genMediaSupported && (activeProvider?.models ?? []).some((m) => modelKind(m.id) === 'video');
	$: activeLevel = LEVELS.find((l) => l.effort === effort) ?? null;
	// On masque l'intelligence seulement si on SAIT que le modèle ne raisonne pas.
	$: showIntelligence = !caps || caps.reasoning !== false;
	// Niveaux honorés par le modèle actif ; null = inconnu → tout autorisé (repli gracieux).
	$: supportedEfforts = caps?.supported_efforts ?? null;

	const ctxLabel = (n: number | null | undefined) => {
		if (!n) return '';
		if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
		if (n >= 1000) return `${Math.round(n / 1000)}k`;
		return `${n}`;
	};

	const loadCaps = async () => {
		if (!active) {
			caps = null;
			return;
		}
		try {
			caps = await getModelCapabilities(localStorage.token, active.provider_id, active.model_id);
			// Sécurité : si le niveau global actif n'est pas honoré par ce modèle (ex.
			// « Maximum »/xhigh alors qu'on bascule sur Gemini), on retombe automatiquement
			// sur le plus poussé qu'il accepte — sinon le chat pourrait planter ou l'ignorer.
			const ok = caps?.supported_efforts;
			if (ok && ok.length && !ok.includes(effort)) {
				await chooseLevel(ok[ok.length - 1]);
			}
		} catch {
			caps = null;
		}
	};

	const load = async () => {
		loading = true;
		unavailable = false;
		try {
			const token = localStorage.token;
			// Modèle actif + liste : endpoints existants (indispensables au sélecteur).
			const [a, p] = await Promise.all([getActiveProvider(token), getProviders(token)]);
			active = a ?? null;
			providers = p?.providers ?? [];
			// Intelligence : endpoint récent — tolère un bridge pas encore resynchronisé.
			try {
				const r = await getReasoning(token);
				effort = r?.effort ?? 'medium';
			} catch {
				effort = 'medium';
			}
			void loadCaps();
		} catch (err) {
			unavailable = true;
		} finally {
			loading = false;
		}
	};

	const chooseModel = async (providerId: string, modelId: string) => {
		try {
			await setActiveProvider(localStorage.token, providerId, modelId);
			active = { provider_id: providerId, model_id: modelId };
			void loadCaps();
			toast.success($i18n.t('Modèle changé — actif pour les nouvelles conversations.'));
		} catch (err: any) {
			toast.error(err?.error?.message || $i18n.t('Changement impossible'));
		}
	};

	// Bascule directe de fournisseur (puces en haut du menu) : on active son modèle
	// recommandé (défaut curé, sinon 1er exposé) → toute la card se met à jour sur lui.
	// Même table que le bridge : la liste des modèles n'est pas triée par pertinence.
	const RECOMMENDED_MODEL: Record<string, string> = {
		anthropic: 'claude-sonnet-4-6',
		'openai-api': 'gpt-5.5',
		gemini: 'gemini-3.5-flash',
		mistral: 'mistral-large-latest',
		deepseek: 'deepseek-v4-pro',
		perplexity: 'sonar',
		xai: 'grok-4.3',
		'ollama-cloud': 'gpt-oss:120b'
	};
	// Fournisseurs à TROP de modèles (catalogues) : pas de badge « Recommandé » (le client
	// choisit), et rien n'est remonté en tête → l'ordre alphabétique du bridge est préservé.
	const NO_RECOMMENDED_BADGE = new Set(['ollama-cloud', 'openrouter']);
	// Défaut d'ACTIVATION à la bascule de fournisseur : le curé s'il existe (pour Ollama, un
	// GRATUIT — sinon models[0] serait un premium 403 avec le tri alpha), sinon le 1er exposé.
	const defaultModelId = (p: { id: string; models: { id: string }[] }): string | undefined => {
		const rec = RECOMMENDED_MODEL[p.id];
		if (rec && p.models.some((m) => m.id === rec)) return rec;
		return p.models[0]?.id;
	};
	const switchProvider = (p: { id: string; models: { id: string }[] }) => {
		if (p.id === active?.provider_id) return; // déjà aux commandes
		modelQuery = ''; // change de fournisseur => on repart d'une recherche vierge
		const mid = defaultModelId(p);
		if (mid) chooseModel(p.id, mid);
	};

	const chooseLevel = async (level: string) => {
		const previous = effort;
		effort = level;
		try {
			await setReasoning(localStorage.token, level);
		} catch (err: any) {
			effort = previous;
			toast.error(err?.error?.message || $i18n.t('Changement impossible'));
		}
	};

	onMount(load);
</script>

{#if !unavailable}
	<div class="relative">
		<!-- Déclencheur : montre le VRAI modèle actif -->
		<button
			type="button"
			bind:this={triggerEl}
			style="-webkit-app-region: no-drag;"
			class="flex items-center gap-1.5 rounded-xl px-2 py-1 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 transition max-w-full"
			on:click={toggle}
			aria-haspopup="menu"
			aria-expanded={open}
		>
			<span class="flex min-w-0 flex-col text-left leading-tight">
				<span class="flex items-center gap-1.5">
					<span class="font-medium text-gray-900 dark:text-white truncate">
						{loading ? $i18n.t('Chargement…') : hasBrain ? activeBrainName : $i18n.t('Aucun modèle IA')}
					</span>
					{#if activeLevel && showIntelligence}
						<span
							class="hidden sm:inline text-[11px] text-gray-400 dark:text-gray-500 whitespace-nowrap"
							>· {$i18n.t(activeLevel.label)}</span
						>
					{/if}
				</span>
				{#if hasBrain && activeModelLabel}
					<span class="truncate text-[10px] text-gray-400 dark:text-gray-500">{activeModelLabel}</span>
				{/if}
			</span>
			<svg class="size-3.5 text-gray-400 shrink-0" viewBox="0 0 20 20" fill="currentColor"
				><path
					fill-rule="evenodd"
					d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
					clip-rule="evenodd"
				/></svg
			>
		</button>

		{#if open}
			<!-- fond cliquable pour fermer -->
			<button
				class="fixed inset-0 z-40 cursor-default"
				on:click={() => (open = false)}
				tabindex="-1"
				aria-label={$i18n.t('Fermer')}
			></button>

			<div
				role="menu"
				style="{menuStyle} -webkit-app-region: no-drag;"
				class="fixed z-50 w-96 max-h-[70vh] overflow-y-auto rounded-2xl border border-gray-100 bg-white p-2 shadow-xl dark:border-gray-800 dark:bg-gray-900 scrollbar-hidden"
			>
				<!-- En-tête : modèle actif + ses capacités (le menu s'adapte à CE modèle) -->
				<div class="px-2 pb-2 pt-1">
					<div class="truncate text-sm font-medium text-gray-900 dark:text-white">
						{hasBrain ? activeBrainName : $i18n.t('Aucun modèle IA')}
					</div>
					{#if activeProviderLabel}
						<div class="text-[11px] text-gray-400">{activeProviderLabel}</div>
					{/if}
					{#if caps && (caps.reasoning || caps.vision || caps.tools || caps.context_window)}
						<div class="mt-1.5 flex flex-wrap items-center gap-1">
							{#if caps.reasoning}
								<span class="inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">{$i18n.t('Raisonnement')}</span>
							{/if}
							{#if caps.vision}
								<span class="inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">{$i18n.t('Vision')}</span>
							{/if}
							{#if caps.tools}
								<span class="inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">{$i18n.t('Outils')}</span>
							{/if}
							{#if caps.context_window}
								<span class="inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">{ctxLabel(caps.context_window)} {$i18n.t('contexte')}</span>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Switch fournisseur : bascule TOUTE la card (capacités + intelligence + modèles)
				     sur l'autre fournisseur. Visible dès qu'au moins 2 sont connectés. -->
				{#if connected.length > 1}
					<!-- Titre pliable : montre le fournisseur actif même replié -->
					<button
						type="button"
						class="flex w-full items-center justify-between gap-2 border-t border-gray-100 px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400 transition hover:text-gray-600 dark:border-gray-800 dark:hover:text-gray-200"
						on:click={() => (providersOpen = !providersOpen)}
						aria-expanded={providersOpen}
					>
						<span class="flex min-w-0 items-center gap-1.5">
							<span class="whitespace-nowrap">{$i18n.t('Changer de modèle IA')}</span>
							{#if activeProviderLabel}<span class="max-w-[9rem] truncate font-normal normal-case tracking-normal text-gray-400">· {activeProviderLabel}</span>{/if}
						</span>
						<svg
							class="size-3.5 shrink-0 transition-transform {providersOpen ? 'rotate-180' : ''}"
							viewBox="0 0 20 20"
							fill="currentColor"
							><path
								fill-rule="evenodd"
								d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
								clip-rule="evenodd"
							/></svg
						>
					</button>
					{#if providersOpen}
						<div class="px-2 pb-1 pt-1">
							{#each connectedSorted as p (p.id)}
								{@const isActive = active?.provider_id === p.id}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={isActive}
									class="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left transition {isActive
										? 'bg-gray-100 dark:bg-gray-800'
										: 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
									on:click={() => switchProvider(p)}
								>
									<span class="flex min-w-0 items-center gap-1.5">
										<span class="shrink-0 text-gray-300 dark:text-gray-600" aria-hidden="true">·</span>
										<span class="truncate text-sm text-gray-900 dark:text-white">{getProviderName(p.id, p.label)}</span>
									</span>
									{#if isActive}
										<svg class="size-4 shrink-0 text-gray-900 dark:text-white" viewBox="0 0 20 20" fill="currentColor"
											><path
												fill-rule="evenodd"
												d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0l-3.5-3.5a1 1 0 111.4-1.4l2.8 2.79 6.8-6.79a1 1 0 011.4 0z"
												clip-rule="evenodd"
											/></svg
										>
									{/if}
								</button>
							{/each}
						</div>
					{/if}
				{/if}

				<!-- Intelligence : affichée seulement si le modèle sait raisonner -->
				{#if showIntelligence}
					<!-- Titre pliable : montre le niveau courant même replié -->
					<button
						type="button"
						class="flex w-full items-center justify-between gap-2 border-t border-gray-100 px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400 transition hover:text-gray-600 dark:border-gray-800 dark:hover:text-gray-200"
						on:click={() => (intelligenceOpen = !intelligenceOpen)}
						aria-expanded={intelligenceOpen}
					>
						<span class="flex items-center gap-1.5">
							{$i18n.t('Intelligence')}
							{#if activeLevel}<span class="normal-case font-normal tracking-normal text-gray-400">· {$i18n.t(activeLevel.label)}</span>{/if}
						</span>
						<svg
							class="size-3.5 shrink-0 transition-transform {intelligenceOpen ? 'rotate-180' : ''}"
							viewBox="0 0 20 20"
							fill="currentColor"
							><path
								fill-rule="evenodd"
								d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
								clip-rule="evenodd"
							/></svg
						>
					</button>
					{#if intelligenceOpen}
					{#each LEVELS as lvl (lvl.effort)}
						{@const supported = !supportedEfforts || supportedEfforts.includes(lvl.effort)}
						<button
							type="button"
							role="menuitemradio"
							aria-checked={effort === lvl.effort}
							disabled={!supported}
							title={supported ? '' : $i18n.t('Ce modèle ne propose pas ce niveau')}
							class="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left transition {!supported
								? 'cursor-not-allowed opacity-40'
								: effort === lvl.effort
									? 'bg-gray-100 dark:bg-gray-800'
									: 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
							on:click={() => supported && chooseLevel(lvl.effort)}
						>
							<span class="min-w-0">
								<span class="block text-sm text-gray-900 dark:text-white">{$i18n.t(lvl.label)}</span>
								<span class="block text-[11px] text-gray-400"
									>{supported ? $i18n.t(lvl.desc) : $i18n.t('Non proposé par ce modèle')}</span
								>
							</span>
							{#if supported && effort === lvl.effort}
								<svg class="size-4 shrink-0 text-gray-900 dark:text-white" viewBox="0 0 20 20" fill="currentColor"
									><path
										fill-rule="evenodd"
										d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0l-3.5-3.5a1 1 0 111.4-1.4l2.8 2.79 6.8-6.79a1 1 0 011.4 0z"
										clip-rule="evenodd"
									/></svg
								>
							{/if}
						</button>
					{/each}
					{/if}
				{:else}
					<div class="border-t border-gray-100 dark:border-gray-800 px-2 py-2 text-[11px] text-gray-400">
						{$i18n.t('Ce modèle ne gère pas les niveaux d’intelligence.')}
					</div>
				{/if}

				<!-- Modèle (pliable) : montre le modèle actif même replié -->
				<button
					type="button"
					class="mt-2 flex w-full items-center justify-between gap-2 border-t border-gray-100 px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400 transition hover:text-gray-600 dark:border-gray-800 dark:hover:text-gray-200"
					on:click={() => (modelOpen = !modelOpen)}
					aria-expanded={modelOpen}
				>
					<span class="flex min-w-0 items-center gap-1.5">
						{$i18n.t('Modèle')}
						{#if hasBrain && activeModelLabel}<span class="max-w-[9rem] truncate font-normal normal-case tracking-normal text-gray-400">· {activeModelLabel}</span>{/if}
					</span>
					<svg
						class="size-3.5 shrink-0 transition-transform {modelOpen ? 'rotate-180' : ''}"
						viewBox="0 0 20 20"
						fill="currentColor"
						><path
							fill-rule="evenodd"
							d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
							clip-rule="evenodd"
						/></svg
					>
				</button>
				{#if modelOpen}
					{#if connected.length === 0}
						<div class="px-2 py-2 text-[12px] text-gray-400">
							{$i18n.t('Aucun modèle IA connecté. Connectez-en un dans « Modèles IA ».')}
						</div>
					{:else if activeProvider}
						<!-- Passerelles (OpenRouter, 256+ modèles) : barre de recherche pour ne pas
						     noyer le dirigeant. Grands noms visibles par défaut, le reste à la demande. -->
						{#if showModelSearch}
							<div class="px-1 pb-1.5 pt-1">
								<div class="relative">
									<svg
										class="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-gray-400"
										viewBox="0 0 20 20"
										fill="currentColor"
										aria-hidden="true"
										><path
											fill-rule="evenodd"
											d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l3.08 3.08a1 1 0 01-1.42 1.42l-3.08-3.08A7 7 0 012 9z"
											clip-rule="evenodd"
										/></svg
									>
									<input
										type="text"
										bind:value={modelQuery}
										placeholder={$i18n.t('Rechercher un modèle…')}
										aria-label={$i18n.t('Rechercher un modèle')}
										class="w-full rounded-lg border border-gray-200 bg-gray-50 py-1.5 pl-8 pr-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-400 focus:outline-none dark:border-gray-800 dark:bg-gray-850 dark:text-white"
									/>
								</div>
							</div>
						{/if}
						<!-- Liste scrollable dédiée : barre de scroll visible (256+ modèles), la
						     barre de recherche au-dessus reste fixe. -->
						<div class="max-h-[50vh] overflow-y-auto scrollbar-thin pr-1">
						<!-- Modèles de CONVERSATION du fournisseur aux commandes, recommandé en tête. -->
						{#each filteredModels as m (m.id)}
							{@const isActive = active?.model_id === m.id}
							{@const isRecommended = m.id === recommendedModelId}
							<button
								type="button"
								role="menuitemradio"
								aria-checked={isActive}
								class="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left transition {isActive
									? 'bg-gray-100 dark:bg-gray-800'
									: 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
								on:click={() => chooseModel(activeProvider.id, m.id)}
							>
								<span class="flex min-w-0 items-center gap-1.5">
									<span class="shrink-0 text-gray-300 dark:text-gray-600" aria-hidden="true">·</span>
									<span class="truncate text-sm text-gray-900 dark:text-white">{m.label}</span>
									{#if isRecommended}
										<span class="shrink-0 rounded-full bg-gray-100 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-gray-500 dark:bg-gray-800 dark:text-gray-400">{$i18n.t('Recommandé')}</span>
									{/if}
								</span>
								{#if isActive}
									<svg class="size-4 shrink-0 text-gray-900 dark:text-white" viewBox="0 0 20 20" fill="currentColor"
										><path
											fill-rule="evenodd"
											d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0l-3.5-3.5a1 1 0 111.4-1.4l2.8 2.79 6.8-6.79a1 1 0 011.4 0z"
											clip-rule="evenodd"
										/></svg
									>
								{/if}
							</button>
						{/each}
						{#if showModelSearch && filteredModels.length === 0}
							<div class="px-2 py-2 text-[12px] text-gray-400">
								{$i18n.t('Aucun modèle ne correspond à votre recherche.')}
							</div>
						{/if}
						</div>

						<!-- Capacité (pas un cerveau sélectionnable) : image/vidéo se demandent dans le chat. -->
						{#if canGenImage || canGenVideo}
							<div class="mx-1 mt-1.5 rounded-lg bg-gray-50 px-2.5 py-2 dark:bg-gray-850">
								<div class="text-[11px] leading-snug text-gray-500 dark:text-gray-400">
									<span aria-hidden="true">✨</span>
									{#if canGenImage && canGenVideo}
										{$i18n.t('Ce modèle IA peut aussi créer des images et des vidéos.')}
									{:else if canGenImage}
										{$i18n.t('Ce modèle IA peut aussi créer des images.')}
									{:else}
										{$i18n.t('Ce modèle IA peut aussi créer des vidéos.')}
									{/if}
								</div>
								<div class="mt-0.5 text-[10px] text-gray-400">
									{$i18n.t('Demande-le simplement dans le chat.')}
								</div>
							</div>
						{/if}
					{/if}
				{/if}
			</div>
		{/if}
	</div>
{/if}
