<script lang="ts">
	// Étape 2 de l'onboarding : Adam restitue « voici ce que j'ai compris de votre boîte » — le
	// dirigeant VALIDE ou CORRIGE. Rien n'est écrit avant sa confirmation (FR-006). À la validation :
	// le contexte est fusionné dans le profil (USER.md, propagé à tous les agents) + déposé, daté,
	// dans le coffre. Champs vides assumés (jamais inventés).
	import { createEventDispatcher, getContext } from 'svelte';
	import {
		formatContextForProfile,
		isContextEmpty,
		type CompanyContext
	} from '$lib/onboarding/companySynthesis';
	import { saveProfile, writeInboxNote, initMemoryVault } from '$lib/apis/memory';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Contexte à relire (issu de la synthèse, ou vide en saisie manuelle). Édité localement.
	export let context: CompanyContext = {
		offre: '',
		tonDeMarque: '',
		clienteleCible: '',
		services: []
	};
	// Statut honnête du crawl (pour un bandeau « lecture partielle » le cas échéant).
	export let crawlStatus: 'reussi' | 'partiel' | 'echec' | null = null;

	// Édition : services en texte (un par ligne), reconverti en tableau à la sauvegarde.
	let offre = context.offre;
	let clienteleCible = context.clienteleCible;
	let tonDeMarque = context.tonDeMarque;
	let servicesText = context.services.join('\n');

	let saving = false;
	let errorMessage = '';

	const collect = (): CompanyContext => ({
		offre: offre.trim(),
		tonDeMarque: tonDeMarque.trim(),
		clienteleCible: clienteleCible.trim(),
		services: servicesText
			.split('\n')
			.map((s) => s.trim())
			.filter(Boolean)
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
			// Profil = source de vérité lue par tous les agents (l'écriture propage aux profils, étape 2).
			await saveProfile(localStorage.token, profileText);
			// Trace datée dans le coffre (best-effort : n'empêche pas la validation si le coffre manque).
			try {
				await initMemoryVault(localStorage.token);
				const date = new Date().toLocaleDateString('fr-FR');
				await writeInboxNote(
					localStorage.token,
					`Contexte entreprise (${date})`,
					profileText
				);
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
		class="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-white/80 dark:bg-gray-900/60 ring-1 ring-inset ring-gray-900/10 dark:ring-white/10"
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

			{#if crawlStatus === 'partiel'}
				<div
					class="mt-4 text-[13px] rounded-lg bg-amber-100/70 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 px-3 py-2 ring-1 ring-inset ring-amber-500/20"
				>
					{$i18n.t('Le site n’a livré qu’une partie de son contenu — complétez si besoin.')}
				</div>
			{/if}

			<div class="mt-6 space-y-4 text-left">
				<label class="block">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Votre offre')}</span>
					<input
						bind:value={offre}
						placeholder={$i18n.t('Ce que vous vendez, en une phrase')}
						class="mt-1 w-full px-3 py-2 rounded-lg bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
					/>
				</label>
				<label class="block">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-200"
						>{$i18n.t('Votre clientèle')}</span
					>
					<input
						bind:value={clienteleCible}
						placeholder={$i18n.t('À qui vous vous adressez')}
						class="mt-1 w-full px-3 py-2 rounded-lg bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
					/>
				</label>
				<label class="block">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-200"
						>{$i18n.t('Votre ton de marque')}</span
					>
					<input
						bind:value={tonDeMarque}
						placeholder={$i18n.t('Ex. chaleureux, direct')}
						class="mt-1 w-full px-3 py-2 rounded-lg bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 focus:outline-none focus:ring-2 focus:ring-amber-400/60"
					/>
				</label>
				<label class="block">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-200"
						>{$i18n.t('Vos services')}</span
					>
					<textarea
						bind:value={servicesText}
						rows="3"
						placeholder={$i18n.t('Un service par ligne')}
						class="mt-1 w-full px-3 py-2 rounded-lg bg-white dark:bg-white/10 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-900/10 dark:ring-white/15 focus:outline-none focus:ring-2 focus:ring-amber-400/60 resize-y"
					></textarea>
				</label>
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
