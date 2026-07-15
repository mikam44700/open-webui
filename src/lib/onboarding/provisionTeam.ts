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

// --- Verrou de provisionnement (audit HAUTE #1, 2026-07-15) ------------------------------------
//
// POURQUOI : `provisionSocleTeam` est séquentiel EN INTERNE, mais rien n'empêchait deux APPELS
// concurrents. Dans OnboardingFlow.svelte, le garde-fou « une seule fois » était une variable
// LOCALE au composant (`teamReady`) : si le dirigeant recharge la page pendant le crawl ou
// l'interview (plusieurs minutes, largement le temps qu'un provisioning tourne), l'instance
// Svelte est détruite mais la boucle asynchrone en vol n'est PAS annulée. La nouvelle instance
// repart avec `teamReady = null` et relance `provisionSocleTeam` → deux boucles concurrentes,
// chacune séquentielle en interne, qui clonent le même `config.yaml` en même temps — exactement
// le risque que la séquentialité interne voulait éviter.
//
// Une variable de composant ne peut PAS survivre à un reload ni être vue par un autre onglet.
// `localStorage` si : il est lu/écrit de façon synchrone, visible cross-onglet, et persiste au
// reload. On y pose un verrou horodaté AVANT de lancer le provisioning, et on le lève à la fin.
// Un TTL protège contre le cas où le provisioning plante sans jamais lever le verrou (onglet fermé
// en pleine création, exception non rattrapée) : sans lui, un client resterait bloqué pour
// toujours. `provisionSocleTeam` reste par ailleurs déjà idempotent côté bridge (code `exists`) —
// ce verrou ne duplique pas cette protection, il évite la CONCURRENCE que l'idempotence seule ne
// suffit pas à rendre sûre (deux `create_profile` simultanés sur le même agent peuvent tout de
// même se marcher dessus avant que le second ne découvre que le premier a fini).
//
// Interface minimale (pas tout `Storage`) : testable avec un simple objet en mémoire, sans jsdom.
export interface LockStorage {
	getItem(key: string): string | null;
	setItem(key: string, value: string): void;
	removeItem(key: string): void;
}

const PROVISION_LOCK_KEY = 'lunaria-onboarding-team-provision-lock';

// 5 minutes : un provisioning normal (6 créations séquentielles) se compte en secondes, une minute
// grand maximum sur un moteur lent — 5 min est une marge large. Assez court pour qu'un crash ne
// prive pas le dirigeant d'un nouvel essai (reload, nouvel onglet, prochaine connexion) plus de
// 5 minutes.
export const PROVISION_LOCK_TTL_MS = 5 * 60 * 1000;

/**
 * Pose le verrou si aucun n'est actif. Renvoie `true` si l'appelant peut lancer le provisioning,
 * `false` si un verrou récent existe déjà (un autre onglet, ou l'instance précédente avant reload,
 * est probablement en train de provisionner) — l'appelant ne doit alors PAS relancer
 * `provisionSocleTeam`.
 */
export const acquireProvisionLock = (storage: LockStorage, now: number = Date.now()): boolean => {
	const raw = storage.getItem(PROVISION_LOCK_KEY);
	if (raw !== null) {
		const ts = Number(raw);
		if (Number.isFinite(ts) && now - ts < PROVISION_LOCK_TTL_MS) {
			return false; // verrou actif et non expiré
		}
	}
	storage.setItem(PROVISION_LOCK_KEY, String(now));
	return true;
};

/**
 * Lève le verrou. Best-effort : si le provisioning plante après l'avoir posé, le TTL le libère de
 * toute façon — un `finally` doit appeler ceci, mais son absence n'est jamais bloquante.
 */
export const releaseProvisionLock = (storage: LockStorage): void => {
	storage.removeItem(PROVISION_LOCK_KEY);
};
