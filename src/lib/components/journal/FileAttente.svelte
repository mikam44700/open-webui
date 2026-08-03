<script lang="ts">
	/**
	 * Les dossiers prepares qui attendent une signature.
	 *
	 * C'est l'ecran ou se joue le produit : le moteur a fait le travail, il
	 * reste a dire oui. Le geste doit tenir en un clic, sinon la personne
	 * retourne faire la saisie a la main et l'outil ne sert plus a rien.
	 *
	 * Deux details qui comptent plus qu'ils n'en ont l'air :
	 *
	 *   - Le bouton se desactive pendant l'appel. Sans cela, un double clic
	 *     envoie deux signatures, dont la seconde part en 409 et affiche une
	 *     erreur alors que tout s'est bien passe.
	 *
	 *   - Un 409 ne s'affiche pas en rouge : il veut dire qu'un collegue a signe
	 *     entre-temps. On rafraichit, on ne culpabilise personne.
	 */
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { deciderTraitement, type Traitement } from '$lib/apis/journal';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let traitements: Traitement[] = [];

	let enCours: string | null = null;

	const sources: Record<string, string> = {
		interface: 'journal.source.interface',
		telegram: 'journal.source.telegram',
		scheduled: 'journal.source.planifie',
		api: 'journal.source.api'
	};

	const decider = async (traitement: Traitement, issue: 'ok' | 'error') => {
		if (enCours) {
			return;
		}

		enCours = traitement.id;

		try {
			await deciderTraitement(localStorage.token, traitement.id, issue);
			toast.success(
				$i18n.t(issue === 'ok' ? 'journal.signe' : 'journal.refuse', {
					reference: traitement.reference ?? ''
				})
			);
			dispatch('decide');
		} catch (erreur: any) {
			if (erreur?.statut === 409) {
				toast.info($i18n.t('journal.deja_decide'));
				dispatch('decide');
			} else {
				toast.error($i18n.t('journal.decision_impossible'));
				console.error(erreur);
			}
		} finally {
			enCours = null;
		}
	};
</script>

{#if traitements.length > 0}
	<section class="flex flex-col gap-2">
		<h2 class="text-sm font-medium text-gray-800 dark:text-gray-200">
			{$i18n.t('journal.a_signer')}
		</h2>

		<ul class="flex flex-col gap-2">
			{#each traitements as traitement (traitement.id)}
				<li
					class="flex flex-wrap items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50/60 px-4 py-3 dark:border-amber-900/40 dark:bg-amber-950/20"
				>
					<div class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-sm text-gray-900 dark:text-gray-100">
							{traitement.summary || traitement.action}
						</span>
						<span class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(sources[traitement.source] ?? 'journal.source.api')}
							{#if traitement.reference}
								· <span class="font-mono">{traitement.reference}</span>
							{/if}
						</span>
					</div>

					<div class="flex shrink-0 gap-2">
						<button
							type="button"
							class="rounded-lg bg-gray-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-black disabled:opacity-50 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
							disabled={enCours !== null}
							on:click={() => decider(traitement, 'ok')}
						>
							{$i18n.t('journal.valider')}
						</button>
						<button
							type="button"
							class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm transition hover:bg-white disabled:opacity-50 dark:border-gray-700 dark:hover:bg-gray-900"
							disabled={enCours !== null}
							on:click={() => decider(traitement, 'error')}
						>
							{$i18n.t('journal.refuser')}
						</button>
					</div>
				</li>
			{/each}
		</ul>
	</section>
{/if}
