/**
 * Prefix for runtime asset URLs.
 *
 * The build is served from a subpath on itch.io
 * (html-classic.itch.zone/html/<build-id>/), so absolute paths like
 * `/palworld/...` resolve against the CDN root and 404. Vite's `base` is
 * './', which makes BASE_URL relative to index.html and correct in every
 * host: dev server, Cloudflare Pages, and an itch iframe.
 */
export const ASSET_BASE = import.meta.env.BASE_URL;
