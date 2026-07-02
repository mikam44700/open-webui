<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { automationTemplates, type AutomationTemplate } from '$lib/automations/templates';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let compact = false;

	const select = (t: AutomationTemplate) => dispatch('select', t);
</script>

<div class="grid gap-2 {compact ? 'sm:grid-cols-2 lg:grid-cols-3' : 'sm:grid-cols-2 lg:grid-cols-3'}">
	{#each automationTemplates as t (t.id)}
		<button
			type="button"
			class="text-left p-3 rounded-2xl border border-gray-100 dark:border-gray-850 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-850/40 card-lift min-w-0 overflow-hidden"
			on:click={() => select(t)}
		>
			<div class="flex items-start gap-2.5 min-w-0">
				<span class="text-lg leading-none mt-0.5 shrink-0">{t.emoji}</span>
				<div class="min-w-0 flex-1">
					<div class="text-sm font-medium truncate">{$i18n.t(t.title)}</div>
					<div class="text-xs text-gray-500 mt-0.5 line-clamp-2">{$i18n.t(t.summary)}</div>
					<div class="flex items-center gap-1.5 mt-1.5">
						{#each t.apps as app}
							{#if app.src}
								<span
									class="size-5 rounded-[5px] bg-white border border-gray-200 dark:border-gray-700 flex items-center justify-center overflow-hidden shrink-0"
									title={app.alt}
								>
									<img src={app.src} alt={app.alt} class="size-3.5 object-contain" loading="lazy" />
								</span>
							{:else}
								<span
									class="size-5 rounded-[5px] bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs shrink-0"
									title={app.alt}
								>
									{app.emoji}
								</span>
							{/if}
						{/each}
						<span class="ml-auto text-[11px] text-gray-400">{$i18n.t('Utiliser')} →</span>
					</div>
				</div>
			</div>
		</button>
	{/each}
</div>
