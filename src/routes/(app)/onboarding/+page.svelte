<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { getActiveProvider } from '$lib/apis/providers';
	import DocumentsStep from '$lib/components/onboarding-agentos/DocumentsStep.svelte';
	import FinalProofStep from '$lib/components/onboarding-agentos/FinalProofStep.svelte';
	import FoundationSetupStep from '$lib/components/onboarding-agentos/FoundationSetupStep.svelte';
	import OnboardingShell from '$lib/components/onboarding-agentos/OnboardingShell.svelte';
	import WelcomeStep from '$lib/components/onboarding-agentos/WelcomeStep.svelte';
	import {
		crawlCompanySite,
		generateWorkflowProposals,
		initMemoryVault,
		saveManagedNote,
		searchCompanyWeb,
		synthesizeSiteFacts,
		synthesizeWebFacts
	} from '$lib/apis/onboarding-agentos';
	import {
		COMPANY_MAP_NOTE_ID,
		COMPANY_MAP_NOTE_TITLE,
		DONE_KEY,
		DRAFT_KEY,
		WORKFLOW_NOTE_ID,
		WORKFLOW_NOTE_TITLE,
		answerToFact,
		buildInterviewQuestions,
		buildMapMarkdown,
		buildWorkflowMarkdown,
		factsBySection,
		integrationSearchTerm,
		mergeFacts,
		provenanceLabel,
		SKIP_ONCE_KEY,
		statusLabel
	} from '$lib/onboarding-agentos/logic';
	import type {
		EvidenceFact,
		InterviewAnswer,
		InterviewQuestion,
		OnboardingDocument,
		OnboardingDraft,
		OperationalMap,
		WorkflowProposal
	} from '$lib/onboarding-agentos/types';

	type Step = OnboardingDraft['step'];

	let mounted = false;
	let alreadyDone = false;
	let step: Step = 'welcome';
	let siteUrl = '';
	let map: OperationalMap = { companyName: '', siteUrl: '', facts: [] };
	let answers: InterviewAnswer[] = [];
	let questionIndex = 0;
	let answerText = '';
	let foundationConfirmed = false;
	let selectedProviderId = '';
	let selectedModelId = '';
	let selectedWebProvider = '';
	let documents: OnboardingDocument[] = [];
	let knowledgeBaseId = '';
	let workflows: WorkflowProposal[] = [];
	let selectedWorkflowId = '';

	let model = '';
	let modelError = '';
	let analysisError = '';
	let analysisStage = 0;
	let analysisDetails = '';
	let analysisFailed = false;
	let reviewError = '';
	let savingMap = false;
	let workflowLoading = false;
	let workflowError = '';
	let finishing = false;
	let finishedWithWorkflow: WorkflowProposal | null = null;

	const ANALYSIS_STAGES = [
		'Cartographie du site',
		'Compréhension de l’activité',
		'Recherche de l’environnement extérieur',
		'Préparation de votre entretien'
	];

	$: questions = buildInterviewQuestions(map.facts);
	$: currentQuestion = questions[questionIndex] as InterviewQuestion | undefined;
	$: groupedFacts = factsBySection(map.facts);
	$: unconfirmedCount = map.facts.filter((fact) => fact.status === 'a_confirmer').length;
	$: selectedWorkflow = workflows.find((workflow) => workflow.id === selectedWorkflowId) ?? null;
	$: integrationNames = Array.from(new Set(workflows.flatMap((workflow) => workflow.integrations)));
	const evidenceLabel = (id: string) =>
		map.facts.find((fact) => fact.id === id)?.label ?? 'Élément de la Carte';

	const persistDraft = (
		currentStep: Step,
		currentSite: string,
		currentMap: OperationalMap,
		currentAnswers: InterviewAnswer[],
		currentQuestionIndex: number,
		currentFoundationConfirmed: boolean,
		currentSelectedProviderId: string,
		currentSelectedModelId: string,
		currentSelectedWebProvider: string,
		currentDocuments: OnboardingDocument[],
		currentKnowledgeBaseId: string,
		currentWorkflows: WorkflowProposal[],
		currentSelectedWorkflowId: string,
		currentPendingAnswer: string
	) => {
		if (!mounted || currentStep === 'done') return;
		const draft: OnboardingDraft = {
			version: 1,
			step: currentStep,
			siteUrl: currentSite,
			map: currentMap,
			answers: currentAnswers,
			questionIndex: currentQuestionIndex,
			foundationConfirmed: currentFoundationConfirmed,
			selectedProviderId: currentSelectedProviderId,
			selectedModelId: currentSelectedModelId,
			selectedWebProvider: currentSelectedWebProvider,
			documents: currentDocuments,
			knowledgeBaseId: currentKnowledgeBaseId,
			workflows: currentWorkflows,
			selectedWorkflowId: currentSelectedWorkflowId,
			pendingAnswer: currentPendingAnswer,
			updatedAt: new Date().toISOString()
		};
		try {
			localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
		} catch {
			// Le parcours reste utilisable même si le stockage local est indisponible.
		}
	};

	$: persistDraft(
		step,
		siteUrl,
		map,
		answers,
		questionIndex,
		foundationConfirmed,
		selectedProviderId,
		selectedModelId,
		selectedWebProvider,
		documents,
		knowledgeBaseId,
		workflows,
		selectedWorkflowId,
		answerText
	);

	const readDraft = (): OnboardingDraft | null => {
		try {
			const raw = localStorage.getItem(DRAFT_KEY);
			if (!raw) return null;
			const parsed = JSON.parse(raw);
			return parsed?.version === 1 ? (parsed as OnboardingDraft) : null;
		} catch {
			return null;
		}
	};

	const refreshModel = async () => {
		modelError = '';
		try {
			const active = await getActiveProvider(localStorage.token);
			if (!active?.provider_id || active.provider_id === 'auto' || !active?.model_id) {
				model = '';
			} else if (
				foundationConfirmed &&
				selectedProviderId &&
				selectedModelId &&
				(active.provider_id !== selectedProviderId || active.model_id !== selectedModelId)
			) {
				model = '';
				modelError =
					'Le cerveau IA actif a changé depuis votre confirmation. Revenez à la configuration pour le confirmer.';
			} else {
				model = active.model_id;
				selectedProviderId = active.provider_id;
				selectedModelId = active.model_id;
			}
		} catch {
			model = '';
		}
		if (!model && !modelError) {
			modelError =
				'Choisissez explicitement un provider et son modèle avant de confier votre entreprise à LunarIA.';
		}
		return Boolean(model);
	};

	onMount(async () => {
		alreadyDone = localStorage.getItem(DONE_KEY) === '1';
		const draft = readDraft();
		if (draft) {
			step = draft.step === 'analysis' ? 'site' : draft.step;
			siteUrl = draft.siteUrl ?? '';
			map = draft.map ?? map;
			answers = draft.answers ?? [];
			questionIndex = Math.min(
				draft.questionIndex ?? 0,
				buildInterviewQuestions(map.facts).length - 1
			);
			foundationConfirmed = draft.foundationConfirmed ?? false;
			selectedProviderId = draft.selectedProviderId ?? '';
			selectedModelId = draft.selectedModelId ?? '';
			selectedWebProvider = draft.selectedWebProvider ?? '';
			if (!foundationConfirmed && step !== 'welcome') step = 'foundation';
			documents = draft.documents ?? [];
			knowledgeBaseId = draft.knowledgeBaseId ?? '';
			workflows = draft.workflows ?? [];
			selectedWorkflowId = draft.selectedWorkflowId ?? '';
			answerText = draft.pendingAnswer ?? '';
		}
		const brainIsReady = await refreshModel();
		if (!brainIsReady && step !== 'welcome') {
			foundationConfirmed = false;
			step = 'foundation';
		}
		mounted = true;
	});

	const normaliseUrl = (value: string) => {
		const candidate = value.trim();
		if (!candidate) return '';
		return /^https?:\/\//i.test(candidate) ? candidate : `https://${candidate}`;
	};

	const begin = () => {
		step = 'foundation';
	};

	const completeFoundation = (
		event: CustomEvent<{ providerId: string; modelId: string; webProvider: string }>
	) => {
		foundationConfirmed = true;
		selectedProviderId = event.detail.providerId;
		selectedModelId = event.detail.modelId;
		selectedWebProvider = event.detail.webProvider;
		model = event.detail.modelId;
		modelError = '';
		step = 'site';
	};

	const startWithoutSite = () => {
		siteUrl = '';
		map = { companyName: '', siteUrl: '', facts: [] };
		answers = [];
		questionIndex = 0;
		answerText = '';
		step = 'interview';
	};

	const analyze = async () => {
		analysisError = '';
		analysisFailed = false;
		const url = normaliseUrl(siteUrl);
		if (!url) {
			analysisError = "Indiquez l'adresse du site ou choisissez « Je n'ai pas de site ».";
			return;
		}
		try {
			new URL(url);
		} catch {
			analysisError = "Cette adresse de site n'est pas valide.";
			return;
		}
		if (!(await refreshModel())) return;

		siteUrl = url;
		step = 'analysis';
		analysisStage = 0;
		analysisDetails = 'LunarIA découvre les pages réellement utiles.';
		let companyName = '';
		let siteFacts: EvidenceFact[] = [];

		try {
			const crawl = await crawlCompanySite(localStorage.token, url);
			if (crawl.status !== 'reussi' || !crawl.markdown.trim()) {
				throw new Error(
					crawl.message ||
						"Le site n'a pas été lu complètement. L'analyse est arrêtée pour éviter une Carte incomplète."
				);
			}

			analysisStage = 1;
			analysisDetails = `${crawl.pages?.length ?? 1} page(s) utile(s) lue(s). Le cerveau IA structure les informations.`;
			const synthesis = await synthesizeSiteFacts(
				localStorage.token,
				selectedProviderId,
				selectedModelId,
				crawl
			);
			companyName = synthesis.companyName;
			siteFacts = synthesis.facts;
			if (!companyName || !siteFacts.length) {
				throw new Error(
					'Le cerveau IA n’a pas produit assez d’éléments vérifiables à partir du site.'
				);
			}

			map = {
				companyName,
				siteUrl: url,
				facts: mergeFacts(map.facts, siteFacts)
			};

			analysisStage = 2;
			analysisDetails = `${selectedWebProvider} cherche les clients, concurrents, avis et signaux récents.`;
			const sectorHint =
				siteFacts.find((fact) => fact.label.toLowerCase().includes('secteur'))?.value ?? '';
			const items = await searchCompanyWeb(
				localStorage.token,
				selectedWebProvider,
				companyName,
				url,
				sectorHint
			);
			const webFacts = await synthesizeWebFacts(
				localStorage.token,
				selectedProviderId,
				selectedModelId,
				items
			);
			if (!webFacts.length) {
				throw new Error('La recherche Web n’a produit aucun fait extérieur suffisamment fiable.');
			}
			map = { ...map, facts: mergeFacts(map.facts, webFacts) };
		} catch (error) {
			analysisError =
				error instanceof Error ? error.message : "L'analyse de l'entreprise a échoué.";
			analysisDetails = 'Analyse interrompue : aucune donnée incomplète ne sera validée.';
			analysisFailed = true;
			return;
		}

		analysisStage = 3;
		analysisDetails = 'Les questions sont adaptées à ce qui manque ou reste à confirmer.';
		questionIndex = 0;
		answerText = '';
		step = 'interview';
	};

	const existingAnswer = (questionId: string) =>
		answers.find((answer) => answer.questionId === questionId);

	const loadQuestionAnswer = (index: number) => {
		const question = questions[index];
		answerText = question ? (existingAnswer(question.id)?.value ?? '') : '';
	};

	const storeAnswer = (question: InterviewQuestion, skipped = false) => {
		const answer: InterviewAnswer = {
			questionId: question.id,
			value: skipped ? '' : answerText.trim(),
			skipped
		};
		answers = [...answers.filter((item) => item.questionId !== question.id), answer];
		const fact = answerToFact(question, answer);
		if (fact) {
			map = { ...map, facts: mergeFacts(map.facts, [fact]) };
			if (question.id === 'nom-entreprise') map = { ...map, companyName: fact.value };
		}
	};

	const nextQuestion = () => {
		if (!currentQuestion) return;
		if (!answerText.trim() && !currentQuestion.optional) {
			toast.error('Cette réponse est nécessaire pour construire votre AgentOS.');
			return;
		}
		storeAnswer(currentQuestion);
		if (questionIndex >= questions.length - 1) {
			answerText = '';
			step = 'documents';
			return;
		}
		questionIndex += 1;
		loadQuestionAnswer(questionIndex);
	};

	const skipQuestion = () => {
		if (!currentQuestion?.optional) return;
		storeAnswer(currentQuestion, true);
		if (questionIndex >= questions.length - 1) {
			answerText = '';
			step = 'documents';
			return;
		}
		questionIndex += 1;
		loadQuestionAnswer(questionIndex);
	};

	const previousQuestion = () => {
		if (questionIndex === 0) {
			step = siteUrl ? 'site' : 'welcome';
			return;
		}
		questionIndex -= 1;
		loadQuestionAnswer(questionIndex);
	};

	const updateDocuments = (
		event: CustomEvent<{ documents: OnboardingDocument[]; knowledgeBaseId: string }>
	) => {
		documents = event.detail.documents;
		knowledgeBaseId = event.detail.knowledgeBaseId;
		const documentFacts: EvidenceFact[] = documents
			.filter((document) => document.status === 'done')
			.map((document) => ({
				id: `document-${document.id}`,
				section: 'Outils et sources de vérité',
				label: 'Document fourni',
				value: document.name,
				sourceType: 'document',
				sourceTitle: document.name,
				observedAt: new Date().toISOString().slice(0, 10),
				status: 'confirme',
				confidence: 1
			}));
		map = { ...map, facts: mergeFacts(map.facts, documentFacts) };
	};

	const updateFact = (id: string, value: string) => {
		map = {
			...map,
			facts: map.facts.map((fact) =>
				fact.id === id ? { ...fact, value, status: 'corrige', confidence: 1 } : fact
			)
		};
	};

	const confirmFact = (id: string) => {
		map = {
			...map,
			facts: map.facts.map((fact) =>
				fact.id === id && fact.status === 'a_confirmer'
					? { ...fact, status: 'confirme', confidence: Math.max(fact.confidence, 0.8) }
					: fact
			)
		};
	};

	const removeFact = (id: string) => {
		map = { ...map, facts: map.facts.filter((fact) => fact.id !== id) };
	};

	const confirmAllRemaining = () => {
		map = {
			...map,
			facts: map.facts.map((fact) =>
				fact.status === 'a_confirmer'
					? { ...fact, status: 'confirme', confidence: Math.max(fact.confidence, 0.8) }
					: fact
			)
		};
	};

	const saveMapAndGenerate = async () => {
		reviewError = '';
		if (unconfirmedCount > 0) {
			reviewError = `Il reste ${unconfirmedCount} élément(s) à confirmer, corriger ou retirer.`;
			return;
		}
		if (!map.companyName.trim()) {
			reviewError = "Le nom de l'entreprise manque encore.";
			return;
		}
		savingMap = true;
		const validatedMap = { ...map, validatedAt: new Date().toISOString().slice(0, 10) };
		try {
			await initMemoryVault(localStorage.token);
			await saveManagedNote(
				localStorage.token,
				COMPANY_MAP_NOTE_ID,
				COMPANY_MAP_NOTE_TITLE,
				buildMapMarkdown(validatedMap)
			);
			map = validatedMap;
		} catch (error) {
			reviewError =
				error instanceof Error ? error.message : "La Carte n'a pas pu être enregistrée.";
			savingMap = false;
			return;
		}
		savingMap = false;
		step = 'workflows';
		await designWorkflows();
	};

	const designWorkflows = async () => {
		workflowError = '';
		workflowLoading = true;
		try {
			if (!(await refreshModel())) throw new Error(modelError);
			workflows = await generateWorkflowProposals(
				localStorage.token,
				selectedProviderId,
				selectedModelId,
				map
			);
			if (!workflows.length) {
				throw new Error(
					"LunarIA n'a pas encore assez d'éléments fiables pour proposer un workflow précis."
				);
			}
		} catch (error) {
			workflowError =
				error instanceof Error ? error.message : 'Les workflows n’ont pas pu être préparés.';
		} finally {
			workflowLoading = false;
		}
	};

	const finish = async (postpone = false) => {
		if (!postpone && !selectedWorkflow) {
			toast.error('Choisissez un workflow ou sélectionnez « Décider plus tard ».');
			return;
		}
		finishing = true;
		try {
			if (selectedWorkflow) {
				await saveManagedNote(
					localStorage.token,
					WORKFLOW_NOTE_ID,
					WORKFLOW_NOTE_TITLE,
					buildWorkflowMarkdown(selectedWorkflow)
				);
				finishedWithWorkflow = selectedWorkflow;
			}
			localStorage.setItem(DONE_KEY, '1');
			localStorage.removeItem(DRAFT_KEY);
			step = 'done';
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Le choix n'a pas pu être enregistré.");
		} finally {
			finishing = false;
		}
	};

	const restart = () => {
		if (!confirm('Recommencer l’onboarding ? Le brouillon actuel sera remplacé.')) return;
		localStorage.removeItem(DRAFT_KEY);
		step = 'welcome';
		siteUrl = '';
		map = { companyName: '', siteUrl: '', facts: [] };
		answers = [];
		questionIndex = 0;
		answerText = '';
		foundationConfirmed = false;
		selectedProviderId = '';
		selectedModelId = '';
		selectedWebProvider = '';
		documents = [];
		knowledgeBaseId = '';
		workflows = [];
		selectedWorkflowId = '';
		finishedWithWorkflow = null;
	};

	const leaveForNow = () => {
		sessionStorage.setItem(SKIP_ONCE_KEY, '1');
		goto('/');
	};
</script>

<svelte:head>
	<title>Onboarding AgentOS · LunarIA</title>
</svelte:head>

<OnboardingShell
	{step}
	canRestart={step !== 'welcome' && step !== 'done'}
	on:restart={restart}
	on:leave={leaveForNow}
>
	{#if step === 'welcome'}
		<WelcomeStep {alreadyDone} on:begin={begin} on:memory={() => goto('/memoire')} />
	{:else if step === 'foundation' || step === 'model'}
		<FoundationSetupStep on:complete={completeFoundation} />
	{:else if step === 'site'}
		<section class="m-auto w-full max-w-3xl py-10">
			<div class="text-center">
				<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
					Étape 2 · Découverte
				</div>
				<h1 class="mt-4 text-3xl font-medium tracking-[-0.03em] md:text-5xl">
					Commençons par votre entreprise.
				</h1>
				<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
					LunarIA lira votre site puis complétera avec des sources extérieures. Elle ne vous
					redemandera pas ce qu’elle peut déjà comprendre.
				</p>
			</div>

			<div
				class="mt-9 rounded-[2rem] border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616] md:p-7"
			>
				<label for="company-site" class="text-sm font-medium">Site internet de l’entreprise</label>
				<div class="mt-3 flex flex-col gap-3 sm:flex-row">
					<input
						id="company-site"
						bind:value={siteUrl}
						placeholder="www.votreentreprise.fr"
						class="min-w-0 flex-1 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3.5 text-sm outline-none transition focus:border-[#6b62f2] dark:border-gray-800 dark:bg-[#101010]"
						on:keydown={(event) => event.key === 'Enter' && analyze()}
					/>
					<button
						class="rounded-2xl bg-[#6b62f2] px-6 py-3.5 text-sm font-medium text-white disabled:opacity-50"
						disabled={!siteUrl.trim()}
						on:click={analyze}>Analyser mon entreprise</button
					>
				</div>
				{#if modelError}
					<div
						class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
					>
						{modelError}
						<a href="/hermes?tab=providers" class="ml-1 font-medium underline"
							>Connecter un modèle IA</a
						>
					</div>
				{/if}
				{#if analysisError}
					<div
						class="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200"
					>
						{analysisError}
					</div>
				{/if}
				<div
					class="mt-6 flex items-center justify-between border-t border-gray-100 pt-5 dark:border-gray-800"
				>
					<button
						class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white"
						on:click={() => (step = 'welcome')}>Retour</button
					>
					<button
						class="text-sm font-medium text-[#5b52dd] dark:text-[#aaa4ff]"
						on:click={startWithoutSite}>Je n’ai pas de site internet</button
					>
				</div>
			</div>
		</section>
	{:else if step === 'analysis'}
		<section class="m-auto w-full max-w-3xl py-10 text-center">
			<div
				class="mx-auto flex size-20 items-center justify-center rounded-[1.75rem] bg-[#6b62f2]/10"
			>
				{#if analysisFailed}
					<span class="text-3xl text-red-500">!</span>
				{:else}
					<div
						class="size-8 animate-spin rounded-full border-[3px] border-[#6b62f2]/20 border-t-[#6b62f2]"
					></div>
				{/if}
			</div>
			<div class="mt-7 text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
				{analysisFailed ? 'Analyse interrompue' : 'Analyse en cours'}
			</div>
			<h1 class="mt-3 text-3xl font-medium tracking-[-0.03em]">
				LunarIA apprend votre entreprise.
			</h1>
			<p class="mt-3 text-sm text-gray-500 dark:text-gray-400">{analysisDetails}</p>
			{#if analysisFailed}
				<div
					class="mx-auto mt-6 max-w-xl rounded-2xl border border-red-200 bg-red-50 p-4 text-left text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200"
				>
					{analysisError}
				</div>
				<div class="mt-5 flex flex-wrap justify-center gap-3">
					<button
						class="rounded-full px-5 py-2.5 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={() => (step = 'site')}>Revenir au site</button
					>
					<button
						class="rounded-full bg-[#6b62f2] px-6 py-2.5 text-sm font-medium text-white"
						on:click={analyze}>Réessayer l’analyse complète</button
					>
				</div>
			{/if}
			<div
				class="mx-auto mt-9 max-w-xl rounded-[2rem] border border-black/6 bg-white p-5 text-left dark:border-white/8 dark:bg-[#161616]"
			>
				{#each ANALYSIS_STAGES as label, index}
					<div
						class="flex items-center gap-3 py-3 {index < ANALYSIS_STAGES.length - 1
							? 'border-b border-gray-100 dark:border-gray-800'
							: ''}"
					>
						<div
							class="flex size-7 items-center justify-center rounded-full {index < analysisStage
								? 'bg-emerald-500 text-white'
								: index === analysisStage
									? 'bg-[#6b62f2] text-white'
									: 'bg-gray-100 text-gray-400 dark:bg-gray-800'}"
						>
							{#if index < analysisStage}
								<svg
									viewBox="0 0 20 20"
									class="size-4"
									fill="none"
									stroke="currentColor"
									stroke-width="2"><path d="m5 10 3 3 7-7" /></svg
								>
							{:else}
								{index + 1}
							{/if}
						</div>
						<div class="text-sm {index <= analysisStage ? 'font-medium' : 'text-gray-400'}">
							{label}
						</div>
					</div>
				{/each}
			</div>
		</section>
	{:else if step === 'interview' && currentQuestion}
		<section class="m-auto w-full max-w-3xl py-8">
			<div class="mb-6 flex items-center justify-between">
				<div>
					<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
						Étape 3 · Entretien
					</div>
					<div class="mt-2 text-xs text-gray-500">
						Question {questionIndex + 1} sur {questions.length}
					</div>
				</div>
				<div class="h-1.5 w-36 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
					<div
						class="h-full rounded-full bg-[#6b62f2] transition-all"
						style={`width:${((questionIndex + 1) / questions.length) * 100}%`}
					></div>
				</div>
			</div>

			<div
				class="rounded-[2rem] border border-black/6 bg-white p-6 dark:border-white/8 dark:bg-[#161616] md:p-9"
			>
				<div class="text-xs font-medium text-gray-400">{currentQuestion.section}</div>
				<h1 class="mt-3 text-2xl font-medium leading-tight tracking-[-0.025em] md:text-4xl">
					{currentQuestion.prompt}
				</h1>
				<p class="mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
					{currentQuestion.helper}
				</p>
				<textarea
					bind:value={answerText}
					rows="6"
					placeholder={currentQuestion.placeholder}
					class="mt-7 w-full resize-none rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm leading-6 outline-none transition focus:border-[#6b62f2] dark:border-gray-800 dark:bg-[#101010]"
				></textarea>
				<div class="mt-6 flex flex-wrap items-center justify-between gap-3">
					<button
						class="rounded-full px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={previousQuestion}>Retour</button
					>
					<div class="flex items-center gap-2">
						{#if currentQuestion.optional}
							<button
								class="rounded-full px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
								on:click={skipQuestion}>Je ne sais pas / Passer</button
							>
						{/if}
						<button
							class="rounded-full bg-[#6b62f2] px-6 py-2.5 text-sm font-medium text-white"
							on:click={nextQuestion}
						>
							{questionIndex === questions.length - 1 ? 'Ajouter mes sources' : 'Continuer'}
						</button>
					</div>
				</div>
			</div>
		</section>
	{:else if step === 'documents'}
		<DocumentsStep
			token={localStorage.token}
			companyName={map.companyName}
			{documents}
			{knowledgeBaseId}
			on:change={updateDocuments}
			on:back={() => {
				step = 'interview';
				questionIndex = questions.length - 1;
				loadQuestionAnswer(questionIndex);
			}}
			on:done={() => (step = 'review')}
		/>
	{:else if step === 'review'}
		<section class="w-full py-8">
			<div class="mx-auto max-w-4xl text-center">
				<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
					Étape 5 · Porte humaine
				</div>
				<h1 class="mt-3 text-3xl font-medium tracking-[-0.03em] md:text-5xl">
					Voici comment LunarIA comprend votre entreprise.
				</h1>
				<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
					Confirmez, corrigez ou retirez chaque information publique. Vos réponses directes sont
					déjà confirmées.
				</p>
			</div>

			<div class="mx-auto mt-8 max-w-5xl space-y-5">
				{#each groupedFacts as group}
					<div
						class="rounded-[2rem] border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616] md:p-7"
					>
						<div class="mb-4 flex items-center justify-between gap-3">
							<h2 class="text-lg font-medium">{group.section}</h2>
							<div class="text-xs text-gray-400">{group.facts.length} élément(s)</div>
						</div>
						<div class="space-y-3">
							{#each group.facts as fact}
								<div
									class="rounded-2xl border border-gray-100 bg-gray-50/60 p-4 dark:border-gray-800 dark:bg-[#101010]"
								>
									<div class="flex flex-wrap items-start justify-between gap-2">
										<div>
											<div class="text-sm font-medium">{fact.label}</div>
											<div class="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
												<span
													class="rounded-full bg-gray-200/70 px-2 py-0.5 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
													>{provenanceLabel(fact)}</span
												>
												<span
													class="rounded-full px-2 py-0.5 {fact.status === 'confirme' ||
													fact.status === 'corrige'
														? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
														: fact.status === 'non_recherche'
															? 'bg-gray-200 text-gray-500 dark:bg-gray-800'
															: 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300'}"
													>{statusLabel(fact)}</span
												>
											</div>
										</div>
										<button
											class="text-xs text-red-500 hover:underline"
											on:click={() => removeFact(fact.id)}>Retirer</button
										>
									</div>
									<textarea
										value={fact.value}
										rows={Math.min(6, Math.max(2, fact.value.split('\n').length))}
										class="mt-3 w-full resize-y rounded-xl border border-transparent bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-[#6b62f2] dark:bg-[#161616]"
										on:input={(event) => updateFact(fact.id, event.currentTarget.value)}
									></textarea>
									<div class="mt-2 flex flex-wrap items-center justify-between gap-2">
										<div class="min-w-0 truncate text-[11px] text-gray-400">
											{#if fact.sourceUrl}
												<a
													href={fact.sourceUrl}
													target="_blank"
													rel="noreferrer"
													class="hover:text-[#6b62f2] hover:underline"
													>{fact.sourceTitle || fact.sourceUrl}</a
												>
												<span> · </span>
											{/if}
											Vérifié le {fact.observedAt}
										</div>
										{#if fact.status === 'a_confirmer'}
											<button
												class="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white"
												on:click={() => confirmFact(fact.id)}>Confirmer</button
											>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>

			<div
				class="sticky bottom-4 mx-auto mt-7 flex max-w-5xl flex-col gap-3 rounded-2xl border border-black/8 bg-white/95 p-4 shadow-lg backdrop-blur dark:border-white/10 dark:bg-[#161616]/95 sm:flex-row sm:items-center sm:justify-between"
			>
				<div>
					<div class="text-sm font-medium">
						{unconfirmedCount === 0
							? 'Votre Carte est prête à être enregistrée.'
							: `${unconfirmedCount} élément(s) restent à relire.`}
					</div>
					{#if reviewError}<div class="mt-1 text-xs text-red-500">{reviewError}</div>{/if}
				</div>
				<div class="flex flex-wrap gap-2">
					<button
						class="rounded-full px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={() => {
							step = 'interview';
							questionIndex = questions.length - 1;
							loadQuestionAnswer(questionIndex);
						}}>Retour à l’entretien</button
					>
					{#if unconfirmedCount > 0}
						<button
							class="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium dark:border-gray-700"
							on:click={confirmAllRemaining}>Tout confirmer après relecture</button
						>
					{/if}
					<button
						class="rounded-full bg-[#6b62f2] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
						disabled={savingMap}
						on:click={saveMapAndGenerate}
						>{savingMap ? 'Enregistrement…' : 'Valider ma Carte'}</button
					>
				</div>
			</div>
		</section>
	{:else if step === 'workflows'}
		<section class="w-full py-8">
			<div class="mx-auto max-w-4xl text-center">
				<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
					Étape 6 · Votre AgentOS
				</div>
				<h1 class="mt-3 text-3xl font-medium tracking-[-0.03em] md:text-5xl">
					Les premières boucles utiles à votre entreprise.
				</h1>
				<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
					Chaque recommandation part de votre Carte, précise le résultat attendu et place votre
					validation au bon endroit.
				</p>
			</div>

			{#if workflowLoading}
				<div
					class="mx-auto mt-12 flex max-w-xl flex-col items-center rounded-[2rem] border border-black/6 bg-white p-10 text-center dark:border-white/8 dark:bg-[#161616]"
				>
					<div
						class="size-8 animate-spin rounded-full border-[3px] border-[#6b62f2]/20 border-t-[#6b62f2]"
					></div>
					<div class="mt-5 text-sm font-medium">
						LunarIA relie vos douleurs, vos outils et vos garde-fous…
					</div>
				</div>
			{:else if workflowError}
				<div
					class="mx-auto mt-10 max-w-xl rounded-[2rem] border border-red-200 bg-red-50 p-6 text-center dark:border-red-900/50 dark:bg-red-950/20"
				>
					<div class="text-sm text-red-700 dark:text-red-200">{workflowError}</div>
					<button
						class="mt-4 rounded-full bg-[#6b62f2] px-5 py-2.5 text-sm font-medium text-white"
						on:click={designWorkflows}>Réessayer</button
					>
				</div>
			{:else}
				<div class="mx-auto mt-9 grid max-w-6xl gap-5 lg:grid-cols-3">
					{#each workflows as workflow, index}
						<div
							class="flex h-full flex-col rounded-[2rem] border p-5 text-left transition md:p-6 {selectedWorkflowId ===
							workflow.id
								? 'border-[#6b62f2] bg-[#6b62f2]/5 ring-2 ring-[#6b62f2]/15'
								: 'border-black/6 bg-white hover:border-[#6b62f2]/35 dark:border-white/8 dark:bg-[#161616]'}"
						>
							<div class="flex items-center justify-between">
								<div
									class="flex size-9 items-center justify-center rounded-xl bg-[#6b62f2]/10 text-xs font-semibold text-[#6b62f2]"
								>
									0{index + 1}
								</div>
								<div class="text-xs text-gray-400">
									Confiance {Math.round(workflow.confidence * 100)} %
								</div>
							</div>
							<h2 class="mt-5 text-xl font-medium tracking-[-0.02em]">{workflow.title}</h2>
							<p class="mt-3 text-sm leading-6 text-gray-500 dark:text-gray-400">
								{workflow.problem}
							</p>
							<div
								class="mt-4 rounded-2xl bg-emerald-50 p-3 text-xs leading-5 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"
							>
								<span class="font-medium">Impact attendu :</span>
								{workflow.impact}
							</div>
							<div class="mt-5 space-y-3 text-xs">
								<div>
									<span class="text-gray-400">Déclencheur</span>
									<div class="mt-1 leading-5">{workflow.trigger}</div>
								</div>
								<div>
									<span class="text-gray-400">Résultat mesuré</span>
									<div class="mt-1 leading-5">{workflow.metric}</div>
								</div>
								<div>
									<span class="text-gray-400">Porte humaine</span>
									<div class="mt-1 leading-5">{workflow.humanGate}</div>
								</div>
								<div>
									<span class="text-gray-400">Responsable · première échéance</span>
									<div class="mt-1 leading-5">{workflow.owner} · {workflow.deadline}</div>
								</div>
							</div>
							<div class="mt-5 border-t border-gray-100 pt-4 dark:border-gray-800">
								<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400">
									Boucle
								</div>
								<ol class="mt-2 space-y-1.5 text-xs leading-5 text-gray-600 dark:text-gray-300">
									{#each workflow.steps as loopStep, stepIndex}
										<li>{stepIndex + 1}. {loopStep}</li>
									{/each}
								</ol>
							</div>
							<div class="mt-5 grid gap-3 text-xs">
								<div class="rounded-2xl bg-gray-50 p-3 dark:bg-[#101010]">
									<div class="font-medium">Données nécessaires</div>
									<ul class="mt-2 space-y-1 text-gray-500 dark:text-gray-400">
										{#each workflow.dataNeeded as item}<li>• {item}</li>{/each}
									</ul>
								</div>
								<div class="rounded-2xl bg-[#6b62f2]/5 p-3">
									<div class="font-medium">LunarIA peut préparer seule</div>
									<ul class="mt-2 space-y-1 text-gray-500 dark:text-gray-400">
										{#each workflow.autonomousActions as item}<li>• {item}</li>{/each}
									</ul>
								</div>
								<div
									class="rounded-2xl bg-red-50 p-3 text-red-800 dark:bg-red-950/25 dark:text-red-200"
								>
									<div class="font-medium">Interdictions</div>
									<ul class="mt-2 space-y-1">
										{#each workflow.forbidden as item}<li>• {item}</li>{/each}
									</ul>
								</div>
							</div>
							{#if workflow.evidenceFactIds.length}
								<div class="mt-5 text-[11px] leading-5 text-gray-400">
									Justifié par : {workflow.evidenceFactIds.map(evidenceLabel).join(' · ')}
								</div>
							{/if}
							{#if workflow.integrations.length}
								<div class="mt-5 flex flex-wrap gap-1.5">
									{#each workflow.integrations as integration}
										<a
											href={`/hermes?tab=integrations&search=${encodeURIComponent(integrationSearchTerm(integration))}`}
											on:click|stopPropagation
											class="rounded-full bg-gray-100 px-2.5 py-1 text-[11px] text-gray-600 hover:text-[#6b62f2] dark:bg-gray-800 dark:text-gray-300"
											>{integration}</a
										>
									{/each}
								</div>
							{/if}
							<div class="mt-auto pt-6">
								<button
									type="button"
									class="flex items-center gap-2 text-sm font-medium {selectedWorkflowId ===
									workflow.id
										? 'text-[#6b62f2]'
										: 'text-gray-500'}"
									on:click={() => (selectedWorkflowId = workflow.id)}
								>
									<span
										class="flex size-5 items-center justify-center rounded-full border {selectedWorkflowId ===
										workflow.id
											? 'border-[#6b62f2] bg-[#6b62f2] text-white'
											: 'border-gray-300 dark:border-gray-700'}"
									>
										{#if selectedWorkflowId === workflow.id}<span>✓</span>{/if}
									</span>
									Choisir ce workflow
								</button>
							</div>
						</div>
					{/each}
				</div>

				<div
					class="mx-auto mt-8 flex max-w-4xl flex-col items-center justify-between gap-3 sm:flex-row"
				>
					<button
						class="rounded-full px-5 py-2.5 text-sm text-gray-500 hover:bg-black/5 dark:hover:bg-white/5"
						on:click={() => (step = 'review')}>Retour à ma Carte</button
					>
					<div class="flex flex-wrap items-center justify-center gap-2">
						<button
							class="rounded-full px-5 py-2.5 text-sm text-gray-500 hover:bg-black/5 dark:hover:bg-white/5"
							disabled={finishing}
							on:click={() => finish(true)}>Décider plus tard</button
						>
						<button
							class="rounded-full bg-[#6b62f2] px-6 py-3 text-sm font-medium text-white disabled:opacity-50"
							disabled={!selectedWorkflow || finishing}
							on:click={() => finish(false)}
							>{finishing ? 'Enregistrement…' : 'Choisir et terminer'}</button
						>
					</div>
				</div>
			{/if}
		</section>
	{:else if step === 'done'}
		<FinalProofStep
			companyName={map.companyName}
			facts={map.facts}
			{documents}
			workflow={finishedWithWorkflow}
			{integrationNames}
			on:enter={() => goto('/')}
		/>
	{/if}
</OnboardingShell>
