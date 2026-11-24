# Ciudad en vivo — memoria del proyecto

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
/data/<ciudad>/events.json      eventos próximos (GENERADO por scrapers/run.py, no editar a mano)
/data/<ciudad>/venues.json      lugares (los de los conectores se añaden solos; los manuales se conservan)
/data/<ciudad>/sources/<fuente>.json   último resultado bueno de cada conector
/data/<ciudad>/archive/AAAA-MM.json    eventos ya pasados (archivo)
/scrapers/common.py     sesión HTTP educada (UA CiudadEnVivoBot, robots.txt, pausa 1,5 s, 3 intentos ante 429/5xx/cortes: esperas 5 s y 20 s, respeta Retry-After), fechas en español
/scrapers/granada/ugr.py   conector CANAL UGR
/scrapers/run.py        ejecuta conectores (lista CONNECTORS), fusiona, archiva  → `python -m scrapers.run`
/scrapers/tests/        pruebas sin red → `python -m unittest discover -s scrapers/tests -t .`
/docs/email-ayuntamiento.md   borrador de email para pedir acceso a la agenda municipal
/.github/workflows/deploy.yml   pruebas → recoger eventos → commit de data/ en main → build → GitHub Pages (push, manual y diario 04:00 UTC)
```
- Astro 7 en la raíz del repo (no en /site). `npm run dev` / `npm run build`.
- URL actual: https://beacruzmo9.github.io/agenda-eventos/ (`base: '/agenda-eventos'` en astro.config.mjs; quitarlo al pasar a dominio propio).
- Filtros: búsqueda de texto, cuándo (todo/hoy/finde/7 días/30 días), gratis/de pago, tipos (multiselección). Exposiciones en curso aparecen en el grupo "En curso".

## 3. Fuentes de datos — evaluación inicial

⚠️ Evaluación hecha de memoria en la sesión 0; **hay que verificar las condiciones de uso de cada una antes de programar su conector** (Fase 2–3). No es asesoramiento jurídico.

Recordatorio legal clave: en la UE, aunque los *hechos* (fecha, hora, lugar) no tienen copyright, las **bases de datos** tienen un derecho *sui generis* (Directiva 96/9/CE, art. 133 LPI): extraer de forma sistemática una parte sustancial de la base de datos de otro agregador puede ser ilegal aunque solo copies datos básicos. Por eso preferimos **fuentes primarias** (quien organiza el evento) y **APIs o datos abiertos**.

| Fuente | Valoración | Motivo |
|---|---|---|
| Agenda del Ayuntamiento (granada.org) | ⛔ **Bloqueada (S2)** | Sector público (Ley 37/2007), pero granada.org (Akamai) devuelve 403 "Access Denied" a servidores en la nube, **incluido GitHub Actions** (comprobado). La agenda cultural está en `granada.org/inet/wagenda.nsf` (Lotus Notes, solo HTML; sin RSS/iCal/datos abiertos encontrados). Pendiente: email de la propietaria pidiendo formato reutilizable o acceso (borrador en docs/). |
| Universidad de Granada (CANAL UGR) | ✅ **Conector hecho (S2)** | `canal.ugr.es/agenda-canal-ugr/proximas-actividades/` (HTML, ~3 páginas, ~45 actividades) + ficha de cada actividad solo para el campo de entrada (se cachea). Existe también `/wp-json/SI2/v1/agenda` pero solo da el día actual. robots.txt lo permite. Se descartan: actos institucionales, seminarios académicos (título "Seminario…/Defensa…"), sedes de Ceuta/Melilla/Santa Fe y en línea. |
| Junta de Andalucía (datos abiertos) | 🟡 Poco útil para Granada capital | API `datos.juntadeandalucia.es/api/v0/schedule/all?format=json` (CC BY 4.0, ~900 eventos, mayoría antiguos). Solo 1 evento futuro en Granada capital (nov. 2026). Conector sencillo posible en Fase 3, baja prioridad. |
| Diputación de Granada | ❓ Sin evaluar | Fase 3. |
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
| 2 ✅ | Primer conector real (UGR; Ayuntamiento bloqueado) + GitHub Action diaria que actualiza y despliega | Web con datos reales que se actualiza sola |
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
- (S2) Los datos generados se guardan en el repo (commit automático del bot) → historial y "último dato bueno" aunque una fuente falle. Si un conector devuelve <30 % de los eventos que tenía, se considera fallo y se conserva lo anterior.
- (S3) Cambio de nombre: Agendalia → **Ciudad en vivo** (web, bot `CiudadEnVivoBot`, commits del bot `ciudadenvivo-bot`, README, email al Ayuntamiento). Dominio previsto: ciudadenvivo.es.
- (S2) La UGR publica muchos seminarios de investigación: se filtran por título para no ahogar la agenda cultural. Revisar el criterio si la propietaria lo pide.

## 7. Respuestas de la propietaria (S0) y decisiones derivadas
1. **Nombre**: la web debe servir a la larga para **cualquier capital** (selector de ciudad). ~~Agendalia~~ → **(S3) Nombre definitivo: Ciudad en vivo.** Dominio libre según la propietaria: **ciudadenvivo.es** (no comprado aún; se usará en Fase 8). Repo: `beacruzmo9/agenda-eventos` (el nombre del repo puede quedarse así).
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
- ✅ GitHub Pages activado (Source: GitHub Actions). Web publicada y comprobada por la propietaria: https://beacruzmo9.github.io/agenda-eventos/ (el workflow también se ejecuta solo cada día a las 04:00 UTC).
- Mejoras menores anotadas para más adelante: guardar filtros en la URL (para compartir enlaces), botón "volver arriba", página de detalle por evento.
- **Fase 2 hecha (S2, 2026-11-23)**: granada.org bloquea GitHub (403) → primer conector real = **CANAL UGR** (36 eventos útiles al estrenarlo: exposiciones, cineclub, conferencias, conciertos). `SAMPLE_DATA = false`, eventos de ejemplo eliminados. Precio desconocido → `price.free: null` y se muestra "Consultar" (no aparece en filtros gratis/de pago). Workflow: pruebas → `scrapers.run` (si falla, se publica igual con los últimos datos buenos) → commit automático de `data/` en main → build. Probado en GitHub Actions desde la rama de trabajo.
- Entorno cloud de Claude: entorno personal `agenda-eventos` con acceso a granada.org, canal.ugr.es y datos/www.juntadeandalucia.es. Para nuevas fuentes hay que añadir el dominio.
- ✅ PR #1 fusionada (2026-11-23). Primer despliegue: la UGR dio un 503 momentáneo → se publicaron los datos guardados (el respaldo funcionó). Primera recogida diaria automática OK (commit del bot 2026-11-24).
- (S2b, 2026-11-24) Añadidos reintentos HTTP en `PoliteSession` + pruebas (`scrapers/tests/test_http.py`).
- ⏳ **Pendiente de la propietaria**: enviar el email al Ayuntamiento (docs/email-ayuntamiento.md).
- **Siguiente paso: Fase 3** — más fuentes: Ticketmaster Discovery API (necesita clave gratuita), Diputación, Junta (baja prioridad), webs de salas con iCal; deduplicación entre fuentes. Si el Ayuntamiento responde, conector de granada.org.

## 9. Registro de sesiones
- S0 — 2026-11-23 — Planificación. Arquitectura, evaluación de fuentes, checklist legal, plan por fases. Repo creado. Nombre: Agendalia.
- S1 — 2026-11-23 — Fase 1: esqueleto web, filtros, ES/EN, datos de ejemplo, workflow de GitHub Pages.
- S2 — 2026-11-23 — Fase 2: granada.org bloquea servidores en la nube (también GitHub) → conector CANAL UGR, recogida diaria en la Action, datos reales en la web, archivo de eventos pasados, borrador de email al Ayuntamiento.
- S2b — 2026-11-24 — Reintentos ante errores momentáneos de las fuentes (tras un 503 de la UGR en el primer despliegue).
- S3a — 2026-11-24 — Cambio de nombre a **Ciudad en vivo** (dominio previsto ciudadenvivo.es). Título de página: "Granada · lema · Ciudad en vivo".
