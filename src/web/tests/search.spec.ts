import { test, expect } from '@playwright/test';

test.describe('The Connection: Search Flow', () => {
    test('should fetch insight from Agni (Backend) and display it', async ({ page }) => {
        // 1. Visit
        await page.goto('/');

        // 2. Type Query
        const input = page.getByPlaceholder('Query the Archive...');
        await input.fill('Who is Agni?');

        // 3. Trigger Search
        // We can hit Enter or Click Button. Let's hit Enter.
        await input.press('Enter');

        // 4. Expect Loading State (Optional, might be too fast)
        // await expect(page.locator('.animate-pulse')).toBeVisible();

        // 5. Expect Result
        // The "The Model" signature text appears only when result is ready
        const signature = page.getByText('— The Model');
        await expect(signature).toBeVisible({ timeout: 30000 }); // Give Llama 30s to think

        // 6. Verify Content
        // Result should contain "Agni" or "Fire" or "Priest" (based on our context/model)
        const resultText = page.locator('.prose');
        await expect(resultText).toContainText(/Agni|Fire|Priest/i);

        // 7. Verify Metadata
        const memStat = page.locator('text=TOKENS');
        await expect(memStat).toBeVisible();
    });
});
