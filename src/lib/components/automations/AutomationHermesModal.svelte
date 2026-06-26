<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { expertMode } from '$lib/stores';
	import {
		createAutomation,
		updateAutomation,
		type Automation
	} from '$lib/apis/automations-hermes';

	import Modal from '$lib/components/common/Modal.svelte';
	import { buildRhythm as buildRhythmPayload } from '$lib/automations/labels';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let automation: Automation | null = null; // null = création

	$: editing = automation !== null;

	// Champs
	let name = '';
	let instruction = '';

	// Rythme (preset simple)
	let rhythmType: 'daily' | 'weekly' | 'interval' | 'once' | 'advanced' = 'daily';
	let time = '08:00';
	let weekday = 0; // 0 = lundi
	let everyValue = 2;
	let everyUnit: 'h' | 'm' = 'h';
	let onceAt = '';
	let advancedSchedule = '';
	let changeRhythm = true; // en édition : ne change le rythme que si demandé

	// Mode Expert
	let deliver = '';

	let saving = false;

	const weekdays = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];

	$: if (show) init(automation);

	const init = (a: Automation | null) => {
		if (a) {
			name = a.name;
			instruction = a.instruction;
			deliver = a.deliver ?? '';
			changeRhythm = false; // on ne touche pas au rythme par défaut en édition
		} else {
			name = '';
			instruction = '';
			deliver = '';
			rhythmType = 'daily';
			time = '08:00';
			weekday = 0;
			everyValue = 2;
			everyUnit = 'h';
			onceAt = '';
			advancedSchedule = '';
			changeRhythm = true;
		}
	};

	const buildRhythm = () =>
		buildRhythmPayload({ rhythmType, time, weekday, everyValue, everyUnit, onceAt, advancedSchedule });

	const submit = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Donnez un nom à votre automatisation.'));
			return;
		}
		if (!instruction.trim()) {
			toast.error($i18n.t('Décrivez ce que doit faire l’automatisation.'));
			return;
		}
		saving = true;
		try {
			const expert = $expertMode;
			if (editing && automation) {
				const body: Record<string, unknown> = { name, instruction };
				if (changeRhythm) body.rhythm = buildRhythm();
				if (expert && deliver) body.deliver = deliver;
				await updateAutomation(localStorage.token, automation.id, body, expert);
				toast.success($i18n.t('Automatisation mise à jour'));
			} else {
				const body: Record<string, unknown> = { name, instruction, rhythm: buildRhythm() };
				if (expert && deliver) body.deliver = deliver;
				await createAutomation(localStorage.token, body, expert);
				toast.success($i18n.t('Automatisation créée'));
			}
			show = false;
			dispatch('save');
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Échec de l’enregistrement'));
		} finally {
			saving = false;
		}
	};
</script>

<Modal bind:show size="sm">
	<div class="px-5 py-4">
		<div class="flex justify-between items-center mb-3">
			<div class="text-lg font-medium">
				{editing ? $i18n.t('Modifier l’automatisation') : $i18n.t('Nouvelle automatisation')}
			</div>
			<button class="text-gray-400 hover:text-gray-700" on:click={() => (show = false)} aria-label="Fermer">
				✕
			</button>
		</div>

		<div class="flex flex-col gap-3">
			<label class="text-sm">
				<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Nom')}</span>
				<input
					class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm"
					bind:value={name}
					placeholder={$i18n.t('Ex : Résumé de mes emails du matin')}
					maxlength="200"
				/>
			</label>

			<label class="text-sm">
				<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Que doit faire Agent OS ?')}</span>
				<textarea
					class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm resize-none"
					rows="3"
					bind:value={instruction}
					placeholder={$i18n.t('Ex : Résume mes emails importants reçus depuis hier.')}
					maxlength="5000"
				/>
			</label>

			{#if editing}
				<label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
					<input type="checkbox" bind:checked={changeRhythm} />
					{$i18n.t('Modifier le rythme')}
				</label>
			{/if}

			{#if !editing || changeRhythm}
				<div class="text-sm">
					<span class="text-gray-600 dark:text-gray-300">{$i18n.t('À quel rythme ?')}</span>
					<div class="mt-1 grid grid-cols-2 gap-2">
						<select class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={rhythmType}>
							<option value="daily">{$i18n.t('Chaque jour')}</option>
							<option value="weekly">{$i18n.t('Chaque semaine')}</option>
							<option value="interval">{$i18n.t('À intervalle régulier')}</option>
							<option value="once">{$i18n.t('Une seule fois')}</option>
							{#if $expertMode}
								<option value="advanced">{$i18n.t('Avancé (expression)')}</option>
							{/if}
						</select>

						{#if rhythmType === 'daily'}
							<input type="time" class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={time} />
						{:else if rhythmType === 'weekly'}
							<select class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={weekday}>
								{#each weekdays as d, i}
									<option value={i}>{d}</option>
								{/each}
							</select>
							<input type="time" class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm col-span-2" bind:value={time} />
						{:else if rhythmType === 'interval'}
							<div class="flex gap-2">
								<input type="number" min="1" class="w-20 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={everyValue} />
								<select class="px-2 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={everyUnit}>
									<option value="h">{$i18n.t('heures')}</option>
									<option value="m">{$i18n.t('minutes')}</option>
								</select>
							</div>
						{:else if rhythmType === 'once'}
							<input type="datetime-local" class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={onceAt} />
						{:else if rhythmType === 'advanced'}
							<input
								class="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm font-mono"
								bind:value={advancedSchedule}
								placeholder="0 9 * * 1-5"
							/>
						{/if}
					</div>
				</div>
			{/if}

			{#if $expertMode}
				<label class="text-sm">
					<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Canal de livraison (avancé)')}</span>
					<input
						class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm font-mono"
						bind:value={deliver}
						placeholder="origin"
					/>
				</label>
			{/if}
		</div>

		<div class="flex justify-end gap-2 mt-4">
			<button class="px-3 py-1.5 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (show = false)}>
				{$i18n.t('Annuler')}
			</button>
			<button
				class="px-3 py-1.5 rounded-lg text-sm bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
				disabled={saving}
				on:click={submit}
			>
				{editing ? $i18n.t('Enregistrer') : $i18n.t('Créer')}
			</button>
		</div>
	</div>
</Modal>
