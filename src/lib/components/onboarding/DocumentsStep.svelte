<script lang="ts">
	// Étape « Vos documents » (juste avant Adam) : le dirigeant nourrit ses agents avec des fichiers.
	// Présentée PAR AGENT — chaque agent a SON bouton « Ajouter » et SA base de documents (rangée chez
	// lui, option A) : les docs de Maxime vont chez Maxime, ils ne se mélangent pas. 100 % optionnel.
	// Pipeline 100 % existant : uploadFile (extraction) → base de connaissances DE L'AGENT →
	// syncKnowledgeToAgent (recopie dans le coffre, lisible par Hermes). Aucun code backend nouveau.
	import { createEventDispatcher, getContext } from 'svelte';
	import { uploadFile } from '$lib/apis/files';
	import { createNewKnowledge, addFileToKnowledgeById } from '$lib/apis/knowledge';
	import { syncKnowledgeToAgent } from '$lib/apis/knowledge-agent';
	import { AGENT_TEMPLATES, SOCLE_IDS } from '$lib/components/agents/templates';
	import { faceFromImage, avatarId } from '$lib/components/agents/avatars';
	import { avatarColor } from '$lib/components/agents/avatar-colors';
	import { avatarImgFallback } from '$lib/utils/agentIdentity';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Garde-fous d'upload : évitent d'abuser la mémoire d'un agent (et de la noyer de bruit).
	const MAX_FILE_MB = 20; // taille max par fichier
	const MAX_DOCS_PER_AGENT = 15; // nombre max de documents par agent

	// Pour chaque agent : un exemple CONCRET des documents qu'il attend (guide le dirigeant).
	type AgentDoc = { id: string; example: string };

	// Exemple de documents attendus, par agent. Sert aussi de filtre : seuls les agents présents ici
	// sont montrés sur cet écran documentaire.
	const EXAMPLES: Record<string, string> = {
		'assistant-administratif': 'Vos procédures internes, vos modèles de courriers, votre organigramme',
		'commercial-devis': 'Votre catalogue, vos tarifs, un modèle de devis',
		'comptable-impayes': 'Un modèle de facture, vos conditions de paiement, vos relances',
		'redacteur-de-documents': 'Votre plaquette, votre charte éditoriale, vos modèles de courriers',
		veille: 'Vos documents de veille concurrents',
		'service-client': 'Votre FAQ, vos procédures SAV, vos conditions de garantie',
		'conformite-juridique': 'Vos CGV, vos contrats types, vos mentions légales',
		'finance-previsionnel': 'Vos bilans, votre prévisionnel, votre budget',
		rh: 'Contrats de travail, fiches de poste, convention collective',
		'achats-fournisseurs': 'Contrats et conditions fournisseurs',
		'chasseur-clients': 'Personas, fichiers prospects, argumentaires',
		'marketing-presence': 'Charte graphique, contenus, calendrier éditorial',
		'pilote-briefing': 'Plannings, comptes-rendus, objectifs',
		'analyste-commercial': 'Scripts et enregistrements d’appels',
		'livraison-projet': 'Vos process de livraison client'
	};

	// Mike (chef d'orchestre, n'ingère pas de documents) et Adam (mémoire, il a sa propre étape juste
	// après) sont volontairement écartés de cet écran, bien qu'ils fassent partie du socle.
	const EXCLUDED = new Set(['mike-chef-orchestre', 'agent-obsidian']);
	const shown = (t: (typeof AGENT_TEMPLATES)[number]) => !EXCLUDED.has(t.id) && !!EXAMPLES[t.id];
	const toDoc = (t: (typeof AGENT_TEMPLATES)[number]): AgentDoc => ({ id: t.id, example: EXAMPLES[t.id] });

	// ACTIFS = les agents du socle des 7 pertinents pour les documents (socle − Mike − Adam).
	// Dérivé de SOCLE_IDS → reste automatiquement cohérent si le socle évolue (source de vérité unique).
	const PRIMARY_AGENTS: AgentDoc[] = AGENT_TEMPLATES.filter((t) => SOCLE_IDS.has(t.id) && shown(t)).map(toDoc);
	// À ACTIVER = le catalogue (hors socle) : le dirigeant devra les activer depuis ses Capacités.
	const MORE_AGENTS: AgentDoc[] = AGENT_TEMPLATES.filter((t) => !SOCLE_IDS.has(t.id) && shown(t)).map(toDoc);
	const tpl = (id: string) => AGENT_TEMPLATES.find((t) => t.id === id);
	let showAll = false;

	type DocState = 'uploading' | 'done' | 'error';
	type Doc = { id: string; name: string; size: number; status: DocState };
	// Documents ET base de connaissances PAR agent (rangé chez lui — option A).
	let docsByAgent: Record<string, Doc[]> = {};
	let kbByAgent: Record<string, string> = {};
	let noticeByAgent: Record<string, string> = {}; // message de garde-fou par agent (limite atteinte…)
	let seq = 0;
	let finishing = false;

	let fileInput: HTMLInputElement;
	let pickerAgent: string | null = null; // agent pour lequel le sélecteur de fichiers est ouvert

	const humanSize = (bytes: number): string => {
		if (bytes < 1024) return `${bytes} o`;
		if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
	};

	const setStatus = (agentId: string, docId: string, status: DocState) => {
		docsByAgent = {
			...docsByAgent,
			[agentId]: (docsByAgent[agentId] ?? []).map((d) => (d.id === docId ? { ...d, status } : d))
		};
	};
	const removeDoc = (agentId: string, docId: string) => {
		docsByAgent = { ...docsByAgent, [agentId]: (docsByAgent[agentId] ?? []).filter((d) => d.id !== docId) };
		clearNotice(agentId); // libère la place → l'avertissement de limite n'a plus lieu d'être
	};

	// Base de connaissances propre à l'agent, créée à la volée au 1er document.
	const ensureKbFor = async (agentId: string, label: string): Promise<string> => {
		if (kbByAgent[agentId]) return kbByAgent[agentId];
		const kb = await createNewKnowledge(
			token(),
			`Documents ${label}`,
			`Documents fournis à l’accueil pour l’agent ${label}.`,
			[] // aucun partage : la base reste privée au dirigeant
		);
		kbByAgent = { ...kbByAgent, [agentId]: kb.id };
		return kb.id;
	};

	const token = (): string => localStorage.token;

	const setNotice = (agentId: string, msg: string) => {
		noticeByAgent = { ...noticeByAgent, [agentId]: msg };
	};
	const clearNotice = (agentId: string) => {
		if (!noticeByAgent[agentId]) return;
		const { [agentId]: _drop, ...rest } = noticeByAgent;
		noticeByAgent = rest;
	};

	const addFilesForAgent = async (agentId: string, label: string, list: FileList | File[]) => {
		clearNotice(agentId);
		// On compte les documents déjà présents (en cours ou réussis) pour cet agent.
		let current = (docsByAgent[agentId] ?? []).filter((d) => d.status !== 'error').length;
		for (const file of Array.from(list)) {
			// Garde-fou nombre : au-delà de la limite, on arrête et on prévient.
			if (current >= MAX_DOCS_PER_AGENT) {
				setNotice(
					agentId,
					$i18n.t('Maximum {{n}} documents par agent. Retirez-en pour en ajouter d’autres.', {
						n: MAX_DOCS_PER_AGENT
					})
				);
				break;
			}
			// Garde-fou taille : on refuse le fichier trop lourd sans bloquer les suivants.
			if (file.size > MAX_FILE_MB * 1024 * 1024) {
				setNotice(
					agentId,
					$i18n.t('« {{name}} » dépasse {{n}} Mo et n’a pas été ajouté.', {
						name: file.name,
						n: MAX_FILE_MB
					})
				);
				continue;
			}
			const id = `doc-${seq++}`;
			current += 1;
			docsByAgent = {
				...docsByAgent,
				[agentId]: [...(docsByAgent[agentId] ?? []), { id, name: file.name, size: file.size, status: 'uploading' }]
			};
			try {
				const uploaded = await uploadFile(token(), file, null, true);
				const kb = await ensureKbFor(agentId, label);
				await addFileToKnowledgeById(token(), kb, uploaded.id);
				setStatus(agentId, id, 'done');
			} catch (e) {
				console.error(e);
				setStatus(agentId, id, 'error');
			}
		}
	};

	const openPickerFor = (agentId: string) => {
		pickerAgent = agentId;
		fileInput?.click();
	};
	const onPick = (e: Event) => {
		const input = e.currentTarget as HTMLInputElement;
		if (input.files?.length && pickerAgent) {
			addFilesForAgent(pickerAgent, tpl(pickerAgent)?.firstName ?? '', input.files);
		}
		input.value = ''; // permet de re-choisir le même fichier
	};

	// « Continuer » : on recopie CHAQUE base d'agent dans le coffre (best-effort) avant de passer à Adam.
	// Best-effort ASSUMÉ (non bloquant) : un échec de synchro n'arrête pas le parcours, mais il n'est
	// plus avalé en silence — `syncFailures` remonte jusqu'à l'écran final (audit 2026-07-15 : le
	// dirigeant croyait ses documents rangés à tort).
	const finishDocuments = async () => {
		const count = Object.values(docsByAgent)
			.flat()
			.filter((d) => d.status === 'done').length;
		const kbs = Object.values(kbByAgent);
		let syncFailures = 0;
		if (kbs.length) {
			finishing = true;
			try {
				for (const kbId of kbs) {
					try {
						await syncKnowledgeToAgent(token(), kbId);
					} catch (e) {
						console.error(e);
						syncFailures += 1;
					}
				}
			} finally {
				finishing = false;
			}
		}
		dispatch('next', { count, syncFailures });
	};

	$: anyUploading = Object.values(docsByAgent)
		.flat()
		.some((d) => d.status === 'uploading');
	$: anyDone = Object.values(docsByAgent)
		.flat()
		.some((d) => d.status === 'done');
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
				'Ce n’est pas obligatoire — mais c’est le meilleur moyen pour que vos agents connaissent votre entreprise à 100 %. Chaque document va directement à l’agent concerné.'
			)}
		</p>
		<p class="mt-2 text-[12.5px] text-gray-400 dark:text-gray-500 max-w-md mx-auto">
			🔒 {$i18n.t(
				'Vos documents restent privés. Chaque agent n’utilise que les siens, rangés dans sa propre mémoire.'
			)}
		</p>
	</div>

	<!-- Sélecteur de fichiers unique, réutilisé pour l'agent en cours (pickerAgent). -->
	<input
		bind:this={fileInput}
		type="file"
		multiple
		on:change={onPick}
		class="hidden"
		accept=".pdf,.doc,.docx,.txt,.md,.csv,.xls,.xlsx,.ppt,.pptx"
	/>

	<!-- Carte agent : visage + prénom (sur sa ligne, jamais coupé) + rôle + exemple de docs + bouton
	     « Ajouter » DÉDIÉ + la liste des fichiers de CET agent. -->
	{#snippet agentCard(a: AgentDoc)}
		{@const t = tpl(a.id)}
		{#if t}
			<div class="flex flex-col h-full rounded-2xl bg-white dark:bg-white/[0.03] ring-1 ring-inset ring-black/5 dark:ring-white/10 p-4">
				<!-- flex-1 : le header occupe tout l'espace dispo → les boutons se calent au même niveau,
				     que l'exemple tienne sur 1, 2 ou 3 lignes (cartes de hauteur égale via grid + h-full). -->
				<div class="flex items-start gap-3 flex-1">
					<img
						src={faceFromImage(t.image) ?? '/favicon.png'}
						alt={t.firstName}
						on:error={(e) => avatarImgFallback(e, t.image)}
						style="background: {avatarColor(avatarId(t.image) || t.firstName).gradient}"
						class="flex-none h-10 w-10 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15"
					/>
					<div class="min-w-0 flex-1">
						<div class="text-sm font-semibold text-gray-900 dark:text-white">{t.firstName}</div>
						<div class="text-[11px] text-gray-400 dark:text-gray-500">{$i18n.t(t.role)}</div>
						<p class="mt-1.5 text-[12.5px] leading-snug text-gray-500 dark:text-gray-400">
							<span class="text-gray-400 dark:text-gray-500">{$i18n.t('Ex :')}</span>
							{$i18n.t(a.example)}
						</p>
					</div>
				</div>

				<button
					type="button"
					on:click={() => openPickerFor(a.id)}
					class="mt-3 w-full inline-flex items-center justify-center gap-1.5 text-[13px] font-semibold px-4 py-2 rounded-xl bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-500/25 hover:bg-amber-100 dark:bg-amber-900/20 dark:text-amber-200 dark:hover:bg-amber-900/30 transition"
				>
					+ {$i18n.t('Ajouter un document')}
				</button>
				<p class="mt-1.5 text-center text-[11px] text-gray-400 dark:text-gray-500">
					{$i18n.t('PDF, Word, Excel, texte…')} · {$i18n.t('{{n}} Mo max', { n: MAX_FILE_MB })}
				</p>
				{#if noticeByAgent[a.id]}
					<p class="mt-1.5 text-center text-[11px] text-amber-700 dark:text-amber-300">
						{noticeByAgent[a.id]}
					</p>
				{/if}

				<!-- Fichiers déposés POUR cet agent -->
				{#if (docsByAgent[a.id] ?? []).length}
					<div class="mt-2 flex flex-col gap-1.5">
						{#each docsByAgent[a.id] as d (d.id)}
							<div class="flex items-center gap-2 rounded-lg bg-gray-50 dark:bg-white/[0.04] px-2.5 py-1.5">
								<span class="text-sm" aria-hidden="true">📎</span>
								<span class="min-w-0 flex-1">
									<span class="block text-[12.5px] text-gray-800 dark:text-gray-100 truncate">{d.name}</span>
									<span class="block text-[10.5px] text-gray-400">{humanSize(d.size)}</span>
								</span>
								{#if d.status === 'uploading'}
									<span class="inline-block h-3.5 w-3.5 rounded-full border-2 border-amber-500 border-t-transparent animate-spin"></span>
								{:else if d.status === 'done'}
									<span class="text-emerald-500 text-sm font-bold" title={$i18n.t('Ajouté')}>✓</span>
								{:else}
									<span class="text-[11px] text-red-500" title={$i18n.t('Échec de l’envoi')}>{$i18n.t('échec')}</span>
								{/if}
								<button
									type="button"
									on:click={() => removeDoc(a.id, d.id)}
									aria-label={$i18n.t('Retirer')}
									class="h-5 w-5 flex-none rounded-full flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200/60 dark:hover:bg-white/10 transition"
								>×</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	{/snippet}

	<!-- Les 7 agents ACTIFS -->
	<div class="mt-7 grid gap-2.5 sm:grid-cols-2">
		{#each PRIMARY_AGENTS as a (a.id)}{@render agentCard(a)}{/each}
	</div>

	<!-- Les 8 agents À ACTIVER : section séparée, avec la précision qu'ils ne sont pas encore actifs. -->
	<button
		type="button"
		on:click={() => (showAll = !showAll)}
		class="mt-4 w-full text-center text-[13px] font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 transition"
	>
		{showAll
			? $i18n.t('Masquer les autres agents')
			: $i18n.t('Voir les {{n}} autres agents (à activer)', { n: MORE_AGENTS.length })}
	</button>
	{#if showAll}
		<div class="mt-3 rounded-2xl border border-dashed border-gray-300 dark:border-white/15 p-3.5">
			<p class="mb-3 text-[12.5px] leading-relaxed text-gray-500 dark:text-gray-400">
				⚙️ {$i18n.t(
					'Ces agents ne sont pas encore actifs. Activez-les depuis vos Capacités pour qu’ils utilisent ces documents.'
				)}
			</p>
			<div class="grid gap-2.5 sm:grid-cols-2">
				{#each MORE_AGENTS as a (a.id)}{@render agentCard(a)}{/each}
			</div>
		</div>
	{/if}

	<!-- Navigation (le « Retour » et le « Plus tard » global vivent dans le header du parcours). -->
	<div class="mt-8 flex items-center justify-end">
		<button
			disabled={anyUploading || finishing}
			class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 disabled:opacity-60"
			on:click={finishDocuments}
		>
			{#if finishing}
				{$i18n.t('Enregistrement…')}
			{:else}
				{anyDone ? $i18n.t('Continuer') : $i18n.t('Continuer sans document')} →
			{/if}
		</button>
	</div>
</div>
