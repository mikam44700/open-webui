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
import crawl4aiLogo from '$lib/assets/connectors/crawl4ai.jpg';
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
import sentryLogo from '$lib/assets/connectors/sentry.png';
import vercelLogo from '$lib/assets/connectors/vercel.svg';
import neonLogo from '$lib/assets/connectors/neon.png';
import postgresLogo from '$lib/assets/connectors/postgres.png';
import redisLogo from '$lib/assets/connectors/redis.png';
import sqliteLogo from '$lib/assets/connectors/sqlite.png';
import supabaseLogo from '$lib/assets/connectors/supabase.jpg';
import baseLogo from '$lib/assets/connectors/base.png';
import ccxtLogo from '$lib/assets/connectors/ccxt.png';
import coingeckoLogo from '$lib/assets/connectors/coingecko.jpg';
import etherscanLogo from '$lib/assets/connectors/etherscan.svg';
import solanaLogo from '$lib/assets/connectors/solana-agent-kit.png';
import theGraphLogo from '$lib/assets/connectors/the-graph.png';
import thirdwebLogo from '$lib/assets/connectors/thirdweb.jpg';
import awsLogo from '$lib/assets/connectors/aws.png';
import fetchLogo from '$lib/assets/connectors/fetch.png';
import filesystemLogo from '$lib/assets/connectors/filesystem.png';
import memoryLogo from '$lib/assets/connectors/memory.jpg';
import mistralLogo from '$lib/assets/connectors/mistral.png';
import sequentialLogo from '$lib/assets/connectors/sequential-thinking.jpg';
import elevenlabsLogo from '$lib/assets/connectors/elevenlabs.png';
import dataGouvFrLogo from '$lib/assets/connectors/data-gouv-fr.svg';
import apifyLogo from '$lib/assets/connectors/apify.webp';

export const CONNECTOR_LOGO: Record<string, string> = {
	'data-gouv-fr': dataGouvFrLogo,
	apify: apifyLogo,
	linear: linearLogo,
	n8n: n8nLogo,
	'unreal-engine': unrealEngineLogo,
	hubspot: hubspotLogo,
	crawl4ai: crawl4aiLogo,
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
	puppeteer: puppeteerLogo,
	sentry: sentryLogo,
	vercel: vercelLogo,
	neon: neonLogo,
	postgres: postgresLogo,
	redis: redisLogo,
	sqlite: sqliteLogo,
	supabase: supabaseLogo,
	base: baseLogo,
	ccxt: ccxtLogo,
	coingecko: coingeckoLogo,
	etherscan: etherscanLogo,
	'solana-agent-kit': solanaLogo,
	'the-graph': theGraphLogo,
	thirdweb: thirdwebLogo,
	aws: awsLogo,
	fetch: fetchLogo,
	filesystem: filesystemLogo,
	memory: memoryLogo,
	mistral: mistralLogo,
	'sequential-thinking': sequentialLogo,
	elevenlabs: elevenlabsLogo
};

// Logos « carré plein » (fond intégré, dégradés compris) → affichés bord à bord pour
// remplir tout le carré. Les autres gardent le fond blanc + une marge.
export const CONNECTOR_LOGO_FULL_BLEED = new Set<string>([
	'data-gouv-fr',
	'crawl4ai',
	'linear',
	'n8n',
	'unreal-engine',
	'plaid',
	'stripe',
	'higgsfield',
	'alpaca',
	'meigen-ai-design',
	'polygon-io',
	'ableton',
	'redis',
	'supabase',
	'base',
	'ccxt',
	'coingecko',
	'thirdweb',
	'memory',
	'sequential-thinking',
	'elevenlabs',
	'fetch'
]);
