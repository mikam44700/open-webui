// Logos des intégrations — source UNIQUE partagée par l'onglet Intégrations
// (IntegrationsList / IntegrationCard). Même principe que connectorLogos.ts.
//
// `INTEGRATION_LOGO` : logo principal par intégration.
// `GOOGLE_SERVICE_LOGO` : logo de chaque service Google (espace Google Workspace).

import googleLogo from '$lib/assets/integrations/google/workspace.png';
import notionLogo from '$lib/assets/integrations/notion-new.png';
import githubLogo from '$lib/assets/integrations/github-new.svg';
import airtableLogo from '$lib/assets/integrations/airtable-new.png';
import emailLogo from '$lib/assets/integrations/email-new.png';
import obsidianLogo from '$lib/assets/integrations/obsidian-new.webp';
import xLogo from '$lib/assets/integrations/x.svg';
import appleLogo from '$lib/assets/integrations/apple.svg';
import hueLogo from '$lib/assets/integrations/hue.svg';

export const INTEGRATION_LOGO: Record<string, string> = {
	'google-workspace': googleLogo,
	notion: notionLogo,
	github: githubLogo,
	airtable: airtableLogo,
	email: emailLogo,
	obsidian: obsidianLogo,
	x: xLogo,
	apple: appleLogo,
	hue: hueLogo
};

// Espace Google Workspace : chaque service avec son propre logo (clé = nom du sous-service FR).
import gwsGmail from '$lib/assets/integrations/google/gmail.png';
import gwsDrive from '$lib/assets/integrations/google/drive.png';
import gwsSheets from '$lib/assets/integrations/google/sheets.png';
import gwsCalendar from '$lib/assets/integrations/google/calendar.png';
import gwsDocs from '$lib/assets/integrations/google/docs.png';
import gwsContacts from '$lib/assets/integrations/google/contacts.png';

export const GOOGLE_SERVICE_LOGO: Record<string, string> = {
	Gmail: gwsGmail,
	Drive: gwsDrive,
	Sheets: gwsSheets,
	Agenda: gwsCalendar,
	Docs: gwsDocs,
	Contacts: gwsContacts
};
