<script lang="ts">
	// Segmented control premium partagé : rail clair + pilule blanche qui glisse sous l'onglet
	// actif (mouvement fluide, accéléré GPU). Source UNIQUE pour toutes les barres d'onglets de
	// l'app (Capacités, Modèles IA, Espace de travail, Mémoire…). DRY.
	//
	// Deux modes, selon la forme de chaque item :
	//   - lien   : { label, href, count? }  → rend un <a> (navigation par URL).
	//   - bouton : { label, count? }        → rend un <button> qui émet `select` (index).
	// L'onglet actif est piloté par `activeIndex` (calculé par le parent : état ou pathname).
	// L'animation se coupe seule si l'utilisateur a désactivé les animations système
	// (motion-safe:* → prefers-reduced-motion). Défile horizontalement sur petit écran.

	import { createEventDispatcher, onMount, tick } from 'svelte';

	export let items: { label: string; href?: string; count?: number | null }[] = [];
	export let activeIndex: number = 0;
	export let ariaLabel: string = '';

	const dispatch = createEventDispatcher();

	let tabEls: HTMLElement[] = [];
	let indicator = { left: 0, width: 0, ready: false };

	async function refresh() {
		await tick();
		const el = tabEls[activeIndex];
		if (el) {
			indicator = { left: el.offsetLeft, width: el.offsetWidth, ready: true };
		}
	}

	// Re-mesure quand l'onglet actif ou la liste changent.
	$: activeIndex, items, refresh();

	onMount(() => {
		const onResize = () => refresh();
		window.addEventListener('resize', onResize);
		return () => window.removeEventListener('resize', onResize);
	});
</script>

<div
	role="tablist"
	aria-label={ariaLabel || undefined}
	class="scrollbar-hidden relative inline-flex max-w-full items-center gap-0.5 overflow-x-auto rounded-full bg-gray-100/80 p-1 dark:bg-gray-850/80"
>
	{#if indicator.ready}
		<span
			aria-hidden="true"
			class="pointer-events-none absolute bottom-1 top-1 rounded-full bg-white shadow-sm ring-1 ring-black/5 motion-safe:transition-all motion-safe:duration-300 motion-safe:ease-out dark:bg-gray-900 dark:ring-white/10"
			style="left: {indicator.left}px; width: {indicator.width}px;"
		></span>
	{/if}

	{#each items as item, i (item.href ?? item.label)}
		{#if item.href}
			<a
				href={item.href}
				role="tab"
				aria-selected={i === activeIndex}
				draggable="false"
				bind:this={tabEls[i]}
				class="relative z-10 whitespace-nowrap rounded-full px-4 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900/40 dark:focus-visible:ring-white/40 {i ===
				activeIndex
					? 'font-medium text-gray-900 dark:text-white'
					: 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'}"
			>
				{item.label}{#if item.count != null}<span class="ml-1 text-gray-400 dark:text-gray-500"
						>({item.count})</span
					>{/if}
			</a>
		{:else}
			<button
				type="button"
				role="tab"
				aria-selected={i === activeIndex}
				bind:this={tabEls[i]}
				on:click={() => dispatch('select', i)}
				class="relative z-10 whitespace-nowrap rounded-full px-4 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900/40 dark:focus-visible:ring-white/40 {i ===
				activeIndex
					? 'font-medium text-gray-900 dark:text-white'
					: 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'}"
			>
				{item.label}{#if item.count != null}<span class="ml-1 text-gray-400 dark:text-gray-500"
						>({item.count})</span
					>{/if}
			</button>
		{/if}
	{/each}
</div>
