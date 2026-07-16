import { test, expect } from '@playwright/test';

/**
 * Smoke E2E — porte d'entrée de l'onboarding LunarIA (spec 019).
 *
 * Portée volontairement réduite : ce test ne rejoue PAS le parcours complet
 * (crawl du site, synthèse de fiche entreprise, mini-interview, preuve d'équipe) —
 * ces étapes appellent des services externes/lents et exigent une session admin
 * authentifiée. Sans identifiants de test dédiés, on ne peut pas se connecter sans
 * risquer de créer un compte ou de manipuler le compte admin réel.
 *
 * Ce test prouve seulement que la pile répond et que la PREMIÈRE porte du parcours
 * (l'écran de connexion, qui précède l'onboarding déclenché après le 1er login)
 * s'affiche correctement : marque LunarIA visible, formulaire de connexion avec les
 * champs email/mot de passe, bouton de connexion.
 *
 * Pour couvrir le parcours complet, voir e2e/README.md.
 */
test.describe('Porte d\'entrée onboarding (login)', () => {
	test('la page se charge et affiche l\'écran de connexion LunarIA', async ({ page }) => {
		const response = await page.goto('/');
		expect(response?.ok()).toBeTruthy();

		// La marque LunarIA est rendue côté serveur (balise <title>), preuve que le
		// bon build/branding tourne (pas un OpenWebUI générique non rebrandé).
		await expect(page).toHaveTitle(/LunarIA/);

		// Écran de connexion : champs email + mot de passe présents (id stables dans
		// src/routes/auth/+page.svelte), et un bouton de soumission visible.
		const emailInput = page.locator('#email');
		const passwordInput = page.locator('#password');

		await expect(emailInput).toBeVisible();
		await expect(passwordInput).toBeVisible();

		const submitButton = page.getByRole('button', { name: /sign in|se connecter|connexion/i });
		await expect(submitButton.first()).toBeVisible();
	});

	test('aucune erreur console bloquante au chargement de la page de connexion', async ({
		page
	}) => {
		const pageErrors: string[] = [];
		page.on('pageerror', (err) => pageErrors.push(err.message));

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		expect(pageErrors).toEqual([]);
	});
});
