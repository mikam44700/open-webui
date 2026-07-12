<script lang="ts">
	// Étape « Voici ce que j'ai compris » — Adam restitue la fiche entreprise (10 blocs, 3 sections)
	// tirée du crawl MULTI-PAGES ; le dirigeant VALIDE ou CORRIGE. Rien n'est écrit avant confirmation
	// (FR-006). À la validation : fusion dans le profil (USER.md, propagé à tous les agents) + dépôt
	// daté dans le coffre. Champs vides assumés (jamais inventés, D27). Badge « ✎ IA » sur chaque
	// champ pré-rempli, retiré dès que le dirigeant le corrige.
	import { createEventDispatcher, getContext } from 'svelte';
	import {
		formatContextForProfile,
		isContextEmpty,
		EMPTY_CONTEXT,
		type CompanyContext
	} from '$lib/onboarding/companySynthesis';
	import { saveProfile, writeInboxNote, initMemoryVault } from '$lib/apis/memory';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let context: CompanyContext = { ...EMPTY_CONTEXT };
	export let crawlStatus: 'reussi' | 'partiel' | 'echec' | null = null;
	export let pagesRead = 0;

	// Édition locale : les listes (services, vocabulaire, preuves) s'éditent en texte (un par ligne).
	let form: Record<string, string> = {
		nomEntreprise: context.nomEntreprise,
		secteur: context.secteur,
		coordonnees: context.coordonnees,
		offre: context.offre,
		servicesText: context.services.join('\n'),
		tonDeMarque: context.tonDeMarque,
		vocabulaireText: context.vocabulaire.join('\n'),
		clienteleCible: context.clienteleCible,
		problemesResolus: context.problemesResolus,
		preuveSocialeText: context.preuveSociale.join('\n')
	};
	// Valeurs de référence figées : servent à marquer « Généré par l'IA » tant que non modifié.
	const seeds: Record<string, string> = Object.fromEntries(
		Object.entries(form).map(([k, v]) => [k, v.trim()])
	);
	const anyAi = Object.values(seeds).some(Boolean);
	// Un champ est « issu de l'IA » s'il était pré-rempli ET n'a pas encore été modifié.
	const fromAi = (key: string): boolean => !!seeds[key] && (form[key] ?? '').trim() === seeds[key];

	type Field = { key: string; label: string; ph: string; area?: boolean; rows?: number };
	type Section = { title: string; icon: string; fields: Field[] };

	const SECTIONS: Section[] = [
		{
			title: 'Votre identité',
			icon: '🏢',
			fields: [
				{ key: 'nomEntreprise', label: 'Nom de l’entreprise', ph: 'Le nom de votre entreprise' },
				{ key: 'secteur', label: 'Secteur d’activité', ph: 'Votre métier, votre secteur' },
				{
					key: 'coordonnees',
					label: 'Coordonnées',
					ph: 'Téléphone, e-mail, adresse, horaires…',
					area: true,
					rows: 2
				}
			]
		},
		{
			title: 'Votre offre',
			icon: '💡',
			fields: [
				{ key: 'offre', label: 'Votre offre', ph: 'Ce que vous vendez, en une phrase', area: true, rows: 3 },
				{ key: 'servicesText', label: 'Vos services', ph: 'Un service par ligne', area: true, rows: 5 },
				{ key: 'tonDeMarque', label: 'Votre ton de marque', ph: 'Ex. chaleureux, direct' },
				{
					key: 'vocabulaireText',
					label: 'Votre vocabulaire maison',
					ph: 'Vos mots et expressions, un par ligne',
					area: true,
					rows: 3
				}
			]
		},
		{
			title: 'Votre marché',
			icon: '🎯',
			fields: [
				{
					key: 'clienteleCible',
					label: 'Votre clientèle',
					ph: 'À qui vous vous adressez',
					area: true,
					rows: 2
				},
				{
					key: 'problemesResolus',
					label: 'Les problèmes que vous résolvez',
					ph: 'Les besoins de vos clients que vous adressez',
					area: true,
					rows: 3
				},
				{
					key: 'preuveSocialeText',
					label: 'Vos preuves & réassurance',
					ph: 'Clients, avis, chiffres clés — un par ligne',
					area: true,
					rows: 3
				}
			]
		}
	];

	// Auto-ajustement de hauteur : chaque zone grandit pour montrer TOUT son contenu (pas de petit
	// cadre qui scrolle). Plafonné par max-height côté CSS (scroll seulement au-delà).
	const autogrow = (node: HTMLTextAreaElement) => {
		const resize = () => {
			node.style.height = 'auto';
			node.style.height = `${node.scrollHeight + 2}px`;
		};
		resize();
		requestAnimationFrame(resize); // re-mesure après le 1er paint (contenu pré-rempli)
		node.addEventListener('input', resize);
		return { destroy: () => node.removeEventListener('input', resize) };
	};

	// Champs encore vides (pour la note honnête + les puces « à compléter »). Réactif : suit les
	// éditions — chaque puce disparaît dès que le dirigeant remplit le champ. Honnêteté D27 : on
	// assume que le crawl ne trouve pas toujours tout et on invite à compléter, sans rien inventer.
	$: emptyCount = SECTIONS.flatMap((s) => s.fields).filter((f) => !(form[f.key] ?? '').trim()).length;

	let saving = false;
	let errorMessage = '';

	const toList = (s: string): string[] =>
		s
			.split('\n')
			.map((x) => x.trim())
			.filter(Boolean);

	const collect = (): CompanyContext => ({
		nomEntreprise: form.nomEntreprise.trim(),
		secteur: form.secteur.trim(),
		coordonnees: form.coordonnees.trim(),
		offre: form.offre.trim(),
		services: toList(form.servicesText),
		tonDeMarque: form.tonDeMarque.trim(),
		vocabulaire: toList(form.vocabulaireText),
		clienteleCible: form.clienteleCible.trim(),
		problemesResolus: form.problemesResolus.trim(),
		preuveSociale: toList(form.preuveSocialeText)
	});

	const validate = async () => {
		const ctx = collect();
		if (isContextEmpty(ctx)) {
			errorMessage = $i18n.t('Ajoutez au moins un élément avant de valider.');
			return;
		}
		const profileText = formatContextForProfile(ctx);
		errorMessage = '';
		saving = true;
		try {
			// Profil = source de vérité lue par tous les agents (l'écriture propage aux profils).
			await saveProfile(localStorage.token, profileText);
			// Trace datée dans le coffre (best-effort : n'empêche pas la validation si le coffre manque).
			try {
				await initMemoryVault(localStorage.token);
				const date = new Date().toLocaleDateString('fr-FR');
				await writeInboxNote(localStorage.token, `Contexte entreprise (${date})`, profileText);
			} catch (e) {
				console.error(e);
			}
			dispatch('done', { context: ctx });
		} catch (err: any) {
			const code = err?.error?.code ?? err?.code;
			errorMessage =
				code === 'too_long'
					? $i18n.t('C’est un peu long — raccourcissez un peu pour enregistrer.')
					: $i18n.t('L’enregistrement a échoué. Réessayez dans un instant.');
		} finally {
			saving = false;
		}
	};
</script>

<div class="min-h-[80vh] w-full flex items-center justify-center p-4 sm:p-8">
	<div
		class="relative w-full max-w-4xl overflow-hidden rounded-3xl bg-white/80 dark:bg-gray-900/60 ring-1 ring-inset ring-gray-900/10 dark:ring-white/10"
	>
		<div class="relative z-20 px-6 py-8 sm:px-10 sm:py-10">
			<div
				class="text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-700/90 dark:text-amber-300/90"
			>
				{$i18n.t('Voici ce que j’ai compris')}
			</div>
			<h1 class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
				{$i18n.t('C’est bien ça ?')}
			</h1>
			<p class="mt-2 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300">
				{$i18n.t('Corrigez librement — rien n’est enregistré tant que vous n’avez pas validé.')}
			</p>

			{#if anyAi}
				<div
					class="mt-4 flex items-center gap-2 text-[13px] rounded-lg bg-amber-50/80 dark:bg-amber-900/15 text-amber-800 dark:text-amber-200 px-3 py-2 ring-1 ring-inset ring-amber-500/20"
				>
					<span class="font-semibold">✎ {$i18n.t('Généré par l’IA')}</span>
					<span class="text-amber-700/80 dark:text-amber-200/70">
						{#if pagesRead > 1}
							{$i18n.t('à partir de {{n}} pages de votre site', { n: pagesRead })} — {$i18n.t('vérifiez et corrigez si besoin.')}
						{:else}
							{$i18n.t('à partir de votre site — vérifiez et corrigez si besoin.')}
						{/if}
					</span>
				</div>
			{/if}

			{#if crawlStatus === 'partiel'}
				<div
					class="mt-4 text-[13px] rounded-lg bg-amber-100/70 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 px-3 py-2 ring-1 ring-inset ring-amber-500/20"
				>
					{$i18n.t('Le site n’a livré qu’une partie de son contenu — complétez si besoin.')}
				</div>
			{/if}

			{#if emptyCount > 0}
				<p class="mt-3 text-[13px] leading-relaxed text-gray-500 dark:text-gray-400">
					{$i18n.t(
						'Je n’ai pas forcément tout trouvé sur votre site — les champs marqués « à compléter » ci-dessous, ajoutez-les en un mot si vous le souhaitez.'
					)}
				</p>
			{/if}

			{#snippet aiTag(show: boolean)}
				{#if show}
					<span
						class="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300 bg-amber-100/70 dark:bg-amber-900/25 px-1.5 py-0.5 rounded"
						title={$i18n.t('Pré-rempli par l’IA — modifiez pour valider vous-même')}>✎ {$i18n.t('IA')}</span
					>
				{/if}
			{/snippet}

			<!-- Puce honnête miroir du « ✎ IA » : le crawl n'a pas trouvé ce champ → on le dit et on invite
			     à le compléter (jamais d'invention, D27). Disparaît dès que le dirigeant le renseigne. -->
			{#snippet todoTag(show: boolean)}
				{#if show}
					<span
						class="inline-flex items-center text-[10px] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-white/5 px-1.5 py-0.5 rounded"
						title={$i18n.t('Je n’ai pas trouvé cette info sur votre site — ajoutez-la si vous le souhaitez')}
						>{$i18n.t('à compléter')}</span
					>
				{/if}
			{/snippet}

			<div class="mt-6 flex flex-col gap-7 text-left">
				{#each SECTIONS as section (section.title)}
					<div>
						<div
							class="text-[12px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2"
						>
							<span aria-hidden="true">{section.icon}</span>
							{$i18n.t(section.title)}
						</div>
						<div class="grid grid-cols-1 gap-4">
							{#each section.fields as field (field.key)}
								<label class="block">
									<span
										class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200"
										>{$i18n.t(field.label)}{@render aiTag(fromAi(field.key))}{@render todoTag(
											!(form[field.key] ?? '').trim()
										)}</span
									>
									{#if field.area}
										<textarea
											bind:value={form[field.key]}
											rows={field.rows ?? 2}
											use:autogrow
											placeholder={$i18n.t(field.ph)}
											class="mt-1 w-full px-3 py-2 rounded-lg bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 focus:outline-none focus:ring-2 focus:ring-amber-400/60 resize-y leading-relaxed overflow-hidden max-h-[28rem]"
										></textarea>
									{:else}
										<input
											bind:value={form[field.key]}
											placeholder={$i18n.t(field.ph)}
											class="mt-1 w-full px-3 py-2 rounded-lg bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
										/>
									{/if}
								</label>
							{/each}
						</div>
					</div>
				{/each}
			</div>

			{#if errorMessage}
				<p class="mt-4 text-sm text-red-600 dark:text-red-400">{errorMessage}</p>
			{/if}

			<div class="mt-8 flex flex-wrap items-center gap-3">
				<button
					disabled={saving}
					class="text-sm font-medium px-6 py-3 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
					on:click={validate}
				>
					{saving ? $i18n.t('Enregistrement…') : $i18n.t('Valider')}
				</button>
				<button
					disabled={saving}
					class="text-sm font-medium px-5 py-3 rounded-xl bg-white/70 dark:bg-white/10 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-900/10 dark:ring-white/15"
					on:click={() => dispatch('skip')}
				>
					{$i18n.t('Plus tard')}
				</button>
			</div>
		</div>
	</div>
</div>
