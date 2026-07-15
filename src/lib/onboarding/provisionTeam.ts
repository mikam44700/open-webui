// Provisionnement du socle à la première connexion (spec 019).
//
// POURQUOI (trou vérifié le 2026-07-15) : les 6 spécialistes du socle n'étaient créés NULLE PART —
// ni au déploiement, ni à l'onboarding. Ils n'existaient que si le dirigeant les adoptait un par un
// depuis « Mes agents ». Conséquences chez un client neuf :
//   - le roster de Mike est VIDE : il répond « je n'ai pas d'équipe » à sa première demande ;
//   - l'écran final de l'onboarding (`teamProof`) présente 6 agents lus dans le CATALOGUE, donc une
//     équipe qui n'existe pas — exactement ce que D27 interdit.
// Les 6 agents d'ici viennent d'une installation manuelle du 30/06 : on développait sur la seule
// machine correctement peuplée.
//
// POURQUOI À L'ONBOARDING, ET PAS AU DÉPLOIEMENT : le moteur crée un profil avec
// `create_profile(clone_config=True)` — le nouvel agent HÉRITE du modèle IA et des clés du profil
// actif au moment de sa naissance (cf. `profiles_adapter._CREATE_SCRIPT`). Au déploiement, aucune
// clé n'est encore saisie : les 6 naîtraient sans cerveau. On les crée donc APRÈS l'étape « Votre
// modèle IA », quand il y a un vrai cerveau à cloner.
//
// Logique PURE (dépendance `create` injectée) : testable sans réseau ni moteur.

import { AGENT_TEMPLATES, SOCLE_IDS, type AgentTemplate } from '$lib/components/agents/templates';

// Mike EST le profil `default` du moteur — il n'a pas de profil à lui. Le créer poserait un SECOND
// orchestrateur à côté du `default` : deux Mike, deux mémoires, et le chat parle à celui qu'on ne
// voit pas. Même piège que celui refermé le 15/07 avec `hermes-defaults/profile.yaml`.
export const MIKE_TEMPLATE_ID = 'mike-chef-orchestre';

/** Les 6 spécialistes du socle, dans l'ordre du catalogue. Mike exclu (il est le `default`). */
export const socleSpecialists = (): AgentTemplate[] =>
	AGENT_TEMPLATES.filter((t) => SOCLE_IDS.has(t.id) && t.id !== MIKE_TEMPLATE_ID);

export type CreateFn = (tpl: AgentTemplate) => Promise<void>;

export type ProvisionResult = {
	/** Agents réellement créés pendant cet appel. */
	created: string[];
	/** Agents déjà en place (rien à faire) — état sain, pas un échec. */
	alreadyThere: string[];
	/** Agents que le moteur a refusés : l'appelant doit être honnête là-dessus. */
	failed: string[];
};

// Le bridge renvoie `exists` quand le profil est déjà là. Ce n'est PAS un échec : deux onglets
// ouverts, ou un onboarding rejoué, mènent au même état sain.
const isAlreadyExists = (err: unknown): boolean =>
	(err as { error?: { code?: string } })?.error?.code === 'exists';

/**
 * Crée les spécialistes du socle qui manquent. Idempotent, et non bloquant par nature :
 * un agent qui échoue n'empêche pas les suivants, il est simplement rapporté dans `failed`.
 *
 * @param existingIds identifiants des agents déjà présents (source : `getAgents`)
 * @param create      crée un agent depuis son template (injecté : réseau isolé du calcul)
 */
export const provisionSocleTeam = async (
	existingIds: readonly string[],
	create: CreateFn
): Promise<ProvisionResult> => {
	const present = new Set(existingIds);
	const res: ProvisionResult = { created: [], alreadyThere: [], failed: [] };

	// SÉQUENTIEL, jamais en parallèle : chaque naissance clone le `config.yaml` du profil actif.
	// Six clonages simultanés lisent/écrivent le même fichier — on ne prend pas ce risque pour
	// gagner deux secondes sur une étape déjà masquée par le crawl.
	for (const tpl of socleSpecialists()) {
		if (present.has(tpl.id)) {
			res.alreadyThere.push(tpl.id);
			continue;
		}
		try {
			await create(tpl);
			res.created.push(tpl.id);
		} catch (err) {
			if (isAlreadyExists(err)) res.alreadyThere.push(tpl.id);
			else res.failed.push(tpl.id);
		}
	}
	return res;
};
