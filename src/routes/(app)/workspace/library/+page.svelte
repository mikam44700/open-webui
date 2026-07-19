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
				iconWrap: 'bg-violet-100 text-violet-600 dark:bg-[#6b62f2]/15 dark:text-[#a5a0f7]',
				visible: isAdmin || !!perms.models
			},
			{
				id: 'knowledge',
				titre: 'Connaissances',
				desc: 'Les documents et dossiers que vos agents connaissent par cœur.',
				href: '/workspace/knowledge',
				icon: BookOpen,
				iconWrap: 'bg-violet-100 text-violet-600 dark:bg-[#6b62f2]/15 dark:text-[#a5a0f7]',
				visible: isAdmin || !!perms.knowledge
			},
			{
				id: 'prompts',
				titre: 'Prompts',
				desc: "Vos instructions prêtes à l'emploi, accessibles avec « / » dans le chat.",
				href: '/workspace/prompts',
				icon: ChatBubble,
				iconWrap: 'bg-violet-100 text-violet-600 dark:bg-[#6b62f2]/15 dark:text-[#a5a0f7]',
				visible: isAdmin || !!perms.prompts
			},
			{
				id: 'skills',
				titre: 'Skills',
				desc: 'Les compétences réutilisables que vos agents savent exécuter.',
				href: '/workspace/skills',
				icon: Sparkles,
				iconWrap: 'bg-violet-100 text-violet-600 dark:bg-[#6b62f2]/15 dark:text-[#a5a0f7]',
				visible: isAdmin || !!perms.skills
			},
			{
				id: 'tools',
				titre: 'Outils',
				desc: 'Les outils sur mesure que vos agents peuvent utiliser.',
				href: '/workspace/tools',
				icon: Wrench,
				iconWrap: 'bg-violet-100 text-violet-600 dark:bg-[#6b62f2]/15 dark:text-[#a5a0f7]',
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
	wrap="from-violet-200/60 via-slate-100/60 to-violet-100/40 dark:from-[#6b62f2]/25 dark:via-[#161616]/80 dark:to-[#0a0a0a]/90"
	halo1="bg-violet-300/40 dark:bg-[#6b62f2]/25"
	halo2="bg-indigo-200/30 dark:bg-[#6b62f2]/10"
/>

<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 pb-8">
	{#each sections as section (section.id)}
		<button
			class="group flex items-start gap-4 rounded-3xl border border-gray-200/80 dark:border-white/6 bg-white dark:bg-[#161616] p-6 text-left transition-colors hover:border-gray-300 dark:hover:border-white/15 cursor-pointer"
			on:click={() => goto(section.href)}
		>
			<div
				class="flex size-12 shrink-0 items-center justify-center rounded-2xl {section.iconWrap}"
			>
				<svelte:component this={section.icon} className="size-6" />
			</div>
			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-2">
					<div class="font-medium tracking-tight text-gray-900 dark:text-gray-50">
						{section.titre}
					</div>
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
