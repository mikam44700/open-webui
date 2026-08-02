<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		setGoogleClientSecret,
		getGoogleAuthUrl,
		submitGoogleAuthCode
	} from '$lib/apis/integrations';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;

	let step = 1; // 1 = app Google · 2 = autoriser · 3 = connecté
	let busy = false;
	let authUrl = '';
	let code = '';

	const close = () => {
		open = false;
		dispatch('close');
	};

	const reset = () => {
		step = 1;
		busy = false;
		authUrl = '';
		code = '';
	};

	// Étape 1 : le client fournit son app Google (fichier client_secret.json).
	const onFile = async (e: Event) => {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		busy = true;
		try {
			const json = JSON.parse(await file.text());
			await setGoogleClientSecret(localStorage.token, json);
			// Étape 2 : récupérer l'URL d'autorisation
			const res = await getGoogleAuthUrl(localStorage.token);
			authUrl = res?.auth_url ?? '';
			step = 2;
		} catch {
			toast.error($i18n.t('Fichier d’app Google invalide.'));
		} finally {
			busy = false;
		}
	};

	// Étape 2 : valider le code collé après autorisation Google.
	const submitCode = async () => {
		if (!code.trim()) return;
		busy = true;
		try {
			// On accepte une URL de redirection complète ou juste le code.
			const m = code.match(/[?&]code=([^&\s]+)/);
			const value = m ? decodeURIComponent(m[1]) : code.trim();
			const res = await submitGoogleAuthCode(localStorage.token, value);
			if (res?.state === 'connected') {
				step = 3;
				dispatch('connected');
			} else {
				toast.error($i18n.t('La connexion n’a pas pu être confirmée. Réessaie.'));
			}
		} catch {
			toast.error($i18n.t('Échec de la connexion Google.'));
		} finally {
			busy = false;
		}
	};
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click|self={close}
	>
		<div class="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-xl">
			<div class="flex items-center justify-between mb-1">
				<div class="text-sm font-medium">{$i18n.t('Connecter Google Workspace')}</div>
				<button class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" on:click={close}>✕</button>
			</div>
			<div class="text-[11px] text-gray-500 mb-4">{$i18n.t('Étape')} {step} / 3</div>

			{#if step === 1}
				<div class="flex flex-col gap-3">
					<div class="text-sm text-gray-600 dark:text-gray-300">
						{$i18n.t('Pour des raisons de sécurité, Google demande une « app » à fournir une seule fois.')}
					</div>
					<ol class="text-xs text-gray-500 dark:text-gray-400 list-decimal pl-4 flex flex-col gap-1">
						<li>{$i18n.t('Va sur la console Google Cloud → Identifiants → Créer un ID client OAuth (type « Application de bureau »).')}</li>
						<li>{$i18n.t('Télécharge le fichier JSON.')}</li>
						<li>{$i18n.t('Dépose-le ci-dessous.')}</li>
					</ol>
					<a
						href="https://console.cloud.google.com/apis/credentials"
						target="_blank"
						rel="noopener noreferrer"
						class="text-xs text-sky-600 dark:text-sky-400 hover:underline w-fit"
					>
						{$i18n.t('Ouvrir la console Google Cloud')}
					</a>
					<label
						class="flex items-center justify-center gap-2 text-sm border border-dashed border-gray-300 dark:border-gray-700 rounded-xl px-3 py-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					>
						{#if busy}<Spinner className="size-4" />{:else}{$i18n.t('Choisir le fichier client_secret.json')}{/if}
						<input type="file" accept="application/json,.json" class="hidden" on:change={onFile} disabled={busy} />
					</label>
				</div>
			{:else if step === 2}
				<div class="flex flex-col gap-3">
					<div class="text-sm text-gray-600 dark:text-gray-300">
						{$i18n.t('Ouvre la page Google, connecte-toi et autorise les accès, puis copie le code (ou l’URL) de retour.')}
					</div>
					<a
						href={authUrl}
						target="_blank"
						rel="noopener noreferrer"
						class="text-sm text-center px-3 py-2 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition"
					>
						{$i18n.t('Se connecter avec Google')}
					</a>
					<input
						class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
						placeholder={$i18n.t('Colle ici le code (ou l’URL) de retour')}
						bind:value={code}
						autocomplete="off"
					/>
					<div class="flex justify-end">
						<button
							class="text-xs px-3 py-1.5 rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
							disabled={busy || !code.trim()}
							on:click={submitCode}
						>
							{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Valider')}{/if}
						</button>
					</div>
				</div>
			{:else}
				<div class="flex flex-col items-center gap-3 py-6 text-center">
					<div class="text-green-600 dark:text-green-400 text-3xl">✓</div>
					<div class="text-sm font-medium">{$i18n.t('Google Workspace est connecté !')}</div>
					<button
						class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						on:click={() => {
							reset();
							close();
						}}
					>
						{$i18n.t('Terminer')}
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}
