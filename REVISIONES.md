# Revisiones de la mejora estética

Cada vuelta: cambios → checks → capturas → **árbitro adversarial** (subagente independiente, contexto limpio, sin ver mi razonamiento; recibe capturas antes/después, salida de checks y acceso al código) → correcciones.

Nota ponderada = 0,4·Diseño + 0,3·Usabilidad + 0,2·Creatividad + 0,1·Contenido. Listón: ponderada ≥ 8,5 y ningún criterio < 8,0.

Capturas: `docs/estetica/capturas/<antes|vuelta1|…>/` (12 pantallas + paleta, 390/768/1440 px, oscuro y claro). `docs/` no entra en el ejecutable ni en la imagen Docker.

## Checks objetivos

| Check | Antes | Vuelta 1 |
|---|---|---|
| pytest | verde | verde |
| npm test (jsdom) | 30/30 | 30/30 |
| Errores/avisos de consola | 0 | 0 |
| Scroll horizontal 360–1920 | **sí** (Distribución, Rentabilidad, Evolución a 360/390) | no |
| axe WCAG 2 A/AA (nodos con fallo) | **1093** (843 de contraste) | 0 |
| Foco visible (30 tabulaciones) | OK | OK |
| Lighthouse escritorio — Rendimiento | 61 | 90 |
| Lighthouse escritorio — Accesibilidad | 92 | 100 |
| Lighthouse escritorio — Best Practices | 100 | 100 |
| Lighthouse escritorio — CLS | 0,975 | 0 |
| Lighthouse móvil — Rendimiento | 30 | 60 |
| Lighthouse móvil — Accesibilidad / BP | 92 / 100 | 100 / 100 |

Lighthouse: mediana de 3 ejecuciones (Lighthouse 12 + Chromium de Playwright, `--preset=desktop` y móvil por defecto), contra la versión original (commit `a47c1ec`, puerto aparte) y la rama, en la misma máquina. Primera visita (muestra la bienvenida).

Nota sobre la consola: en algunas ejecuciones aparece un error CORS de `api.coingecko.com` (precio de Bitcoin en vivo). Es la API externa limitando peticiones (responde sin cabecera CORS); ocurre igual en la versión original y no depende de esta rama.

## Vuelta 1 — veredicto del árbitro

| Diseño | Usabilidad | Creatividad | Contenido | **Ponderada** |
|---|---|---|---|---|
| 6,5 | 6,0 | 5,0 | 6,5 | **6,05** |

Defectos que señaló (resumen):

| # | Prioridad | Defecto | Evidencia |
|---|---|---|---|
| 1 | Bloqueante | Sub-pestañas del Panel en móvil/tableta: carril de 1044 px en 334 visibles; «Ingresos» e «Inmuebles» quedan ocultas (antes se veían todas). | `vuelta1/01-inicio_390_claro.jpg`, `08-inmuebles_768_claro.jpg` |
| 2 | Bloqueante | El contenido se oculta (`visibility:hidden`) hasta que pinta el JS; el LCP móvil empeora 9,1→9,9 s y, si el JS falla, 2,5 s en blanco. | `index.html` (`body > .env:not(.listo)`) |
| 3 | Mayor | Siguen emojis haciendo de icono: botones (✏️ Gestionar, ⚖️ Rebalancear, 🧪, ✎ Personalizar), banners (🏠), Ayuda (👋 🌐 🔗 ⬇ ▶ 💼). | `11-ayuda_1440_claro.jpg`, `08-inmuebles_768_claro.jpg` |
| 4 | Mayor | Animaciones de propiedades no permitidas: `transition:.13s` genéricas, `box-shadow` en hover, `width` en `.metaFill`, `left` en `cargaDesliza`, `box-shadow` en `calFlash`. | `index.html:81, 132, 150, 420, 1002, 1149, 1431…` |
| 5 | Mayor | Atajo «⌘K» en Windows. | barra superior |
| 6 | Mayor | Distribución: 17 tarjetas idénticas con borde de color (lo «genérico»). | `03-distribucion_1440_claro.jpg` |
| 7 | Mayor | Cifras de Inmuebles desalineadas a 768 (etiquetas en 2 líneas). | `08-inmuebles_768_claro.jpg` |
| 8 | Mayor | Paleta Ctrl+K: rectángulo fantasma detrás y el mismo icono en las 9 vistas. | `13-paleta_1440_claro.jpg` |
| 9 | Menor | Botón «i» en Georgia (tercera tipografía). | `index.html:1247` |
| 10 | Menor | Cuatro niveles de navegación con tres estilos en Ingresos. | `07-ingresos_1440_claro.jpg` |
| 11 | Menor | Verde de ingresos demasiado saturado en oscuro. | `01-inicio_1440_oscuro.jpg` |
| 12 | Menor | Rentabilidad en móvil: KPIs a media anchura, rango de fechas partido, tablas cortadas sin indicación. | `04-rentabilidad_390_oscuro.jpg` |
| 13 | Menor | Entrada escalonada demasiado larga (~1 s por cambio de vista). | `app.js` `fundeEntrada` |

También señaló: 19 radios distintos, ausencia de un «momento firma» (Creatividad 5).
