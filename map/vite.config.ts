import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
	// itch.io serves HTML5 builds from html-classic.itch.zone/html/<id>/,
	// so absolute URLs resolve to the CDN root and 404. Everything must be
	// relative to index.html.
	base: './',
	plugins: [react()],
	resolve: {
		alias: {
			react: 'preact/compat',
			'react-dom': 'preact/compat',
			'react-dom/client': 'preact/compat/client',
			'react/jsx-runtime': 'preact/jsx-runtime',
			'react/jsx-dev-runtime': 'preact/jsx-dev-runtime',
		},
	},
	server: { port: 4322 },
});
