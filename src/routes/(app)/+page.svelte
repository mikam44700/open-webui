<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import OnboardingFlow from '$lib/components/onboarding/OnboardingFlow.svelte';
	import { page } from '$app/stores';

	// Affichage du parcours d'accueil au 1er login. Signal provisoire (drapeau local) : affiné
	// ensuite avec l'état réel (contexte entreprise présent ?). Repli sûr : au moindre souci, on
	// n'affiche rien et le Chat s'affiche normalement — jamais de blocage de l'entrée de l'app.
	let showOnboarding = false;

	const dismissOnboarding = () => {
		try {
			localStorage.setItem('lunaria_onboarding_done', '1');
		} catch {
			/* tolérant */
		}
		showOnboarding = false;
	};

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
		try {
			showOnboarding = localStorage.getItem('lunaria_onboarding_done') !== '1';
		} catch {
			showOnboarding = false;
		}
	});
</script>

{#if showOnboarding}
	<OnboardingFlow on:done={dismissOnboarding} on:skip={dismissOnboarding} />
{:else}
	<Chat />
{/if}
