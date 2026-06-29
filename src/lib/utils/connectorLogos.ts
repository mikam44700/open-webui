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
import canvaLogo from '$lib/assets/connectors/canva.png';
import figmaLogo from '$lib/assets/connectors/figma.svg';
import higgsfieldLogo from '$lib/assets/connectors/higgsfield.png';
import braveSearchLogo from '$lib/assets/connectors/brave-search.png';
import airtableLogo from '$lib/assets/connectors/airtable.svg';
import asanaLogo from '$lib/assets/connectors/asana.svg';
import gmailLogo from '$lib/assets/connectors/gmail.png';
import googleCalendarLogo from '$lib/assets/connectors/google-calendar.svg';
import googleDriveLogo from '$lib/assets/connectors/google-drive.svg';
import notionLogo from '$lib/assets/connectors/notion.svg';
import paypalLogo from '$lib/assets/connectors/paypal.svg';
import slackLogo from '$lib/assets/connectors/slack.svg';
import youtubeLogo from '$lib/assets/connectors/youtube.svg';
import alpacaLogo from '$lib/assets/connectors/alpaca.jpg';
import duneLogo from '$lib/assets/connectors/dune.png';
import polygonLogo from '$lib/assets/connectors/polygon-io.png';
import tradingviewLogo from '$lib/assets/connectors/tradingview.png';
import abletonLogo from '$lib/assets/connectors/ableton.png';
import blenderLogo from '$lib/assets/connectors/blender.png';
import davinciLogo from '$lib/assets/connectors/davinci-resolve.png';
import meigenLogo from '$lib/assets/connectors/meigen-ai-design.jpg';
import cloudflareLogo from '$lib/assets/connectors/cloudflare.png';
import context7Logo from '$lib/assets/connectors/context7.png';
import dockerHubLogo from '$lib/assets/connectors/docker-hub.png';
import gitLogo from '$lib/assets/connectors/git.png';
import githubLogo from '$lib/assets/connectors/github.svg';
import kubernetesLogo from '$lib/assets/connectors/kubernetes.png';
import playwrightLogo from '$lib/assets/connectors/playwright.svg';
import puppeteerLogo from '$lib/assets/connectors/puppeteer.png';

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
	'brave-search': braveSearchLogo,
	airtable: airtableLogo,
	asana: asanaLogo,
	gmail: gmailLogo,
	'google-calendar': googleCalendarLogo,
	'google-drive': googleDriveLogo,
	notion: notionLogo,
	paypal: paypalLogo,
	slack: slackLogo,
	youtube: youtubeLogo,
	alpaca: alpacaLogo,
	dune: duneLogo,
	'polygon-io': polygonLogo,
	tradingview: tradingviewLogo,
	ableton: abletonLogo,
	blender: blenderLogo,
	'davinci-resolve': davinciLogo,
	'meigen-ai-design': meigenLogo,
	cloudflare: cloudflareLogo,
	context7: context7Logo,
	'docker-hub': dockerHubLogo,
	git: gitLogo,
	github: githubLogo,
	kubernetes: kubernetesLogo,
	playwright: playwrightLogo,
	puppeteer: puppeteerLogo
};

// Logos « carré plein » (fond intégré, dégradés compris) → affichés bord à bord pour
// remplir tout le carré. Les autres gardent le fond blanc + une marge.
export const CONNECTOR_LOGO_FULL_BLEED = new Set<string>([
	'linear',
	'n8n',
	'unreal-engine',
	'plaid',
	'stripe',
	'higgsfield',
	'alpaca',
	'meigen-ai-design',
	'polygon-io',
	'ableton'
]);
