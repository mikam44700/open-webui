<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import Card from './Card.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	const shortcuts = [
		{ labelKey: 'Models', href: '/workspace/models' },
		{ labelKey: 'Skills', href: '/workspace/skills' },
		{ labelKey: 'Tools', href: '/workspace/tools' }
	];
</script>

<Card title={$i18n.t('Quick actions')}>
	<a
		href="/"
		class="mt-1 flex items-center justify-center rounded-xl bg-black px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 dark:bg-white dark:text-black"
	>
		{$i18n.t('New chat')}
	</a>

	<div class="grid grid-cols-3 gap-2">
		{#each shortcuts as shortcut (shortcut.href)}
			<a
				href={shortcut.href}
				class="rounded-xl border border-gray-100 px-2 py-2 text-center text-xs text-gray-700 transition hover:bg-gray-50 dark:border-gray-850 dark:text-gray-200 dark:hover:bg-gray-850"
			>
				{$i18n.t(shortcut.labelKey)}
			</a>
		{/each}
	</div>
</Card>
