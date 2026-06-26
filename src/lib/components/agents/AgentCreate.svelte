<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import { createAgent } from '$lib/apis/agents';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let name = '';
	let description = '';
	let soul = '';
	let saving = false;

	const inputClass =
		'w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none';

	const reset = () => {
		name = '';
		description = '';
		soul = '';
		saving = false;
	};

	const submit = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Donnez un nom à votre agent'));
			return;
		}
		saving = true;
		try {
			const res = await createAgent(localStorage.token, {
				name: name.trim(),
				description: description.trim(),
				soul: soul.trim()
			});
			toast.success($i18n.t('Agent créé'));
			reset();
			show = false;
			dispatch('created', res);
		} catch (err) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Un agent porte déjà ce nom'));
			} else {
				toast.error($i18n.t('Impossible de créer cet agent'));
			}
			saving = false;
		}
	};
</script>

<Modal bind:show size="md">
	<div class="p-5">
		<div class="flex items-center justify-between mb-1">
			<div class="text-lg font-medium">{$i18n.t('Créer un agent')}</div>
			<button
				class="text-gray-400 hover:text-gray-700 dark:hover:text-white"
				on:click={() => (show = false)}>✕</button
			>
		</div>
		<div class="text-xs text-gray-500 mb-4">
			{$i18n.t('Un collègue numérique spécialisé sur un métier ou un process.')}
		</div>

		<div class="space-y-4">
			<div>
				<div class="text-xs text-gray-500 mb-1">{$i18n.t('Nom de l’agent')}</div>
				<input bind:value={name} placeholder={$i18n.t('Ex : Assistant RH')} class={inputClass} />
			</div>
			<div>
				<div class="text-xs text-gray-500 mb-1">{$i18n.t('En une phrase, à quoi sert-il ?')}</div>
				<input
					bind:value={description}
					placeholder={$i18n.t('Ex : Gère les congés et les contrats')}
					class={inputClass}
				/>
			</div>
			<div>
				<div class="text-xs text-gray-500 mb-1">
					{$i18n.t('Que doit faire cet agent ? (sa mission)')}
				</div>
				<textarea
					bind:value={soul}
					rows="6"
					placeholder={$i18n.t('Décris en langage normal ce qu’il doit faire, son ton, ses règles…')}
					class="{inputClass} resize-none"
				></textarea>
			</div>
		</div>

		<div class="flex justify-end gap-2 mt-5">
			<button
				class="text-sm px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => (show = false)}>{$i18n.t('Annuler')}</button
			>
			<button
				class="text-sm px-4 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-50"
				disabled={saving}
				on:click={submit}
			>
				{saving ? $i18n.t('Création…') : $i18n.t('Créer l’agent')}
			</button>
		</div>
	</div>
</Modal>
