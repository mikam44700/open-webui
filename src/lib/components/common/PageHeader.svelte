<script lang="ts">
	// En-tête de page premium partagé (DRY). Style « monochrome restreint » (Stripe/Linear/Vercel) :
	//   EYEBROW — nom fonctionnel : petit, capitales, GRIS neutre (subordonné au titre, JAMAIS coloré).
	//   Titre   — semibold (pas bold lourd), tracking serré (letter-spacing négatif = rendu « designed »).
	//   Desc    — 15px, interligne aéré, largeur ~65 caractères.
	// Slot « actions » optionnel : contenu aligné à droite du titre (ex. un interrupteur).

	export let eyebrow = '';
	export let title = '';
	export let description = '';
</script>

<div class="flex items-start justify-between gap-3">
	<div class="min-w-0">
		{#if eyebrow}
			<div
				class="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400 dark:text-gray-500"
			>
				{eyebrow}
			</div>
		{/if}
		<h1
			class="{eyebrow
				? 'mt-1.5'
				: ''} text-2xl font-semibold tracking-tight text-gray-900 dark:text-white"
		>
			{title}
		</h1>
		{#if description}
			<p class="mt-1.5 max-w-2xl text-[15px] leading-relaxed text-gray-500 dark:text-gray-400">
				{description}
			</p>
		{/if}
	</div>
	{#if $$slots.actions}
		<div class="flex-none pt-1">
			<slot name="actions" />
		</div>
	{/if}
</div>
