import { defineConfig, devices } from '@playwright/test';

// Smoke E2E contre le container LunarIA/OpenWebUI DÉJÀ EN COURS (docker compose up -d,
// http://localhost:3000). Ce config ne démarre AUCUN serveur (pas de webServer) : on ne fait
// que piloter un navigateur contre l'instance déjà lancée, jamais de rebuild déclenché ici.
export default defineConfig({
	testDir: './e2e',
	timeout: 30_000,
	expect: { timeout: 10_000 },
	fullyParallel: false,
	retries: 0,
	reporter: [['list']],
	use: {
		baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
		trace: 'retain-on-failure',
		screenshot: 'only-on-failure'
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	]
});
