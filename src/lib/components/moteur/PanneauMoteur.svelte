<script lang="ts">
	/**
	 * Sous-onglet « Moteur » — LunarIA V2.
	 *
	 * Repond a « mon moteur est-il bien branche et a jour ? ». C'est le seul
	 * endroit ou l'on parle du moteur en tant que logiciel, pas en tant que
	 * cerveau.
	 *
	 * Mise en page reprise d'AgentOS V1 : une carte unique, des lignes
	 * « libelle -> valeur » separees par des filets, et tout le technique replie
	 * derriere un lien. La grille de quatre cases precedente montrait la meme
	 * chose, mais faisait lire quatre blocs la ou trois lignes suffisent.
	 */
	import { onMount } from 'svelte';
	import { getEtatDetaille, type EtatDetaille } from '$lib/apis/hermes';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	let etat: EtatDetaille | null = null;
	let chargement = true;
	let erreur: string | null = null;

	const charger = async () => {
		chargement = true;
		erreur = null;
		try {
			etat = await getEtatDetaille(localStorage.token);
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	/**
	 * Deux versions cohabitent et ne veulent pas dire la meme chose : celle du
	 * logiciel, et celle du fichier de configuration. Une config en retard se
	 * repare toute seule au demarrage suivant — ce n'est pas une mise a jour du
	 * moteur, et il ne faut pas les confondre a l'ecran.
	 */
	$: configARetard =
		etat?.config_version !== undefined &&
		etat?.latest_config_version !== undefined &&
		etat.config_version < etat.latest_config_version;

	onMount(charger);
</script>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500 dark:text-gray-400">
		<Spinner className="size-4" />
		Lecture de l'état du moteur…
	</div>
{:else if erreur}
	<div
		class="rounded-2xl border border-red-200 bg-red-50 px-5 py-6 text-sm dark:border-red-900/40 dark:bg-red-950/20"
	>
		<div class="font-medium text-red-800 dark:text-red-300">Le moteur n'a pas répondu</div>
		<div class="mt-1 text-red-700/80 dark:text-red-400/80">{erreur}</div>
	</div>
{:else}
	<div
		class="flex flex-col gap-3 rounded-2xl border border-gray-100 p-4 dark:border-gray-850"
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2.5">
				<img
					src="{WEBUI_BASE_URL}/assets/providers/nousresearch.png"
					alt=""
					class="size-11 shrink-0 rounded-xl object-cover"
					draggable="false"
				/>
				<div class="text-sm font-medium text-gray-900 dark:text-gray-50">État du moteur</div>
			</div>
			<button
				type="button"
				class="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-850 dark:hover:text-gray-200"
				title="Relire l'état"
				aria-label="Relire l'état"
				on:click={charger}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.8"
					stroke="currentColor"
					class="size-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M16.023 9.348h4.992V4.356M3 3.75v4.5m0 0h4.5m-4.5 0 3.181-3.183a8.25 8.25 0 0 1 11.667 0l3.181 3.183m0 6.75v4.5m0 0h-4.5m4.5 0-3.182-3.182a8.25 8.25 0 0 1-11.667 0L3 16.5"
					/>
				</svg>
			</button>
		</div>

		<div class="h-px bg-gray-100 dark:bg-gray-850"></div>

		<!-- Version installee -->
		<div class="flex items-center justify-between gap-4 text-sm">
			<span class="text-gray-500 dark:text-gray-400">Version installée</span>
			<span class="text-right font-medium text-gray-900 dark:text-gray-100">
				Hermes {etat?.version ?? '—'}
				{#if etat?.release_date}
					<span class="font-normal text-gray-400 dark:text-gray-500">
						· publiée le {etat.release_date}
					</span>
				{/if}
			</span>
		</div>

		<!-- Mise a jour -->
		<div class="flex items-start justify-between gap-4 text-sm">
			<span class="flex-none text-gray-500 dark:text-gray-400">Mise à jour</span>
			{#if etat?.can_update_hermes}
				<span class="text-right">
					<span
						class="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400"
					>
						<span class="size-1.5 rounded-full bg-amber-500"></span>
						Une version plus récente existe
					</span>
					<span class="mt-0.5 block text-[11px] leading-relaxed text-gray-400 dark:text-gray-500">
						Le moteur tourne dans son propre conteneur : la mise à jour se fait en reconstruisant
						l'image, pas depuis cet écran.
					</span>
				</span>
			{:else}
				<span
					class="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"
				>
					<span class="size-1.5 rounded-full bg-emerald-500"></span>
					À jour — rien à faire
				</span>
			{/if}
		</div>

		<!-- Passerelle de messagerie -->
		<div class="flex items-start justify-between gap-4 text-sm">
			<span class="flex-none text-gray-500 dark:text-gray-400">Passerelle de messagerie</span>
			<span class="text-right">
				<span
					class="inline-flex items-center gap-1.5 text-xs font-medium {etat?.gateway_running
						? 'text-emerald-600 dark:text-emerald-400'
						: 'text-gray-500 dark:text-gray-400'}"
				>
					<span
						class="size-1.5 rounded-full {etat?.gateway_running
							? 'bg-emerald-500'
							: 'bg-gray-300 dark:bg-gray-700'}"
					></span>
					{etat?.gateway_running ? 'En marche' : 'À l’arrêt'}
				</span>
				<span class="mt-0.5 block text-[11px] text-gray-400 dark:text-gray-500">
					{etat?.gateway_running
						? 'Vos canaux (WhatsApp, e-mail…) sont écoutés.'
						: 'Normal tant qu’aucun canal de messagerie n’est branché.'}
				</span>
			</span>
		</div>

		<!-- Fichier de configuration -->
		<div class="flex items-start justify-between gap-4 text-sm">
			<span class="flex-none text-gray-500 dark:text-gray-400">Fichier de configuration</span>
			<span class="text-right">
				<span class="font-medium text-gray-900 dark:text-gray-100">
					{configARetard ? 'Sera mis à niveau' : 'À jour'}
				</span>
				<span class="mt-0.5 block text-[11px] text-gray-400 dark:text-gray-500">
					{#if configARetard}
						version {etat?.config_version} sur {etat?.latest_config_version} — le moteur s'en occupe
						seul au prochain démarrage
					{:else}
						version {etat?.config_version ?? '—'}
					{/if}
				</span>
			</span>
		</div>

		<!-- Detail technique : ferme par defaut. Ce qui rassure un technicien
		     inquiete un dirigeant, donc on ne le montre qu'a la demande. -->
		{#if etat}
			<details class="group border-t border-gray-100 pt-2.5 dark:border-gray-850">
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
						etat,
						null,
						2
					)}</pre>
			</details>
		{/if}
	</div>
{/if}
