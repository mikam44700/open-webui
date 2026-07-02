<script lang="ts">
	import { getContext, onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import { getModelPresentation } from '$lib/catalog/model-badges';
	import { PROVIDER_INFO } from '$lib/catalog/provider-info';
	import { PROVIDER_LOGO_FULL_BLEED } from '$lib/utils/providerLogos';
	import { getMoaConfig, setMoaConfig, activateMoa, deactivateMoa } from '$lib/apis/moa-hermes';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// La carte MoA (provider « moa ») + la liste complète des fournisseurs (pour connaître
	// les cerveaux déjà connectés, candidats proposeurs / agrégateur).
	export let provider: { id: string; label: string; logo: string };
	export let providers: Array<{
		id: string;
		label: string;
		state: string;
		models?: { id: string; label: string }[];
	}> = [];

	type Opt = { provider: string; model: string; label: string };

	// Cerveaux connectés = candidats. On exclut moa (récursion) et sakana (déjà multi-agents).
	$: options = providers
		.filter((p) => p.state !== 'not_configured' && p.id !== 'moa' && p.id !== 'sakana')
		.map(
			(p) => ({ provider: p.id, model: p.models?.[0]?.id ?? 'default', label: p.label }) as Opt
		);

	let selected = new Set<string>();
	let aggregator = '';
	let loading = true;
	let activating = false;
	let active = false;
	// Force le re-rendu de l'interrupteur pour qu'il reflète TOUJOURS `active` (même après échec).
	let nonce = 0;

	$: presentation = getModelPresentation(provider.id);
	$: info = PROVIDER_INFO[provider.id] ?? {};
	$: logoFull = PROVIDER_LOGO_FULL_BLEED.has(provider.logo);
	$: logoUrl = `${WEBUI_BASE_URL}/assets/providers/${provider.logo}.png`;

	$: proposers = options.filter((o) => selected.has(o.provider));
	$: canSave = proposers.length >= 2 && !!aggregator;

	onMount(async () => {
		try {
			const cfg = await getMoaConfig(localStorage.token);
			active = cfg.active;
			selected = new Set((cfg.reference_models ?? []).map((s) => s.provider));
			aggregator = (cfg.aggregator as any)?.provider ?? '';
		} catch {
			// preset absent / bridge indispo : on démarre vierge, sans crier.
		} finally {
			loading = false;
		}
	});

	const buildPayload = () => {
		const refs = proposers.map((o) => ({ provider: o.provider, model: o.model }));
		const agg = options.find((o) => o.provider === aggregator);
		return { refs, agg };
	};

	// Si MoA est actif et qu'on modifie la sélection, on resauvegarde en silence pour que
	// la config active reste à jour.
	const persistIfActive = async () => {
		if (!active || !canSave) return;
		try {
			const { refs, agg } = buildPayload();
			await setMoaConfig(localStorage.token, refs, agg!);
		} catch {
			// silencieux : la sauvegarde explicite se refait à la prochaine bascule
		}
	};

	const toggle = (id: string) => {
		const n = new Set(selected);
		n.has(id) ? n.delete(id) : n.add(id);
		selected = n;
		void persistIfActive();
	};

	// Interrupteur ON/OFF : allume (enregistre + active) ou éteint (revient au cerveau précédent).
	const onSwitch = async () => {
		activating = true;
		try {
			if (!active) {
				const { refs, agg } = buildPayload();
				await setMoaConfig(localStorage.token, refs, agg!);
				await activateMoa(localStorage.token);
				active = true;
				toast.success(
					$i18n.t('Mixture of Agents activé — le chat combine désormais vos cerveaux')
				);
			} else {
				await deactivateMoa(localStorage.token);
				active = false;
				toast.success($i18n.t('Mixture of Agents éteint — retour à votre cerveau habituel'));
			}
			dispatch('changed');
		} catch (e: any) {
			toast.error(e?.error?.message ?? e?.message ?? $i18n.t('Changement impossible'));
		} finally {
			activating = false;
			nonce++; // resynchronise l'interrupteur sur l'état réel (succès comme échec)
		}
	};
</script>

<div
	class="flex flex-col gap-2.5 h-full p-4 rounded-2xl border border-gray-100 dark:border-gray-850 transition"
>
	<!-- En-tête -->
	<div class="flex items-center gap-2.5">
		<div
			class="flex-none size-12 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {logoFull
				? ''
				: 'bg-white p-0.5'}"
		>
			<img
				src={logoUrl}
				class={logoFull ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
				alt={provider.label}
				draggable="false"
			/>
		</div>
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium">{provider.label}</div>
			<div class="text-xs text-gray-500">
				{info.desc ?? $i18n.t('Combine plusieurs cerveaux')}
			</div>
		</div>
		{#if active}
			<Badge type="success" content={$i18n.t('Actif')} />
		{/if}
	</div>

	<!-- Badges -->
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

	<div class="mt-auto flex flex-col gap-2.5 pt-1">
		{#if loading}
			<div class="flex justify-center py-4"><Spinner className="size-5" /></div>
		{:else if options.length < 2}
			<!-- Garde-fou : il faut au moins 2 cerveaux connectés -->
			<div class="text-xs text-gray-500 leading-relaxed">
				{$i18n.t(
					'Connecte d’abord au moins 2 cerveaux (onglet Clés API) — Mixture of Agents les combine ensuite ici.'
				)}
			</div>
		{:else}
			<!-- Proposeurs -->
			<div class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
				{$i18n.t('Les cerveaux à combiner')}
			</div>
			<div class="flex flex-col gap-1">
				{#each options as o (o.provider)}
					<label class="flex items-center gap-2 text-sm cursor-pointer">
						<input
							type="checkbox"
							class="rounded"
							checked={selected.has(o.provider)}
							on:change={() => toggle(o.provider)}
						/>
						<span class="truncate">{o.label}</span>
					</label>
				{/each}
			</div>

			<!-- Agrégateur -->
			<div
				class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mt-1"
			>
				{$i18n.t('Le chef de synthèse')}
			</div>
			<select
				bind:value={aggregator}
				on:change={persistIfActive}
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
			>
				<option value="">{$i18n.t('Choisir un modèle…')}</option>
				{#each options as o (o.provider)}
					<option value={o.provider}>{o.label}</option>
				{/each}
			</select>

			<!-- Interrupteur ON/OFF (le point d'activation depuis Modèles IA) -->
			<div
				class="mt-1 flex items-center justify-between gap-2 pt-2 border-t border-gray-100 dark:border-gray-850"
			>
				<div class="min-w-0">
					<div class="text-sm text-gray-900 dark:text-white">
						{$i18n.t('Utiliser Mixture of Agents')}
					</div>
					<div class="text-[11px] text-gray-400">
						{#if active}
							{$i18n.t('Actif — le chat combine vos cerveaux')}
						{:else if canSave}
							{proposers.length} {$i18n.t('cerveaux + un chef, prêt à activer')}
						{:else}
							{$i18n.t('Choisis au moins 2 cerveaux + un chef de synthèse')}
						{/if}
					</div>
				</div>
				{#if activating}
					<Spinner className="size-4" />
				{:else if active || canSave}
					{#key nonce}
						<Switch state={active} on:change={onSwitch} />
					{/key}
				{:else}
					<!-- pas encore configurable : interrupteur inactif visuel -->
					<div class="opacity-40 pointer-events-none">
						<Switch state={false} />
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
