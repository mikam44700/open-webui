<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { uploadFile } from '$lib/apis/files';
	import { addFileToKnowledgeById, createNewKnowledge } from '$lib/apis/knowledge';
	import type { OnboardingDocument } from '$lib/onboarding-agentos/types';

	export let token: string;
	export let companyName = '';
	export let documents: OnboardingDocument[] = [];
	export let knowledgeBaseId = '';

	const dispatch = createEventDispatcher();
	const maxFiles = 10;
	const maxSize = 20 * 1024 * 1024;
	let knowledgePromise: Promise<string> | null = null;
	let input: HTMLInputElement;

	const publish = () =>
		dispatch('change', {
			documents,
			knowledgeBaseId
		});

	const ensureKnowledgeBase = async () => {
		if (knowledgeBaseId) return knowledgeBaseId;
		if (!knowledgePromise) {
			knowledgePromise = createNewKnowledge(
				token,
				`Documents d’onboarding — ${companyName || 'Entreprise'}`,
				'Documents confiés à LunarIA pendant la création de la Carte opérationnelle.',
				[]
			).then((knowledge) => {
				knowledgeBaseId = knowledge.id;
				publish();
				return knowledgeBaseId;
			});
		}
		return knowledgePromise;
	};

	const errorMessage = (error: unknown) => {
		if (typeof error === 'string') return error;
		if (error instanceof Error) return error.message;
		return "Le document n'a pas pu être ajouté à la mémoire.";
	};

	const uploadOne = async (file: File) => {
		const temporaryId = `${Date.now()}-${crypto.randomUUID()}`;
		documents = [
			...documents,
			{ id: temporaryId, name: file.name, size: file.size, status: 'uploading' }
		];
		publish();

		try {
			const baseId = await ensureKnowledgeBase();
			const uploaded = await uploadFile(
				token,
				file,
				{ source: 'onboarding-agentos', company: companyName },
				true
			);
			if (!uploaded?.id) throw new Error("Le serveur n'a pas retourné l'identifiant du document.");
			await addFileToKnowledgeById(token, baseId, uploaded.id);
			documents = documents.map((document) =>
				document.id === temporaryId
					? {
							...document,
							id: uploaded.id,
							status: 'done',
							message: 'Ajouté à la mémoire'
						}
					: document
			);
		} catch (error) {
			documents = documents.map((document) =>
				document.id === temporaryId
					? { ...document, status: 'error', message: errorMessage(error) }
					: document
			);
		}
		publish();
	};

	const selectFiles = async (event: Event) => {
		const files = Array.from((event.currentTarget as HTMLInputElement).files ?? []);
		const remaining = Math.max(0, maxFiles - documents.length);
		for (const file of files.slice(0, remaining)) {
			if (file.size > maxSize) {
				documents = [
					...documents,
					{
						id: `${Date.now()}-${crypto.randomUUID()}`,
						name: file.name,
						size: file.size,
						status: 'error',
						message: 'Ce fichier dépasse la limite de 20 Mo.'
					}
				];
				publish();
				continue;
			}
			await uploadOne(file);
		}
		input.value = '';
	};

	const formatSize = (size: number) =>
		size < 1024 * 1024
			? `${Math.max(1, Math.round(size / 1024))} Ko`
			: `${(size / 1024 / 1024).toFixed(1)} Mo`;

	$: uploading = documents.some((document) => document.status === 'uploading');
</script>

<section class="m-auto w-full max-w-4xl py-8">
	<div class="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
		<div>
			<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
				Étape 3 · Sources internes
			</div>
			<h1 class="mt-3 text-3xl font-medium tracking-[-0.03em] md:text-5xl">
				Donnez à Luna ce que votre site ne raconte pas.
			</h1>
			<p class="mt-5 text-sm leading-6 text-gray-500 dark:text-gray-400">
				Procédures, offres, présentation commerciale ou FAQ interne : ces documents rejoignent
				réellement la mémoire privée de votre entreprise.
			</p>
			<div
				class="mt-5 rounded-2xl bg-[#6b62f2]/8 p-4 text-xs leading-5 text-[#5149c7] dark:text-[#bbb7ff]"
			>
				Luna ne considère pas un document comme une vérité absolue : il reste identifiable comme
				source interne dans votre Carte.
			</div>
		</div>

		<div
			class="rounded-[2rem] border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616] md:p-7"
		>
			<input
				bind:this={input}
				type="file"
				multiple
				accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.md,.html"
				class="hidden"
				on:change={selectFiles}
			/>
			<button
				class="flex min-h-36 w-full flex-col items-center justify-center rounded-2xl border border-dashed border-[#6b62f2]/40 bg-[#6b62f2]/[0.035] p-5 text-center transition hover:bg-[#6b62f2]/[0.07] disabled:opacity-50"
				disabled={uploading || documents.length >= maxFiles}
				on:click={() => input.click()}
			>
				<div
					class="flex size-11 items-center justify-center rounded-2xl bg-[#6b62f2]/10 text-xl text-[#6b62f2]"
				>
					↑
				</div>
				<div class="mt-3 text-sm font-medium">Choisir des documents</div>
				<div class="mt-1 text-xs text-gray-400">
					PDF, Office, CSV ou texte · 20 Mo maximum · 10 fichiers
				</div>
			</button>

			{#if documents.length}
				<div class="mt-4 space-y-2">
					{#each documents as document}
						<div class="flex items-center gap-3 rounded-2xl bg-gray-50 p-3 dark:bg-[#101010]">
							<div
								class="flex size-8 shrink-0 items-center justify-center rounded-xl text-xs {document.status ===
								'done'
									? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
									: document.status === 'error'
										? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300'
										: 'bg-[#6b62f2]/10 text-[#6b62f2]'}"
							>
								{document.status === 'done' ? '✓' : document.status === 'error' ? '!' : '…'}
							</div>
							<div class="min-w-0 flex-1">
								<div class="truncate text-xs font-medium">{document.name}</div>
								<div class="mt-0.5 text-[11px] text-gray-400">
									{formatSize(document.size)} · {document.message ||
										'Envoi et indexation en cours…'}
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<div
				class="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-5 dark:border-gray-800"
			>
				<button class="text-sm text-gray-500" on:click={() => dispatch('back')}>Retour</button>
				<div class="flex items-center gap-2">
					{#if !documents.some((document) => document.status === 'done')}
						<button
							class="rounded-full px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
							disabled={uploading}
							on:click={() => dispatch('done')}>Continuer sans document</button
						>
					{/if}
					{#if documents.some((document) => document.status === 'done')}
						<button
							class="rounded-full bg-[#6b62f2] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
							disabled={uploading}
							on:click={() => dispatch('done')}>Continuer avec ces sources</button
						>
					{/if}
				</div>
			</div>
		</div>
	</div>
</section>
