<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let alreadyDone = false;

	const dispatch = createEventDispatcher();

	const outcomes = [
		['01', 'Découvrir', 'Votre site et ce que le Web dit de votre entreprise'],
		['02', 'Comprendre', 'Vos clients, processus, priorités et pertes'],
		['03', 'Apprendre', 'Les documents et sources de vérité que vous choisissez'],
		['04', 'Structurer', 'Une Carte opérationnelle vérifiée par vous'],
		['05', 'Recommander', 'Un à trois workflows mesurables et encadrés'],
		['06', 'Préparer', 'La mémoire, les outils et la prochaine action']
	];
</script>

<section class="m-auto grid w-full items-center gap-8 py-10 lg:grid-cols-[0.9fr_1.1fr]">
	<div
		class="relative min-h-[520px] overflow-hidden rounded-[2.25rem] border border-[#6b62f2]/20 bg-gradient-to-br from-[#6b62f2]/18 via-white to-indigo-100 p-7 dark:from-[#6b62f2]/25 dark:via-[#161616] dark:to-indigo-950/30 md:p-10"
	>
		<div class="absolute -right-20 -top-20 size-64 rounded-full bg-[#6b62f2]/25 blur-3xl"></div>
		<div class="relative z-10">
			<div
				class="text-xs font-semibold uppercase tracking-[0.16em] text-[#5b52dd] dark:text-[#aaa4ff]"
			>
				Bienvenue sur LunarIA
			</div>
			<h1 class="mt-3 text-4xl font-medium tracking-[-0.04em] md:text-5xl">
				Bonjour, je suis Luna.
			</h1>
			<p class="mt-4 max-w-lg text-base leading-7 text-gray-600 dark:text-gray-300">
				Je vais apprendre comment votre entreprise fonctionne avant de vous proposer quoi que ce
				soit. À la fin, vous aurez une mémoire vérifiée et un premier système réellement utile.
			</p>
			<div
				class="mt-6 inline-flex rounded-full border border-black/8 bg-white/65 px-3 py-1.5 text-xs text-gray-600 dark:border-white/10 dark:bg-white/8 dark:text-gray-300"
			>
				Environ 10 à 15 minutes · reprenable à tout moment
			</div>
		</div>
		<img
			src="/static/agents/luna.png"
			alt="Luna, orchestratrice de LunarIA"
			class="absolute bottom-0 right-2 h-[54%] max-w-[70%] object-contain object-bottom drop-shadow-[0_20px_35px_rgba(0,0,0,0.22)] md:right-8 md:h-[58%]"
		/>
	</div>

	<div>
		<div class="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">
			Ce que nous allons construire ensemble
		</div>
		<div class="mt-4 grid gap-3 sm:grid-cols-2">
			{#each outcomes as item}
				<div
					class="rounded-2xl border border-black/6 bg-white p-4 dark:border-white/8 dark:bg-[#161616]"
				>
					<div class="flex gap-3">
						<div
							class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[#6b62f2]/10 text-xs font-semibold text-[#6b62f2]"
						>
							{item[0]}
						</div>
						<div>
							<div class="text-sm font-medium">{item[1]}</div>
							<div class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">{item[2]}</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
		<div class="mt-7 flex flex-wrap gap-3">
			<button
				class="rounded-full bg-[#6b62f2] px-6 py-3 text-sm font-medium text-white transition hover:bg-[#5a52dc]"
				on:click={() => dispatch('begin')}>Construire mon AgentOS</button
			>
			{#if alreadyDone}
				<button
					class="rounded-full border border-gray-200 bg-white px-6 py-3 text-sm font-medium dark:border-gray-800 dark:bg-[#161616]"
					on:click={() => dispatch('memory')}>Voir ma mémoire</button
				>
			{/if}
		</div>
	</div>
</section>
