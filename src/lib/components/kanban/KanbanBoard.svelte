<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getBoards,
		createBoard,
		switchBoard,
		getTasks,
		getTaskDetail,
		createTask,
		taskAction,
		dispatchBoard,
		type KanbanBoard,
		type KanbanTask,
		type KanbanTaskDetail
	} from '$lib/apis/kanban';
	import { getAgents } from '$lib/apis/agents';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	let showDispatchConfirm = false;

	// Colonnes (ordre du flux de travail). « archived » n'apparaît que si demandé.
	const COLUMNS = [
		{ key: 'triage', label: 'Triage' },
		{ key: 'todo', label: 'À faire' },
		{ key: 'ready', label: 'Prêt' },
		{ key: 'running', label: 'En cours' },
		{ key: 'scheduled', label: 'Planifié' },
		{ key: 'blocked', label: 'Bloqué' },
		{ key: 'review', label: 'Revue' },
		{ key: 'done', label: 'Terminé' }
	];

	let loading = true;
	let bridgeDown = false;

	let boards: KanbanBoard[] = [];
	let currentBoard = 'default';
	let tasks: KanbanTask[] = [];
	let agents: { name: string; description?: string }[] = [];
	let showArchived = false;
	let dispatching = false;

	// modale nouvelle tâche
	let showTaskModal = false;
	let nt = { title: '', body: '', assignee: '', priority: 0, triage: false };
	let creatingTask = false;

	// modale nouveau board
	let showBoardModal = false;
	let nb = { slug: '', name: '' };
	let creatingBoard = false;

	// panneau de détail
	let detail: KanbanTaskDetail | null = null;
	let detailLoading = false;

	let draggedId: string | null = null;
	let refreshTimer: ReturnType<typeof setInterval> | null = null;

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	$: columns = showArchived ? [...COLUMNS, { key: 'archived', label: 'Archivé' }] : COLUMNS;
	$: tasksByStatus = (() => {
		const map: Record<string, KanbanTask[]> = {};
		for (const c of columns) map[c.key] = [];
		for (const t of tasks) {
			if (map[t.status]) map[t.status].push(t);
			else if (map['todo']) map['todo'].push(t);
		}
		return map;
	})();

	const load = async (silent = false) => {
		if (!silent) loading = true;
		bridgeDown = false;
		try {
			const token = localStorage.token;
			// Board pour lequel on demande les tâches (peut différer du board courant côté serveur).
			const requestedBoard = currentBoard;
			const [b, t] = await Promise.all([
				getBoards(token, false),
				getTasks(token, { board: requestedBoard, includeArchived: showArchived })
			]);
			boards = b?.boards ?? [];
			const serverBoard = b?.current ?? requestedBoard;
			currentBoard = serverBoard;
			// Si le board courant côté serveur diffère de celui demandé, recharge les tâches du
			// bon board : sinon on afficherait les tâches d'un board en surlignant l'autre.
			if (serverBoard !== requestedBoard) {
				const t2 = await getTasks(token, { board: serverBoard, includeArchived: showArchived });
				tasks = t2?.tasks ?? [];
			} else {
				tasks = t?.tasks ?? [];
			}
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else if (!silent) toast.error($i18n.t('Échec du chargement'));
		} finally {
			loading = false;
		}
	};

	const loadAgents = async () => {
		try {
			const res = await getAgents(localStorage.token);
			agents = res?.agents ?? res ?? [];
		} catch {
			agents = [];
		}
	};

	const onSwitchBoard = async (slug: string) => {
		currentBoard = slug;
		try {
			await switchBoard(localStorage.token, slug);
		} catch {
			// le board courant est surtout local à l'UI ; on recharge quand même
		}
		await load(true);
	};

	const submitBoard = async () => {
		if (!nb.slug.trim()) return;
		creatingBoard = true;
		try {
			await createBoard(localStorage.token, nb.slug.trim(), nb.name.trim() || undefined);
			toast.success($i18n.t('Board créé'));
			showBoardModal = false;
			nb = { slug: '', name: '' };
			await load(true);
		} catch (err) {
			toast.error($i18n.t('Échec de la création'));
		} finally {
			creatingBoard = false;
		}
	};

	const submitTask = async () => {
		if (!nt.title.trim()) return;
		creatingTask = true;
		try {
			await createTask(localStorage.token, {
				title: nt.title.trim(),
				body: nt.body.trim() || undefined,
				assignee: nt.assignee || undefined,
				priority: nt.priority,
				triage: nt.triage,
				board: currentBoard
			});
			toast.success($i18n.t('Tâche créée'));
			showTaskModal = false;
			nt = { title: '', body: '', assignee: '', priority: 0, triage: false };
			await load(true);
		} catch (err) {
			toast.error($i18n.t('Échec de la création'));
		} finally {
			creatingTask = false;
		}
	};

	const act = async (taskId: string, verb: any, extra: any = {}) => {
		try {
			const res = await taskAction(localStorage.token, taskId, verb, {
				board: currentBoard,
				...extra
			});
			if (res?.ok === false) {
				toast.error(res?.message || $i18n.t('Action impossible'));
			}
			await load(true);
			if (detail?.task?.id === taskId) openDetail(taskId);
		} catch (err) {
			toast.error($i18n.t('Action impossible'));
		}
	};

	const onDispatch = async () => {
		dispatching = true;
		try {
			const res = await dispatchBoard(localStorage.token, currentBoard, false);
			if (res?.ok === false) toast.error(res?.message || $i18n.t('Dispatch impossible'));
			else toast.success($i18n.t('Dispatch lancé'));
			setTimeout(() => load(true), 2500);
		} catch (err) {
			toast.error($i18n.t('Dispatch impossible'));
		} finally {
			dispatching = false;
		}
	};

	const openDetail = async (taskId: string) => {
		detailLoading = true;
		try {
			detail = await getTaskDetail(localStorage.token, taskId, currentBoard);
		} catch {
			detail = null;
			toast.error($i18n.t('Détail indisponible'));
		} finally {
			detailLoading = false;
		}
	};
	const closeDetail = () => (detail = null);

	// --- transitions par glisser-déposer ------------------------------------
	const resolveVerb = (from: string, to: string): string | null => {
		if (from === to) return null;
		switch (to) {
			case 'blocked':
				return ['todo', 'ready', 'running', 'scheduled', 'review'].includes(from) ? 'block' : null;
			case 'ready':
				if (from === 'blocked' || from === 'scheduled') return 'unblock';
				if (from === 'todo') return 'promote';
				if (from === 'running') return 'reclaim';
				return null;
			case 'scheduled':
				return ['todo', 'ready', 'blocked'].includes(from) ? 'schedule' : null;
			case 'done':
				return from !== 'archived' ? 'complete' : null;
			case 'archived':
				return 'archive';
			case 'todo':
				return from === 'triage' ? 'specify' : null;
			default:
				return null;
		}
	};

	const onDrop = (toStatus: string) => {
		const id = draggedId;
		draggedId = null;
		if (!id) return;
		const task = tasks.find((t) => t.id === id);
		if (!task) return;
		const verb = resolveVerb(task.status, toStatus);
		if (!verb) {
			toast.error($i18n.t('Transition non autorisée'));
			return;
		}
		act(id, verb);
	};

	// --- helpers d'affichage -------------------------------------------------
	const prio = (p: number) => {
		if (p >= 10) return { label: 'Urgent', cls: 'bg-red-500/10 text-red-600 dark:text-red-400' };
		if (p >= 5) return { label: 'Élevé', cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' };
		if (p < 0) return { label: 'Bas', cls: 'bg-gray-500/10 text-gray-500' };
		return null;
	};

	const age = (ts: number | null) => {
		if (!ts) return '';
		const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
		if (s < 3600) return `${Math.floor(s / 60)}min`;
		if (s < 86400) return `${Math.floor(s / 3600)}h`;
		return `${Math.floor(s / 86400)}j`;
	};

	const initials = (name: string | null) =>
		(name || '?')
			.split(/[-_\s]/)
			.map((p) => p[0])
			.join('')
			.slice(0, 2)
			.toUpperCase();

	// actions contextuelles par statut (boutons compacts sur la carte)
	const cardActions = (status: string) => {
		switch (status) {
			case 'triage':
				return [{ verb: 'specify', label: 'Préciser' }];
			case 'todo':
				return [{ verb: 'promote', label: 'Promouvoir' }, { verb: 'block', label: 'Bloquer' }];
			case 'ready':
				return [{ verb: 'complete', label: 'Terminer' }, { verb: 'block', label: 'Bloquer' }];
			case 'running':
				return [{ verb: 'reclaim', label: 'Reprendre' }];
			case 'blocked':
				return [{ verb: 'unblock', label: 'Débloquer' }];
			case 'scheduled':
				return [{ verb: 'unblock', label: 'Activer' }];
			case 'review':
				return [{ verb: 'complete', label: 'Terminer' }];
			case 'done':
				return [{ verb: 'archive', label: 'Archiver' }];
			default:
				return [];
		}
	};

	onMount(() => {
		load();
		loadAgents();
		refreshTimer = setInterval(() => load(true), 8000);
	});
	onDestroy(() => {
		if (refreshTimer) clearInterval(refreshTimer);
	});
</script>

<div class="flex flex-col h-full w-full">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner /></div>
	{:else if bridgeDown}
		<div class="flex flex-col items-center justify-center text-center py-16 gap-3">
			<div class="text-sm font-medium">{$i18n.t('Le service Tâches est injoignable.')}</div>
			<button
				class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => load()}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- Barre d'outils : boards + actions -->
		<div class="flex items-center gap-2 px-3 py-2 flex-wrap">
			<div class="flex items-center gap-1 overflow-x-auto scrollbar-none">
				{#each boards as b (b.slug)}
					<button
						class="px-2.5 py-1 text-xs rounded-lg transition whitespace-nowrap {b.slug ===
						currentBoard
							? 'bg-gray-200 dark:bg-gray-800 font-medium'
							: 'hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-500'}"
						on:click={() => onSwitchBoard(b.slug)}
					>
						{b.name}
						<span class="opacity-60">({b.total})</span>
					</button>
				{/each}
				<button
					class="px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-400 transition"
					title={$i18n.t('Nouveau board')}
					on:click={() => (showBoardModal = true)}
				>
					+ {$i18n.t('Board')}
				</button>
			</div>

			<div class="flex-1"></div>

			<label class="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
				<input type="checkbox" bind:checked={showArchived} on:change={() => load(true)} />
				{$i18n.t('Archivées')}
			</label>
			<button
				class="px-2.5 py-1 text-xs rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => load()}
			>
				{$i18n.t('Rafraîchir')}
			</button>
			<button
				class="px-2.5 py-1 text-xs rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50"
				on:click={() => (showDispatchConfirm = true)}
				disabled={dispatching}
				title={$i18n.t('Promouvoir les tâches prêtes et lancer les agents')}
			>
				{dispatching ? $i18n.t('Dispatch…') : $i18n.t('Dispatch')}
			</button>
			<button
				class="px-2.5 py-1 text-xs rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
				on:click={() => (showTaskModal = true)}
			>
				+ {$i18n.t('Nouvelle tâche')}
			</button>
		</div>

		<!-- Colonnes -->
		<div class="flex-1 overflow-x-auto overflow-y-hidden px-3 pb-3">
			<div class="flex gap-3 h-full min-w-fit">
				{#each columns as col (col.key)}
					<div
						class="flex flex-col w-72 shrink-0 rounded-2xl bg-gray-50 dark:bg-gray-850/50"
						on:dragover|preventDefault
						on:drop|preventDefault={() => onDrop(col.key)}
						role="list"
					>
						<div class="flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500">
							<span>{$i18n.t(col.label)}</span>
							<span class="opacity-60">{tasksByStatus[col.key]?.length ?? 0}</span>
						</div>
						<div class="flex-1 overflow-y-auto px-2 pb-2 flex flex-col gap-2">
							{#each tasksByStatus[col.key] ?? [] as task (task.id)}
								{@const p = prio(task.priority)}
								<div
									class="rounded-xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 p-2.5 cursor-pointer hover:border-gray-300 dark:hover:border-gray-700 transition"
									draggable="true"
									on:dragstart={() => (draggedId = task.id)}
									on:click={() => openDetail(task.id)}
									role="listitem"
								>
									<div class="flex items-start justify-between gap-2">
										<div class="text-sm font-medium line-clamp-2">{task.title}</div>
										{#if task.status === 'running'}
											<span class="relative flex size-2 mt-1 shrink-0">
												<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
												<span class="relative inline-flex rounded-full size-2 bg-green-500"></span>
											</span>
										{/if}
									</div>

									<div class="flex items-center gap-1.5 mt-2 flex-wrap">
										{#if task.assignee}
											<span
												class="inline-flex items-center justify-center size-5 rounded-full bg-gray-200 dark:bg-gray-700 text-[9px] font-semibold"
												title={task.assignee}
											>
												{initials(task.assignee)}
											</span>
										{/if}
										{#if p}
											<span class="px-1.5 py-0.5 rounded-full text-[10px] font-medium {p.cls}">{$i18n.t(p.label)}</span>
										{/if}
										{#if task.skills?.length}
											<span class="text-[10px] text-gray-400">{task.skills.length} skill(s)</span>
										{/if}
										<span class="text-[10px] text-gray-400 ml-auto">{age(task.created_at)}</span>
									</div>

									{#if cardActions(task.status).length}
										<div class="flex items-center gap-1 mt-2 flex-wrap" on:click|stopPropagation role="group">
											{#each cardActions(task.status) as a}
												<button
													class="px-1.5 py-0.5 text-[10px] rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
													on:click={() => act(task.id, a.verb)}
												>
													{$i18n.t(a.label)}
												</button>
											{/each}
										</div>
									{/if}
								</div>
							{/each}
							{#if (tasksByStatus[col.key] ?? []).length === 0}
								<div class="text-[11px] text-gray-300 dark:text-gray-700 text-center py-4">—</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

<!-- Modale nouvelle tâche -->
{#if showTaskModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" on:click={() => (showTaskModal = false)} role="presentation">
		<div class="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 shadow-xl p-5" on:click|stopPropagation role="dialog" aria-modal="true">
			<div class="text-base font-medium mb-4">{$i18n.t('Nouvelle tâche')}</div>
			<div class="flex flex-col gap-3">
				<input class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none" placeholder={$i18n.t('Titre')} bind:value={nt.title} />
				<textarea class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none resize-none" rows="3" placeholder={$i18n.t('Description (optionnel)')} bind:value={nt.body}></textarea>
				<div class="flex items-center gap-2">
					<select class="flex-1 px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none" bind:value={nt.assignee}>
						<option value="">{$i18n.t('Agent (non assigné)')}</option>
						{#each agents as a}
							<option value={a.name}>{a.name}</option>
						{/each}
					</select>
					<select class="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none" bind:value={nt.priority}>
						<option value={0}>{$i18n.t('Priorité normale')}</option>
						<option value={5}>{$i18n.t('Élevée')}</option>
						<option value={10}>{$i18n.t('Urgente')}</option>
						<option value={-5}>{$i18n.t('Basse')}</option>
					</select>
				</div>
				<label class="flex items-center gap-2 text-xs text-gray-500 cursor-pointer">
					<input type="checkbox" bind:checked={nt.triage} />
					{$i18n.t('Triage (un agent précisera la tâche avant exécution)')}
				</label>
			</div>
			<div class="flex items-center gap-2 mt-5">
				<div class="flex-1"></div>
				<button class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => (showTaskModal = false)}>
					{$i18n.t('Annuler')}
				</button>
				<button class="px-3 py-1.5 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40" on:click={submitTask} disabled={!nt.title.trim() || creatingTask}>
					{$i18n.t('Créer')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Modale nouveau board -->
{#if showBoardModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" on:click={() => (showBoardModal = false)} role="presentation">
		<div class="w-full max-w-md rounded-2xl bg-white dark:bg-gray-900 shadow-xl p-5" on:click|stopPropagation role="dialog" aria-modal="true">
			<div class="text-base font-medium mb-4">{$i18n.t('Nouveau board')}</div>
			<div class="flex flex-col gap-3">
				<input class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none" placeholder={$i18n.t('Identifiant (ex : projet-x)')} bind:value={nb.slug} />
				<input class="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none" placeholder={$i18n.t('Nom affiché (optionnel)')} bind:value={nb.name} />
			</div>
			<div class="flex items-center gap-2 mt-5">
				<div class="flex-1"></div>
				<button class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => (showBoardModal = false)}>
					{$i18n.t('Annuler')}
				</button>
				<button class="px-3 py-1.5 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40" on:click={submitBoard} disabled={!nb.slug.trim() || creatingBoard}>
					{$i18n.t('Créer')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Panneau de détail -->
{#if detail || detailLoading}
	<div class="fixed inset-0 z-50 flex justify-end bg-black/40" on:click={closeDetail} role="presentation">
		<div class="w-full max-w-md h-full overflow-y-auto bg-white dark:bg-gray-900 shadow-xl p-5" on:click|stopPropagation role="dialog" aria-modal="true">
			{#if detailLoading}
				<div class="flex justify-center py-16"><Spinner /></div>
			{:else if detail?.task}
				{@const t = detail.task}
				<div class="flex items-start justify-between gap-2 mb-3">
					<div class="text-base font-medium">{t.title}</div>
					<button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500" on:click={closeDetail} aria-label={$i18n.t('Fermer')}>✕</button>
				</div>
				<div class="flex items-center gap-2 flex-wrap mb-4 text-xs text-gray-500">
					<span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">{$i18n.t('Statut')} : {t.status}</span>
					{#if t.assignee}<span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">{t.assignee}</span>{/if}
					<span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">{t.id}</span>
				</div>

				{#if t.body}
					<div class="mb-4">
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{$i18n.t('Description')}</div>
						<div class="text-sm whitespace-pre-wrap">{t.body}</div>
					</div>
				{/if}

				{#if detail.latest_summary}
					<div class="mb-4">
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{$i18n.t('Dernier résumé')}</div>
						<div class="text-sm whitespace-pre-wrap">{detail.latest_summary}</div>
					</div>
				{/if}

				{#if t.result}
					<div class="mb-4">
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{$i18n.t('Résultat')}</div>
						<div class="text-sm whitespace-pre-wrap bg-gray-50 dark:bg-gray-850 rounded-lg p-2">{t.result}</div>
					</div>
				{/if}

				{#if detail.runs?.length}
					<div class="mb-4">
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{$i18n.t('Exécutions')} ({detail.runs.length})</div>
						<div class="flex flex-col gap-1.5">
							{#each detail.runs as run}
								<div class="text-xs bg-gray-50 dark:bg-gray-850 rounded-lg p-2">
									<span class="font-medium">{run.profile ?? '?'}</span>
									{#if run.outcome}<span class="ml-2 text-gray-500">{run.outcome}</span>{/if}
									{#if run.summary}<div class="text-gray-500 mt-1">{run.summary}</div>{/if}
									{#if run.error}<div class="text-red-500 mt-1">{run.error}</div>{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if detail.comments?.length}
					<div class="mb-4">
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{$i18n.t('Commentaires')} ({detail.comments.length})</div>
						<div class="flex flex-col gap-1.5">
							{#each detail.comments as c}
								<div class="text-xs bg-gray-50 dark:bg-gray-850 rounded-lg p-2">
									<span class="font-medium">{c.author ?? '?'}</span>
									<div class="text-gray-600 dark:text-gray-300 mt-0.5">{c.body}</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if detail.events?.length}
					<div class="mb-2">
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{$i18n.t('Historique')}</div>
						<div class="flex flex-col gap-1">
							{#each detail.events.slice(-12).reverse() as e}
								<div class="text-[11px] text-gray-500 flex items-center gap-2">
									<span class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800">{e.kind}</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}

<ConfirmDialog
	bind:show={showDispatchConfirm}
	title={$i18n.t('Lancer le dispatch ?')}
	message={$i18n.t(
		'Les tâches prêtes vont être promues et les agents lancés pour les exécuter. Cette action démarre du travail réel.'
	)}
	confirmLabel={$i18n.t('Lancer')}
	onConfirm={onDispatch}
/>
