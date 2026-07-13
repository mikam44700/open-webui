<script lang="ts">
	// Mini-interview : Mike pose, UNE question par écran, ce que le site ne dit jamais (qui dirige,
	// comment il travaille, ses priorités). Chips pour le catégorisable, champ libre limité, tout
	// skippable sauf le prénom, progression visible, anti-paralysie. Réponses remontées au parent
	// (persistées avec la fiche entreprise). Cf. interview.ts (logique + séquence).
	import { createEventDispatcher, getContext } from 'svelte';
	import { buildQuestions, type Answers, type Question } from '$lib/onboarding/interview';
	import { faceFromImage } from '$lib/components/agents/avatars';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Le crawl a-t-il déjà rempli la fiche ? → interview courte (compléments) vs complète (sans site).
	export let hasSite = true;
	// Réponses déjà données (ex. retour depuis l'étape Adam) : on les réaffiche et on reprend à la
	// dernière question plutôt que de repartir de zéro. Vide au premier passage.
	export let initialAnswers: Answers = {};

	const questions: Question[] = buildQuestions(hasSite);
	let answers: Answers = { ...initialAnswers };
	let idx = Object.keys(initialAnswers).length > 0 ? questions.length - 1 : 0;

	let mikeError = false;
	// Gros plan visage cadré pour le cercle (MÊME source que le chat/AgentSelector via VisageAvatars),
	// repli sur le portrait buste si le visage manque — cohérence de l'identité de Mike partout.
	const mikeBody = '/assets/agents/mike.webp';
	const mikeImage = faceFromImage(mikeBody) ?? mikeBody;

	$: q = questions[idx];
	$: total = questions.length;
	$: isLast = idx === total - 1;
	// Valeur courante (texte) ou sélection (chips).
	$: textValue = typeof answers[q.key] === 'string' ? (answers[q.key] as string) : '';
	$: multiValue = Array.isArray(answers[q.key]) ? (answers[q.key] as string[]) : [];
	// Champ « Précisez… » : affiché quand l'option « Autre » de la question est sélectionnée.
	// Stocké dans une clé compagnon `${key}Autre` ; le profil final la substitue à « Autre ».
	$: otherKey = `${q.key}Autre`;
	$: otherText = typeof answers[otherKey] === 'string' ? (answers[otherKey] as string) : '';
	$: showOther =
		(q.kind === 'chips' || q.kind === 'chipsMulti') &&
		!!q.otherOption &&
		(q.kind === 'chips' ? textValue === q.otherOption : multiValue.includes(q.otherOption));
	$: otherPlaceholder =
		(q.kind === 'chips' || q.kind === 'chipsMulti') && q.otherPlaceholder ? q.otherPlaceholder : 'Précisez';
	const setOther = (v: string) => (answers = { ...answers, [otherKey]: v });
	// Le prénom est la seule réponse requise pour avancer.
	$: canNext = q.optional || (typeof answers[q.key] === 'string' && (answers[q.key] as string).trim() !== '');

	const setText = (v: string) => (answers = { ...answers, [q.key]: v });
	const pickChip = (opt: string) => (answers = { ...answers, [q.key]: opt });
	const toggleChip = (opt: string) => {
		const cur = multiValue;
		const next = cur.includes(opt) ? cur.filter((x) => x !== opt) : [...cur, opt];
		answers = { ...answers, [q.key]: next };
	};

	const next = () => {
		if (isLast) {
			dispatch('done', { answers });
			return;
		}
		idx += 1;
	};
	const skipQuestion = () => {
		if (isLast) {
			dispatch('done', { answers });
			return;
		}
		idx += 1;
	};
	// Retour : entre questions, ou vers l'étape précédente (site / fiche) si on est à la 1re question.
	const back = () => {
		if (idx > 0) idx -= 1;
		else dispatch('back');
	};
</script>

<div class="flex flex-col min-h-[80vh] w-full">
	<!-- Progression fine des questions (le « Plus tard » global vit dans le shell). -->
	<div class="flex-none w-full max-w-2xl mx-auto px-5 pt-2">
		<div class="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400 dark:text-gray-500 mb-3">
			{$i18n.t('Question')} {idx + 1} {$i18n.t('sur')} {total}
		</div>
		<div class="flex gap-1.5">
			{#each questions as _, i}
				<div class="h-[5px] flex-1 rounded-full bg-gray-200 dark:bg-white/10 overflow-hidden">
					<div
						class="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 origin-left transition-transform duration-500 ease-out"
						style="transform: scaleX({i < idx ? 1 : i === idx ? 0.5 : 0});"
					></div>
				</div>
			{/each}
		</div>
	</div>

	<!-- Question courante -->
	<div class="flex-1 w-full flex items-center justify-center p-4 sm:p-8">
		<div class="w-full max-w-2xl">
			<div class="flex items-center gap-3">
				{#if !mikeError}
					<img
						src={mikeImage}
						alt="Mike"
						on:error={(e) => {
							const el = e.currentTarget;
							if (!el.dataset.triedBody) {
								el.dataset.triedBody = '1';
								el.src = mikeBody;
							} else {
								mikeError = true;
							}
						}}
						class="h-11 w-11 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15 bg-amber-100 dark:bg-amber-900/20"
					/>
				{/if}
				<div class="text-[13px] text-gray-500 dark:text-gray-400">
					{#if idx === 0}
						{$i18n.t('Faisons connaissance — ça prend moins de 2 minutes.')}
					{:else}
						{$i18n.t('Encore quelques questions et c’est bon.')}
					{/if}
				</div>
			</div>

			<h1 class="mt-5 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
				{$i18n.t(q.title)}
			</h1>
			{#if q.kind === 'chips' && q.hint}
				<p class="mt-2 text-[15px] text-gray-500 dark:text-gray-400">{$i18n.t(q.hint)}</p>
			{/if}

			<div class="mt-6">
				{#if q.kind === 'text'}
					<input
						type="text"
						value={textValue}
						on:input={(e) => setText((e.currentTarget as HTMLInputElement).value)}
						placeholder={$i18n.t(q.placeholder)}
						class="w-full px-4 py-3 rounded-xl bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
					/>
				{:else if q.kind === 'textarea'}
					<textarea
						value={textValue}
						on:input={(e) => setText((e.currentTarget as HTMLTextAreaElement).value)}
						rows="3"
						placeholder={$i18n.t(q.placeholder)}
						class="w-full px-4 py-3 rounded-xl bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60 resize-y leading-relaxed"
					></textarea>
				{:else if q.kind === 'chips' && q.optionHints}
					<!-- Choix important à expliciter : cartes (libellé + explication concrète). -->
					<div class="flex flex-col gap-2.5">
						{#each q.options as opt (opt)}
							<button
								type="button"
								on:click={() => pickChip(opt)}
								class="text-left px-4 py-3 rounded-xl ring-1 ring-inset transition {textValue === opt
									? 'bg-amber-500/10 ring-amber-500'
									: 'bg-white/70 dark:bg-white/5 ring-gray-900/10 dark:ring-white/15 hover:ring-amber-400/60'}"
							>
								<span class="flex items-center gap-2.5 text-sm font-semibold text-gray-900 dark:text-white">
									<span
										class="inline-flex h-4 w-4 flex-none rounded-full ring-1 ring-inset {textValue === opt
											? 'bg-amber-500 ring-amber-500'
											: 'ring-gray-400 dark:ring-white/30'}"
									></span>
									{$i18n.t(opt)}
								</span>
								<span class="mt-1 block pl-[26px] text-[13px] text-gray-500 dark:text-gray-400">
									{$i18n.t(q.optionHints?.[opt] ?? '')}
								</span>
							</button>
						{/each}
					</div>
				{:else if q.kind === 'chips'}
					<div class="flex flex-wrap gap-2">
						{#each q.options as opt (opt)}
							<button
								type="button"
								on:click={() => pickChip(opt)}
								class="text-sm px-4 py-2 rounded-full ring-1 ring-inset transition {textValue === opt
									? 'bg-amber-500 text-amber-950 ring-amber-500 font-semibold'
									: 'bg-white/70 dark:bg-white/5 text-gray-700 dark:text-gray-200 ring-gray-900/10 dark:ring-white/15 hover:ring-amber-400/60'}"
							>
								{$i18n.t(opt)}
							</button>
						{/each}
					</div>
				{:else if q.kind === 'chipsMulti'}
					<div class="flex flex-wrap gap-2">
						{#each q.options as opt (opt)}
							<button
								type="button"
								on:click={() => toggleChip(opt)}
								class="text-sm px-4 py-2 rounded-full ring-1 ring-inset transition {multiValue.includes(opt)
									? 'bg-amber-500 text-amber-950 ring-amber-500 font-semibold'
									: 'bg-white/70 dark:bg-white/5 text-gray-700 dark:text-gray-200 ring-gray-900/10 dark:ring-white/15 hover:ring-amber-400/60'}"
							>
								{multiValue.includes(opt) ? '✓ ' : ''}{$i18n.t(opt)}
							</button>
						{/each}
					</div>
				{/if}

				<!-- Champ libre de précision quand « Autre » est sélectionné (rôle, outils…). -->
				{#if showOther}
					<input
						type="text"
						value={otherText}
						on:input={(e) => setOther((e.currentTarget as HTMLInputElement).value)}
						placeholder={$i18n.t(otherPlaceholder)}
						class="mt-3 w-full px-4 py-3 rounded-xl bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
					/>
				{/if}
			</div>

			<!-- Navigation -->
			<div class="mt-8 flex items-center justify-between gap-3">
				<button
					class="text-sm font-medium px-4 py-2 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
					on:click={back}
				>
					← {$i18n.t('Retour')}
				</button>
				<div class="flex items-center gap-3">
					{#if q.optional}
						<button
							class="text-sm font-medium px-4 py-2 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
							on:click={skipQuestion}
						>
							{$i18n.t('Passer')}
						</button>
					{/if}
					<button
						class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 disabled:opacity-40"
						on:click={next}
						disabled={!canNext}
					>
						{isLast ? $i18n.t('Terminer') : $i18n.t('Suivant')} →
					</button>
				</div>
			</div>
			{#if !q.optional}
				<p class="mt-3 text-[13px] text-gray-400 dark:text-gray-500">
					{$i18n.t('Pas de bonne ou mauvaise réponse — on pourra tout modifier plus tard.')}
				</p>
			{/if}
		</div>
	</div>
</div>
