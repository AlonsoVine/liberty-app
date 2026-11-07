# Revisiones de la mejora estética

Cada vuelta: cambios → checks → capturas → **árbitro adversarial** (subagente independiente, contexto limpio, sin ver mi razonamiento; recibe capturas antes/después, salida de checks y acceso al código) → correcciones.

Nota ponderada = 0,4·Diseño + 0,3·Usabilidad + 0,2·Creatividad + 0,1·Contenido. Listón: ponderada ≥ 8,5 y ningún criterio < 8,0.

Capturas: `docs/estetica/capturas/<antes|vuelta1|…>/` (12 pantallas + paleta, 390/768/1440 px, oscuro y claro). `docs/` no entra en el ejecutable ni en la imagen Docker.

## Checks objetivos

| Check | Antes | Vuelta 1 | Vuelta 2 | Vuelta 3 | Vuelta 4 |
|---|---|---|---|---|---|
| pytest | verde | verde | verde | verde | verde |
| npm test (jsdom) | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 |
| Errores/avisos de consola | 0 | 0 | 0 propios (solo el CORS de CoinGecko, ver nota) | 0 propios | 0 propios |
| Scroll horizontal 360–1920 | **sí** (Distribución, Rentabilidad, Evolución a 360/390) | no | no | no | no |
| axe WCAG 2 A/AA (nodos con fallo) | **1093** (843 de contraste) | 0 | 0 | 0 | 0 (también en los diálogos de ayuda abiertos) |
| Foco visible (30 tabulaciones) | OK | OK | OK | OK (anillo opaco ≥ 3:1) | OK |
| Lighthouse escritorio — Rendimiento | 61 | 90 | 90 | 90 | 90 |
| Lighthouse escritorio — Accesibilidad | 92 | 100 | 100 | 100 | 100 |
| Lighthouse escritorio — Best Practices | 100 | 100 | 100 | 100 | 100 |
| Lighthouse escritorio — CLS | 0,975 | 0 | 0,001 | 0,001 | 0,001 |
| Lighthouse móvil — Rendimiento | 30 | 60 | 58 | 58 | 57 |
| Lighthouse móvil — Accesibilidad / BP | 92 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 |

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

### Qué se corrigió tras la vuelta 1

| # | Corrección |
|---|---|
| 1 | Sub-pestañas en móvil y tableta: chips en flujo, con las 9 visibles; la activa va en tinta sólida. |
| 2 | Se mantiene la ocultación hasta pintar; el razonamiento está en `DECISIONES.md` (el LCP es el diálogo de bienvenida, fuera de `.env`, y sin la ocultación vuelve el CLS de 0,97). Añadido `<noscript>`, red de seguridad a 2 s y fuera el preload de Fraunces. |
| 3 | Iconizador central con `MutationObserver`: ningún emoji hace de icono en botones, encabezados ni apartados, y no se toca el contenido del usuario. |
| 4 | Regla de sistema: solo se animan `transform` y `opacity`. El tema cambia con View Transitions, las sombras van en `::after`, y se corrigieron la barra de carga, el calendario y `metaFill`. |
| 5 | El atajo se muestra como «Ctrl K» o «⌘K» según la plataforma. |
| 6 | Distribución como libro de cuentas: filas con línea de peso, dos columnas y el anillo junto a su leyenda. |
| 7 | KPIs de Inmuebles alineados con subgrid. |
| 8 | Paleta: sin marco fantasma, centrada, con un icono propio por vista y la selección con contraste ≥ 5:1. |
| 9 | Botón «i» como icono de línea por máscara. |
| 10 | Navegación de Ingresos en píldoras. |
| 11 | `--bien` menos saturado en oscuro. |
| 12 | Rentabilidad en móvil: ventanas en 2 columnas, filtros y periodo en rejilla, y sombra de desplazamiento en las tablas. |
| 13 | Entrada escalonada de 0,3 s. |
| — | Radios normalizados a 4/8/12/16/20/pastilla. «Momento firma»: odómetro en las cifras protagonistas. |

Detectado y corregido en mis propias capturas antes de pasar el árbitro:
- El foco de `.lfCelda` y `.hudCell` quedaba anulado por la sombra nueva; restaurado.
- La paleta salía descentrada por `width:auto`.
- Los chips de sub-pestañas tenían una sangría rara.
- Los filtros se truncaban a 360 px.
- La fila de botones de Ayuda quedaba fuera de la columna.

## Vuelta 2 — veredicto del árbitro

| Diseño | Usabilidad | Creatividad | Contenido | **Ponderada** |
|---|---|---|---|---|
| 7,0 | 6,5 | 5,5 | 6,5 | **6,50** (+0,45) |

| # | Prioridad | Defecto | Evidencia |
|---|---|---|---|
| 1 | Bloqueante | El odómetro no se ve: Inicio se pinta dos veces (~100 ms) y la entrada «sube y baja» la opacidad; el de Cartera se gasta en segundo plano. | `app.js` odómetro y ensamblado de Inicio |
| 2 | Mayor | Anillo de foco en claro < 3:1 (`--s1` al 65 %). | `index.html:66` |
| 3 | Mayor | Móvil: ~3 pantallas antes del primer dato; la «i» suelta entre las filas de pestañas. | `01-inicio_390_claro.jpg` |
| 4 | Mayor | Dos verdes para «ingresos» (series en `--s6 #008300`, cifras en `--bien`). | `07-ingresos_1440_oscuro.jpg` |
| 5 | Mayor | Inicio repite tres rejillas de baldosas iguales. | `01-inicio_1440_oscuro.jpg` |
| 6 | Menor | Distribución: el anillo flota en una columna ancha. | `03-distribucion_1440_claro.jpg` |
| 7 | Menor | Inmuebles a 768: hueco en la rejilla 4+3. | `08-inmuebles_768_claro.jpg` |
| 8 | Menor | Trazado de líneas con `stroke-dashoffset` anulado (código muerto). | `graficos.js:108` |
| 9 | Menor | Durante el odómetro los dígitos están en `visibility:hidden` (el lector de pantalla no lee la cifra). | `index.html` `.odoD` |
| — | Contenido | «2.1 años» con punto; «+59.933,19 €» con céntimos; «⬇» en el texto de Ayuda. | `app.js:3158`, `index.html:2553` |

### Qué se corrigió tras la vuelta 2

| # | Corrección |
|---|---|
| 1 | Causa del doble pintado: el precio en vivo de Bitcoin llega a los ~150 ms y repinta la vista. Ahora el odómetro guarda cuándo empezó y, si la vista se repinta a mitad, el nodo nuevo **continúa** el giro con un retardo negativo. Solo arranca con la cifra pintada y a la vista (`IntersectionObserver`), así que el de Cartera gira al abrir Cartera. La entrada escalonada hace lo mismo con un `MutationObserver` durante su ventana. Fuera el «ensamblado» propio de Inicio, que la duplicaba. Medido: la opacidad sube de forma monótona y los dígitos giran (`translateY` de 0 a −132 px). |
| 2 | Anillo de foco opaco en `--s1` (≥ 3:1 en claro y oscuro). |
| 3 | Móvil: chips más compactos, la «i» arriba a la derecha de las pestañas, aviso legal en 11 px, filas de avisos más bajas y «Ver →» reducido a la flecha (la fila entera es el botón). |
| 4 | Token `--ingreso` (= `--bien`) en todas las series de ingresos; `--s6` queda para la paleta categórica, porque igualarlo chocaría con `--s3`. |
| 5 | Inicio con tres ritmos: baldosas en «Tu cartera», estado de cuentas en filas en «Ingresos y gastos» y «Tus inmuebles», y tira de indicadores con filetes en «Tu constancia». |
| 6 | Distribución: el anillo y su leyenda, centrados juntos. |
| 7 | Inmuebles: 4 columnas con la última cifra ocupando el hueco (2 columnas en móvil). |
| 8 | El trazado de líneas pasa a un fundido de opacidad real. |
| 9 | Dígitos con `-webkit-text-fill-color:transparent` en vez de `visibility:hidden`: la cifra sigue en el árbol de accesibilidad. |
| — | «2,1 años» con formato español; variación desde el inicio sin céntimos; Ayuda sin «⬇». |

No se cambia:
- «8052 €» sin separador de miles: es la norma española (RAE/Intl `es-ES`: sin separador en números de 4 cifras).
- Los 0 € del mes actual: son datos del ejemplo y el mes acaba de empezar.

Detectado y corregido en mis capturas: en móvil, la rejilla de filtros anulaba su ocultación en Inicio.

## Vuelta 3 — veredicto del árbitro

| Diseño | Usabilidad | Creatividad | Contenido | **Ponderada** |
|---|---|---|---|---|
| 7,5 | 7,5 | 6,5 | 7,5 | **7,30** (+0,80) |

| # | Prioridad | Defecto | Evidencia |
|---|---|---|---|
| 1 | Bloqueante | Los diálogos de ayuda («i») muestran emojis como icono (33 sin equivalente: 🍩 🏷️ 👆 💎 🏅…). | `app.js` `.novIco`; `arbitro3/ayuda_Dist.png` |
| 2 | Mayor | Emoji en el texto de Cartera (👆) y «🖨 Imprimir» en un párrafo. | `app.js:969`, `index.html:2569` |
| 3 | Mayor | Cartera: 6 KPI + 8 cifras en tarjetas idénticas. | `02-cartera_1440_oscuro.jpg` |
| 4 | Mayor | El odómetro arranca con un fotograma «000 000» sin separador ni €. | `index.html` `.odoS` |
| 5 | Mayor | Marco fantasma en los diálogos de ayuda y novedades (también en el original). | `index.html:919` |
| 6 | Menor | Guion en lugar de signo menos; punto de miles pegado en la cifra grande. | formateador, `.hCifra` |
| 7 | Menor | «+0,00 €» en verde. | `02-cartera` |
| 8 | Menor | Rango de fechas partido a 768 px. | `03-distribucion_768_claro.jpg` |
| 9 | Menor | Verdes del tema claro demasiado oscuros para rellenar barras. | `01-inicio_1440_claro.jpg` |
| 10 | Menor | `@keyframes faroAterriza` duplicado con `box-shadow` (muerto). | `index.html:612` |

### Qué se corrigió tras la vuelta 3

| # | Corrección |
|---|---|
| 1 | 17 iconos de línea nuevos (dona, etiqueta, medalla, diamante, personas, disquete, calculadora…) y los 27 emojis que faltaban, mapeados. Los iconos de las listas de ayuda y novedades pasan por `ico()` en una ficha tonal; si un emoji no tuviera equivalente, no se muestra. Comprobado en vivo: 5/5 SVG en el diálogo de Distribución. |
| 2 | 👆 → icono de flecha; «🖨 Imprimir» en el texto → «Imprimir». |
| 3 | Los 6 indicadores pasan a una franja con filetes (sin cajas). «Tu cartera hoy» pasa a ser **dos cuentas de libro**: `bruta − deudas = neta` y `disponible − reservados − colchón = libre`, con operadores, filete de total y cifra mayor en los resultados. «No disponible» queda como nota. |
| 4 | Separadores y € visibles desde el primer fotograma del odómetro. |
| 5 | `dialog.novedades` sin el marco heredado (`box-shadow:none; width:fit-content`). |
| 6 | Signo menos tipográfico (U+2212) en todos los formateadores de importes y porcentajes; tracking de la cifra protagonista de −0,045 a −0,03 em. |
| 7 | Las variaciones nulas se muestran neutras y sin signo («0,00 €», «0 €»). |
| 8 | «desde → hasta · Ver» agrupados sin partirse (en móvil siguen en su rejilla). |
| 9 | `--ingreso` en claro: `#2b9a5b` (≥ 3:1 sobre las superficies, al nivel del coral de gastos). |
| 10 | Eliminado el keyframe muerto. |
| — | Pastilla «Cómo funciona esta pantalla»: blanco sobre el verde `--s3` daba < 4,5:1; ahora `--s3` oscurecido (≥ 6,4:1). Pastilla de versión de novedades sobre `--acento-fondo`. |

Detectado en mis capturas y corregido antes del árbitro:
- La regla de subgrid de los KPI ponía la nota encima de la etiqueta en «Tu cartera hoy».
- La opacidad de «No disponible» bajaba el contraste a 4,43:1 en claro (axe).
