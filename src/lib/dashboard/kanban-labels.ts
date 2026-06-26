/**
 * Traduction des statuts techniques Kanban en libellés dirigeant (features 007/009).
 * Module pur, testable. Source de vérité des statuts = le moteur (Kanban) ; on ne fait que mapper
 * vers un vocabulaire lisible.
 */

export const KANBAN_STATUS_LABELS: Record<string, string> = {
	triage: 'À clarifier',
	todo: 'À faire',
	ready: 'Prêt',
	running: 'En cours',
	scheduled: 'Planifié',
	blocked: 'Bloqué',
	review: 'À valider',
	done: 'Terminé'
};

/** Libellé dirigeant d'un statut, repli sur le statut brut si inconnu. */
export const labelForStatus = (status: string): string => KANBAN_STATUS_LABELS[status] ?? status;

/** Une tâche « bloquée » au sens dirigeant = bloquée ou en attente de validation. */
export const isBlockedStatus = (status: string): boolean => status === 'blocked' || status === 'review';
