<script lang="ts">
	// Sélecteur d'agent dans l'en-tête du chat (SPEC-chat-agentique, critère 2) :
	// montre l'agent actif (visage + prénom) et, au clic, la liste de l'équipe
	// (« Avec qui parler ? »). Choisir un agent = sélectionner son modèle : pas d'état
	// global, le pipeline open-webui standard fait le reste. Adapté du composant v1.
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { models as _models } from '$lib/stores';
	import { teamAgents, agentView, isTeamAgent, avatarImgFallback } from '$lib/utils/team';

	const i18n = getContext('i18n');

	export let selectedModels: string[] = [];

	let open = false;

	$: team = teamAgents($_models);
	$: activeModel = $_models.find((m) => m.id === selectedModels?.[0]);
	$: active = isTeamAgent(activeModel) ? agentView(activeModel) : null;

	const choose = (id: string) => {
		open = false;
		if (selectedModels?.[0] === id) return;
		selectedModels = [id];
		const chosen = team.find((a) => a.id === id);
		if (chosen) {
			toast.success($i18n.t('{{name}} est prêt à discuter', { name: chosen.firstName }));
		}
	};
</script>

{#if team.length > 0}
	<div class="relative">
		<button
			type="button"
			class="flex items-center gap-1.5 rounded-xl px-1.5 py-1 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
			on:click={() => (open = !open)}
			aria-haspopup="menu"
			aria-expanded={open}
			title={$i18n.t('Choisir un agent')}
		>
			{#if active}
				<img
					src={active.avatarUrl}
					alt={active.firstName}
					class="size-6 rounded-full object-cover bg-gray-100 dark:bg-gray-800"
					draggable="false"
					on:error={avatarImgFallback}
				/>
				<span class="text-sm font-medium text-gray-800 dark:text-gray-100 line-clamp-1 max-w-28">
					{active.firstName}
				</span>
			{:else}
				<span class="text-sm font-medium text-gray-500 dark:text-gray-400">
					{$i18n.t('Votre équipe')}
				</span>
			{/if}
			<svg class="size-3.5 text-gray-400 shrink-0" viewBox="0 0 20 20" fill="currentColor">
				<path
					fill-rule="evenodd"
					d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>

		{#if open}
			<button
				class="fixed inset-0 z-40 cursor-default"
				on:click={() => (open = false)}
				tabindex="-1"
				aria-label={$i18n.t('Fermer')}
			></button>

			<div
				role="menu"
				class="absolute left-0 top-full mt-1.5 z-50 w-64 max-h-[70vh] overflow-y-auto rounded-2xl border border-gray-100 bg-white p-1.5 shadow-xl dark:border-gray-800 dark:bg-gray-900 scrollbar-hidden"
			>
				<div
					class="px-2.5 pt-1.5 pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400 dark:text-gray-500"
				>
					{$i18n.t('Avec qui parler ?')}
				</div>

				{#each team as agent (agent.id)}
					<button
						type="button"
						role="menuitem"
						class="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-xl text-left hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => choose(agent.id)}
					>
						<img
							src={agent.avatarUrl}
							alt={agent.firstName}
							class="size-8 rounded-full object-cover bg-gray-100 dark:bg-gray-800 shrink-0"
							draggable="false"
							on:error={avatarImgFallback}
						/>
						<span class="flex flex-col min-w-0 flex-1">
							<span class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
								{agent.firstName}
							</span>
							{#if agent.tagline}
								<span class="text-[11px] text-gray-400 dark:text-gray-500 truncate">
									{agent.tagline}
								</span>
							{/if}
						</span>
						{#if agent.id === selectedModels?.[0]}
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
			</div>
		{/if}
	</div>
{/if}
