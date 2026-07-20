<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	// Popup « Voir ce que ça fait » des connecteurs : même style que la modale des
	// Intégrations (overlay centré, logo + nom + description + liste des actions).
	// Partagée par ConnectorCard, CatalogCard et Crawl4aiCard — SPEC-popup-connecteurs.
	export let open = false;
	export let name = '';
	export let desc = '';
	export let logoSrc = '';
	export let fullBleed = false;
	export let actions: string[] = [];
	// Lien d'aide optionnel sous la liste (ex. guide d'autorisation ChatGPT) :
	// ferme la popup et émet `help`, le parent ouvre son guide — SPEC-cartes-modeles-ia.
	export let helpLabel = '';
</script>

{#if open && actions.length}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={() => (open = false)}
		role="presentation"
	>
		<div
			class="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 shadow-xl p-5"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
		>
			<div class="flex items-center justify-between mb-1">
				<div class="flex items-center gap-2">
					{#if logoSrc}
						<div
							class="size-7 rounded-md border border-gray-100 dark:border-gray-700 overflow-hidden flex items-center justify-center {fullBleed
								? ''
								: 'bg-white p-1'}"
						>
							<img
								src={logoSrc}
								alt={name}
								class={fullBleed ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}
								draggable="false"
							/>
						</div>
					{/if}
					<span class="text-base font-medium">{name}</span>
				</div>
				<button
					class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
					on:click={() => (open = false)}
					aria-label={$i18n.t('Fermer')}
				>
					✕
				</button>
			</div>
			{#if desc}
				<div class="text-xs text-gray-500 mb-4">{desc}</div>
			{/if}

			<div
				class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2.5"
			>
				{$i18n.t('Ce que ça fait')}
			</div>
			<ul class="flex flex-col gap-3">
				{#each actions as action}
					<li class="flex items-start gap-2.5 text-xs text-gray-600 dark:text-gray-300">
						<span class="flex-none mt-1.5 size-1.5 rounded-full bg-gray-400 dark:bg-gray-600"></span>
						<span>{$i18n.t(action)}</span>
					</li>
				{/each}
			</ul>

			{#if helpLabel}
				<button
					type="button"
					class="mt-4 text-left text-[13px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 underline decoration-dotted underline-offset-2 transition"
					on:click={() => {
						open = false;
						dispatch('help');
					}}
				>
					{$i18n.t(helpLabel)}
				</button>
			{/if}

			<div class="mt-5 flex justify-end">
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (open = false)}
				>
					{$i18n.t('Fermer')}
				</button>
			</div>
		</div>
	</div>
{/if}
