<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	import { config, models, settings } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { chatCompletion } from '$lib/apis/openai';
	import { splitStream } from '$lib/utils';

	import {
		getMemoryTree,
		getMemoryStatus,
		getMemoryNote,
		saveMemoryNote,
		initMemoryVault
	} from '$lib/apis/memory';
	import type { MemoryNode, MemoryStatus } from '$lib/apis/memory';

	import type { Editor } from '@tiptap/core';

	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import SparklesSolid from '$lib/components/icons/SparklesSolid.svelte';
	import MicSolid from '$lib/components/icons/MicSolid.svelte';

	import AiMenu from '$lib/components/notes/AIMenu.svelte';
	import RecordMenu from '$lib/components/notes/RecordMenu.svelte';
	import VoiceRecording from '$lib/components/chat/MessageInput/VoiceRecording.svelte';

	// ─── State ───────────────────────────────────────────────────────────────

	let loaded = false;
	let tree: MemoryNode[] = [];
	let status: MemoryStatus | null = null;

	// Vue : 'list' | 'editor'
	let view: 'list' | 'editor' = 'list';

	// Liste
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout> | undefined = undefined;

	// Éditeur
	let selectedNode: MemoryNode | null = null;
	let currentMd = '';
	let loadingNote = false;
	let saveState: 'idle' | 'saving' | 'saved' = 'idle';
	let saveTimeout: ReturnType<typeof setTimeout>;
	// Sauvegarde en attente (debounce) : permet de la flusher avant de quitter la note.
	let pendingSave: { path: string; md: string } | null = null;

	let inputElement: RichTextInput | null = null;
	let editor: Editor | null = null;

	// FABs
	let recording = false;
	let displayMediaRecord = false;
	let editing = false;
	let streaming = false;
	let stopResponseFlag = false;
	let selectedModelId = '';

	// ─── Données ──────────────────────────────────────────────────────────────

	// Aplatir l'arbre en liste avec info de dossier parent
	type FlatNote = MemoryNode & { folder: string };

	const flattenNotes = (nodes: MemoryNode[], folder = ''): FlatNote[] => {
		const acc: FlatNote[] = [];
		for (const n of nodes) {
			if (n.type === 'folder') {
				const sub = flattenNotes(n.children ?? [], n.name);
				acc.push(...sub);
			} else {
				acc.push({ ...n, folder });
			}
		}
		return acc;
	};

	// Notes filtrées par la recherche
	$: allNotes = flattenNotes(tree);

	$: filteredNotes = query.trim()
		? allNotes.filter((n) =>
				n.name.toLowerCase().includes(query.toLowerCase())
			)
		: allNotes;

	// Notes groupées par dossier
	const groupByFolder = (notes: FlatNote[]): [string, FlatNote[]][] => {
		const map = new Map<string, FlatNote[]>();
		for (const n of notes) {
			const key = n.folder || '';
			if (!map.has(key)) map.set(key, []);
			map.get(key)!.push(n);
		}
		return Array.from(map.entries());
	};

	$: groupedNotes = groupByFolder(filteredNotes);

	// ─── Chargement ───────────────────────────────────────────────────────────

	const load = async () => {
		loaded = false;
		try {
			const token = localStorage.token;
			const [t, s] = await Promise.all([getMemoryTree(token), getMemoryStatus(token)]);
			tree = t?.tree ?? [];
			status = s;
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de charger la mémoire');
		}
		loaded = true;
	};

	// ─── Navigation ───────────────────────────────────────────────────────────

	const openNote = async (node: MemoryNode) => {
		if (node.type !== 'note') return;
		loadingNote = true;
		saveState = 'idle';
		editor = null;
		inputElement = null;
		try {
			const res = await getMemoryNote(localStorage.token, node.path);
			selectedNode = node;
			currentMd = res.content ?? '';
			view = 'editor';
		} catch (e) {
			toast.error(typeof e === 'string' ? e : "Impossible d'ouvrir cette note");
		}
		loadingNote = false;
	};

	const goBack = async () => {
		// Flush la sauvegarde en attente : ne pas perdre la dernière modif si on revient
		// pendant le délai du debounce.
		await flushSave();
		view = 'list';
		selectedNode = null;
		currentMd = '';
		saveState = 'idle';
		clearTimeout(saveTimeout);
	};

	// ─── Nouvelle note ────────────────────────────────────────────────────────

	const newNote = async () => {
		const title = (prompt('Nom de la nouvelle note ?') ?? '').trim();
		if (!title) return;
		const path = `${title}.md`;
		try {
			await saveMemoryNote(localStorage.token, path, `# ${title}\n\n`);
			await load();
			const node: MemoryNode = { path, name: title, type: 'note', children: [] };
			await openNote(node);
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de créer la note');
		}
	};

	// ─── Initialiser la structure du coffre (PARA) ────────────────────────────

	let initializing = false;

	const initVault = async () => {
		initializing = true;
		try {
			const res = await initMemoryVault(localStorage.token);
			const n = res?.created?.length ?? 0;
			toast.success(n > 0 ? `Structure créée (${n} dossiers)` : 'Structure déjà en place');
			await load();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : "Impossible d'initialiser le coffre");
		}
		initializing = false;
	};

	// ─── Sauvegarde débouncée ─────────────────────────────────────────────────

	// Écrit immédiatement la sauvegarde en attente (s'il y en a une), en annulant le timer.
	const flushSave = async () => {
		if (!pendingSave) return;
		clearTimeout(saveTimeout);
		const { path, md } = pendingSave;
		pendingSave = null;
		saveState = 'saving';
		try {
			await saveMemoryNote(localStorage.token, path, md);
			saveState = 'saved';
		} catch (e) {
			saveState = 'idle';
			toast.error(typeof e === 'string' ? e : "Échec de l'enregistrement");
		}
	};

	const scheduleSave = (md: string) => {
		if (!selectedNode) return;
		currentMd = md;
		saveState = 'saving';
		pendingSave = { path: selectedNode.path, md };
		clearTimeout(saveTimeout);
		saveTimeout = setTimeout(flushSave, 600);
	};

	// ─── Enhance (FAB AI) ─────────────────────────────────────────────────────

	const stopResponseHandler = () => {
		stopResponseFlag = true;
	};

	const enhanceNoteHandler = async () => {
		if (!selectedModelId) {
			toast.error('Veuillez sélectionner un modèle.');
			return;
		}

		const model = $models
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			.filter((m) => !((m?.info?.meta as any)?.hidden ?? false))
			.find((m) => m.id === selectedModelId);

		if (!model) {
			toast.error('Modèle introuvable.');
			return;
		}

		editing = true;
		stopResponseFlag = false;

		const systemPrompt = `Améliore les notes existantes en les rendant plus claires, mieux structurées et plus complètes.
Garde la langue d'origine. Retourne uniquement le texte en markdown.`;

		let enhanced = '';

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{ role: 'system', content: systemPrompt },
					{ role: 'user', content: `<notes>${currentMd}</notes>` }
				]
			},
			`${WEBUI_BASE_URL}/api`
		);

		streaming = true;

		if (res && res.ok && res.body) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) controller.abort('User: Stop Response');
					break;
				}
				try {
					const lines = value.split('\n');
					for (const line of lines) {
						if (!line || line === 'data: [DONE]') continue;
						const data = JSON.parse(line.replace(/^data: /, ''));
						const delta = data?.choices?.[0]?.delta?.content;
						if (delta) {
							enhanced += delta;
							currentMd = enhanced;
						}
					}
				} catch (_) {
					// ignore parse errors mid-stream
				}
			}
		}

		streaming = false;
		editing = false;

		// Recharge l'éditeur avec le contenu amélioré
		await tick();
		if (inputElement && enhanced) {
			scheduleSave(enhanced);
		}
	};

	// ─── VoiceRecording (insertion du texte transcrit) ────────────────────────

	const onVoiceConfirm = async (data: { text?: string; file?: File }) => {
		recording = false;
		displayMediaRecord = false;
		if (data?.text) {
			const inserted = `\n\n${data.text}`;
			currentMd = currentMd + inserted;
			scheduleSave(currentMd);
		}
	};

	// ─── Cycle de vie ─────────────────────────────────────────────────────────

	onMount(async () => {
		await load();

		// Sélectionner le modèle par défaut
		if ($settings?.models) {
			selectedModelId = $settings.models[0] ?? '';
		} else if ($config?.default_models) {
			selectedModelId = $config.default_models.split(',')[0];
		}

		if (selectedModelId) {
			const exists = $models
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				.filter((m) => !((m?.info?.meta as any)?.hidden ?? false))
				.find((m) => m.id === selectedModelId);
			if (!exists) selectedModelId = '';
		}

		if (!selectedModelId) {
			selectedModelId =
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				$models.filter((m) => !((m?.info?.meta as any)?.hidden ?? false))[0]?.id ?? '';
		}
	});

	onDestroy(() => {
		// Best-effort : déclenche la sauvegarde en attente avant de détruire le composant.
		flushSave();
		clearTimeout(saveTimeout);
		clearTimeout(searchDebounceTimer);
	});
</script>

<!-- ═══════════════════════════════════════════════════════════════════════════
     VUE LISTE
     ═══════════════════════════════════════════════════════════════════════════ -->

{#if view === 'list'}
	<div class="w-full min-h-full h-full px-3 md:px-[18px]">
		{#if loaded}
			<!-- Header : titre + compteur + bouton nouvelle note -->
			<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
				<div class="flex justify-between items-center">
					<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
						<div>Mémoire</div>
						<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
							{allNotes.length}
						</div>
					</div>

					<div class="flex w-full justify-end gap-1.5">
						<button
							class="px-2 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-850 transition font-medium text-xs flex items-center disabled:opacity-50"
							on:click={initVault}
							disabled={initializing}
							title="Crée la structure de rangement du coffre (Réception, Projets, Domaines…)"
						>
							{initializing ? 'Initialisation…' : 'Initialiser le coffre'}
						</button>
						<button
							class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
							on:click={newNote}
						>
							<Plus className="size-3" strokeWidth="2.5" />
							<div class="ml-1 text-xs">Nouvelle note</div>
						</button>
					</div>
				</div>

				<!-- Statut honnête -->
				{#if status}
					<div class="flex items-center gap-1.5 px-0.5 text-xs text-gray-500 dark:text-gray-500">
						{#if status.ok}
							<span class="relative flex size-2 shrink-0">
								<span
									class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60"
								></span>
								<span class="relative inline-flex size-2 rounded-full bg-green-500"></span>
							</span>
							<span>Mémoire active</span>
							<span class="text-gray-300 dark:text-gray-700">·</span>
							<span>Partagée avec votre assistant</span>
							<span class="text-gray-300 dark:text-gray-700">·</span>
							<span>{status.note_count} notes</span>
							{#if status.local_copy}
								<span class="text-gray-300 dark:text-gray-700">·</span>
								<span>Copie locale reliée</span>
							{/if}
						{:else}
							<span class="relative flex size-2 shrink-0">
								<span class="relative inline-flex size-2 rounded-full bg-amber-500"></span>
							</span>
							<span class="text-amber-600 dark:text-amber-400">Mémoire indisponible</span>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Panneau recherche (markup identique à Notes.svelte) -->
			<div
				class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
			>
				<div class="px-3.5 flex flex-1 items-center w-full space-x-2 py-0.5 pb-2">
					<div class="flex flex-1 items-center">
						<div class="self-center ml-1 mr-3">
							<Search className="size-3.5" />
						</div>
						<input
							class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
							bind:value={query}
							placeholder="Rechercher dans la mémoire"
						/>
						{#if query}
							<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
								<button
									class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
									on:click={() => { query = ''; }}
								>
									<XMark className="size-3" strokeWidth="2" />
								</button>
							</div>
						{/if}
					</div>
				</div>

				<!-- Liste organisée par dossier -->
				{#if groupedNotes.length > 0}
					<div class="@container h-full py-2.5 px-2.5">
						<div>
							{#each groupedNotes as [folder, notes], idx}
								<!-- Titre de section (dossier) — même style que le groupement par date dans Notes -->
								{#if folder}
									<div
										class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium px-2.5 pb-2.5 uppercase tracking-wide"
									>
										{folder}
									</div>
								{/if}

								<div class="{groupedNotes.length - 1 !== idx ? 'mb-3' : ''} gap-1.5 flex flex-col">
									{#each notes as note}
										<div
											class="flex cursor-pointer w-full px-3.5 py-1.5 border border-gray-50 dark:border-gray-850/30 bg-transparent dark:hover:bg-gray-850 hover:bg-white rounded-2xl transition"
											on:click={() => openNote(note)}
											on:keydown={(e) => e.key === 'Enter' && openNote(note)}
											role="button"
											tabindex="0"
										>
											<div class="w-full flex flex-col justify-between">
												<div class="flex-1">
													<div class="flex items-center gap-2 self-center justify-between">
														<Tooltip content={note.name} className="flex-1" placement="top-start">
															<div class="text-sm font-medium capitalize flex-1 w-full line-clamp-1">
																{note.name}
															</div>
														</Tooltip>
													</div>
												</div>
											</div>
										</div>
									{/each}
								</div>
							{/each}
						</div>
					</div>
				{:else if query}
					<!-- Recherche sans résultats -->
					<div class="w-full h-full flex flex-col items-center justify-center">
						<div class="py-20 text-center">
							<div class="text-sm text-gray-400 dark:text-gray-600">
								Aucune note trouvée pour « {query} »
							</div>
						</div>
					</div>
				{:else}
					<!-- État vide accueillant -->
					<div class="w-full h-full flex flex-col items-center justify-center">
						<div class="py-20 text-center">
							<div class="text-sm text-gray-400 dark:text-gray-600">
								Votre mémoire se remplira au fil de vos échanges.
							</div>
							<div class="mt-1 text-xs text-gray-300 dark:text-gray-700">
								Créez votre première note, ou mettez en place le rangement du coffre.
							</div>
							<button
								class="mt-3 px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-xs disabled:opacity-50"
								on:click={initVault}
								disabled={initializing}
							>
								{initializing ? 'Initialisation…' : 'Créer la structure du coffre'}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<div class="w-full h-full flex justify-center items-center">
				<Spinner className="size-4" />
			</div>
		{/if}
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════════
     VUE ÉDITEUR
     ═══════════════════════════════════════════════════════════════════════════ -->
{:else if view === 'editor'}
	<div class="relative flex-1 w-full h-full flex justify-center pt-[11px]" id="memory-editor">
		{#if loadingNote}
			<div class="absolute top-0 bottom-0 left-0 right-0 flex">
				<div class="m-auto"><Spinner className="size-5" /></div>
			</div>
		{:else}
			<div class="w-full flex flex-col">
				<!-- Barre supérieure : retour + titre + indicateur sauvegarde -->
				<div class="shrink-0 w-full flex justify-between items-center px-3.5 mb-1.5">
					<div class="w-full min-w-0 flex items-center gap-2">
						<!-- Bouton retour -->
						<Tooltip content="Retour à la liste">
							<button
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition p-1.5 shrink-0"
								on:click={goBack}
							>
								<ChevronLeft className="size-4" />
							</button>
						</Tooltip>

						<!-- Titre de la note (non éditable en v1) -->
						<input
							class="w-full text-2xl font-medium bg-transparent outline-hidden"
							type="text"
							value={selectedNode?.name ?? ''}
							placeholder="Sans titre"
							disabled
						/>
					</div>

					<!-- Indicateur de sauvegarde -->
					<div class="shrink-0 text-xs text-gray-500 dark:text-gray-500 pr-1">
						{#if saveState === 'saving'}
							Enregistrement…
						{:else if saveState === 'saved'}
							Enregistré
						{/if}
					</div>
				</div>

				<!-- Zone d'édition principale -->
				<div
					class="flex-1 w-full h-full overflow-auto px-3.5 relative"
					id="memory-content-container"
				>
					{#if editing}
						<div
							class="w-full h-full fixed top-0 left-0 {streaming
								? ''
								: 'backdrop-blur-xs bg-white/10 dark:bg-gray-900/10'} flex items-center justify-center z-10 cursor-not-allowed"
						></div>
					{/if}

					{#key selectedNode?.path}
						<RichTextInput
							bind:this={inputElement}
							bind:editor
							id={`memory-${selectedNode?.path ?? 'note'}`}
							className="input-prose-sm px-0.5 h-[calc(100%-2rem)]"
							html={currentMd ? (marked.parse(currentMd) ) : ''}
							dragHandle={true}
							link={true}
							image={true}
							placeholder="Écrivez quelque chose…"
							editable={!editing}
							onChange={(content) => {
								scheduleSave(content.md ?? '');
							}}
						/>
					{/key}
				</div>
			</div>
		{/if}

		<!-- FABs flottants (markup EXACT de NoteEditor.svelte) -->
		<div class="absolute z-50 bottom-0 right-0 p-3.5 flex select-none">
			<div class="flex flex-col gap-2 justify-end">
				{#if recording}
					<div class="flex-1 w-full">
						<VoiceRecording
							bind:recording
							className="p-1 w-full max-w-full"
							transcribe={true}
							displayMedia={displayMediaRecord}
							echoCancellation={false}
							noiseSuppression={false}
							onCancel={() => {
								recording = false;
								displayMediaRecord = false;
							}}
							onConfirm={onVoiceConfirm}
						/>
					</div>
				{:else}
					<!-- FAB AI -->
					<div
						class="cursor-pointer flex gap-0.5 rounded-full border border-gray-50 dark:border-gray-850/30 dark:bg-gray-850 transition shadow-xl"
					>
						<Tooltip content="IA" placement="top">
							{#if editing}
								<button
									class="p-2 flex justify-center items-center hover:bg-gray-50 dark:hover:bg-gray-800 rounded-full transition shrink-0"
									on:click={stopResponseHandler}
									type="button"
								>
									<Spinner className="size-5" />
								</button>
							{:else}
								<AiMenu
									onEdit={enhanceNoteHandler}
									onChat={() => {}}
								>
									<div
										class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
									>
										<SparklesSolid />
									</div>
								</AiMenu>
							{/if}
						</Tooltip>
					</div>

					<!-- FAB Record -->
					<RecordMenu
						onRecord={async () => {
							displayMediaRecord = false;
							try {
								const stream = await navigator.mediaDevices
									.getUserMedia({ audio: true })
									.catch((err) => {
										toast.error(`Permission micro refusée : ${err}`);
										return null;
									});
								if (stream) {
									recording = true;
									stream.getTracks().forEach((t) => t.stop());
								}
							} catch {
								toast.error('Permission micro refusée');
							}
						}}
						onCaptureAudio={() => {
							displayMediaRecord = true;
							recording = true;
						}}
						onUpload={() => {
							const input = document.createElement('input');
							input.type = 'file';
							input.accept = 'audio/*';
							input.click();
							input.onchange = async (e) => {
								const target = e.target as HTMLInputElement;
								const file = target.files?.[0];
								if (file) toast.info('Fichier audio reçu — transcription non implémentée en v1.');
							};
						}}
					>
						<Tooltip content="Enregistrer" placement="top">
							<div
								class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
							>
								<MicSolid className="size-4.5" />
							</div>
						</Tooltip>
					</RecordMenu>
				{/if}
			</div>
		</div>
	</div>
{/if}
