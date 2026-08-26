import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import ReactPalworldMap from './map/ReactPalworldMap';
import { FIRST_TILE_EVENT } from './map/pmtilesLayer';

// Clear the splash once real tiles are on screen. The timeout is a
// backstop: if the archives fail we still want the map and its markers
// visible rather than a spinner that never resolves.
const splash = document.getElementById('loading');
if (splash) {
	const dismiss = () => {
		splash.classList.add('done');
		window.setTimeout(() => splash.setAttribute('hidden', ''), 400);
	};
	document.addEventListener(FIRST_TILE_EVENT, dismiss, { once: true });
	window.setTimeout(dismiss, 10_000);
}

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<div className="pal-map-panel">
			<ReactPalworldMap />
		</div>
	</StrictMode>,
);
