export type FactSourceType = 'site' | 'web' | 'dirigeant' | 'document' | 'integration';
export type FactStatus = 'confirme' | 'a_confirmer' | 'corrige' | 'non_recherche';

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
};

export type OperationalMap = {
	companyName: string;
	siteUrl: string;
	facts: EvidenceFact[];
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

export type OnboardingDraft = {
	version: 1;
	step: 'welcome' | 'site' | 'analysis' | 'interview' | 'review' | 'workflows' | 'done';
	siteUrl: string;
	map: OperationalMap;
	answers: InterviewAnswer[];
	questionIndex: number;
	workflows: WorkflowProposal[];
	selectedWorkflowId: string;
	pendingAnswer: string;
	updatedAt: string;
};
