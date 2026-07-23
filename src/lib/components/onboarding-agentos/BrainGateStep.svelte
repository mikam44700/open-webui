<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let checking = false;
	export let error = '';

	const dispatch = createEventDispatcher();
</script>

<section class="m-auto w-full max-w-3xl py-10">
	<div
		class="grid items-center gap-6 rounded-[2rem] border border-black/6 bg-white p-6 dark:border-white/8 dark:bg-[#161616] md:grid-cols-[1fr_auto] md:p-9"
	>
		<div>
			<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
				Le cerveau de LunarIA
			</div>
			<h1 class="mt-3 text-3xl font-medium tracking-[-0.03em]">
				Luna a besoin d’un modèle IA actif.
			</h1>
			<p class="mt-4 text-sm leading-6 text-gray-500 dark:text-gray-400">
				C’est lui qui lui permet de comprendre votre site, vos réponses et vos documents. Une fois
				connecté, revenez ici : votre progression sera conservée.
			</p>
			{#if error}
				<div
					class="mt-4 rounded-2xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/25 dark:text-amber-200"
				>
					{error}
				</div>
			{/if}
			<div class="mt-6 flex flex-wrap gap-3">
				<a
					href="/hermes?tab=providers"
					class="rounded-full bg-[#6b62f2] px-5 py-2.5 text-sm font-medium text-white"
				>
					Connecter le cerveau IA
				</a>
				<button
					class="rounded-full border border-gray-200 px-5 py-2.5 text-sm font-medium disabled:opacity-50 dark:border-gray-700"
					disabled={checking}
					on:click={() => dispatch('check')}
				>
					{checking ? 'Vérification…' : 'Vérifier la connexion'}
				</button>
			</div>
		</div>
		<div
			class="mx-auto flex size-28 items-center justify-center rounded-[2rem] bg-[#6b62f2]/10 text-5xl"
		>
			✦
		</div>
	</div>
</section>
