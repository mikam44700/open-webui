<script lang="ts">
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import ComingSoon from '$lib/components/workspace/common/ComingSoon.svelte';
</script>

<HeroBanner
	lead="Le"
	strong="tableau de bord du travail"
	sub="Vos tâches, triées et suivies par vos agents."
	wrap="from-violet-200/60 via-slate-100/60 to-violet-100/40 dark:from-[#6b62f2]/25 dark:via-[#161616]/80 dark:to-[#0a0a0a]/90"
	halo1="bg-violet-300/40 dark:bg-[#6b62f2]/25"
	halo2="bg-indigo-200/30 dark:bg-[#6b62f2]/10"
/>

<ComingSoon label="Tâches" />
