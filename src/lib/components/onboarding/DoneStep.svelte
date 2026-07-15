<script lang="ts">
	// Étape finale : la PREUVE TANGIBLE (design Gojiberry, temps 9). On n'atteint cet écran qu'après
	// validation du contexte (review → done) : le modèle est branché, le contexte entreprise est
	// réellement enregistré ET propagé au profil de chaque agent (USER.md write-through). On le prouve
	// en montrant l'ÉQUIPE RÉELLE qui connaît maintenant la boîte — pas une démo scriptée (D27).
	import { createEventDispatcher, getContext } from 'svelte';
	import { buildTeamProof } from '$lib/onboarding/teamProof';
	import { EMPTY_CONTEXT, type CompanyContext } from '$lib/onboarding/companySynthesis';
	import { faceFromImage, avatarId } from '$lib/components/agents/avatars';
	import { avatarColor } from '$lib/components/agents/avatar-colors';
	import { avatarImgFallback } from '$lib/utils/agentIdentity';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Contexte validé à l'étape précédente (personnalise la preuve de chaque agent). Peut être vide
	// si le dirigeant a sauté la saisie : le helper retombe alors sur des phrases de repli honnêtes.
	export let context: CompanyContext = { ...EMPTY_CONTEXT };

	// Agents RÉELLEMENT présents dans le moteur (lus après le provisionnement du socle). L'écran est
	// une preuve : il ne montre que ce qui existe. Avant le 2026-07-15 il lisait le catalogue et
	// affichait donc une équipe entière à un client qui n'avait aucun agent.
	export let teamIds: string[] = [];

	// Deux échecs non bloquants du parcours, auparavant avalés en simple console.error (audit
	// 2026-07-15) : agents du socle refusés par le moteur, et bases documentaires non synchronisées
	// vers le coffre. On ne bloque toujours rien (choix produit assumé) — mais le dirigeant le sait.
	export let agentsFailedCount: number = 0;
	export let docsSyncFailedCount: number = 0;

	$: team = buildTeamProof(context, teamIds);

	// Bandeau discret, honnête, non alarmiste. Le cas « agents » n'est affiché que si une ÉQUIPE est
	// par ailleurs montrée (team.length > 0) : équipe totalement absente est déjà couvert par le
	// discours principal ci-dessus (« Mike connaît déjà votre entreprise »), pas la peine d'insister.
	$: notices = [
		agentsFailedCount > 0 && team.length > 0
			? $i18n.t('Certains agents n’ont pas pu être créés. Retrouvez-les depuis « Mes agents ».')
			: null,
		docsSyncFailedCount > 0
			? $i18n.t(
					'{{n}} document(s) n’ont pas pu être synchronisés. Réessayez depuis « Mémoire ».',
					{ n: docsSyncFailedCount }
				)
			: null
	].filter((m): m is string => !!m);
</script>

<div class="w-full max-w-2xl mx-auto px-5 py-9 sm:py-10">
	<!-- Célébration -->
	<div class="text-center">
		<div
			class="mx-auto h-16 w-16 rounded-full flex items-center justify-center text-2xl text-amber-950 bg-gradient-to-br from-amber-400 to-amber-600 shadow-[0_0_44px_-6px_rgba(240,178,62,0.5)]"
		>
			✓
		</div>
		<div
			class="mt-5 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-600 dark:text-amber-300/90"
		>
			{team.length ? $i18n.t('Votre équipe est prête') : $i18n.t('Votre contexte est enregistré')}
		</div>
		<!-- Deux discours, parce que deux réalités. Si l'équipe n'a pas pu être mise en place (moteur
		     injoignable), on ne parle PAS d'équipe : le contexte, lui, est bien enregistré, et Mike
		     est là. Promettre une équipe absente serait le premier mensonge du produit (D27). -->
		<h1 class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
			{team.length
				? $i18n.t('Ils connaissent déjà votre entreprise')
				: $i18n.t('Mike connaît déjà votre entreprise')}
		</h1>
		<p class="mt-3 text-[15px] leading-relaxed text-gray-600 dark:text-gray-300 max-w-md mx-auto">
			{team.length
				? $i18n.t(
						'Mike a transmis votre contexte à toute l’équipe. Voici ce que chacun sait déjà — avant même votre première demande.'
					)
				: $i18n.t(
						'Votre contexte est en mémoire. Votre équipe de spécialistes n’a pas encore pu être mise en place — vous pourrez l’ajouter depuis « Mes agents ».'
					)}
		</p>
	</div>

	<!-- La preuve : l'équipe réelle + ce que chacun connaît de la boîte -->
	<div class="mt-7 grid gap-2.5 sm:grid-cols-2">
		{#each team as agent (agent.id)}
			{@const agentGradient = avatarColor(avatarId(agent.image) || agent.firstName).gradient}
			<div
				class="flex items-start gap-3 rounded-2xl bg-white dark:bg-white/[0.03] ring-1 ring-inset ring-black/5 dark:ring-white/10 px-4 py-3.5"
			>
				<!-- Visage détouré (transparent) : le fond du cercle = couleur signature de l'agent. -->
				<img
					src={faceFromImage(agent.image) ?? '/favicon.png'}
					alt={agent.firstName}
					on:error={(e) => avatarImgFallback(e, agent.image)}
					style="background: {agentGradient}"
					class="flex-none h-11 w-11 rounded-full object-cover ring-1 ring-inset ring-black/10 dark:ring-white/15"
				/>
				<div class="min-w-0">
					<div class="flex items-baseline gap-2">
						<span class="text-sm font-semibold text-gray-900 dark:text-white">{agent.firstName}</span>
						<span class="text-[12px] text-gray-400 dark:text-gray-500 truncate">{$i18n.t(agent.role)}</span>
					</div>
					<div class="mt-0.5 flex items-start gap-1.5 text-[13px] leading-snug text-gray-600 dark:text-gray-300">
						<span class="text-emerald-500 font-bold leading-none mt-[3px]">✓</span>
						<span>{$i18n.t(agent.proof)}</span>
					</div>
				</div>
			</div>
		{/each}
	</div>

	<!-- Bandeau discret : échecs non bloquants remontés (agents refusés / documents non synchronisés). -->
	{#if notices.length}
		<div
			class="mt-4 rounded-xl bg-amber-50 dark:bg-amber-900/15 ring-1 ring-inset ring-amber-500/20 px-4 py-3 text-[13px] leading-snug text-amber-800 dark:text-amber-200"
		>
			{#each notices as msg}
				<p>{msg}</p>
			{/each}
		</div>
	{/if}

	<!-- Aller plus loin (non bloquant) -->
	<div
		class="mt-5 rounded-2xl border border-dashed border-amber-500/30 px-5 py-4 text-left text-sm text-gray-600 dark:text-gray-300"
	>
		<span class="font-semibold text-gray-900 dark:text-white">{$i18n.t('Envie d’aller plus loin ?')}</span>
		{$i18n.t(
			'Connectez votre agenda et votre boîte mail pour que vos agents agissent à votre place. Maintenant ou plus tard.'
		)}
	</div>

	<div class="mt-7 flex flex-wrap items-center justify-center gap-3">
		<button
			class="text-sm font-semibold px-6 py-3 rounded-xl btn-premium bg-gradient-to-br from-amber-400 to-amber-600 text-amber-950"
			on:click={() => dispatch('done')}
		>
			{$i18n.t('Rencontrer mon équipe')} →
		</button>
		<button
			class="text-sm font-medium px-5 py-3 rounded-xl bg-white/70 dark:bg-white/10 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-900/10 dark:ring-white/15"
			on:click={() => dispatch('workspace')}
		>
			{$i18n.t('Connecter mon espace de travail')}
		</button>
	</div>
</div>
