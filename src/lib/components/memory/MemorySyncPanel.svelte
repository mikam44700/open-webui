<script lang="ts">
	// Bandeau de synchronisation du coffre avec Obsidian (sync Syncthing pré-appairée).
	// Extrait de MemoryExplorer.svelte (finding découpe) — comportement inchangé, 3 états honnêtes :
	// indisponible / déjà relié / relié-able (téléchargement du pack).
	import { toast } from 'svelte-sonner';
	import { getSyncPack, downloadSyncPack } from '$lib/apis/memory';
	import type { MemoryStatus } from '$lib/apis/memory';

	export let status: MemoryStatus | null;

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
</script>

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
	{:else if status.sync_available}
		<!-- Une invitation, pas un défaut : le coffre existe déjà, il ne lui manque qu'une copie
		     locale. Et ce bloc n'apparaît QUE là où le pack peut vraiment être généré. -->
		<div
			class="mb-3 flex flex-wrap items-center gap-3 rounded-2xl bg-sky-50/70 dark:bg-sky-900/15 ring-1 ring-inset ring-sky-500/20 px-3.5 py-3"
		>
			<div class="min-w-0 flex-1">
				<div class="text-[13px] font-medium text-gray-900 dark:text-white">
					Ouvrir votre coffre dans Obsidian
				</div>
				<div class="text-[12px] text-gray-500 dark:text-gray-400">
					Vos {status.note_count} notes sont enregistrées. Installez la copie sur votre ordinateur
					pour les ouvrir dans Obsidian.
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
