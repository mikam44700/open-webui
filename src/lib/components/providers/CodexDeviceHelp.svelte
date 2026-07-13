<script lang="ts">
	// Guide « comment activer les codes d'appareil ChatGPT » — pré-requis au device flow Codex
	// (désactivé par défaut côté compte ChatGPT). Illustré avec de vraies captures maison.
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	const close = () => dispatch('close');

	const BASE = '/assets/onboarding/codex-guide';
	const steps = [
		{
			img: `${BASE}/etape-1-parametres.png`,
			alt: 'Menu du profil ChatGPT avec Paramètres',
			title: 'Ouvrez vos réglages ChatGPT',
			desc: 'Sur chatgpt.com, cliquez sur votre profil (en bas à gauche), puis sur « Paramètres ».'
		},
		{
			img: `${BASE}/etape-2-securite.png`,
			alt: 'Onglet Sécurité et connexion des réglages ChatGPT',
			title: 'Allez dans « Sécurité et connexion »',
			desc: 'Dans la liste de gauche, choisissez « Sécurité et connexion ».'
		},
		{
			img: `${BASE}/etape-3-toggle.png`,
			alt: 'Interrupteur « codes d’appareil pour Codex »',
			title: 'Activez « Autorisation par code d’appareil pour Codex »',
			desc: 'Basculez l’interrupteur : il devient bleu. C’est tout — revenez ici et entrez votre code.'
		}
	];

	const onKey = (e: KeyboardEvent) => {
		if (e.key === 'Escape') close();
	};
	onMount(() => window.addEventListener('keydown', onKey));
	onDestroy(() => window.removeEventListener('keydown', onKey));
</script>

<!-- Overlay plein écran -->
<div
	class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
	on:click|self={close}
	role="presentation"
>
	<div
		class="w-full max-w-lg max-h-[88vh] overflow-y-auto rounded-2xl bg-white dark:bg-gray-900 ring-1 ring-inset ring-black/10 dark:ring-white/10 shadow-2xl"
		role="dialog"
		aria-modal="true"
		aria-label={$i18n.t('Activer les codes d’appareil ChatGPT')}
	>
		<!-- En-tête collant -->
		<div
			class="sticky top-0 z-10 flex items-start justify-between gap-3 px-5 sm:px-6 pt-5 pb-3 bg-white/95 dark:bg-gray-900/95 backdrop-blur border-b border-black/5 dark:border-white/10"
		>
			<div>
				<div class="text-base font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Activer la connexion ChatGPT (une seule fois)')}
				</div>
				<p class="mt-1 text-[13px] leading-relaxed text-gray-600 dark:text-gray-300">
					{$i18n.t(
						'Par sécurité, ChatGPT bloque les codes d’appareil par défaut. Il suffit de l’activer une fois dans vos réglages.'
					)}
				</p>
			</div>
			<button
				type="button"
				class="flex-none -mr-1 -mt-1 h-8 w-8 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-white/10 transition flex items-center justify-center"
				on:click={close}
				aria-label={$i18n.t('Fermer')}
			>
				✕
			</button>
		</div>

		<!-- Étapes illustrées -->
		<div class="px-5 sm:px-6 py-5 flex flex-col gap-6">
			{#each steps as step, i}
				<div class="flex flex-col gap-2.5">
					<div class="flex items-start gap-3">
						<span
							class="flex-none h-6 w-6 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300 text-xs font-bold flex items-center justify-center"
							>{i + 1}</span
						>
						<div class="min-w-0">
							<div class="text-sm font-semibold text-gray-900 dark:text-white">
								{$i18n.t(step.title)}
							</div>
							<p class="mt-0.5 text-[13px] leading-relaxed text-gray-600 dark:text-gray-300">
								{$i18n.t(step.desc)}
							</p>
						</div>
					</div>
					<div
						class="ml-9 rounded-xl overflow-hidden ring-1 ring-inset ring-black/10 dark:ring-white/10 bg-gray-50 dark:bg-black/20"
					>
						<img src={step.img} alt={step.alt} class="w-full h-auto block" loading="lazy" />
					</div>
				</div>
			{/each}

			<!-- Note compte pro -->
			<div
				class="rounded-xl bg-gray-50 dark:bg-white/[0.03] ring-1 ring-inset ring-black/5 dark:ring-white/10 px-4 py-3 text-[13px] leading-relaxed text-gray-600 dark:text-gray-300"
			>
				<span class="font-medium text-gray-800 dark:text-gray-100"
					>{$i18n.t('Compte professionnel / entreprise ?')}</span
				>
				{$i18n.t(
					'C’est votre administrateur qui doit activer l’option (Espace de travail → Autorisations).'
				)}
			</div>

			<a
				href="https://learn.chatgpt.com/docs/auth"
				target="_blank"
				rel="noopener noreferrer"
				class="text-[13px] font-medium text-amber-700 dark:text-amber-300 hover:underline"
			>
				{$i18n.t('Voir le guide officiel ChatGPT')} ↗
			</a>
		</div>

		<!-- Pied collant -->
		<div
			class="sticky bottom-0 flex justify-end px-5 sm:px-6 py-4 bg-white/95 dark:bg-gray-900/95 backdrop-blur border-t border-black/5 dark:border-white/10"
		>
			<button
				type="button"
				class="text-sm font-semibold px-5 py-2.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black"
				on:click={close}
			>
				{$i18n.t('C’est activé, je réessaie')}
			</button>
		</div>
	</div>
</div>
