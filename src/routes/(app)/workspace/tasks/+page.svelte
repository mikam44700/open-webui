<script lang="ts">
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import ComingSoon from '$lib/components/workspace/common/ComingSoon.svelte';
</script>

<HeroBanner
	lead="Le"
	strong="tableau de bord du travail"
	sub="Vos tâches, triées et suivies par vos agents."
	wrap="from-sky-200/70 via-blue-100/50 to-indigo-100/60 dark:from-sky-900/30 dark:via-blue-900/20 dark:to-indigo-900/20"
	halo1="bg-sky-400/30 dark:bg-sky-500/20"
	halo2="bg-indigo-300/30 dark:bg-indigo-500/10"
/>

<ComingSoon label="Tâches" />
