/**
 * Dérivation des alertes du tableau de bord (feature 007, US1).
 *
 * Fonction PURE (aucune I/O) : prend les états déjà chargés et renvoie la liste des alertes à
 * afficher. Isolée ici pour être testable unitairement (la partie logique la plus à risque).
 *
 * Honnêteté (D27) : un état `unknown` (source non joignable / champ absent) ne génère PAS d'alerte
 * « en panne » trompeuse — seul un état réellement `down` déclenche l'alerte correspondante.
 */

export type DisplayStatus = 'ok' | 'down' | 'unknown';

export type AlertSeverity = 'critical' | 'warning' | 'info';

export type Alert = {
	severity: AlertSeverity;
	message: string;
	/** Lien vers la page de résolution. */
	href: string;
};

export type DashboardStates = {
	/** Pont (bridge) globalement joignable. `down` = aucune source n'a pu être interrogée. */
	bridge: DisplayStatus;
	/** Moteur (Hermes) joignable et fonctionnel. */
	engine: DisplayStatus;
	/** Messagerie (gateway) démarrée. */
	messaging: DisplayStatus;
	/** Mémoire (coffre) accessible. */
	memory: DisplayStatus;
	/** Un cerveau (modèle IA) est-il actif ? `unknown` si non déterminé. */
	activeBrain: boolean | 'unknown';
	/** Nombre de tâches bloquées / en attente de validation. `unknown` si non déterminé. */
	blockedTasks: number | 'unknown';
};

/**
 * Dérive la liste des alertes à partir des états du tableau de bord.
 * Liste vide => « Tout est opérationnel » (géré côté affichage).
 */
export const deriveAlerts = (s: DashboardStates): Alert[] => {
	// Pont totalement injoignable : une seule alerte chapeau, on n'empile pas les « indisponible ».
	if (s.bridge === 'down') {
		return [
			{
				severity: 'critical',
				message: 'Connexion au système indisponible',
				href: '/providers'
			}
		];
	}

	const alerts: Alert[] = [];

	if (s.engine === 'down') {
		alerts.push({ severity: 'critical', message: 'Moteur injoignable', href: '/providers' });
	}

	if (s.activeBrain === false) {
		alerts.push({ severity: 'warning', message: 'Aucun modèle IA actif', href: '/providers' });
	}

	if (s.messaging === 'down') {
		alerts.push({ severity: 'warning', message: 'Messagerie arrêtée', href: '/gateway' });
	}

	if (s.memory === 'down') {
		alerts.push({ severity: 'warning', message: 'Mémoire inaccessible', href: '/memory' });
	}

	if (typeof s.blockedTasks === 'number' && s.blockedTasks > 0) {
		const n = s.blockedTasks;
		alerts.push({
			severity: 'info',
			message: n === 1 ? '1 tâche à valider' : `${n} tâches à valider`,
			href: '/kanban'
		});
	}

	return alerts;
};
