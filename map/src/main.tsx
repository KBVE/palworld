import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import ReactPalworldMap from './map/ReactPalworldMap';

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<div className="pal-map-panel">
			<ReactPalworldMap />
		</div>
	</StrictMode>,
);
