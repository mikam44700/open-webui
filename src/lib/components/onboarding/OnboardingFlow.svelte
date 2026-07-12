<script lang="ts">
	// Coquille du parcours d'onboarding : barre de progression PERSISTANTE + orchestration des étapes.
	// TOUJOURS skippable (non bloquant). Parcours (spec 019, design validé 2026-07-12) :
	//   Bienvenue (Mike) → Modèle IA (Codex recommandé, non bloquant) → Votre entreprise (crawl +
	//   synthèse + validation) → C'est prêt (récap). L'espace de travail (Google/MS) s'insèrera ensuite.
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getModels } from '$lib/apis';
	import WelcomeStep from './WelcomeStep.svelte';
	import ModelSetupStep from './ModelSetupStep.svelte';
	import SiteCrawlStep from './SiteCrawlStep.svelte';
	import CrawlLoadingStep from './CrawlLoadingStep.svelte';
	import ContextReviewStep from './ContextReviewStep.svelte';
	import InterviewStep from './InterviewStep.svelte';
	import DoneStep from './DoneStep.svelte';
	import {
		EMPTY_CONTEXT,
		isContextEmpty,
		formatContextForProfile,
		type CompanyContext
	} from '$lib/onboarding/companySynthesis';
	import {
		formatInterviewForProfile,
		answersToContext,
		type Answers
	} from '$lib/onboarding/interview';
	import { saveProfile, writeInboxNote, initMemoryVault } from '$lib/apis/memory';
	import { crawlSite, synthesizeContext, type CrawlResult } from '$lib/apis/onboarding';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	type Step = 'welcome' | 'model' | 'site' | 'loading' | 'review' | 'interview' | 'done';
	let step: Step = 'welcome';

	// Historique de navigation : permet un vrai « Retour » qui remonte l'étape réellement
	// précédente (ex. review peut venir de site OU de la saisie manuelle → back revient à site).
	let history: Step[] = [];
	const go = (next: Step) => {
		history = [...history, step];
		step = next;
	};
	const back = () => {
		if (history.length === 0) return;
		step = history[history.length - 1];
		history = history.slice(0, -1);
	};
	// Pas de « Retour » pendant le chargement (transitoire), l'interview (navigation interne) ni l'écran final.
	$: canGoBack = history.length > 0 && step !== 'done' && step !== 'loading' && step !== 'interview';

	// Progression : 5 jalons. « site », « loading » et « review » partagent le jalon 3.
	const TOTAL = 5;
	const META: Record<Step, { index: number; label: string }> = {
		welcome: { index: 1, label: 'Bienvenue' },
		model: { index: 2, label: 'Votre modèle IA' },
		site: { index: 3, label: 'Votre entreprise' },
		loading: { index: 3, label: 'Votre entreprise' },
		review: { index: 3, label: 'Votre entreprise' },
		interview: { index: 4, label: 'Faisons connaissance' },
		done: { index: 5, label: 'C’est prêt' }
	};
	$: meta = META[step];

	// Modèle actif (pour la synthèse). Rafraîchi avant l'étape « site » : le dirigeant vient
	// peut-être de brancher son modèle à l'étape précédente.
	let model = '';
	const refreshModel = async () => {
		try {
			const res = await getModels(localStorage.token);
			const list = res?.data ?? res ?? [];
			model = list?.[0]?.id ?? '';
		} catch {
			/* la synthèse basculera en saisie manuelle */
		}
	};
	onMount(refreshModel);

	// Contexte en cours de construction + statut du crawl (bandeau honnête à la relecture).
	let context: CompanyContext = { ...EMPTY_CONTEXT };
	let crawlStatus: CrawlResult['status'] | null = null;
	// Pilotage de la page de chargement dédiée + erreur éventuelle remontée à l'étape « site ».
	let loadingPhase: 'reading' | 'thinking' = 'reading';
	let siteError = '';
	let pagesRead = 0; // nb de pages réellement lues par le crawl multi-pages (affichage honnête)

	const skip = () => dispatch('skip');
	const finish = () => dispatch('done');

	const goToSite = async () => {
		await refreshModel();
		go('site');
	};

	// Analyse du site : on bascule d'abord sur la PAGE DE CHARGEMENT dédiée (le dirigeant voit l'IA
	// travailler jusqu'à ~1 min), puis on crawle et on synthétise. Succès → validation ; échec → retour à la
	// saisie avec un message honnête (jamais d'invention). « loading » reste hors historique (le
	// « Retour » depuis la validation revient bien à « site », pas à l'écran de chargement).
	const analyze = async (e: CustomEvent<{ url: string }>) => {
		siteError = '';
		loadingPhase = 'reading';
		go('loading');

		const crawl = await crawlSite(localStorage.token, e.detail.url);
		if (crawl.status === 'echec' || !crawl.markdown.trim()) {
			siteError = crawl.message || $i18n.t('Le site n’a pas pu être lu.');
			back();
			return;
		}

		loadingPhase = 'thinking';
		const ctx = await synthesizeContext(localStorage.token, model, crawl.markdown);
		if (isContextEmpty(ctx)) {
			siteError = $i18n.t(
				'J’ai lu le site mais je n’en ai pas tiré assez d’éléments fiables. On peut les saisir ensemble.'
			);
			back();
			return;
		}

		context = ctx;
		crawlStatus = crawl.status;
		pagesRead = crawl.pages?.length ?? 1;
		step = 'review'; // remplace « loading » sans l'empiler dans l'historique
	};

	// Deux entrées vers l'interview :
	//  - « complement » (le site a été lu → review validée) : interview courte, profil dirigeant.
	//  - « full » (pas de site) : interview guidée qui REMPLIT aussi la fiche entreprise (pas de
	//    mur de champs vides) puis va directement à l'écran final.
	let interviewMode: 'full' | 'complement' = 'complement';
	let answers: Answers = {};

	// « Je n'ai pas de site internet » → interview complète guidée (elle remplace le crawl).
	const onManual = () => {
		context = { ...EMPTY_CONTEXT };
		crawlStatus = null;
		interviewMode = 'full';
		go('interview');
	};

	// Fiche validée (avec site) → interview de compléments (profil dirigeant).
	const onReviewDone = () => {
		interviewMode = 'complement';
		go('interview');
	};

	// Fin de l'interview : on persiste le profil COMBINÉ avec la fiche entreprise (saveProfile
	// remplace tout le contenu). En mode « full », les réponses forment aussi la fiche.
	const onInterviewDone = async (e: CustomEvent<{ answers: Answers }>) => {
		answers = e.detail.answers ?? {};
		if (interviewMode === 'full') context = answersToContext(answers);

		const combined = [formatContextForProfile(context), formatInterviewForProfile(answers)]
			.filter(Boolean)
			.join('\n\n');
		if (combined.trim()) {
			try {
				await saveProfile(localStorage.token, combined);
				try {
					await initMemoryVault(localStorage.token);
					const date = new Date().toLocaleDateString('fr-FR');
					await writeInboxNote(localStorage.token, `Contexte entreprise (${date})`, combined);
				} catch (err) {
					console.error(err);
				}
			} catch (err) {
				console.error(err);
			}
		}
		go('done');
	};
</script>

<!-- Overlay plein écran : l'onboarding prend TOUTE la fenêtre (recouvre la sidebar de l'app, z-50).
     Le dirigeant ne voit que le parcours au 1er login, aucune navigation parasite derrière. -->
<div
	class="fixed inset-0 z-[60] flex flex-col h-screen w-screen overflow-y-auto bg-white dark:bg-gray-900"
>
	<!-- En-tête + progression persistante -->
	<div class="flex-none w-full max-w-3xl mx-auto px-5 pt-5">
		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-2.5 font-semibold tracking-tight text-gray-900 dark:text-white">
				<span
					class="h-6 w-6 rounded-full bg-gradient-to-br from-amber-300 to-amber-600 shadow-[inset_-5px_-4px_0_-2px_rgba(0,0,0,0.25),0_0_16px_rgba(240,178,62,0.4)]"
				></span>
				LunarIA
			</div>
			<button
				class="text-[13px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-2.5 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/5 transition"
				on:click={skip}
			>
				{$i18n.t('Plus tard')}
			</button>
		</div>

		<div class="mt-4 mb-2">
			<div class="flex items-center gap-3 mb-2.5">
				{#if canGoBack}
					<button
						type="button"
						on:click={back}
						class="flex items-center gap-1 text-[12px] font-medium text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 transition"
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5">
							<path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 010 1.06L9.06 10l3.73 3.71a.75.75 0 11-1.06 1.06l-4.25-4.24a.75.75 0 010-1.06l4.25-4.24a.75.75 0 011.06 0z" clip-rule="evenodd" />
						</svg>
						{$i18n.t('Retour')}
					</button>
					<span class="h-3 w-px bg-gray-200 dark:bg-white/10"></span>
				{/if}
				<div
					class="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400 dark:text-gray-500"
				>
					{$i18n.t('Étape')} {meta.index} {$i18n.t('sur')} {TOTAL} · {$i18n.t(meta.label)}
				</div>
			</div>
			<div class="flex gap-1.5">
				{#each Array(TOTAL) as _, i}
					<div class="h-[5px] flex-1 rounded-full bg-gray-200 dark:bg-white/10 overflow-hidden">
						<div
							class="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 origin-left transition-transform duration-500 ease-out"
							style="transform: scaleX({i + 1 < meta.index ? 1 : i + 1 === meta.index ? 0.5 : 0});"
						></div>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Contenu de l'étape -->
	<div class="flex-1 w-full">
		{#if step === 'welcome'}
			<WelcomeStep on:next={() => go('model')} on:skip={skip} />
		{:else if step === 'model'}
			<ModelSetupStep on:next={goToSite} on:skip={skip} />
		{:else if step === 'site'}
			<SiteCrawlStep
				hasContext={!isContextEmpty(context)}
				error={siteError}
				on:analyze={analyze}
				on:manual={onManual}
				on:continue={() => go('review')}
				on:skip={skip}
			/>
		{:else if step === 'loading'}
			<CrawlLoadingStep phase={loadingPhase} />
		{:else if step === 'review'}
			<ContextReviewStep {context} {crawlStatus} {pagesRead} on:done={onReviewDone} on:skip={skip} />
		{:else if step === 'interview'}
			<!-- « complement » (avec site) : questions courtes de profil. « full » (sans site) :
			     interview guidée qui remplit aussi la fiche entreprise, sans mur de champs vides. -->
			<InterviewStep
				hasSite={interviewMode === 'complement'}
				on:done={onInterviewDone}
				on:back={back}
				on:skip={skip}
			/>
		{:else if step === 'done'}
			<DoneStep {context} on:done={finish} on:workspace={finish} />
		{/if}
	</div>
</div>
