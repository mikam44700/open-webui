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
// Logo principal Microsoft 365
import microsoft365Logo from '$lib/assets/integrations/microsoft/microsoft365-main.jpg';
// Logos officiels OAuth 1 clic (Salesforce = SVG vectoriel ; les autres = PNG/JPEG haute def).
import calendlyLogo from '$lib/assets/integrations/calendly/calendly-logo.png';
import boxLogo from '$lib/assets/integrations/box/box-logo.png';
import dropboxLogo from '$lib/assets/integrations/dropbox/dropbox-logo.png';
import salesforceLogo from '$lib/assets/integrations/salesforce/salesforce-logo.svg';
import clickupLogo from '$lib/assets/integrations/clickup/clickup-logo.jpg';

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

// Logos « carré plein » (fond couleur intégré, ex. Box bleu) → affichés bord-à-bord pour
// remplir toute la case, sans marge ni fond blanc. Les autres gardent fond + padding.
export const INTEGRATION_LOGO_FULL_BLEED = new Set<string>(['box']);

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

// Espace Microsoft 365 : chaque service avec son propre logo (cle = nom du sous-service renvoyé par le serveur).
import ms365Outlook from '$lib/assets/integrations/microsoft/outlook.png';
import ms365Calendar from '$lib/assets/integrations/microsoft/calendar.png';
import ms365OneDrive from '$lib/assets/integrations/microsoft/onedrive.png';
import ms365Word from '$lib/assets/integrations/microsoft/word.png';
import ms365Excel from '$lib/assets/integrations/microsoft/excel.svg';
import ms365PowerPoint from '$lib/assets/integrations/microsoft/powerpoint.png';
import ms365Teams from '$lib/assets/integrations/microsoft/teams.png';
import ms365OneNote from '$lib/assets/integrations/microsoft/onenote.png';
import ms365Todo from '$lib/assets/integrations/microsoft/todo.png';
import ms365Contacts from '$lib/assets/integrations/microsoft/contacts.png';

export const MICROSOFT_SERVICE_LOGO: Record<string, string> = {
	Outlook: ms365Outlook,
	Agenda: ms365Calendar,
	OneDrive: ms365OneDrive,
	Word: ms365Word,
	Excel: ms365Excel,
	PowerPoint: ms365PowerPoint,
	Teams: ms365Teams,
	OneNote: ms365OneNote,
	'To Do': ms365Todo,
	Contacts: ms365Contacts
};
