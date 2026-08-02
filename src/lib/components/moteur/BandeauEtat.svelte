<script lang="ts">
	/**
	 * Bandeau de sante, en haut de la page Moteur — LunarIA V2.
	 *
	 * Repris d'AgentOS V1. Il repond a une seule question, en un coup d'oeil :
	 * est-ce que mon assistant fonctionne ? La couleur porte la reponse avant
	 * meme qu'on ait lu le texte — vert on est tranquille, ambre il manque
	 * quelque chose, rouge il faut agir.
	 *
	 * Le ton est volontairement rassurant et sans jargon : c'est la premiere
	 * chose que voit un dirigeant qui n'y connait rien, et souvent la seule
	 * qu'il lira.
	 */
	import type { EtatMoteur } from '$lib/apis/hermes';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let etat: EtatMoteur | null = null;
	export let chargement = false;

	/**
	 * Trois etats seulement, et jamais deux messages a la fois : un bandeau qui
	 * enumere les problemes ne se lit pas. On remonte le plus bloquant.
	 *
	 * Le moteur qui tourne sans cerveau n'est PAS « operationnel » : il ne peut
	 * repondre a rien. C'est un avertissement, pas un feu vert.
	 */
	$: joignable = Boolean(etat?.joignable);
	$: cerveauBranche = Boolean(etat?.modele_actif);

	$: sante = !joignable
		? {
				ton: 'panne',
				titre: 'Votre assistant est hors ligne',
				sous: etat?.detail ?? 'Le moteur ne répond pas pour le moment.'
			}
		: !cerveauBranche
			? {
					ton: 'attention',
					titre: 'Aucun modèle IA connecté',
					sous: 'Le moteur tourne, mais aucun cerveau ne lui est branché : il ne peut encore répondre à rien.'
				}
			: {
					ton: 'bon',
					titre: 'Votre assistant est opérationnel',
					sous: 'Le moteur tourne et répond normalement.'
				};
</script>

<div
	class="mb-5 flex items-center gap-3.5 rounded-2xl border p-4 {sante.ton === 'bon'
		? 'border-emerald-200/70 bg-gradient-to-br from-emerald-50 to-green-50/40 dark:border-emerald-900/40 dark:from-emerald-950/30 dark:to-green-950/10'
		: sante.ton === 'attention'
			? 'border-amber-200/70 bg-gradient-to-br from-amber-50 to-orange-50/40 dark:border-amber-900/40 dark:from-amber-950/30 dark:to-orange-950/10'
			: 'border-red-200/70 bg-gradient-to-br from-red-50 to-rose-50/40 dark:border-red-900/40 dark:from-red-950/30 dark:to-rose-950/10'}"
>
	{#if chargement}
		<div class="flex items-center gap-2.5 text-sm text-gray-500 dark:text-gray-400">
			<Spinner className="size-4" />
			Interrogation du moteur…
		</div>
	{:else}
		<!-- La pastille pulse uniquement quand tout va bien : un halo qui bat sur
		     une alerte rouge donnerait un sentiment d'urgence permanent. -->
		<span class="relative flex size-3 shrink-0">
			{#if sante.ton === 'bon'}
				<span
					class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60"
				></span>
			{/if}
			<span
				class="relative inline-flex size-3 rounded-full {sante.ton === 'bon'
					? 'bg-emerald-500'
					: sante.ton === 'attention'
						? 'bg-amber-500'
						: 'bg-red-500'}"
			></span>
		</span>

		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-white">{sante.titre}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">{sante.sous}</div>
		</div>

		<!-- Le cerveau actif, a droite : l'information qu'on vient verifier le
		     plus souvent apres « est-ce que ça tourne ». -->
		{#if joignable && etat?.modele_actif}
			<div class="ml-auto hidden flex-none text-right sm:block">
				<div class="text-[11px] uppercase tracking-wide text-gray-400 dark:text-gray-500">
					Cerveau actif
				</div>
				<div class="text-sm font-medium text-gray-900 dark:text-gray-50">
					{etat.modele_actif}
				</div>
				{#if etat.fournisseur_actif}
					<div class="text-[11px] text-gray-400 dark:text-gray-500">
						fourni par {etat.fournisseur_actif}
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>
