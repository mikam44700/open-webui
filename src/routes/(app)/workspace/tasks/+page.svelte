<script>
	import KanbanBoard from '$lib/components/kanban/KanbanBoard.svelte';
</script>

<!-- h-full : le board remplit la zone défilante (gérée par le layout en mode « board plein écran »),
     avec scroll interne des colonnes. L'en-tête du hub reste figé sur cet onglet (comportement board). -->
<div class="h-full">
	<KanbanBoard />
</div>
