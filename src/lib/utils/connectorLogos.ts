// Logos des connecteurs MCP — source UNIQUE partagée par le Catalogue (CatalogCard)
// et Mes connecteurs (ConnectorCard), pour garantir le même visuel partout.
//
// Pour ajouter un connecteur : dépose son logo dans src/lib/assets/connectors/
// et mappe-le ici par son identifiant Hermes (le `name` du catalogue = l'`id` du connecteur).
// Sans entrée ici, la carte retombe sur l'icône générique (aucune erreur).

import linearLogo from '$lib/assets/connectors/linear.png';
import n8nLogo from '$lib/assets/connectors/n8n.svg';
import unrealEngineLogo from '$lib/assets/connectors/unreal-engine.png';
import hubspotLogo from '$lib/assets/connectors/hubspot.svg';
import atlassianLogo from '$lib/assets/connectors/atlassian.svg';
import plaidLogo from '$lib/assets/connectors/plaid.jpg';
import quickbooksLogo from '$lib/assets/connectors/quickbooks.svg';
import stripeLogo from '$lib/assets/connectors/stripe.png';
import canvaLogo from '$lib/assets/connectors/canva.jpg';
import figmaLogo from '$lib/assets/connectors/figma.svg';
import higgsfieldLogo from '$lib/assets/connectors/higgsfield.png';
import braveSearchLogo from '$lib/assets/connectors/brave-search.png';

export const CONNECTOR_LOGO: Record<string, string> = {
	linear: linearLogo,
	n8n: n8nLogo,
	'unreal-engine': unrealEngineLogo,
	hubspot: hubspotLogo,
	atlassian: atlassianLogo,
	plaid: plaidLogo,
	quickbooks: quickbooksLogo,
	stripe: stripeLogo,
	canva: canvaLogo,
	figma: figmaLogo,
	higgsfield: higgsfieldLogo,
	'brave-search': braveSearchLogo
};

// Logos « carré plein » (fond intégré, dégradés compris) → affichés bord à bord pour
// remplir tout le carré. Les autres gardent le fond blanc + une marge.
export const CONNECTOR_LOGO_FULL_BLEED = new Set<string>([
	'linear',
	'n8n',
	'unreal-engine',
	'plaid',
	'stripe',
	'higgsfield'
]);
