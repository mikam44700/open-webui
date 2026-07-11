<script lang="ts">
	// Modale « Voir ses compétences » d'un agent : sa mission (SOUL) + ses intégrations recommandées
	// (état réel, jamais supposé). Autonome et partagée entre la galerie « Prêts à l'emploi » et la
	// page Catalogue (DRY). Émet `adopt` (activer l'agent) et `close`.
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import type { AgentTemplate } from './templates';
	import { avatarId, faceFromImage } from './avatars';
	import { avatarColor } from './avatar-colors';
	import MissionSections from './MissionSections.svelte';
	import { buildReco, loadRecoState, emptyRecoState, type RecoState } from './agentReco';

	export let template: AgentTemplate | null = null;

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let recoState: RecoState = emptyRecoState();
	let imgError: Record<string, boolean> = {};

	onMount(async () => {
		recoState = await loadRecoState(localStorage.token);
	});

	$: recoItems = buildReco(template, recoState);
	// Couleur signature de l'agent (même teinte que sa carte) → cadre coloré autour du visage.
	$: col = template ? avatarColor(avatarId(template.image) || template.id) : null;

	const close = () => dispatch('close');
	const adopt = () => {
		const t = template;
		dispatch('close');
		if (t) dispatch('adopt', t);
	};
</script>

<svelte:window
	on:keydown={(e) => {
		if (e.key === 'Escape' && template) close();
	}}
/>

{#if template}
	<div
		class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
		on:click|self={close}
		transition:fade={{ duration: 150 }}
		role="presentation"
	>
		<div
			class="relative w-full max-w-lg max-h-[85vh] flex flex-col rounded-3xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-100 dark:border-gray-800"
			in:fly={{ y: 12, duration: 200 }}
			role="dialog"
			aria-modal="true"
		>
			<!-- En-tête -->
			<div class="flex items-center gap-3.5 p-5 border-b border-gray-100 dark:border-gray-800">
				{#if template.image && !imgError[template.id]}
					<!-- Gros plan visage cadré, posé sur un fin cadre à la couleur signature de l'agent. -->
					<div
						class="flex-none size-11 rounded-2xl p-[2px] shadow-sm ring-1 ring-black/5"
						style="background-image: {col?.gradient}"
					>
						<img
							src={faceFromImage(template.image)}
							alt={template.label}
							on:error={() => template && (imgError = { ...imgError, [template.id]: true })}
							class="size-full rounded-[14px] object-cover"
						/>
					</div>
				{:else}
					<div
						class="flex-none size-11 rounded-2xl flex items-center justify-center text-2xl shadow-sm ring-1 ring-black/5 {col?.light
							? 'text-gray-900'
							: 'text-white'}"
						style="background-image: {col?.gradient}"
					>
						{template.emoji}
					</div>
				{/if}
				<div class="min-w-0 flex-1">
					<div class="text-base font-semibold truncate">
						{template.firstName ?? template.label}
					</div>
					{#if template.role}
						<div class="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">
							{template.role}
						</div>
					{/if}
				</div>
				<button
					class="flex-none p-1.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={close}
					aria-label={$i18n.t('Fermer')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
						<path
							d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
						/>
					</svg>
				</button>
			</div>

			<!-- Corps : la mission (SOUL) en cartes lisibles, défilable -->
			<div class="flex-1 overflow-y-auto px-5 py-4">
				<MissionSections soul={template.soul} animate={false} />

				<!-- Intégrations recommandées : ce qui rend cet agent vraiment utile (état réel, jamais supposé) -->
				{#if recoItems.length}
					<div class="mt-5 pt-4 border-t border-gray-100 dark:border-gray-800">
						<div class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2.5">
							{$i18n.t('Intégrations recommandées')}
						</div>
						<div class="flex flex-col gap-1.5">
							{#each recoItems as it (it.key)}
								<div
									class="flex items-center gap-3 rounded-xl border border-gray-100 dark:border-gray-800 px-3 py-2"
								>
									<div
										class="flex-none size-8 rounded-lg overflow-hidden flex items-center justify-center ring-1 ring-black/5 {it.bg}"
									>
										{#if it.logo}
											<img
												src={it.logo}
												alt={it.name}
												class={it.fullBleed ? 'h-full w-full object-cover' : 'h-5 w-5 object-contain'}
											/>
										{/if}
									</div>
									<div class="min-w-0 flex-1">
										<div class="text-sm font-medium truncate">{it.name}</div>
										<div
											class="text-[11px] {it.connected
												? 'text-emerald-600 dark:text-emerald-400'
												: 'text-gray-400'}"
										>
											{it.connected ? '✓ ' + $i18n.t('Connecté') : $i18n.t('À connecter')}
										</div>
									</div>
									<button
										class="flex-none text-[12px] font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white underline-offset-2 hover:underline transition"
										on:click={() => {
											close();
											goto(`/connectors?tab=${it.tab}`);
										}}
									>
										{it.connected ? $i18n.t('Gérer') : $i18n.t('Connecter')}
									</button>
								</div>
							{/each}
						</div>
						<p class="text-[11px] text-gray-400 mt-2">
							{$i18n.t('Ces connexions rendent cet agent plus utile — activez-les quand vous voulez.')}
						</p>
					</div>
				{/if}
			</div>

			<!-- Pied : activer -->
			<div class="p-4 border-t border-gray-100 dark:border-gray-800">
				<button
					class="w-full text-sm font-medium px-3 py-2.5 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-black hover:opacity-90 hover:shadow-md transition-all"
					on:click={adopt}
				>
					{$i18n.t('+ Activer')}
				</button>
			</div>
		</div>
	</div>
{/if}
