import { WEBUI_API_BASE_URL } from '$lib/constants';

// Helper interne : un appel JSON authentifié vers /api/v1/kanban
const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/kanban${path}`, {
		method,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export type KanbanBoard = {
	slug: string;
	name: string;
	description: string;
	icon: string;
	color: string;
	is_current: boolean;
	archived: boolean;
	total: number;
	counts: Record<string, number>;
};

export type KanbanTask = {
	id: string;
	title: string;
	body: string | null;
	assignee: string | null;
	status: string;
	priority: number;
	tenant: string | null;
	workspace_kind: string;
	workspace_path: string | null;
	branch_name: string | null;
	created_by: string | null;
	created_at: number | null;
	started_at: number | null;
	completed_at: number | null;
	result: string | null;
	skills: string[];
	max_retries: number | null;
};

export type KanbanTaskDetail = {
	task: KanbanTask | null;
	latest_summary: string | null;
	parents: string[];
	children: string[];
	comments: Record<string, unknown>[];
	events: Record<string, unknown>[];
	runs: Record<string, unknown>[];
};

// --- Boards
export const getBoards = (token: string, includeArchived = false) =>
	call(token, 'GET', `/boards?include_archived=${includeArchived}`);

export const createBoard = (token: string, slug: string, name?: string) =>
	call(token, 'POST', '/boards', { slug, name });

export const switchBoard = (token: string, slug: string) =>
	call(token, 'POST', `/boards/${slug}/switch`);

// --- Tasks
export const getTasks = (
	token: string,
	opts: { board?: string; includeArchived?: boolean } = {}
) => {
	const params = new URLSearchParams();
	params.set('include_archived', String(opts.includeArchived ?? false));
	if (opts.board) params.set('board', opts.board);
	return call(token, 'GET', `/tasks?${params.toString()}`);
};

export const getTaskDetail = (token: string, taskId: string, board?: string) =>
	call(token, 'GET', `/tasks/${taskId}${board ? `?board=${board}` : ''}`);

export const createTask = (
	token: string,
	input: {
		title: string;
		body?: string;
		assignee?: string;
		priority?: number;
		workspace?: string;
		triage?: boolean;
		board?: string;
	}
) => call(token, 'POST', '/tasks', input);

export const taskAction = (
	token: string,
	taskId: string,
	verb:
		| 'complete'
		| 'block'
		| 'unblock'
		| 'promote'
		| 'schedule'
		| 'reclaim'
		| 'specify'
		| 'archive'
		| 'assign',
	body: { board?: string; reason?: string; result?: string; assignee?: string } = {}
) => call(token, 'POST', `/tasks/${taskId}/${verb}`, body);

export const dispatchBoard = (token: string, board?: string, dryRun = false) =>
	call(token, 'POST', `/dispatch?dry_run=${dryRun}`, { board });
