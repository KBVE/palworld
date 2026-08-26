import { test, expect, type Page } from '@playwright/test';

/**
 * Browser-side checks. The static side is covered by validate_assets.py;
 * these cover what only a real page can answer — does the map paint, do
 * tiles resolve, and does live data drive the UI.
 *
 * Both live endpoints are always stubbed. Player and base counts change
 * while the suite runs, so asserting against the real gameserver is
 * either flaky or too loose to mean anything. Stubs also let us reach the
 * states that matter and cannot be summoned on demand: no bases at all, a
 * populated guild, and the endpoint being down.
 */

const PLAYERS_ROUTE = '**/live/players*';
const BASES_ROUTE = '**/live/bases*';

type Snapshot = {
	ts?: number;
	players?: unknown[];
	bosses?: unknown[];
	events?: unknown[];
};

/** Stub both live endpoints. Pass null to make one fail. */
async function stubLive(
	page: Page,
	opts: { players?: Snapshot | null; guilds?: unknown[] | null } = {},
) {
	const { players = { players: [], bosses: [], events: [] }, guilds = [] } = opts;

	await page.route(PLAYERS_ROUTE, (route) =>
		players === null
			? route.fulfill({ status: 503, body: '' })
			: route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ts: Date.now(), ...players }),
				}),
	);

	await page.route(BASES_ROUTE, (route) =>
		guilds === null
			? route.fulfill({ status: 503, body: '' })
			: route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ guilds }),
				}),
	);
}

/** A guild with one base, positioned inside the main island. */
function guildFixture() {
	return {
		id: 'g1',
		name: 'Test Guild',
		base_camp_level: 12,
		players: [{ name: 'Alpha' }, { name: 'Beta' }],
		bases: [
			{
				id: 'b1',
				x: -100000,
				y: 80000,
				pals: [{ id: 'BOSS_Anubis', name: 'Ann', level: 42 }],
			},
		],
	};
}

test('renders the map without console errors or broken assets', async ({ page }) => {
	const consoleErrors: string[] = [];
	const badResponses: string[] = [];
	page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()));
	page.on('response', (res) => {
		const { pathname } = new URL(res.url());
		if (pathname.startsWith('/palworld/') && res.status() >= 400) {
			badResponses.push(`${res.status()} ${pathname}`);
		}
	});

	await stubLive(page);
	await page.goto('/');

	await expect(page.locator('.leaflet-container')).toBeVisible();
	await page.waitForFunction(
		() => document.querySelectorAll('.leaflet-tile-loaded').length > 0,
		null,
		{ timeout: 15_000 },
	);

	expect(badResponses, 'asset requests under /palworld/').toEqual([]);
	expect(consoleErrors, 'console errors').toEqual([]);
});

test('reads both pyramids from their pmtiles archives', async ({ page }) => {
	// Tiles ship as two PMTiles archives rather than ~10,600 loose files,
	// because itch caps an HTML5 project at 1000. The client reads them
	// with range requests, so a partial response is the success signal.
	const layers = new Set<string>();
	let ranged = 0;
	page.on('response', (res) => {
		const m = new URL(res.url()).pathname.match(/^\/palworld\/(tiles|wt-overlay)\.pmtiles$/);
		if (!m) return;
		layers.add(m[1]);
		if (res.status() === 206) ranged += 1;
	});

	await stubLive(page);
	await page.goto('/');

	await expect
		.poll(() => [...layers].sort(), { timeout: 15_000 })
		.toEqual(['tiles', 'wt-overlay']);
	await expect.poll(() => ranged, { timeout: 15_000 }).toBeGreaterThan(0);
});


test('renders a filter toggle for every marker kind', async ({ page }) => {
	await stubLive(page);
	await page.goto('/');

	const filters = page.locator('.pal-map-filters');
	await expect(filters).toBeVisible();
	await expect(filters.locator('input[type="checkbox"]')).not.toHaveCount(0);
});

test('shows the offline state when the player endpoint fails', async ({ page }) => {
	await stubLive(page, { players: null });
	await page.goto('/');

	await expect(page.getByText('Players (offline)')).toBeVisible({ timeout: 15_000 });
});

test('reflects the live player count', async ({ page }) => {
	await stubLive(page, {
		players: {
			players: [
				{ name: 'Alpha', level: 32, x: -100000, y: 80000 },
				{ name: 'Beta', level: 7, x: -120000, y: 60000 },
			],
			bosses: [],
			events: [],
		},
	});
	await page.goto('/');

	await expect(page.getByText('Players (2)')).toBeVisible({ timeout: 15_000 });
});

test('shows no bases when the server reports none', async ({ page }) => {
	await stubLive(page, { guilds: [] });
	await page.goto('/');

	await expect(page.getByText('Bases (0)')).toBeVisible({ timeout: 15_000 });
	await expect(page.locator('.pal-base')).toHaveCount(0);
});

test('renders base markers from live guild data', async ({ page }) => {
	await stubLive(page, { guilds: [guildFixture()] });
	await page.goto('/');

	await expect(page.getByText('Bases (1)')).toBeVisible({ timeout: 15_000 });
	await expect(page.locator('.pal-base')).toHaveCount(1);
});

test('opens guild details when a base is clicked', async ({ page }) => {
	await stubLive(page, { guilds: [guildFixture()] });
	await page.goto('/');

	await page.locator('.pal-base').first().click();

	const modal = page.locator('.pal-base-modal');
	await expect(modal).toBeVisible();
	await expect(modal.getByText('Test Guild')).toBeVisible();
	await expect(modal.getByText('Camp Lv 12')).toBeVisible();
});

test('stays usable when the bases endpoint fails', async ({ page }) => {
	await stubLive(page, { guilds: null });
	await page.goto('/');

	// The map must still render and the count must not advance past zero.
	await expect(page.locator('.leaflet-container')).toBeVisible();
	await expect(page.getByText('Bases (0)')).toBeVisible({ timeout: 15_000 });
});
