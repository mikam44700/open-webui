<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import {
		getHermesStatus,
		checkHermesUpdate,
		startHermesUpdate,
		getHermesUpdateStatus
	} from '$lib/apis/providers';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getProviderName } from '$lib/catalog/provider-info';
	import { expertMode } from '$lib/stores';

	let showUpdateConfirm = false;

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loading = true;
	let status: any = null;

	let checking = false;
	let checkOutput = '';
	let checkResult: { tone: 'update' | 'uptodate' | 'unknown'; msg: string } | null = null;

	let updateState: 'idle' | 'running' | 'success' | 'error' | 'rolled_back' = 'idle';
	let updateLog = '';
	let poller: ReturnType<typeof setInterval> | null = null;

	// État de santé synthétique : moteur en ligne + connexion au chat + un cerveau branché.
	$: engineOk = !!status?.hermes_available;
	$: chatOk = !!status?.api_server?.reachable;
	// Rétrocompat : champ absent (bridge pas encore resync) => on ne déclenche pas l'alerte.
	$: brainConnected = status?.brain_connected !== false;
	// « auto » = le cerveau par défaut d'usine (openrouter sans clé) : il ne répond PAS.
	// On ne doit donc pas afficher « opérationnel » tant qu'un vrai cerveau n'est pas activé.
	$: activeIsAuto = status?.active?.provider_id === 'auto';
	$: health = !engineOk
		? {
				tone: 'down',
				title: 'Votre assistant est hors ligne',
				sub: 'Le moteur ne répond pas pour le moment.'
			}
		: !chatOk
			? {
					tone: 'warn',
					title: 'Connexion au chat interrompue',
					sub: 'Le moteur tourne, mais le lien avec le chat ne répond pas.'
				}
			: !brainConnected
				? {
						tone: 'warn',
						title: 'Aucun modèle IA connecté',
						sub: 'Connecte un compte ou une clé API pour que ton assistant puisse répondre.'
					}
				: activeIsAuto
					? {
							tone: 'warn',
							title: 'Choisissez le cerveau de votre assistant',
							sub: 'Aucun modèle IA n’est encore activé. Branchez une clé dans « Modèles IA » : votre assistant s’activera tout seul dessus.'
						}
					: {
							tone: 'ok',
							title: 'Votre assistant est opérationnel',
							sub: 'Le moteur tourne et répond normalement.'
						};
	// Version lisible (ex. « v0.17.0 ») extraite de la chaîne technique complète.
	$: versionShort = (() => {
		const v = status?.version ?? '';
		const m = v.match(/v\d+\.\d+(?:\.\d+)?/);
		return m ? m[0] : v || '—';
	})();

	const loadStatus = async () => {
		loading = true;
		try {
			status = await getHermesStatus(localStorage.token);
		} catch {
			toast.error($i18n.t('Impossible de récupérer l’état du moteur'));
		} finally {
			loading = false;
		}
	};

	const check = async () => {
		checking = true;
		checkOutput = '';
		checkResult = null;
		try {
			const r = await checkHermesUpdate(localStorage.token);
			const out = r?.output ?? '';
			checkOutput = out || $i18n.t('Aucune information.');
			// Détection déterministe PAR VERSION (le bridge compare la version locale à
			// origin/main). On n'interprète plus le texte technique anglais — fragile et
			// trompeur : un simple correctif sur `main` qui ne change pas le numéro de
			// version ne doit pas faire croire au client qu'une mise à jour l'attend.
			const clean = (v) => (v ? String(v).replace(/^v/i, '') : '');
			if (r?.available) {
				const to = r?.latest_version ? ` (v${clean(r.latest_version)})` : '';
				checkResult = { tone: 'update', msg: `Une mise à jour est disponible.${to}` };
			} else if (r?.current_version) {
				checkResult = {
					tone: 'uptodate',
					msg: `Votre moteur est à jour — dernière version v${clean(r.current_version)}.`
				};
			} else {
				// Comparaison impossible (hors-ligne, git indisponible) : rester honnête.
				checkResult = { tone: 'unknown', msg: 'Vérification impossible pour le moment.' };
			}
		} catch {
			toast.error($i18n.t('Échec de la vérification'));
		} finally {
			checking = false;
		}
	};

	const stopPolling = () => {
		if (poller) {
			clearInterval(poller);
			poller = null;
		}
	};

	const pollUpdate = async () => {
		try {
			const st = await getHermesUpdateStatus(localStorage.token);
			updateLog = st?.log ?? updateLog;
			if (st && st.running === false && st.started) {
				stopPolling();
				if (st.success) {
					updateState = 'success';
					toast.success($i18n.t('Moteur mis à jour'));
					await loadStatus();
				} else if (st.rolled_back) {
					// La MAJ a échoué mais le filet a fonctionné : moteur restauré à l'état d'avant.
					updateState = 'rolled_back';
					toast.error($i18n.t('Mise à jour annulée : ton assistant a été restauré'));
					await loadStatus();
				} else {
					updateState = 'error';
					toast.error($i18n.t('Échec de la mise à jour'));
				}
			}
		} catch {
			stopPolling();
			updateState = 'error';
		}
	};

	// Format court d'une date ISO en français (ex. « 2 juillet 2026 »).
	const formatDate = (iso: string): string => {
		try {
			return new Date(iso).toLocaleDateString('fr-FR', {
				day: 'numeric',
				month: 'long',
				year: 'numeric'
			});
		} catch {
			return iso;
		}
	};

	const update = async () => {
		updateState = 'running';
		updateLog = '';
		// Efface le message « Une mise à jour est disponible » du check précédent
		// (sinon il resterait affiché à tort une fois le moteur à jour).
		checkResult = null;
		try {
			await startHermesUpdate(localStorage.token);
			stopPolling();
			poller = setInterval(pollUpdate, 1500);
		} catch {
			updateState = 'error';
			toast.error($i18n.t('Impossible de démarrer la mise à jour'));
		}
	};

	onMount(loadStatus);
	onDestroy(stopPolling);
</script>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-6" /></div>
{:else if status}
	<!-- Bandeau santé : l'essentiel en un coup d'œil, ton rassurant. -->
	<div
		class="flex items-center gap-3.5 p-4 rounded-2xl border {health.tone === 'ok'
			? 'border-emerald-200/70 bg-gradient-to-br from-emerald-50 to-green-50/40 dark:border-emerald-900/40 dark:from-emerald-950/30 dark:to-green-950/10'
			: health.tone === 'warn'
				? 'border-amber-200/70 bg-gradient-to-br from-amber-50 to-orange-50/40 dark:border-amber-900/40 dark:from-amber-950/30 dark:to-orange-950/10'
				: 'border-red-200/70 bg-gradient-to-br from-red-50 to-rose-50/40 dark:border-red-900/40 dark:from-red-950/30 dark:to-rose-950/10'}"
	>
		<span class="relative flex size-3 shrink-0">
			{#if health.tone === 'ok'}
				<span class="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60 animate-ping"></span>
			{/if}
			<span
				class="relative inline-flex size-3 rounded-full {health.tone === 'ok'
					? 'bg-emerald-500'
					: health.tone === 'warn'
						? 'bg-amber-500'
						: 'bg-red-500'}"
			></span>
		</span>
		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-white">{$i18n.t(health.title)}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t(health.sub)}</div>
		</div>
	</div>

	<!-- État détaillé -->
	<div class="mt-3 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2.5">
				<img
					src="{WEBUI_BASE_URL}/assets/providers/nousresearch.png"
					alt="Agent Hermes"
					class="size-11 rounded-xl object-cover shrink-0"
					draggable="false"
				/>
				<div class="text-sm font-medium">{$i18n.t('État du moteur')}</div>
			</div>
			<button
				type="button"
				class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 dark:hover:text-gray-200 transition"
				title={$i18n.t('Rafraîchir')}
				aria-label={$i18n.t('Rafraîchir')}
				on:click={loadStatus}
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

		<!-- Modèle IA : le fournisseur lisible (OpenAI Codex), pas le modèle technique. -->
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Modèle IA')}</span>
			{#if brainConnected}
				<span class="font-medium text-right text-gray-900 dark:text-gray-100">
					{status.active?.provider_id
						? getProviderName(status.active.provider_id, status.active_provider_label ?? status.active.provider_id)
						: (status.active_provider_label ?? '—')}
				</span>
			{:else}
				<span class="inline-flex items-center gap-1.5 text-xs font-medium text-red-600 dark:text-red-400">
					<span class="size-1.5 rounded-full bg-red-500"></span>
					{$i18n.t('Aucun modèle IA connecté')}
				</span>
			{/if}
		</div>

		<!-- Moteur -->
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Moteur de LunarIA')}</span>
			<span
				class="inline-flex items-center gap-1.5 text-xs font-medium {engineOk
					? 'text-emerald-600 dark:text-emerald-400'
					: 'text-red-600 dark:text-red-400'}"
			>
				<span class="size-1.5 rounded-full {engineOk ? 'bg-emerald-500' : 'bg-red-500'}"></span>
				{engineOk ? $i18n.t('En ligne') : $i18n.t('Hors ligne')}
			</span>
		</div>

		<!-- Connexion au chat -->
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">
				{$i18n.t('Réponses dans le chat')}
				{#if $expertMode && status.api_server?.port}
					<span class="text-gray-400">(API :{status.api_server.port})</span>
				{/if}
			</span>
			<span
				class="inline-flex items-center gap-1.5 text-xs font-medium {chatOk
					? 'text-emerald-600 dark:text-emerald-400'
					: 'text-red-600 dark:text-red-400'}"
			>
				<span class="size-1.5 rounded-full {chatOk ? 'bg-emerald-500' : 'bg-red-500'}"></span>
				{chatOk ? $i18n.t('Actives') : $i18n.t('Interrompues')}
			</span>
		</div>

		<!-- Version -->
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Version du moteur')}</span>
			<span class="font-medium text-right text-gray-900 dark:text-gray-100">{versionShort}</span>
		</div>

		<!-- Date de la dernière mise à jour (déduite de la dernière sauvegarde pre-update) -->
		{#if status.last_update}
			<div class="flex items-center justify-between text-sm">
				<span class="text-gray-500">{$i18n.t('Dernière mise à jour')}</span>
				<span class="font-medium text-right text-gray-900 dark:text-gray-100">
					{formatDate(status.last_update)}
				</span>
			</div>
		{/if}

		{#if $expertMode && status.version}
			<div
				class="text-[11px] leading-relaxed text-gray-400 dark:text-gray-500 break-all border-t border-gray-100 dark:border-gray-850 pt-2"
			>
				{status.version}
			</div>
		{/if}
	</div>

	<!-- Mise à jour -->
	<div class="mt-3 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 flex flex-col gap-3">
		<div>
			<div class="text-sm font-medium">{$i18n.t('Mise à jour du moteur')}</div>
			<div class="text-xs text-gray-500 mt-0.5">
				{$i18n.t('Récupère la dernière version du moteur (et ses derniers modèles). Une sauvegarde est faite automatiquement avant.')}
			</div>
		</div>

		<!-- résultat -->
		{#if updateState === 'running'}
			<div class="inline-flex items-center gap-2 text-xs font-medium text-amber-600 dark:text-amber-400">
				<Spinner className="size-3.5" />
				{$i18n.t('Mise à jour en cours, ne ferme pas la page… (compte 2 à 5 minutes)')}
			</div>
		{:else if updateState === 'success'}
			<div class="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
				<span class="size-1.5 rounded-full bg-emerald-500"></span>
				{$i18n.t('Le moteur est à jour ✓')}
			</div>
		{:else if updateState === 'rolled_back'}
			<div class="flex items-start gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
				<span class="size-1.5 rounded-full bg-amber-500 mt-1 shrink-0"></span>
				<span
					>{$i18n.t(
						'La mise à jour a échoué, mais ton assistant a été restauré à la version précédente — il fonctionne normalement. Tu peux réessayer plus tard.'
					)}</span
				>
			</div>
		{:else if updateState === 'error'}
			<div class="inline-flex items-center gap-1.5 text-xs font-medium text-red-600 dark:text-red-400">
				<span class="size-1.5 rounded-full bg-red-500"></span>
				{$i18n.t('La mise à jour a échoué. Vois le détail ci-dessous.')}
			</div>
		{/if}

		<div class="flex items-center gap-2">
			<button
				type="button"
				class="text-sm px-3.5 py-2 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-50 inline-flex items-center gap-2"
				disabled={checking || updateState === 'running'}
				on:click={check}
			>
				{#if checking}<Spinner className="size-4" />{/if}
				{$i18n.t('Vérifier les mises à jour')}
			</button>
			<button
				type="button"
				class="text-sm px-3.5 py-2 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-50 inline-flex items-center gap-2"
				disabled={updateState === 'running'}
				on:click={() => (showUpdateConfirm = true)}
			>
				{#if updateState === 'running'}<Spinner className="size-4" />{$i18n.t('Mise à jour en cours…')}{:else}{$i18n.t('Mettre à jour le moteur')}{/if}
			</button>
		</div>

		<!-- résultat clair de la vérification (le détail technique anglais reste replié) -->
		{#if checkResult}
			<div
				class="inline-flex items-center gap-1.5 text-xs font-medium {checkResult.tone === 'uptodate'
					? 'text-emerald-600 dark:text-emerald-400'
					: checkResult.tone === 'update'
						? 'text-amber-600 dark:text-amber-400'
						: 'text-gray-500'}"
			>
				<span
					class="size-1.5 rounded-full {checkResult.tone === 'uptodate'
						? 'bg-emerald-500'
						: checkResult.tone === 'update'
							? 'bg-amber-500'
							: 'bg-gray-400'}"
				></span>
				{$i18n.t(checkResult.msg)}
				{#if checkResult.tone === 'update'}
					<span class="font-normal text-gray-400"
						>— {$i18n.t('cliquez sur « Mettre à jour le moteur ».')}</span
					>
				{/if}
			</div>
		{/if}

		<!-- détail technique repliable (caché par défaut, rassure le non-tech) -->
		{#if checkOutput || updateLog}
			<details class="group">
				<summary
					class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 cursor-pointer select-none list-none inline-flex items-center gap-1"
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
					{$i18n.t('Voir le détail technique')}
				</summary>
				{#if checkOutput}
					<pre class="mt-2 text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2.5 max-h-40 overflow-y-auto whitespace-pre-wrap">{checkOutput}</pre>
				{/if}
				{#if updateLog}
					<pre class="mt-2 text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2.5 max-h-60 overflow-y-auto whitespace-pre-wrap">{updateLog}</pre>
				{/if}
			</details>
		{/if}
	</div>
{/if}

<ConfirmDialog
	bind:show={showUpdateConfirm}
	title={$i18n.t('Mettre à jour le moteur ?')}
	message={$i18n.t(
		'Le moteur va être mis à jour vers la dernière version, avec une sauvegarde automatique au préalable. Compte 2 à 5 minutes : le service peut être interrompu quelques instants, puis il redémarre tout seul.'
	)}
	confirmLabel={$i18n.t('Mettre à jour')}
	onConfirm={update}
/>
