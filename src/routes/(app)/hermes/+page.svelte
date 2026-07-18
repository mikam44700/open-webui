<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { showSidebar } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import {
		getHermesStatus,
		checkHermesUpdate,
		type HermesStatus,
		type HermesUpdateCheck
	} from '$lib/apis/hermes';
	import { getProviders } from '$lib/apis/providers';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import GatewayList from '$lib/components/gateway/GatewayList.svelte';
	import IntegrationsList from '$lib/components/integrations/IntegrationsList.svelte';
	import McpList from '$lib/components/connectors/McpList.svelte';
	import WebSearchList from '$lib/components/capabilities/WebSearchList.svelte';
	import ToolsetList from '$lib/components/capabilities/ToolsetList.svelte';
	import { prefetchTools } from '$lib/apis/capabilities';
	import mcpLogo from '$lib/assets/connectors/mcp.svg';

	// --- Onglets de l'espace de travail ---
	const ONGLETS = [
		'Modèles IA',
		'Messagerie',
		'Intégrations',
		'MCP',
		'Recherche & web',
		'Outils'
	] as const;
	let ongletActif: (typeof ONGLETS)[number] = 'Modèles IA';

	// Bannières premium par onglet (portées de la v1) : accroche + palette dégradée.
	// Classes Tailwind en toutes lettres (littéraux) pour être compilées.
	type Banniere = {
		lead: string;
		strong: string;
		sub: string;
		wrap: string;
		halo1: string;
		halo2: string;
	};
	const SECTIONS: Record<string, { desc: string; logo?: string; banner: Banniere }> = {
		'Modèles IA': {
			desc: "Choisissez les modèles d'intelligence artificielle qui font tourner votre assistant.",
			banner: {
				lead: 'Choisissez le',
				strong: 'modèle IA de votre assistant',
				sub: "Les modèles d'IA qui le font réfléchir.",
				wrap: 'from-emerald-200/70 via-green-100/50 to-lime-100/60 dark:from-emerald-900/30 dark:via-green-900/20 dark:to-lime-900/20',
				halo1: 'bg-emerald-400/30 dark:bg-emerald-500/20',
				halo2: 'bg-lime-300/30 dark:bg-lime-500/10'
			}
		},
		Messagerie: {
			desc: 'Reliez vos canaux (WhatsApp, Telegram, e-mail…) pour échanger avec votre assistant là où vous êtes déjà.',
			banner: {
				lead: 'Parlez à votre assistant depuis',
				strong: 'WhatsApp, Telegram, e-mail et plus',
				sub: 'Retrouvez-le là où vous échangez déjà.',
				wrap: 'from-amber-200/70 via-orange-100/50 to-yellow-100/60 dark:from-amber-900/30 dark:via-orange-900/20 dark:to-yellow-900/20',
				halo1: 'bg-orange-300/40 dark:bg-orange-500/20',
				halo2: 'bg-amber-300/30 dark:bg-amber-500/10'
			}
		},
		Intégrations: {
			desc: 'Connectez vos applications (Google, Notion, GitHub…) pour que votre assistant agisse directement à l’intérieur.',
			banner: {
				lead: 'Connectez votre agent à vos',
				strong: 'e-mails, agendas, fichiers et bien plus',
				sub: 'Il agit directement dans vos applications, à votre place.',
				wrap: 'from-sky-200/70 via-sky-100/50 to-emerald-100/60 dark:from-sky-900/30 dark:via-slate-900/20 dark:to-emerald-900/20',
				halo1: 'bg-indigo-300/40 dark:bg-indigo-500/20',
				halo2: 'bg-sky-300/30 dark:bg-sky-500/10'
			}
		},
		MCP: {
			desc: 'Branchez des serveurs spécialisés (MCP) pour étendre votre assistant à de nouvelles sources et de nouveaux outils.',
			logo: mcpLogo,
			banner: {
				lead: 'Étendez votre assistant avec des',
				strong: 'connecteurs spécialisés (MCP)',
				sub: 'Pour brancher vos sources et outils sur mesure.',
				wrap: 'from-rose-200/70 via-pink-100/50 to-fuchsia-100/60 dark:from-rose-900/30 dark:via-pink-900/20 dark:to-fuchsia-900/20',
				halo1: 'bg-rose-400/30 dark:bg-rose-500/20',
				halo2: 'bg-fuchsia-300/30 dark:bg-fuchsia-500/10'
			}
		},
		'Recherche & web': {
			desc: 'Tous les services de recherche et de navigation web, visibles d’un coup d’œil. Activez et connectez ceux que vous voulez.',
			banner: {
				lead: 'Donnez à votre assistant la',
				strong: 'recherche et la lecture du web',
				sub: 'Tous les fournisseurs réunis, sans rien chercher.',
				wrap: 'from-sky-200/70 via-cyan-100/50 to-blue-100/60 dark:from-sky-900/30 dark:via-cyan-900/20 dark:to-blue-900/20',
				halo1: 'bg-sky-400/30 dark:bg-sky-500/20',
				halo2: 'bg-cyan-300/30 dark:bg-cyan-500/10'
			}
		},
		Outils: {
			desc: 'Les capacités natives de votre assistant : recherche web, navigateur, génération d’images, mémoire… Activez ce dont vous avez besoin.',
			banner: {
				lead: 'Donnez des super-pouvoirs à votre assistant :',
				strong: 'recherche web, images, mémoire et plus',
				sub: 'Activez seulement ce dont vous avez besoin.',
				wrap: 'from-violet-200/70 via-indigo-100/50 to-purple-100/60 dark:from-violet-900/30 dark:via-indigo-900/20 dark:to-purple-900/20',
				halo1: 'bg-violet-300/40 dark:bg-violet-500/20',
				halo2: 'bg-indigo-300/30 dark:bg-indigo-500/10'
			}
		}
	};
	$: sectionActive = SECTIONS[ongletActif];

	// --- Sous-onglets : Moteur (vue locale) + catégories de ProviderList (portées de la v1) ---
	const SOUS_ONGLETS = [
		{ key: 'moteur', label: 'Moteur' },
		{ key: 'oauth', label: 'Comptes' },
		{ key: 'api', label: 'Clés API' },
		{ key: 'local', label: 'Local' }
	] as const;
	let sousOngletActif: (typeof SOUS_ONGLETS)[number]['key'] = 'moteur';

	// Compteurs des puces (mêmes règles que ProviderList : masqués/expert/multi-agents exclus)
	let compteurs: Record<string, number> = { oauth: 0, api: 0, local: 0 };
	const chargerCompteurs = async () => {
		try {
			const res = await getProviders(localStorage.token);
			const providers: { id: string; category: string }[] = res?.providers ?? [];
			const { MULTIAGENT_IDS, isExpertProvider, isHiddenProvider } = await import(
				'$lib/catalog/provider-taxonomy'
			);
			const visible = providers.filter((p) => !isHiddenProvider(p.id) && !isExpertProvider(p.id));
			compteurs = {
				oauth: visible.filter((p) => p.category === 'oauth').length,
				api: visible.filter((p) => p.category === 'api' && !MULTIAGENT_IDS.has(p.id)).length,
				local: visible.filter((p) => p.category === 'local').length
			};
		} catch {
			// backend indisponible : les puces restent sans compteur
		}
	};

	// Un changement dans ProviderList (clé, OAuth, modèle actif) → on resynchronise tout.
	const surChangementProviders = () => {
		chargerCompteurs();
		rafraichir();
	};

	// --- État du moteur ---
	let statut: HermesStatus | null = null;
	let chargement = true;
	let erreur: string | null = null;
	let dernierControle = '-';
	let interval: ReturnType<typeof setInterval> | null = null;

	// --- Vérification des mises à jour ---
	let verifMajEnCours = false;
	let resultatMaj: HermesUpdateCheck | null = null;
	let erreurMaj: string | null = null;

	const PROVIDER_LABELS: Record<string, string> = {
		anthropic: 'Anthropic',
		openai: 'OpenAI',
		'openai-api': 'OpenAI',
		google: 'Google',
		gemini: 'Google',
		xai: 'xAI',
		openrouter: 'OpenRouter',
		deepseek: 'DeepSeek',
		nous: 'Nous Research',
		ollama: 'Ollama',
		lmstudio: 'LM Studio',
		huggingface: 'Hugging Face',
		groq: 'Groq'
	};

	// « anthropic/claude-opus-4.6 » → « Claude Opus 4.6 (Anthropic) »
	const nomModele = (s: HermesStatus | null): string => {
		const brut = s?.active?.model;
		if (!brut) return 'Non configuré';
		const [prefixe, ...reste] = brut.split('/');
		const id = reste.length > 0 ? reste.join('/') : brut;
		const nom = id
			.split('-')
			.map((mot) => (/\d/.test(mot) ? mot : mot.charAt(0).toUpperCase() + mot.slice(1)))
			.join(' ');
		const fournisseur = reste.length > 0 ? PROVIDER_LABELS[prefixe.toLowerCase()] : null;
		return fournisseur ? `${nom} (${fournisseur})` : nom;
	};

	// « 2026-07-07 » → « 7 juillet 2026 »
	const dateFr = (iso: string | null): string => {
		if (!iso) return '-';
		const d = new Date(`${iso}T00:00:00`);
		if (isNaN(d.getTime())) return iso;
		return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
	};

	$: enLigne = statut?.api_server?.reachable ?? false;

	const rafraichir = async () => {
		erreur = null;
		try {
			statut = await getHermesStatus(localStorage.token);
		} catch (e) {
			erreur = typeof e === 'string' ? e : 'Impossible de contacter le backend.';
			statut = null;
		}
		chargement = false;
		dernierControle = new Date().toLocaleTimeString('fr-FR');
	};

	const verifierMaj = async () => {
		verifMajEnCours = true;
		resultatMaj = null;
		erreurMaj = null;
		try {
			resultatMaj = await checkHermesUpdate(localStorage.token);
		} catch (e) {
			erreurMaj = typeof e === 'string' ? e : 'La vérification a échoué.';
		}
		verifMajEnCours = false;
	};

	onMount(() => {
		rafraichir();
		chargerCompteurs();
		// L'onglet Outils charge /tools (~2,5 s côté bridge) : préchargé en fond dès
		// l'ouverture de la page pour un affichage instantané (recette v1).
		prefetchTools(localStorage.token);
		interval = setInterval(rafraichir, 30000);
	});

	onDestroy(() => {
		if (interval) clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Espace de travail · Hermes</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<nav class="px-3 pt-2 pb-1 shrink-0 flex items-center">
		<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
			<button
				id="sidebar-toggle-button"
				class="cursor-pointer p-1.5 flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={() => showSidebar.set(!$showSidebar)}
				aria-label="Basculer la barre latérale"
			>
				<Sidebar />
			</button>
		</div>
	</nav>

	<div class="flex flex-col w-full px-6 md:px-10 py-4 overflow-y-auto">
		<div class="mb-5">
			<div class="text-xs font-semibold tracking-widest text-gray-500 dark:text-gray-400 uppercase">
				Espace de travail
			</div>
			<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-50 mt-1">Hermes Agent</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				{sectionActive?.desc}
			</p>
		</div>

		<!-- Barre d'onglets -->
		<div
			class="flex flex-wrap items-center gap-1 mb-5 p-1 rounded-full bg-gray-50 dark:bg-gray-850 w-fit"
			role="tablist"
		>
			{#each ONGLETS as onglet}
				<button
					role="tab"
					aria-selected={ongletActif === onglet}
					class="px-4 py-1.5 rounded-full text-sm transition {ongletActif === onglet
						? 'bg-white dark:bg-gray-900 font-semibold text-gray-900 dark:text-gray-50 shadow-sm'
						: 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => (ongletActif = onglet)}
				>
					{onglet}
				</button>
			{/each}
		</div>

		<!-- Bannière premium : couleur + texte selon l'onglet actif (portée de la v1) -->
		{#if sectionActive?.banner}
			<div
				class="relative mb-5 overflow-hidden rounded-3xl bg-linear-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 {sectionActive
					.banner.wrap}"
			>
				<div
					class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {sectionActive
						.banner.halo1}"
				></div>
				<div
					class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {sectionActive
						.banner.halo2}"
				></div>
				<div class="hero-mesh pointer-events-none absolute inset-0"></div>
				<div class="hero-grain pointer-events-none absolute inset-0"></div>
				{#if sectionActive?.logo}
					<div
						class="pointer-events-none absolute left-6 top-1/2 hidden -translate-y-1/2 sm:left-10 sm:flex"
					>
						<div
							class="flex size-16 items-center justify-center rounded-2xl bg-white/90 p-3 shadow-sm backdrop-blur dark:bg-gray-900/80"
						>
							<img
								src={sectionActive.logo}
								alt={ongletActif}
								class="max-h-full max-w-full object-contain dark:invert"
								draggable="false"
							/>
						</div>
					</div>
				{/if}
				<div class="relative flex flex-col items-center justify-center gap-2 px-6 py-8 text-center">
					<div
						class="rounded-full bg-white/90 px-5 py-2 text-sm text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
					>
						{sectionActive.banner.lead}
						<span class="font-semibold text-gray-900 dark:text-white"
							>{sectionActive.banner.strong}</span
						>
					</div>
					<p class="text-sm text-gray-500 dark:text-gray-400">{sectionActive.banner.sub}</p>
				</div>
			</div>
		{/if}

		{#if ongletActif === 'Messagerie'}
			<!-- Canaux de messagerie (porté de la v1) -->
			<div class="-mx-3">
				<GatewayList />
			</div>
		{:else if ongletActif === 'Intégrations'}
			<!-- Applications connectées (porté de la v1) -->
			<div class="-mx-3">
				<IntegrationsList />
			</div>
		{:else if ongletActif === 'MCP'}
			<!-- Connecteurs MCP (porté de la v1) -->
			<div class="-mx-3">
				<McpList />
			</div>
		{:else if ongletActif === 'Recherche & web'}
			<!-- Recherche web, navigateur, X, extraction (porté de la v1) -->
			<div class="-mx-3">
				<WebSearchList />
			</div>
		{:else if ongletActif === 'Outils'}
			<!-- Capacités de l'assistant : toolsets Hermes (porté de la v1) -->
			<div class="-mx-3">
				<ToolsetList />
			</div>
		{:else if ongletActif !== 'Modèles IA'}
			<!-- Onglets à venir -->
			<div
				class="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-5 py-16 text-center"
			>
				<div class="font-medium text-gray-900 dark:text-gray-50">Bientôt disponible</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					L'onglet « {ongletActif} » arrive dans un prochain chantier.
				</div>
			</div>
		{:else}
			<div class="flex flex-wrap items-center justify-between gap-3 mb-4">
				<div class="text-sm text-gray-900 dark:text-gray-50">
					Modèle IA actif : <span class="font-semibold">{nomModele(statut)}</span>
				</div>

				<!-- Sous-onglets : Moteur / Comptes / Clés API / Local -->
				<div class="flex items-center gap-1.5">
					{#each SOUS_ONGLETS as sousOnglet (sousOnglet.key)}
						<button
							class="px-3.5 py-1.5 rounded-full text-sm border transition {sousOngletActif ===
							sousOnglet.key
								? 'bg-gray-900 text-gray-50 dark:bg-gray-50 dark:text-gray-900 border-transparent font-medium'
								: 'border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850'}"
							on:click={() => (sousOngletActif = sousOnglet.key)}
						>
							{sousOnglet.label}
							{#if sousOnglet.key !== 'moteur' && compteurs[sousOnglet.key]}
								<span class="opacity-60">({compteurs[sousOnglet.key]})</span>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			{#if sousOngletActif !== 'moteur'}
				<!-- Comptes / Clés API / Local : catalogue providers porté de la v1 -->
				<div class="-mx-3">
					<ProviderList
						embedded
						allowedTabs={[sousOngletActif]}
						on:changed={surChangementProviders}
					/>
				</div>
			{:else}

			<!-- Bandeau d'état -->
			<div
				class="rounded-2xl px-5 py-4 mb-4 border {enLigne
					? 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900'
					: 'bg-gray-50 dark:bg-gray-850 border-gray-200 dark:border-gray-800'}"
			>
				<div class="flex items-center gap-3">
					<span class="relative flex size-3 shrink-0" aria-hidden="true">
						{#if chargement}
							<span class="relative inline-flex rounded-full size-3 bg-yellow-400 animate-pulse" />
						{:else if enLigne}
							<span
								class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
							/>
							<span class="relative inline-flex rounded-full size-3 bg-green-500" />
						{:else}
							<span class="relative inline-flex rounded-full size-3 bg-gray-400" />
						{/if}
					</span>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-50">
							{#if chargement}
								Vérification en cours...
							{:else if enLigne}
								Votre assistant est opérationnel
							{:else}
								Moteur hors ligne
							{/if}
						</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">
							{#if chargement}
								Contact du moteur...
							{:else if enLigne}
								Le moteur tourne et répond normalement.
							{:else if erreur}
								{erreur}
							{:else}
								Hermes est installé mais son serveur n'est pas démarré (commande
								<span class="font-mono">hermes gateway</span> dans le terminal).
							{/if}
						</div>
					</div>
				</div>
			</div>

			<!-- Carte état du moteur -->
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 px-5 py-4 mb-4">
				<div class="flex items-center justify-between mb-3">
					<div class="font-medium text-gray-900 dark:text-gray-50">État du moteur</div>
					<button
						class="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={rafraichir}
						title="Rafraîchir (dernier contrôle : {dernierControle})"
						aria-label="Rafraîchir l'état du moteur"
					>
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
								d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
							/>
						</svg>
					</button>
				</div>
				<div class="flex flex-col gap-2.5 text-sm">
					<div class="flex justify-between">
						<span class="text-gray-500 dark:text-gray-400">Modèle IA</span>
						<span class="text-gray-900 dark:text-gray-50 font-medium">{nomModele(statut)}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-500 dark:text-gray-400">Moteur de LunarIA</span>
						<span
							class="font-medium {enLigne
								? 'text-green-600 dark:text-green-400'
								: 'text-gray-500 dark:text-gray-400'}"
						>
							● {enLigne ? 'En ligne' : 'Hors ligne'}
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-500 dark:text-gray-400">Réponses dans le chat</span>
						<span
							class="font-medium {enLigne
								? 'text-green-600 dark:text-green-400'
								: 'text-gray-500 dark:text-gray-400'}"
						>
							● {enLigne ? 'Actives' : 'Inactives'}
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-500 dark:text-gray-400">Version du moteur</span>
						<span class="text-gray-900 dark:text-gray-50 font-medium">
							{statut?.version ?? '-'}
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-500 dark:text-gray-400">Dernière mise à jour</span>
						<span class="text-gray-900 dark:text-gray-50 font-medium">
							{dateFr(statut?.last_update ?? null)}
						</span>
					</div>
				</div>
			</div>

			<!-- Carte mise à jour du moteur -->
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 px-5 py-4">
				<div class="font-medium text-gray-900 dark:text-gray-50">Mise à jour du moteur</div>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-3">
					Récupère la dernière version du moteur (et ses derniers modèles). Une sauvegarde est faite
					automatiquement avant.
				</p>
				<div class="flex flex-wrap gap-2">
					<button
						class="px-4 py-2 rounded-xl text-sm font-medium border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-gray-50 hover:bg-gray-50 dark:hover:bg-gray-850 transition disabled:opacity-50"
						on:click={verifierMaj}
						disabled={verifMajEnCours}
					>
						{verifMajEnCours ? 'Vérification...' : 'Vérifier les mises à jour'}
					</button>
					<button
						class="px-4 py-2 rounded-xl text-sm font-medium bg-gray-900 text-gray-50 dark:bg-gray-50 dark:text-gray-900 opacity-50 cursor-not-allowed"
						disabled
						title="Bientôt disponible — sera câblé dans un prochain chantier"
					>
						Mettre à jour le moteur
					</button>
				</div>

				{#if resultatMaj}
					<div
						class="mt-3 rounded-xl px-4 py-3 text-sm {resultatMaj.up_to_date === false
							? 'bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300'
							: 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400'}"
					>
						{#if resultatMaj.up_to_date === true}
							Votre moteur est à jour.
						{:else if resultatMaj.up_to_date === false}
							Une mise à jour est disponible.
						{:else}
							Résultat de la vérification :
						{/if}
						{#if resultatMaj.output}
							<pre
								class="mt-2 text-xs whitespace-pre-wrap font-mono text-gray-600 dark:text-gray-400 max-h-40 overflow-y-auto">{resultatMaj.output}</pre>
						{/if}
					</div>
				{:else if erreurMaj}
					<div
						class="mt-3 rounded-xl px-4 py-3 text-sm bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400"
					>
						{erreurMaj}
					</div>
				{/if}
			</div>
			{/if}
		{/if}
	</div>
</div>
