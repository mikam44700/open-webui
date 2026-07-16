<script lang="ts">
	import { createEventDispatcher, getContext, onDestroy, onMount, tick } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import { toast } from 'svelte-sonner';

	import { getModels } from '$lib/apis';
	import { createAgent } from '$lib/apis/agents';
	import { uploadFile, getFileById } from '$lib/apis/files';
	import { generateAgent, MAX_DOCS, type GeneratedAgent, type SourceDoc } from '$lib/agents/generator';
	import { getIntegrations } from '$lib/apis/integrations';
	import { getConnectors } from '$lib/apis/connectors';
	import { getProfile } from '$lib/apis/memory';
	import AvatarPicker from './AvatarPicker.svelte';
	import { suggestAvatar, avatarImage } from './avatars';
	import { parseSoulSections } from './soul';
	import MissionSections from './MissionSections.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	// Identifiants d'avatars déjà pris par des agents existants (évite les doublons).
	export let used: string[] = [];

	type Phase = 'brief' | 'generating' | 'result' | 'error';
	let phase: Phase = 'brief';

	let brief = '';
	let adjustment = '';
	let showAdjust = false;
	let result: GeneratedAgent | null = null;
	let errorMsg = '';
	let activating = false;

	// Avatar choisi pour l'agent (chemin d'image). Suggéré à la génération, changeable.
	let selectedAvatar: string | null = null;
	let showAvatarPicker = false;

	let model = '';
	let briefEl: HTMLTextAreaElement;

	// Documents fournis par le dirigeant (procédures existantes).
	let sources: SourceDoc[] = [];
	let uploading = false;
	let dragOver = false;
	let fileInput: HTMLInputElement;

	// Mode guidé : 3 questions de capture (le vrai process) pour un agent sur-mesure.
	let guidedOpen = false;
	let gWalkthrough = '';
	let gExceptions = '';
	let gSuccess = '';

	// Édition directe de la mission générée (sauvegardée avant activation).
	let editing = false;
	let editLabel = '';
	let editDescription = '';
	let editSections: { title: string; body: string; icon: string }[] = [];

	// Suggestions concrètes (langage dirigeant, pas de jargon).
	const ideas = [
		'Relancer mes clients qui n’ont pas payé, avec tact',
		'Répondre vite et bien aux demandes des clients',
		'Préparer mes devis et les relancer au bon moment',
		'Animer mes réseaux sociaux',
		'Trier mes emails et préparer les réponses',
		'Faire progresser mon équipe commerciale'
	];

	// Messages rassurants pendant la fabrication.
	const genMessages = [
		'Je cerne précisément son métier…',
		'Je rédige sa méthode de travail…',
		'J’ajoute ses livrables concrets…',
		'Je pose ses garde-fous…',
		'Dernières finitions…'
	];
	let genMsg = genMessages[0];
	let genTimer: ReturnType<typeof setInterval> | null = null;

	const startGenMessages = () => {
		stopGenMessages();
		let i = 0;
		genMsg = genMessages[0];
		genTimer = setInterval(() => {
			i = (i + 1) % genMessages.length;
			genMsg = genMessages[i];
		}, 1900);
	};
	const stopGenMessages = () => {
		if (genTimer) {
			clearInterval(genTimer);
			genTimer = null;
		}
	};

	const loadModels = async () => {
		try {
			const res = await getModels(localStorage.token);
			const list = res?.data ?? res ?? [];
			model = list?.[0]?.id ?? '';
		} catch {
			/* géré au moment de générer */
		}
	};

	onMount(loadModels);
	onDestroy(stopGenMessages);

	// Focus auto du champ quand on ouvre / revient à l'écran de saisie.
	$: if (show && phase === 'brief') {
		tick().then(() => briefEl?.focus());
	}

	const useIdea = async (t: string) => {
		brief = t;
		await tick();
		briefEl?.focus();
	};

	// Upload + extraction du texte d'un document via OpenWebUI.
	const handleFiles = async (files: FileList | File[]) => {
		const list = Array.from(files ?? []);
		if (!list.length) return;

		const free = MAX_DOCS - sources.length;
		if (free <= 0) {
			toast.error($i18n.t('{{n}} documents maximum par agent', { n: MAX_DOCS }));
			return;
		}
		const toProcess = list.slice(0, free);
		if (list.length > free) {
			toast.error($i18n.t('{{n}} documents maximum par agent', { n: MAX_DOCS }));
		}

		uploading = true;
		for (const file of toProcess) {
			try {
				const up = await uploadFile(localStorage.token, file, null, true, true);
				let content = up?.data?.content ?? '';
				if (!content && up?.id) {
					const full = await getFileById(localStorage.token, up.id);
					content = full?.data?.content ?? full?.content ?? '';
				}
				if (!content.trim()) {
					toast.error($i18n.t('Document illisible : {{name}}', { name: file.name }));
					continue;
				}
				sources = [...sources, { name: file.name, content }];
			} catch {
				toast.error($i18n.t('Échec de l’import : {{name}}', { name: file.name }));
			}
		}
		uploading = false;
	};

	const removeSource = (name: string) => {
		sources = sources.filter((s) => s.name !== name);
	};

	const onPick = (e: Event) => {
		const input = e.target as HTMLInputElement;
		if (input.files) handleFiles(input.files);
		input.value = '';
	};

	const onDrop = (e: DragEvent) => {
		e.preventDefault();
		dragOver = false;
		if (e.dataTransfer?.files) handleFiles(e.dataTransfer.files);
	};

	$: canGenerate =
		(brief.trim().length > 0 ||
			sources.length > 0 ||
			gWalkthrough.trim() ||
			gExceptions.trim() ||
			gSuccess.trim()) &&
		!uploading;

	// Outils réellement connectés (intégrations + MCP) → injectés au générateur pour le niveau 3-4.
	let connectedTools: string[] = [];
	const fetchConnectedTools = async (): Promise<string[]> => {
		const out: string[] = [];
		try {
			const res: any = await getIntegrations(localStorage.token);
			const list = Array.isArray(res) ? res : (res?.integrations ?? []);
			for (const it of list) {
				if (it?.state === 'connected') out.push(it.label || it.name || it.id);
			}
		} catch {
			/* tolérant : si indisponible, on génère sans la liste (niveau 3-4 via le prompt seul) */
		}
		try {
			const res: any = await getConnectors(localStorage.token);
			const list = Array.isArray(res) ? res : (res?.connectors ?? []);
			for (const c of list) {
				if (c?.enabled !== false) out.push(c.label || c.id || c.name);
			}
		} catch {
			/* tolérant */
		}
		return [...new Set(out.filter(Boolean))];
	};

	// Contexte de l'entreprise (USER.md, capté à l'onboarding) → injecté pour un agent « de la boîte ».
	let companyContext = '';
	const fetchCompanyContext = async (): Promise<string> => {
		try {
			const res = await getProfile(localStorage.token);
			return (res?.content ?? '').trim();
		} catch {
			/* tolérant : sans contexte, on génère un agent générique (dégradé gracieux) */
			return '';
		}
	};

	const generate = async () => {
		if (!brief.trim() && sources.length === 0) return;
		phase = 'generating';
		errorMsg = '';
		startGenMessages();
		try {
			if (!model) await loadModels();
			[connectedTools, companyContext] = await Promise.all([
				fetchConnectedTools(),
				fetchCompanyContext()
			]);
			result = await generateAgent(localStorage.token, model, brief.trim(), {
				sources,
				guided: { walkthrough: gWalkthrough, exceptions: gExceptions, success: gSuccess },
				connectedTools,
				companyContext
			});
			// Suggestion d'avatar cohérente et stable, en évitant un visage déjà pris.
			selectedAvatar = avatarImage(suggestAvatar(result.label, result.gender, used));
			phase = 'result';
		} catch (e: any) {
			errorMsg = e?.message ?? 'La génération a échoué.';
			phase = 'error';
		} finally {
			stopGenMessages();
		}
	};

	const regenerate = async () => {
		editing = false;
		phase = 'generating';
		errorMsg = '';
		startGenMessages();
		try {
			result = await generateAgent(localStorage.token, model, brief.trim(), {
				sources,
				guided: { walkthrough: gWalkthrough, exceptions: gExceptions, success: gSuccess },
				connectedTools,
				companyContext,
				previous: result ?? undefined,
				adjustment: adjustment.trim() || undefined
			});
			// On préserve l'avatar choisi ; on n'en suggère un que s'il n'y en avait pas.
			if (!selectedAvatar)
				selectedAvatar = avatarImage(suggestAvatar(result.label, result.gender, used));
			adjustment = '';
			showAdjust = false;
			phase = 'result';
		} catch (e: any) {
			errorMsg = e?.message ?? 'La génération a échoué.';
			phase = 'error';
		} finally {
			stopGenMessages();
		}
	};

	const activate = async () => {
		if (!result) return;
		if (editing) syncFromEdits();
		activating = true;
		try {
			await createAgent(localStorage.token, {
				name: result.label,
				description: result.description,
				soul: result.soul,
				avatar: selectedAvatar ?? undefined
			});
			toast.success($i18n.t('{{name}} est prêt à travailler', { name: result.label }));
			dispatch('created');
			close();
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Un agent porte déjà ce nom'));
			} else {
				toast.error($i18n.t('Impossible d’activer cet agent'));
			}
			activating = false;
		}
	};

	const startEditing = () => {
		if (!result) return;
		editLabel = result.label;
		editDescription = result.description;
		editSections = sections.map((s) => ({ ...s }));
		showAdjust = false;
		editing = true;
	};

	// Reconstruit result.soul depuis les blocs édités → la version corrigée sera activée.
	const syncFromEdits = () => {
		if (!result) return;
		result = {
			...result,
			label: editLabel.trim() || result.label,
			description: editDescription.trim(),
			soul: editSections.map((s) => `## ${s.title}\n${s.body.trim()}`).join('\n\n')
		};
	};

	const finishEditing = () => {
		syncFromEdits();
		editing = false;
	};

	const restart = () => {
		result = null;
		selectedAvatar = null;
		adjustment = '';
		showAdjust = false;
		editing = false;
		phase = 'brief';
	};

	const close = () => {
		show = false;
		stopGenMessages();
		setTimeout(() => {
			phase = 'brief';
			brief = '';
			result = null;
			selectedAvatar = null;
			adjustment = '';
			showAdjust = false;
			activating = false;
			sources = [];
			editing = false;
			guidedOpen = false;
			gWalkthrough = '';
			gExceptions = '';
			gSuccess = '';
		}, 200);
	};

	// Découpe la mission en sections lisibles (parsing partagé avec l'aperçu des templates).
	$: sections = parseSoulSections(result?.soul);
</script>

{#if show}
	<div class="fixed inset-0 z-[60] bg-white dark:bg-gray-900 overflow-y-auto" transition:fade={{ duration: 150 }}>
		<!-- Barre du haut -->
		<div
			class="sticky top-0 z-10 flex items-center justify-between px-5 py-4 bg-white/80 dark:bg-gray-900/80 backdrop-blur"
		>
			<div class="flex items-center gap-2 text-sm font-medium text-gray-400">
				<span>✨</span>{$i18n.t('Atelier des agents')}
			</div>
			<button
				class="size-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={close}
				aria-label={$i18n.t('Fermer')}>✕</button
			>
		</div>

		<div class="max-w-2xl mx-auto px-5 pb-28">
			{#if phase === 'brief'}
				<div class="text-center mt-[7vh]" in:fly={{ y: 12, duration: 300 }}>
					<div class="text-3xl sm:text-4xl font-semibold tracking-tight leading-tight">
						{$i18n.t('Votre nouveau collègue,')}<br />{$i18n.t('en une phrase.')}
					</div>
					<div class="text-sm text-gray-500 mt-3">
						{$i18n.t('Décrivez ce dont vous avez besoin. On fabrique l’agent. Vous validez.')}
					</div>
				</div>

				<div class="mt-8">
					<textarea
						bind:this={briefEl}
						bind:value={brief}
						rows="3"
						placeholder={$i18n.t('Ex : relancer mes clients qui n’ont pas payé, avec tact et sans les braquer')}
						class="w-full text-base bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-2xl px-4 py-3.5 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition resize-none"
						on:keydown={(e) => {
							if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') generate();
						}}
					></textarea>

					<!-- Documents (optionnel) — la procédure existe souvent déjà en fichier -->
					<div
						class="mt-3 rounded-2xl border border-dashed {dragOver
							? 'border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-850'
							: 'border-gray-200 dark:border-gray-800'} transition px-4 py-3"
						role="button"
						tabindex="0"
						on:click={() => fileInput?.click()}
						on:keydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') fileInput?.click();
						}}
						on:dragover|preventDefault={() => (dragOver = true)}
						on:dragleave={() => (dragOver = false)}
						on:drop={onDrop}
					>
						<input
							bind:this={fileInput}
							type="file"
							class="hidden"
							multiple
							accept=".pdf,.doc,.docx,.txt,.md,.rtf,.png,.jpg,.jpeg"
							on:change={onPick}
						/>

						{#if sources.length === 0}
							<div class="flex items-center justify-center gap-2 text-sm text-gray-500 py-1">
								{#if uploading}
									<Spinner className="size-4" />{$i18n.t('Lecture du document…')}
								{:else}
									<span>📎</span>{$i18n.t('Vous avez une procédure ? Glissez vos documents (optionnel)')}
								{/if}
							</div>
						{:else}
							<div class="flex flex-wrap items-center gap-2">
								{#each sources as s (s.name)}
									<span
										class="inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 text-gray-700 dark:text-gray-200"
									>
										<span>📄</span>
										<span class="max-w-[180px] truncate">{s.name}</span>
										<button
											class="text-gray-400 hover:text-gray-700 dark:hover:text-white"
											on:click|stopPropagation={() => removeSource(s.name)}
											aria-label={$i18n.t('Retirer')}>✕</button
										>
									</span>
								{/each}
								{#if uploading}
									<span class="inline-flex items-center gap-1.5 text-xs text-gray-500">
										<Spinner className="size-3.5" />{$i18n.t('Lecture…')}
									</span>
								{:else if sources.length < MAX_DOCS}
									<span class="text-xs text-gray-400">{$i18n.t('+ ajouter')}</span>
								{/if}
							</div>
							<div class="text-[11px] text-gray-400 mt-1.5">
								{$i18n.t('{{n}} documents maximum — l’agent s’appuiera dessus.', {
									n: MAX_DOCS
								})}
							</div>
						{/if}
					</div>

					<!-- Mode guidé : 3 questions de capture pour un agent sur-mesure -->
					<div class="mt-3">
						<button
							class="mx-auto flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
							on:click={() => (guidedOpen = !guidedOpen)}
							aria-expanded={guidedOpen}
						>
							<span>✨</span>
							{guidedOpen
								? $i18n.t('Masquer les questions')
								: $i18n.t('Répondre à 3 questions pour un agent sur-mesure')}
						</button>

						{#if guidedOpen}
							<div class="mt-3 space-y-3 text-left" in:fly={{ y: 8, duration: 200 }}>
								<div>
									<div class="text-xs text-gray-500 mb-1">
										{$i18n.t('1. Racontez un cas concret récent, étape par étape')}
									</div>
									<textarea
										bind:value={gWalkthrough}
										rows="2"
										placeholder={$i18n.t(
											'Ex : le client appelle, je note ses coordonnées, je regarde le planning, je propose un créneau…'
										)}
										class="w-full text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition resize-none"
									></textarea>
								</div>
								<div>
									<div class="text-xs text-gray-500 mb-1">
										{$i18n.t('2. Qu’est-ce qui se passe quand ça déraille ?')}
									</div>
									<textarea
										bind:value={gExceptions}
										rows="2"
										placeholder={$i18n.t(
											'Ex : le client annule à la dernière minute, ou la pièce n’est pas en stock…'
										)}
										class="w-full text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition resize-none"
									></textarea>
								</div>
								<div>
									<div class="text-xs text-gray-500 mb-1">
										{$i18n.t('3. C’est réussi quand ?')}
									</div>
									<textarea
										bind:value={gSuccess}
										rows="2"
										placeholder={$i18n.t(
											'Ex : le rendez-vous est confirmé, noté dans l’agenda, et le client a reçu un récapitulatif…'
										)}
										class="w-full text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition resize-none"
									></textarea>
								</div>
							</div>
						{/if}
					</div>

					<div class="flex flex-wrap gap-2 justify-center mt-4">
						{#each ideas as idea}
							<button
								class="text-xs px-3 py-1.5 rounded-full border border-gray-150 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								on:click={() => useIdea(idea)}
							>
								{idea}
							</button>
						{/each}
					</div>
				</div>

				<div class="mt-8 flex justify-center">
					<button
						class="text-sm font-medium px-6 py-3 rounded-2xl btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
						disabled={!canGenerate}
						on:click={generate}
					>
						✨ {$i18n.t('Créer mon agent')}
					</button>
				</div>
				<div class="text-center text-[11px] text-gray-400 mt-3">
					{$i18n.t('Astuce : ⌘ + Entrée pour lancer')}
				</div>
			{:else if phase === 'generating'}
				<div class="flex flex-col items-center gap-6 mt-[20vh]" in:fade>
					<div class="atelier-orb"></div>
					<div class="text-lg font-medium">{$i18n.t('Je fabrique votre agent…')}</div>
					<div class="text-sm text-gray-500 transition-all">{genMsg}</div>
				</div>
			{:else if phase === 'result' && result}
				<div in:fly={{ y: 16, duration: 350 }}>
					<!-- En-tête de l'agent -->
					<div class="flex items-center gap-4 mt-[4vh]">
						<div class="group/av relative flex-none">
							<button
								type="button"
								class="size-16 rounded-3xl overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-850 dark:to-gray-800 flex items-center justify-center text-4xl shadow-sm ring-1 ring-transparent group-hover/av:ring-gray-300 dark:group-hover/av:ring-gray-600 transition"
								on:click={() => (showAvatarPicker = true)}
								title={$i18n.t('Changer le visage')}
								aria-label={$i18n.t('Changer le visage')}
							>
								{#if selectedAvatar}
									<img src={selectedAvatar} alt="" class="size-full object-cover object-top" />
								{:else}
									<span>{result.emoji}</span>
								{/if}
								<span
									class="absolute inset-0 flex items-center justify-center bg-black/45 text-white text-[10px] font-medium opacity-0 group-hover/av:opacity-100 transition"
								>
									{$i18n.t('Changer')}
								</span>
							</button>
							<!-- Pastille « modifiable » toujours visible (affordance pour non-tech) -->
							<span
								aria-hidden="true"
								class="pointer-events-none absolute -bottom-1 -right-1 size-6 rounded-full bg-white dark:bg-gray-800 shadow-md ring-1 ring-gray-200 dark:ring-gray-700 flex items-center justify-center text-gray-600 dark:text-gray-300 group-hover/av:scale-110 transition"
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-3.5">
									<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
									<circle cx="12" cy="13" r="3.5" />
								</svg>
							</span>
						</div>
						<div class="min-w-0 flex-1">
							{#if editing}
								<input
									bind:value={editLabel}
									class="w-full text-2xl font-semibold bg-transparent border-b border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 pb-0.5"
								/>
								<input
									bind:value={editDescription}
									class="w-full text-sm text-gray-500 bg-transparent border-b border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 mt-1.5 pb-0.5"
								/>
							{:else}
								<div class="text-2xl font-semibold truncate">{result.label}</div>
								<div class="text-sm text-gray-500">{result.description}</div>
							{/if}
						</div>
					</div>

					<!-- Sa mission, en sections lisibles (éditable directement) -->
					<div class="mt-6 space-y-3">
						{#if editing}
							{#each editSections as s (s.title)}
								<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-4">
									<div class="flex items-center gap-2 text-sm font-semibold">
										<span>{s.icon}</span>{s.title}
									</div>
									<textarea
										bind:value={s.body}
										rows={Math.max(3, s.body.split('\n').length)}
										class="w-full text-sm text-gray-700 dark:text-gray-200 mt-2 bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition resize-y leading-relaxed"
									></textarea>
								</div>
							{/each}
						{:else}
							<MissionSections soul={result.soul} />
						{/if}
					</div>

					<!-- Ajustement en langage naturel -->
					{#if showAdjust}
						<div class="mt-4 flex flex-col sm:flex-row gap-2" in:fly={{ y: 8, duration: 200 }}>
							<input
								bind:value={adjustment}
								placeholder={$i18n.t('Ex : rends-le plus diplomate, ajoute la relance par SMS')}
								class="flex-1 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
								on:keydown={(e) => {
									if (e.key === 'Enter' && adjustment.trim()) regenerate();
								}}
							/>
							<button
								class="text-sm px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-40"
								disabled={!adjustment.trim()}
								on:click={regenerate}>{$i18n.t('Régénérer')}</button
							>
						</div>
					{/if}
				</div>
			{:else if phase === 'error'}
				<div class="text-center mt-[18vh] flex flex-col items-center gap-3" in:fade>
					<div class="text-3xl">😕</div>
					<div class="text-lg font-medium">{$i18n.t('La génération a échoué')}</div>
					<div class="text-sm text-gray-500 max-w-sm">{errorMsg}</div>
					<button
						class="mt-3 text-sm px-5 py-2.5 rounded-2xl btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
						on:click={generate}>{$i18n.t('Réessayer')}</button
					>
				</div>
			{/if}
		</div>

		<!-- Barre d'actions (uniquement sur le résultat) -->
		{#if phase === 'result' && result}
			<div
				class="sticky bottom-0 z-10 bg-white/85 dark:bg-gray-900/85 backdrop-blur border-t border-gray-100 dark:border-gray-850"
			>
				<div class="max-w-2xl mx-auto px-5 py-3.5 flex items-center justify-between gap-3">
					<button
						class="text-sm px-3 py-2 rounded-xl text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
						on:click={restart}>↻ {$i18n.t('Recommencer')}</button
					>
					<div class="flex items-center gap-2">
						{#if editing}
							<button
								class="text-sm px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={finishEditing}>✓ {$i18n.t('Terminé')}</button
							>
						{:else}
							<button
								class="text-sm px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={startEditing}>✏️ {$i18n.t('Modifier')}</button
							>
							<button
								class="text-sm px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => (showAdjust = !showAdjust)}>{$i18n.t('Ajuster')}</button
							>
						{/if}
						<button
							class="text-sm font-medium px-5 py-2 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-50"
							disabled={activating}
							on:click={activate}
						>
							{activating ? $i18n.t('Activation…') : '✓ ' + $i18n.t('Activer cet agent')}
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Galerie de sélection d'avatar (par-dessus l'atelier) -->
		<AvatarPicker bind:show={showAvatarPicker} bind:value={selectedAvatar} {used} />
	</div>
{/if}

<style>
	.atelier-orb {
		width: 64px;
		height: 64px;
		border-radius: 9999px;
		background: conic-gradient(from 0deg, #6366f1, #8b5cf6, #ec4899, #6366f1);
		filter: blur(2px);
		animation: orb-spin 1.4s linear infinite, orb-pulse 1.8s ease-in-out infinite;
	}
	@keyframes orb-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@keyframes orb-pulse {
		0%,
		100% {
			transform: scale(0.92);
			opacity: 0.85;
		}
		50% {
			transform: scale(1.08);
			opacity: 1;
		}
	}
</style>
