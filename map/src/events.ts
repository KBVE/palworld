// Local stand-in for @kbve/droid's event bus. The map uses exactly one
// event, so depending on the monorepo package for it is not worth the
// coupling. Same surface: on / off / emit.

export interface LivePlayer {
	name: string;
	level: number;
	x: number;
	y: number;
}

export interface LiveBoss {
	x: number;
	y: number;
	respawn_at: number;
	name?: string;
	level?: number;
}

export interface LiveEvent {
	kind: string;
	x: number;
	y: number;
	first_seen: number;
}

export interface DroidEventMap {
	'palworld-live-snapshot': {
		ts: number;
		offline: boolean;
		players: LivePlayer[];
		bosses: LiveBoss[];
		events: LiveEvent[];
	};
}

type Handler<K extends keyof DroidEventMap> = (payload: DroidEventMap[K]) => void;

const handlers = new Map<string, Set<Handler<never>>>();

export const DroidEvents = {
	on<K extends keyof DroidEventMap>(key: K, fn: Handler<K>): void {
		let set = handlers.get(key as string);
		if (!set) handlers.set(key as string, (set = new Set()));
		set.add(fn as Handler<never>);
	},

	off<K extends keyof DroidEventMap>(key: K, fn: Handler<K>): void {
		handlers.get(key as string)?.delete(fn as Handler<never>);
	},

	emit<K extends keyof DroidEventMap>(key: K, payload: DroidEventMap[K]): void {
		const set = handlers.get(key as string);
		if (!set) return;
		for (const fn of set) (fn as Handler<K>)(payload);
	},
};
