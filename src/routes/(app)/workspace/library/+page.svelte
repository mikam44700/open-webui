<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { getModelItems } from '$lib/apis/models';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getPromptList } from '$lib/apis/prompts';
	import { getSkillList } from '$lib/apis/skills';
	import { getToolList } from '$lib/apis/tools';
	import HeroBanner from '$lib/components/workspace/common/HeroBanner.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';

	// Les 5 sections open-webui d'origine, regroupées ici en cartes (routes conservées).
	let sections = [];
	let counts: Record<string, number | null> = {};

	// Un résultat de liste peut être un tableau brut ou une page { items, total }.
	const compter = (res) =>
		res == null ? null : Array.isArray(res) ? res.length : (res.total ?? res.items?.length ?? null);

	$: {
		const perms = $user?.permissions?.workspace ?? {};
		const isAdmin = $user?.role === 'admin';

		sections = [
			{
				id: 'models',
				titre: 'Modèles',
				desc: 'Vos assistants personnalisés : leur caractère, leurs instructions, leur modèle IA.',
				href: '/workspace/models',
				icon: Cube,
				iconWrap: 'bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-300',
				visible: isAdmin || !!perms.models
			},
			{
				id: 'knowledge',
				titre: 'Connaissances',
				desc: 'Les documents et dossiers que vos agents connaissent par cœur.',
				href: '/workspace/knowledge',
				icon: BookOpen,
				iconWrap: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-300',
				visible: isAdmin || !!perms.knowledge
			},
			{
				id: 'prompts',
				titre: 'Prompts',
				desc: "Vos instructions prêtes à l'emploi, accessibles avec « / » dans le chat.",
				href: '/workspace/prompts',
				icon: ChatBubble,
				iconWrap: 'bg-sky-100 text-sky-600 dark:bg-sky-900/40 dark:text-sky-300',
				visible: isAdmin || !!perms.prompts
			},
			{
				id: 'skills',
				titre: 'Skills',
				desc: 'Les compétences réutilisables que vos agents savent exécuter.',
				href: '/workspace/skills',
				icon: Sparkles,
				iconWrap: 'bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-300',
				visible: isAdmin || !!perms.skills
			},
			{
				id: 'tools',
				titre: 'Outils',
				desc: 'Les outils sur mesure que vos agents peuvent utiliser.',
				href: '/workspace/tools',
				icon: Wrench,
				iconWrap: 'bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-300',
				visible: isAdmin || !!perms.tools
			}
		].filter((s) => s.visible);
	}

	onMount(async () => {
		const token = localStorage.token;
		const chargeurs: Record<string, () => Promise<unknown>> = {
			models: () => getModelItems(token, '', null, null, null, null, null),
			knowledge: () => getKnowledgeBases(token),
			prompts: () => getPromptList(token),
			skills: () => getSkillList(token),
			tools: () => getToolList(token)
		};

		// Compteurs chargés en parallèle ; une section en erreur affiche juste sa carte sans compteur.
		await Promise.all(
			sections.map(async (s) => {
				const res = await chargeurs[s.id]().catch(() => null);
				counts = { ...counts, [s.id]: compter(res) };
			})
		);
	});
</script>

<HeroBanner
	lead="Toute la"
	strong="boîte à outils de vos agents"
	sub="Modèles, connaissances, prompts, skills et outils — réunis au même endroit."
	wrap="from-emerald-200/70 via-teal-100/50 to-cyan-100/60 dark:from-emerald-900/30 dark:via-teal-900/20 dark:to-cyan-900/20"
	halo1="bg-emerald-400/30 dark:bg-emerald-500/20"
	halo2="bg-teal-300/30 dark:bg-teal-500/10"
/>

<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 pb-6">
	{#each sections as section (section.id)}
		<button
			class="group flex items-start gap-4 rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900 p-5 text-left transition hover:shadow-md cursor-pointer"
			on:click={() => goto(section.href)}
		>
			<div
				class="flex size-12 shrink-0 items-center justify-center rounded-2xl {section.iconWrap}"
			>
				<svelte:component this={section.icon} className="size-6" />
			</div>
			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-2">
					<div class="font-medium text-gray-900 dark:text-gray-50">{section.titre}</div>
					{#if counts[section.id] != null}
						<span
							class="rounded-full bg-gray-100 dark:bg-gray-850 px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400"
						>
							{counts[section.id]}
						</span>
					{/if}
				</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{section.desc}</div>
			</div>
			<div
				class="self-center text-gray-300 dark:text-gray-600 transition group-hover:text-gray-500 dark:group-hover:text-gray-300"
			>
				<ChevronRight className="size-4" />
			</div>
		</button>
	{/each}
</div>
