// Détecte si une erreur d'appel API signifie « le pont Hermes est injoignable » —
// mutualisé pour éviter que chaque composant redéfinisse la même fonction (DRY).
export const isBridgeDown = (err: any): boolean =>
	err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';
