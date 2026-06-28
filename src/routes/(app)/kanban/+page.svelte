<script>
	// Page Tâches déplacée dans le hub « Espace de travail » (onglet Tâches).
	// On redirige l'ancienne route pour ne casser aucun lien/favori existant.
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		goto('/workspace/tasks');
	});
</script>
