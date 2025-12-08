import { test, expect } from '@playwright/test';

test.describe('The Face: Landing Page', () => {
    test('should display the Research Interface', async ({ page }) => {
        // 1. Visit the landing page
        await page.goto('/');

        // 2. Check Page Title
        await expect(page).toHaveTitle(/Dhi/);

        // 3. Verify Polyglot Header (The Rosetta Stone)
        const header = page.locator('h1');
        await expect(header).toContainText('धी');
        await expect(header).toContainText('ధీ');
        await expect(header).toContainText('Dhī');

        // 4. Verify Search Input
        const input = page.getByPlaceholder('Query the Archive...');
        await expect(input).toBeVisible();
        await expect(input).toHaveClass(/font-mono/); // Should use Hurmit Nerd Font (Monospace)

        // 5. Interaction: Typing the Query
        await input.fill('Who is the translator?');
        await expect(input).toHaveValue('Who is the translator?');

        // 6. Verify Aesthetic (Dark Mode)
        // We can't easily check colors in unit tests without snapshotting, 
        // but we can check the body class or background style if set inline/class
        // Here we trust the visual regression or class names.
    });
});
