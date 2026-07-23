<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type {
		EvidenceFact,
		OnboardingDocument,
		WorkflowProposal
	} from '$lib/onboarding-agentos/types';

	export let companyName = '';
	export let facts: EvidenceFact[] = [];
	export let documents: OnboardingDocument[] = [];
	export let workflow: WorkflowProposal | null = null;
	export let integrationNames: string[] = [];

	const dispatch = createEventDispatcher();

	$: confirmedFacts = facts.filter(
		(fact) => fact.status === 'confirme' || fact.status === 'corrige'
	).length;
	$: publicSources = new Set(facts.map((fact) => fact.sourceUrl).filter(Boolean)).size;
	$: indexedDocuments = documents.filter((document) => document.status === 'done').length;
</script>

<section class="m-auto w-full max-w-5xl py-10">
	<div class="text-center">
		<img
			src="/static/agents/luna.png"
			alt="Luna"
			class="mx-auto size-20 rounded-[1.75rem] object-cover shadow-sm"
		/>
		<div class="mt-6 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-600">
			Votre fondation AgentOS est prête
		</div>
		<h1 class="mx-auto mt-3 max-w-4xl text-3xl font-medium tracking-[-0.03em] md:text-5xl">
			Luna connaît maintenant {companyName || 'votre entreprise'} — et peut le prouver.
		</h1>
		<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
			La Carte ci-dessous est enregistrée dans votre mémoire privée. Rien ne sera exécuté sans le
			chantier et la validation humaine prévus.
		</p>
	</div>

	<div class="mt-9 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
		{#each [[String(confirmedFacts), 'faits confirmés', 'Relus ou fournis directement'], [String(publicSources), 'sources publiques', 'Rattachées aux affirmations'], [String(indexedDocuments), 'documents internes', 'Réellement indexés'], [workflow ? '1' : '0', 'workflow prioritaire', workflow ? workflow.title : 'À choisir plus tard']] as proof}
			<div
				class="rounded-2xl border border-black/6 bg-white p-5 dark:border-white/8 dark:bg-[#161616]"
			>
				<div class="text-3xl font-medium tracking-[-0.04em]">{proof[0]}</div>
				<div class="mt-2 text-sm font-medium">{proof[1]}</div>
				<div class="mt-1 text-xs leading-5 text-gray-400">{proof[2]}</div>
			</div>
		{/each}
	</div>

	{#if workflow}
		<div class="mt-4 rounded-[2rem] border border-[#6b62f2]/20 bg-[#6b62f2]/5 p-5 md:p-7">
			<div
				class="text-xs font-semibold uppercase tracking-[0.14em] text-[#5b52dd] dark:text-[#aaa4ff]"
			>
				Première boucle préparée
			</div>
			<div class="mt-2 text-xl font-medium">{workflow.title}</div>
			<div class="mt-2 text-sm text-gray-500 dark:text-gray-400">{workflow.impact}</div>
			<div class="mt-4 text-xs">
				<span class="font-medium">Porte humaine :</span>
				{workflow.humanGate}
			</div>
		</div>
	{/if}

	<div class="mt-7 flex flex-col items-stretch justify-center gap-3 sm:flex-row">
		<a
			href="/memoire"
			class="rounded-full border border-gray-200 bg-white px-6 py-3 text-center text-sm font-medium dark:border-gray-700 dark:bg-[#161616]"
		>
			Voir la mémoire enregistrée
		</a>
		<a
			href="/hermes?tab=integrations"
			class="rounded-full border border-gray-200 bg-white px-6 py-3 text-center text-sm font-medium dark:border-gray-700 dark:bg-[#161616]"
		>
			{integrationNames.length
				? `Connecter ${integrationNames.length} outil(s)`
				: 'Connecter mes outils'}
		</a>
		<button
			class="rounded-full bg-[#6b62f2] px-7 py-3 text-sm font-medium text-white"
			on:click={() => dispatch('enter')}>Entrer dans LunarIA</button
		>
	</div>
</section>
