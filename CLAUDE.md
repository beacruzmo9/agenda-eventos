# Agendalia — memoria del proyecto

> Este archivo es la memoria compartida entre sesiones. **Léelo entero al empezar cada sesión y actualízalo al terminar** (sección "Estado actual" y "Registro de sesiones").

## 1. Qué es

Web pública y gratuita que reúne **todos los eventos de Granada** (conciertos, teatro, cine, exposiciones, actividades culturales…), gratuitos y de pago, actualizada automáticamente cada día.

Requisitos de la propietaria:
- Todos los eventos programados, sin límite de fecha.
- Filtros por tipología y por gratis / de pago.
- Vista de **listado** y vista de **calendario**.
- **Favoritos**: guardar eventos y sitios (salas, teatros…) y ver los demás eventos de esos sitios.
- Cada evento: título, fecha y hora, lugar, tipología, precio (o "Gratis") y **enlace a la fuente original**.
- **Formulario** para que salas, bares, peñas u organizadores envíen sus eventos.
- Diseño limpio, *mobile first*.
- Se actualiza sola cada día (GitHub Actions). Alojamiento gratuito. Quizá dominio propio más adelante.
- **Solo datos básicos + enlace**. Nunca copiar descripciones completas ni imágenes de otras webs.

Forma de trabajar:
- Sesiones cortas, **una fase por sesión**. No adelantar fases sin pedirlo.
- Cuando la propietaria tenga que hacer algo (cuentas, configuración), explicarlo **paso a paso y en lenguaje sencillo**.
- Idioma de trabajo: español.
- **Último paso obligatorio de CADA fase/sesión**: actualizar este CLAUDE.md con lo que se ha hecho y lo que falta (secciones 5, 8 y 9), hacer commit y push.

## 2. Arquitectura (confirmada en Fase 1)

```
            GitHub Actions (cron diario ~05:00 Europe/Madrid)
                              │
   ┌──────────────────────────┼───────────────────────────┐
   │  scrapers/ (Python)      │                           │
   │  un "conector" por fuente│  envíos del formulario    │
   │  ayuntamiento.py, ugr.py │  (Google Sheet → CSV)     │
   │  ticketmaster.py, ...    │  solo filas "aprobado"    │
   └──────────────┬───────────┴──────────────┬────────────┘
                  ▼                          ▼
          normalizar + deduplicar + asignar lugar (venues.yaml)
                              │
                              ▼
                 data/events.json  ·  data/venues.json
                              │
                              ▼
       Web estática (Astro) → build → GitHub Pages
```

- **Recogida de datos**: Python 3.12 (`requests`, `beautifulsoup4`, `icalendar`, `feedparser`). Cada conector devuelve eventos con el mismo esquema. Si un conector falla, los demás siguen y el último dato bueno se conserva.
- **Web**: [Astro](https://astro.build) (genera HTML estático, rápido, bueno para SEO; permite una página por lugar y por evento). JS mínimo en el navegador para filtros, calendario y favoritos.
- **Calendario**: vista mensual propia y ligera (o FullCalendar si compensa).
- **Favoritos**: en `localStorage` del navegador. Sin cuentas ni login → sin datos personales → más simple legalmente. (Limitación: no se sincronizan entre dispositivos.)
- **Formulario**: Google Forms o Tally (gratis) → hoja de cálculo → la Action lee solo las filas marcadas como aprobadas. Moderación manual (una casilla).
- **Alojamiento**: GitHub Pages (gratis, admite dominio propio con HTTPS). Netlify como alternativa.
- **Analítica** (opcional): GoatCounter o similar sin cookies → no hace falta banner de cookies.

### Esquema de evento (borrador)
```json
{
  "id": "ayto-2026-12-05-concierto-x",
  "city": "granada",
  "title": "Concierto X",
  "start": "2026-12-05T21:00:00+01:00",
  "end": null,
  "all_day": false,
  "venue_id": "teatro-isabel-la-catolica",
  "category": "concierto",        // concierto | teatro | danza | cine | exposicion | infantil | flamenco | conferencia | festival | otros
  "price": { "free": false, "min": 12, "max": 20, "text": "12–20 €" },
  "url": "https://fuente-original/...",
  "source": "ayuntamiento",
  "updated": "2026-11-23"
}
```
Las exposiciones (eventos de varios días) llevan `start` y `end` con `all_day: true`.

### Estructura de carpetas (real)
```
/src/lib/config.ts      nombre web, idiomas, ciudades, categorías, SAMPLE_DATA, url()
/src/lib/i18n.ts        textos ES/EN y nombres de categorías
/src/lib/data.ts        tipos EventItem/Venue y lectura de data/<ciudad>/*.json
/src/layouts/Base.astro cabecera (logo, selector idioma), aviso datos de ejemplo, pie
/src/components/EventCard.astro
/src/pages/index.astro                 redirige según idioma del navegador → /es|en/granada/
/src/pages/[lang]/index.astro          → ciudad por defecto (futuro selector de ciudad)
/src/pages/[lang]/[city]/index.astro   listado agrupado por día + filtros (JS inline)
/src/styles/global.css  estilos, modo oscuro automático
/data/<ciudad>/events.json, venues.json   (ahora: 15 eventos de EJEMPLO, Fase 2 los genera)
/scrapers/              (Fase 2) conectores Python
/.github/workflows/deploy.yml   build + publicar en GitHub Pages (push, manual y diario 04:00 UTC)
```
- Astro 7 en la raíz del repo (no en /site). `npm run dev` / `npm run build`.
- URL actual: https://beacruzmo9.github.io/agenda-eventos/ (`base: '/agenda-eventos'` en astro.config.mjs; quitarlo al pasar a dominio propio).
- Filtros: búsqueda de texto, cuándo (todo/hoy/finde/7 días/30 días), gratis/de pago, tipos (multiselección). Exposiciones en curso aparecen en el grupo "En curso".

## 3. Fuentes de datos — evaluación inicial

⚠️ Evaluación hecha de memoria en la sesión 0; **hay que verificar las condiciones de uso de cada una antes de programar su conector** (Fase 2–3). No es asesoramiento jurídico.

Recordatorio legal clave: en la UE, aunque los *hechos* (fecha, hora, lugar) no tienen copyright, las **bases de datos** tienen un derecho *sui generis* (Directiva 96/9/CE, art. 133 LPI): extraer de forma sistemática una parte sustancial de la base de datos de otro agregador puede ser ilegal aunque solo copies datos básicos. Por eso preferimos **fuentes primarias** (quien organiza el evento) y **APIs o datos abiertos**.

| Fuente | Valoración | Motivo |
|---|---|---|
| Agenda del Ayuntamiento (granada.org) | ✅ **Empezar aquí** | Información del sector público, reutilizable por defecto (Ley 37/2007) citando la fuente. Comprobar si hay RSS/iCal/datos abiertos o si hay que leer el HTML. |
| Universidad de Granada (agenda cultural UGR / La Madraza) | ✅ Prioridad alta | Organismo público, mucha actividad gratuita. Comprobar RSS/iCal. |
| Diputación de Granada / Junta de Andalucía (datos abiertos, agenda cultural) | ✅ Prioridad alta | Sector público; la Junta publica portal de datos abiertos. Comprobar si hay dataset de eventos. |
| Ticketmaster Discovery API | ✅ Buena opción | API oficial gratuita con clave; permite mostrar datos básicos con enlace. Cubre parte de los grandes conciertos. |
| Eventbrite API | 🟡 Parcial | Su API ya no permite buscar eventos por ciudad (se retiró en 2019-2020); solo eventos de organizadores/lugares concretos cuyo ID conozcamos. |
| Webs de salas y teatros | 🟡 Caso a caso | Muchas tienen iCal/RSS o calendario sencillo. **Pedir permiso por email** (casi siempre dicen que sí: es publicidad gratis). Mejor aún: invitarles a usar el formulario. |
| Viral Agenda | 🔴 No sin permiso | Es un agregador privado: su base de datos está protegida. Solo si nos dan permiso o acuerdo (se les puede escribir). |
| Fever | 🔴 Descartar | Sin API pública; sus condiciones prohíben la extracción automatizada. Posible programa de afiliados en el futuro. |
| El Corte Inglés Entradas | 🔴 Descartar | Condiciones prohíben la extracción automatizada; sin API pública. |

Candidatas a salas/espacios a contactar (por confirmar): Teatro Isabel la Católica, Teatro Alhambra, Auditorio Manuel de Falla / OCG, Centro Federico García Lorca, Palacio de Congresos, Centro Cultural CajaGranada, Sala El Tren, Planta Baja, Lemon Rock, Industrial Copera, La Expositiva…

## 4. Legal — checklist para la web pública (España)

No es asesoramiento jurídico; revisar con un profesional si la web crece o se monetiza.
- [ ] **Aviso legal** (LSSI-CE art. 10): titular, NIF/DNI, email de contacto. Obligatorio si hay actividad económica (publicidad, afiliados); recomendable siempre.
- [ ] **Política de privacidad** (RGPD + LOPDGDD): obligatoria porque el formulario recoge datos (nombre/email del organizador). Indicar responsable, finalidad, base legal, plazo de conservación, derechos y que los datos van a Google/Tally (encargado de tratamiento).
- [ ] **Política de cookies**: si solo usamos `localStorage` para favoritos (técnicamente necesario, lo pide el usuario) y analítica sin cookies → **no hace falta banner**. Si se añaden Google Analytics, YouTube, mapas de Google, etc. → banner de consentimiento obligatorio (guía AEPD).
- [ ] **Aviso de exactitud**: "Los datos proceden de fuentes externas; consulta siempre la web original antes de ir".
- [ ] **Condiciones del formulario**: el organizador declara que la información es veraz y que tiene derecho a publicarla; nos reservamos moderar.
- [ ] **Atribución**: mostrar la fuente en cada evento y una página "Fuentes" con todas.
- [ ] **Retirada**: email de contacto para que cualquier fuente pida quitar sus datos (y atenderlo rápido).
- [ ] No usar imágenes ni textos de otras webs. No usar logos de marcas.
- [ ] Respetar `robots.txt`, identificar el bot (User-Agent con URL de la web) y hacer pocas peticiones (1 vez al día, con pausas).

## 5. Plan por fases (una por sesión)

| Fase | Contenido | Resultado |
|---|---|---|
| 0 ✅ | Preguntas, arquitectura, plan, repo con CLAUDE.md | Este archivo |
| 1 ✅ | Esqueleto web Astro + esquema de datos + datos de ejemplo + listado con filtros (tipo, gratis/pago, fecha) + diseño móvil. Publicar en GitHub Pages | Web visible con datos de prueba |
| 2 | Primer conector real (Ayuntamiento) + GitHub Action diaria que actualiza y despliega | Web con datos reales que se actualiza sola |
| 3 | Más fuentes públicas/APIs: UGR, Diputación/Junta, Ticketmaster (y Eventbrite por organizador) + deduplicación | Más cobertura |
| 4 | Vista calendario | Calendario mensual/semanal |
| 5 | Lugares (venues.yaml normalizado, página por lugar) + Favoritos de eventos y lugares | Sección "Mis favoritos" |
| 6 | Formulario de envío (Tally/Google Forms) + moderación + integración en la Action | Organizadores pueden enviar eventos |
| 7 | Páginas legales, página "Fuentes", SEO básico, accesibilidad, rendimiento | Lista para difundir |
| 8 | Dominio propio (opcional), contacto con salas para iCal/permiso, mejoras | — |

## 6. Decisiones tomadas
- (S0) Web estática + datos generados por GitHub Actions cada día; sin servidor ni base de datos.
- (S0) Solo datos básicos + enlace a la fuente; sin textos completos ni imágenes ajenas.
- (S0) Priorizar fuentes públicas y APIs oficiales; agregadores privados solo con permiso.
- (S0) Favoritos en el navegador (sin cuentas).
- (S0) Repositorio público `beacruzmo9/agenda-eventos` (solo la propietaria y Claude pueden modificarlo) → GitHub Pages.
- (S0) Multiciudad e idiomas ES/EN previstos desde el principio; solo Granada capital activa.

## 7. Respuestas de la propietaria (S0) y decisiones derivadas
1. **Nombre**: la web debe servir a la larga para **cualquier capital** (selector de ciudad). **Elegido: Agendalia.** ⏳ Pendiente: comprobar si agendalia.es / .com están libres (no comprar aún). Repo: `beacruzmo9/agenda-eventos` (el nombre del repo puede quedarse así).
   → **Multiciudad desde el diseño**: campo `city` en eventos y lugares, URLs `/{idioma}/{ciudad}/...` (ej. `/es/granada/`), conectores agrupados por ciudad (`scrapers/granada/`). Solo Granada activa al principio.
2. **Ámbito**: Granada capital. Área metropolitana/provincia más adelante.
3. **Cine** (a criterio de Claude): incluir cine "evento" — filmoteca, ciclos, cineclubs (p. ej. UGR), cine de verano, VOS especiales, preestrenos, festivales. **No** la cartelera comercial completa (cientos de sesiones, ahogaría el resto); en su lugar, enlace a la cartelera de cada cine en la página del lugar.
4. **Eventos pasados** (a criterio de Claude): se ocultan del listado y calendario por defecto; se guardan en un **archivo** consultable (por mes y en la página de cada lugar). Datos pasados en ficheros separados por mes para que la web siga ligera.
5. **Formulario**: moderación manual por la propietaria antes de publicar.
6. **Idiomas**: español e inglés. Se traduce la interfaz, categorías y textos fijos; los títulos de los eventos se muestran tal cual vienen de la fuente (sin traducir).
7. **Analítica** (recomendación): GoatCounter (gratuito, sin cookies, sin banner). Se configura en Fase 7.
8. **Publicidad/afiliación**: no, por ahora.
9. **Titular**: la propietaria (persona física). Aviso legal con su nombre y un email de contacto dedicado (recomendado crear uno solo para la web). Con NIF si en algún momento hay actividad económica.

## 8. Estado actual
- **Fase 1 hecha (S1, 2026-11-23)**: web Astro con listado agrupado por día, filtros (texto, cuándo, gratis/pago, tipos), ES/EN, estructura multiciudad, modo oscuro, diseño móvil probado (captura iPhone OK, filtros OK, sin errores JS). 15 eventos de ejemplo con aviso visible (`SAMPLE_DATA = true`). Workflow `deploy.yml` creado.
- ⏳ **Pendiente de la propietaria**: activar GitHub Pages (Settings → Pages → Source: "GitHub Actions") y comprobar que la web carga en https://beacruzmo9.github.io/agenda-eventos/. Si el primer workflow falló antes de activarlo, relanzarlo (Actions → "Publicar web" → Run workflow).
- Mejoras menores anotadas para más adelante: guardar filtros en la URL (para compartir enlaces), botón "volver arriba", página de detalle por evento.
- **Siguiente paso: Fase 2** — revisar condiciones/formato de la agenda de granada.org, programar el conector en Python (`scrapers/granada/ayuntamiento.py`) que escriba `data/granada/events.json` y `venues.json`, añadirlo al workflow diario (antes del build) y poner `SAMPLE_DATA = false` cuando haya datos reales. Último paso: actualizar CLAUDE.md.

## 9. Registro de sesiones
- S0 — 2026-11-23 — Planificación. Arquitectura, evaluación de fuentes, checklist legal, plan por fases. Repo creado. Nombre: Agendalia.
- S1 — 2026-11-23 — Fase 1: esqueleto web, filtros, ES/EN, datos de ejemplo, workflow de GitHub Pages.
