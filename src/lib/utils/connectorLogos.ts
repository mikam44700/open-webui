// Logos des connecteurs MCP — source UNIQUE partagée par le Catalogue (CatalogCard)
// et Mes connecteurs (ConnectorCard), pour garantir le même visuel partout.
//
// Pour ajouter un connecteur : dépose son logo dans src/lib/assets/connectors/
// et mappe-le ici par son identifiant Hermes (le `name` du catalogue = l'`id` du connecteur).
// Sans entrée ici, la carte retombe sur l'icône générique (aucune erreur).

import linearLogo from '$lib/assets/connectors/linear.png';
import n8nLogo from '$lib/assets/connectors/n8n.svg';
import unrealEngineLogo from '$lib/assets/connectors/unreal-engine.png';

export const CONNECTOR_LOGO: Record<string, string> = {
	linear: linearLogo,
	n8n: n8nLogo,
	'unreal-engine': unrealEngineLogo
};

// Logos « carré plein » (fond intégré, dégradés compris) → affichés bord à bord pour
// remplir tout le carré. Les autres gardent le fond blanc + une marge.
export const CONNECTOR_LOGO_FULL_BLEED = new Set<string>(['linear', 'n8n', 'unreal-engine']);
