<script lang="ts">
	// Sélecteur d'agent dans l'en-tête du chat : montre l'agent actif (visage + prénom) et,
	// au clic, déroule la liste de l'équipe (visages) pour choisir avec qui parler.
	// Le changement est GLOBAL (setActiveAgent côté bridge) et incarne aussitôt le chat.
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getAgents, setActiveAgent } from '$lib/apis/agents';
	import { activeAgent, ensureActiveAgent } from '$lib/stores/agent';
	import { agentIdentity, avatarImgFallback } from '$lib/utils/agentIdentity';
	import { resolveAgentView } from '$lib/catalog/agentActions';
	import { avatarColor } from '$lib/components/agents/avatar-colors';

	const i18n = getContext('i18n');

	type Agent = {
		name: string;
		description?: string | null;
		avatar?: string | null;
		active?: boolean;
		is_default?: boolean;
	};

	let open = false;
	let loading = false;
	let agents: Agent[] = [];
	let switching = '';

	// Menu rendu en position FIXE (calculée sous le bouton) pour échapper au conteneur
	// `overflow-hidden` de la barre. Aligné à DROITE du déclencheur (barre côté droit).
	let triggerEl: HTMLButtonElement;
	let menuStyle = '';
	const MENU_W = 264;

	// Vue d'affichage robuste d'un agent : visage + prénom + rôle + dégradé (repli en cascade).
	// Le dégradé est posé en fond du cercle (visage détouré) pour la même identité visuelle
	// que sa carte « Votre équipe ».
	const view = (a: Agent) => {
		const v = resolveAgentView(a);
		const id = agentIdentity(a);
		const avatar = v?.avatar ?? id?.avatarUrl ?? '/favicon.png';
		return {
			firstName: v?.firstName ?? id?.firstName ?? a.name,
			role: v?.role ?? '',
			face: v?.face ?? id?.faceUrl ?? id?.avatarUrl ?? '/favicon.png',
			avatar,
			gradient: avatarColor((v?.avatar ?? id?.avatarUrl) || a.name).gradient
		};
	};

	// Identité de l'agent actif pour le déclencheur (repli sur le store global).
	$: badge = agentIdentity($activeAgent);
	$: badgeGradient = $activeAgent
		? avatarColor($activeAgent.avatar || $activeAgent.name || '').gradient
		: '';

	// Ordre du menu : Mike (l'orchestrateur, profil « default ») TOUJOURS en 1re position —
	// c'est le point d'entrée de l'équipe. Ensuite l'agent actif, puis le reste.
	$: teamSorted = [...agents].sort(
		(a, b) =>
			Number(b.name === 'default') - Number(a.name === 'default') ||
			Number(!!b.active) - Number(!!a.active)
	);

	const load = async () => {
		loading = true;
		try {
			const res = await getAgents(localStorage.token);
			agents = (res?.agents ?? []) as Agent[];
		} catch {
			agents = [];
		} finally {
			loading = false;
		}
	};

	const toggle = async () => {
		open = !open;
		if (open) {
			if (triggerEl) {
				const r = triggerEl.getBoundingClientRect();
				const left = Math.max(8, Math.round(r.right - MENU_W));
				menuStyle = `top:${Math.round(r.bottom + 6)}px; left:${left}px;`;
			}
			await load();
		}
	};

	const choose = async (a: Agent) => {
		if (a.active || switching) {
			open = false;
			return;
		}
		switching = a.name;
		try {
			await setActiveAgent(localStorage.token, a.name);
			await ensureActiveAgent(localStorage.token, true);
			await load();
			toast.success($i18n.t('{{name}} est prêt à discuter', { name: view(a).firstName }));
			open = false;
		} catch {
			toast.error($i18n.t('Impossible d’activer cet agent'));
		} finally {
			switching = '';
		}
	};

	onMount(() => ensureActiveAgent(localStorage.token));
</script>

{#if badge}
	<div class="relative">
		<!-- Déclencheur : agent actif (visage + prénom) -->
		<button
			type="button"
			bind:this={triggerEl}
			style="-webkit-app-region: no-drag;"
			class="flex items-center gap-1.5 rounded-xl px-1.5 py-1 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
			on:click={toggle}
			aria-haspopup="menu"
			aria-expanded={open}
			title={$i18n.t('Choisir un agent')}
		>
			{#if badge.faceUrl ?? badge.avatarUrl}
				<img
					src={badge.faceUrl ?? badge.avatarUrl}
					alt={badge.firstName}
					style="background-image: {badgeGradient}"
					class="size-6 rounded-full object-cover bg-gray-100 dark:bg-gray-800"
					draggable="false"
					on:error={(e) => avatarImgFallback(e, badge.avatarUrl)}
				/>
			{/if}
			<span class="text-sm font-medium text-gray-800 dark:text-gray-100 line-clamp-1 max-w-28">
				{badge.firstName}
			</span>
			<svg class="size-3.5 text-gray-400 shrink-0" viewBox="0 0 20 20" fill="currentColor">
				<path
					fill-rule="evenodd"
					d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>

		{#if open}
			<!-- fond cliquable pour fermer -->
			<button
				class="fixed inset-0 z-40 cursor-default"
				on:click={() => (open = false)}
				tabindex="-1"
				aria-label={$i18n.t('Fermer')}
			></button>

			<div
				role="menu"
				style="{menuStyle} width:{MENU_W}px; -webkit-app-region: no-drag;"
				class="fixed z-50 max-h-[70vh] overflow-y-auto rounded-2xl border border-gray-100 bg-white p-1.5 shadow-xl dark:border-gray-800 dark:bg-gray-900 scrollbar-hidden"
			>
				<div
					class="px-2.5 pt-1.5 pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400 dark:text-gray-500"
				>
					{$i18n.t('Avec qui parler ?')}
				</div>

				{#if loading && agents.length === 0}
					<div class="px-2.5 py-3 text-sm text-gray-400">{$i18n.t('Chargement…')}</div>
				{:else}
					{#each teamSorted as a (a.name)}
						{@const v = view(a)}
						<button
							type="button"
							role="menuitem"
							class="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-xl text-left hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-60"
							on:click={() => choose(a)}
							disabled={!!switching}
						>
							<img
								src={v.face}
								alt={v.firstName}
								style="background-image: {v.gradient}"
								class="size-8 rounded-full object-cover bg-gray-100 dark:bg-gray-800 shrink-0"
								draggable="false"
								on:error={(e) => avatarImgFallback(e, v.avatar)}
							/>
							<span class="flex flex-col min-w-0 flex-1">
								<span class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
									{v.firstName}
								</span>
								{#if v.role}
									<span class="text-[11px] text-gray-400 dark:text-gray-500 truncate">{v.role}</span>
								{/if}
							</span>
							{#if switching === a.name}
								<svg class="size-4 text-gray-400 animate-spin shrink-0" viewBox="0 0 24 24" fill="none">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
								</svg>
							{:else if a.active}
								<svg class="size-4 text-emerald-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
									<path
										fill-rule="evenodd"
										d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		{/if}
	</div>
{/if}
