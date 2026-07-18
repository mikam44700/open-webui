<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getToolConnection } from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderConnectCard from '$lib/components/capabilities/ProviderConnectCard.svelte';
	import { TOOLSET_FR } from '$lib/utils/toolsetLabels';
	import { type Provider, CATEGORY_ORDER, CATEGORY_LABEL } from '$lib/utils/toolConnect';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;
	export let toolset: { name: string; label: string } | null = null;

	let loading = false;
	let providers: Provider[] = [];
	// Encart d'information optionnel affiché en haut (ex. vision : « si ton modèle gère les images… »).
	let note: string | null = null;
	// Fournisseurs techniques (clé API ou serveur à lancer) repliés sous « Options avancées ».
	let showAdvanced = false;
	$: standardProviders = providers.filter((p) => !p.advanced);
	$: advancedProviders = providers.filter((p) => p.advanced);
	// Avancés regroupés par catégorie (gratuit → auto-hébergé → payant), groupes vides masqués.
	$: advancedByCategory = CATEGORY_ORDER.map((cat) => ({
		cat,
		items: advancedProviders.filter((p) => (p.category ?? 'paid') === cat)
	})).filter((g) => g.items.length > 0);

	const load = async () => {
		if (!toolset) return;
		loading = true;
		try {
			const res = await getToolConnection(localStorage.token, toolset.name);
			providers = res?.providers ?? [];
			note = res?.note ?? null;
			showAdvanced = false;
		} catch {
			toast.error($i18n.t('Impossible de charger la connexion de cet outil'));
		} finally {
			loading = false;
		}
	};

	$: if (open && toolset) {
		load();
	}

	const close = () => dispatch('close');
	// Une carte a changé d'état (clé enregistrée / déconnectée / OAuth réussi) → on remonte au parent.
	const onChanged = () => dispatch('connected');
</script>

{#if open && toolset}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click|self={close}
	>
		<div
			class="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-xl"
		>
			<div class="flex items-center justify-between mb-3">
				<div class="text-sm font-medium">
					{$i18n.t('Connecter')} — {TOOLSET_FR[toolset.name]?.label ?? toolset.label}
				</div>
				<button
					class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
					on:click={close}>✕</button
				>
			</div>

			{#if loading}
				<div class="flex justify-center py-10"><Spinner className="size-5" /></div>
			{:else}
				{#if note}
					<div
						class="text-xs leading-relaxed text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-900/40 rounded-xl px-3 py-2.5 mb-3"
					>
						{note}
					</div>
				{/if}

				{#each standardProviders as provider (provider.name)}
					<ProviderConnectCard toolsetName={toolset.name} {provider} on:changed={onChanged} />
				{/each}

				{#if advancedProviders.length > 0}
					<button
						type="button"
						class="w-full flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition mb-3"
						on:click={() => (showAdvanced = !showAdvanced)}
					>
						<span class="font-medium"
							>{$i18n.t('Options avancées (Expert)')} · {advancedProviders.length}</span
						>
						<span aria-hidden="true">{showAdvanced ? '▴' : '▾'}</span>
					</button>
					{#if showAdvanced}
						<div class="text-[11px] text-gray-400 mb-3 -mt-1 px-1">
							{$i18n.t(
								'Pour utilisateurs avancés : nécessite une clé API ou un serveur à lancer soi-même.'
							)}
						</div>
						{#each advancedByCategory as group (group.cat)}
							<div
								class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2 px-1"
							>
								{CATEGORY_LABEL[group.cat]}
							</div>
							{#each group.items as provider (provider.name)}
								<ProviderConnectCard toolsetName={toolset.name} {provider} on:changed={onChanged} />
							{/each}
						{/each}
					{/if}
				{/if}

				{#if providers.length === 0}
					<div class="text-xs text-gray-500 py-4">
						{$i18n.t('Aucune connexion requise pour cet outil.')}
					</div>
				{/if}

				<div class="flex justify-end mt-4">
					<button
						class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						on:click={close}
					>
						{$i18n.t('Fermer')}
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}
