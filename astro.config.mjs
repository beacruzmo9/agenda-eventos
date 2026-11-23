import { defineConfig } from 'astro/config';

// Mientras la web viva en https://beacruzmo9.github.io/agenda-eventos/ necesita "base".
// Con dominio propio (p. ej. agendalia.es): site = 'https://agendalia.es' y quitar base.
export default defineConfig({
  site: 'https://beacruzmo9.github.io',
  base: '/agenda-eventos',
  trailingSlash: 'always',
});
