<script lang="ts">
	// Niveau d'intelligence en français (SPEC-chat-agentique, critère 4) : Rapide /
	// Équilibré / Approfondi / Maximum — l'effort de raisonnement GLOBAL du moteur Hermes
	// (recette v1 : deux axes orthogonaux, le niveau n'est jamais dans le payload de chat).
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getReasoning, setReasoning } from '$lib/apis/providers';

	const i18n = getContext('i18n');

	const LEVELS = [
		{ effort: 'low', label: 'Rapide', desc: 'Réponses vives' },
		{ effort: 'medium', label: 'Équilibré', desc: 'Le bon compromis' },
		{ effort: 'high', label: 'Approfondi', desc: 'Réflexion poussée' },
		{ effort: 'xhigh', label: 'Maximum', desc: 'Raisonnement maximal' }
	];

	let open = false;
	let effort = 'medium';
	let available = false; // masqué tant que le moteur ne répond pas (jamais d'erreur visible)

	$: current = LEVELS.find((l) => l.effort === effort) ?? LEVELS[1];

	const choose = async (level: (typeof LEVELS)[number]) => {
		open = false;
		if (level.effort === effort) return;
		const previous = effort;
		effort = level.effort;
		try {
			await setReasoning(localStorage.token, level.effort);
		} catch {
			effort = previous;
			toast.error($i18n.t('Impossible de changer le niveau d’intelligence'));
		}
	};

	onMount(async () => {
		try {
			const res = await getReasoning(localStorage.token);
			if (res?.effort) {
				effort = res.effort;
				available = true;
			}
		} catch {
			available = false;
		}
	});
</script>

{#if available}
	<div class="relative">
		<button
			type="button"
			class="flex items-center gap-1 rounded-xl px-1.5 py-1 text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
			on:click={() => (open = !open)}
			aria-haspopup="menu"
			aria-expanded={open}
			title={$i18n.t('Niveau d’intelligence')}
		>
			<span class="hidden @sm:inline text-gray-400 dark:text-gray-500">·</span>
			<span>{current.label}</span>
			<svg class="size-3 text-gray-400 shrink-0" viewBox="0 0 20 20" fill="currentColor">
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
				class="absolute left-0 top-full mt-1.5 z-50 w-60 rounded-2xl border border-gray-100 bg-white p-1.5 shadow-xl dark:border-gray-800 dark:bg-gray-900"
			>
				<div
					class="px-2.5 pt-1.5 pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400 dark:text-gray-500"
				>
					{$i18n.t('Intelligence')}
				</div>
				{#each LEVELS as level (level.effort)}
					<button
						type="button"
						role="menuitem"
						class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-left hover:bg-gray-100 dark:hover:bg-gray-850 transition {level.effort ===
						effort
							? 'bg-gray-100 dark:bg-gray-850'
							: ''}"
						on:click={() => choose(level)}
					>
						<span class="flex flex-col min-w-0 flex-1">
							<span class="text-sm font-medium text-gray-800 dark:text-gray-100">{level.label}</span>
							<span class="text-[11px] text-gray-400 dark:text-gray-500">{level.desc}</span>
						</span>
						{#if level.effort === effort}
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
