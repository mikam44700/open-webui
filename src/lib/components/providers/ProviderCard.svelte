<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Badge from '$lib/components/common/Badge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderOAuth from './ProviderOAuth.svelte';
	import { setProviderKey, validateProviderKey, setActiveProvider } from '$lib/apis/providers';

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
	// La plupart des logos sont en PNG ; seuls ces quelques-uns restent en SVG.
	const SVG_LOGOS = new Set(['api']);
	$: logoExt = SVG_LOGOS.has(provider.logo) ? 'svg' : 'png';
	$: logoUrl = `${WEBUI_BASE_URL}/assets/providers/${provider.logo}.${logoExt}`;

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
			if (e?.error?.code === 'not_configured') toast.error($i18n.t('Ce provider n’est pas configuré'));
			else toast.error($i18n.t('Échec de la mise à jour du cerveau actif'));
		} finally {
			activating = false;
		}
	};
</script>

<div class="flex flex-col gap-2.5 p-3.5 rounded-2xl border border-gray-100 dark:border-gray-850">
	<!-- En-tête : logo + nom + état -->
	<div class="flex items-center gap-2.5">
		<div
			class="flex-none size-8 rounded-lg overflow-hidden ring-1 ring-gray-200/70 dark:ring-gray-700/60"
		>
			<img src={logoUrl} on:error={onError} class="w-full h-full object-cover" alt={provider.label} draggable="false" />
		</div>
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium line-clamp-1">{provider.label}</div>
			<div class="text-xs text-gray-500 line-clamp-1">{provider.models?.length ?? 0} {$i18n.t('modèles')}</div>
		</div>
		<Badge type={badge.type} content={$i18n.t(badge.label)} />
	</div>

	<!-- Action de connexion selon la catégorie -->
	{#if provider.category === 'oauth'}
		<ProviderOAuth {provider} on:connected={() => dispatch('changed')} />
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
		<div class="flex items-center justify-end gap-2">
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
				class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
				disabled={!value || saving}
				on:click={saveKey}
			>
				{#if saving}<Spinner className="size-3.5" />{:else}{$i18n.t('Enregistrer')}{/if}
			</button>
		</div>
	{:else}
		<div class="text-xs text-gray-500">{$i18n.t('Authentification externe (AWS / Copilot).')}</div>
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
