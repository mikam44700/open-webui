<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Badge from '$lib/components/common/Badge.svelte';
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
		setActiveProvider,
		setAwsCredentials
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

	const badgeByState: Record<string, { type: string; label: string }> = {
		active: { type: 'success', label: 'Actif' },
		configured: { type: 'info', label: 'Configuré' },
		not_configured: { type: 'muted', label: 'Non configuré' }
	};

	$: badge = badgeByState[provider.state] ?? badgeByState['not_configured'];
	$: configured = provider.state !== 'not_configured';
	// Présentation métier curée (libellé humain + badges) — repli neutre si inconnu (D27).
	$: presentation = getModelPresentation(provider.id);
	// Infos client : phrase grise courte, « Voir ce que ça fait », lien « Obtenir la clé ».
	$: info = PROVIDER_INFO[provider.id] ?? {};
	// Origine / juridiction du fournisseur (souveraineté) — drapeau + nom au survol.
	$: regionFlag = getProviderRegionFlag(provider.id);
	$: regionName = getProviderRegionName(provider.id);
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
			await setProviderKey(localStorage.token, provider.id, value);
			toast.success($i18n.t('Clé enregistrée'));
			value = '';
			dispatch('changed');
		} catch {
			toast.error($i18n.t('Impossible d’enregistrer la clé'));
		} finally {
			saving = false;
		}
	};

	const testKey = async () => {
		if (!value) return;
		testing = true;
		try {
			const r = await validateProviderKey(localStorage.token, provider.id, value);
			if (r?.valid) toast.success($i18n.t('Clé valide'));
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

	// --- Modèle actif (inline, pour providers connectés avec des modèles) ---
	let chosenModel = '';
	$: if (provider.state === 'active' && !chosenModel) {
		chosenModel = activeModelId || provider.models?.[0]?.id || '';
	}
	let activating = false;

	const activate = async () => {
		const m = chosenModel || provider.models?.[0]?.id;
		if (!m) return;
		activating = true;
		try {
			await setActiveProvider(localStorage.token, provider.id, m);
			toast.success($i18n.t('Cerveau actif mis à jour'));
			dispatch('changed');
		} catch (e: any) {
			if (e?.error?.code === 'not_configured') toast.error($i18n.t('Ce modèle IA n’est pas configuré'));
			else toast.error($i18n.t('Échec de la mise à jour du cerveau actif'));
		} finally {
			activating = false;
		}
	};
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
			<div class="text-sm font-medium">{provider.label}</div>
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
			{#if provider.state === 'active'}
				<ActiveBadge />
			{:else if provider.state === 'configured'}
				<Badge type="info" content={$i18n.t('Configuré')} />
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
		<ProviderOAuth {provider} on:connected={() => dispatch('changed')} />
	{:else if provider.id === 'moa'}
		<!-- Mixture of Agents : technique interne du moteur, AUCUNE clé propre —
		     il combine les modèles déjà connectés. Pas de champ clé (ce serait trompeur). -->
		<div class="text-xs text-gray-500 leading-relaxed">
			{$i18n.t(
				'Pas de clé à saisir : Mixture of Agents combine les modèles que vous avez déjà connectés pour produire une meilleure réponse. Il se règle dans les options avancées du moteur.'
			)}
		</div>
	{:else if provider.category === 'api' || provider.category === 'local'}
		<div class="flex items-center gap-2">
			<input
				class="flex-1 min-w-0 text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				type={show ? 'text' : 'password'}
				placeholder={configured ? '••••••••  ' + $i18n.t('(remplacer)') : provider.label + ' — ' + $i18n.t('clé API')}
				bind:value
				autocomplete="off"
				on:keydown={(e) => e.key === 'Enter' && saveKey()}
			/>
			<button
				type="button"
				class="flex-none text-xs px-2 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={() => (show = !show)}
			>
				{show ? $i18n.t('Masquer') : $i18n.t('Afficher')}
			</button>
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

	<!-- Choix du modèle + activation (providers connectés avec modèles) -->
	{#if configured && (provider.models?.length ?? 0) > 0}
		<div class="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-850">
			<select
				class="flex-1 min-w-0 text-xs bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-2 py-1.5 outline-none"
				bind:value={chosenModel}
			>
				{#each provider.models ?? [] as m (m.id)}
					<option value={m.id}>{m.label}</option>
				{/each}
			</select>
			<button
				type="button"
				class="flex-none text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-40"
				disabled={activating || provider.state === 'active'}
				on:click={activate}
			>
				{#if activating}
					<Spinner className="size-3.5" />
				{:else if provider.state === 'active'}
					{$i18n.t('Cerveau actif')}
				{:else}
					{$i18n.t('Activer')}
				{/if}
			</button>
		</div>
	{/if}
	</div>
</div>
