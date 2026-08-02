<script lang="ts">
	/** Squelette de chargement partagé par les cartes du moteur. */
	export let lines = 3;
</script>

<div class="mt-3 flex flex-col gap-2.5" aria-hidden="true">
	{#each [...Array(lines).keys()] as index (index)}
		<div
			class="h-3 rounded bg-gray-100 dark:bg-gray-800 {index % 2 === 0 ? 'w-full' : 'w-2/3'}"
		></div>
	{/each}
</div>
