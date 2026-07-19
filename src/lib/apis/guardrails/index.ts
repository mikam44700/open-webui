import { apiCall } from '$lib/apis/apiCall';

// Client API des Garde-fous (chantier Guardrails) : état des protections + file
// d'approbation des écritures mémoire. Router admin /api/v1/guardrails (bridge).
const call = (token: string, method: string, path: string, body?: unknown) =>
	apiCall(token, '/guardrails', method, path, body);

// État des protections : disjoncteur de boucle, approbation mémoire, compteur en attente.
export const getGuardrails = (token: string) => call(token, 'GET', '');

// Arme les protections (idempotent) et renvoie l'état à jour.
export const armGuardrails = (token: string) => call(token, 'POST', '/arm');

// Écritures mémoire en attente d'approbation.
export const getPendingMemory = (token: string) => call(token, 'GET', '/memory/pending');

// Approuve une écriture (id précis ou 'all') : elle est réellement appliquée à la mémoire.
export const approveMemory = (token: string, id: string) =>
	call(token, 'POST', '/memory/approve', { id });

// Rejette une écriture (id précis ou 'all') : retirée de la file, mémoire inchangée.
export const rejectMemory = (token: string, id: string) =>
	call(token, 'POST', '/memory/reject', { id });
