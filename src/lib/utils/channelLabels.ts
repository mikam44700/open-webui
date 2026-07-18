// Descriptions FR courtes + actions des canaux de messagerie (orientées client, sans jargon).
// Même principe que connectorLabels.ts / integrationLabels.ts : phrase grise courte (jamais
// coupée) + déroulant « Voir ce que ça fait ». Clé = identifiant du canal (`p.id`).

export type ChannelMeta = { desc: string; actions: string[] };

// Tags de capacités (pastilles courtes, style « subservices ») — 2 à 3 mots. Keyés par `p.id`.
export const CHANNEL_TAGS: Record<string, string[]> = {
	telegram: ['Messages', 'Réponses auto', 'Bot'],
	discord: ['Serveurs', 'Canaux', 'Bot'],
	slack: ['Canaux', 'Fils', 'App Slack'],
	whatsapp_cloud: ['Messages', 'Réponses auto', 'API Cloud'],
	signal: ['Messages', 'Réponses auto', 'signal-cli'],
	email: ['E-mails', 'Réponses auto', 'IMAP/SMTP'],
	sms: ['SMS', 'Réponses auto', 'Twilio'],
	bluebubbles: ['iMessage', 'Réponses auto', 'BlueBubbles']
};

export const CHANNEL_FR: Record<string, ChannelMeta> = {
	telegram: {
		desc: 'Vos agents répondent dans Telegram.',
		actions: [
			'Recevoir les messages Telegram',
			'Répondre automatiquement',
			'Brancher un bot Telegram'
		]
	},
	discord: {
		desc: 'Vos agents répondent dans vos serveurs.',
		actions: [
			'Recevoir les messages de vos serveurs',
			'Répondre dans les canaux',
			'Brancher un bot Discord'
		]
	},
	slack: {
		desc: 'Vos agents répondent dans vos canaux.',
		actions: [
			'Recevoir les messages Slack',
			'Répondre dans les canaux et les fils',
			'Brancher une app Slack'
		]
	},
	whatsapp_cloud: {
		desc: 'Vos agents répondent sur WhatsApp.',
		actions: [
			'Recevoir des messages WhatsApp',
			'Répondre automatiquement',
			'Via l’API WhatsApp Cloud (Meta)'
		]
	},
	signal: {
		desc: 'Vos agents répondent sur Signal.',
		actions: [
			'Recevoir des messages Signal',
			'Répondre automatiquement',
			'Via signal-cli (REST API)'
		]
	},
	email: {
		desc: 'Vos agents répondent par e-mail.',
		actions: [
			'Recevoir les e-mails entrants',
			'Répondre automatiquement',
			'Via une boîte IMAP/SMTP'
		]
	},
	sms: {
		desc: 'Vos agents répondent par SMS.',
		actions: ['Recevoir des SMS', 'Répondre par texto', 'Via Twilio']
	},
	bluebubbles: {
		desc: 'Vos agents répondent sur iMessage.',
		actions: [
			'Recevoir des iMessages',
			'Répondre automatiquement',
			'Via un serveur BlueBubbles'
		]
	}
};
