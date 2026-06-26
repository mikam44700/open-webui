<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getSkills, setSkillEnabled } from '$lib/apis/capabilities';
	import { expertMode } from '$lib/stores';
	import { skillsFr, skillCategoriesFr, skillCategoryOrder } from '$lib/capabilities/skills-fr';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	type Skill = {
		name: string;
		category?: string | null;
		description?: string;
		enabled: boolean;
	};

	type LocalizedSkill = Skill & { title: string; desc: string; catKey: string; catLabel: string };

	let loading = true;
	let bridgeDown = false;
	let skills: Skill[] = [];
	let search = '';

	// Traduction FR de l'affichage (titre + description + catégorie) avec fallback honnête.
	$: localized = skills.map((s): LocalizedSkill => {
		const fr = skillsFr[s.name];
		const catKey = s.category ?? 'autres';
		return {
			...s,
			title: fr?.title ?? s.name,
			desc: fr?.description ?? (s.description ?? ''),
			catKey,
			catLabel: skillCategoriesFr[catKey] ?? s.category ?? 'Autres'
		};
	});

	$: q = search.trim().toLowerCase();
	$: filtered = q
		? localized.filter(
				(s) =>
					s.title.toLowerCase().includes(q) ||
					s.desc.toLowerCase().includes(q) ||
					s.name.toLowerCase().includes(q) ||
					s.catLabel.toLowerCase().includes(q)
			)
		: localized;

	// Regroupe par catégorie, dans l'ordre défini (catégories connues d'abord, le reste alpha).
	$: groups = (() => {
		const map = new Map<string, LocalizedSkill[]>();
		for (const s of filtered) {
			if (!map.has(s.catKey)) map.set(s.catKey, []);
			map.get(s.catKey)!.push(s);
		}
		const keys = [...map.keys()].sort((a, b) => {
			const ia = skillCategoryOrder.indexOf(a);
			const ib = skillCategoryOrder.indexOf(b);
			if (ia !== -1 && ib !== -1) return ia - ib;
			if (ia !== -1) return -1;
			if (ib !== -1) return 1;
			return (skillCategoriesFr[a] ?? a).localeCompare(skillCategoriesFr[b] ?? b);
		});
		return keys.map((k) => ({
			key: k,
			label: skillCategoriesFr[k] ?? k,
			items: map.get(k)!.slice().sort((a, b) => a.title.localeCompare(b.title))
		}));
	})();

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getSkills(localStorage.token);
			skills = res?.skills ?? [];
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des compétences'));
			}
		} finally {
			loading = false;
		}
	};

	const toggle = async (skill: Skill) => {
		const next = !skill.enabled;
		skills = skills.map((s) => (s.name === skill.name ? { ...s, enabled: next } : s));
		try {
			await setSkillEnabled(localStorage.token, skill.name, next);
		} catch (err) {
			skills = skills.map((s) => (s.name === skill.name ? { ...s, enabled: !next } : s));
			toast.error($i18n.t('Impossible de modifier cette compétence'));
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-5xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Capacités est injoignable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('Le moteur ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- En-tête explicatif : ce que sont les compétences, en clair -->
		<div class="mb-4">
			<div class="text-sm text-gray-700 dark:text-gray-200 font-medium">
				{$i18n.t('Ce que votre assistant sait faire')}
			</div>
			<div class="text-xs text-gray-500 mt-1 max-w-2xl">
				{$i18n.t('Chaque compétence est un savoir-faire que votre assistant peut utiliser (lire vos emails, gérer un agenda, créer un PowerPoint…). Activez ce que vous voulez qu’il puisse faire ; désactivez le reste. Les compétences activées sont aussi celles que vos automatisations peuvent utiliser.')}
			</div>
		</div>

		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-4"
			placeholder={$i18n.t('Rechercher une compétence')}
			bind:value={search}
		/>

		{#if groups.length > 0}
			<div class="flex flex-col gap-5">
				{#each groups as group (group.key)}
					<div>
						<div class="flex items-baseline gap-2 mb-2">
							<div class="text-sm font-semibold">{$i18n.t(group.label)}</div>
							<div class="text-xs text-gray-400">{group.items.length}</div>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
							{#each group.items as skill (skill.name)}
								<div
									class="flex items-start gap-3 border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3"
								>
									<div class="flex-1 min-w-0">
										<div class="text-sm font-medium truncate">{skill.title}</div>
										{#if skill.desc}
											<div class="text-xs text-gray-500 mt-0.5 line-clamp-2">{skill.desc}</div>
										{/if}
										{#if $expertMode}
											<div class="text-[10px] text-gray-400 mt-1 font-mono truncate">{skill.name}</div>
										{/if}
									</div>
									<div class="flex-none self-center">
										<Switch state={skill.enabled} on:change={() => toggle(skill)} />
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div
				class="flex flex-col items-center justify-center text-center py-16 gap-2 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Aucune compétence')}</div>
				<div class="text-xs text-gray-500 max-w-md">
					{search.trim()
						? $i18n.t('Aucune compétence ne correspond à votre recherche.')
						: $i18n.t('Ajoute des compétences à ton assistant pour les voir ici.')}
				</div>
			</div>
		{/if}
	{/if}
</div>
