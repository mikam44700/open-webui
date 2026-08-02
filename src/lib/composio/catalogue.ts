/**
 * Les applications recommandees du catalogue Composio, rangees par usage.
 *
 * Composio en expose plus de mille, presque toutes des micro-services d'API —
 * verification d'adresses IP, capture d'ecran, conversion de PDF, validation
 * d'e-mails. Melangees aux vraies applications metier, elles les rendent
 * introuvables.
 *
 * Ce tri a ete fait avec Mike le 2 aout 2026 sur les 1069 identifiants reels
 * du catalogue, verifies un par un. L'ordre alphabetique mettait ActiveCampaign
 * a cote d'Agentql et d'Ahrefs : ces familles-la rendent la fenetre lisible.
 *
 * Rien n'est masque : ce qui n'est pas ici reste accessible derriere
 * « + d'integrations », un clic plus loin, et par la recherche.
 */

export type FamilleCatalogue = {
	id: string;
	libelle: string;
	applications: string[];
};

export const FAMILLES: FamilleCatalogue[] = [
	{
		id: 'messagerie',
		libelle: 'Messagerie & discussion',
		applications: [
			'gmail',
			'outlook',
			'slack',
			'microsoft_teams',
			'google_chat',
			'discord',
			'telegram',
			'whatsapp',
			'chatwork',
			'missive',
			'zulip',
			'respond_io',
			'wati'
		]
	},
	{
		id: 'reunions',
		libelle: 'Réunions',
		applications: [
			'zoom',
			'googlemeet',
			'webex',
			'clickmeeting',
			'demio',
			'fireflies',
			'tldv',
			'recallai',
			'granola_mcp'
		]
	},
	{
		id: 'agenda',
		libelle: 'Agenda & rendez-vous',
		applications: [
			'googlecalendar',
			'calendly',
			'cal',
			'scheduleonce',
			'supersaas',
			'appointo',
			'etermin',
			'calendarhero',
			'motion',
			'ticktick',
			'todoist',
			'microsoft_todo'
		]
	},
	{
		id: 'fichiers',
		libelle: 'Fichiers & documents',
		applications: [
			'googledrive',
			'one_drive',
			'dropbox',
			'box',
			'egnyte',
			'share_point',
			'sharepoint_graph',
			'googledocs',
			'googlesheets',
			'googleslides',
			'onenote',
			'notion',
			'coda',
			'excel',
			'googlephotos'
		]
	},
	{
		id: 'crm',
		libelle: 'CRM & ventes',
		applications: [
			'hubspot',
			'salesforce',
			'salesforce_service_cloud',
			'pipedrive',
			'attio',
			'close',
			'folk',
			'capsule_crm',
			'nutshell',
			'zoho',
			'zoho_bigin',
			'kommo',
			'espocrm',
			'salesflare',
			'salesmate',
			'nethunt_crm',
			'highlevel',
			'follow_up_boss',
			'forcemanager',
			'firmao',
			'dynamics365',
			'netsuite',
			'odoo',
			'apollo',
			'lusha',
			'zoominfo',
			'gong',
			'rocket_reach',
			'hunter'
		]
	},
	{
		id: 'projets',
		libelle: 'Projets & tâches',
		applications: [
			'asana',
			'trello',
			'monday',
			'clickup',
			'jira',
			'confluence',
			'basecamp',
			'wrike',
			'shortcut',
			'linear',
			'teamcamp',
			'kanbanize',
			'productboard',
			'miro',
			'mural',
			'airtable',
			'baserow',
			'nocodb',
			'grist',
			'ninox',
			'fibery'
		]
	},
	{
		id: 'support',
		libelle: 'Support client',
		applications: [
			'zendesk',
			'intercom',
			'freshdesk',
			'freshservice',
			'help_scout',
			'helpdesk',
			'gorgias',
			're_amaze',
			'supportbee',
			'plain',
			'canny',
			'gleap',
			'servicenow'
		]
	},
	{
		id: 'compta',
		libelle: 'Compta & paiement',
		applications: [
			'stripe',
			'paypal',
			'quickbooks',
			'xero',
			'freshbooks',
			'freeagent',
			'moneybird',
			'sevdesk',
			'lexoffice',
			'elorus',
			'quaderno',
			'square',
			'razorpay',
			'paystack',
			'flutterwave',
			'lemon_squeezy',
			'gumroad',
			'brex',
			'ramp',
			'ynab',
			'taxjar',
			'zoho_books',
			'zoho_invoice',
			'zoho_inventory'
		]
	},
	{
		id: 'marketing',
		libelle: 'Marketing & e-mailing',
		applications: [
			'mailchimp',
			'brevo',
			'sendgrid',
			'mailerlite',
			'mailersend',
			'klaviyo',
			'active_campaign',
			'constant_contact',
			'omnisend',
			'moosend',
			'sender',
			'emailoctopus',
			'loops_so',
			'customerio',
			'iterable',
			'postmark',
			'resend',
			'mailtrap',
			'kit',
			'instantly',
			'lemlist',
			'reply_io',
			'woodpecker_co',
			'ayrshare',
			'postiz_mcp',
			'typefully',
			'planly',
			'metaads',
			'linkedin_ads',
			'googleads'
		]
	},
	{
		id: 'reseaux',
		libelle: 'Réseaux sociaux',
		applications: [
			'linkedin',
			'facebook',
			'twitter',
			'instagram',
			'tiktok',
			'youtube',
			'reddit',
			'snapchat'
		]
	},
	{
		id: 'rh',
		libelle: 'RH & temps',
		applications: [
			'bamboohr',
			'gusto',
			'workday',
			'sap_successfactors',
			'greenhouse',
			'lever',
			'ashby',
			'recruitee',
			'workable',
			'breezy_hr',
			'breathehr',
			'talenthr',
			'connecteam',
			'timecamp',
			'clockify',
			'toggl',
			'harvest',
			'everhour',
			'timely'
		]
	},
	{
		id: 'signature',
		libelle: 'Signature & devis',
		applications: [
			'docusign',
			'dropbox_sign',
			'pandadoc',
			'documenso',
			'docuseal',
			'signwell',
			'signaturely',
			'eversign',
			'esignatures_io',
			'boldsign',
			'better_proposals'
		]
	},
	{
		id: 'vente',
		libelle: 'Vente en ligne & livraison',
		applications: [
			'shopify',
			'wix',
			'webflow',
			'loyverse',
			'baselinker',
			'cloudcart',
			'shippo',
			'shipengine',
			'shipday',
			'detrack',
			'route4me',
			'optimoroute',
			'payhip',
			'whop'
		]
	},
	{
		id: 'formulaires',
		libelle: 'Formulaires & enquêtes',
		applications: [
			'typeform',
			'jotform',
			'tally',
			'fillout_forms',
			'formbricks',
			'getform',
			'formsite',
			'paperform',
			'survey_monkey',
			'googleforms',
			'delighted',
			'satismeter',
			'refiner',
			'simplesat',
			'retently'
		]
	},
	{
		id: 'analyse',
		libelle: 'Analyse & données',
		applications: [
			'google_analytics',
			'microsoft_power_bi',
			'metabase',
			'mixpanel',
			'amplitude',
			'posthog',
			'plausible_analytics',
			'simple_analytics',
			'databox',
			'klipfolio',
			'google_search_console',
			'semrush',
			'ahrefs',
			'moz'
		]
	},
	{
		id: 'automatisation',
		libelle: 'Automatisation',
		applications: ['make', 'bubble', 'softr', 'nango', 'celigo']
	},
	{
		id: 'recherche-web',
		libelle: 'Recherche & extraction web',
		applications: [
			'exa',
			'tavily',
			'firecrawl',
			'perplexityai',
			'linkup',
			'openperplex',
			'serpapi',
			'brightdata',
			'apify',
			'browseai',
			'browserbase_tool',
			'hyperbrowser',
			'scrapegraph_ai',
			'diffbot',
			'agentql',
			'kadoa',
			'news_api',
			'composio_search'
		]
	},
	{
		id: 'memoire',
		libelle: 'Mémoire & bases vectorielles',
		applications: ['mem0', 'zep', 'pinecone', 'ragie', 'needle']
	},
	{
		id: 'sandbox',
		libelle: 'Bac à sable de code',
		applications: ['e2b', 'daytona']
	},
	{
		id: 'developpement',
		libelle: 'Développement & design',
		applications: [
			'github',
			'gitlab',
			'bitbucket',
			'gitea',
			'sentry',
			'datadog',
			'new_relic',
			'grafana',
			'pagerduty',
			'incident_io',
			'rootly',
			'circleci',
			'buildkite',
			'vercel',
			'render',
			'railway',
			'fly',
			'digital_ocean',
			'cloudflare',
			'supabase',
			'neon',
			'snowflake',
			'databricks',
			'elasticsearch',
			'postman',
			'figma',
			'penpot',
			'zeplin',
			'sourcegraph',
			'npm',
			'docker_hub'
		]
	},
	{
		id: 'ia',
		libelle: 'Modèles IA',
		applications: [
			'openai',
			'gemini',
			'mistral_ai',
			'deepseek',
			'hugging_face',
			'elevenlabs',
			'replicate',
			'openrouter',
			'ollama',
			'wolfram_alpha_api'
		]
	}
];

/** Toutes les recommandees, a plat — pour trancher vite. */
export const RECOMMANDEES = new Set<string>(FAMILLES.flatMap((f) => f.applications));

/** Une application du catalogue merite-t-elle d'etre proposee d'emblee ? */
export const estRecommandee = (slug: string): boolean => RECOMMANDEES.has(`${slug}`.toLowerCase());
