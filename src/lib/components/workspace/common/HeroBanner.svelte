<script lang="ts">
	// Bannière premium V1 (même recette que la page Capacités) : accroche + palette dégradée.
	// Classes Tailwind passées en littéraux par la page appelante pour être compilées.
	export let lead: string;
	export let strong: string;
	export let sub: string;
	export let wrap: string;
	export let halo1: string;
	export let halo2: string;
	export let compact = false;
</script>

<!-- shrink-0 : enfant d'un flex-col a hauteur d'ecran, l'overflow-hidden ramene sa
     taille minimale de flex item a 0 - sans lui le bandeau est ecrase a 0px des que
     le contenu de l'onglet depasse l'ecran. -->
<div
	class="relative shrink-0 overflow-hidden bg-linear-to-br hero-modern ring-1 ring-inset ring-white/50 dark:ring-white/10 {compact
		? 'mb-4 rounded-2xl'
		: 'mb-5 rounded-3xl'} {wrap}"
>
	<div
		class="pointer-events-none absolute -right-12 top-1/2 h-44 w-44 -translate-y-1/2 rounded-full blur-3xl {halo1}"
	></div>
	<div
		class="pointer-events-none absolute -left-16 -top-10 h-40 w-40 rounded-full blur-3xl {halo2}"
	></div>
	<div class="hero-mesh pointer-events-none absolute inset-0"></div>
	<div class="hero-grain pointer-events-none absolute inset-0"></div>
	<div
		class="relative flex flex-col items-center justify-center text-center {compact
			? 'gap-1.5 px-5 py-5 sm:py-6'
			: 'gap-2 px-6 py-8'}"
	>
		<div
			class="rounded-full bg-white/90 px-5 py-2 text-sm text-gray-800 shadow-sm backdrop-blur dark:bg-gray-900/80 dark:text-gray-100"
		>
			{lead}
			<span class="font-semibold text-gray-900 dark:text-white">{strong}</span>
		</div>
		<p class="text-sm text-gray-500 dark:text-gray-400">{sub}</p>
	</div>
</div>
