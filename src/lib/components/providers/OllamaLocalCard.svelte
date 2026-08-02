<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import {
		activerServeurPersonnalise,
		enregistrerServeurPersonnalise,
		verifierServeurPersonnalise
	} from '$lib/apis/hermes';
	import { providerLogoUrl, PROVIDER_LOGO_FALLBACK } from '$lib/utils/providerLogos';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let provider: {
		id: string;
		label: string;
		logo: string;
		state: 'active' | 'configured' | 'not_configured';
		base_url?: string | null;
		endpoint_id?: string | null;
		models?: { id: string; label: string }[];
	};

	let baseUrl = provider.base_url || 'http://host.docker.internal:11434/v1';
	let model = provider.models?.[0]?.id ?? '';
	let detectedModels = provider.models?.map((item) => item.id) ?? [];
	let testing = false;
	let saving = false;
	let activating = false;
	let message = '';

	$: configured = provider.state !== 'not_configured';
	$: active = provider.state === 'active';
	$: busy = testing || saving || activating;

	const payload = () => ({
		id: provider.endpoint_id || 'ollama-local',
		name: 'Ollama',
		base_url: baseUrl.trim().replace(/\/$/, ''),
		model: model.trim(),
		models: detectedModels,
		discover_models: true,
		make_default: false
	});

	const test = async () => {
		if (!baseUrl.trim() || busy) return;
		testing = true;
		message = '';
		try {
			const result = await verifierServeurPersonnalise(localStorage.token, payload());
			detectedModels = result?.models ?? [];
			if (!result?.ok) {
				message = result?.message || $i18n.t('Ollama n’a pas répondu correctement.');
				return;
			}
			if (!model && detectedModels.length) model = detectedModels[0];
			message = $i18n.t('{{count}} modèle(s) détecté(s).', {
				count: detectedModels.length
			});
		} catch (error) {
			message = `${error}`;
		} finally {
			testing = false;
		}
	};

	const save = async () => {
		if (!baseUrl.trim() || !model.trim() || busy) return;
		saving = true;
		message = '';
		try {
			await enregistrerServeurPersonnalise(localStorage.token, payload());
			toast.success($i18n.t('Ollama est enregistré'));
			dispatch('changed');
		} catch (error) {
			message = `${error}`;
		} finally {
			saving = false;
		}
	};

	const activate = async () => {
		const endpointId = provider.endpoint_id || 'ollama-local';
		if (!configured || active || busy) return;
		activating = true;
		try {
			await activerServeurPersonnalise(localStorage.token, endpointId);
			toast.success($i18n.t('Ollama est maintenant le modèle IA actif'));
			dispatch('changed');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			activating = false;
		}
	};

	const onLogoError = (event: Event) => {
		(event.currentTarget as HTMLImageElement).src = PROVIDER_LOGO_FALLBACK;
	};
</script>

<article
	class="card-lift flex min-h-64 flex-col gap-3 rounded-2xl border border-gray-100 bg-white p-4 dark:border-gray-850 dark:bg-gray-900"
>
	<div class="flex items-start gap-3">
		<div
			class="flex size-12 flex-none items-center justify-center overflow-hidden rounded-xl border border-gray-100 bg-white p-0.5 dark:border-gray-700"
		>
			<img
				src={providerLogoUrl(provider)}
				alt=""
				class="size-full object-contain"
				draggable="false"
				on:error={onLogoError}
			/>
		</div>
		<div class="min-w-0 flex-1">
			<div class="flex items-start justify-between gap-2">
				<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Ollama</h3>
				{#if active}
					<ActiveBadge label={$i18n.t('Actif')} />
				{:else if configured}
					<span class="text-xs font-medium text-green-600 dark:text-green-400">
						{$i18n.t('Connecté')}
					</span>
				{/if}
			</div>
			<p class="mt-1 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
				{$i18n.t('Ollama — un modèle sur votre machine.')}
			</p>
		</div>
	</div>

	<div class="flex flex-wrap gap-1">
		<span
			class="rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-850 dark:text-gray-300"
		>
			{$i18n.t('Local')}
		</span>
		<span
			class="rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-850 dark:text-gray-300"
		>
			{$i18n.t('Confidentiel')}
		</span>
	</div>

	<div class="mt-auto flex flex-col gap-2">
		<input
			class="min-w-0 rounded-xl border border-gray-100 bg-transparent px-3 py-2 text-sm outline-none dark:border-gray-850"
			bind:value={baseUrl}
			placeholder="http://host.docker.internal:11434/v1"
			autocomplete="url"
		/>

		{#if detectedModels.length}
			<select
				class="min-w-0 rounded-xl border border-gray-100 bg-transparent px-3 py-2 text-sm outline-none dark:border-gray-850 dark:bg-gray-900"
				bind:value={model}
			>
				{#each detectedModels as item}
					<option value={item}>{item}</option>
				{/each}
			</select>
		{:else}
			<input
				class="min-w-0 rounded-xl border border-gray-100 bg-transparent px-3 py-2 text-sm outline-none dark:border-gray-850"
				bind:value={model}
				placeholder={$i18n.t('Testez l’adresse pour détecter les modèles')}
			/>
		{/if}

		{#if message}
			<p class="text-xs text-gray-500 dark:text-gray-400">{message}</p>
		{/if}

		<div class="flex items-center justify-end gap-2">
			{#if configured && !active}
				<button
					type="button"
					class="rounded-lg px-2 py-1 text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40 dark:hover:text-gray-200"
					disabled={busy}
					on:click={activate}
				>
					{#if activating}<Spinner className="size-3.5" />{:else}{$i18n.t('Utiliser')}{/if}
				</button>
			{/if}
			<button
				type="button"
				class="rounded-lg px-2 py-1 text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40 dark:hover:text-gray-200"
				disabled={!baseUrl.trim() || busy}
				on:click={test}
			>
				{#if testing}<Spinner className="size-3.5" />{:else}{$i18n.t('Tester')}{/if}
			</button>
			<button
				type="button"
				class="btn-premium rounded-lg bg-black px-3 py-1.5 text-xs text-white disabled:opacity-40 dark:bg-white dark:text-black"
				disabled={!baseUrl.trim() || !model.trim() || busy}
				on:click={save}
			>
				{#if saving}<Spinner className="size-3.5" />{:else}{$i18n.t('Enregistrer')}{/if}
			</button>
		</div>
	</div>
</article>
