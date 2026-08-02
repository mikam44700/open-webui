<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getIntegrations } from '$lib/apis/integrations';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import IntegrationCard from './IntegrationCard.svelte';
	import IntegrationsBrowseModal from './IntegrationsBrowseModal.svelte';
	import PanneauComposio from '$lib/components/composio/PanneauComposio.svelte';
	import { filtrerNatives } from '$lib/composio/doublons';

	const i18n = getContext('i18n');

	type Integration = {
		id: string;
		auth_mode: 'account' | 'key' | 'credentials' | 'path' | 'local';
		state: 'not_connected' | 'key_present' | 'connected' | 'error' | 'unavailable';
		secret_state?: 'present' | 'absent' | null;
		subservices?: string[];
		visible?: boolean;
		local_only?: boolean;
		reason?: string | null;
	};

	let loading = true;
	let bridgeDown = false;
	let integrations: Integration[] = [];
	let showBrowse = false;
	// Remonte par le panneau Composio. Une application ne doit jamais avoir deux
	// cartes : quand Composio la porte, la carte native s'efface — sauf si elle
	// est reellement connectee, auquel cas c'est la native qui reste (doublons.ts).
	let composioActif = false;

	// Les 6 intégrations essentielles visibles sur la page, dans l'ordre produit décidé.
	// Le catalogue « Tout parcourir » continue de recevoir toutes les intégrations visibles.
	const HOME_INTEGRATION_IDS = [
		'google-workspace',
		'microsoft-365',
		'obsidian',
		'notion',
		'airtable',
		'linkedin'
	];

	// Le client final ne voit que les intégrations visibles (les masquées restent gérées en admin).
	$: visible = filtrerNatives(
		integrations.filter((i) => i.visible !== false),
		composioActif
	);
	// Avec Composio actif il ne reste que ce qu'il ne sait pas faire : quelques
	// cartes, toutes montrees. Sans Composio, la selection produit d'origine.
	$: home = composioActif
		? visible
		: HOME_INTEGRATION_IDS.map((id) => visible.find((i) => i.id === id)).filter(
				(i): i is Integration => i !== undefined
			);

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getIntegrations(localStorage.token);
			integrations = res?.integrations ?? [];
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else toast.error($i18n.t('Échec du chargement des intégrations'));
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
	<!-- Composio en tete : c'est par lui que passent les connexions par compte
	     (messagerie, agenda, fichiers), que le moteur ne sait pas ouvrir seul.
	     Il se charge independamment du reste : sa panne ne masque pas les
	     integrations natives en dessous, et l'inverse est vrai aussi. -->
	<div class="mb-6">
		<PanneauComposio on:etat={(e) => (composioActif = e.detail?.etat === 'ok')} />
	</div>

	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Intégrations est injoignable')}</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else if visible.length > 0}
		<!-- Sélection fixe de 6 cartes + catalogue complet. Leur ordre reste identique même connectées. -->
		{#if home.length > 0}
			<div class="flex items-center justify-between mb-3">
				<!-- Une fois Composio actif, ce qui reste ici est ce qu'il ne peut pas
				     atteindre : un coffre sur le disque, un protocole de messagerie,
				     de la domotique. Le titre doit le dire, sinon la section parait
				     arbitraire a cote du catalogue du dessus. -->
				<div class="text-sm font-medium">
					{composioActif ? $i18n.t('Sur cette machine') : $i18n.t('Les plus populaires')}
				</div>
				<button
					type="button"
					class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white transition inline-flex items-center gap-1"
					on:click={() => (showBrowse = true)}
				>
					{$i18n.t('Tout parcourir')}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="size-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
						/>
					</svg>
				</button>
			</div>

			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each home as integration (integration.id)}
					<IntegrationCard {integration} on:changed={load} />
				{/each}
			</div>
		{/if}
	{:else if !composioActif}
		<!-- Silence volontaire quand Composio est actif : la liste native est vide
		     parce que tout est passe au-dessus, pas parce que rien n'est
		     disponible. Afficher « Aucune intégration » ferait croire a une panne. -->
		<div class="text-xs text-gray-500 text-center py-8">
			{$i18n.t('Aucune intégration disponible')}
		</div>
	{/if}
</div>

<IntegrationsBrowseModal bind:open={showBrowse} integrations={visible} on:changed={load} />
