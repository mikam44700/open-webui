<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { addCustomConnector } from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;

	let name = '';
	let transport = 'http';
	let url = '';
	let command = '';
	let argsText = '';
	let envText = '';
	let authType = 'none';
	let saving = false;

	const reset = () => {
		name = '';
		transport = 'http';
		url = '';
		command = '';
		argsText = '';
		envText = '';
		authType = 'none';
	};

	const parseArgs = (value: string): string[] =>
		value
			.split(/\r?\n/)
			.map((l) => l.trim())
			.filter(Boolean);

	const parseEnv = (value: string): Record<string, string> => {
		const env: Record<string, string> = {};
		for (const line of value.split(/\r?\n/)) {
			const eq = line.trim().indexOf('=');
			if (eq > 0) env[line.slice(0, eq).trim()] = line.slice(eq + 1).trim();
		}
		return env;
	};

	const close = () => {
		dispatch('close');
	};

	const submit = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Le nom est requis'));
			return;
		}
		if (transport === 'http' && !url.trim()) {
			toast.error($i18n.t('L’URL est requise'));
			return;
		}
		if (transport === 'stdio' && !command.trim()) {
			toast.error($i18n.t('La commande est requise'));
			return;
		}
		saving = true;
		try {
			const payload: any = { name: name.trim(), transport, auth_type: authType };
			if (transport === 'http') {
				payload.url = url.trim();
			} else {
				payload.command = command.trim();
				const args = parseArgs(argsText);
				const env = parseEnv(envText);
				if (args.length) payload.args = args;
				if (Object.keys(env).length) payload.env = env;
			}
			await addCustomConnector(localStorage.token, payload);
			toast.success($i18n.t('Connecteur ajouté'));
			reset();
			dispatch('added');
		} catch (e: any) {
			const code = e?.error?.code;
			if (code === 'name_conflict') toast.error($i18n.t('Un connecteur du même nom existe déjà'));
			else if (code === 'invalid_connector') toast.error($i18n.t('Configuration invalide'));
			else toast.error($i18n.t('Impossible d’ajouter le connecteur'));
		} finally {
			saving = false;
		}
	};
</script>

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" on:click|self={close}>
		<div class="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-xl">
			<div class="flex items-center justify-between mb-4">
				<div class="text-sm font-medium">{$i18n.t('Ajouter un connecteur personnalisé')}</div>
				<button class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" on:click={close}>✕</button>
			</div>

			<div class="flex flex-col gap-3">
				<input
					class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
					placeholder={$i18n.t('Nom (ex : mon-serveur)')}
					bind:value={name}
					autocomplete="off"
				/>

				<div class="flex items-center gap-2">
					<label class="text-xs text-gray-500 w-24" for="conn-transport">{$i18n.t('Transport')}</label>
					<select
						class="flex-1 text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						bind:value={transport}
						id="conn-transport"
					>
						<option value="http">HTTP</option>
						<option value="stdio">stdio</option>
					</select>
				</div>

				{#if transport === 'http'}
					<input
						class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						placeholder="https://exemple.com/mcp"
						bind:value={url}
						autocomplete="off"
					/>
				{:else}
					<input
						class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						placeholder={$i18n.t('Commande (ex : npx)')}
						bind:value={command}
						autocomplete="off"
					/>
					<textarea
						class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						rows="2"
						placeholder={$i18n.t('Arguments (un par ligne)')}
						bind:value={argsText}
					></textarea>
					<textarea
						class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						rows="2"
						placeholder={$i18n.t('Variables d’environnement (CLE=valeur, une par ligne)')}
						bind:value={envText}
					></textarea>
				{/if}

				<div class="flex items-center gap-2">
					<label class="text-xs text-gray-500 w-24" for="conn-auth">{$i18n.t('Authentification')}</label>
					<select
						class="flex-1 text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						bind:value={authType}
						id="conn-auth"
					>
						<option value="none">{$i18n.t('Sans auth')}</option>
						<option value="key">{$i18n.t('Clé API')}</option>
						{#if transport === 'http'}<option value="oauth">OAuth</option>{/if}
					</select>
				</div>
			</div>

			<div class="flex justify-end gap-2 mt-5">
				<button
					class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={close}
				>
					{$i18n.t('Annuler')}
				</button>
				<button
					class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
					disabled={saving}
					on:click={submit}
				>
					{#if saving}<Spinner className="size-3.5" />{:else}{$i18n.t('Ajouter')}{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
