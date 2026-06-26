<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { mobile, showSidebar, user } from '$lib/stores';
	import { goto } from '$app/navigation';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';

	import HealthCard from '$lib/components/dashboard/HealthCard.svelte';
	import AlertsBanner from '$lib/components/dashboard/AlertsBanner.svelte';
	import ConnectionsCard from '$lib/components/dashboard/ConnectionsCard.svelte';
	import ActivityCard from '$lib/components/dashboard/ActivityCard.svelte';
	import QuickActionsCard from '$lib/components/dashboard/QuickActionsCard.svelte';

	import { getHermesStatus, getActiveProvider } from '$lib/apis/providers';
	import { getGatewayStatus } from '$lib/apis/gateway';
	import { getMemoryStatus } from '$lib/apis/memory';
	import { getIntegrations } from '$lib/apis/integrations';
	import { getBoards, getTasks } from '$lib/apis/kanban';
	import { deriveAlerts, type DashboardStates, type DisplayStatus } from '$lib/dashboard/alerts';

	let loaded = false;
	let loading = true;

	// États assemblés (honnêteté D27 : 'unknown' tant que non confirmé).
	let bricks: { label: string; status: DisplayStatus; detail?: string }[] = [];
	let states: DashboardStates = {
		bridge: 'unknown',
		engine: 'unknown',
		messaging: 'unknown',
		memory: 'unknown',
		activeBrain: 'unknown',
		blockedTasks: 'unknown'
	};

	// Connexions
	let connectionsUnavailable = false;
	let activeBrainLabel: string | null = null;
	let integrations: { label: string; connected: boolean }[] = [];

	// Activité
	let activityUnavailable = false;
	let counts: { label: string; n: number }[] = [];
	let recent: { title: string; statusLabel: string; blocked: boolean }[] = [];

	$: alerts = deriveAlerts(states);

	// Statuts techniques Kanban -> libellés dirigeant.
	const STATUS_LABELS: Record<string, string> = {
		triage: 'À clarifier',
		todo: 'À faire',
		ready: 'Prêt',
		running: 'En cours',
		scheduled: 'Planifié',
		blocked: 'Bloqué',
		review: 'À valider',
		done: 'Terminé'
	};
	const labelForStatus = (s: string) => STATUS_LABELS[s] ?? s;
	const isBlocked = (s: string) => s === 'blocked' || s === 'review';

	const loadHermes = async () => {
		try {
			const s = await getHermesStatus(localStorage.token);
			if (!s) throw new Error('empty');
			states.bridge = 'ok';
			states.engine = s.hermes_available ? 'ok' : 'down';
			return { engineDetail: s.version ?? undefined };
		} catch {
			states.bridge = 'down';
			states.engine = 'unknown';
			return { engineDetail: undefined };
		}
	};

	const loadActive = async () => {
		try {
			const a = await getActiveProvider(localStorage.token);
			if (a && a.provider_id) {
				states.activeBrain = true;
				activeBrainLabel = a.model_id ? `${a.provider_id} / ${a.model_id}` : a.provider_id;
			} else {
				states.activeBrain = false;
				activeBrainLabel = null;
			}
		} catch {
			states.activeBrain = 'unknown';
			activeBrainLabel = null;
		}
	};

	const loadGateway = async () => {
		try {
			const g = await getGatewayStatus(localStorage.token);
			if (!g) throw new Error('empty');
			states.messaging = g.running ? 'ok' : 'down';
		} catch {
			states.messaging = 'unknown';
		}
	};

	let memoryDetail: string | undefined;
	const loadMemory = async () => {
		try {
			const m = await getMemoryStatus(localStorage.token);
			if (!m) throw new Error('empty');
			states.memory = m.ok ? 'ok' : 'down';
			memoryDetail = m.ok ? `${m.note_count} ${m.note_count > 1 ? 'notes' : 'note'}` : undefined;
		} catch {
			states.memory = 'unknown';
		}
	};

	const loadIntegrations = async () => {
		try {
			const res = await getIntegrations(localStorage.token);
			const list = res?.integrations ?? [];
			integrations = list.map((it: any) => ({
				label: it.name ?? it.id,
				connected: it.state === 'connected'
			}));
		} catch {
			connectionsUnavailable = true;
		}
	};

	const loadKanban = async () => {
		try {
			const [b, t] = await Promise.all([
				getBoards(localStorage.token, false),
				getTasks(localStorage.token, {})
			]);
			const boards = b?.boards ?? [];
			const tasks = t?.tasks ?? [];

			// Compteurs agrégés par statut sur l'ensemble des tableaux.
			const agg: Record<string, number> = {};
			for (const board of boards) {
				for (const [k, v] of Object.entries(board.counts ?? {})) {
					agg[k] = (agg[k] ?? 0) + (v as number);
				}
			}
			counts = Object.entries(agg)
				.filter(([, n]) => (n as number) > 0)
				.map(([k, n]) => ({ label: labelForStatus(k), n: n as number }));

			const blocked = (agg['blocked'] ?? 0) + (agg['review'] ?? 0);
			states.blockedTasks = blocked;

			recent = [...tasks]
				.sort((x: any, y: any) => (y.created_at ?? 0) - (x.created_at ?? 0))
				.slice(0, 6)
				.map((task: any) => ({
					title: task.title,
					statusLabel: labelForStatus(task.status),
					blocked: isBlocked(task.status)
				}));
		} catch {
			activityUnavailable = true;
			states.blockedTasks = 'unknown';
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}
		loaded = true;

		// Chaque source est interrogée indépendamment : la panne de l'une n'empêche pas les autres.
		const [{ engineDetail }] = await Promise.all([
			loadHermes(),
			loadActive(),
			loadGateway(),
			loadMemory(),
			loadIntegrations(),
			loadKanban()
		]);

		bricks = [
			{ label: 'Moteur', status: states.engine, detail: engineDetail },
			{
				label: 'Modèle IA actif',
				status: states.activeBrain === true ? 'ok' : states.activeBrain === false ? 'down' : 'unknown',
				detail: activeBrainLabel ?? undefined
			},
			{ label: 'Messagerie', status: states.messaging },
			{ label: 'Mémoire', status: states.memory, detail: memoryDetail }
		];

		loading = false;
	});
</script>

{#if loaded}
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav class="px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
			<div class="flex items-center">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip content={$i18n.t('Close Sidebar')} interactive={true}>
							<button
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => showSidebar.set(!$showSidebar)}
							>
								<div class="self-center p-1.5"><SidebarIcon /></div>
							</button>
						</Tooltip>
					</div>
				{/if}
				<div class="ml-2 py-0.5 self-center flex items-center w-full">
					<div class="text-sm font-medium py-1">{$i18n.t('Tableau de bord')}</div>
				</div>
			</div>
		</nav>

		<div class="flex-1 max-h-full overflow-y-auto @container">
			<div class="w-full max-w-5xl mx-auto px-3 py-3 flex flex-col gap-3">
				<AlertsBanner {alerts} {loading} />

				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					<HealthCard {bricks} {loading} />
					<ConnectionsCard
						{loading}
						unavailable={connectionsUnavailable}
						{activeBrainLabel}
						{integrations}
					/>
					<ActivityCard {loading} unavailable={activityUnavailable} {counts} {recent} />
					<QuickActionsCard />
				</div>
			</div>
		</div>
	</div>
{/if}
