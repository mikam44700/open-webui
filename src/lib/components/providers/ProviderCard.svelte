<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderOAuth from './ProviderOAuth.svelte';
	import { getModelPresentation } from '$lib/catalog/model-badges';
	import { getProviderRegionFlag, getProviderRegionName } from '$lib/catalog/provider-taxonomy';
	import { PROVIDER_INFO } from '$lib/catalog/provider-info';
	import { PROVIDER_LOGO_FULL_BLEED } from '$lib/utils/providerLogos';
	import {
		setProviderKey,
		validateProviderKey,
		setAwsCredentials,
		deleteProviderKey,
		getModelCapabilities
	} from '$lib/apis/providers';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let provider: {
		id: string;
		label: string;
		logo: string;
		category: 'oauth' | 'api' | 'local' | 'other';
		state: 'active' | 'configured' | 'not_configured';
		env_key?: string | null;
		base_url?: string | null;
		models?: { id: string; label: string }[];
	};
	export let activeModelId = '';

	$: configured = provider.state !== 'not_configured';
	// Présentation métier curée (libellé humain + badges) — repli neutre si inconnu (D27).
	$: presentation = getModelPresentation(provider.id);
	// Infos client : phrase grise courte, « Voir ce que ça fait », lien « Obtenir la clé ».
	$: info = PROVIDER_INFO[provider.id] ?? {};
	// Origine / juridiction du fournisseur (souveraineté) — drapeau + nom au survol.
	$: regionFlag = getProviderRegionFlag(provider.id);
	$: regionName = getProviderRegionName(provider.id);

	// Capacités affichées sur la carte (Raisonnement/Vision/Outils/contexte), tirées du
	// modèle PRINCIPAL du fournisseur (le recommandé qui s'active par défaut, sinon le
	// 1er exposé). Même source que le sélecteur du chat → cohérent et honnête.
	const RECOMMENDED_MODEL: Record<string, string> = {
		anthropic: 'claude-sonnet-4-6',
		'openai-api': 'gpt-5.5',
		gemini: 'gemini-3.5-flash',
		mistral: 'mistral-large-latest',
		deepseek: 'deepseek-v4-pro',
		perplexity: 'sonar',
		xai: 'grok-4.3',
		'ollama-cloud': 'gpt-oss:120b'
	};
	$: repModelId = (() => {
		const rec = RECOMMENDED_MODEL[provider.id];
		if (rec && provider.models?.some((m) => m.id === rec)) return rec;
		return provider.models?.[0]?.id;
	})();
	let caps: {
		reasoning?: boolean | null;
		vision?: boolean | null;
		tools?: boolean | null;
		context_window?: number | null;
	} | null = null;
	let capsFor = '';
	const loadCaps = async (mid: string) => {
		try {
			caps = await getModelCapabilities(localStorage.token, provider.id, mid);
		} catch {
			caps = null;
		}
	};
	$: if (repModelId && repModelId !== capsFor) {
		capsFor = repModelId;
		void loadCaps(repModelId);
	}
	const ctxLabel = (n: number | null | undefined) => {
		if (!n) return '';
		if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
		if (n >= 1000) return `${Math.round(n / 1000)}k`;
		return `${n}`;
	};
	let aboutOpen = false;
	// La plupart des logos sont en PNG ; seuls ces quelques-uns restent en SVG.
	const SVG_LOGOS = new Set(['api']);
	// Nous Portal : forcer le logo « NOUS RESEARCH » (boîte) côté front, sans dépendre du
	// rechargement du bridge. Les autres providers gardent le logo renvoyé par le bridge.
	$: logoFile = provider.id === 'nous' ? 'nous-research' : provider.logo;
	$: logoExt = SVG_LOGOS.has(logoFile) ? 'svg' : 'png';
	$: logoUrl = `${WEBUI_BASE_URL}/assets/providers/${logoFile}.${logoExt}`;
	// Logo « carré plein » → affiché bord à bord (remplit le carré) ; sinon icône sur fond blanc.
	$: fullBleed = PROVIDER_LOGO_FULL_BLEED.has(logoFile);

	const onError = (e: Event) => {
		(e.currentTarget as HTMLImageElement).src = `${WEBUI_BASE_URL}/assets/providers/api.svg`;
	};

	// --- Clé API (inline) ---
	let value = '';
	let show = false;
	let saving = false;
	let testing = false;

	const saveKey = async () => {
		if (!value) return;
		saving = true;
		try {
			// Le bridge auto-active ce fournisseur si aucun cerveau n'était encore actif
			// (« poser sa clé = ça marche tout de suite »). On adapte le message en conséquence.
			const r = await setProviderKey(localStorage.token, provider.id, value);
			if (r?.activated) {
				toast.success(
					$i18n.t('Clé enregistrée — votre assistant tourne maintenant sur {{name}}', {
						name: info.name ?? provider.label
					})
				);
			} else {
				toast.success($i18n.t('Clé enregistrée'));
			}
			value = '';
			replacing = false;
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible d’enregistrer la clé'));
		} finally {
			saving = false;
		}
	};

	// Déconnexion d'une clé API : confirmation inline (rien ne s'efface sans un « oui »).
	let confirmingDelete = false;
	let deleting = false;
	// « Remplacer la clé » : une fois connecté, la carte est calme ; on ne révèle le champ
	// de saisie que si l'utilisateur veut remplacer sa clé (sinon rien à saisir).
	let replacing = false;

	const disconnect = async () => {
		deleting = true;
		try {
			const r = await deleteProviderKey(localStorage.token, provider.id);
			if (r?.switched?.provider_id && r.switched.provider_id !== 'auto') {
				toast.success($i18n.t('Clé retirée — assistant basculé sur un autre modèle connecté'));
			} else if (r?.switched) {
				toast.success($i18n.t('Clé retirée — choisissez un nouveau cerveau'));
			} else {
				toast.success($i18n.t('Clé retirée'));
			}
			confirmingDelete = false;
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible de retirer la clé'));
		} finally {
			deleting = false;
		}
	};

	const testKey = async () => {
		if (!value) return;
		testing = true;
		try {
			const r = await validateProviderKey(localStorage.token, provider.id, value);
			if (r?.valid) toast.success($i18n.t('Clé valide'));
			else if (r?.reason === 'no_credit')
				// La clé est bonne, il manque juste du crédit chez le fournisseur.
				toast.warning(
					$i18n.t('Clé valide, mais compte sans crédit — ajoutez du crédit chez le fournisseur pour l’utiliser.')
				);
			else toast.error($i18n.t('Clé invalide') + (r?.reason ? ` (${r.reason})` : ''));
		} catch {
			toast.error($i18n.t('Impossible de tester la clé'));
		} finally {
			testing = false;
		}
	};

	// --- Credentials AWS (Bedrock, auth_type=aws_sdk) ---
	let awsKeyId = '';
	let awsSecret = '';
	let awsRegion = 'us-east-1';
	let savingAws = false;

	const saveAws = async () => {
		if (!awsKeyId || !awsSecret) return;
		savingAws = true;
		try {
			await setAwsCredentials(localStorage.token, provider.id, {
				access_key_id: awsKeyId,
				secret_access_key: awsSecret,
				region: awsRegion || undefined
			});
			toast.success($i18n.t('Credentials AWS enregistrés'));
			awsKeyId = '';
			awsSecret = '';
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible d’enregistrer les credentials AWS'));
		} finally {
			savingAws = false;
		}
	};

	// Le choix du modèle actif (et le changement de cerveau) se fait dans le chat, via le
	// sélecteur de cerveau — pas ici. La page « Modèles IA » sert à brancher les clés ;
	// à l'enregistrement, le bridge auto-active le fournisseur (voir saveKey).
</script>

<div
	class="flex flex-col gap-2.5 h-full p-4 rounded-2xl border border-gray-100 dark:border-gray-850 card-lift hover:border-gray-200 dark:hover:border-gray-700"
>
	<!-- En-tête : logo + nom + état -->
	<div class="flex items-center gap-2.5">
		<div
			class="flex-none size-12 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {fullBleed
				? ''
				: 'bg-white p-0.5'}"
		>
			<img
				src={logoUrl}
				on:error={onError}
				class={fullBleed ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
				alt={provider.label}
				draggable="false"
			/>
		</div>
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium">{info.name ?? provider.label}</div>
			<div class="text-xs text-gray-500">
				{info.desc ?? presentation.humanLabel ?? `${provider.models?.length ?? 0} ${$i18n.t('modèles')}`}
			</div>
		</div>
		<div class="flex-none flex items-center gap-1.5">
			{#if regionFlag}
				<span
					class="text-sm leading-none cursor-default"
					title={`${$i18n.t(regionName)} — ${$i18n.t('origine du fournisseur (pas une garantie d’hébergement des données)')}`}
					aria-label={$i18n.t(regionName)}
				>
					{regionFlag}
				</span>
			{/if}
			<!-- Toute clé qui marche = « Actif » (jamais « Configuré » : mot technique qui ne
			     parle pas au dirigeant). Le cerveau réellement utilisé se lit en haut de page
			     (« Modèle IA actif : … ») et dans le chat. -->
			{#if provider.state === 'active' || provider.state === 'configured'}
				<ActiveBadge />
			{/if}
		</div>
	</div>

	<!-- Badges métier curés (US3) : affichés seulement s'ils reflètent la nature réelle (D27). -->
	{#if presentation.badges.length > 0}
		<div class="flex flex-wrap gap-1">
			{#each presentation.badges as b (b)}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
					>{$i18n.t(b)}</span
				>
			{/each}
		</div>
	{/if}

	<!-- Capacités du modèle principal (Raisonnement/Vision/Outils/contexte). Même source
	     que le chat → honnête. Emoji pour distinguer des badges métier ci-dessus. -->
	{#if caps && (caps.reasoning || caps.vision || caps.tools || caps.context_window)}
		<div class="flex flex-wrap gap-1">
			{#if caps.reasoning}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-md bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
					>🧠 {$i18n.t('Raisonnement')}</span
				>
			{/if}
			{#if caps.vision}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-md bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
					>👁️ {$i18n.t('Vision')}</span
				>
			{/if}
			{#if caps.tools}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-md bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
					>🔧 {$i18n.t('Outils')}</span
				>
			{/if}
			{#if caps.context_window}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-md bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
					>📏 {ctxLabel(caps.context_window)} {$i18n.t('contexte')}</span
				>
			{/if}
		</div>
	{/if}

	<!-- Voir ce que ça fait (déroulant façon MCP / Intégrations). -->
	{#if info.about?.length}
		{#if !aboutOpen}
			<button
				type="button"
				class="self-start text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline"
				on:click={() => (aboutOpen = true)}
			>
				{$i18n.t('Voir ce que ça fait')} ›
			</button>
		{:else}
			<div class="flex flex-col gap-1.5">
				<div class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
					{$i18n.t('Ce que ça fait')}
				</div>
				<ul class="flex flex-col gap-1 pl-0.5">
					{#each info.about as line}
						<li class="flex items-start gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
							<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
							<span>{$i18n.t(line)}</span>
						</li>
					{/each}
				</ul>
				<button
					type="button"
					class="self-start text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
					on:click={() => (aboutOpen = false)}
				>
					{$i18n.t('Masquer')}
				</button>
			</div>
		{/if}
	{/if}

	<!-- Bloc de connexion collé en bas : aligne champ + Tester/Enregistrer entre les cartes,
	     quels que soient les badges/description au-dessus. -->
	<div class="mt-auto flex flex-col gap-2.5">
	<!-- Action de connexion selon la catégorie -->
	{#if provider.category === 'oauth'}
		<ProviderOAuth
			{provider}
			on:connected={() => dispatch('changed')}
			on:changed={() => dispatch('changed')}
		/>
		{#if info.usageUrl && provider.state !== 'not_configured'}
			<a
				href={info.usageUrl}
				target="_blank"
				rel="noopener"
				class="self-start text-xs text-sky-600 dark:text-sky-400 hover:underline"
			>
				{$i18n.t('Voir mon usage')} ›
			</a>
		{/if}
	{:else if provider.id === 'moa'}
		<!-- Mixture of Agents : technique interne du moteur, AUCUNE clé propre —
		     il combine les modèles déjà connectés. Pas de champ clé (ce serait trompeur). -->
		<div class="text-xs text-gray-500 leading-relaxed">
			{$i18n.t(
				'Pas de clé à saisir : Mixture of Agents combine les modèles que vous avez déjà connectés pour produire une meilleure réponse. Il se règle dans les options avancées du moteur.'
			)}
		</div>
	{:else if provider.category === 'api' || provider.category === 'local'}
		{#if configured && !replacing}
			<!-- Carte CALME (connectée) : on cache la mécanique, on montre juste l'état. -->
			<!-- « ✓ Clé connectée » toujours affiché : rassure le dirigeant que sa clé marche. -->
			<div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
				<svg class="size-4 flex-none text-green-600 dark:text-green-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path fill-rule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 10.7a1 1 0 1 1 1.4-1.4l3.1 3.1 6.8-6.8a1 1 0 0 1 1.4 0Z" clip-rule="evenodd" />
				</svg>
				<span>{$i18n.t('Clé connectée')}</span>
			</div>
			<div class="flex items-center justify-between gap-2">
				<!-- Voir sa conso / son quota chez le fournisseur (facturation à l'usage). -->
				{#if info.usageUrl}
					<a
						href={info.usageUrl}
						target="_blank"
						rel="noopener"
						class="text-xs text-sky-600 dark:text-sky-400 hover:underline"
					>
						{$i18n.t('Voir mon usage')} ›
					</a>
				{:else}
					<span></span>
				{/if}
				<div class="flex items-center gap-3">
					{#if confirmingDelete}
						<span class="text-xs text-gray-500">{$i18n.t('Retirer cette clé ?')}</span>
						<button
							type="button"
							class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
							on:click={() => (confirmingDelete = false)}
							disabled={deleting}
						>
							{$i18n.t('Annuler')}
						</button>
						<button
							type="button"
							class="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition disabled:opacity-40"
							on:click={disconnect}
							disabled={deleting}
						>
							{#if deleting}<Spinner className="size-3.5" />{:else}{$i18n.t('Confirmer')}{/if}
						</button>
					{:else}
						<button
							type="button"
							class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
							on:click={() => {
								replacing = true;
								value = '';
							}}
						>
							{$i18n.t('Remplacer la clé')}
						</button>
						<button
							type="button"
							class="text-xs text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition"
							on:click={() => (confirmingDelete = true)}
						>
							{$i18n.t('Déconnecter')}
						</button>
					{/if}
				</div>
			</div>
		{:else}
			<!-- Saisie : provider non connecté, OU on remplace une clé existante. -->
			<div class="flex items-center gap-2">
				<input
					class="flex-1 min-w-0 text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
					type={show ? 'text' : 'password'}
					placeholder={replacing
						? $i18n.t('Coller la nouvelle clé')
						: (info.name ?? provider.label) + ' — ' + $i18n.t('clé API')}
					bind:value
					autocomplete="off"
					on:keydown={(e) => e.key === 'Enter' && saveKey()}
				/>
				<!-- Afficher : seulement s'il y a quelque chose à révéler (l'utilisateur tape). -->
				{#if value}
					<button
						type="button"
						class="flex-none text-xs px-2 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => (show = !show)}
					>
						{show ? $i18n.t('Masquer') : $i18n.t('Afficher')}
					</button>
				{/if}
			</div>
			<div class="flex items-center justify-between gap-2">
				{#if info.keyUrl}
					<a
						href={info.keyUrl}
						target="_blank"
						rel="noopener"
						class="text-xs text-sky-600 dark:text-sky-400 hover:underline"
					>
						{$i18n.t('Obtenir la clé')} ›
					</a>
				{:else}
					<span></span>
				{/if}
				<div class="flex items-center gap-2">
					{#if replacing}
						<button
							type="button"
							class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
							on:click={() => {
								replacing = false;
								value = '';
							}}
						>
							{$i18n.t('Annuler')}
						</button>
					{/if}
					<button
						type="button"
						class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition disabled:opacity-40"
						disabled={!value || testing}
						on:click={testKey}
					>
						{#if testing}<Spinner className="size-3.5" />{:else}{$i18n.t('Tester')}{/if}
					</button>
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
						disabled={!value || saving}
						on:click={saveKey}
					>
						{#if saving}<Spinner className="size-3.5" />{:else}{$i18n.t('Enregistrer')}{/if}
					</button>
				</div>
			</div>
		{/if}
	{:else if provider.id === 'bedrock'}
		<!-- AWS Bedrock : credentials AWS (lus par le SDK de Hermes) -->
		<div class="flex flex-col gap-2">
			<input
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				type="text"
				placeholder={configured ? '••••••••  ' + $i18n.t('(remplacer)') : 'AWS Access Key ID'}
				bind:value={awsKeyId}
				autocomplete="off"
			/>
			<input
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				type="password"
				placeholder="AWS Secret Access Key"
				bind:value={awsSecret}
				autocomplete="off"
			/>
			<input
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				type="text"
				placeholder={$i18n.t('Région') + ' (ex : us-east-1)'}
				bind:value={awsRegion}
				autocomplete="off"
			/>
			<div class="flex items-center justify-end">
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
					disabled={!awsKeyId || !awsSecret || savingAws}
					on:click={saveAws}
				>
					{#if savingAws}<Spinner className="size-3.5" />{:else}{$i18n.t('Enregistrer')}{/if}
				</button>
			</div>
		</div>
	{:else}
		<div class="text-xs text-gray-500 leading-relaxed">
			{$i18n.t(
				'Connexion via le CLI GitHub Copilot authentifié sur la machine hôte (login externe) — rien à configurer ici.'
			)}
		</div>
	{/if}

	<!-- Rappel discret sous CHAQUE clé connectée : le choix du cerveau se fait dans le chat. -->
	{#if configured}
		<div class="pt-2 border-t border-gray-100 dark:border-gray-850 text-xs text-gray-500">
			{$i18n.t('Changez de modèle dans le chat, en haut à gauche.')}
		</div>
	{/if}
	</div>
</div>
