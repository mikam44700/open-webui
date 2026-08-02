<script lang="ts">
	/**
	 * En-tete de page partage — repris d'AgentOS V1.
	 *
	 * Style monochrome restreint (Stripe / Linear / Vercel) :
	 *   surtitre — nom fonctionnel, petit, capitales, GRIS neutre. Jamais colore :
	 *              il est subordonne au titre, pas en concurrence avec lui.
	 *   titre    — semibold plutot que bold, tracking serre.
	 *   phrase   — 15 px, interligne aere, largeur limitee a ~65 caracteres pour
	 *              rester lisible.
	 *
	 * Le volet « actions » est optionnel : il aligne un contenu a droite du titre
	 * (par exemple l'interrupteur « Reglages avances »).
	 */
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
