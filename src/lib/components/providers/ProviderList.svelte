<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getProviders, getActiveProvider, setActiveProvider } from '$lib/apis/providers';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderCard from './ProviderCard.svelte';
	import ModelSelect from './ModelSelect.svelte';

	const i18n = getContext('i18n');

	type Model = { id: string; label: string };
	type Provider = {
		id: string;
		label: string;
		logo: string;
		state: 'active' | 'configured' | 'not_configured';
		models?: Model[];
	};

	let loading = true;
	let bridgeDown = false;

	let providers: Provider[] = [];
	let active: { provider_id: string; model_id: string } | null = null;

	let search = '';
	let selected: Provider | null = null;
	let selectedModel = '';
	let applying = false;

	$: filtered = search.trim()
		? providers.filter(
				(p) =>
					p.label.toLowerCase().includes(search.toLowerCase()) ||
					p.id.toLowerCase().includes(search.toLowerCase())
			)
		: providers;

	const isBridgeDown = (err: any) => err?.error?.code === 'bridge_unreachable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const token = localStorage.token;
			const [provRes, activeRes] = await Promise.all([
				getProviders(token),
				getActiveProvider(token).catch(() => null)
			]);
			providers = provRes?.providers ?? [];
			active = activeRes;
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Failed to load providers'));
			}
		} finally {
			loading = false;
		}
	};

	const onSelect = (e: CustomEvent<Provider>) => {
		const provider = e.detail;
		if (provider.state === 'not_configured') {
			toast.error($i18n.t('This provider has no credentials configured yet'));
			return;
		}
		selected = provider;
		// pré-sélectionne le modèle actif si c'est le provider courant, sinon le premier
		selectedModel =
			active?.provider_id === provider.id
				? active.model_id
				: (provider.models?.[0]?.id ?? '');
	};

	const apply = async () => {
		if (!selected || !selectedModel) return;
		applying = true;
		try {
			await setActiveProvider(localStorage.token, selected.id, selectedModel);
			toast.success($i18n.t('Active brain updated (applies to new conversations)'));
			selected = null;
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'not_configured') {
				toast.error($i18n.t('This provider is not configured'));
			} else {
				toast.error($i18n.t('Failed to update the active brain'));
			}
		} finally {
			applying = false;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-5xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<!-- T021 : état dégradé, bridge injoignable -->
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('The Providers service is unreachable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('The bridge to Hermes is not responding. Make sure it is running, then retry.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Retry')}
			</button>
		</div>
	{:else}
		<!-- cerveau actif courant -->
		<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
			{#if active}
				{$i18n.t('Active brain')}:
				<span class="font-medium text-gray-900 dark:text-gray-100">{active.provider_id}</span>
				/ {active.model_id}
			{:else}
				{$i18n.t('No active brain selected')}
			{/if}
		</div>

		<!-- FR-012 : recherche providers -->
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Search a provider')}
			bind:value={search}
		/>

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
			{#each filtered as provider (provider.id)}
				<ProviderCard
					{provider}
					selected={selected?.id === provider.id}
					on:select={onSelect}
				/>
			{/each}
		</div>

		{#if filtered.length === 0}
			<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('No provider found')}</div>
		{/if}

		<!-- panneau de sélection du modèle pour le provider choisi -->
		{#if selected}
			<div class="mt-4 p-4 border border-gray-100 dark:border-gray-850 rounded-2xl">
				<div class="text-sm font-medium mb-2">
					{$i18n.t('Choose a model for')}
					{selected.label}
				</div>

				{#if (selected.models?.length ?? 0) > 0}
					<ModelSelect
						models={selected.models ?? []}
						value={selectedModel}
						on:change={(e) => (selectedModel = e.detail)}
					/>
				{:else}
					<div class="text-xs text-gray-500">{$i18n.t('No model available for this provider')}</div>
				{/if}

				<div class="flex justify-end gap-2 mt-3">
					<button
						class="text-sm px-3 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => (selected = null)}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="text-sm px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-50"
						disabled={!selectedModel || applying}
						on:click={apply}
					>
						{#if applying}
							<Spinner className="size-4" />
						{:else}
							{$i18n.t('Set as active brain')}
						{/if}
					</button>
				</div>
			</div>
		{/if}
	{/if}
</div>
