<script lang="ts">
	// Le tableau de bord du travail (SPEC-kanban-taches, palier 1 : lecture + actions sûres).
	// Les tâches viennent du moteur Hermes via le router /api/v1/kanban — aucune écriture
	// directe en base, aucun verbe destructif exposé.
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getBoard,
		createTask,
		moveTask,
		type TableauKanban,
		type TacheKanban
	} from '$lib/apis/kanban';
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	let tableau: TableauKanban | null = null;
	let erreur: string | null = null;

	// Formulaire de création (volontairement minimal : titre + précisions)
	let creationOuverte = false;
	let nouveauTitre = '';
	let nouvelleDescription = '';
	let enregistrement = false;

	// Déplacements en cours, pour désactiver le bouton de la carte concernée
	let enMouvement = new Set<string>();

	// La colonne suivante dans le flux — le palier 1 fait avancer, jamais reculer.
	const SUIVANTE: Record<string, { vers: 'a_faire' | 'en_cours' | 'termine'; libelle: string }> = {
		triage: { vers: 'a_faire', libelle: 'Mettre à faire' },
		a_faire: { vers: 'en_cours', libelle: 'Démarrer' },
		en_cours: { vers: 'termine', libelle: 'Marquer terminé' }
	};

	const charger = async () => {
		try {
			tableau = await getBoard(localStorage.token);
			erreur = null;
		} catch (err) {
			erreur = typeof err === 'string' ? err : 'Le tableau des tâches est indisponible.';
		}
	};

	const tachesDe = (cle: string): TacheKanban[] =>
		(tableau?.taches ?? []).filter((t) => t.colonne === cle);

	const creer = async () => {
		const titre = nouveauTitre.trim();
		if (!titre || enregistrement) return;

		enregistrement = true;
		try {
			await createTask(localStorage.token, titre, nouvelleDescription.trim() || undefined);
			nouveauTitre = '';
			nouvelleDescription = '';
			creationOuverte = false;
			await charger();
			toast.success('Tâche créée');
		} catch (err) {
			toast.error(typeof err === 'string' ? err : "La tâche n'a pas pu être créée.");
		} finally {
			enregistrement = false;
		}
	};

	const avancer = async (tache: TacheKanban) => {
		const suite = SUIVANTE[tache.colonne];
		if (!suite || enMouvement.has(tache.id)) return;

		enMouvement = new Set(enMouvement).add(tache.id);
		try {
			await moveTask(localStorage.token, tache.id, suite.vers);
			await charger();
		} catch (err) {
			toast.error(typeof err === 'string' ? err : 'Ce déplacement a été refusé.');
		} finally {
			const suivant = new Set(enMouvement);
			suivant.delete(tache.id);
			enMouvement = suivant;
		}
	};

	// Âge de la tâche façon V1 (« 7j ») : plus parlant qu'une date pour du suivi.
	const age = (epoch: number | null): string => {
		if (!epoch) return '';
		const jours = Math.floor((Date.now() / 1000 - epoch) / 86400);
		if (jours <= 0) return "auj.";
		if (jours === 1) return '1j';
		return `${jours}j`;
	};

	// Initiales de l'agent dans la pastille ronde de la carte (recette V1).
	const initiales = (nom: string): string =>
		nom
			.split(/[\s_-]+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((mot) => mot[0].toUpperCase())
			.join('');

	// Pastille de couleur par colonne (portage V1 : repère visuel immédiat).
	const PASTILLE: Record<string, string> = {
		triage: 'bg-gray-400 dark:bg-gray-500',
		a_faire: 'bg-blue-500 dark:bg-blue-400',
		en_cours: 'bg-emerald-500 dark:bg-emerald-400',
		termine: 'bg-violet-500 dark:bg-[#6b62f2]'
	};

	onMount(charger);
</script>

<HeroBanner
	lead="Le"
	strong="tableau de bord du travail"
	sub="Suivez d'un coup d'œil ce que vos agents font : à faire, en cours, terminé."
	wrap="from-violet-200/60 via-slate-100/60 to-violet-100/40 dark:from-[#6b62f2]/25 dark:via-[#161616]/80 dark:to-[#0a0a0a]/90"
	halo1="bg-violet-300/40 dark:bg-[#6b62f2]/25"
	halo2="bg-indigo-200/30 dark:bg-[#6b62f2]/10"
/>

{#if tableau === null && erreur === null}
	<div class="flex justify-center py-16">
		<Spinner className="size-5" />
	</div>
{:else if erreur}
	<div
		class="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-5 py-16 text-center"
	>
		<div class="font-medium text-gray-900 dark:text-gray-50">Le tableau n'est pas joignable</div>
		<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{erreur}</div>
		<button
			class="mt-4 rounded-full border border-gray-200 dark:border-gray-800 px-4 py-1.5 text-sm text-gray-600 dark:text-gray-400 transition hover:bg-gray-50 dark:hover:bg-gray-850"
			on:click={charger}
		>
			Réessayer
		</button>
	</div>
{:else if tableau}
	<!-- Barre d'outils V1 : libellé du tableau à gauche, actions à droite -->
	<div class="flex items-center justify-between mb-4">
		<div
			class="rounded-full bg-white dark:bg-[#161616] border border-gray-200/80 dark:border-white/6 px-4 py-1.5 text-sm font-medium text-gray-900 dark:text-gray-50"
		>
			Mon tableau <span class="text-gray-400 dark:text-gray-500">({tableau.total})</span>
		</div>
		<div class="flex items-center gap-2">
			<button
				class="rounded-full border border-gray-200 dark:border-gray-800 px-4 py-1.5 text-sm text-gray-600 dark:text-gray-400 transition hover:bg-gray-50 dark:hover:bg-gray-850"
				on:click={charger}
			>
				Rafraîchir
			</button>
			<button
				class="inline-flex items-center gap-1.5 rounded-full bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
				on:click={() => (creationOuverte = !creationOuverte)}
			>
				<Plus className="size-3.5" strokeWidth="2.5" />
				Nouvelle tâche
			</button>
		</div>
	</div>

	{#if creationOuverte}
		<div
			class="mb-5 rounded-3xl border border-gray-200/80 dark:border-white/6 bg-white dark:bg-[#161616] p-5"
		>
			<input
				class="w-full rounded-xl bg-gray-50 dark:bg-[#0f0f0f] px-3.5 py-2.5 text-sm outline-hidden border border-transparent focus:border-violet-400/60 dark:text-gray-100"
				placeholder="Que faut-il faire ?"
				maxlength="300"
				bind:value={nouveauTitre}
				on:keydown={(e) => e.key === 'Enter' && creer()}
			/>
			<textarea
				class="mt-2 w-full resize-none rounded-xl bg-gray-50 dark:bg-[#0f0f0f] px-3.5 py-2.5 text-sm outline-hidden border border-transparent focus:border-violet-400/60 dark:text-gray-100"
				rows="2"
				maxlength="5000"
				placeholder="Précisions (facultatif)"
				bind:value={nouvelleDescription}
			></textarea>
			<div class="mt-3 flex justify-end gap-2">
				<button
					class="rounded-full px-4 py-1.5 text-sm text-gray-500 dark:text-gray-400 transition hover:bg-gray-50 dark:hover:bg-gray-850"
					on:click={() => (creationOuverte = false)}
				>
					Annuler
				</button>
				<button
					class="rounded-full bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
					disabled={!nouveauTitre.trim() || enregistrement}
					on:click={creer}
				>
					{enregistrement ? 'Création…' : 'Créer la tâche'}
				</button>
			</div>
		</div>
	{/if}

	<!-- Colonnes façon V1 : lanes séparées par un filet vertical, pastille de couleur
	     en tête, compteur en pastille ronde. -->
	<div
		class="grid grid-cols-1 gap-0 md:grid-cols-2 xl:grid-cols-4 pb-8 rounded-3xl border border-gray-200/80 dark:border-white/6 bg-white dark:bg-[#111111]/70 overflow-hidden"
	>
		{#each tableau.colonnes as colonne, i (colonne.cle)}
			{@const taches = tachesDe(colonne.cle)}
			<div
				class="flex flex-col min-h-[26rem] p-4 {i > 0
					? 'md:border-l border-gray-200/70 dark:border-white/6'
					: ''}"
			>
				<div class="flex items-center gap-2 mb-1">
					<span class="size-2 rounded-full {PASTILLE[colonne.cle]}"></span>
					<div class="text-sm font-medium text-gray-900 dark:text-gray-50">{colonne.titre}</div>
					<span
						class="ml-auto min-w-6 rounded-full bg-gray-100 dark:bg-[#1e1e1e] px-2 py-0.5 text-center text-xs text-gray-500 dark:text-gray-400"
					>
						{taches.length}
					</span>
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-3.5">{colonne.aide}</div>

				{#if taches.length === 0}
					<div
						class="rounded-2xl border border-dashed border-gray-200 dark:border-white/10 px-3 py-10 text-center text-xs text-gray-400 dark:text-gray-500"
					>
						Aucune tâche
					</div>
				{:else}
					<div class="flex flex-col gap-2.5">
						{#each taches as tache (tache.id)}
							<div
								class="rounded-2xl border border-gray-200/80 dark:border-white/6 bg-white dark:bg-[#181818] p-3.5 transition-colors hover:border-gray-300 dark:hover:border-white/15"
							>
								<div class="text-sm leading-snug text-gray-900 dark:text-gray-50">{tache.titre}</div>
								{#if tache.description}
									<div class="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
										{tache.description}
									</div>
								{/if}

								<!-- Pied de carte V1 : pastille agent à gauche, âge à droite -->
								<div class="mt-3 flex items-center gap-2">
									{#if tache.agent}
										<span
											class="flex size-6 items-center justify-center rounded-full bg-gray-100 dark:bg-[#262626] text-[10px] font-medium text-gray-600 dark:text-gray-300"
											title={tache.agent}
										>
											{initiales(tache.agent)}
										</span>
									{/if}
									{#if tache.bloquee}
										<span
											class="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] text-amber-700 dark:bg-amber-500/15 dark:text-amber-400"
										>
											Décision attendue
										</span>
									{/if}
									<span class="ml-auto text-[11px] text-gray-400 dark:text-gray-500">
										{age(tache.cree_le)}
									</span>
								</div>

								{#if SUIVANTE[tache.colonne]}
									<div class="mt-2.5">
										<button
											class="rounded-lg bg-gray-100 dark:bg-[#262626] px-2.5 py-1 text-[11px] text-gray-600 dark:text-gray-300 transition hover:bg-gray-200 dark:hover:bg-[#303030] disabled:opacity-50"
											disabled={enMouvement.has(tache.id)}
											on:click={() => avancer(tache)}
										>
											{enMouvement.has(tache.id) ? 'Déplacement…' : SUIVANTE[tache.colonne].libelle}
										</button>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}
