// Configuración general de Ciudad en vivo.
export const SITE_NAME = 'Ciudad en vivo';

export const LANGS = ['es', 'en'] as const;
export type Lang = (typeof LANGS)[number];
export const DEFAULT_LANG: Lang = 'es';

// Ciudades activas. Para añadir una: nueva entrada aquí + carpeta data/<id>/.
export const CITIES = [
  { id: 'granada', name: 'Granada', timezone: 'Europe/Madrid' },
] as const;
export type CityId = (typeof CITIES)[number]['id'];
export const DEFAULT_CITY: CityId = 'granada';

// Mientras sea true, se muestra un aviso de "datos de ejemplo".
export const SAMPLE_DATA = false;

export const CATEGORIES = [
  'concierto',
  'teatro',
  'danza',
  'flamenco',
  'cine',
  'exposicion',
  'infantil',
  'conferencia',
  'festival',
  'otros',
] as const;
export type Category = (typeof CATEGORIES)[number];

/** Construye una URL interna respetando el "base" de GitHub Pages. */
export function url(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}/${path.replace(/^\//, '')}`;
}
