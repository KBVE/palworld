import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
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
