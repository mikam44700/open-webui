<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		installConnector,
		setConnectorKey,
		startConnectorOAuth,
		getInstallStatus
	} from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import OAuthProgressModal from './OAuthProgressModal.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let entry: {
		name: string;
		description?: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		installed: boolean;
		source_url?: string | null;
	};

	const AUTH_LABEL: Record<string, string> = { none: 'Sans auth', key: 'Clé API', oauth: 'OAuth' };

	let keyValue = '';
	let working = false;
	let oauthOpen = false;

	// Attend la fin de l'installation asynchrone (git clone + bootstrap côté Hermes).
	const waitInstall = async () => {
		for (let i = 0; i < 60; i++) {
			await new Promise((r) => setTimeout(r, 1500));
			const s = await getInstallStatus(localStorage.token, entry.name).catch(() => null);
			if (s && s.started && !s.running) return s.success ?? false;
		}
		return false;
	};

	const install = async () => {
		working = true;
		try {
			// 1) clé API d'abord (pour une install non-interactive)
			if (entry.auth_type === 'key') {
				if (!keyValue) {
					toast.error($i18n.t('Saisis la clé API d’abord'));
					working = false;
					return;
				}
				await setConnectorKey(localStorage.token, entry.name, keyValue);
				keyValue = '';
			}
			// 2) installation
			await installConnector(localStorage.token, entry.name);
			const ok = await waitInstall();
			if (!ok) {
				toast.error($i18n.t('L’installation a échoué.'));
				return;
			}
			// 3) OAuth si nécessaire
			if (entry.auth_type === 'oauth') {
				await startConnectorOAuth(localStorage.token, entry.name);
				oauthOpen = true;
			} else {
				toast.success($i18n.t('Connecteur installé.'));
				dispatch('changed');
			}
		} catch {
			toast.error($i18n.t('Impossible d’installer ce connecteur.'));
		} finally {
			working = false;
		}
	};
</script>

<div class="flex flex-col gap-2.5 p-3.5 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="flex items-center gap-2.5">
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium line-clamp-1">{entry.name}</div>
			{#if entry.description}
				<div class="text-xs text-gray-500 line-clamp-2">{entry.description}</div>
			{/if}
		</div>
		{#if entry.installed}
			<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium text-green-700 bg-green-500/10 dark:text-green-400">
				{$i18n.t('Installé')}
			</span>
		{/if}
	</div>

	<div class="flex items-center gap-1.5">
		<span class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300">
			{entry.transport}
		</span>
		<span class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300">
			{$i18n.t(AUTH_LABEL[entry.auth_type] ?? entry.auth_type)}
		</span>
	</div>

	{#if !entry.installed}
		{#if entry.auth_type === 'key'}
			<input
				class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				type="password"
				placeholder={entry.name + ' — ' + $i18n.t('clé API')}
				bind:value={keyValue}
				autocomplete="off"
			/>
		{/if}
		<div class="flex justify-end">
			<button
				type="button"
				class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
				disabled={working}
				on:click={install}
			>
				{#if working}
					<Spinner className="size-3.5" />
				{:else if entry.auth_type === 'oauth'}
					{$i18n.t('Installer & connecter')}
				{:else}
					{$i18n.t('Installer')}
				{/if}
			</button>
		</div>
	{/if}
</div>

<OAuthProgressModal
	connectorId={entry.name}
	bind:open={oauthOpen}
	on:connected={() => {
		oauthOpen = false;
		dispatch('changed');
	}}
	on:close={() => {
		oauthOpen = false;
		dispatch('changed');
	}}
/>
