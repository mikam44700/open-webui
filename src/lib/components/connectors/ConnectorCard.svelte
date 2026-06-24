<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let connector: {
		id: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		enabled: boolean;
		state: 'connected' | 'disconnected' | 'error' | 'disabled' | 'incomplete' | 'auth_required';
		endpoint?: string;
		secret_state?: 'present' | 'absent';
		source?: string | null;
	};

	// Libellé + couleur de l'état (cf. data-model ConnectorState).
	const STATE_META: Record<string, { label: string; cls: string }> = {
		connected: { label: 'Connecté', cls: 'text-green-700 bg-green-500/10 dark:text-green-400' },
		disconnected: { label: 'Configuré', cls: 'text-sky-700 bg-sky-500/10 dark:text-sky-400' },
		error: { label: 'Erreur', cls: 'text-red-700 bg-red-500/10 dark:text-red-400' },
		disabled: { label: 'Désactivé', cls: 'text-gray-600 bg-gray-500/10 dark:text-gray-400' },
		incomplete: {
			label: 'Configuration incomplète',
			cls: 'text-amber-700 bg-amber-500/10 dark:text-amber-400'
		},
		auth_required: {
			label: 'Authentification requise',
			cls: 'text-amber-700 bg-amber-500/10 dark:text-amber-400'
		}
	};

	const AUTH_LABEL: Record<string, string> = { none: 'Sans auth', key: 'Clé API', oauth: 'OAuth' };

	$: state = STATE_META[connector.state] ?? STATE_META['disconnected'];
</script>

<div
	class="flex flex-col gap-2.5 p-3.5 rounded-2xl border border-gray-100 dark:border-gray-850 {connector.enabled
		? ''
		: 'opacity-60'}"
>
	<!-- En-tête : icône connecteur + nom + état -->
	<div class="flex items-center gap-2.5">
		<div
			class="flex-none size-8 rounded-lg flex items-center justify-center bg-gray-100 dark:bg-gray-850 ring-1 ring-gray-200/70 dark:ring-gray-700/60"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.6"
				stroke="currentColor"
				class="size-4 text-gray-500"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
				/>
			</svg>
		</div>
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium line-clamp-1">{connector.id}</div>
			{#if connector.endpoint}
				<div class="text-xs text-gray-500 line-clamp-1">{connector.endpoint}</div>
			{/if}
		</div>
		<span class="flex-none text-[11px] px-2 py-0.5 rounded-full font-medium {state.cls}">
			{$i18n.t(state.label)}
		</span>
	</div>

	<!-- Badges : transport + type d'auth -->
	<div class="flex items-center gap-1.5">
		<span
			class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
		>
			{connector.transport}
		</span>
		<span
			class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-gray-600 dark:text-gray-300"
		>
			{$i18n.t(AUTH_LABEL[connector.auth_type] ?? connector.auth_type)}
		</span>
	</div>
</div>
