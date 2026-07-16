<script lang="ts">
	// Mini-interview : Mike pose ce que le site ne dit jamais (qui dirige, comment il travaille, ses
	// priorités). Regroupée en PAGES thématiques (3-4 questions) pour alléger le rythme : le dirigeant
	// remplit un petit bloc cohérent à la fois plutôt qu'un écran par question. Chips pour le
	// catégorisable, champ libre limité, tout skippable sauf le prénom. Cf. interview.ts (séquence).
	import { createEventDispatcher, getContext } from 'svelte';
	import { buildPages, type Answers, type Question, type Page } from '$lib/onboarding/interview';
	import { faceFromImage } from '$lib/components/agents/avatars';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Le crawl a-t-il déjà rempli la fiche ? → interview courte (compléments) vs complète (sans site).
	export let hasSite = true;
	// Réponses déjà données (ex. retour depuis l'étape Adam) : on les réaffiche et on reprend à la
	// dernière page plutôt que de repartir de zéro. Vide au premier passage.
	export let initialAnswers: Answers = {};

	const pages: Page[] = buildPages(hasSite);
	let answers: Answers = { ...initialAnswers };
	let pageIdx = Object.keys(initialAnswers).length > 0 ? pages.length - 1 : 0;

	let mikeError = false;
	// Gros plan visage cadré pour le cercle (MÊME source que le chat/AgentSelector via VisageAvatars),
	// repli sur le portrait buste si le visage manque — cohérence de l'identité de Mike partout.
	const mikeBody = '/assets/agents/mike.webp';
	const mikeImage = faceFromImage(mikeBody) ?? mikeBody;

	$: page = pages[pageIdx];
	$: total = pages.length;
	$: isLast = pageIdx === total - 1;

	// Accès aux réponses PAR clé (plusieurs questions coexistent sur une page). Réactif via `answers`
	// (réassigné à chaque saisie) → le template se met à jour tout seul.
	// IMPORTANT : ces lecteurs prennent `answers` en PARAMÈTRE pour que Svelte trace la dépendance quand
	// on les appelle dans le markup — sinon les chips ne se re-rendraient pas après un clic (Svelte ne
	// voit pas la lecture de `answers` cachée dans une closure).
	const valOf = (a: Answers, key: string): string =>
		typeof a[key] === 'string' ? (a[key] as string) : '';
	const multiOf = (a: Answers, key: string): string[] =>
		Array.isArray(a[key]) ? (a[key] as string[]) : [];
	const otherKeyOf = (key: string): string => `${key}Autre`;
	const otherOf = (a: Answers, key: string): string => valOf(a, otherKeyOf(key));
	// Champ « Précisez… » : visible quand l'option « Autre » de la question est sélectionnée.
	const showOtherFor = (a: Answers, q: Question): boolean =>
		(q.kind === 'chips' || q.kind === 'chipsMulti') &&
		!!q.otherOption &&
		(q.kind === 'chips' ? valOf(a, q.key) === q.otherOption : multiOf(a, q.key).includes(q.otherOption));

	const setText = (key: string, v: string) => (answers = { ...answers, [key]: v });
	const setOther = (key: string, v: string) => (answers = { ...answers, [otherKeyOf(key)]: v });
	const pickChip = (key: string, opt: string) => (answers = { ...answers, [key]: opt });
	const toggleChip = (key: string, opt: string) => {
		const cur = multiOf(answers, key);
		answers = { ...answers, [key]: cur.includes(opt) ? cur.filter((x) => x !== opt) : [...cur, opt] };
	};

	// On peut avancer quand toutes les questions REQUISES de la page sont remplies (seul le prénom l'est).
	$: canNext = page.questions.every(
		(q) => q.optional || (typeof answers[q.key] === 'string' && (answers[q.key] as string).trim() !== '')
	);
	// Y a-t-il au moins une question requise sur cette page ? (pour la note de réassurance).
	$: hasRequired = page.questions.some((q) => !q.optional);

	const next = () => {
		if (isLast) {
			dispatch('done', { answers });
			return;
		}
		pageIdx += 1;
	};
	// Retour : entre pages, ou vers l'étape précédente (site / fiche) si on est sur la 1re page.
	const back = () => {
		if (pageIdx > 0) pageIdx -= 1;
		else dispatch('back');
	};
</script>

<div class="flex flex-col min-h-[80vh] w-full">
	<!-- Progression par PAGE (le « Plus tard » global vit dans le shell). -->
	<div class="flex-none w-full max-w-2xl mx-auto px-5 pt-2">
		<div class="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400 dark:text-gray-500 mb-3">
			{$i18n.t('Étape')} {pageIdx + 1} {$i18n.t('sur')} {total}
		</div>
		<div class="flex gap-1.5">
			{#each pages as _, i}
				<div class="h-[5px] flex-1 rounded-full bg-gray-200 dark:bg-white/10 overflow-hidden">
					<div
						class="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 origin-left transition-transform duration-500 ease-out"
						style="transform: scaleX({i < pageIdx ? 1 : i === pageIdx ? 0.5 : 0});"
					></div>
				</div>
			{/each}
		</div>
	</div>

	<!-- Page de questions -->
	<div class="flex-1 w-full flex items-start justify-center p-4 pt-8 sm:p-8">
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
					{#if pageIdx === 0}
						{$i18n.t('Faisons connaissance — ça prend moins de 2 minutes.')}
					{:else}
						{$i18n.t('Encore quelques questions et c’est bon.')}
					{/if}
				</div>
			</div>

			<h1 class="mt-5 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
				{$i18n.t(page.title)}
			</h1>

			<!-- Les questions de la page, empilées. Chaque titre de question devient un label de champ. -->
			<div class="mt-6 flex flex-col gap-6">
				{#each page.questions as q (q.key)}
					<div>
						<div class="flex items-baseline gap-2 flex-wrap">
							<span class="text-sm font-semibold text-gray-800 dark:text-gray-100">{$i18n.t(q.title)}</span>
							{#if q.optional}
								<span class="text-[11px] text-gray-400 dark:text-gray-500">{$i18n.t('facultatif')}</span>
							{/if}
						</div>
						{#if q.hint}
							<p class="mt-1 text-[13px] text-gray-500 dark:text-gray-400">{$i18n.t(q.hint)}</p>
						{/if}

						<div class="mt-2.5">
							{#if q.kind === 'text'}
								<input
									type="text"
									value={valOf(answers, q.key)}
									on:input={(e) => setText(q.key, (e.currentTarget as HTMLInputElement).value)}
									placeholder={$i18n.t(q.placeholder)}
									class="w-full px-4 py-3 rounded-xl bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
								/>
							{:else if q.kind === 'textarea'}
								<textarea
									value={valOf(answers, q.key)}
									on:input={(e) => setText(q.key, (e.currentTarget as HTMLTextAreaElement).value)}
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
											on:click={() => pickChip(q.key, opt)}
											aria-pressed={valOf(answers, q.key) === opt}
											class="text-left px-4 py-3 rounded-xl ring-1 ring-inset transition {valOf(answers, q.key) === opt
												? 'bg-amber-500/10 ring-amber-500'
												: 'bg-white/70 dark:bg-white/5 ring-gray-900/10 dark:ring-white/15 hover:ring-amber-400/60'}"
										>
											<span class="flex items-center gap-2.5 text-sm font-semibold text-gray-900 dark:text-white">
												<span
													class="inline-flex h-4 w-4 flex-none rounded-full ring-1 ring-inset {valOf(answers, q.key) === opt
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
											on:click={() => pickChip(q.key, opt)}
											aria-pressed={valOf(answers, q.key) === opt}
											class="text-sm px-4 py-2 rounded-full ring-1 ring-inset transition {valOf(answers, q.key) === opt
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
											on:click={() => toggleChip(q.key, opt)}
											aria-pressed={multiOf(answers, q.key).includes(opt)}
											class="text-sm px-4 py-2 rounded-full ring-1 ring-inset transition {multiOf(answers, q.key).includes(opt)
												? 'bg-amber-500 text-amber-950 ring-amber-500 font-semibold'
												: 'bg-white/70 dark:bg-white/5 text-gray-700 dark:text-gray-200 ring-gray-900/10 dark:ring-white/15 hover:ring-amber-400/60'}"
										>
											{multiOf(answers, q.key).includes(opt) ? '✓ ' : ''}{$i18n.t(opt)}
										</button>
									{/each}
								</div>
							{/if}

							<!-- Champ libre de précision quand « Autre » est sélectionné (rôle, outils…). -->
							{#if showOtherFor(answers, q)}
								<input
									type="text"
									value={otherOf(answers, q.key)}
									on:input={(e) => setOther(q.key, (e.currentTarget as HTMLInputElement).value)}
									placeholder={$i18n.t(q.otherPlaceholder ?? 'Précisez')}
									class="mt-3 w-full px-4 py-3 rounded-xl bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
								/>
							{/if}
						</div>
					</div>
				{/each}
			</div>

			<!-- Navigation par page -->
			<div class="mt-8 flex items-center justify-between gap-3">
				<button
					class="text-sm font-medium px-4 py-2 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
					on:click={back}
				>
					← {$i18n.t('Retour')}
				</button>
				<button
					class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950 disabled:opacity-40"
					on:click={next}
					disabled={!canNext}
				>
					{isLast ? $i18n.t('Terminer') : $i18n.t('Suivant')} →
				</button>
			</div>
			<p class="mt-3 text-[13px] text-gray-400 dark:text-gray-500">
				{#if hasRequired}
					{$i18n.t('Pas de bonne ou mauvaise réponse — on pourra tout modifier plus tard.')}
				{:else}
					{$i18n.t('Répondez à ce que vous voulez, laissez le reste vide — modifiable à tout moment.')}
				{/if}
			</p>
		</div>
	</div>
</div>
