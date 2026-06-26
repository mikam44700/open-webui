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

	// Onglet Mémoire / Second Cerveau. Affiche le coffre (arborescence), permet de lire et de
	// corriger une note. Zéro jargon technique (pas de « markdown », « sync », « coffre »).
	// Cf. specs/005-memoire.

	let loading = true;
	let tree = [];
	let flat = [];
	let status = null;

	let selected = null; // { path, name }
	let content = '';
	let dirty = false;
	let saving = false;
	let loadingNote = false;

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
		if (dirty && !confirm($i18n.t('Vous avez des modifications non enregistrées. Continuer ?'))) {
			return;
		}
		loadingNote = true;
		try {
			const note = await getMemoryNote(localStorage.token, node.path);
			selected = node;
			content = note.content;
			dirty = false;
		} catch (e) {
			toast.error(typeof e === 'string' ? e : ($i18n.t('Impossible d’ouvrir cette note') ?? ''));
		}
		loadingNote = false;
	};

	const save = async () => {
		if (!selected) return;
		saving = true;
		try {
			await saveMemoryNote(localStorage.token, selected.path, content);
			dirty = false;
			toast.success($i18n.t('Correction enregistrée'));
			await load();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : ($i18n.t('Échec de l’enregistrement') ?? ''));
		}
		saving = false;
	};

	onMount(load);
</script>

<div class="w-full max-w-6xl mx-auto px-3 pt-3">
	<!-- Statut honnête (jamais d'état non vérifié) -->
	{#if status}
		<div class="mb-3 flex items-center gap-2 text-xs text-gray-500">
			<span
				class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
					<path
						fill-rule="evenodd"
						d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
						clip-rule="evenodd"
					/>
				</svg>
				{$i18n.t('À jour')}
			</span>
			<span>{status.note_count} {$i18n.t('notes')}</span>
		</div>
	{/if}

	{#if loading}
		<div class="text-sm text-gray-500 py-10 text-center">{$i18n.t('Chargement…')}</div>
	{:else if flat.length === 0}
		<!-- État vide -->
		<div class="py-16 text-center">
			<div class="text-sm font-medium text-gray-700 dark:text-gray-200">
				{$i18n.t('Votre mémoire est encore vide')}
			</div>
			<div class="mt-1 text-xs text-gray-500 max-w-md mx-auto">
				{$i18n.t(
					'Votre assistant la remplira au fil de vos échanges : vos façons de faire, vos décisions, vos clients. Vous pourrez tout relire et corriger ici.'
				)}
			</div>
		</div>
	{:else}
		<div class="flex gap-4 min-h-[60vh]">
			<!-- Arborescence -->
			<div class="w-64 flex-none border-r border-gray-100 dark:border-gray-850 pr-2">
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

			<!-- Lecture / correction -->
			<div class="flex-1 min-w-0">
				{#if loadingNote}
					<div class="text-sm text-gray-500 py-10 text-center">{$i18n.t('Chargement…')}</div>
				{:else if selected}
					<div class="flex items-center justify-between mb-2">
						<div class="text-sm font-medium">{selected.name}</div>
						<button
							type="button"
							class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black disabled:opacity-40 transition"
							disabled={!dirty || saving}
							on:click={save}
						>
							{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer la correction')}
						</button>
					</div>
					<textarea
						class="w-full h-[55vh] resize-none rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent p-3 text-sm leading-relaxed outline-none focus:border-gray-400 dark:focus:border-gray-600"
						bind:value={content}
						on:input={() => (dirty = true)}
						placeholder={$i18n.t('Cette note est vide.')}
					></textarea>
				{:else}
					<div class="text-sm text-gray-500 py-16 text-center">
						{$i18n.t('Choisissez une note à gauche pour la lire ou la corriger.')}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
