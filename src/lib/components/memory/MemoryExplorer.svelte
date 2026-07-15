<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import { config, models, settings } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { chatCompletion } from '$lib/apis/openai';

	import {
		getMemoryTree,
		getMemoryStatus,
		getMemoryNote,
		saveMemoryNote,
		initMemoryVault,
		createFolder,
		moveNote,
		moveFolder,
		renameFolder,
		deleteFolder,
		restoreFolder,
		searchMemory,
		deleteMemoryNote,
		restoreMemoryNote,
		renameMemoryNote
	} from '$lib/apis/memory';
	import type { MemoryNode, MemoryStatus, SearchResult } from '$lib/apis/memory';
	import {
		buildFolderList,
		buildSuggestPrompt,
		parseSuggestions,
		type FilingSuggestion
	} from '$lib/memory/suggestFiling';
	import { FRIENDLY_FOLDER, FOLDER_SUBTITLE } from '$lib/memory/vaultFolders';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import MemoryTreeNode from '$lib/components/memory/MemoryTreeNode.svelte';
	import MemoryToolbar from '$lib/components/memory/MemoryToolbar.svelte';
	import MemorySyncPanel from '$lib/components/memory/MemorySyncPanel.svelte';
	import MemoryNewFolderRow from '$lib/components/memory/MemoryNewFolderRow.svelte';
	import MemoryTrash from '$lib/components/memory/MemoryTrash.svelte';
	import MemorySearch from '$lib/components/memory/MemorySearch.svelte';
	import MemoryMovePicker from '$lib/components/memory/MemoryMovePicker.svelte';
	import MemoryNoteEditor from '$lib/components/memory/MemoryNoteEditor.svelte';


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

	// Dossier « courant » : où atterrissent les créations (note/dossier). Suit le dernier dossier
	// cliqué ou la note ouverte ; null = pas de choix explicite → défaut (Réception pour les notes).
	let activeFolder: string | null = null;
	const parentOf = (p: string): string => (p.includes('/') ? p.slice(0, p.lastIndexOf('/')) : '');
	// Cible d'une nouvelle note : dossier courant, sinon la Réception si elle existe, sinon racine.
	$: noteTarget =
		activeFolder ?? (tree.some((n) => n.path === '00-Réception') ? '00-Réception' : '');
	// Cible d'un nouveau dossier : le dossier courant SAUF la Réception (boîte d'entrée d'Adam, jamais
	// une zone de structure) → dans ce cas on retombe sur « Mes responsabilités » (02-Mes responsabilités), sinon racine.
	const inReception = (p: string | null): boolean =>
		!!p && (p === RECEPTION || p.startsWith(`${RECEPTION}/`));
	$: folderTarget =
		activeFolder && !inReception(activeFolder)
			? activeFolder
			: tree.some((n) => n.path === '02-Mes responsabilités')
				? '02-Mes responsabilités'
				: '';

	// Création de dossier : saisie inline (pas de prompt natif, cohérent avec la refonte).
	// La saisie elle-même (focus, champ, validation clavier) vit dans MemoryNewFolderRow.
	let creatingFolder = false;

	// Éditeur (la vue elle-même vit dans MemoryNoteEditor ; le débounce de sauvegarde reste ici
	// pour préserver l'ordonnancement exact avec goBack()/onDestroy()).
	let titleDraft = ''; // titre éditable (renommage)
	let noteEditorRef: MemoryNoteEditor | null = null;
	let selectedNode: MemoryNode | null = null;
	let currentMd = '';
	let loadingNote = false;
	let saveState: 'idle' | 'saving' | 'saved' = 'idle';
	let noteModified: number | null = null; // date de dernière modif de la note ouverte (epoch)
	let saveTimeout: ReturnType<typeof setTimeout>;
	// Sauvegarde en attente (debounce) : permet de la flusher avant de quitter la note.
	let pendingSave: { path: string; md: string } | null = null;

	// Modèle actif (utilisé par le rangement assisté d'Adam, feature 021).
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
	// Renommer ICI ne touche que l'affichage : les vrais dossiers du coffre ne bougent pas.
	// Source unique des 9 dossiers (slug + libellé + sous-titre) : $lib/memory/vaultFolders.ts.
	const friendlyFolder = (name: string): string => FRIENDLY_FOLDER[name] ?? name;

	// Sous-titre « langage dirigeant » sous chaque dossier racine : explique le classeur d'un coup d'œil.
	// Volontairement limité aux 9 dossiers du squelette PARA → les sous-dossiers du client restent nus.
	const folderSubtitle = (name: string): string => FOLDER_SUBTITLE[name] ?? '';

	// Date lisible « langage dirigeant » à partir d'un epoch (secondes). Vide si absente.
	const formatModified = (epoch: number | null): string => {
		if (!epoch) return '';
		return new Date(epoch * 1000).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	};

	// ─── Corbeille : notes/dossiers supprimés dans LunarIA, récupérables ────────
	// Le panneau (liste, restauration, purge confirmée) vit entièrement dans MemoryTrash, qui
	// se recharge à chaque montage — exactement le comportement précédent (recharge à chaque
	// ouverture). Ici, seul l'état d'affichage (ouvert/fermé) reste, pour piloter la bascule
	// avec la recherche/l'arbre dans le template.
	let showTrash = false;

	// Dossiers structurels du squelette PARA : protégés (ni renommés, ni supprimés). Le dirigeant
	// range DEDANS (ses casquettes), mais ne casse pas le squelette clé en main. (Miroir du bridge.)
	const STRUCTURAL_FOLDERS = new Set(Object.keys(FRIENDLY_FOLDER));
	const isStructural = (path: string): boolean => STRUCTURAL_FOLDERS.has(path);

	// ─── Rangement assisté par Adam (feature 021) ──────────────────────────────
	// Suggestions de destination pour les notes de Réception. Calculées à la demande, éphémères.
	const RECEPTION = '00-Réception';
	let suggestionsByPath: Record<string, FilingSuggestion[]> = {};
	let dismissedPaths = new Set<string>();
	let suggestComputed = false; // évite de rappeler le modèle à chaque rendu
	const isGuideNote = (name: string): boolean => name.startsWith('À lire');

	// Déplacement d'une note : liste à plat des dossiers (cible du sélecteur « Déplacer vers »).
	type FolderOpt = { path: string; label: string; depth: number };
	const collectFolders = (nodes: MemoryNode[], d = 0): FolderOpt[] => {
		const acc: FolderOpt[] = [];
		for (const n of nodes) {
			if (n.type === 'folder') {
				acc.push({ path: n.path, label: friendlyFolder(n.name), depth: d });
				acc.push(...collectFolders(n.children ?? [], d + 1));
			}
		}
		return acc;
	};
	$: folderOptions = collectFolders(tree);
	// Élément en cours de déplacement (note OU dossier) → ouvre le sélecteur. null = fermé.
	let movingItem: MemoryNode | null = null;
	// Destinations proposées : pour un DOSSIER, on exclut la Réception, le dossier lui-même et ses
	// descendants (pas de cycle). Pour une NOTE, tout est permis (y compris la Réception).
	$: pickerOptions =
		movingItem?.type === 'folder'
			? folderOptions.filter(
					(o) =>
						!inReception(o.path) &&
						o.path !== movingItem?.path &&
						!o.path.startsWith(`${movingItem?.path}/`)
				)
			: folderOptions;

	// Dépliage des dossiers : niveau 0 ouvert par défaut, sous-dossiers fermés (scalable). Persisté.
	// La logique de rendu récursif vit dans MemoryTreeNode ; ici on ne gère que l'état.
	const toggleOpen = (path: string, depth: number): void => {
		activeFolder = path; // cliquer un dossier en fait la cible des créations
		const currentlyOpen = openState[path] ?? depth === 0;
		openState = { ...openState, [path]: !currentlyOpen };
		try {
			localStorage.setItem('lunaria:memory-open', JSON.stringify(openState));
		} catch {
			/* localStorage indisponible : dépliage non persisté, sans conséquence */
		}
	};
	const showAllIn = (path: string): void => {
		expandedFull = { ...expandedFull, [path]: true };
	};

	// Tout déplier / tout replier (comme Obsidian) : bascule l'état d'ouverture de TOUS les dossiers.
	let allExpanded = false;
	const collectFolderPaths = (nodes: MemoryNode[]): string[] => {
		const acc: string[] = [];
		for (const n of nodes) {
			if (n.type === 'folder') {
				acc.push(n.path);
				acc.push(...collectFolderPaths(n.children ?? []));
			}
		}
		return acc;
	};
	const toggleExpandAll = (): void => {
		allExpanded = !allExpanded;
		const next: Record<string, boolean> = { ...openState };
		for (const p of collectFolderPaths(tree)) next[p] = allExpanded;
		openState = next;
		try {
			localStorage.setItem('lunaria:memory-open', JSON.stringify(openState));
		} catch {
			/* localStorage indisponible : sans conséquence */
		}
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
		baselineMd = null; // le 1er onChange (écho d'init de l'éditeur) ne doit pas déclencher de sauvegarde
		try {
			const res = await getMemoryNote(localStorage.token, node.path);
			selectedNode = node;
			activeFolder = parentOf(node.path); // les créations suivent le dossier de la note ouverte
			titleDraft = node.name;
			currentMd = res.content ?? '';
			noteModified = res.modified ?? null;
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

	// Chemin libre pour une nouvelle note dans un dossier donné (suffixe si collision DANS ce dossier).
	const uniqueNotePath = (folder: string, base: string): { path: string; name: string } => {
		const prefix = folder ? `${folder}/` : '';
		const existing = new Set(allNotes.map((x) => x.path.toLowerCase()));
		let name = base;
		let i = 2;
		while (existing.has(`${prefix}${name}.md`.toLowerCase())) name = `${base} ${i++}`;
		return { path: `${prefix}${name}.md`, name };
	};

	const newNote = async () => {
		const folder = noteTarget; // dossier courant, sinon Réception, sinon racine
		const { path, name } = uniqueNotePath(folder, 'Nouvelle note');
		try {
			await saveMemoryNote(localStorage.token, path, '');
			await load();
			if (folder) openState = { ...openState, [folder]: true }; // rend la note visible
			await openNote({ path, name, type: 'note', children: [] });
			// Titre prêt à être renommé tout de suite (le champ vit dans MemoryNoteEditor).
			await tick();
			noteEditorRef?.focusTitle();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de créer la note');
		}
	};

	// ─── Nouveau dossier (saisie inline, sans prompt natif) ────────────────────
	// Le champ de saisie (focus auto, clavier) vit dans MemoryNewFolderRow.

	const startNewFolder = (): void => {
		creatingFolder = true;
	};

	const cancelNewFolder = (): void => {
		creatingFolder = false;
	};

	const confirmNewFolder = async (name: string): Promise<void> => {
		const parent = folderTarget; // dossier courant, sinon « 02-Mes responsabilités » par défaut
		try {
			const node = await createFolder(localStorage.token, parent, name);
			await load();
			if (parent) openState = { ...openState, [parent]: true };
			openState = { ...openState, [node.path]: true };
			activeFolder = node.path; // le nouveau dossier devient la cible
			creatingFolder = false;
			toast.success(`Dossier « ${node.name} » créé`);
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de créer le dossier');
		}
	};

	// ─── Déplacer une note (glisser-déposer OU sélecteur « Déplacer vers ») ─────

	const doMove = async (notePath: string, destFolder: string) => {
		try {
			await moveNote(localStorage.token, notePath, destFolder);
			await load();
			if (destFolder) openState = { ...openState, [destFolder]: true };
			toast.success('Note déplacée');
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de déplacer la note');
		}
	};
	const doMoveFolder = async (folderPath: string, destParent: string) => {
		try {
			await moveFolder(localStorage.token, folderPath, destParent);
			await load();
			if (destParent) openState = { ...openState, [destParent]: true };
			toast.success('Dossier déplacé');
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de déplacer le dossier');
		}
	};
	const requestMove = (node: MemoryNode) => {
		movingItem = node;
	};
	const chooseMoveTarget = async (dest: string) => {
		const item = movingItem;
		movingItem = null;
		if (!item) return;
		if (item.type === 'folder') await doMoveFolder(item.path, dest);
		else await doMove(item.path, dest);
	};

	// ─── Renommer / supprimer un dossier (les PARA structurels sont protégés) ───

	const renameFolderHandler = async (node: MemoryNode, newName: string) => {
		try {
			await renameFolder(localStorage.token, node.path, newName);
			await load();
			toast.success('Dossier renommé');
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de renommer le dossier');
		}
	};
	const deleteFolderHandler = async (node: MemoryNode) => {
		try {
			const res = await deleteFolder(localStorage.token, node.path);
			await load();
			toast.success(`Dossier « ${node.name} » supprimé`, {
				action: {
					label: 'Annuler',
					onClick: async () => {
						try {
							await restoreFolder(localStorage.token, res.trash_ref, res.path);
							await load();
							toast.success('Dossier restauré');
						} catch (e) {
							toast.error(typeof e === 'string' ? e : 'Impossible de restaurer le dossier');
						}
					}
				}
			});
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de supprimer le dossier');
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

	// ─── Rangement assisté : génération des suggestions (à la demande, 1 appel groupé) ──

	const generateSuggestions = async () => {
		if (suggestComputed || !selectedModelId) return;
		const reception = tree.find((n) => n.path === RECEPTION);
		const notes = (reception?.children ?? [])
			.filter((c) => c.type === 'note' && !isGuideNote(c.name))
			.slice(0, 15); // borne le coût : au plus 15 notes par génération
		if (notes.length === 0) return;
		suggestComputed = true;
		const folders = buildFolderList(tree, friendlyFolder);
		if (folders.length === 0) return;
		const model = $models
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			.filter((m) => !((m?.info?.meta as any)?.hidden ?? false))
			.find((m) => m.id === selectedModelId);
		if (!model) return;
		try {
			const withContent = await Promise.all(
				notes.map(async (n) => {
					try {
						const r = await getMemoryNote(localStorage.token, n.path);
						return { path: n.path, content: r.content ?? '' };
					} catch {
						return { path: n.path, content: '' };
					}
				})
			);
			const prompt = buildSuggestPrompt(withContent, folders);
			const [res] = await chatCompletion(
				localStorage.token,
				{ model: model.id, stream: false, messages: [{ role: 'user', content: prompt }] },
				`${WEBUI_BASE_URL}/api`
			);
			if (!res || !res.ok) return;
			const data = await res.json();
			const content = data?.choices?.[0]?.message?.content ?? '';
			const map: Record<string, FilingSuggestion[]> = {};
			for (const ns of parseSuggestions(content, folders)) {
				if (ns.suggestions.length) map[ns.notePath] = ns.suggestions;
			}
			suggestionsByPath = map;
		} catch {
			// Silencieux : l'absence de suggestion ne bloque jamais l'onglet (FR-013).
		}
	};

	// Applique une suggestion : range la note (réutilise moveNote, réversible en la renvoyant en Réception).
	const fileHere = async (notePath: string, dest: string) => {
		try {
			const res = await moveNote(localStorage.token, notePath, dest);
			const { [notePath]: _moved, ...rest } = suggestionsByPath;
			suggestionsByPath = rest;
			await load();
			if (dest) openState = { ...openState, [dest]: true };
			toast.success('Note rangée', {
				action: {
					label: 'Annuler',
					onClick: async () => {
						try {
							await moveNote(localStorage.token, res.path, RECEPTION);
							await load();
							toast.success('Rangement annulé');
						} catch (e) {
							toast.error(typeof e === 'string' ? e : "Impossible d'annuler le rangement");
						}
					}
				}
			});
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de ranger la note');
		}
	};

	// Écarte la suggestion d'une note (le dirigeant ne veut pas la ranger maintenant).
	const dismissSuggestion = (notePath: string) => {
		dismissedPaths = new Set(dismissedPaths).add(notePath);
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

	// La connexion du coffre à Obsidian (sync Syncthing pré-appairée) vit entièrement dans
	// MemorySyncPanel (bandeau autonome, ne dépend d'aucun autre état de ce composant).

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

	// Référence du contenu chargé : le 1er onChange après ouverture (écho d'init de l'éditeur) sert
	// de base et n'est PAS sauvegardé — on ne sauvegarde qu'un VRAI changement (édition humaine).
	let baselineMd: string | null = null;

	const scheduleSave = (md: string) => {
		if (!selectedNode) return;
		if (baselineMd === null) {
			baselineMd = md; // écho d'initialisation : on mémorise, on ne sauvegarde pas
			return;
		}
		if (md === baselineMd) return; // aucun changement réel
		baselineMd = md;
		currentMd = md;
		saveState = 'saving';
		pendingSave = { path: selectedNode.path, md };
		clearTimeout(saveTimeout);
		saveTimeout = setTimeout(flushSave, 600);
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

		// Rangement assisté : Adam calcule ses suggestions à la demande (non bloquant).
		generateSuggestions();
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
			<MemoryToolbar
				{status}
				{noteTarget}
				{friendlyFolder}
				{allExpanded}
				onNewNote={newNote}
				onNewFolder={startNewFolder}
				onToggleExpandAll={toggleExpandAll}
				onOpenTrash={() => (showTrash = true)}
			/>

			<!-- Création de dossier : saisie inline (pas de prompt natif). -->
			{#if creatingFolder}
				<MemoryNewFolderRow
					{folderTarget}
					{friendlyFolder}
					onConfirm={confirmNewFolder}
					onCancel={cancelNewFolder}
				/>
			{/if}

			<!-- Bandeau de synchronisation avec Obsidian — 3 états honnêtes. -->
			<MemorySyncPanel {status} />

			{#if showTrash}
				<!-- ═══ Corbeille : éléments supprimés, récupérables ═══ -->
				<MemoryTrash
					{friendlyFolder}
					{formatModified}
					onReload={load}
					onClose={() => (showTrash = false)}
				/>
			{:else}
				<!-- Barre de recherche (serveur, FTS5) + résultats OU arbre du coffre. -->
				<MemorySearch
					bind:query
					{searching}
					{searchResults}
					onInput={scheduleSearch}
					onClear={() => {
						query = '';
						runSearch('');
					}}
					onOpenNote={openNoteByPath}
				/>

				{#if !query.trim()}
					{#if tree.length > 0}
						<div class="mt-2.5 px-1 pb-10">
							{#each tree as node (node.path)}
								<MemoryTreeNode
									{node}
									depth={0}
									{openState}
									{expandedFull}
									noteCap={NOTE_CAP}
									{friendlyFolder}
									{folderSubtitle}
									{isStructural}
									suggestions={suggestionsByPath}
									dismissed={dismissedPaths}
									onOpen={openNote}
									onDelete={(n) => deleteNote(n)}
									onToggle={toggleOpen}
									onShowAll={showAllIn}
									onMoveNote={doMove}
									onMoveFolder={doMoveFolder}
									onRequestMove={requestMove}
									onRenameFolder={renameFolderHandler}
									onDeleteFolder={deleteFolderHandler}
									onFileHere={fileHere}
									onDismiss={dismissSuggestion}
								/>
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
				{/if}

				<div class="mb-8"></div>
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
	<MemoryNoteEditor
		bind:this={noteEditorRef}
		{loadingNote}
		{selectedNode}
		bind:titleDraft
		{saveState}
		{noteModified}
		{currentMd}
		{formatModified}
		onBack={goBack}
		onCommitRename={commitRename}
		onDelete={() => {
			if (selectedNode) deleteNote(selectedNode, true);
		}}
		onChange={(content) => scheduleSave(content.md ?? '')}
	/>
{/if}

<!-- ═══════════════════════════════════════════════════════════════════════════
     Sélecteur « Déplacer vers » (alternative robuste au glisser-déposer)
     ═══════════════════════════════════════════════════════════════════════════ -->
{#if movingItem}
	<MemoryMovePicker
		item={movingItem}
		options={pickerOptions}
		onChoose={chooseMoveTarget}
		onCancel={() => (movingItem = null)}
	/>
{/if}
