<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	const shortcuts: { label: string; href: string }[] = [
		{ label: 'Modèles IA', href: '/providers' },
		{ label: 'Capacités', href: '/connectors' },
		{ label: 'Messagerie', href: '/gateway' },
		{ label: 'Mémoire', href: '/memory' },
		{ label: 'Tâches', href: '/workspace/tasks' }
	];
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="text-sm font-medium">{$i18n.t('Démarrer')}</div>

	<a
		href="/"
		class="flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium transition hover:opacity-90"
	>
		{$i18n.t('Nouveau chat')}
	</a>

	<div class="grid grid-cols-2 gap-2">
		{#each shortcuts as s (s.href)}
			<a
				href={s.href}
				class="text-center text-xs px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
			>
				{$i18n.t(s.label)}
			</a>
		{/each}
	</div>
</div>
