// Modèles d'automatisation « pour commencer » (feature 013 — refonte accueil).
// Tous basés sur un PLANNING (cron natif Hermes) — pas de déclencheur événementiel.
// Les instructions s'appuient sur les capacités réelles de Hermes (mails, agenda,
// tâches Kanban, briefing, coffre Obsidian) ; elles restent des suggestions à
// adapter par le dirigeant. Honnêteté : aucune ne prétend qu'une intégration est
// connectée — si elle ne l'est pas, l'agent le dira au moment de l'exécution.

import type { RhythmForm } from './labels';

import gmailLogo from '$lib/assets/integrations/google/gmail.png';
import calendarLogo from '$lib/assets/integrations/google/calendar.png';
import obsidianLogo from '$lib/assets/integrations/obsidian.svg';

// Pastille de brique : un vrai logo (apps externes) ou un emoji (briques internes
// Agent OS comme le Kanban, qui n'ont pas de logo tiers). Honnêteté : on n'affiche
// que les briques réellement sollicitées par le modèle.
export type AppBadge = { src?: string; emoji?: string; alt: string };

export type AutomationTemplate = {
	id: string;
	emoji: string;
	title: string;
	summary: string; // 1 ligne affichée sur la carte
	apps: AppBadge[]; // logos/emoji des briques utilisées
	name: string; // pré-remplit le champ « Nom »
	instruction: string; // pré-remplit le champ « Que doit faire Agent OS ? »
	rhythm: RhythmForm; // pré-remplit le bloc rythme
};

const GMAIL: AppBadge = { src: gmailLogo, alt: 'Gmail' };
const AGENDA: AppBadge = { src: calendarLogo, alt: 'Google Agenda' };
const OBSIDIAN: AppBadge = { src: obsidianLogo, alt: 'Obsidian' };
const KANBAN: AppBadge = { emoji: '✅', alt: 'Tâches' };

export const automationTemplates: AutomationTemplate[] = [
	{
		id: 'brief-matinal',
		emoji: '📊',
		title: 'Briefing du matin',
		summary: 'Chaque matin : agenda, tâches du jour et emails importants en un récap',
		apps: [AGENDA, KANBAN, GMAIL],
		name: 'Briefing du matin',
		instruction:
			'Chaque matin, assemble mon briefing du jour : mes rendez-vous du jour (Google Agenda), mes tâches en cours (Kanban) et un résumé de mes emails importants reçus depuis hier. Réponds en français, concis, en sections claires.',
		rhythm: { rhythmType: 'daily', time: '08:00' }
	},
	{
		id: 'resume-mails',
		emoji: '📧',
		title: 'Résumé des emails',
		summary: 'Chaque matin : un résumé clair de tes emails importants',
		apps: [GMAIL],
		name: 'Résumé quotidien des mails',
		instruction:
			'Résume mes emails importants reçus depuis hier. Priorise : expéditeur, sujet, urgence, actions attendues, deadlines. Sortie en français, concise : résumé global en 2-4 lignes, mails importants, actions à faire. Si rien de notable, dis-le simplement.',
		rhythm: { rhythmType: 'daily', time: '09:00' }
	},
	{
		id: 'agenda-demain',
		emoji: '📅',
		title: 'Agenda de demain',
		summary: 'Chaque soir : la liste de tes rendez-vous du lendemain',
		apps: [AGENDA],
		name: 'Agenda de demain',
		instruction:
			'Chaque soir, liste mes rendez-vous de demain depuis Google Agenda : heure, titre, lieu/lien. Termine par un rappel des éventuelles préparations à prévoir. En français, concis.',
		rhythm: { rhythmType: 'daily', time: '18:00' }
	},
	{
		id: 'taches-jour',
		emoji: '✅',
		title: 'Mes tâches du jour',
		summary: 'Chaque matin : tes tâches en cours pour rester focalisé',
		apps: [KANBAN],
		name: 'Mes tâches du jour',
		instruction:
			'Chaque matin, liste mes tâches en cours et à faire depuis le Kanban. Mets en avant les priorités et les échéances proches. En français, court et actionnable.',
		rhythm: { rhythmType: 'daily', time: '09:00' }
	},
	{
		id: 'bilan-hebdo',
		emoji: '🧠',
		title: 'Bilan de la semaine',
		summary: 'Chaque vendredi : le bilan de ta semaine dans ton second cerveau',
		apps: [OBSIDIAN],
		name: 'Bilan de la semaine',
		instruction:
			'Chaque vendredi en fin de journée, fais le bilan de ma semaine : ce qui a avancé (tâches terminées), ce qui reste, et 3 priorités pour la semaine prochaine. Propose de l’enregistrer dans mon coffre Obsidian. En français.',
		rhythm: { rhythmType: 'weekly', weekday: 4, time: '17:00' }
	}
];
