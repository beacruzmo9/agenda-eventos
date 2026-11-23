import type { Category, Lang } from './config';

const ui = {
  es: {
    tagline: 'Todo lo que pasa en la ciudad',
    sampleNotice: 'Versión de prueba: los eventos que ves son de ejemplo.',
    search: 'Buscar evento o lugar',
    when: 'Cuándo',
    whenAll: 'Todo',
    whenToday: 'Hoy',
    whenWeekend: 'Este finde',
    whenWeek: 'Próximos 7 días',
    whenMonth: 'Próximos 30 días',
    price: 'Precio',
    priceAll: 'Todos',
    priceFree: 'Gratis',
    pricePaid: 'De pago',
    categories: 'Tipo',
    allCategories: 'Todos',
    free: 'Gratis',
    source: 'Ver en la fuente',
    noResults: 'No hay eventos con estos filtros.',
    results: (n: number) => (n === 1 ? '1 evento' : `${n} eventos`),
    until: 'Hasta el',
    ongoing: 'En curso',
    clear: 'Quitar filtros',
    footerData: 'Datos básicos tomados de sus fuentes originales. Consulta siempre la web del organizador antes de ir.',
    language: 'Idioma',
  },
  en: {
    tagline: 'Everything happening in town',
    sampleNotice: 'Preview version: the events shown are samples.',
    search: 'Search event or venue',
    when: 'When',
    whenAll: 'All',
    whenToday: 'Today',
    whenWeekend: 'This weekend',
    whenWeek: 'Next 7 days',
    whenMonth: 'Next 30 days',
    price: 'Price',
    priceAll: 'All',
    priceFree: 'Free',
    pricePaid: 'Paid',
    categories: 'Type',
    allCategories: 'All',
    free: 'Free',
    source: 'View source',
    noResults: 'No events match these filters.',
    results: (n: number) => (n === 1 ? '1 event' : `${n} events`),
    until: 'Until',
    ongoing: 'On now',
    clear: 'Clear filters',
    footerData: 'Basic details taken from their original sources. Always check the organiser’s website before going.',
    language: 'Language',
  },
} as const;

const categoryNames: Record<Lang, Record<Category, string>> = {
  es: {
    concierto: 'Conciertos',
    teatro: 'Teatro',
    danza: 'Danza',
    flamenco: 'Flamenco',
    cine: 'Cine',
    exposicion: 'Exposiciones',
    infantil: 'Infantil',
    conferencia: 'Charlas',
    festival: 'Festivales',
    otros: 'Otros',
  },
  en: {
    concierto: 'Concerts',
    teatro: 'Theatre',
    danza: 'Dance',
    flamenco: 'Flamenco',
    cine: 'Film',
    exposicion: 'Exhibitions',
    infantil: 'Kids',
    conferencia: 'Talks',
    festival: 'Festivals',
    otros: 'Other',
  },
};

export function t(lang: Lang) {
  return ui[lang];
}

export function categoryName(lang: Lang, c: Category) {
  return categoryNames[lang][c];
}

export const locales: Record<Lang, string> = { es: 'es-ES', en: 'en-GB' };
