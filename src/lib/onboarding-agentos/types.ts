export type FactSourceType = 'site' | 'web' | 'dirigeant' | 'document' | 'integration';
export type FactStatus = 'confirme' | 'a_confirmer' | 'corrige' | 'non_recherche';
export type BusinessOutcomeId =
	| 'revenus'
	| 'clients'
	| 'efficacite'
	| 'qualite'
	| 'risques'
	| 'connaissance'
	| 'personnalise';

export type BusinessGoal = {
	id: string;
	outcomeId: BusinessOutcomeId;
	label: string;
	detail?: string;
};

export type FactUtility = {
	outcomeIds: BusinessOutcomeId[];
	purpose: string;
	decision: string;
	workflowHint: string;
	metricHint: string;
	priority: number;
};

export type EvidenceFact = {
	id: string;
	section: string;
	label: string;
	value: string;
	sourceType: FactSourceType;
	sourceUrl?: string;
	sourceTitle?: string;
	observedAt: string;
	status: FactStatus;
	confidence: number;
	utility?: FactUtility;
};

export type OperationalMap = {
	companyName: string;
	siteUrl: string;
	facts: EvidenceFact[];
	goals?: BusinessGoal[];
	validatedAt?: string;
};

export type InterviewQuestion = {
	id: string;
	section: string;
	label: string;
	prompt: string;
	helper: string;
	placeholder: string;
	optional: boolean;
};

export type InterviewAnswer = {
	questionId: string;
	value: string;
	skipped?: boolean;
};

export type WorkflowProposal = {
	id: string;
	title: string;
	problem: string;
	impact: string;
	trigger: string;
	steps: string[];
	dataNeeded: string[];
	integrations: string[];
	autonomousActions: string[];
	owner: string;
	humanGate: string;
	forbidden: string[];
	metric: string;
	deadline: string;
	confidence: number;
	evidenceFactIds: string[];
};

export type ExternalSearchItem = {
	title: string;
	link: string;
	snippet: string;
	publishedDate?: string | null;
};

export type OnboardingDocument = {
	id: string;
	name: string;
	size: number;
	status: 'uploading' | 'done' | 'error';
	message?: string;
};

export type OnboardingDraft = {
	version: 1;
	step:
		| 'welcome'
		| 'foundation'
		| 'model'
		| 'goals'
		| 'site'
		| 'analysis'
		| 'understanding'
		| 'interview'
		| 'documents'
		| 'review'
		| 'workflows'
		| 'done';
	siteUrl: string;
	map: OperationalMap;
	answers: InterviewAnswer[];
	questionIndex: number;
	foundationConfirmed?: boolean;
	selectedProviderId?: string;
	selectedModelId?: string;
	selectedWebProvider?: string;
	pagesRead?: number;
	externalSourcesRetained?: number;
	documents?: OnboardingDocument[];
	knowledgeBaseId?: string;
	workflows: WorkflowProposal[];
	selectedWorkflowId: string;
	pendingAnswer: string;
	updatedAt: string;
};
