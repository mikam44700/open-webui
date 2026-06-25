<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { guessEmailServers, setEmailCredentials } from '$lib/apis/integrations';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;

	let email = '';
	let password = '';
	let imapHost = '';
	let imapPort = 993;
	let smtpHost = '';
	let smtpPort = 587;
	let showAdvanced = false;
	let busy = false;

	const close = () => {
		open = false;
		dispatch('close');
	};

	// Pré-remplit les serveurs dès qu'on quitte le champ email (fournisseurs courants).
	const onEmailBlur = async () => {
		if (!email.includes('@')) return;
		try {
			const res = await guessEmailServers(localStorage.token, email);
			if (res?.servers) {
				imapHost = res.servers.imap_host;
				imapPort = res.servers.imap_port;
				smtpHost = res.servers.smtp_host;
				smtpPort = res.servers.smtp_port;
			} else {
				showAdvanced = true; // fournisseur inconnu → on demande les serveurs
			}
		} catch {
			/* silencieux : l'utilisateur peut saisir manuellement */
		}
	};

	const connect = async () => {
		if (!email || !password || !imapHost || !smtpHost) {
			toast.error($i18n.t('Renseigne au moins l’email, le mot de passe et les serveurs.'));
			return;
		}
		busy = true;
		try {
			await setEmailCredentials(localStorage.token, {
				email,
				password,
				imap_host: imapHost,
				imap_port: Number(imapPort),
				smtp_host: smtpHost,
				smtp_port: Number(smtpPort)
			});
			toast.success($i18n.t('Email connecté !'));
			dispatch('connected');
			password = '';
			close();
		} catch {
			toast.error($i18n.t('Échec de la connexion Email.'));
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
			<div class="flex items-center justify-between mb-3">
				<div class="text-sm font-medium">{$i18n.t('Connecter ta boîte mail')}</div>
				<button class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" on:click={close}>✕</button>
			</div>

			<div class="flex flex-col gap-2.5">
				<input
					class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
					type="email"
					placeholder={$i18n.t('Adresse email')}
					bind:value={email}
					on:blur={onEmailBlur}
					autocomplete="off"
				/>
				<input
					class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
					type="password"
					placeholder={$i18n.t('Mot de passe (ou mot de passe d’application)')}
					bind:value={password}
					autocomplete="off"
				/>

				<button
					type="button"
					class="text-[11px] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition w-fit"
					on:click={() => (showAdvanced = !showAdvanced)}
				>
					{showAdvanced ? $i18n.t('Masquer les serveurs') : $i18n.t('Serveurs (avancé)')}
				</button>

				{#if showAdvanced}
					<div class="grid grid-cols-2 gap-2">
						<input class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none" placeholder={$i18n.t('Serveur IMAP')} bind:value={imapHost} />
						<input class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none" type="number" placeholder="993" bind:value={imapPort} />
						<input class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none" placeholder={$i18n.t('Serveur SMTP')} bind:value={smtpHost} />
						<input class="text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none" type="number" placeholder="587" bind:value={smtpPort} />
					</div>
				{/if}

				<div class="text-[11px] text-gray-400">
					{$i18n.t('Gmail/Yahoo : crée un « mot de passe d’application » dans les réglages de sécurité.')}
				</div>

				<div class="flex justify-end pt-1">
					<button
						class="text-xs px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
						disabled={busy}
						on:click={connect}
					>
						{#if busy}<Spinner className="size-3.5" />{:else}{$i18n.t('Connecter')}{/if}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
