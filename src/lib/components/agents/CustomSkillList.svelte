<script lang="ts">
	// Page « Compétences » de l'Espace de travail : NOS compétences maison (sur mesure).
	// Distinctes des compétences natives Hermes — ce sont celles qu'on crée pour nos agents.
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getCustomSkills,
		getCustomSkill,
		createCustomSkill,
		deleteCustomSkill
	} from '$lib/apis/capabilities';
	import { getModels } from '$lib/apis';
	import { getIntegrations } from '$lib/apis/integrations';
	import { getConnectors } from '$lib/apis/connectors';
	import { generateSkill, transformSkill, toRawSkillUrl } from '$lib/skills/skill-generator';
	import { expertMode } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import { SKILL_CATEGORIES } from '$lib/skills/skill-generator';

	const i18n = getContext('i18n');

	type CustomSkill = { name: string; label: string; description: string; category?: string };

	let loading = true;
	let bridgeDown = false;
	let skills: CustomSkill[] = [];
	let search = '';

	// Modale de création
	let showCreate = false;
	let saving = false;
	let formLabel = '';
	let formDescription = '';
	let formInstructions = '';
	let formCategory = 'Autres';

	// Regroupement par catégorie + filtre de recherche.
	$: q = search.trim().toLowerCase();
	$: filtered = q
		? skills.filter(
				(s) =>
					s.label.toLowerCase().includes(q) ||
					(s.description ?? '').toLowerCase().includes(q) ||
					(s.category ?? '').toLowerCase().includes(q)
			)
		: skills;
	$: groups = (() => {
		const map = new Map<string, CustomSkill[]>();
		for (const s of filtered) {
			const cat = s.category || 'Autres';
			if (!map.has(cat)) map.set(cat, []);
			map.get(cat)!.push(s);
		}
		return [...map.keys()]
			.sort((a, b) => a.localeCompare(b))
			.map((cat) => ({ cat, items: map.get(cat)!.slice().sort((x, y) => x.label.localeCompare(y.label)) }));
	})();

	// Génération par l'IA (✨) — réutilise le moteur de l'Atelier d'agents.
	let model = '';
	let genBrief = '';
	let generating = false;
	let genError = '';

	// Import d'une skill existante (URL GitHub) → transformée au niveau 4.
	let showImport = false;
	let importUrl = '';
	let importing = false;
	let importError = '';

	const loadModel = async () => {
		if (model) return;
		try {
			const res = await getModels(localStorage.token);
			const list = res?.data ?? res ?? [];
			model = list?.[0]?.id ?? '';
		} catch {
			/* géré au moment de générer */
		}
	};

	// Outils réellement connectés : la compétence générée les mobilisera nommément.
	const fetchConnectedTools = async (): Promise<string[]> => {
		const out: string[] = [];
		try {
			const res: any = await getIntegrations(localStorage.token);
			const list = Array.isArray(res) ? res : (res?.integrations ?? []);
			for (const it of list) {
				if (it?.state === 'connected') out.push(it.label || it.name || it.id);
			}
		} catch {
			/* tolérant */
		}
		try {
			const res: any = await getConnectors(localStorage.token);
			const list = Array.isArray(res) ? res : (res?.connectors ?? []);
			for (const c of list) {
				if (c?.enabled !== false) out.push(c.label || c.id || c.name);
			}
		} catch {
			/* tolérant */
		}
		return [...new Set(out.filter(Boolean))];
	};

	const doGenerate = async () => {
		if (!genBrief.trim()) {
			toast.error($i18n.t('Décris d’abord ce que la compétence doit faire'));
			return;
		}
		generating = true;
		genError = '';
		try {
			if (!model) await loadModel();
			const tools = await fetchConnectedTools();
			const result = await generateSkill(localStorage.token, model, genBrief.trim(), {
				connectedTools: tools
			});
			// On remplit le formulaire : le dirigeant relit et ajuste avant de créer.
			formLabel = result.label;
			formDescription = result.description;
			formInstructions = result.instructions;
			formCategory = result.category || 'Autres';
		} catch (err: any) {
			genError = err?.message || $i18n.t('La génération a échoué. Réessaie.');
		} finally {
			generating = false;
		}
	};

	// Confirmation de suppression
	let showDelete = false;
	let toDelete: CustomSkill | null = null;

	// Détail d'une compétence (contenu complet, au clic sur une carte)
	let showDetail = false;
	let detailLoading = false;
	let detail: { name: string; label: string; description: string; category: string; instructions: string } | null = null;

	const openDetail = async (skill: CustomSkill) => {
		showDetail = true;
		detailLoading = true;
		detail = null;
		try {
			detail = await getCustomSkill(localStorage.token, skill.name);
		} catch {
			toast.error($i18n.t('Impossible d’ouvrir cette compétence'));
			showDetail = false;
		} finally {
			detailLoading = false;
		}
	};

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getCustomSkills(localStorage.token);
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

	const openCreate = () => {
		formLabel = '';
		formDescription = '';
		formInstructions = '';
		formCategory = 'Autres';
		genBrief = '';
		genError = '';
		showCreate = true;
		loadModel();
	};

	const openImport = () => {
		importUrl = '';
		importError = '';
		showImport = true;
		loadModel();
	};

	// Récupère le SKILL.md d'une URL GitHub, le transforme au niveau 4, et pré-remplit la création.
	const doImport = async () => {
		if (!importUrl.trim()) {
			toast.error($i18n.t('Colle l’URL d’une skill (GitHub)'));
			return;
		}
		importing = true;
		importError = '';
		try {
			const rawUrl = toRawSkillUrl(importUrl);
			const res = await fetch(rawUrl);
			if (!res.ok) throw new Error('introuvable');
			const sourceMarkdown = await res.text();
			if (!sourceMarkdown.trim() || sourceMarkdown.length < 20) {
				throw new Error('vide');
			}
			if (!model) await loadModel();
			const tools = await fetchConnectedTools();
			const result = await transformSkill(localStorage.token, model, sourceMarkdown, {
				connectedTools: tools
			});
			// On bascule sur la modale de création, pré-remplie : le dirigeant relit et ajuste.
			formLabel = result.label;
			formDescription = result.description;
			formInstructions = result.instructions;
			formCategory = result.category || 'Autres';
			genBrief = '';
			genError = '';
			showImport = false;
			showCreate = true;
		} catch (err: any) {
			const msg = err?.message;
			importError =
				msg === 'introuvable'
					? $i18n.t('SKILL.md introuvable à cette URL. Vérifie le lien (vers le dossier de la skill ou son SKILL.md).')
					: msg === 'vide'
						? $i18n.t('Le fichier récupéré est vide.')
						: $i18n.t('Import impossible. Vérifie l’URL et réessaie.');
		} finally {
			importing = false;
		}
	};

	const submitCreate = async () => {
		if (!formLabel.trim()) {
			toast.error($i18n.t('Donnez un nom à la compétence'));
			return;
		}
		saving = true;
		try {
			await createCustomSkill(
				localStorage.token,
				formLabel.trim(),
				formDescription.trim(),
				formInstructions.trim(),
				formCategory || 'Autres'
			);
			showCreate = false;
			toast.success($i18n.t('Compétence créée'));
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'exists') {
				toast.error($i18n.t('Une compétence porte déjà ce nom'));
			} else {
				toast.error($i18n.t('Impossible de créer la compétence'));
			}
		} finally {
			saving = false;
		}
	};

	const askDelete = (skill: CustomSkill) => {
		toDelete = skill;
		showDelete = true;
	};

	const confirmDelete = async () => {
		if (!toDelete) return;
		try {
			await deleteCustomSkill(localStorage.token, toDelete.name);
			toast.success($i18n.t('Compétence supprimée'));
			await load();
		} catch {
			toast.error($i18n.t('Impossible de supprimer la compétence'));
		} finally {
			toDelete = null;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
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
		<!-- En-tête + bouton créer -->
		<div class="flex items-start justify-between gap-3 mb-4">
			<div>
				<div class="text-sm text-gray-700 dark:text-gray-200 font-medium">
					{$i18n.t('Vos compétences sur mesure')}
				</div>
				<div class="text-xs text-gray-500 mt-1 max-w-2xl">
					{$i18n.t('Des savoir-faire que vous créez vous-même pour vos agents (une procédure métier, une façon de faire propre à votre entreprise). Une fois créée, une compétence est utilisable par vos agents.')}
				</div>
			</div>
			<div class="flex-none flex items-center gap-2">
				<button
					class="text-sm px-3.5 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition font-medium"
					on:click={openCreate}
				>
					✨ {$i18n.t('Générer avec l’IA')}
				</button>
				{#if $expertMode}
					<button
						class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition font-medium"
						on:click={openImport}
						title={$i18n.t('Réservé aux réglages avancés')}
					>
						⬇ {$i18n.t('Importer une skill')}
					</button>
				{/if}
			</div>
		</div>

		{#if skills.length > 0}
			<!-- Barre de recherche (utile dès qu'il y a beaucoup de compétences) -->
			<input
				class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-4"
				placeholder={$i18n.t('Rechercher une compétence (nom, catégorie…)')}
				bind:value={search}
			/>

			{#if groups.length > 0}
				<div class="flex flex-col gap-5">
					{#each groups as group (group.cat)}
						<div>
							<div class="flex items-baseline gap-2 mb-2">
								<div class="text-sm font-semibold">{group.cat}</div>
								<div class="text-xs text-gray-400">{group.items.length}</div>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
								{#each group.items as skill (skill.name)}
									<div
										role="button"
										tabindex="0"
										class="group flex items-start gap-3 border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3.5 transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm cursor-pointer"
										on:click={() => openDetail(skill)}
										on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openDetail(skill)}
										title={$i18n.t('Voir la compétence en détail')}
									>
										<div class="flex-1 min-w-0">
											<div class="text-sm font-medium truncate">{skill.label}</div>
											{#if skill.description}
												<div class="text-xs text-gray-500 mt-0.5 line-clamp-2">{skill.description}</div>
											{/if}
										</div>
										<button
											class="flex-none self-center text-xs text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
											title={$i18n.t('Supprimer')}
											on:click|stopPropagation={() => askDelete(skill)}
										>
											{$i18n.t('Supprimer')}
										</button>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center text-xs text-gray-500 py-12">
					{$i18n.t('Aucune compétence ne correspond à votre recherche.')}
				</div>
			{/if}
		{:else}
			<div
				class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Aucune compétence maison pour l’instant')}</div>
				<div class="text-xs text-gray-500 max-w-md">
					{$i18n.t('Créez votre première compétence sur mesure : décrivez un savoir-faire propre à votre entreprise, et vos agents pourront l’utiliser.')}
				</div>
				<button
					class="text-sm px-3.5 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition font-medium"
					on:click={openCreate}
				>
					✨ {$i18n.t('Générer avec l’IA')}
				</button>
			</div>
		{/if}
	{/if}
</div>

<!-- Modale de création -->
<Modal bind:show={showCreate} size="md">
	<div class="p-5">
		<div class="text-base font-semibold mb-1">{$i18n.t('Créer une compétence')}</div>
		<div class="text-xs text-gray-500 mb-4">
			{$i18n.t('Décrivez le savoir-faire en clair. Vos agents pourront s’en servir.')}
		</div>

		<!-- ✨ Génération par l'IA : décris en une phrase, on remplit le formulaire pour toi -->
		<div
			class="rounded-2xl border border-violet-200/70 dark:border-violet-900/40 bg-gradient-to-br from-violet-50/80 to-indigo-50/60 dark:from-violet-950/30 dark:to-indigo-950/20 p-3.5 mb-5"
		>
			<div class="text-xs font-medium text-violet-900 dark:text-violet-200 mb-2">
				✨ {$i18n.t('Générer avec l’IA')}
			</div>
			<textarea
				class="w-full text-sm bg-white/70 dark:bg-gray-900/50 border border-violet-100 dark:border-violet-900/40 rounded-xl px-3 py-2 outline-none min-h-16 resize-y"
				placeholder={$i18n.t('Décris la compétence en une phrase. Ex. : relancer les devis sans réponse après 7 jours, poliment.')}
				bind:value={genBrief}
				disabled={generating}
			></textarea>
			{#if genError}
				<div class="text-xs text-red-500 mt-1">{genError}</div>
			{/if}
			<div class="flex justify-end mt-2">
				<button
					class="text-xs px-3 py-1.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 transition font-medium disabled:opacity-50 flex items-center gap-1.5"
					on:click={doGenerate}
					disabled={generating}
				>
					{#if generating}
						<Spinner className="size-3.5" />
						{$i18n.t('Génération…')}
					{:else}
						✨ {$i18n.t('Générer')}
					{/if}
				</button>
			</div>
			<div class="text-[11px] text-gray-500 dark:text-gray-400 mt-1.5">
				{$i18n.t('L’IA remplit les champs ci-dessous. Vous pouvez tout relire et ajuster avant de créer.')}
			</div>
		</div>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Nom')}
		</label>
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Ex. : Relance de devis')}
			bind:value={formLabel}
		/>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('À quoi ça sert')}
		</label>
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Ex. : Relancer les devis restés sans réponse, poliment.')}
			bind:value={formDescription}
		/>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Catégorie')}
		</label>
		<select
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			bind:value={formCategory}
		>
			{#each SKILL_CATEGORIES as cat}
				<option value={cat}>{cat}</option>
			{/each}
		</select>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Comment faire (la procédure)')}
		</label>
		<textarea
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-4 min-h-32 resize-y"
			placeholder={$i18n.t('Décrivez les étapes, le ton, les règles à respecter…')}
			bind:value={formInstructions}
		></textarea>

		<div class="flex justify-end gap-2">
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => (showCreate = false)}
				disabled={saving}
			>
				{$i18n.t('Annuler')}
			</button>
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition font-medium disabled:opacity-50"
				on:click={submitCreate}
				disabled={saving}
			>
				{saving ? $i18n.t('Création…') : $i18n.t('Créer')}
			</button>
		</div>
	</div>
</Modal>

<!-- Modale de détail : le contenu complet de la compétence -->
<Modal bind:show={showDetail} size="lg">
	<div class="p-5">
		{#if detailLoading}
			<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
		{:else if detail}
			<div class="flex items-start justify-between gap-3 mb-1">
				<div class="text-lg font-semibold">{detail.label}</div>
				<span
					class="flex-none text-[11px] px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
				>
					{detail.category}
				</span>
			</div>
			{#if detail.description}
				<div class="text-xs text-gray-500 mb-4">{detail.description}</div>
			{/if}
			<div
				class="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap leading-relaxed border-t border-gray-100 dark:border-gray-850 pt-4 max-h-[60vh] overflow-y-auto"
			>{detail.instructions}</div>
			<div class="flex justify-end gap-2 mt-5">
				<button
					class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => (showDetail = false)}
				>
					{$i18n.t('Fermer')}
				</button>
			</div>
		{/if}
	</div>
</Modal>

<!-- Modale d'import d'une skill existante -->
<Modal bind:show={showImport} size="md">
	<div class="p-5">
		<div class="text-base font-semibold mb-1">⬇ {$i18n.t('Importer une skill')}</div>
		<div class="text-xs text-gray-500 mb-4">
			{$i18n.t('Colle l’adresse d’une compétence trouvée sur GitHub. On la récupère et on la transforme automatiquement au niveau Agent OS (en français, branchée à tes outils, avec garde-fous).')}
		</div>

		<label class="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
			{$i18n.t('Adresse de la skill (GitHub)')}
		</label>
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-1"
			placeholder="https://github.com/.../skills/relance-impayes"
			bind:value={importUrl}
			disabled={importing}
		/>
		<div class="text-[11px] text-gray-400 mb-3">
			{$i18n.t('Lien vers le dossier de la skill ou directement son fichier SKILL.md.')}
		</div>

		{#if importError}
			<div class="text-xs text-red-500 mb-3">{importError}</div>
		{/if}

		<div class="flex justify-end gap-2">
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => (showImport = false)}
				disabled={importing}
			>
				{$i18n.t('Annuler')}
			</button>
			<button
				class="text-sm px-3.5 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition font-medium disabled:opacity-50 flex items-center gap-1.5"
				on:click={doImport}
				disabled={importing}
			>
				{#if importing}
					<Spinner className="size-3.5" />
					{$i18n.t('Récupération + transformation…')}
				{:else}
					⬇ {$i18n.t('Récupérer et transformer')}
				{/if}
			</button>
		</div>
	</div>
</Modal>

<!-- Confirmation de suppression -->
<ConfirmDialog
	bind:show={showDelete}
	title={$i18n.t('Supprimer cette compétence ?')}
	message={toDelete
		? $i18n.t('« {{label}} » sera définitivement supprimée. Cette action est irréversible.', {
				label: toDelete.label
			})
		: ''}
	confirmLabel={$i18n.t('Supprimer')}
	cancelLabel={$i18n.t('Annuler')}
	on:confirm={confirmDelete}
/>
