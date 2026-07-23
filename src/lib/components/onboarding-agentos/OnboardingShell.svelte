<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type { OnboardingDraft } from '$lib/onboarding-agentos/types';

	export let step: OnboardingDraft['step'];
	export let canRestart = false;

	const dispatch = createEventDispatcher();

	const phases = [
		{ id: 'welcome', label: 'Bienvenue' },
		{ id: 'discovery', label: 'Découverte' },
		{ id: 'interview', label: 'Entretien' },
		{ id: 'documents', label: 'Documents' },
		{ id: 'review', label: 'Carte' },
		{ id: 'agentos', label: 'AgentOS' }
	];

	const phaseIndex = (value: OnboardingDraft['step']) => {
		if (value === 'welcome' || value === 'model') return 0;
		if (value === 'site' || value === 'analysis') return 1;
		if (value === 'interview') return 2;
		if (value === 'documents') return 3;
		if (value === 'review') return 4;
		return 5;
	};

	$: activeIndex = phaseIndex(step);
</script>

<div
	class="fixed inset-0 z-[999] overflow-y-auto bg-[#f7f7f8] text-gray-950 dark:bg-[#0a0a0a] dark:text-gray-50"
>
	<div class="fixed inset-0 pointer-events-none overflow-hidden">
		<div class="absolute -top-24 left-[12%] size-80 rounded-full bg-[#6b62f2]/12 blur-3xl"></div>
		<div class="absolute top-[35%] right-[5%] size-72 rounded-full bg-indigo-400/8 blur-3xl"></div>
	</div>

	<header
		class="relative z-10 border-b border-black/5 bg-white/55 px-5 py-4 backdrop-blur dark:border-white/6 dark:bg-black/30 md:px-8"
	>
		<div class="mx-auto flex w-full max-w-6xl items-center justify-between gap-4">
			<button class="flex items-center gap-3" on:click={() => dispatch('leave')}>
				<img src="/static/favicon.png" alt="LunarIA" class="size-8 rounded-xl" />
				<div class="text-left">
					<div class="text-sm font-semibold">LunarIA</div>
					<div class="text-[11px] text-gray-500 dark:text-gray-400">Création de votre AgentOS</div>
				</div>
			</button>
			<div class="flex items-center gap-2">
				{#if canRestart}
					<button
						class="rounded-full px-3 py-1.5 text-xs text-gray-500 hover:bg-black/5 dark:hover:bg-white/5"
						on:click={() => dispatch('restart')}>Recommencer</button
					>
				{/if}
				<button
					class="rounded-full px-3 py-1.5 text-xs text-gray-500 hover:bg-black/5 dark:hover:bg-white/5"
					on:click={() => dispatch('leave')}>Reprendre plus tard</button
				>
			</div>
		</div>

		<div class="mx-auto mt-4 grid w-full max-w-6xl grid-cols-6 gap-1.5">
			{#each phases as phase, index}
				<div>
					<div
						class="h-1.5 rounded-full transition {index <= activeIndex
							? 'bg-[#6b62f2]'
							: 'bg-gray-200 dark:bg-gray-800'}"
					></div>
					<div
						class="mt-1.5 hidden text-[10px] font-medium sm:block {index === activeIndex
							? 'text-[#5b52dd] dark:text-[#aaa4ff]'
							: 'text-gray-400'}"
					>
						{phase.label}
					</div>
				</div>
			{/each}
		</div>
	</header>

	<main
		class="relative z-10 mx-auto flex min-h-[calc(100vh-112px)] w-full max-w-6xl flex-col px-5 pb-12 md:px-8"
	>
		<slot />
	</main>
</div>
