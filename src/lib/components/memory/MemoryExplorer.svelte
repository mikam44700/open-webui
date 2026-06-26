<script>
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import {
		getMemoryTree,
		getMemoryStatus,
		getMemoryNote,
		saveMemoryNote
	} from '$lib/apis/memory';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';

	// Onglet Mémoire / Second Cerveau. Surface UNIQUE de la connaissance écrite de l'entreprise
	// (fusion de l'ancienne page Notes). Éditeur riche (TipTap via RichTextInput) branché sur le
	// coffre Obsidian (markdown), au lieu de la base OpenWebUI. Lecture + correction. Zéro jargon.
	// Cf. specs/005-memoire.

	let loading = true;
	let tree = [];
	let flat = [];
	let status = null;

	let selected = null; // { path, name }
	let currentMd = '';
	let loadingNote = false;
	let saveState = 'idle'; // idle | saving | saved
	let saveTimeout;

	const flatten = (nodes, depth = 0, acc = []) => {
		for (const n of nodes) {
			acc.push({ ...n, depth });
			if (n.type === 'folder' && n.children?.length) flatten(n.children, depth + 1, acc);
		}
		return acc;
	};

	const load = async () => {
		loading = true;
		try {
			const token = localStorage.token;
			const [t, s] = await Promise.all([getMemoryTree(token), getMemoryStatus(token)]);
			tree = t?.tree ?? [];
			flat = flatten(tree);
			status = s;
		} catch (e) {
			toast.error(typeof e === 'string' ? e : ($i18n.t('Impossible de charger la mémoire') ?? ''));
		}
		loading = false;
	};

	const openNote = async (node) => {
		if (node.type !== 'note') return;
		loadingNote = true;
		saveState = 'idle';
		try {
			const note = await getMemoryNote(localStorage.token, node.path);
			selected = node;
			currentMd = note.content;
		} catch (e) {
			toast.error(typeof e === 'string' ? e : ($i18n.t('Impossible d’ouvrir cette note') ?? ''));
		}
		loadingNote = false;
	};

	// Sauvegarde automatique débouncée vers le coffre (markdown).
	const scheduleSave = (md) => {
		if (!selected) return;
		currentMd = md;
		saveState = 'saving';
		clearTimeout(saveTimeout);
		saveTimeout = setTimeout(async () => {
			try {
				await saveMemoryNote(localStorage.token, selected.path, currentMd);
				saveState = 'saved';
				if (status) status = { ...status }; // refresh léger
			} catch (e) {
				saveState = 'idle';
				toast.error(typeof e === 'string' ? e : ($i18n.t('Échec de l’enregistrement') ?? ''));
			}
		}, 600);
	};

	const newNote = async () => {
		const title = (prompt($i18n.t('Nom de la nouvelle note ?')) ?? '').trim();
		if (!title) return;
		const path = `${title}.md`;
		try {
			await saveMemoryNote(localStorage.token, path, `# ${title}\n\n`);
			await load();
			await openNote({ path, name: title, type: 'note' });
		} catch (e) {
			toast.error(typeof e === 'string' ? e : ($i18n.t('Impossible de créer la note') ?? ''));
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-6xl mx-auto px-3 pt-3">
	<!-- Statut honnête + action -->
	<div class="mb-3 flex items-center justify-between gap-2">
		<div class="flex items-center gap-2 text-xs text-gray-500">
			{#if status?.ok}
				<span
					class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300"
				>
					<span class="relative flex size-2">
						<span
							class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60"
						></span>
						<span class="relative inline-flex size-2 rounded-full bg-green-500"></span>
					</span>
					{$i18n.t('Mémoire active')}
				</span>
				<span>·</span>
				<span>{$i18n.t('Partagée avec votre assistant')}</span>
				<span>·</span>
				<span>{status.note_count} {$i18n.t('notes')}</span>
				<span class="text-gray-400"
					>· {status.local_copy
						? $i18n.t('copie sur votre ordinateur')
						: $i18n.t('copie locale non reliée')}</span
				>
			{:else if status}
				<span class="text-amber-600">{$i18n.t('Mémoire indisponible')}</span>
			{/if}
		</div>
		<button
			type="button"
			class="flex-none text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
			on:click={newNote}
		>
			+ {$i18n.t('Nouvelle note')}
		</button>
	</div>

	{#if loading}
		<div class="text-sm text-gray-500 py-10 text-center">{$i18n.t('Chargement…')}</div>
	{:else}
		<div class="flex gap-4 min-h-[65vh]">
			<!-- Arborescence -->
			<div class="w-64 flex-none border-r border-gray-100 dark:border-gray-850 pr-2 overflow-y-auto">
				{#if flat.length === 0}
					<div class="px-2 py-4 text-xs text-gray-500">
						{$i18n.t('Votre mémoire est encore vide. Créez une note ou laissez votre assistant la remplir.')}
					</div>
				{/if}
				{#each flat as node}
					{#if node.type === 'folder'}
						<div
							class="px-2 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide"
							style="padding-left: {node.depth * 12 + 8}px"
						>
							{node.name}
						</div>
					{:else}
						<button
							type="button"
							class="w-full text-left px-2 py-1 rounded-lg text-sm transition {selected?.path ===
							node.path
								? 'bg-gray-100 dark:bg-gray-850 font-medium'
								: 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900'}"
							style="padding-left: {node.depth * 12 + 8}px"
							on:click={() => openNote(node)}
						>
							{node.name}
						</button>
					{/if}
				{/each}
			</div>

			<!-- Lecture / correction (éditeur riche) -->
			<div class="flex-1 min-w-0">
				{#if loadingNote}
					<div class="text-sm text-gray-500 py-10 text-center">{$i18n.t('Chargement…')}</div>
				{:else if selected}
					<div class="flex items-center justify-between mb-2">
						<div class="text-sm font-medium">{selected.name}</div>
						<div class="text-xs text-gray-400">
							{#if saveState === 'saving'}
								{$i18n.t('Enregistrement…')}
							{:else if saveState === 'saved'}
								{$i18n.t('Enregistré')}
							{/if}
						</div>
					</div>
					{#key selected.path}
						<div class="h-[58vh] overflow-y-auto rounded-xl border border-gray-200 dark:border-gray-800 p-3">
							<RichTextInput
								id={`memory-${selected.path}`}
								value={currentMd}
								className="input-prose-sm h-full"
								richText={true}
								link={true}
								image={true}
								placeholder={$i18n.t('Cette note est vide.')}
								onChange={({ md }) => scheduleSave(md)}
							/>
						</div>
					{/key}
				{:else}
					<div class="text-sm text-gray-500 py-16 text-center">
						{$i18n.t('Choisissez une note à gauche pour la lire ou la corriger.')}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
