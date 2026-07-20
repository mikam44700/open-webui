<script>
	// Page Documents (SPEC-page-documents) : la maison des livrables produits par les
	// agents. Elle lit l'API officielle des fichiers et ne montre QUE ceux marqués
	// « document d'agent » (métadonnée lunaria_document posée par le pont Fichiers) —
	// jamais les pièces jointes déposées dans les conversations.
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import dayjs from '$lib/dayjs';
	import { mobile, showSidebar } from '$lib/stores';
	import { getFiles } from '$lib/apis/files';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let loaded = false;
	let documents = [];

	// Icône simple par famille de fichier — lisible d'un coup d'œil, sans bibliothèque.
	const iconeParExtension = (nom) => {
		const ext = (nom ?? '').split('.').pop()?.toLowerCase();
		if (['xlsx', 'xls', 'csv'].includes(ext)) return '📊';
		if (['docx', 'doc'].includes(ext)) return '📝';
		if (['pptx', 'ppt'].includes(ext)) return '📽️';
		if (ext === 'pdf') return '📄';
		return '📎';
	};

	onMount(async () => {
		// L'API répond { items, total } (FileListResponse) — on déballe puis on filtre.
		const res = await getFiles(localStorage.token).catch(() => null);
		const files = res?.items ?? (Array.isArray(res) ? res : []);
		documents = files
			.filter((f) => f?.meta?.data?.lunaria_document)
			.sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0));
		loaded = true;
	});
</script>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<nav class="px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class="flex items-center gap-1">
			{#if $mobile || !$showSidebar}
				<div class="flex flex-none items-center">
					<button
						class="p-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => showSidebar.set(!$showSidebar)}
						aria-label={$i18n.t('Toggle Sidebar')}
					>
						<Sidebar className="size-5" />
					</button>
				</div>
			{/if}
			<div class="font-primary text-lg font-medium px-1.5 py-1">{$i18n.t('Documents')}</div>
		</div>
	</nav>

	<div class="flex-1 overflow-y-auto px-4 md:px-8 py-4">
		<div class="max-w-3xl mx-auto w-full">
			<div class="text-sm text-gray-500 dark:text-gray-400 mb-4">
				Les livrables produits par tes agents — téléchargeables à tout moment.
			</div>

			{#if !loaded}
				<div class="flex justify-center py-10"><Spinner className="size-5" /></div>
			{:else if documents.length === 0}
				<div
					class="rounded-2xl border border-gray-100 dark:border-gray-850 px-6 py-10 text-center text-sm text-gray-500 dark:text-gray-400"
				>
					Aucun document pour l'instant.<br />
					Demande un tableau, un rapport ou une présentation à Théo — son premier livrable apparaîtra
					ici.
				</div>
			{:else}
				<div class="flex flex-col gap-1.5">
					{#each documents as doc (doc.id)}
						<div
							class="flex items-center gap-3 rounded-2xl border border-gray-100 dark:border-gray-850 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
						>
							<div class="text-xl flex-none" aria-hidden="true">
								{iconeParExtension(doc.filename)}
							</div>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-medium truncate">{doc.filename}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{doc?.meta?.data?.lunaria_agent
										? `Produit par ${doc.meta.data.lunaria_agent} · `
										: ''}{dayjs(doc.created_at * 1000).format('DD/MM/YYYY HH:mm')}
								</div>
							</div>
							<Tooltip content={$i18n.t('Download')} placement="top">
								<a
									class="flex-none px-3 py-1.5 rounded-xl text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 transition"
									href={`${WEBUI_API_BASE_URL}/files/${doc.id}/content`}
									target="_blank"
									rel="noreferrer"
								>
									{$i18n.t('Download')}
								</a>
							</Tooltip>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
