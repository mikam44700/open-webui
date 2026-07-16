<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { exchangeOAuth } from '$lib/apis/integrations';
	import { INTEGRATION_FR } from '$lib/utils/integrationLabels';

	// État de la page pendant l'échange OAuth.
	type CallbackState = 'loading' | 'success' | 'error';

	let state: CallbackState = 'loading';
	let providerName = '';
	let errorMessage = '';

	// Messages connus renvoyés par les fournisseurs OAuth (RFC 6749 §4.1.2.1 + variantes
	// courantes). Tout code hors de cette liste passe par un message générique préfixé
	// (jamais affiché comme une déclaration de l'application — cf. issue #2 de l'audit).
	const OAUTH_ERROR_LABELS: Record<string, string> = {
		access_denied: "Vous avez refusé l'autorisation d'accès.",
		invalid_request: 'Requête invalide envoyée au fournisseur.',
		invalid_scope: 'Permissions demandées invalides ou non reconnues.',
		unauthorized_client: "Cette application n'est pas autorisée pour ce fournisseur.",
		unsupported_response_type: 'Configuration invalide côté fournisseur.',
		server_error: 'Le fournisseur a rencontré une erreur interne.',
		temporarily_unavailable: 'Le fournisseur est temporairement indisponible. Réessayez plus tard.'
	};

	// Redirige vers la page Capacités (onglet Intégrations) après un court délai.
	const redirectToIntegrations = () => {
		setTimeout(() => {
			goto('/connectors?tab=integrations');
		}, 1500);
	};

	onMount(async () => {
		const params = $page.url.searchParams;

		// Cas d'erreur renvoyée directement par le fournisseur OAuth. `error`/`error_description`
		// sont des paramètres de query string contrôlés par un tiers (potentiellement un lien
		// forgé) : jamais affichés tels quels comme un message de l'application.
		const oauthError = params.get('error');
		if (oauthError) {
			const known = OAUTH_ERROR_LABELS[oauthError];
			if (known) {
				errorMessage = known;
			} else {
				const raw = (params.get('error_description') ?? oauthError).slice(0, 200);
				errorMessage = `Le fournisseur a renvoyé : ${raw}`;
			}
			state = 'error';
			return;
		}

		const code = params.get('code');
		const oauthState = params.get('state') ?? '';
		const providerId = sessionStorage.getItem('oauth_provider');
		const expectedNonce = sessionStorage.getItem('oauth_nonce');

		// Récupérer le nom affiché du provider pour les messages utilisateur.
		providerName = (providerId && INTEGRATION_FR[providerId]?.name) || providerId || 'ce service';

		if (!code || !providerId) {
			errorMessage = 'Paramètres manquants dans la réponse du fournisseur.';
			state = 'error';
			return;
		}

		// Défense en profondeur CSRF (côté navigateur) : le state reçu doit correspondre
		// STRICTEMENT au state mémorisé au moment du clic « Se connecter » (cf.
		// IntegrationCard.onConnectOAuth). Absent ou différent = lien de callback forgé ou
		// rejoué → on refuse avant tout appel réseau. Le bridge valide aussi le state côté
		// serveur ; ceci s'ajoute, ça ne le remplace pas.
		if (!expectedNonce || oauthState !== expectedNonce) {
			errorMessage = 'Lien de connexion invalide ou expiré. Relancez la connexion depuis les intégrations.';
			state = 'error';
			sessionStorage.removeItem('oauth_provider');
			sessionStorage.removeItem('oauth_nonce');
			return;
		}

		try {
			const token = localStorage.token as string | undefined;
			if (!token) {
				errorMessage = 'Session expirée. Reconnectez-vous puis réessayez.';
				state = 'error';
				return;
			}

			const res = await exchangeOAuth(token, providerId, code, oauthState);

			if (res?.state === 'connected') {
				// Nettoyer les clés temporaires du sessionStorage.
				sessionStorage.removeItem('oauth_provider');
				sessionStorage.removeItem('oauth_nonce');
				state = 'success';
				redirectToIntegrations();
			} else {
				errorMessage = "La connexion n'a pas pu etre confirmee par le serveur.";
				state = 'error';
			}
		} catch {
			errorMessage = 'Une erreur est survenue lors de la connexion. Réessayez.';
			state = 'error';
		}
	});
</script>

<svelte:head>
	<title>Connexion en cours…</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-white dark:bg-gray-950 p-6">
	<div class="w-full max-w-sm flex flex-col items-center gap-6 text-center">
		{#if state === 'loading'}
			<!-- Spinner pendant l'échange du code -->
			<div
				class="size-12 rounded-full border-4 border-gray-200 dark:border-gray-800 border-t-gray-900 dark:border-t-gray-100 animate-spin"
			></div>
			<div>
				<p class="text-sm font-medium text-gray-800 dark:text-gray-200">Connexion en cours…</p>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Finalisation de la connexion avec {providerName || 'le service'}.
				</p>
			</div>
		{:else if state === 'success'}
			<!-- Confirmation de connexion -->
			<div
				class="size-12 rounded-full bg-green-500/10 flex items-center justify-center text-green-600 dark:text-green-400"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="size-6">
					<path d="M20 6 9 17l-5-5" />
				</svg>
			</div>
			<div>
				<p class="text-sm font-medium text-gray-800 dark:text-gray-200">
					{providerName} est connecté
				</p>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Retour vers vos intégrations…
				</p>
			</div>
		{:else}
			<!-- Erreur -->
			<div
				class="size-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-600 dark:text-red-400"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="size-6">
					<line x1="12" y1="8" x2="12" y2="13" />
					<line x1="12" y1="17" x2="12.01" y2="17" />
				</svg>
			</div>
			<div class="flex flex-col gap-1">
				<p class="text-sm font-medium text-gray-800 dark:text-gray-200">La connexion a échoué</p>
				{#if errorMessage}
					<p class="text-xs text-gray-500 dark:text-gray-400">{errorMessage}</p>
				{/if}
			</div>
			<button
				type="button"
				class="text-sm px-4 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black transition hover:opacity-80"
				on:click={() => goto('/connectors?tab=integrations')}
			>
				Retour aux intégrations
			</button>
		{/if}
	</div>
</div>
