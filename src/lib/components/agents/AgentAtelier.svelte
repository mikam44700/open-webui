<script lang="ts">
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import { toast } from 'svelte-sonner';

	import { getModels } from '$lib/apis';
	import { createAgent } from '$lib/apis/agents';
	import { generateAgent, type GeneratedAgent } from '$lib/agents/generator';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	type Phase = 'brief' | 'generating' | 'result' | 'error';
	let phase: Phase = 'brief';

	let brief = '';
	let adjustment = '';
	let showAdjust = false;
	let result: GeneratedAgent | null = null;
	let errorMsg = '';
	let activating = false;

	let model = '';
	let briefEl: HTMLTextAreaElement;

	// Suggestions concrètes (langage dirigeant, pas de jargon).
	const ideas = [
		'Relancer mes clients qui n’ont pas payé, avec tact',
		'Répondre vite et bien aux demandes des clients',
		'Préparer mes devis et les relancer au bon moment',
		'Animer mes réseaux sociaux',
		'Trier mes emails et préparer les réponses',
		'Faire progresser mon équipe commerciale'
	];

	// Messages rassurants pendant la fabrication.
	const genMessages = [
		'Je cerne précisément son métier…',
		'Je rédige sa méthode de travail…',
		'J’ajoute ses livrables concrets…',
		'Je pose ses garde-fous…',
		'Dernières finitions…'
	];
	let genMsg = genMessages[0];
	let genTimer: ReturnType<typeof setInterval> | null = null;

	const startGenMessages = () => {
		stopGenMessages();
		let i = 0;
		genMsg = genMessages[0];
		genTimer = setInterval(() => {
			i = (i + 1) % genMessages.length;
			genMsg = genMessages[i];
		}, 1900);
	};
	const stopGenMessages = () => {
		if (genTimer) {
			clearInterval(genTimer);
			genTimer = null;
		}
	};

	const loadModels = async () => {
		try {
			const res = await getModels(localStorage.token);
			const list = res?.data ?? res ?? [];
			model = list?.[0]?.id ?? '';
		} catch {
			/* géré au moment de générer */
		}
	};

	onMount(loadModels);

	// Focus auto du champ quand on ouvre / revient à l'écran de saisie.
	$: if (show && phase === 'brief') {
		tick().then(() => briefEl?.focus());
	}

	const useIdea = async (t: string) => {
		brief = t;
		await tick();
		briefEl?.focus();
	};

	const generate = async () => {
		if (!brief.trim()) return;
		phase = 'generating';
		errorMsg = '';
		startGenMessages();
		try {
			if (!model) await loadModels();
			result = await generateAgent(localStorage.token, model, brief.trim());
			phase = 'result';
		} catch (e: any) {
			errorMsg = e?.message ?? 'La génération a échoué.';
			phase = 'error';
		} finally {
			stopGenMessages();
		}
	};

	const regenerate = async () => {
		phase = 'generating';
		errorMsg = '';
		startGenMessages();
		try {
			result = await generateAgent(
				localStorage.token,
				model,
				brief.trim(),
				result ?? undefined,
				adjustment.trim() || undefined
			);
			adjustment = '';
			showAdjust = false;
			phase = 'result';
		} catch (e: any) {
			errorMsg = e?.message ?? 'La génération a échoué.';
			phase = 'error';
		} finally {
			stopGenMessages();
		}
	};

	const activate = async () => {
		if (!result) return;
		activating = true;
		try {
			await createAgent(localStorage.token, {
				name: result.label,
				description: result.description,
				soul: result.soul
			});
			toast.success($i18n.t('{{name}} est prêt à travailler', { name: result.label }));
			dispatch('created');
			close();
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Un agent porte déjà ce nom'));
			} else {
				toast.error($i18n.t('Impossible d’activer cet agent'));
			}
			activating = false;
		}
	};

	const restart = () => {
		result = null;
		adjustment = '';
		showAdjust = false;
		phase = 'brief';
	};

	const close = () => {
		show = false;
		stopGenMessages();
		setTimeout(() => {
			phase = 'brief';
			brief = '';
			result = null;
			adjustment = '';
			showAdjust = false;
			activating = false;
		}, 200);
	};

	// Découpe la mission en sections (## …) pour un affichage lisible et premium.
	type Section = { title: string; body: string; icon: string };
	const iconFor = (title: string): string => {
		const t = title.toLowerCase();
		if (t.startsWith('identit')) return '🪪';
		if (t.startsWith('mission')) return '🎯';
		if (t.startsWith('méthode') || t.startsWith('methode')) return '🛠️';
		if (t.startsWith('livrable')) return '📦';
		if (t.startsWith('garde')) return '🛡️';
		return '•';
	};
	$: sections = ((): Section[] => {
		if (!result?.soul) return [];
		return result.soul
			.split(/^##\s+/m)
			.map((p) => p.trim())
			.filter(Boolean)
			.map((p) => {
				const nl = p.indexOf('\n');
				const title = (nl >= 0 ? p.slice(0, nl) : p).trim();
				const body = (nl >= 0 ? p.slice(nl + 1) : '').trim();
				return { title, body, icon: iconFor(title) };
			});
	})();
</script>

{#if show}
	<div class="fixed inset-0 z-[60] bg-white dark:bg-gray-900 overflow-y-auto" transition:fade={{ duration: 150 }}>
		<!-- Barre du haut -->
		<div
			class="sticky top-0 z-10 flex items-center justify-between px-5 py-4 bg-white/80 dark:bg-gray-900/80 backdrop-blur"
		>
			<div class="flex items-center gap-2 text-sm font-medium text-gray-400">
				<span>✨</span>{$i18n.t('Atelier des agents')}
			</div>
			<button
				class="size-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={close}
				aria-label={$i18n.t('Fermer')}>✕</button
			>
		</div>

		<div class="max-w-2xl mx-auto px-5 pb-28">
			{#if phase === 'brief'}
				<div class="text-center mt-[7vh]" in:fly={{ y: 12, duration: 300 }}>
					<div class="text-3xl sm:text-4xl font-semibold tracking-tight leading-tight">
						{$i18n.t('Votre nouveau collègue,')}<br />{$i18n.t('en une phrase.')}
					</div>
					<div class="text-sm text-gray-500 mt-3">
						{$i18n.t('Décrivez ce dont vous avez besoin. On fabrique l’agent. Vous validez.')}
					</div>
				</div>

				<div class="mt-8">
					<textarea
						bind:this={briefEl}
						bind:value={brief}
						rows="3"
						placeholder={$i18n.t('Ex : relancer mes clients qui n’ont pas payé, avec tact et sans les braquer')}
						class="w-full text-base bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-2xl px-4 py-3.5 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition resize-none"
						on:keydown={(e) => {
							if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') generate();
						}}
					></textarea>

					<div class="flex flex-wrap gap-2 justify-center mt-4">
						{#each ideas as idea}
							<button
								class="text-xs px-3 py-1.5 rounded-full border border-gray-150 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								on:click={() => useIdea(idea)}
							>
								{idea}
							</button>
						{/each}
					</div>
				</div>

				<div class="mt-8 flex justify-center">
					<button
						class="text-sm font-medium px-6 py-3 rounded-2xl bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
						disabled={!brief.trim()}
						on:click={generate}
					>
						✨ {$i18n.t('Créer mon agent')}
					</button>
				</div>
				<div class="text-center text-[11px] text-gray-400 mt-3">
					{$i18n.t('Astuce : ⌘ + Entrée pour lancer')}
				</div>
			{:else if phase === 'generating'}
				<div class="flex flex-col items-center gap-6 mt-[20vh]" in:fade>
					<div class="atelier-orb"></div>
					<div class="text-lg font-medium">{$i18n.t('Je fabrique votre agent…')}</div>
					<div class="text-sm text-gray-500 transition-all">{genMsg}</div>
				</div>
			{:else if phase === 'result' && result}
				<div in:fly={{ y: 16, duration: 350 }}>
					<!-- En-tête de l'agent -->
					<div class="flex items-center gap-4 mt-[4vh]">
						<div
							class="flex-none size-16 rounded-3xl bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-850 dark:to-gray-800 flex items-center justify-center text-4xl shadow-sm"
						>
							{result.emoji}
						</div>
						<div class="min-w-0">
							<div class="text-2xl font-semibold truncate">{result.label}</div>
							<div class="text-sm text-gray-500">{result.description}</div>
						</div>
					</div>

					<!-- Sa mission, en sections lisibles -->
					<div class="mt-6 space-y-3">
						{#each sections as s, idx}
							<div
								class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"
								in:fly={{ y: 10, duration: 250, delay: 60 * idx }}
							>
								<div class="flex items-center gap-2 text-sm font-semibold">
									<span>{s.icon}</span>{s.title}
								</div>
								<div
									class="text-sm text-gray-600 dark:text-gray-300 mt-2 whitespace-pre-line leading-relaxed"
								>
									{s.body}
								</div>
							</div>
						{/each}
					</div>

					<!-- Ajustement en langage naturel -->
					{#if showAdjust}
						<div class="mt-4 flex flex-col sm:flex-row gap-2" in:fly={{ y: 8, duration: 200 }}>
							<input
								bind:value={adjustment}
								placeholder={$i18n.t('Ex : rends-le plus diplomate, ajoute la relance par SMS')}
								class="flex-1 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
								on:keydown={(e) => {
									if (e.key === 'Enter' && adjustment.trim()) regenerate();
								}}
							/>
							<button
								class="text-sm px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-40"
								disabled={!adjustment.trim()}
								on:click={regenerate}>{$i18n.t('Régénérer')}</button
							>
						</div>
					{/if}
				</div>
			{:else if phase === 'error'}
				<div class="text-center mt-[18vh] flex flex-col items-center gap-3" in:fade>
					<div class="text-3xl">😕</div>
					<div class="text-lg font-medium">{$i18n.t('La génération a échoué')}</div>
					<div class="text-sm text-gray-500 max-w-sm">{errorMsg}</div>
					<button
						class="mt-3 text-sm px-5 py-2.5 rounded-2xl bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition"
						on:click={generate}>{$i18n.t('Réessayer')}</button
					>
				</div>
			{/if}
		</div>

		<!-- Barre d'actions (uniquement sur le résultat) -->
		{#if phase === 'result' && result}
			<div
				class="sticky bottom-0 z-10 bg-white/85 dark:bg-gray-900/85 backdrop-blur border-t border-gray-100 dark:border-gray-850"
			>
				<div class="max-w-2xl mx-auto px-5 py-3.5 flex items-center justify-between gap-3">
					<button
						class="text-sm px-3 py-2 rounded-xl text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
						on:click={restart}>↻ {$i18n.t('Recommencer')}</button
					>
					<div class="flex items-center gap-2">
						<button
							class="text-sm px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={() => (showAdjust = !showAdjust)}>{$i18n.t('Ajuster')}</button
						>
						<button
							class="text-sm font-medium px-5 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition disabled:opacity-50"
							disabled={activating}
							on:click={activate}
						>
							{activating ? $i18n.t('Activation…') : '✓ ' + $i18n.t('Activer cet agent')}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.atelier-orb {
		width: 64px;
		height: 64px;
		border-radius: 9999px;
		background: conic-gradient(from 0deg, #6366f1, #8b5cf6, #ec4899, #6366f1);
		filter: blur(2px);
		animation: orb-spin 1.4s linear infinite, orb-pulse 1.8s ease-in-out infinite;
	}
	@keyframes orb-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@keyframes orb-pulse {
		0%,
		100% {
			transform: scale(0.92);
			opacity: 0.85;
		}
		50% {
			transform: scale(1.08);
			opacity: 1;
		}
	}
</style>
