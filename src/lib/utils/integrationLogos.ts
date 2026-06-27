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
import obsidianLogo from '$lib/assets/integrations/obsidian-icon.webp';
import xLogo from '$lib/assets/integrations/x.svg';
import appleLogo from '$lib/assets/integrations/apple.svg';
import hueLogo from '$lib/assets/integrations/hue.svg';
// Placeholder Microsoft 365 — a remplacer par le logo officiel Microsoft 365
import microsoft365Logo from '$lib/assets/integrations/microsoft/microsoft365.svg';
// Placeholders OAuth 1 clic — a remplacer par les logos officiels de chaque service
import calendlyLogo from '$lib/assets/integrations/calendly/calendly.svg';
import boxLogo from '$lib/assets/integrations/box/box.svg';
import dropboxLogo from '$lib/assets/integrations/dropbox/dropbox.svg';
import salesforceLogo from '$lib/assets/integrations/salesforce/salesforce.svg';
import clickupLogo from '$lib/assets/integrations/clickup/clickup.svg';

export const INTEGRATION_LOGO: Record<string, string> = {
	'google-workspace': googleLogo,
	notion: notionLogo,
	github: githubLogo,
	airtable: airtableLogo,
	email: emailLogo,
	obsidian: obsidianLogo,
	x: xLogo,
	apple: appleLogo,
	hue: hueLogo,
	'microsoft-365': microsoft365Logo,
	calendly: calendlyLogo,
	box: boxLogo,
	dropbox: dropboxLogo,
	salesforce: salesforceLogo,
	clickup: clickupLogo
};

// Couleur du fond derrière le logo. Certains logos (ex. Obsidian, cristal violet) sont
// pensés pour un fond sombre — on respecte leur identité. Défaut : fond blanc.
export const INTEGRATION_LOGO_BG: Record<string, string> = {
	obsidian: 'bg-black'
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
