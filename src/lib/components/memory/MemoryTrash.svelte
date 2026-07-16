<script lang="ts">
	// Corbeille : notes/dossiers supprimés dans LunarIA, récupérables. Extrait de
	// MemoryExplorer.svelte (finding découpe) — comportement inchangé : recharge la liste à
	// chaque ouverture (montage du composant), restauration, suppression définitive confirmée
	// (item par item ou vidage complet), rien n'est jamais purgé tout seul.
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getTrash,
		restoreFolder,
		restoreMemoryNote,
		purgeTrashItem,
		emptyTrash
	} from '$lib/apis/memory';
	import type { TrashItem } from '$lib/apis/memory';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	export let friendlyFolder: (name: string) => string;
	export let formatModified: (epoch: number | null) => string;
	// Recharge l'arbre du coffre (parent) : nécessaire après restauration pour faire réapparaître
	// l'élément à sa place.
	export let onReload: () => Promise<void>;
	export let onClose: () => void;

	let trashItems: TrashItem[] = [];
	let trashLoading = false;

	// Recharge la corbeille elle-même (pas seulement l'arbre du parent) : nécessaire quand un
	// élément listé ici n'existe déjà plus côté serveur (404) ou a changé (409 — restauré ailleurs,
	// conflit de nom), pour ne pas laisser une liste périmée où « Restaurer »/« Supprimer »
	// échoueraient à nouveau sans que le dirigeant comprenne pourquoi.
	const reloadTrash = async (): Promise<void> => {
		try {
			trashItems = (await getTrash(localStorage.token)).items ?? [];
		} catch {
			/* affichage best-effort : la corbeille garde sa dernière liste connue */
		}
	};

	// Erreurs CRUD : distingue le code renvoyé par le bridge (même principe que
	// BrainMemoryPane.isConflict / MemoryExplorer.reportCrudError) plutôt qu'un message générique
	// unique — un 404/409 signifie que la liste affichée est FAUSSE, pas juste qu'une action a
	// échoué : on la recharge plutôt que de laisser le dirigeant réessayer sur des données périmées.
	const STALE_CRUD_CODES = new Set(['not_found', 'destination_exists', 'already_exists']);
	const reportCrudError = async (e: any, fallback: string): Promise<void> => {
		toast.error(e?.error?.message ?? (typeof e === 'string' ? e : fallback));
		if (STALE_CRUD_CODES.has(e?.error?.code)) await reloadTrash();
	};

	onMount(async () => {
		trashLoading = true;
		try {
			trashItems = (await getTrash(localStorage.token)).items ?? [];
		} catch (e) {
			toast.error(typeof e === 'string' ? e : "Impossible d'ouvrir la corbeille");
		}
		trashLoading = false;
	});

	const restoreFromTrash = async (item: TrashItem) => {
		try {
			if (item.type === 'folder') await restoreFolder(localStorage.token, item.ref, item.path);
			else await restoreMemoryNote(localStorage.token, item.ref, item.path);
			trashItems = trashItems.filter((t) => t.ref !== item.ref);
			await onReload(); // recharge l'arbre pour faire réapparaître l'élément restauré
			toast.success(`« ${item.name} » restauré`);
		} catch (e) {
			await reportCrudError(e, 'Impossible de restaurer cet élément');
		}
	};

	// Suppression DÉFINITIVE : rien ne part sans un « oui » explicite du dirigeant. Le produit, lui,
	// ne purge jamais tout seul (pas de délai d'expiration) — mais on ne l'enferme pas non plus.
	let purgeTarget: TrashItem | null = null;
	let showPurgeConfirm = false;
	let showEmptyTrashConfirm = false;

	const askPurge = (item: TrashItem) => {
		purgeTarget = item;
		showPurgeConfirm = true;
	};

	const trashTotalSize = (items: TrashItem[]): number =>
		items.reduce((sum, i) => sum + (i.size ?? 0), 0);

	// Taille lisible (« 4,2 Mo ») — le dirigeant doit voir la place qu'il récupère.
	const formatSize = (bytes: number): string => {
		if (!bytes) return '0 o';
		const units = ['o', 'Ko', 'Mo', 'Go'];
		const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, i);
		return `${value.toLocaleString('fr-FR', { maximumFractionDigits: i === 0 ? 0 : 1 })} ${units[i]}`;
	};

	const purgeOne = async () => {
		const item = purgeTarget;
		if (!item) return;
		try {
			await purgeTrashItem(localStorage.token, item.ref);
			trashItems = trashItems.filter((t) => t.ref !== item.ref);
			toast.success(`« ${item.name} » supprimé définitivement`);
		} catch (e) {
			await reportCrudError(e, 'Impossible de supprimer cet élément');
		}
		purgeTarget = null;
	};

	const purgeAll = async () => {
		try {
			const { purged } = await emptyTrash(localStorage.token);
			trashItems = [];
			toast.success(purged > 1 ? `${purged} éléments supprimés définitivement` : 'Corbeille vidée');
		} catch (e) {
			await reportCrudError(e, 'Impossible de vider la corbeille');
		}
	};
</script>

<div class="mt-2.5">
	<div class="flex items-center gap-2 px-1 mb-3">
		<button
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 transition"
			on:click={onClose}
			aria-label="Retour au coffre"
		>
			<ChevronLeft className="size-4" />
		</button>
		<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">Corbeille</div>
		<div class="text-xs text-gray-400 dark:text-gray-600">
			· rien n'est supprimé tout seul{#if trashItems.length > 0} · {formatSize(
					trashTotalSize(trashItems)
				)}{/if}
		</div>
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
							Supprimé le {formatModified(item.deleted_at)}{#if item.path.includes('/')} · depuis {friendlyFolder(
									item.path.split('/')[0]
								)}{/if}{#if item.size} · {formatSize(item.size)}{/if}
						</div>
					</div>
					<button
						class="shrink-0 text-xs px-2.5 py-1.5 rounded-lg text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-900/20 transition font-medium"
						on:click={() => restoreFromTrash(item)}
					>
						Restaurer
					</button>
					<Tooltip content="Supprimer définitivement">
						<button
							class="shrink-0 text-xs px-2.5 py-1.5 rounded-lg text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition font-medium"
							on:click={() => askPurge(item)}
							aria-label={`Supprimer définitivement ${item.name}`}
						>
							Supprimer
						</button>
					</Tooltip>
				</div>
			{/each}
		</div>
		<button
			class="mt-4 mb-8 mx-auto flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-600 hover:text-red-600 dark:hover:text-red-400 transition"
			on:click={() => (showEmptyTrashConfirm = true)}
		>
			Vider la corbeille
		</button>
	{/if}
</div>

<!-- Suppression définitive : on NOMME ce qui disparaît et on dit que c'est sans retour. -->
<ConfirmDialog
	bind:show={showPurgeConfirm}
	title="Supprimer définitivement ?"
	message={purgeTarget
		? `« ${purgeTarget.name} » sera effacé de votre coffre pour de bon. Cette action est irréversible : nous ne pourrons pas le récupérer.`
		: ''}
	confirmLabel="Supprimer définitivement"
	cancelLabel="Annuler"
	on:confirm={purgeOne}
	on:cancel={() => (purgeTarget = null)}
/>

<ConfirmDialog
	bind:show={showEmptyTrashConfirm}
	title="Vider la corbeille ?"
	message={`Les ${trashItems.length} éléments de la corbeille (${formatSize(
		trashTotalSize(trashItems)
	)}) seront effacés pour de bon. Cette action est irréversible : nous ne pourrons rien récupérer.`}
	confirmLabel="Vider la corbeille"
	cancelLabel="Annuler"
	on:confirm={purgeAll}
/>
