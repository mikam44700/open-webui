<script lang="ts">
	// Le tableau de bord du travail (SPEC-kanban-taches, palier 1 : lecture + actions sûres).
	// Les tâches viennent du moteur Hermes via le router /api/v1/kanban — aucune écriture
	// directe en base, aucun verbe destructif exposé.
	import { onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getBoard,
		createTask,
		moveTask,
		getTask,
		type TableauKanban,
		type TacheKanban,
		type DetailTacheKanban
	} from '$lib/apis/kanban';
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	let tableau: TableauKanban | null = null;
	let erreur: string | null = null;

	// Formulaire de création (titre + précisions + priorité)
	let creationOuverte = false;
	let nouveauTitre = '';
	let nouvelleDescription = '';
	let nouvellePriorite: 'urgent' | 'eleve' | 'normal' | 'bas' = 'normal';
	let enregistrement = false;

	// Panneau de détail (manque n°1 de l'audit V1) : ouvert au clic sur une carte
	let detail: DetailTacheKanban | null = null;
	let detailEnCours = false;

	// Rafraîchissement automatique : le tableau vit sans recharger la page (recette V1, 8 s).
	let minuteur: ReturnType<typeof setInterval> | null = null;
	// Un échec isolé ne doit pas effacer un tableau déjà affiché (résilience reprise de la V1).
	let echecsConsecutifs = 0;
	const SEUIL_ECHECS = 3;

	// Déplacements en cours, pour désactiver le bouton de la carte concernée
	let enMouvement = new Set<string>();

	// La colonne suivante dans le flux — le palier 1 fait avancer, jamais reculer.
	const SUIVANTE: Record<string, { vers: 'a_faire' | 'en_cours' | 'termine'; libelle: string }> = {
		triage: { vers: 'a_faire', libelle: 'Mettre à faire' },
		a_faire: { vers: 'en_cours', libelle: 'Démarrer' },
		en_cours: { vers: 'termine', libelle: 'Marquer terminé' }
	};

	const charger = async (silencieux = false) => {
		try {
			tableau = await getBoard(localStorage.token);
			erreur = null;
			echecsConsecutifs = 0;
		} catch (err) {
			echecsConsecutifs++;
			// Un poll de fond qui échoue une fois ne doit pas vider l'écran ; un appel
			// explicite (montage, clic) réagit tout de suite.
			if (!silencieux || echecsConsecutifs >= SEUIL_ECHECS) {
				erreur = typeof err === 'string' ? err : 'Le tableau des tâches est indisponible.';
			}
		}
	};

	const ouvrirDetail = async (id: string) => {
		detailEnCours = true;
		try {
			detail = await getTask(localStorage.token, id);
		} catch (err) {
			detail = null;
			toast.error(typeof err === 'string' ? err : 'Détail indisponible.');
		} finally {
			detailEnCours = false;
		}
	};

	const fermerDetail = () => {
		detail = null;
	};

	const tachesDe = (cle: string): TacheKanban[] =>
		(tableau?.taches ?? []).filter((t) => t.colonne === cle);

	const creer = async () => {
		const titre = nouveauTitre.trim();
		if (!titre || enregistrement) return;

		enregistrement = true;
		try {
			await createTask(
				localStorage.token,
				titre,
				nouvelleDescription.trim() || undefined,
				nouvellePriorite
			);
			nouveauTitre = '';
			nouvelleDescription = '';
			nouvellePriorite = 'normal';
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
		triage: 'bg-slate-400',
		a_faire: 'bg-sky-400',
		en_cours: 'bg-emerald-400',
		termine: 'bg-teal-400'
	};

	// Priorités : pastille + barre de couleur à gauche de la carte (recette V1, très scannable).
	const PRIORITE: Record<string, { label: string; pastille: string; barre: string }> = {
		urgent: {
			label: 'Urgent',
			pastille: 'bg-red-500/10 text-red-600 dark:text-red-400',
			barre: 'border-l-red-500'
		},
		eleve: {
			label: 'Élevé',
			pastille: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
			barre: 'border-l-amber-500'
		},
		bas: {
			label: 'Bas',
			pastille: 'bg-gray-500/10 text-gray-500 dark:text-gray-400',
			barre: 'border-l-gray-300 dark:border-l-gray-600'
		}
	};

	const heureCourte = (epoch: number | null): string => {
		if (!epoch) return '';
		return new Date(epoch * 1000).toLocaleString('fr-FR', {
			day: '2-digit',
			month: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	onMount(() => {
		charger();
		minuteur = setInterval(() => charger(true), 8000);
	});

	onDestroy(() => {
		if (minuteur) clearInterval(minuteur);
	});
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
			on:click={() => charger()}
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
				on:click={() => charger()}
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


	<!-- Colonnes V1 : lanes au fond bleuté (choix de Michael le 2026-07-20 — exception
	     assumée à la charte Dimension, c'est LA signature visuelle du tableau). -->
	<div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4 pb-8">
		{#each tableau.colonnes as colonne (colonne.cle)}
			{@const taches = tachesDe(colonne.cle)}
			<div
				class="flex flex-col min-h-[26rem] rounded-2xl border border-transparent bg-sky-50/50 dark:bg-sky-950/20 p-3"
			>
				<!-- En-tête de colonne V1 : pastille + libellé compact + compteur rond -->
				<div class="flex items-center gap-2 px-1 py-1.5">
					<span class="size-2 rounded-full {PASTILLE[colonne.cle]}"></span>
					<span class="text-xs font-semibold text-gray-600 dark:text-gray-300">{colonne.titre}</span>
					<span
						class="ml-auto min-w-5 rounded-full bg-gray-200/70 dark:bg-gray-800 px-1.5 py-0.5 text-center text-[11px] font-medium text-gray-500 dark:text-gray-400"
					>
						{taches.length}
					</span>
				</div>
				<div class="px-1 pb-2.5 text-[11px] text-gray-400 dark:text-gray-500">{colonne.aide}</div>

				{#if taches.length === 0}
					<div
						class="rounded-2xl border border-dashed border-gray-200 dark:border-white/10 px-3 py-10 text-center text-xs text-gray-400 dark:text-gray-500"
					>
						Aucune tâche
					</div>
				{:else}
					<div class="flex flex-col gap-2.5">
						{#each taches as tache (tache.id)}
							<!-- Carte cliquable : ouvre le détail (manque n°1 de l'audit V1).
							     Barre de couleur à gauche = priorité, scannable d'un coup d'œil. -->
							<div
								class="group cursor-pointer rounded-xl border border-l-4 border-gray-100 dark:border-gray-800 {tache.priorite
									? PRIORITE[tache.priorite].barre
									: 'border-l-transparent'} bg-white dark:bg-gray-900 p-2.5 shadow-sm hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-md motion-safe:transition-all motion-safe:duration-150 motion-safe:hover:-translate-y-0.5"
								role="button"
								tabindex="0"
								on:click={() => ouvrirDetail(tache.id)}
								on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && ouvrirDetail(tache.id)}
							>
								<div class="flex items-start justify-between gap-2">
									<div class="text-sm leading-snug text-gray-900 dark:text-gray-50">{tache.titre}</div>
									{#if tache.colonne === 'en_cours'}
										<!-- Point pulsant « un agent travaille dessus » (recette V1) -->
										<span class="relative mt-1 flex size-2 shrink-0" title="En cours">
											<span
												class="absolute inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-emerald-400 opacity-75"
											></span>
											<span class="relative inline-flex size-2 rounded-full bg-emerald-500"></span>
										</span>
									{/if}
								</div>
								{#if tache.description}
									<div class="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
										{tache.description}
									</div>
								{/if}

								<!-- Pied de carte V1 : pastille agent + priorité à gauche, âge à droite -->
								<div class="mt-3 flex flex-wrap items-center gap-1.5">
									{#if tache.agent}
										<span
											class="flex size-6 items-center justify-center rounded-full bg-gray-100 dark:bg-[#262626] text-[10px] font-medium text-gray-600 dark:text-gray-300"
											title={tache.agent}
										>
											{initiales(tache.agent)}
										</span>
									{/if}
									{#if tache.priorite}
										<span
											class="rounded-full px-1.5 py-0.5 text-[10px] font-medium {PRIORITE[tache.priorite]
												.pastille}"
										>
											{PRIORITE[tache.priorite].label}
										</span>
									{/if}
									{#if tache.bloquee}
										<span
											class="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700 dark:bg-amber-500/15 dark:text-amber-400"
										>
											Décision attendue
										</span>
									{/if}
									<span class="ml-auto text-[11px] text-gray-400 dark:text-gray-500">
										{age(tache.cree_le)}
									</span>
								</div>

								{#if SUIVANTE[tache.colonne]}
									<!-- Actions estompées au repos, pleines au survol (recette V1) -->
									<div class="mt-2.5 opacity-80 motion-safe:transition group-hover:opacity-100">
										<button
											class="rounded-md bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-[10px] text-gray-600 dark:text-gray-300 transition hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
											disabled={enMouvement.has(tache.id)}
											on:click|stopPropagation={() => avancer(tache)}
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

<!-- Modale « Nouvelle tâche » centrée (recette V1) -->
{#if creationOuverte}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={() => (creationOuverte = false)}
		on:keydown={(e) => e.key === 'Escape' && (creationOuverte = false)}
		role="presentation"
	>
		<div
			class="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-xl"
			on:click|stopPropagation
			on:keydown|stopPropagation
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="mb-4 text-base font-medium text-gray-900 dark:text-gray-50">Nouvelle tâche</div>
			<div class="flex flex-col gap-3">
				<input
					class="w-full rounded-lg bg-gray-50 dark:bg-gray-850 px-3 py-2 text-sm outline-hidden dark:text-gray-100"
					placeholder="Que faut-il faire ?"
					maxlength="300"
					bind:value={nouveauTitre}
					on:keydown={(e) => e.key === 'Enter' && creer()}
				/>
				<textarea
					class="w-full resize-none rounded-lg bg-gray-50 dark:bg-gray-850 px-3 py-2 text-sm outline-hidden dark:text-gray-100"
					rows="3"
					maxlength="5000"
					placeholder="Précisions (facultatif)"
					bind:value={nouvelleDescription}
				></textarea>
				<div class="flex flex-wrap items-center gap-1.5">
					<span class="mr-1 text-xs text-gray-500 dark:text-gray-400">Priorité</span>
					{#each [{ v: 'normal', l: 'Normale' }, { v: 'eleve', l: 'Élevée' }, { v: 'urgent', l: 'Urgente' }, { v: 'bas', l: 'Basse' }] as choix}
						<button
							type="button"
							class="rounded-full px-3 py-1 text-xs transition {nouvellePriorite === choix.v
								? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
								: 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-850 dark:text-gray-300 dark:hover:bg-gray-800'}"
							on:click={() => (nouvellePriorite = choix.v as typeof nouvellePriorite)}
						>
							{choix.l}
						</button>
					{/each}
				</div>
			</div>
			<div class="mt-5 flex items-center justify-end gap-2">
				<button
					class="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition hover:bg-gray-200 dark:bg-gray-850 dark:text-gray-300 dark:hover:bg-gray-800"
					on:click={() => (creationOuverte = false)}
				>
					Annuler
				</button>
				<button
					class="rounded-lg bg-black px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40 dark:bg-white dark:text-black"
					disabled={!nouveauTitre.trim() || enregistrement}
					on:click={creer}
				>
					{enregistrement ? 'Création…' : 'Créer'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Panneau de détail (tiroir latéral, recette V1) : ce qui s'est réellement passé
     sur la tâche — dernier résumé, résultat, passages d'agents, commentaires, historique. -->
{#if detail || detailEnCours}
	<div
		class="fixed inset-0 z-50 flex justify-end bg-black/40"
		on:click={fermerDetail}
		on:keydown={(e) => e.key === 'Escape' && fermerDetail()}
		role="presentation"
	>
		<div
			class="h-full w-full max-w-md overflow-y-auto bg-white dark:bg-[#161616] p-5 shadow-xl"
			on:click|stopPropagation
			on:keydown={(e) => e.key === 'Escape' && fermerDetail()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			{#if detailEnCours}
				<div class="flex justify-center py-16"><Spinner className="size-5" /></div>
			{:else if detail}
				{@const t = detail.tache}
				<div class="mb-3 flex items-start justify-between gap-2">
					<div class="text-base font-medium text-gray-900 dark:text-gray-50">{t.titre}</div>
					<button
						class="rounded-lg p-1.5 text-gray-500 transition hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={fermerDetail}
						aria-label="Fermer"
					>
						✕
					</button>
				</div>

				<div class="mb-5 flex flex-wrap items-center gap-1.5 text-xs">
					<span
						class="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-gray-600 dark:bg-[#262626] dark:text-gray-300"
					>
						<span class="size-1.5 rounded-full {PASTILLE[t.colonne]}"></span>
						{tableau?.colonnes.find((c) => c.cle === t.colonne)?.titre ?? t.colonne}
					</span>
					{#if t.priorite}
						<span class="rounded-full px-2 py-0.5 font-medium {PRIORITE[t.priorite].pastille}">
							{PRIORITE[t.priorite].label}
						</span>
					{/if}
					{#if t.agent}
						<span
							class="rounded-full bg-gray-100 px-2.5 py-0.5 text-gray-600 dark:bg-[#262626] dark:text-gray-300"
						>
							{t.agent}
						</span>
					{/if}
					{#if t.cree_le}
						<span class="text-gray-400 dark:text-gray-500">créée le {heureCourte(t.cree_le)}</span>
					{/if}
				</div>

				{#if t.description}
					<div class="mb-5">
						<div
							class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
						>
							Description
						</div>
						<div class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
							{t.description}
						</div>
					</div>
				{/if}

				{#if detail.dernier_resume}
					<div class="mb-5">
						<div
							class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
						>
							Dernier point
						</div>
						<div class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
							{detail.dernier_resume}
						</div>
					</div>
				{/if}

				{#if detail.resultat}
					<div class="mb-5">
						<div
							class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
						>
							Résultat
						</div>
						<div
							class="whitespace-pre-wrap rounded-xl bg-gray-50 p-2.5 text-sm text-gray-700 dark:bg-[#0f0f0f] dark:text-gray-300"
						>
							{detail.resultat}
						</div>
					</div>
				{/if}

				{#if detail.executions.length}
					<div class="mb-5">
						<div
							class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
						>
							Passages d'agents ({detail.executions.length})
						</div>
						<div class="flex flex-col gap-1.5">
							{#each detail.executions as ex}
								<div class="rounded-xl bg-gray-50 p-2.5 text-xs dark:bg-[#0f0f0f]">
									<div class="flex items-center gap-2">
										<span class="font-medium text-gray-700 dark:text-gray-200">
											{ex.agent ?? 'Agent non identifié'}
										</span>
										{#if ex.issue}
											<span class="text-gray-500 dark:text-gray-400">— {ex.issue}</span>
										{/if}
										{#if ex.debut}
											<span class="ml-auto text-gray-400 dark:text-gray-500">
												{heureCourte(ex.debut)}
											</span>
										{/if}
									</div>
									{#if ex.resume}
										<div class="mt-1 text-gray-500 dark:text-gray-400">{ex.resume}</div>
									{/if}
									{#if ex.erreur}
										<div class="mt-1 text-red-500 dark:text-red-400">{ex.erreur}</div>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if detail.commentaires.length}
					<div class="mb-5">
						<div
							class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
						>
							Commentaires ({detail.commentaires.length})
						</div>
						<div class="flex flex-col gap-1.5">
							{#each detail.commentaires as c}
								<div class="rounded-xl bg-gray-50 p-2.5 text-xs dark:bg-[#0f0f0f]">
									<span class="font-medium text-gray-700 dark:text-gray-200">
										{c.auteur ?? 'Anonyme'}
									</span>
									<div class="mt-0.5 text-gray-600 dark:text-gray-300">{c.texte}</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if detail.historique.length}
					<div class="mb-2">
						<div
							class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
						>
							Historique
						</div>
						<div class="flex flex-col gap-1">
							{#each [...detail.historique].reverse().slice(0, 12) as etape}
								<div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
									<span class="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-[#262626]">
										{etape.libelle}
									</span>
									{#if etape.le}
										<span class="text-gray-400 dark:text-gray-500">{heureCourte(etape.le)}</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}
