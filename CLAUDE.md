# Agenda Granada — memoria del proyecto

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

## 2. Arquitectura propuesta (pendiente de confirmar en Fase 1)

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

### Estructura de carpetas prevista
```
/scrapers        conectores por fuente + normalización + dedupe
/data            events.json, venues.json (generados) + venues.yaml (lugares a mano)
/site            web Astro
/.github/workflows/update.yml   actualización diaria + despliegue
CLAUDE.md, README.md
```

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
| 1 | Esqueleto web Astro + esquema de datos + datos de ejemplo + listado con filtros (tipo, gratis/pago, fecha) + diseño móvil. Publicar en GitHub Pages | Web visible con datos de prueba |
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

## 7. Preguntas abiertas (pendientes de respuesta)
1. Nombre de la web (y de la cuenta/repositorio de GitHub). Repositorio: `beacruzmo9/agenda-eventos`. Nombre público de la web: pendiente.
2. Ámbito: ¿solo Granada capital o también área metropolitana / provincia?
3. Cine: ¿incluir la cartelera comercial completa (muchísimas sesiones) o solo cine "evento" (ciclos, filmoteca, estrenos especiales, cine de verano)?
4. Eventos pasados: ¿se ocultan o se guarda un archivo consultable?
5. Formulario: ¿moderación manual antes de publicar (recomendado) o publicación directa?
6. Idioma: ¿solo español o también inglés (turistas, Erasmus)?
7. ¿Analítica de visitas (sin cookies) sí o no?
8. ¿Habrá publicidad/afiliación en algún momento? (afecta al aviso legal)
9. ¿Qué titular aparecerá en el aviso legal (persona física o asociación)?

## 8. Estado actual
- **Sesión 0 (2026-11-23)**: creado el repositorio `beacruzmo9/agenda-eventos` en GitHub con este CLAUDE.md, README y .gitignore. Cuenta de GitHub conectada a Claude (app instalada). Pendiente: decidir si el repo queda público (GitHub Pages) o privado (Netlify/Cloudflare Pages).
- **Siguiente paso**: responder las preguntas abiertas (sección 7) y empezar la **Fase 1**.

## 9. Registro de sesiones
- S0 — 2026-11-23 — Planificación. Arquitectura, evaluación de fuentes, checklist legal, plan por fases.
