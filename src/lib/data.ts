import type { Category, CityId } from './config';

export interface Price {
  free: boolean | null; // null = precio desconocido ("Consultar")
  min?: number | null;
  max?: number | null;
  text?: string | null;
}

export interface EventItem {
  id: string;
  city: CityId;
  title: string;
  start: string; // ISO 8601 con zona horaria
  end?: string | null; // para exposiciones y eventos de varios días
  all_day?: boolean;
  venue_id: string;
  category: Category;
  price: Price;
  url: string; // enlace a la fuente original
  source: string;
  updated?: string;
}

export interface Venue {
  id: string;
  city: CityId;
  name: string;
  address?: string;
  url?: string;
}

// Los datos se generan en data/<ciudad>/ (en Fase 2 los escribirán los conectores).
const eventFiles = import.meta.glob<EventItem[]>('../../data/*/events.json', { eager: true, import: 'default' });
const venueFiles = import.meta.glob<Venue[]>('../../data/*/venues.json', { eager: true, import: 'default' });

export function getVenues(city: CityId): Map<string, Venue> {
  const list = venueFiles[`../../data/${city}/venues.json`] ?? [];
  return new Map(list.map((v) => [v.id, v]));
}

/** Eventos que no han terminado aún, ordenados por fecha. */
export function getUpcomingEvents(city: CityId, now = new Date()): EventItem[] {
  const list = eventFiles[`../../data/${city}/events.json`] ?? [];
  return list
    .filter((e) => new Date(e.end ?? e.start) >= startOfDay(now))
    .sort((a, b) => a.start.localeCompare(b.start));
}

function startOfDay(d: Date) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}
