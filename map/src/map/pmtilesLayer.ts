import L from 'leaflet';
import { PMTiles } from 'pmtiles';

/**
 * Leaflet raster layer backed by a PMTiles archive.
 *
 * itch.io caps an HTML5 project at 1000 files, so the two pyramids ship
 * as single archives read over HTTP range requests instead of ~10,600
 * loose tiles.
 *
 * Archives written by tools/build_pmtiles.py carry two custom metadata
 * keys. `kbve:offsets` records the per-zoom shift applied at build time,
 * because the overlay sits at negative tile coordinates that PMTiles
 * cannot address; the shift is undone here before each lookup.
 * `kbve:minzoom` is the shallowest zoom actually packed, which becomes
 * the layer's minNativeZoom so Leaflet upscales rather than requesting a
 * level that was dropped.
 */

type Offsets = Record<string, [number, number]>;

export interface PMTilesLayerOptions extends L.GridLayerOptions {
	/** Fallback when a tile is absent, as a data URI. Defaults to transparent. */
	errorTileUrl?: string;
}

/** Fired once the first tile of any archive has decoded. */
export const FIRST_TILE_EVENT = 'palmap:first-tile';

let announced = false;
function announceFirstTile(): void {
	if (announced) return;
	announced = true;
	document.dispatchEvent(new CustomEvent(FIRST_TILE_EVENT));
}

const TRANSPARENT =
	'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

export async function pmtilesLayer(
	url: string,
	options: PMTilesLayerOptions = {},
): Promise<L.GridLayer> {
	const archive = new PMTiles(url);
	const metadata = (await archive.getMetadata()) as Record<string, unknown>;

	const offsets = (metadata['kbve:offsets'] as Offsets) ?? {};
	const minNative = metadata['kbve:minzoom'] as number | undefined;
	const maxNative = metadata['kbve:maxzoom'] as number | undefined;
	const fallback = options.errorTileUrl ?? TRANSPARENT;

	// L.GridLayer.extend() is typed as returning a zero-arg constructor, so
	// the options-taking constructor has to be declared.
	const PMTilesLayer = L.GridLayer.extend({
		createTile(coords: L.Coords, done: L.DoneCallback) {
			const img = document.createElement('img');
			img.setAttribute('role', 'presentation');

			const [offsetX, offsetY] = offsets[String(coords.z)] ?? [0, 0];

			archive
				.getZxy(coords.z, coords.x - offsetX, coords.y - offsetY)
				.then((tile) => {
					if (!tile) {
						// A hole in the pyramid is normal: both layers are
						// sparse regions, not full worlds.
						img.src = fallback;
						done(undefined, img);
						return;
					}
					announceFirstTile();
					const blob = new Blob([tile.data], { type: 'image/webp' });
					const objectUrl = URL.createObjectURL(blob);
					// Leaflet reuses tile elements, so the blob has to be
					// released when the element is evicted or this leaks.
					img.onload = () => URL.revokeObjectURL(objectUrl);
					img.src = objectUrl;
					done(undefined, img);
				})
				.catch((err: Error) => {
					img.src = fallback;
					done(err, img);
				});

			return img;
		},
	}) as unknown as new (options: L.GridLayerOptions) => L.GridLayer;

	return new PMTilesLayer({
		...options,
		...(minNative !== undefined ? { minNativeZoom: minNative } : {}),
		...(maxNative !== undefined ? { maxNativeZoom: maxNative } : {}),
	});
}
