<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Badge from '$lib/components/common/Badge.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let provider: {
		id: string;
		label: string;
		logo: string;
		state: 'active' | 'configured' | 'not_configured';
		models?: { id: string; label: string }[];
	};
	export let selected = false;

	// état -> apparence du badge (cf. ProviderState du bridge)
	const badgeByState: Record<string, { type: string; label: string }> = {
		active: { type: 'success', label: 'Active' },
		configured: { type: 'info', label: 'Configured' },
		not_configured: { type: 'muted', label: 'Not configured' }
	};

	$: badge = badgeByState[provider.state] ?? badgeByState['not_configured'];
	$: disabled = provider.state === 'not_configured';
	$: logoUrl = `${WEBUI_BASE_URL}/assets/providers/${provider.logo}.svg`;

	const onError = (e: Event) => {
		// fallback générique si le logo du provider est absent
		(e.currentTarget as HTMLImageElement).src = `${WEBUI_BASE_URL}/assets/providers/api.svg`;
	};
</script>

<button
	type="button"
	class="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-2xl border transition
		{selected
		? 'border-gray-400 dark:border-gray-600 bg-gray-50 dark:bg-gray-850'
		: 'border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-900'}
		{disabled ? 'opacity-60' : ''}"
	on:click={() => dispatch('select', provider)}
	aria-pressed={selected}
>
	<div class="flex-none size-8 flex items-center justify-center">
		<img src={logoUrl} on:error={onError} class="size-6 object-contain" alt={provider.label} draggable="false" />
	</div>

	<div class="flex-1 min-w-0">
		<div class="text-sm font-medium line-clamp-1">{provider.label}</div>
		<div class="text-xs text-gray-500 line-clamp-1">
			{(provider.models?.length ?? 0)}
			{$i18n.t('models')}
		</div>
	</div>

	<Badge type={badge.type} content={$i18n.t(badge.label)} />
</button>
