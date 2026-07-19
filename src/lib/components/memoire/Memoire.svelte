<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import {
		createDossier,
		getFiche,
		getMemoireTree,
		saveFiche,
		type MemoireEntry
	} from '$lib/apis/memoire';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import TreeItem from './TreeItem.svelte';

	const i18n = getContext('i18n');

	let tree: MemoireEntry[] = [];
	let loaded = false;

	let selectedPath: string | null = null;
	let selectedName = '';
	let content = '';
	let draft = '';
	let mode: 'lecture' | 'edition' = 'lecture';
	let saving = false;

	let creating: 'fiche' | 'dossier' | null = null;
	let newName = '';
	let newParent = '';

	const flattenFiches = (entries: MemoireEntry[]): MemoireEntry[] =>
		entries.flatMap((entry) =>
			entry.type === 'fiche' ? [entry] : flattenFiches(entry.children ?? [])
		);

	const flattenDossiers = (entries: MemoireEntry[]): MemoireEntry[] =>
		entries.flatMap((entry) =>
			entry.type === 'dossier' ? [entry, ...flattenDossiers(entry.children ?? [])] : []
		);

	$: fiches = flattenFiches(tree);
	$: dossiers = flattenDossiers(tree);

	const resolveFiche = (target: string): MemoireEntry | null =>
		fiches.find((f) => f.path === target || f.path === `${target}.md` || f.name === target) ?? null;

	// [[Cible]] et [[Cible|Alias]] deviennent des liens internes de la page Mémoire
	const renderWikilinks = (md: string): string =>
		md.replace(
			/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
			(_, target, alias) =>
				`[${alias ?? target}](/memoire?fiche=${encodeURIComponent(target.trim())})`
		);

	const loadTree = async () => {
		try {
			const res = await getMemoireTree(localStorage.token);
			tree = res.tree;
		} catch (e) {
			toast.error(`${e?.detail ?? e}`);
		}
	};

	const openFiche = async (entry: MemoireEntry) => {
		try {
			const res = await getFiche(localStorage.token, entry.path);
			selectedPath = res.path;
			selectedName = entry.name;
			content = res.content;
			mode = 'lecture';
		} catch (e) {
			toast.error(`${e?.detail ?? e}`);
		}
	};

	const openFromQuery = async () => {
		const target = $page.url.searchParams.get('fiche');
		if (!target) return;
		const entry = resolveFiche(target);
		if (entry) {
			await openFiche(entry);
		} else {
			toast.error($i18n.t('Fiche introuvable : {{name}}', { name: target }));
		}
	};

	$: if (loaded && $page.url.searchParams.get('fiche')) {
		openFromQuery();
	}

	const startEdit = () => {
		draft = content;
		mode = 'edition';
	};

	const save = async () => {
		if (!selectedPath || saving) return;
		saving = true;
		try {
			const res = await saveFiche(localStorage.token, selectedPath, draft);
			content = draft;
			mode = 'lecture';
			if (!res.indexed) {
				toast.warning(
					$i18n.t("Fiche enregistrée, mais l'indexation pour le chat a échoué (nouvel essai au prochain enregistrement).")
				);
			} else {
				toast.success($i18n.t('Fiche enregistrée'));
			}
			await loadTree();
		} catch (e) {
			toast.error(`${e?.detail ?? e}`);
		}
		saving = false;
	};

	const createEntry = async () => {
		const name = newName.trim();
		if (!name || name.includes('/')) {
			toast.error($i18n.t('Nom invalide'));
			return;
		}
		const path = newParent ? `${newParent}/${name}` : name;
		try {
			if (creating === 'dossier') {
				await createDossier(localStorage.token, path);
			} else {
				await saveFiche(localStorage.token, path, `# ${name}\n\n`);
			}
			await loadTree();
			if (creating === 'fiche') {
				const entry = resolveFiche(path);
				if (entry) {
					await openFiche(entry);
					startEdit();
				}
			}
			creating = null;
			newName = '';
		} catch (e) {
			toast.error(`${e?.detail ?? e}`);
		}
	};

	// Les liens [[...]] rendus en <a> naviguent dans la page sans rechargement
	const onViewerClick = (e: MouseEvent) => {
		const anchor = (e.target as HTMLElement)?.closest?.('a');
		if (anchor?.getAttribute('href')?.startsWith('/memoire')) {
			e.preventDefault();
			goto(anchor.getAttribute('href') ?? '/memoire');
		}
	};

	onMount(async () => {
		await loadTree();
		// L'ouverture depuis ?fiche=... est déclenchée par le bloc réactif ci-dessus
		loaded = true;
	});
</script>

{#if loaded}
	<div class="flex w-full h-full max-h-full">
		<div
			class="w-64 shrink-0 border-r border-gray-100 dark:border-gray-850 flex flex-col max-h-full"
		>
			<div class="px-3 pt-3 pb-2 flex items-center justify-between">
				<div class="text-sm font-medium text-gray-800 dark:text-gray-200">
					{$i18n.t('Mon cerveau')}
				</div>
				<div class="flex gap-0.5">
					<button
						class="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						title={$i18n.t('Nouvelle fiche')}
						on:click={() => {
							creating = 'fiche';
							newName = '';
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.862 4.487l1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
							/>
						</svg>
					</button>
					<button
						class="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						title={$i18n.t('Nouveau dossier')}
						on:click={() => {
							creating = 'dossier';
							newName = '';
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 10.5v6m3-3H9m4.06-7.19-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
							/>
						</svg>
					</button>
				</div>
			</div>

			{#if creating}
				<div class="px-3 pb-2 flex flex-col gap-1.5">
					<input
						class="w-full text-sm px-2.5 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-850 outline-hidden"
						placeholder={creating === 'fiche'
							? $i18n.t('Nom de la fiche')
							: $i18n.t('Nom du dossier')}
						bind:value={newName}
						on:keydown={(e) => e.key === 'Enter' && createEntry()}
					/>
					<select
						class="w-full text-sm px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-850 outline-hidden"
						bind:value={newParent}
					>
						<option value="">{$i18n.t('À la racine')}</option>
						{#each dossiers as dossier (dossier.path)}
							<option value={dossier.path}>{dossier.path}</option>
						{/each}
					</select>
					<div class="flex gap-1.5">
						<button
							class="text-xs px-3 py-1.5 rounded-full bg-violet-600 hover:bg-violet-700 text-white transition"
							on:click={createEntry}
						>
							{$i18n.t('Créer')}
						</button>
						<button
							class="text-xs px-3 py-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => (creating = null)}
						>
							{$i18n.t('Annuler')}
						</button>
					</div>
				</div>
			{/if}

			<div class="flex-1 overflow-y-auto px-1.5 pb-3">
				{#each tree as entry (entry.path)}
					<TreeItem {entry} {selectedPath} onSelect={openFiche} />
				{/each}
			</div>
		</div>

		<div class="flex-1 max-h-full overflow-y-auto">
			{#if selectedPath}
				<div class="max-w-3xl mx-auto px-6 py-6">
					<div class="flex items-center justify-between mb-4">
						<h1 class="text-xl font-medium text-gray-900 dark:text-gray-100 truncate">
							{selectedName}
						</h1>
						{#if mode === 'lecture'}
							<button
								class="text-sm px-4 py-1.5 rounded-full bg-violet-600 hover:bg-violet-700 text-white transition shrink-0"
								on:click={startEdit}
							>
								{$i18n.t('Modifier')}
							</button>
						{:else}
							<div class="flex gap-1.5 shrink-0">
								<button
									class="text-sm px-4 py-1.5 rounded-full bg-violet-600 hover:bg-violet-700 text-white transition disabled:opacity-50"
									disabled={saving}
									on:click={save}
								>
									{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer')}
								</button>
								<button
									class="text-sm px-4 py-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
									on:click={() => (mode = 'lecture')}
								>
									{$i18n.t('Annuler')}
								</button>
							</div>
						{/if}
					</div>

					{#if mode === 'lecture'}
						<!-- svelte-ignore a11y-no-static-element-interactions -->
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<div class="markdown-prose" on:click={onViewerClick}>
							<Markdown id={`memoire-${selectedPath}`} content={renderWikilinks(content)} />
						</div>
					{:else}
						<textarea
							class="w-full min-h-[60vh] text-sm font-mono px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-850 outline-hidden resize-y"
							bind:value={draft}
							spellcheck="false"
						></textarea>
					{/if}
				</div>
			{:else}
				<div class="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
					<div class="text-center max-w-sm px-6">
						<div class="text-lg font-medium mb-1">{$i18n.t('Votre Mémoire')}</div>
						<div class="text-sm">
							{$i18n.t(
								'Choisissez une fiche dans la colonne de gauche, ou créez-en une nouvelle. Tout ce qui vit ici, votre assistant le connaît.'
							)}
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="h-full flex items-center justify-center">
		<Spinner className="size-5" />
	</div>
{/if}
