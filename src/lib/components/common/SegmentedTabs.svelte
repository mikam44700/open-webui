<script lang="ts">
	/**
	 * Barre d'onglets a pilule glissante — reprise d'AgentOS V1.
	 *
	 * Un rail clair, et une pilule blanche qui *glisse* sous l'onglet actif au
	 * lieu d'apparaitre d'un coup. Le mouvement rattache visuellement l'onglet
	 * quitte a l'onglet choisi : on comprend ou l'on est alle.
	 *
	 * Deux formes d'element, selon ce qu'on passe :
	 *   { label, href }  -> un lien, pour naviguer par URL
	 *   { label }        -> un bouton, qui emet `select` avec son index
	 *
	 * L'onglet actif est pilote par le parent via `activeIndex` : ce composant ne
	 * decide de rien, il montre.
	 *
	 * L'animation se coupe seule si l'utilisateur a desactive les animations dans
	 * son systeme (motion-safe). Le rail defile horizontalement sur petit ecran.
	 */
	import { createEventDispatcher, onMount, tick } from 'svelte';

	export let items: { label: string; href?: string; count?: number | null }[] = [];
	export let activeIndex = 0;
	export let ariaLabel = '';

	const dispatch = createEventDispatcher();

	let tabEls: HTMLElement[] = [];
	let indicator = { left: 0, width: 0, ready: false };

	/**
	 * La pilule se place a la mesure du DOM, pas au calcul : les libelles ont des
	 * largeurs variables et la police n'est pas connue a l'avance.
	 */
	const refresh = async () => {
		await tick();
		const el = tabEls[activeIndex];
		if (el) {
			indicator = { left: el.offsetLeft, width: el.offsetWidth, ready: true };
		}
	};

	// Re-mesure quand l'onglet actif change, ou quand la liste elle-meme change
	// (les Reglages avances ajoutent et retirent des onglets a chaud).
	$: activeIndex, items, refresh();

	onMount(() => {
		const surRedimensionnement = () => refresh();
		window.addEventListener('resize', surRedimensionnement);
		return () => window.removeEventListener('resize', surRedimensionnement);
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
