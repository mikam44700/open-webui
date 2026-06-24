<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getSkills, setSkillEnabled } from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	type Skill = {
		name: string;
		category?: string | null;
		description?: string;
		enabled: boolean;
	};

	let loading = true;
	let bridgeDown = false;
	let skills: Skill[] = [];
	let search = '';

	$: filtered = search.trim()
		? skills.filter(
				(s) =>
					s.name.toLowerCase().includes(search.toLowerCase()) ||
					(s.description ?? '').toLowerCase().includes(search.toLowerCase())
			)
		: skills;

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
				{$i18n.t('Le pont vers Hermes ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
			{$i18n.t('Compétences réutilisables exécutées par ton cerveau Hermes')}
		</div>

		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Rechercher une compétence')}
			bind:value={search}
		/>

		{#if filtered.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
				{#each filtered as skill (skill.name)}
					<div
						class="flex items-start gap-3 border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3"
					>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<div class="text-sm font-medium truncate">{skill.name}</div>
								{#if skill.category}
									<span
										class="flex-none text-[10px] px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-850 text-gray-500"
										>{skill.category}</span
									>
								{/if}
							</div>
							{#if skill.description}
								<div class="text-xs text-gray-500 mt-0.5 line-clamp-2">{skill.description}</div>
							{/if}
						</div>
						<div class="flex-none self-center">
							<Switch state={skill.enabled} on:change={() => toggle(skill)} />
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
					{$i18n.t('Ajoute des compétences à ton cerveau Hermes pour les voir ici.')}
				</div>
			</div>
		{/if}
	{/if}
</div>
