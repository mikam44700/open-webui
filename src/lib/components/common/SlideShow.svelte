<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { onMount } from 'svelte';

	// Fonds du carrousel de connexion en WebP (redimensionnés à 2560 px) : ~5 Mo → 1,6 Mo,
	// pour un premier affichage bien plus léger. Les JPG d'origine sont conservés en repli.
	export let imageUrls = [
		`${WEBUI_BASE_URL}/assets/images/adam.webp`,
		`${WEBUI_BASE_URL}/assets/images/galaxy.webp`,
		`${WEBUI_BASE_URL}/assets/images/earth.webp`,
		`${WEBUI_BASE_URL}/assets/images/space.webp`
	];
	export let duration = 5000;
	let selectedImageIdx = 0;

	onMount(() => {
		setInterval(() => {
			selectedImageIdx = (selectedImageIdx + 1) % (imageUrls.length - 1);
		}, duration);
	});
</script>

{#each imageUrls as imageUrl, idx (idx)}
	<div
		class="image w-full h-full absolute top-0 left-0 bg-cover bg-center transition-opacity duration-1000"
		style="opacity: {selectedImageIdx === idx ? 1 : 0}; background-image: url('{imageUrl}')"
	></div>
{/each}

<style>
	.image {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-size: cover;
		background-position: center; /* Center the background images */
		transition: opacity 1s ease-in-out; /* Smooth fade effect */
		opacity: 0; /* Make images initially not visible */
	}
</style>
