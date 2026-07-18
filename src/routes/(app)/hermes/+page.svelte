<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	// Adresse locale de l'API Hermes Agent (port par defaut du serveur API Hermes)
	const HERMES_API_URL = 'http://localhost:8642';
	const HERMES_VERSION_INSTALLEE = 'v0.18.2';

	let statut: 'verification' | 'en_ligne' | 'hors_ligne' = 'verification';
	let dernierControle: string = '-';
	let interval: ReturnType<typeof setInterval> | null = null;

	const verifierMoteur = async () => {
		statut = 'verification';
		try {
			const controller = new AbortController();
			const timeout = setTimeout(() => controller.abort(), 4000);
			// mode no-cors : on ne lit pas la reponse, on verifie juste que le serveur repond
			await fetch(`${HERMES_API_URL}/v1/models`, {
				mode: 'no-cors',
				signal: controller.signal
			});
			clearTimeout(timeout);
			statut = 'en_ligne';
		} catch {
			statut = 'hors_ligne';
		}
		dernierControle = new Date().toLocaleTimeString('fr-FR');
	};

	onMount(() => {
		verifierMoteur();
		interval = setInterval(verifierMoteur, 30000);
	});

	onDestroy(() => {
		if (interval) clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Hermes Agent</title>
</svelte:head>

<div class="flex flex-col w-full h-full px-5 py-6 max-w-3xl mx-auto overflow-y-auto">
	<div class="mb-6">
		<div class="text-xs font-semibold tracking-widest text-gray-500 dark:text-gray-400 uppercase">
			Le moteur
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-50 mt-1">Hermes Agent</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
			L'agent qui execute le travail : memoire, veille, taches programmees.
		</p>
	</div>

	<!-- Bandeau d'etat -->
	<div
		class="rounded-2xl px-5 py-4 mb-4 border {statut === 'en_ligne'
			? 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900'
			: statut === 'hors_ligne'
				? 'bg-gray-50 dark:bg-gray-850 border-gray-200 dark:border-gray-800'
				: 'bg-gray-50 dark:bg-gray-850 border-gray-200 dark:border-gray-800'}"
	>
		<div class="flex items-center gap-3">
			<span
				class="relative flex size-3 shrink-0"
				aria-hidden="true"
			>
				{#if statut === 'en_ligne'}
					<span
						class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
					/>
					<span class="relative inline-flex rounded-full size-3 bg-green-500" />
				{:else if statut === 'hors_ligne'}
					<span class="relative inline-flex rounded-full size-3 bg-gray-400" />
				{:else}
					<span class="relative inline-flex rounded-full size-3 bg-yellow-400 animate-pulse" />
				{/if}
			</span>
			<div>
				<div class="font-medium text-gray-900 dark:text-gray-50">
					{#if statut === 'en_ligne'}
						Votre moteur est operationnel
					{:else if statut === 'hors_ligne'}
						Moteur hors ligne
					{:else}
						Verification en cours...
					{/if}
				</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">
					{#if statut === 'en_ligne'}
						Hermes tourne et repond normalement.
					{:else if statut === 'hors_ligne'}
						Hermes est installe mais son serveur n'est pas demarre.
					{:else}
						Contact du moteur...
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Carte etat du moteur -->
	<div class="rounded-2xl border border-gray-200 dark:border-gray-800 px-5 py-4 mb-4">
		<div class="font-medium text-gray-900 dark:text-gray-50 mb-3">Etat du moteur</div>
		<div class="flex flex-col gap-2.5 text-sm">
			<div class="flex justify-between">
				<span class="text-gray-500 dark:text-gray-400">Moteur</span>
				<span class="text-gray-900 dark:text-gray-50 font-medium">Hermes Agent</span>
			</div>
			<div class="flex justify-between">
				<span class="text-gray-500 dark:text-gray-400">Version installee</span>
				<span class="text-gray-900 dark:text-gray-50 font-medium">{HERMES_VERSION_INSTALLEE}</span>
			</div>
			<div class="flex justify-between">
				<span class="text-gray-500 dark:text-gray-400">Statut</span>
				<span
					class="font-medium {statut === 'en_ligne'
						? 'text-green-600 dark:text-green-400'
						: 'text-gray-500 dark:text-gray-400'}"
				>
					{statut === 'en_ligne' ? 'En ligne' : statut === 'hors_ligne' ? 'Hors ligne' : '...'}
				</span>
			</div>
			<div class="flex justify-between">
				<span class="text-gray-500 dark:text-gray-400">Adresse locale</span>
				<span class="text-gray-900 dark:text-gray-50 font-mono text-xs self-center"
					>{HERMES_API_URL}</span
				>
			</div>
			<div class="flex justify-between">
				<span class="text-gray-500 dark:text-gray-400">Dernier controle</span>
				<span class="text-gray-900 dark:text-gray-50">{dernierControle}</span>
			</div>
		</div>
	</div>

	<div class="flex gap-2">
		<button
			class="px-4 py-2 rounded-xl text-sm font-medium bg-gray-900 text-gray-50 dark:bg-gray-50 dark:text-gray-900 hover:opacity-90 transition"
			on:click={verifierMoteur}
		>
			Verifier a nouveau
		</button>
	</div>

	{#if statut === 'hors_ligne'}
		<div class="mt-4 text-xs text-gray-500 dark:text-gray-400">
			Le moteur se demarre depuis le terminal avec la commande <span class="font-mono"
				>hermes gateway</span
			> (configuration en cours - etape suivante du projet).
		</div>
	{/if}
</div>
