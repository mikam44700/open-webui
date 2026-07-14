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
		initMemoryVault,
		getSyncPack,
		downloadSyncPack,
		searchMemory,
		deleteMemoryNote,
		restoreMemoryNote,
		renameMemoryNote
	} from '$lib/apis/memory';
	import type { MemoryNode, MemoryStatus, SearchResult } from '$lib/apis/memory';

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

	// Liste / recherche serveur
	let query = '';
	let queryTimer: ReturnType<typeof setTimeout> | undefined = undefined;
	let searching = false;
	let searchResults: SearchResult[] = [];
	let searchSeq = 0;

	// Arbre : dossiers repliés/dépliés (persistés) + affichage progressif des grosses listes
	const NOTE_CAP = 40; // notes rendues d'emblée par dossier (le reste via « Afficher les autres »)
	let openState: Record<string, boolean> = {}; // choix explicites de dépliage (persistés)
	let expandedFull: Record<string, boolean> = {}; // dossiers affichant TOUTES leurs notes

	// Éditeur
	let titleDraft = ''; // titre éditable (renommage)
	let titleInput: HTMLInputElement | null = null;
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

	// ─── Données & arbre ───────────────────────────────────────────────────────

	// Aplatir l'arbre (pour compter et garantir des noms uniques à la création).
	const flattenNotes = (nodes: MemoryNode[]): MemoryNode[] => {
		const acc: MemoryNode[] = [];
		for (const n of nodes) {
			if (n.type === 'folder') acc.push(...flattenNotes(n.children ?? []));
			else acc.push(n);
		}
		return acc;
	};
	$: allNotes = flattenNotes(tree);

	// Noms de dossiers PARA traduits en langage dirigeant (les autres gardent leur nom).
	const FRIENDLY_FOLDER: Record<string, string> = {
		'00-Réception': 'Réception',
		'01-Projets': 'En cours',
		'02-Domaines': 'Mon activité',
		'03-Ressources': 'Idées & ressources',
		'04-Archives': 'Archivées',
		Journal: 'Journal',
		Personnes: 'Personnes',
		_Modèles: 'Modèles',
		_Cartes: 'Cartes'
	};
	const friendlyFolder = (name: string): string => FRIENDLY_FOLDER[name] ?? name;

	const splitChildren = (node: MemoryNode): { folders: MemoryNode[]; notes: MemoryNode[] } => {
		const children = node.children ?? [];
		return {
			folders: children.filter((c) => c.type === 'folder'),
			notes: children.filter((c) => c.type === 'note')
		};
	};

	const countNotes = (node: MemoryNode): number =>
		(node.children ?? []).reduce((sum, c) => sum + (c.type === 'note' ? 1 : countNotes(c)), 0);

	// Dépliage : niveau 0 ouvert par défaut, sous-dossiers fermés (scalable à 1000+ notes).
	const isOpen = (path: string, depth: number): boolean => openState[path] ?? depth === 0;
	const toggleOpen = (path: string, depth: number): void => {
		openState = { ...openState, [path]: !isOpen(path, depth) };
		try {
			localStorage.setItem('lunaria:memory-open', JSON.stringify(openState));
		} catch {
			/* localStorage indisponible : dépliage non persisté, sans conséquence */
		}
	};
	const capFor = (node: MemoryNode): number =>
		expandedFull[node.path] ? Number.POSITIVE_INFINITY : NOTE_CAP;
	const showAllIn = (path: string): void => {
		expandedFull = { ...expandedFull, [path]: true };
	};

	// ─── Recherche serveur (FTS5) : scalable, ne scanne pas les notes côté client ──
	const runSearch = async (q: string): Promise<void> => {
		const my = ++searchSeq;
		const trimmed = q.trim();
		if (!trimmed) {
			searchResults = [];
			searching = false;
			return;
		}
		searching = true;
		try {
			const res = await searchMemory(localStorage.token, trimmed, 30);
			if (my === searchSeq) searchResults = res?.results ?? [];
		} catch (_) {
			if (my === searchSeq) searchResults = [];
		}
		if (my === searchSeq) searching = false;
	};
	// Débounce : relance la recherche 300 ms après la dernière frappe.
	const scheduleSearch = () => {
		clearTimeout(queryTimer);
		const q = query;
		queryTimer = setTimeout(() => runSearch(q), 300);
	};

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
			titleDraft = node.name;
			currentMd = res.content ?? '';
			view = 'editor';
		} catch (e) {
			toast.error(typeof e === 'string' ? e : "Impossible d'ouvrir cette note");
		}
		loadingNote = false;
	};

	// Ouvre une note à partir d'un simple chemin (résultat de recherche).
	const openNoteByPath = (path: string, name: string) =>
		openNote({ path, name, type: 'note', children: [] });

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

	// ─── Nouvelle note (création propre, sans prompt natif) ────────────────────

	const newNote = async () => {
		const base = 'Nouvelle note';
		const existing = new Set(allNotes.map((x) => x.name.toLowerCase()));
		let title = base;
		let i = 2;
		while (existing.has(title.toLowerCase())) title = `${base} ${i++}`;
		try {
			await saveMemoryNote(localStorage.token, `${title}.md`, '');
			await load();
			await openNote({ path: `${title}.md`, name: title, type: 'note', children: [] });
			// Titre prêt à être renommé tout de suite.
			await tick();
			titleInput?.focus();
			titleInput?.select();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de créer la note');
		}
	};

	// ─── Renommage (titre éditable) ────────────────────────────────────────────

	const commitRename = async () => {
		if (!selectedNode) return;
		const t = titleDraft.trim();
		if (!t || t === selectedNode.name) {
			titleDraft = selectedNode.name;
			return;
		}
		try {
			const res = await renameMemoryNote(localStorage.token, selectedNode.path, t);
			selectedNode = { ...selectedNode, path: res.path, name: t };
			titleDraft = t;
			await load();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de renommer la note');
			titleDraft = selectedNode.name;
		}
	};

	// ─── Suppression douce (corbeille) + annulation ────────────────────────────

	const deleteNote = async (node: MemoryNode, fromEditor = false) => {
		try {
			const res = await deleteMemoryNote(localStorage.token, node.path);
			if (fromEditor) {
				view = 'list';
				selectedNode = null;
				currentMd = '';
			}
			await load();
			toast.success(`« ${node.name} » supprimée`, {
				action: {
					label: 'Annuler',
					onClick: async () => {
						try {
							await restoreMemoryNote(localStorage.token, res.trash_ref, res.path);
							await load();
							toast.success('Note restaurée');
						} catch (e) {
							toast.error(typeof e === 'string' ? e : 'Impossible de restaurer la note');
						}
					}
				}
			});
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de supprimer la note');
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

	// ─── Connexion du coffre à Obsidian (sync Syncthing pré-appairée) ─────────
	let connectingSync = false;

	const connectVault = async () => {
		connectingSync = true;
		try {
			const pack = await getSyncPack(localStorage.token);
			downloadSyncPack(pack);
			toast.success('Coffre prêt — ouvrez le fichier téléchargé pour le connecter à Obsidian.');
		} catch (e) {
			toast.error(
				typeof e === 'string'
					? e
					: "La synchronisation avec Obsidian n'est pas encore disponible sur ce serveur."
			);
		}
		connectingSync = false;
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
		// Restaure l'état de dépliage des dossiers (persisté).
		try {
			const raw = localStorage.getItem('lunaria:memory-open');
			if (raw) openState = JSON.parse(raw);
		} catch {
			/* état de dépliage illisible : on repart des défauts */
		}

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
		clearTimeout(queryTimer);
	});
</script>

<!-- ═══════════════════════════════════════════════════════════════════════════
     VUE LISTE
     ═══════════════════════════════════════════════════════════════════════════ -->

{#if view === 'list'}
	<div class="w-full min-h-full h-full px-3 md:px-[18px]">
		{#if loaded}
			<!-- Adam : le gardien de la mémoire — incarne la page (avatar + rôle) + action « Nouvelle note ». -->
			<div class="mt-3 mb-3 flex items-center gap-3 px-1">
				<img
					src="/assets/agents/adam.webp"
					alt="Adam"
					on:error={(e) => ((e.currentTarget as HTMLImageElement).src = '/favicon.png')}
					class="flex-none h-11 w-11 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15 bg-sky-100 dark:bg-sky-900/30"
				/>
				<div class="min-w-0 flex-1">
					<div class="text-sm font-semibold text-gray-900 dark:text-white">
						Adam
						<span class="font-normal text-gray-400 dark:text-gray-500">· votre gardien de mémoire</span>
					</div>
					<div class="text-[12.5px] leading-snug text-gray-500 dark:text-gray-400">
						Il range et retrouve tout ce que vous notez, dans votre coffre.
					</div>
				</div>
				<button
					class="flex-none px-2.5 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					on:click={newNote}
				>
					<Plus className="size-3" strokeWidth="2.5" />
					<div class="ml-1 text-xs">Nouvelle note</div>
				</button>
			</div>

			<!-- Bandeau de synchronisation avec Obsidian — 3 états honnêtes. -->
			{#if status}
				{#if !status.ok}
					<div
						class="mb-3 flex items-center gap-2 rounded-2xl bg-amber-50 dark:bg-amber-900/15 ring-1 ring-inset ring-amber-500/20 px-3.5 py-2.5"
					>
						<span class="flex-none size-2 rounded-full bg-amber-500"></span>
						<span class="text-[13px] text-amber-700 dark:text-amber-300"
							>Mémoire momentanément indisponible — réessayez dans un instant.</span
						>
					</div>
				{:else if status.local_copy}
					<div
						class="mb-3 flex items-center gap-2 rounded-2xl bg-emerald-50/70 dark:bg-emerald-900/15 ring-1 ring-inset ring-emerald-500/20 px-3.5 py-2.5"
					>
						<span class="relative flex size-2 flex-none">
							<span
								class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60"
							></span>
							<span class="relative inline-flex size-2 rounded-full bg-emerald-500"></span>
						</span>
						<span class="text-[13px] text-gray-700 dark:text-gray-200"
							>Coffre synchronisé avec votre Obsidian</span
						>
						<span class="text-gray-300 dark:text-gray-600">·</span>
						<span class="text-[13px] text-gray-500 dark:text-gray-400">{status.note_count} notes</span>
					</div>
				{:else}
					<div
						class="mb-3 flex flex-wrap items-center gap-3 rounded-2xl bg-sky-50/70 dark:bg-sky-900/15 ring-1 ring-inset ring-sky-500/20 px-3.5 py-3"
					>
						<div class="min-w-0 flex-1">
							<div class="text-[13px] font-medium text-gray-900 dark:text-white">
								Pas encore connecté à Obsidian
							</div>
							<div class="text-[12px] text-gray-500 dark:text-gray-400">
								Vos {status.note_count} notes sont en sécurité. Connectez votre coffre pour l'ouvrir dans
								Obsidian sur votre ordinateur.
							</div>
						</div>
						<button
							class="flex-none px-3 py-1.5 rounded-xl bg-sky-500/15 text-sky-800 dark:text-sky-200 ring-1 ring-inset ring-sky-500/30 hover:bg-sky-500/25 transition font-semibold text-[12.5px] disabled:opacity-60"
							on:click={connectVault}
							disabled={connectingSync}
						>
							{connectingSync ? 'Préparation…' : 'Connecter mon coffre'}
						</button>
					</div>
				{/if}
			{/if}

			<!-- Snippets récursifs de l'arbre (comme Obsidian) : dossier repliable + ligne de note. -->
			{#snippet noteRow(note: MemoryNode, depth: number)}
				<div
					class="group flex items-center gap-1.5 rounded-lg hover:bg-gray-100/70 dark:hover:bg-white/[0.05] transition"
					style="padding-left: {depth * 16 + 6}px"
				>
					<button
						class="flex-1 min-w-0 flex items-center gap-2 py-1.5 pr-1 text-left"
						on:click={() => openNote(note)}
					>
						<span class="shrink-0 text-gray-400 dark:text-gray-500">
							<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 3h6l4 4v10H5V3Z" stroke-linejoin="round"/><path d="M11 3v4h4" stroke-linejoin="round"/></svg>
						</span>
						<span class="text-[13.5px] text-gray-800 dark:text-gray-100 truncate">{note.name}</span>
					</button>
					<button
						class="shrink-0 mr-1 p-1 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
						title="Supprimer"
						aria-label="Supprimer la note"
						on:click={() => deleteNote(note)}
					>
						<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" stroke-linecap="round" stroke-linejoin="round"/></svg>
					</button>
				</div>
			{/snippet}

			{#snippet folderBlock(node: MemoryNode, depth: number)}
				{@const kids = splitChildren(node)}
				{@const open = isOpen(node.path, depth)}
				<div>
					<button
						class="w-full flex items-center gap-1.5 py-1.5 rounded-lg hover:bg-gray-100/70 dark:hover:bg-white/[0.05] transition text-left"
						style="padding-left: {depth * 16 + 2}px"
						on:click={() => toggleOpen(node.path, depth)}
					>
						<svg
							class="w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform {open ? 'rotate-90' : ''}"
							viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"
						><path d="M8 5l5 5-5 5" stroke-linecap="round" stroke-linejoin="round" /></svg>
						<span class="shrink-0 text-amber-500/80">
							<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"><path d="M2 5.5A1.5 1.5 0 0 1 3.5 4h4l1.5 2h7A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H3.5A1.5 1.5 0 0 1 2 14.5v-9Z" /></svg>
						</span>
						<span class="text-[13.5px] font-medium text-gray-800 dark:text-gray-100 truncate">{friendlyFolder(node.name)}</span>
						{#if countNotes(node)}
							<span class="ml-auto pr-1 text-[11px] text-gray-400 dark:text-gray-600">{countNotes(node)}</span>
						{/if}
					</button>
					{#if open}
						{#each kids.folders as f (f.path)}{@render folderBlock(f, depth + 1)}{/each}
						{#each kids.notes.slice(0, capFor(node)) as note (note.path)}{@render noteRow(note, depth + 1)}{/each}
						{#if kids.notes.length > capFor(node)}
							<button
								class="text-[12px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 py-1.5 transition"
								style="padding-left: {(depth + 1) * 16 + 24}px"
								on:click={() => showAllIn(node.path)}
							>
								Afficher les {kids.notes.length - NOTE_CAP} autres…
							</button>
						{/if}
					{/if}
				</div>
			{/snippet}

			<!-- Barre de recherche (serveur, FTS5 — scalable). -->
			<div class="py-1.5 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100/60 dark:border-gray-850/40">
				<div class="px-3.5 flex items-center w-full py-0.5">
					<div class="self-center ml-1 mr-3"><Search className="size-3.5" /></div>
					<input
						class="w-full text-sm py-1.5 outline-hidden bg-transparent"
						bind:value={query}
						on:input={scheduleSearch}
						placeholder="Rechercher dans vos notes"
					/>
					{#if searching}
						<Spinner className="size-3.5" />
					{:else if query}
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
							on:click={() => {
								query = '';
								runSearch('');
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					{/if}
				</div>
			</div>

			<!-- Résultats de recherche (serveur) OU arbre du coffre. -->
			{#if query.trim()}
				{#if searchResults.length > 0}
					<div class="mt-2.5 flex flex-col gap-1.5">
						{#each searchResults as r (r.chemin)}
							<button
								class="group w-full text-left px-3.5 py-2.5 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700 transition"
								on:click={() => openNoteByPath(r.chemin, r.titre)}
							>
								<div class="text-sm font-medium text-gray-900 dark:text-white truncate">{r.titre}</div>
								{#if r.extrait}
									<div class="mt-0.5 text-[12px] text-gray-500 dark:text-gray-400 line-clamp-2">{r.extrait}</div>
								{/if}
							</button>
						{/each}
					</div>
				{:else if !searching}
					<div class="py-16 text-center text-sm text-gray-400 dark:text-gray-600">
						Aucune note pour « {query} »
					</div>
				{/if}
			{:else if tree.length > 0}
				<div class="mt-2.5 px-1">
					{#each tree as node (node.path)}
						{#if node.type === 'folder'}
							{@render folderBlock(node, 0)}
						{:else}
							{@render noteRow(node, 0)}
						{/if}
					{/each}
				</div>
			{:else}
				<!-- État vide accueillant, incarné par Adam -->
				<div class="w-full flex flex-col items-center justify-center">
					<div class="py-16 text-center">
						<img
							src="/assets/agents/adam.webp"
							alt="Adam"
							on:error={(e) => ((e.currentTarget as HTMLImageElement).src = '/favicon.png')}
							class="mx-auto h-14 w-14 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15 bg-sky-100 dark:bg-sky-900/30"
						/>
						<div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
							Je n'ai encore rien rangé pour vous.
						</div>
						<div class="mt-1 text-xs text-gray-400 dark:text-gray-600">
							Créez une première note — ou laissez-moi remplir votre coffre au fil de vos échanges.
						</div>
						<button
							class="mt-3 px-3 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition font-medium text-xs disabled:opacity-50"
							on:click={initVault}
							disabled={initializing}
						>
							{initializing ? 'Préparation…' : 'Préparer mon coffre'}
						</button>
					</div>
				</div>
			{/if}
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

						<!-- Titre de la note — éditable (renommage à la validation / perte de focus). -->
						<input
							bind:this={titleInput}
							class="w-full text-2xl font-medium bg-transparent outline-hidden"
							type="text"
							bind:value={titleDraft}
							placeholder="Sans titre"
							on:blur={commitRename}
							on:keydown={(e) => {
								if (e.key === 'Enter') {
									e.preventDefault();
									(e.currentTarget as HTMLInputElement).blur();
								}
							}}
						/>
					</div>

					<div class="shrink-0 flex items-center gap-1.5 pr-1">
						<!-- Indicateur de sauvegarde -->
						<div class="text-xs text-gray-500 dark:text-gray-500">
							{#if saveState === 'saving'}
								Enregistrement…
							{:else if saveState === 'saved'}
								Enregistré
							{/if}
						</div>
						<!-- Supprimer la note (corbeille récupérable) -->
						<Tooltip content="Supprimer">
							<button
								class="cursor-pointer flex rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition p-1.5"
								on:click={() => selectedNode && deleteNote(selectedNode, true)}
							>
								<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" stroke-linecap="round" stroke-linejoin="round" /></svg>
							</button>
						</Tooltip>
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
