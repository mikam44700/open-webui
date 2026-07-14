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
		getSyncPack,
		downloadSyncPack,
		searchMemory,
		deleteMemoryNote,
		restoreMemoryNote,
		renameMemoryNote,
		getTrash
	} from '$lib/apis/memory';
	import type { MemoryNode, MemoryStatus, SearchResult, TrashItem } from '$lib/apis/memory';
	import {
		buildFolderList,
		buildSuggestPrompt,
		parseSuggestions,
		type FilingSuggestion
	} from '$lib/memory/suggestFiling';

	import type { Editor } from '@tiptap/core';

	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import MemoryTreeNode from '$lib/components/memory/MemoryTreeNode.svelte';

	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';


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
	let creatingFolder = false;
	let newFolderName = '';
	let folderInput: HTMLInputElement | null = null;

	// Éditeur
	let titleDraft = ''; // titre éditable (renommage)
	let titleInput: HTMLInputElement | null = null;
	let selectedNode: MemoryNode | null = null;
	let currentMd = '';
	let loadingNote = false;
	let saveState: 'idle' | 'saving' | 'saved' = 'idle';
	let noteModified: number | null = null; // date de dernière modif de la note ouverte (epoch)
	let saveTimeout: ReturnType<typeof setTimeout>;
	// Sauvegarde en attente (debounce) : permet de la flusher avant de quitter la note.
	let pendingSave: { path: string; md: string } | null = null;

	let inputElement: RichTextInput | null = null;
	let editor: Editor | null = null;

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
	const FRIENDLY_FOLDER: Record<string, string> = {
		'00-Réception': 'Réception',
		'01-En cours': 'En cours',
		'02-Mes responsabilités': 'Mes responsabilités',
		'03-Idées & ressources': 'Idées & ressources',
		'04-Archivées': 'Archivées',
		'05-Journal': 'Journal',
		'06-Contacts': 'Contacts',
		'07-Mes réflexions': 'Mes réflexions',
		'08-Modèles de notes': 'Modèles de notes'
	};
	const friendlyFolder = (name: string): string => FRIENDLY_FOLDER[name] ?? name;

	// Sous-titre « langage dirigeant » sous chaque dossier racine : explique le classeur d'un coup d'œil.
	// Volontairement limité aux 9 dossiers du squelette PARA → les sous-dossiers du client restent nus.
	const FOLDER_SUBTITLE: Record<string, string> = {
		'00-Réception': "Tout arrive ici avant d'être rangé",
		'01-En cours': 'Ce sur quoi vous travaillez en ce moment',
		'02-Mes responsabilités': 'Ce dont vous vous occupez en continu (ventes, équipe, finances…)',
		'03-Idées & ressources': 'Documents et idées utiles à garder sous la main',
		'04-Archivées': 'Ce qui est terminé, conservé au cas où',
		'05-Journal': 'Vos notes datées : réunions, décisions, journées',
		'06-Contacts': 'Vos clients, prospects et partenaires',
		'07-Mes réflexions': 'Là où vous posez vos idées et vos notes',
		'08-Modèles de notes': 'Des exemples prêts à réutiliser (compte-rendu, fiche client…)'
	};
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
	let showTrash = false;
	let trashItems: TrashItem[] = [];
	let trashLoading = false;

	const openTrash = async () => {
		showTrash = true;
		trashLoading = true;
		try {
			trashItems = (await getTrash(localStorage.token)).items ?? [];
		} catch (e) {
			toast.error(typeof e === 'string' ? e : "Impossible d'ouvrir la corbeille");
		}
		trashLoading = false;
	};

	const restoreFromTrash = async (item: TrashItem) => {
		try {
			if (item.type === 'folder') await restoreFolder(localStorage.token, item.ref, item.path);
			else await restoreMemoryNote(localStorage.token, item.ref, item.path);
			trashItems = trashItems.filter((t) => t.ref !== item.ref);
			await load(); // recharge l'arbre pour faire réapparaître l'élément restauré
			toast.success(`« ${item.name} » restauré`);
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de restaurer cet élément');
		}
	};

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
		editor = null;
		inputElement = null;
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
			// Titre prêt à être renommé tout de suite.
			await tick();
			titleInput?.focus();
			titleInput?.select();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : 'Impossible de créer la note');
		}
	};

	// ─── Nouveau dossier (saisie inline, sans prompt natif) ────────────────────

	const startNewFolder = async () => {
		creatingFolder = true;
		newFolderName = '';
		await tick();
		folderInput?.focus();
	};

	const cancelNewFolder = () => {
		creatingFolder = false;
		newFolderName = '';
	};

	const confirmNewFolder = async () => {
		const name = newFolderName.trim();
		if (!name) {
			cancelNewFolder();
			return;
		}
		const parent = folderTarget; // dossier courant, sinon « Mon activité » par défaut
		try {
			const node = await createFolder(localStorage.token, parent, name);
			await load();
			if (parent) openState = { ...openState, [parent]: true };
			openState = { ...openState, [node.path]: true };
			activeFolder = node.path; // le nouveau dossier devient la cible
			creatingFolder = false;
			newFolderName = '';
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
				<div class="flex-none flex items-center gap-1.5">
					<Tooltip content={`Créer dans : ${friendlyFolder(noteTarget) || 'Réception'}`}>
						<button
							class="px-2.5 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
							on:click={newNote}
						>
							<Plus className="size-3" strokeWidth="2.5" />
							<div class="ml-1 text-xs">Nouvelle note</div>
						</button>
					</Tooltip>
					<Tooltip content="Nouveau dossier">
						<button
							class="p-2 rounded-xl ring-1 ring-inset ring-black/10 dark:ring-white/15 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition"
							on:click={startNewFolder}
							aria-label="Nouveau dossier"
						>
							<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
								<path
									d="M2.5 6A1.5 1.5 0 0 1 4 4.5h3l1.5 2H16A1.5 1.5 0 0 1 17.5 8v6.5A1.5 1.5 0 0 1 16 16H4a1.5 1.5 0 0 1-1.5-1.5V6Z"
									stroke-linejoin="round"
								/>
								<path d="M10 9.5v4M8 11.5h4" stroke-linecap="round" />
							</svg>
						</button>
					</Tooltip>
					<Tooltip content={allExpanded ? 'Tout replier' : 'Tout déplier'}>
						<button
							class="p-2 rounded-xl ring-1 ring-inset ring-black/10 dark:ring-white/15 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition"
							on:click={toggleExpandAll}
							aria-label={allExpanded ? 'Tout replier' : 'Tout déplier'}
						>
							<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
								{#if allExpanded}
									<!-- chevrons vers l'intérieur = tout replier -->
									<path d="M6 5l4 4 4-4M6 15l4-4 4 4" />
								{:else}
									<!-- chevrons vers l'extérieur = tout déplier -->
									<path d="M6 8l4-4 4 4M6 12l4 4 4-4" />
								{/if}
							</svg>
						</button>
					</Tooltip>
				</div>
			</div>

			<!-- Création de dossier : saisie inline (pas de prompt natif). -->
			{#if creatingFolder}
				<div
					class="mb-3 flex items-center gap-2 rounded-2xl bg-gray-50 dark:bg-white/5 ring-1 ring-inset ring-black/5 dark:ring-white/10 px-3 py-2"
				>
					<span class="shrink-0 text-amber-500/80">
						<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"
							><path
								d="M2 5.5A1.5 1.5 0 0 1 3.5 4h4l1.5 2h7A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H3.5A1.5 1.5 0 0 1 2 14.5v-9Z"
							/></svg
						>
					</span>
					<input
						bind:this={folderInput}
						bind:value={newFolderName}
						class="flex-1 min-w-0 text-sm bg-transparent outline-hidden"
						placeholder="Nom du dossier"
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								confirmNewFolder();
							} else if (e.key === 'Escape') {
								cancelNewFolder();
							}
						}}
					/>
					<span class="shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
						dans {folderTarget ? friendlyFolder(folderTarget.split('/').pop() ?? '') : 'la racine'}
					</span>
					<button
						class="shrink-0 px-2.5 py-1 rounded-lg bg-black text-white dark:bg-white dark:text-black text-xs font-medium transition disabled:opacity-40"
						on:click={confirmNewFolder}
						disabled={!newFolderName.trim()}
					>
						Créer
					</button>
					<button
						class="shrink-0 px-2 py-1 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-200/60 dark:hover:bg-white/10 text-xs transition"
						on:click={cancelNewFolder}
					>
						Annuler
					</button>
				</div>
			{/if}

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

			{#if showTrash}
				<!-- ═══ Corbeille : éléments supprimés, récupérables ═══ -->
				<div class="mt-2.5">
					<div class="flex items-center gap-2 px-1 mb-3">
						<button
							class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 transition"
							on:click={() => (showTrash = false)}
							aria-label="Retour au coffre"
						>
							<ChevronLeft className="size-4" />
						</button>
						<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">Corbeille</div>
						<div class="text-xs text-gray-400 dark:text-gray-600">· éléments supprimés, récupérables</div>
					</div>
					{#if trashLoading}
						<div class="py-16 flex justify-center"><Spinner className="size-4" /></div>
					{:else if trashItems.length === 0}
						<div class="py-16 text-center text-sm text-gray-400 dark:text-gray-600">
							La corbeille est vide.
						</div>
					{:else}
						<div class="flex flex-col gap-1.5">
							{#each trashItems as item (item.ref)}
								<div
									class="flex items-center gap-2.5 px-3 py-2.5 rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900"
								>
									<span class="shrink-0 text-base">{item.type === 'folder' ? '📁' : '📄'}</span>
									<div class="min-w-0 flex-1">
										<div class="text-sm text-gray-800 dark:text-gray-100 truncate">{item.name}</div>
										<div class="text-[11px] text-gray-400 dark:text-gray-600 truncate">
											Supprimé le {formatModified(item.deleted_at)}{#if item.path.includes('/')} · depuis {friendlyFolder(item.path.split('/')[0])}{/if}
										</div>
									</div>
									<button
										class="shrink-0 text-xs px-2.5 py-1.5 rounded-lg text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-900/20 transition font-medium"
										on:click={() => restoreFromTrash(item)}
									>
										Restaurer
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{:else}
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

			<!-- Accès à la corbeille (discret, en bas du coffre) -->
			<button
				class="mt-3 mb-8 mx-auto flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-600 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={openTrash}
			>
				<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" stroke-linecap="round" stroke-linejoin="round" /></svg>
				Corbeille
			</button>
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
						<!-- Indicateur de sauvegarde / date de dernière modif -->
						<div class="text-xs text-gray-500 dark:text-gray-500">
							{#if saveState === 'saving'}
								Enregistrement…
							{:else if saveState === 'saved'}
								Enregistré
							{:else if noteModified}
								Modifié le {formatModified(noteModified)}
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
					{#key selectedNode?.path}
						<RichTextInput
							bind:this={inputElement}
							bind:editor
							id={`memory-${selectedNode?.path ?? 'note'}`}
							className="input-prose-sm px-0.5 h-[calc(100%-2rem)]"
							value={currentMd}
							dragHandle={true}
							link={true}
							image={true}
							placeholder="Écrivez quelque chose…"
							onChange={(content) => {
								scheduleSave(content.md ?? '');
							}}
						/>
					{/key}
				</div>
			</div>
		{/if}
	</div>
{/if}

<!-- ═══════════════════════════════════════════════════════════════════════════
     Sélecteur « Déplacer vers » (alternative robuste au glisser-déposer)
     ═══════════════════════════════════════════════════════════════════════════ -->
{#if movingItem}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 backdrop-blur-[2px] p-4"
		on:click={() => (movingItem = null)}
	>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div
			class="w-full max-w-sm max-h-[70vh] flex flex-col rounded-2xl bg-white dark:bg-gray-900 ring-1 ring-black/10 dark:ring-white/10 shadow-2xl overflow-hidden"
			on:click|stopPropagation
		>
			<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800">
				<div class="text-sm font-semibold text-gray-900 dark:text-white">Déplacer vers…</div>
				<div class="mt-0.5 text-[12px] text-gray-500 dark:text-gray-400 truncate">
					« {movingItem.name} »
				</div>
			</div>
			<div class="flex-1 overflow-y-auto py-1.5">
				<button
					class="w-full text-left px-4 py-2 text-[13.5px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 transition flex items-center gap-2"
					on:click={() => chooseMoveTarget('')}
				>
					<span class="text-gray-400">🗂️</span> Racine du coffre
				</button>
				{#each pickerOptions as opt (opt.path)}
					<button
						class="w-full text-left py-2 text-[13.5px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 transition flex items-center gap-2"
						style="padding-left: {opt.depth * 14 + 16}px; padding-right: 16px"
						on:click={() => chooseMoveTarget(opt.path)}
					>
						<span class="shrink-0 text-amber-500/80">
							<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"
								><path
									d="M2 5.5A1.5 1.5 0 0 1 3.5 4h4l1.5 2h7A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H3.5A1.5 1.5 0 0 1 2 14.5v-9Z"
								/></svg
							>
						</span>
						<span class="truncate">{opt.label}</span>
					</button>
				{/each}
			</div>
			<div class="px-4 py-2.5 border-t border-gray-100 dark:border-gray-800 flex justify-end">
				<button
					class="px-3 py-1.5 rounded-lg text-[12.5px] text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 transition"
					on:click={() => (movingItem = null)}
				>
					Annuler
				</button>
			</div>
		</div>
	</div>
{/if}
