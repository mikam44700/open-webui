<script lang="ts">
	// Contenu du menu d'actions rapides (affiché dans un <Dropdown> par la barre
	// du chat, bouton "/"). Chaque action insère une INSTRUCTION EN FRANÇAIS dans
	// le champ — pas une slash command. L'agent Hermes exécute réellement ces
	// instructions via ses outils (les slash commands /goal /status… ne sont PAS
	// interceptées par l'API du chat, seulement par le terminal/messagerie).
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let query = '';

	// `insert` = texte mis dans le champ. S'il finit par " : " l'utilisateur
	// complète puis envoie ; sinon l'instruction est déjà prête à envoyer.
	type ActionItem = { label: string; hint: string; insert: string };
	type ActionGroup = { title: string; items: ActionItem[] };

	const groups: ActionGroup[] = [
		{
			title: 'Écrire & communiquer',
			items: [
				{
					label: 'Rédiger un email',
					hint: 'professionnel et clair',
					insert:
						"Aide-moi à rédiger un email professionnel. Demande-moi d'abord le destinataire, le contexte et l'objectif, puis propose-moi un texte clair et courtois."
				},
				{
					label: 'Répondre à un message',
					hint: 'ton juste, réponse prête',
					insert: 'Aide-moi à répondre à ce message de façon professionnelle : '
				},
				{
					label: 'Rédiger un document',
					hint: 'première version structurée',
					insert:
						"Aide-moi à rédiger un document. Demande-moi le sujet et l'objectif, puis propose une première version structurée."
				}
			]
		},
		{
			title: 'Analyser & chercher',
			items: [
				{
					label: 'Résumer un document',
					hint: "et en sortir l'essentiel",
					insert:
						'Résume ce document et fais-en ressortir les points essentiels et les actions à retenir : '
				},
				{
					label: 'Rechercher sur le web',
					hint: 'synthèse à jour et sourcée',
					insert: 'Fais une recherche à jour sur le web et donne-moi une synthèse sourcée sur : '
				},
				{
					label: 'Analyser un sujet',
					hint: 'synthèse structurée',
					insert:
						'Analyse ce sujet en profondeur et donne-moi une synthèse structurée avec les points clés : '
				}
			]
		},
		{
			title: 'Organiser & piloter',
			items: [
				{
					label: 'Organiser ma journée',
					hint: 'selon mes priorités',
					insert:
						'Aide-moi à organiser ma journée. Demande-moi mes priorités et mes rendez-vous, puis propose-moi un planning réaliste.'
				},
				{
					label: 'Préparer une réunion',
					hint: 'ordre du jour et points clés',
					insert:
						"Aide-moi à préparer une réunion : un ordre du jour structuré et les points clés à aborder. Demande-moi d'abord le sujet."
				},
				{
					label: 'Mon tableau de tâches',
					hint: 'voir ce qui est en cours',
					insert: 'Montre-moi mon tableau de tâches Kanban et ce qui est en cours.'
				},
				{
					label: 'Structurer une idée',
					hint: 'en plan d’action concret',
					insert:
						"J'ai une idée encore floue. Pose-moi des questions pour la clarifier, puis aide-moi à la transformer en plan d'action concret : "
				}
			]
		}
	];

	$: filteredGroups = (() => {
		const q = query.trim().toLowerCase();
		if (!q) return groups;
		return groups
			.map((g) => ({
				...g,
				items: g.items.filter(
					(it) => it.label.toLowerCase().includes(q) || it.hint.toLowerCase().includes(q)
				)
			}))
			.filter((g) => g.items.length > 0);
	})();

	const select = (item: ActionItem) => {
		dispatch('select', { insert: item.insert });
		query = '';
	};
</script>

<div class="w-80 max-w-[88vw] rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl overflow-hidden">
	<div class="p-2 border-b border-gray-100 dark:border-gray-800">
		<!-- svelte-ignore a11y-autofocus -->
		<input
			type="text"
			bind:value={query}
			placeholder={$i18n.t('Rechercher une action…')}
			class="w-full bg-transparent px-2 py-1.5 text-sm outline-hidden placeholder:text-gray-400"
			autofocus
		/>
	</div>

	<div class="max-h-80 overflow-y-auto scrollbar-thin py-1">
		{#each filteredGroups as group (group.title)}
			<div class="px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
				{group.title}
			</div>
			{#each group.items as item (item.label)}
				<button
					type="button"
					class="w-full flex flex-col px-3 py-1.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800/60 transition"
					on:click={() => select(item)}
				>
					<span class="text-sm text-gray-800 dark:text-gray-100 leading-tight">{item.label}</span>
					{#if item.hint}
						<span class="text-xs text-gray-400 dark:text-gray-500 leading-tight">{item.hint}</span>
					{/if}
				</button>
			{/each}
		{/each}

		{#if filteredGroups.length === 0}
			<div class="px-3 py-6 text-center text-sm text-gray-400">
				{$i18n.t('Aucune action trouvée')}
			</div>
		{/if}
	</div>
</div>
