<script lang="ts">
	// Étape « Vos documents » (juste avant Adam) : le dirigeant dépose des fichiers (plaquette,
	// catalogue, CGV, tarifs…) qui NOURRISSENT la base de connaissances de ses agents. Vaut pour les
	// deux chemins (avec site ET sans site). 100 % optionnel. Le fil narratif : on fournit ici → Adam
	// range → l'écran final révèle une équipe qui « a tout lu ». L'upload réel est délégué à l'API
	// (uploadCompanyDocument) ; ici on gère la file d'attente + l'état honnête de chaque fichier.
	import { createEventDispatcher, getContext } from 'svelte';
	// Pipeline 100 % existant : upload (extraction du texte) → base de connaissances → recopie dans le
	// coffre Obsidian (lisible par les agents Hermes). Aucun code backend nouveau.
	import { uploadFile } from '$lib/apis/files';
	import { createNewKnowledge, addFileToKnowledgeById } from '$lib/apis/knowledge';
	import { syncKnowledgeToAgent } from '$lib/apis/knowledge-agent';
	// Avatars réels des agents (même source que le chat / l'écran final).
	import { AGENT_TEMPLATES } from '$lib/components/agents/templates';
	import { faceFromImage, avatarId } from '$lib/components/agents/avatars';
	import { avatarColor } from '$lib/components/agents/avatar-colors';
	import { avatarImgFallback } from '$lib/utils/agentIdentity';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// On présente l'upload PAR AGENT (visage + exemple CONCRET du document dont il a besoin) plutôt
	// que par catégories abstraites : le dirigeant voit à qui ça sert. Les documents vont dans la base
	// commune (tous les agents y accèdent) — cliquer une carte est un pur guide, aucune cible imposée.
	// 7 agents principaux visibles ; les autres, repliés (moins de besoin documentaire au quotidien).
	type AgentDoc = { id: string; example: string };
	const PRIMARY_AGENTS: AgentDoc[] = [
		{ id: 'commercial-devis', example: 'Votre catalogue et vos tarifs' },
		{ id: 'comptable-impayes', example: 'Vos factures et conditions de paiement' },
		{ id: 'service-client', example: 'Votre FAQ et vos procédures SAV' },
		{ id: 'redacteur-documents', example: 'Votre plaquette et vos modèles de courriers' },
		{ id: 'assistant-administratif', example: 'Vos procédures internes' },
		{ id: 'conformite-juridique', example: 'Vos CGV, contrats et mentions légales' },
		{ id: 'finance-previsionnel', example: 'Vos bilans et votre prévisionnel' }
	];
	const MORE_AGENTS: AgentDoc[] = [
		{ id: 'rh', example: 'Contrats de travail, fiches de poste' },
		{ id: 'achats-fournisseurs', example: 'Contrats et conditions fournisseurs' },
		{ id: 'chasseur-clients', example: 'Personas, fichiers prospects' },
		{ id: 'marketing-presence', example: 'Charte graphique, contenus' },
		{ id: 'pilote-briefing', example: 'Plannings, comptes-rendus' },
		{ id: 'analyste-commercial', example: 'Scripts et enregistrements d’appels' },
		{ id: 'livraison-projet', example: 'Vos process de livraison client' },
		{ id: 'veille', example: 'Vos documents de veille concurrents' }
	];
	const tpl = (id: string) => AGENT_TEMPLATES.find((t) => t.id === id);
	let showAll = false;

	type DocState = 'uploading' | 'done' | 'error';
	type Doc = { id: string; name: string; size: number; status: DocState };
	let docs: Doc[] = [];
	let dragOver = false;
	let fileInput: HTMLInputElement;
	let seq = 0; // identifiants locaux stables (pas de Math.random dans ce projet)
	// Base de connaissances dédiée, créée à la volée au 1er document puis réutilisée pour les suivants.
	let kbId: string | null = null;
	let finishing = false; // recopie finale vers le coffre en cours

	const ensureKb = async (token: string): Promise<string> => {
		if (kbId) return kbId;
		const kb = await createNewKnowledge(
			token,
			'Documents de l’entreprise',
			'Documents fournis à l’accueil pour nourrir les agents.',
			[] // aucun partage : la base reste privée au dirigeant
		);
		kbId = kb.id;
		return kbId;
	};

	const humanSize = (bytes: number): string => {
		if (bytes < 1024) return `${bytes} o`;
		if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
	};

	const setStatus = (id: string, status: DocState) => {
		docs = docs.map((d) => (d.id === id ? { ...d, status } : d));
	};

	// Ajoute puis téléverse chaque fichier, en reflétant honnêtement l'issue (jamais bloquant).
	const addFiles = async (list: FileList | File[]) => {
		const files = Array.from(list);
		for (const file of files) {
			const id = `doc-${seq++}`;
			docs = [...docs, { id, name: file.name, size: file.size, status: 'uploading' }];
			try {
				// 1) upload + extraction du texte, 2) ajout à la base de connaissances (créée au besoin).
				const uploaded = await uploadFile(localStorage.token, file, null, true);
				const kb = await ensureKb(localStorage.token);
				await addFileToKnowledgeById(localStorage.token, kb, uploaded.id);
				setStatus(id, 'done');
			} catch (e) {
				console.error(e);
				setStatus(id, 'error');
			}
		}
	};

	const onPick = (e: Event) => {
		const input = e.currentTarget as HTMLInputElement;
		if (input.files?.length) addFiles(input.files);
		input.value = ''; // permet de re-choisir le même fichier
	};
	const onDrop = (e: DragEvent) => {
		e.preventDefault();
		dragOver = false;
		if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files);
	};
	const removeDoc = (id: string) => (docs = docs.filter((d) => d.id !== id));

	// « Continuer » : on recopie les documents dans le coffre (lisible par les agents Hermes) AVANT de
	// passer à Adam. Best-effort — un échec de recopie n'empêche jamais d'avancer.
	const finishDocuments = async () => {
		const count = docs.filter((d) => d.status === 'done').length;
		if (kbId) {
			finishing = true;
			try {
				await syncKnowledgeToAgent(localStorage.token, kbId);
			} catch (e) {
				console.error(e);
			} finally {
				finishing = false;
			}
		}
		dispatch('next', { count });
	};

	$: anyUploading = docs.some((d) => d.status === 'uploading');
</script>

<div class="w-full max-w-2xl mx-auto px-5 py-9 sm:py-10">
	<!-- En-tête : le pourquoi, avant tout -->
	<div class="text-center">
		<div class="text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-600 dark:text-amber-300/90">
			{$i18n.t('Nourrissez votre équipe')}
		</div>
		<h1 class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
			{$i18n.t('Vos documents')}
		</h1>
		<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md mx-auto">
			{$i18n.t(
				'Déposez ce que vous voulez — vos agents le liront pour mieux vous répondre. C’est facultatif, et vous pourrez en ajouter à tout moment.'
			)}
		</p>
	</div>

	<!-- Carte agent : visage (fond = couleur signature) + prénom + rôle + exemple de document. -->
	{#snippet agentCard(a: AgentDoc)}
		{@const t = tpl(a.id)}
		{#if t}
			<button
				type="button"
				on:click={() => fileInput?.click()}
				class="flex items-start gap-3 rounded-2xl bg-white dark:bg-white/[0.03] ring-1 ring-inset ring-black/5 dark:ring-white/10 px-4 py-3.5 text-left hover:ring-amber-400/50 transition"
			>
				<img
					src={faceFromImage(t.image) ?? '/favicon.png'}
					alt={t.firstName}
					on:error={(e) => avatarImgFallback(e, t.image)}
					style="background: {avatarColor(avatarId(t.image) || t.firstName).gradient}"
					class="flex-none h-10 w-10 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15"
				/>
				<span class="min-w-0">
					<span class="flex items-baseline gap-1.5">
						<span class="text-sm font-semibold text-gray-900 dark:text-white">{t.firstName}</span>
						<span class="text-[11px] text-gray-400 dark:text-gray-500 truncate">{$i18n.t(t.role)}</span>
					</span>
					<span class="block text-[12.5px] text-gray-500 dark:text-gray-400">→ {$i18n.t(a.example)}</span>
				</span>
			</button>
		{/if}
	{/snippet}

	<!-- Suggestions PAR AGENT : 7 principaux, puis les autres à la demande -->
	<div class="mt-7 grid gap-2.5 sm:grid-cols-2">
		{#each PRIMARY_AGENTS as a (a.id)}{@render agentCard(a)}{/each}
		{#if showAll}
			{#each MORE_AGENTS as a (a.id)}{@render agentCard(a)}{/each}
		{/if}
	</div>
	<button
		type="button"
		on:click={() => (showAll = !showAll)}
		class="mt-3 w-full text-center text-[13px] font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 transition"
	>
		{showAll
			? $i18n.t('Voir moins')
			: $i18n.t('Voir les {{n}} autres agents', { n: MORE_AGENTS.length })}
	</button>

	<!-- Zone de dépôt (glisser-déposer + parcourir) -->
	<label
		on:dragover|preventDefault={() => (dragOver = true)}
		on:dragleave={() => (dragOver = false)}
		on:drop={onDrop}
		class="mt-4 flex flex-col items-center justify-center gap-1.5 rounded-2xl border border-dashed px-5 py-8 text-center cursor-pointer transition {dragOver
			? 'border-amber-500 bg-amber-50/60 dark:bg-amber-400/[0.06]'
			: 'border-gray-300 dark:border-white/15 hover:border-amber-400/60'}"
	>
		<input
			bind:this={fileInput}
			type="file"
			multiple
			on:change={onPick}
			class="hidden"
			accept=".pdf,.doc,.docx,.txt,.md,.csv,.xls,.xlsx,.ppt,.pptx"
		/>
		<span class="text-sm font-semibold text-gray-800 dark:text-gray-100">
			{$i18n.t('Glissez vos fichiers ici')}
		</span>
		<span class="text-[13px] text-gray-500 dark:text-gray-400">
			{$i18n.t('ou cliquez pour parcourir · PDF, Word, Excel, texte…')}
		</span>
	</label>

	<!-- Liste des fichiers déposés + état honnête -->
	{#if docs.length}
		<div class="mt-4 flex flex-col gap-2">
			{#each docs as d (d.id)}
				<div
					class="flex items-center gap-3 rounded-xl bg-white dark:bg-white/[0.03] ring-1 ring-inset ring-black/5 dark:ring-white/10 px-3.5 py-2.5"
				>
					<span class="text-lg leading-none" aria-hidden="true">📎</span>
					<span class="min-w-0 flex-1">
						<span class="block text-sm text-gray-900 dark:text-white truncate">{d.name}</span>
						<span class="block text-[12px] text-gray-400 dark:text-gray-500">{humanSize(d.size)}</span>
					</span>
					{#if d.status === 'uploading'}
						<span class="inline-block h-4 w-4 rounded-full border-2 border-amber-500 border-t-transparent animate-spin"></span>
					{:else if d.status === 'done'}
						<span class="text-emerald-500 font-bold" title={$i18n.t('Ajouté')}>✓</span>
					{:else}
						<span class="text-[12px] text-red-500" title={$i18n.t('Échec de l’envoi')}>{$i18n.t('échec')}</span>
					{/if}
					<button
						type="button"
						on:click={() => removeDoc(d.id)}
						aria-label={$i18n.t('Retirer')}
						class="h-6 w-6 flex-none rounded-full flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition"
					>×</button>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Navigation (le « Retour » ET le « Plus tard » global sont fournis par le header du parcours).
	     Un seul bouton d'action : il continue avec ou sans document. -->
	<div class="mt-8 flex items-center justify-end">
		<button
			disabled={anyUploading || finishing}
			class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 disabled:opacity-60"
			on:click={finishDocuments}
		>
			{#if finishing}
				{$i18n.t('Enregistrement…')}
			{:else}
				{docs.some((d) => d.status === 'done') ? $i18n.t('Continuer') : $i18n.t('Continuer sans document')} →
			{/if}
		</button>
	</div>
</div>
