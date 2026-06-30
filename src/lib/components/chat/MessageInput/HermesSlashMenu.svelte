<script lang="ts">
	// Contenu du menu des commandes Hermes (affiché dans un <Dropdown> par la barre
	// du chat). Liste les vraies commandes que le gateway Hermes intercepte (donc
	// qui FONCTIONNENT via le chat, pas seulement dans le terminal). Cliquer émet
	// 'select' ; le parent insère la commande dans le champ.
	//
	// Source : COMMAND_REGISTRY de hermes-agent/hermes_cli/commands.py — on ne
	// garde que les commandes disponibles côté gateway, francisées et pensées
	// pour un dirigeant.
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let query = '';

	type SlashItem = { name: string; label: string; hint: string; args: boolean };
	type SlashGroup = { title: string; items: SlashItem[] };

	const groups: SlashGroup[] = [
		{
			title: 'Piloter le travail',
			items: [
				{ name: 'goal', label: 'Fixer un objectif', hint: "que l'agent poursuit dans le temps", args: true },
				{ name: 'subgoal', label: 'Ajouter un critère', hint: "à l'objectif en cours", args: true },
				{ name: 'background', label: 'Lancer en arrière-plan', hint: 'une tâche qui tourne toute seule', args: true },
				{ name: 'agents', label: 'Voir les agents actifs', hint: 'et les tâches en cours', args: false },
				{ name: 'status', label: "État de la session", hint: 'modèle, contexte, jetons', args: false },
				{ name: 'stop', label: 'Tout arrêter', hint: 'stoppe ce qui tourne', args: false }
			]
		},
		{
			title: 'Organiser',
			items: [
				{ name: 'kanban', label: 'Tableau de tâches', hint: 'créer, lister, assigner', args: true },
				{ name: 'new', label: 'Nouvelle conversation', hint: 'repartir de zéro', args: false },
				{ name: 'resume', label: 'Reprendre une conversation', hint: 'par son nom', args: true },
				{ name: 'sessions', label: 'Parcourir les conversations', hint: 'historique', args: false },
				{ name: 'title', label: 'Donner un titre', hint: 'à la conversation', args: true }
			]
		},
		{
			title: 'Capacités',
			items: [
				{ name: 'skills', label: 'Gérer les compétences', hint: 'chercher, installer, inspecter', args: true },
				{ name: 'suggestions', label: 'Automatisations suggérées', hint: 'accepter / écarter', args: true },
				{ name: 'memory', label: 'Valider la mémoire', hint: 'écritures en attente', args: true },
				{ name: 'insights', label: "Statistiques d'usage", hint: 'analyse de l’activité', args: true }
			]
		},
		{
			title: 'Réglages',
			items: [
				{ name: 'model', label: 'Changer de modèle IA', hint: '', args: true },
				{ name: 'fast', label: 'Mode rapide', hint: 'normal / rapide', args: true },
				{ name: 'reasoning', label: 'Niveau de réflexion', hint: 'effort de raisonnement', args: true },
				{ name: 'voice', label: 'Mode vocal', hint: 'activer / couper', args: true }
			]
		},
		{
			title: 'Infos & crédits',
			items: [
				{ name: 'usage', label: 'Jetons & limites', hint: 'de la session', args: false },
				{ name: 'credits', label: 'Solde de crédits', hint: 'et recharge', args: false },
				{ name: 'help', label: 'Toutes les commandes', hint: 'aide Hermes', args: false }
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
					(it) =>
						it.name.includes(q) ||
						it.label.toLowerCase().includes(q) ||
						it.hint.toLowerCase().includes(q)
				)
			}))
			.filter((g) => g.items.length > 0);
	})();

	const select = (item: SlashItem) => {
		dispatch('select', { name: item.name, args: item.args });
		query = '';
	};
</script>

<div class="w-80 max-w-[88vw] rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl overflow-hidden">
	<div class="p-2 border-b border-gray-100 dark:border-gray-800">
		<!-- svelte-ignore a11y-autofocus -->
		<input
			type="text"
			bind:value={query}
			placeholder={$i18n.t('Rechercher une commande…')}
			class="w-full bg-transparent px-2 py-1.5 text-sm outline-hidden placeholder:text-gray-400"
			autofocus
		/>
	</div>

	<div class="max-h-80 overflow-y-auto scrollbar-thin py-1">
		{#each filteredGroups as group (group.title)}
			<div class="px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
				{group.title}
			</div>
			{#each group.items as item (item.name)}
				<button
					type="button"
					class="w-full flex items-baseline gap-2 px-3 py-1.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800/60 transition"
					on:click={() => select(item)}
				>
					<span class="shrink-0 text-xs font-mono text-gray-400 dark:text-gray-500">/{item.name}</span>
					<span class="flex flex-col">
						<span class="text-sm text-gray-800 dark:text-gray-100 leading-tight">{item.label}</span>
						{#if item.hint}
							<span class="text-xs text-gray-400 dark:text-gray-500 leading-tight">{item.hint}</span>
						{/if}
					</span>
				</button>
			{/each}
		{/each}

		{#if filteredGroups.length === 0}
			<div class="px-3 py-6 text-center text-sm text-gray-400">
				{$i18n.t('Aucune commande trouvée')}
			</div>
		{/if}
	</div>
</div>
