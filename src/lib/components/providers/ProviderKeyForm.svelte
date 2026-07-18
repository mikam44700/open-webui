<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { setProviderKey, validateProviderKey } from '$lib/apis/providers';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let provider: {
		id: string;
		label: string;
		state: 'active' | 'configured' | 'not_configured';
		env_key?: string | null;
	};

	let value = '';
	let show = false;
	let saving = false;
	let testing = false;
	// Verrou partagé Tester/Enregistrer : même champ (la clé saisie) touché par les deux
	// actions — sans lui, des requêtes se chevauchent sur la même clé (issue #3 de l'audit).
	let busy = false;

	$: configured = provider.state !== 'not_configured';

	const test = async () => {
		if (!value || busy) return;
		busy = true;
		testing = true;
		try {
			const res = await validateProviderKey(localStorage.token, provider.id, value);
			if (res?.valid) {
				toast.success($i18n.t('Clé valide'));
			} else {
				toast.error($i18n.t('Clé invalide') + (res?.reason ? ` (${res.reason})` : ''));
			}
		} catch (err) {
			toast.error($i18n.t('Impossible de tester la clé'));
		} finally {
			testing = false;
			busy = false;
		}
	};

	const save = async () => {
		if (!value || busy) return;
		busy = true;
		saving = true;
		try {
			await setProviderKey(localStorage.token, provider.id, value);
			toast.success($i18n.t('Clé enregistrée'));
			value = '';
			dispatch('saved');
		} catch (err) {
			toast.error($i18n.t('Impossible d’enregistrer la clé'));
		} finally {
			saving = false;
			busy = false;
		}
	};
</script>

<div class="flex flex-col gap-2">
	<div class="text-xs text-gray-500">
		{#if configured}
			{$i18n.t('Une clé est déjà configurée. Saisis-en une nouvelle pour la remplacer.')}
		{:else}
			{$i18n.t('Saisis la clé API de ce modèle IA.')}
		{/if}
		{#if provider.env_key}
			<span class="text-gray-400">({provider.env_key})</span>
		{/if}
	</div>

	<div class="flex items-center gap-2">
		<input
			class="flex-1 text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
			type={show ? 'text' : 'password'}
			placeholder="sk-..."
			bind:value
			autocomplete="off"
		/>
		<button
			type="button"
			class="text-xs px-2 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
			on:click={() => (show = !show)}
		>
			{show ? $i18n.t('Masquer') : $i18n.t('Afficher')}
		</button>
	</div>

	<div class="flex justify-end gap-2">
		<button
			type="button"
			class="text-sm px-3 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-50"
			disabled={!value || busy}
			on:click={test}
		>
			{#if testing}
				<Spinner className="size-4" />
			{:else}
				{$i18n.t('Tester')}
			{/if}
		</button>
		<button
			type="button"
			class="text-sm px-3 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-50"
			disabled={!value || busy}
			on:click={save}
		>
			{#if saving}
				<Spinner className="size-4" />
			{:else}
				{$i18n.t('Enregistrer la clé')}
			{/if}
		</button>
	</div>
</div>
