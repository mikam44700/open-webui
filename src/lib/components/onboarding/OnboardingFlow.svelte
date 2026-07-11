<script lang="ts">
	// Coquille du parcours d'onboarding : orchestre les étapes, TOUJOURS skippable (non bloquant).
	// welcome (Mike) → site (crawl + synthèse) → review (validation + persistance) → done.
	// Les étapes « brancher son modèle » et « connecter son espace de travail » viendront s'insérer
	// ici plus tard (Slice suivante), sans casser l'ossature.
	import { createEventDispatcher, onMount } from 'svelte';
	import { getModels } from '$lib/apis';
	import WelcomeStep from './WelcomeStep.svelte';
	import SiteCrawlStep from './SiteCrawlStep.svelte';
	import ContextReviewStep from './ContextReviewStep.svelte';
	import { EMPTY_CONTEXT, type CompanyContext } from '$lib/onboarding/companySynthesis';
	import type { CrawlResult } from '$lib/apis/onboarding';

	const dispatch = createEventDispatcher();

	type Step = 'welcome' | 'site' | 'review';
	let step: Step = 'welcome';

	// Modèle actif pour la synthèse (résolu au montage ; la synthèse dégrade en manuel s'il manque).
	let model = '';
	// Contexte en cours de construction + statut du crawl (pour un bandeau honnête à la relecture).
	let context: CompanyContext = { ...EMPTY_CONTEXT };
	let crawlStatus: CrawlResult['status'] | null = null;

	onMount(async () => {
		try {
			const res = await getModels(localStorage.token);
			const list = res?.data ?? res ?? [];
			model = list?.[0]?.id ?? '';
		} catch {
			/* la synthèse basculera en saisie manuelle */
		}
	});

	const skip = () => dispatch('skip'); // « Plus tard » → on ferme, reprise possible via la checklist
	const done = () => dispatch('done');

	const onSynthesized = (e: CustomEvent<{ context: CompanyContext; crawl: CrawlResult }>) => {
		context = e.detail.context;
		crawlStatus = e.detail.crawl?.status ?? null;
		step = 'review';
	};

	const onManual = () => {
		context = { ...EMPTY_CONTEXT };
		crawlStatus = null;
		step = 'review';
	};
</script>

<div class="h-full w-full overflow-y-auto">
	{#if step === 'welcome'}
		<WelcomeStep on:next={() => (step = 'site')} on:skip={skip} />
	{:else if step === 'site'}
		<SiteCrawlStep {model} on:synthesized={onSynthesized} on:manual={onManual} on:skip={skip} />
	{:else if step === 'review'}
		<ContextReviewStep {context} {crawlStatus} on:done={done} on:skip={skip} />
	{/if}
</div>
