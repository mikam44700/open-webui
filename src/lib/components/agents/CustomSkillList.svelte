<script lang="ts">
	// Page « Compétences » de l'Espace de travail : NOS compétences maison (sur mesure).
	// Distinctes des compétences natives Hermes — ce sont celles qu'on crée pour nos agents.
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getCustomSkills,
		createCustomSkill,
		deleteCustomSkill
	} from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	type CustomSkill = { name: string; label: string; description: string };

	let loading = true;
	let bridgeDown = false;
	let skills: CustomSkill[] = [];

	// Modale de création
	let showCreate = false;
	let saving = false;
	let formLabel = '';
	let formDescription = '';
	let formInstructions = '';

	// Confirmation de suppression
	let showDelete = false;
	let toDelete: CustomSkill | null = null;

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
		showCreate = true;
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
				formInstructions.trim()
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
			<button
				class="flex-none text-sm px-3.5 py-2 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition font-medium"
				on:click={openCreate}
			>
				+ {$i18n.t('Créer une compétence')}
			</button>
		</div>

		{#if skills.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
				{#each skills as skill (skill.name)}
					<div
						class="group flex items-start gap-3 border border-gray-100 dark:border-gray-850 rounded-2xl px-4 py-3.5 transition hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm"
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
							on:click={() => askDelete(skill)}
						>
							{$i18n.t('Supprimer')}
						</button>
					</div>
				{/each}
			</div>
		{:else}
			<div
				class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Aucune compétence maison pour l’instant')}</div>
				<div class="text-xs text-gray-500 max-w-md">
					{$i18n.t('Créez votre première compétence sur mesure : décrivez un savoir-faire propre à votre entreprise, et vos agents pourront l’utiliser.')}
				</div>
				<button
					class="text-sm px-3.5 py-2 rounded-xl bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition font-medium"
					on:click={openCreate}
				>
					+ {$i18n.t('Créer une compétence')}
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
