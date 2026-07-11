import { describe, it, expect } from 'vitest';
import { composeAgentUserContent } from './generator';

// composeAgentUserContent est la partie synchrone/pure de la génération d'agent :
// elle assemble le message utilisateur envoyé au moteur. On teste surtout l'INJECTION
// du contexte entreprise (le fix « agent de la boîte »), sans jamais toucher au réseau.

describe('composeAgentUserContent — contexte entreprise', () => {
	it('injecte le contexte entreprise quand il est fourni', () => {
		const out = composeAgentUserContent('Relancer les impayés', '', {
			companyContext: 'Cabinet de conseil en organisation pour PME industrielles. Ton professionnel et rassurant.'
		});
		expect(out).toContain("Contexte de l'entreprise du dirigeant");
		expect(out).toContain('Cabinet de conseil en organisation');
	});

	it("n'ajoute aucun bloc contexte quand il est absent (dégradé gracieux)", () => {
		const out = composeAgentUserContent('Relancer les impayés', '', {});
		expect(out).not.toContain("Contexte de l'entreprise du dirigeant");
		// Le besoin reste bien présent : le comportement d'origine est préservé.
		expect(out).toContain('Relancer les impayés');
	});

	it('ignore un contexte entreprise vide ou fait uniquement d’espaces', () => {
		const out = composeAgentUserContent('Faire un devis', '', { companyContext: '   ' });
		expect(out).not.toContain("Contexte de l'entreprise du dirigeant");
	});

	it('place le contexte entreprise AVANT les outils connectés (cadre le reste)', () => {
		const out = composeAgentUserContent('Gérer les rendez-vous', '', {
			companyContext: 'Salon de coiffure de quartier.',
			connectedTools: ['Google Agenda', 'Gmail']
		});
		const idxContext = out.indexOf("Contexte de l'entreprise du dirigeant");
		const idxTools = out.indexOf('Outils réellement connectés');
		expect(idxContext).toBeGreaterThanOrEqual(0);
		expect(idxTools).toBeGreaterThan(idxContext);
	});
});

describe('composeAgentUserContent — comportement existant préservé', () => {
	it('mentionne nommément les outils connectés', () => {
		const out = composeAgentUserContent('Trier mes mails', '', {
			connectedTools: ['Gmail', 'Google Agenda']
		});
		expect(out).toContain('Outils réellement connectés');
		expect(out).toContain('Gmail, Google Agenda');
	});

	it('intègre le process guidé du dirigeant quand il est fourni', () => {
		const out = composeAgentUserContent('Suivre les devis', '', {
			guided: { walkthrough: 'On envoie le devis puis on relance à J+7', success: 'Devis signé' }
		});
		expect(out).toContain('SON process réel');
		expect(out).toContain('On envoie le devis puis on relance à J+7');
		expect(out).toContain('Devis signé');
	});

	it('inclut le bloc documents quand un sourcesBlock est fourni', () => {
		const out = composeAgentUserContent('Rédiger des contrats', '--- Document : CGV ---\nArticle 1...', {});
		expect(out).toContain('Documents fournis par le dirigeant');
		expect(out).toContain('Article 1...');
	});

	it('retombe sur un assistant généraliste si tout est vide', () => {
		const out = composeAgentUserContent('', '', {});
		expect(out).toContain('assistant généraliste utile pour une PME');
	});

	it('ajoute la consigne d’ajustement quand previous + adjustment sont fournis', () => {
		const previous = { label: 'X', emoji: '🤖', description: '', soul: 'Tu es X' };
		const out = composeAgentUserContent('', '', {
			previous,
			adjustment: 'Rends-le plus chaleureux'
		});
		expect(out).toContain("l'agent généré précédemment");
		expect(out).toContain('Rends-le plus chaleureux');
	});
});
