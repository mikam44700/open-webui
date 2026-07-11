<script lang="ts">
	// Coquille du parcours d'onboarding : orchestre les étapes, TOUJOURS skippable (non bloquant).
	// V1 en cours de construction : étape 0 (accueil Mike). Les étapes suivantes viendront s'ajouter :
	// brancher son modèle (BYO-LLM), connecter son espace de travail (Google/Microsoft), crawl du site,
	// validation du contexte, enrichir Adam (documents). Chaque étape restera skippable.
	import { createEventDispatcher } from 'svelte';
	import WelcomeStep from './WelcomeStep.svelte';

	const dispatch = createEventDispatcher();

	type Step = 'welcome';
	let step: Step = 'welcome';

	const skip = () => dispatch('skip'); // « Plus tard » → on ferme, reprise possible via la checklist
	const next = () => {
		// TODO(Slice C+) : enchaîner vers l'étape « brancher ton modèle » puis le crawl du site.
		// Pour l'instant, l'accueil clôt le parcours (les étapes suivantes s'ajoutent ensuite).
		dispatch('done');
	};
</script>

<div class="h-full w-full overflow-y-auto">
	{#if step === 'welcome'}
		<WelcomeStep on:next={next} on:skip={skip} />
	{/if}
</div>
