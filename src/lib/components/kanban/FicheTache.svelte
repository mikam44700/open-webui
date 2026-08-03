<script lang="ts">
	// Le detail d'une tache, et la seule action de la page : debloquer.
	//
	// Le bouton n'apparait que quand l'assistant attend vraiment une decision
	// humaine. Proposer de debloquer une tache qui attend sa dependance
	// inviterait le client a casser l'ordre de travail que l'assistant a
	// lui-meme etabli.
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { peutEtreDebloquee } from '$lib/kanban/colonnes';
	import { debloquerTache, ecrireMessageKanban, type FicheKanban } from '$lib/apis/kanban';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let fiche: FicheKanban | null = null;
	export let chargement = false;

	let reponse = '';
	let envoi = false;

	$: aVous = fiche ? peutEtreDebloquee(fiche) : false;

	const debloquer = async () => {
		if (!fiche || envoi) return;
		envoi = true;

		try {
			// Le message part d'abord : si le deblocage echoue, la reponse du
			// client reste ecrite quelque part plutot que d'etre perdue.
			const texte = reponse.trim();
			if (texte) await ecrireMessageKanban(localStorage.token, fiche.id, texte);

			const reelle = await debloquerTache(localStorage.token, fiche.id);
			reponse = '';
			// On remonte l'etat REEL rendu par le moteur, pas celui qu'on esperait.
			dispatch('debloquee', reelle);
		} catch (erreur) {
			const status = (erreur as { status?: number })?.status;
			if (status === 409) {
				// La tache a change entre-temps : on recharge et on montre la
				// realite plutot que d'insister.
				toast.error($i18n.t('Cette tâche a changé entre-temps. Le tableau est rechargé.'));
				dispatch('perime');
			} else {
				toast.error(
					(erreur as { message?: string })?.message ?? $i18n.t('Le moteur a refusé la demande.')
				);
			}
		} finally {
			envoi = false;
		}
	};
</script>

<aside
	class="flex h-full w-full flex-col gap-4 overflow-y-auto border-l border-gray-100 bg-white px-5 py-4 dark:border-gray-850 dark:bg-gray-900 sm:w-[26rem]"
>
	<div class="flex items-start justify-between gap-3">
		<h2 class="text-base font-semibold text-gray-900 dark:text-white">
			{fiche?.titre ?? $i18n.t('Tâche')}
		</h2>
		<button
			type="button"
			class="flex-none rounded-lg px-2 py-1 text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white"
			on:click={() => dispatch('fermer')}
		>
			{$i18n.t('Fermer')}
		</button>
	</div>

	{#if chargement}
		<div class="flex justify-center py-10"><Spinner className="size-5" /></div>
	{:else if !fiche}
		<p class="text-sm text-gray-500">{$i18n.t('Cette tâche n’existe plus.')}</p>
	{:else}
		{#if fiche.consigne}
			<section>
				<h3 class="mb-1 text-xs font-medium uppercase text-gray-400">{$i18n.t('Consigne')}</h3>
				<p class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">{fiche.consigne}</p>
			</section>
		{/if}

		{#if fiche.resultat}
			<section>
				<h3 class="mb-1 text-xs font-medium uppercase text-gray-400">{$i18n.t('Résultat')}</h3>
				<p class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">{fiche.resultat}</p>
			</section>
		{/if}

		{#if fiche.derniereErreur}
			<section>
				<h3 class="mb-1 text-xs font-medium uppercase text-gray-400">
					{$i18n.t('Dernière erreur')}
				</h3>
				<p class="whitespace-pre-wrap text-sm text-gray-600 dark:text-gray-400">
					{fiche.derniereErreur}
				</p>
			</section>
		{/if}

		<section>
			<h3 class="mb-2 text-xs font-medium uppercase text-gray-400">{$i18n.t('Échanges')}</h3>
			{#if fiche.messages.length > 0}
				<ul class="flex flex-col gap-2">
					{#each fiche.messages as message, index (index)}
						<li class="rounded-xl bg-gray-50 px-3 py-2 dark:bg-gray-850/60">
							{#if message.auteur}
								<div class="text-xs font-medium text-gray-500">{message.auteur}</div>
							{/if}
							<p class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
								{message.texte}
							</p>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-xs text-gray-400">{$i18n.t('Aucun échange sur cette tâche.')}</p>
			{/if}
		</section>

		{#if aVous}
			<!-- Le seul endroit ou le client peut agir. Absent partout ailleurs. -->
			<section
				class="mt-auto flex flex-col gap-2 border-t border-gray-100 pt-4 dark:border-gray-850"
			>
				<label class="text-xs font-medium text-gray-500" for="reponse-kanban">
					{$i18n.t('Votre réponse')}
				</label>
				<textarea
					id="reponse-kanban"
					class="min-h-20 w-full resize-y rounded-xl border border-gray-100 bg-transparent px-3 py-2 text-sm outline-none dark:border-gray-850"
					bind:value={reponse}
					placeholder={$i18n.t('Ce que l’assistant doit savoir pour continuer…')}
				></textarea>
				<button
					type="button"
					class="inline-flex items-center justify-center gap-2 rounded-xl bg-gray-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-black disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
					disabled={envoi}
					on:click={debloquer}
				>
					{#if envoi}<Spinner className="size-4" />{/if}
					{$i18n.t('Débloquer la tâche')}
				</button>
			</section>
		{/if}
	{/if}
</aside>
