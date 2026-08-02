<script lang="ts">
	/**
	 * Onglet « Garde-fous » — LunarIA V2.
	 *
	 * Ce que l'assistant n'a PAS le droit de faire. C'est le sujet le plus
	 * vendeur de la page et le plus mal servi jusqu'ici : la premiere version
	 * affichait le JSON brut du moteur, illisible.
	 *
	 * Chaque ligne est donc ecrite en francais et dit ce que ca change pour le
	 * marchand, pas ce que ca vaut dans un fichier. Le JSON reste consultable
	 * dans le detail technique, pour qui veut verifier.
	 *
	 * Regle : rien n'est invente. Un reglage absent de la configuration du
	 * moteur n'apparait pas — mieux vaut une ligne en moins qu'une ligne fausse.
	 */
	import { onMount } from 'svelte';
	import { getGardeFous, type GardeFou } from '$lib/apis/hermes';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let regles: GardeFou[] = [];
	let chargement = true;
	let erreur: string | null = null;

	type Ligne = {
		titre: string;
		valeur: string;
		ton: 'bon' | 'attention' | 'neutre';
		explication: string;
	};

	/**
	 * Mise en mots de chaque reglage.
	 *
	 * Attention aux sens inverses : `adresses_internes` porte la valeur
	 * « autoriser les URL privees ». Faux est donc la BONNE nouvelle. Traduire
	 * mecaniquement vrai en vert aurait affiche l'inverse de la realite.
	 */
	const oui = (v: unknown) => v === true;

	const RENDU: Record<string, (valeur: any) => Ligne> = {
		autorisation_avant_action: (v) => ({
			titre: "Autorisation avant d'agir",
			valeur:
				v === 'smart'
					? 'Activée — mode intelligent'
					: v === 'always'
						? 'Activée — pour chaque action'
						: v === 'never'
							? 'Désactivée'
							: `${v}`,
			ton: v === 'never' ? 'attention' : 'bon',
			explication:
				"L'assistant demande votre accord avant les actions qui engagent quelque chose : envoyer, payer, supprimer."
		}),
		actions_automatiques: (v) => ({
			titre: 'Actions automatiques programmées',
			valeur: v === 'deny' ? 'Interdites sans validation' : v === 'allow' ? 'Autorisées' : `${v}`,
			ton: v === 'deny' ? 'bon' : 'attention',
			explication:
				"Quand une tâche se déclenche seule, la nuit par exemple, personne n'est devant l'écran pour valider. Le moteur refuse alors les actions sensibles."
		}),
		confirmation_destructive: (v) => ({
			titre: 'Confirmation avant une action irréversible',
			valeur: oui(v) ? 'Exigée' : 'Non exigée',
			ton: oui(v) ? 'bon' : 'attention',
			explication: 'Supprimer, écraser, réinitialiser : rien ne part sans un second accord.'
		}),
		arret_si_emballement: (v) => ({
			titre: "Arrêt si l'assistant s'emballe",
			valeur: oui(v) ? 'Activé' : 'Désactivé',
			ton: oui(v) ? 'bon' : 'attention',
			explication:
				"S'il répète la même action sans progresser, le moteur le stoppe net au lieu de le laisser tourner en boucle."
		}),
		plafond_recherches_web: (v) => ({
			titre: 'Recherches web par tâche',
			valeur: `${v} au maximum`,
			ton: 'neutre',
			explication: "Au-delà, la tâche s'arrête — une boucle ne peut pas consommer sans fin."
		}),
		commandes_autorisees: (v) => ({
			titre: 'Commandes système autorisées',
			valeur: v === 0 ? 'Aucune' : `${v} autorisée${v > 1 ? 's' : ''}`,
			ton: v === 0 ? 'bon' : 'neutre',
			explication:
				"La liste des commandes que l'assistant peut lancer sur la machine. Vide : il n'en lance aucune."
		}),
		analyse_des_commandes: (v) => ({
			titre: 'Analyse des commandes avant exécution',
			valeur: oui(v) ? 'Activée' : 'Désactivée',
			ton: oui(v) ? 'bon' : 'attention',
			explication: 'Chaque commande est inspectée avant de tourner, pour écarter les dangereuses.'
		}),
		masquage_des_secrets: (v) => ({
			titre: 'Masquage des mots de passe et des clés',
			valeur: oui(v) ? 'Activé' : 'Désactivé',
			ton: oui(v) ? 'bon' : 'attention',
			explication:
				"Vos clés et mots de passe sont remplacés par des étoiles dans les journaux et dans ce que l'assistant affiche."
		}),
		// Sens inverse : la valeur dit « autoriser », donc faux est la bonne nouvelle.
		adresses_internes: (v) => ({
			titre: 'Accès aux adresses internes du réseau',
			valeur: oui(v) ? 'Autorisé' : 'Bloqué',
			ton: oui(v) ? 'attention' : 'bon',
			explication:
				"L'assistant ne peut pas aller frapper aux portes de votre réseau local depuis un lien reçu de l'extérieur."
		}),
		masquage_donnees_personnelles: (v) => ({
			titre: 'Masquage des données personnelles',
			valeur: oui(v) ? 'Activé' : 'Désactivé',
			ton: oui(v) ? 'bon' : 'neutre',
			explication:
				"Noms, adresses et téléphones peuvent être masqués avant d'être envoyés au modèle IA. Utile si vos échanges partent chez un fournisseur externe."
		}),
		delai_max_execution: (v) => ({
			titre: 'Durée maximale',
			valeur: `${Math.round(Number(v) / 60)} minutes`,
			ton: 'neutre',
			explication: "Passé ce délai, une tâche est coupée plutôt que de rester bloquée."
		})
	};

	/** Un identifiant inconnu est ignore : mieux vaut rien qu'une ligne obscure. */
	$: lignes = regles
		.map((regle) => RENDU[regle.id]?.(regle.valeur))
		.filter((ligne): ligne is Ligne => Boolean(ligne));

	$: aSurveiller = lignes.filter((l) => l.ton === 'attention').length;

	const charger = async () => {
		chargement = true;
		erreur = null;
		try {
			const reponse = await getGardeFous(localStorage.token);
			regles = reponse?.regles ?? [];
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	onMount(charger);
</script>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500 dark:text-gray-400">
		<Spinner className="size-4" />
		Lecture du cadre de sécurité…
	</div>
{:else if erreur}
	<div
		class="rounded-2xl border border-red-200 bg-red-50 px-5 py-6 text-sm dark:border-red-900/40 dark:bg-red-950/20"
	>
		<div class="font-medium text-red-800 dark:text-red-300">Le moteur n'a pas répondu</div>
		<div class="mt-1 text-red-700/80 dark:text-red-400/80">{erreur}</div>
	</div>
{:else if lignes.length === 0}
	<div
		class="rounded-2xl border border-dashed border-gray-300 px-5 py-16 text-center dark:border-gray-700"
	>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			Le moteur n'expose aucune règle d'encadrement pour l'instant.
		</div>
	</div>
{:else}
	<!-- Resume en une phrase : combien de reglages meritent un coup d'oeil. -->
	<div
		class="mb-4 flex items-center gap-3.5 rounded-2xl border p-4 {aSurveiller === 0
			? 'border-emerald-200/70 bg-gradient-to-br from-emerald-50 to-green-50/40 dark:border-emerald-900/40 dark:from-emerald-950/30 dark:to-green-950/10'
			: 'border-amber-200/70 bg-gradient-to-br from-amber-50 to-orange-50/40 dark:border-amber-900/40 dark:from-amber-950/30 dark:to-orange-950/10'}"
	>
		<span
			class="size-3 shrink-0 rounded-full {aSurveiller === 0 ? 'bg-emerald-500' : 'bg-amber-500'}"
		></span>
		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-white">
				{aSurveiller === 0
					? 'Votre assistant est bien encadré'
					: `${aSurveiller} réglage${aSurveiller > 1 ? 's' : ''} à regarder`}
			</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{lignes.length} règles lues dans le moteur. Elles définissent ce qu'il n'a pas le droit de
				faire seul.
			</div>
		</div>
	</div>

	<div class="flex flex-col gap-2.5">
		{#each lignes as ligne (ligne.titre)}
			<div
				class="flex items-start justify-between gap-4 rounded-2xl border border-gray-100 bg-white px-4 py-3.5 dark:border-gray-850 dark:bg-gray-900"
			>
				<div class="min-w-0">
					<div class="text-sm font-medium text-gray-900 dark:text-gray-50">{ligne.titre}</div>
					<div class="mt-0.5 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
						{ligne.explication}
					</div>
				</div>
				<div class="flex-none pt-0.5 text-right">
					<span
						class="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium {ligne.ton ===
						'bon'
							? 'text-emerald-600 dark:text-emerald-400'
							: ligne.ton === 'attention'
								? 'text-amber-600 dark:text-amber-400'
								: 'text-gray-600 dark:text-gray-300'}"
					>
						{#if ligne.ton !== 'neutre'}
							<span
								class="size-1.5 rounded-full {ligne.ton === 'bon'
									? 'bg-emerald-500'
									: 'bg-amber-500'}"
							></span>
						{/if}
						{ligne.valeur}
					</span>
				</div>
			</div>
		{/each}
	</div>

	<!-- Le brut, pour qui veut verifier que rien n'a ete embelli. -->
	<details class="group mt-4">
		<summary
			class="inline-flex cursor-pointer list-none select-none items-center gap-1 text-xs text-gray-500 transition hover:text-gray-700 dark:hover:text-gray-300"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5 transition group-open:rotate-90"
			>
				<path
					fill-rule="evenodd"
					d="M7.21 14.77a.75.75 0 0 1 .02-1.06L11.168 10 7.23 6.29a.75.75 0 1 1 1.04-1.08l4.5 4.25a.75.75 0 0 1 0 1.08l-4.5 4.25a.75.75 0 0 1-1.06-.02Z"
					clip-rule="evenodd"
				/>
			</svg>
			Voir le détail technique
		</summary>
		<pre
			class="mt-2 max-h-60 overflow-y-auto whitespace-pre-wrap rounded-xl bg-gray-50 p-2.5 text-[11px] leading-relaxed text-gray-600 dark:bg-gray-900 dark:text-gray-400">{JSON.stringify(
				regles,
				null,
				2
			)}</pre>
	</details>
{/if}
