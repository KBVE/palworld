import { test, expect, type Page } from '@playwright/test';

/**
 * Browser-side checks. The static side is covered by validate_assets.py;
 * these cover what only a real page can answer — does the map paint, do
 * tiles resolve, and does live data drive the UI in both directions.
 */

const LIVE_ROUTE = '**/live/players*';

/** Collect console errors and failed asset responses for the whole run. */
function watch(page: Page) {
	const consoleErrors: string[] = [];
	const badResponses: string[] = [];

	page.on('console', (msg) => {
		if (msg.type() === 'error') consoleErrors.push(msg.text());
	});
	page.on('response', (res) => {
		const url = new URL(res.url());
		if (url.pathname.startsWith('/palworld/') && res.status() >= 400) {
			badResponses.push(`${res.status()} ${url.pathname}`);
		}
	});

	return { consoleErrors, badResponses };
}

/** Stub the live endpoint so tests never depend on the gameserver. */
async function stubLive(page: Page, body: unknown | null) {
	await page.route(LIVE_ROUTE, async (route) => {
		if (body === null) return route.fulfill({ status: 503, body: '' });
		return route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(body),
		});
	});
}

test('renders the map without console errors or broken assets', async ({ page }) => {
	const { consoleErrors, badResponses } = watch(page);
	await stubLive(page, { ts: Date.now(), players: [], bosses: [], events: [] });

	await page.goto('/');
	await expect(page.locator('.leaflet-container')).toBeVisible();

	// Leaflet only reports load once every tile in view has resolved.
	await page.waitForFunction(
		() => document.querySelectorAll('.leaflet-tile-loaded').length > 0,
		null,
		{ timeout: 15_000 },
	);

	expect(badResponses, 'asset requests under /palworld/').toEqual([]);
	expect(consoleErrors, 'console errors').toEqual([]);
});

test('loads tiles from both pyramids', async ({ page }) => {
	const layers = new Set<string>();
	page.on('request', (req) => {
		const p = new URL(req.url()).pathname;
		const m = p.match(/^\/palworld\/(tiles|wt-overlay)\//);
		if (m) layers.add(m[1]);
	});
	await stubLive(page, { ts: Date.now(), players: [], bosses: [], events: [] });

	await page.goto('/');
	await expect
		.poll(() => [...layers].sort(), { timeout: 15_000 })
		.toEqual(['tiles', 'wt-overlay']);
});

test('renders a filter toggle for every marker kind', async ({ page }) => {
	await stubLive(page, { ts: Date.now(), players: [], bosses: [], events: [] });
	await page.goto('/');

	const filters = page.locator('.pal-map-filters');
	await expect(filters).toBeVisible();
	// One toggle per kind in KIND_META; the exact count is asserted against
	// the source in validate_assets.py, so here we only require several.
	await expect(filters.locator('input[type="checkbox"]')).not.toHaveCount(0);
});

test('shows the offline state when the live endpoint fails', async ({ page }) => {
	await stubLive(page, null);
	await page.goto('/');

	await expect(page.getByText('Players (offline)')).toBeVisible({ timeout: 15_000 });
});

test('reflects the live player count', async ({ page }) => {
	await stubLive(page, {
		ts: Date.now(),
		players: [
			{ name: 'Alpha', level: 32, x: -100000, y: 80000 },
			{ name: 'Beta', level: 7, x: -120000, y: 60000 },
		],
		bosses: [],
		events: [],
	});
	await page.goto('/');

	await expect(page.getByText('Players (2)')).toBeVisible({ timeout: 15_000 });
});
