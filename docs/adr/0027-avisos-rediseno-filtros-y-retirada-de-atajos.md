# ADR 0027 — Rediseño de la caja de avisos, arreglo de los filtros de Ingresos y gastos y retirada de los atajos de una tecla

- **Estado:** aceptado
- **Fecha:** 2026-10-31
- **Fase:** mantenimiento y pulido de UX (versión 1.16.1)

## Contexto

Tras publicar la 1.16.0 (Docker, ADR 0026), Alonso reportó tres asuntos concretos de interfaz,
todos en el front (sin tocar el motor): la flecha del desplegable de avisos le parecía poco
elegante; los filtros de Ingresos y gastos fallaban al filtrar «Sin categoría» y al volver a
«Todas»; y el selector de fecha de esos filtros no dejaba escribir el año (el foco saltaba). A
raíz del tercero, pidió además **eliminar por completo los atajos de teclado de una sola tecla**,
sin dejar siquiera la opción de desactivarlos en Ajustes.

## Decisiones

**A. Rediseño de la caja de avisos (`app.js` `pintaAlertas`, `index.html`).** La cabecera plegable
estrena un **chevron SVG de trazo fino** (mismo grosor que las flechas del resto de la app) en
lugar del carácter `⌄`, que giran con una transición al plegar/desplegar. La caja pasa a ser una
**tarjeta real** (`borde`, `radius`, fondo `--sup2`, `overflow:hidden`) con los avisos como
**filas planas** dentro (acento rojo con `box-shadow:inset`), y un envoltorio `.avisosListaIn`
para la animación de altura (`grid-template-rows 1fr⇄0fr`). En «Mis datos» el aviso suelto sigue
siendo tarjeta independiente.

**B. Arreglo del filtro «Sin categoría» (`editor.js`).** Causa raíz: el centinela que marcaba
«sin categoría» en el `value` del `<option>` era `"\u0000sincat"`, y el parser de HTML sustituye
`U+0000` por `U+FFFD`, dejando el valor corrupto y la comparación siempre a falso (por eso ni
filtraba ni se marcaba «Todas» de vuelta). Se cambia el centinela a `"__sincat__"` (texto plano) y
se **sanea** en `filtrosFlujos()` el valor viejo roto que pudiera quedar en `localStorage`.

**C. Selector de fecha que deja escribir el año (`editor.js`, `app.js`).** Un `<input type=date>`
dispara `change` en cada dígito del año (cada fecha parcial es válida), y `refrescaFlujos()` /
`refrescaIg()` reconstruían la tabla —y con ella el propio input— al cruzar la frontera 0⇄N filas,
lo que tiraba el foco al `body`. Se añade un **debounce de 450 ms** a los filtros de tipo fecha e
importe (en `montaFiltrosFlujos` y en `pintaIgPeriodo`), de modo que la tabla no se reconstruye en
mitad del tecleo. (El salto a Patrimonio que además ocurría se resuelve en el punto D.)

**D. Retirada completa de los atajos de una sola tecla (`app.js`, `index.html`, `docs`).** Se
eliminan los atajos de una pulsación (`1`–`8` vistas, `V` vídeo, `L` largo plazo, `?` la lista),
su diálogo de ayuda, el comando de la paleta, la preferencia `patrimonio.atajos` /`window.ATAJOS`
y su interruptor en Ajustes. El manejador global de teclado conserva únicamente las dos
combinaciones deliberadas que no se pulsan sin querer y que ya se ignoraban al escribir en un
campo: **Ctrl/⌘+K** (paleta de acciones) y **Esc** (quitar el filtro). Esto **revierte el punto D
del ADR 0025** (el interruptor de atajos): la causa de fondo —teclas sueltas que capturan la
pulsación— se elimina en vez de hacerla opcional.

## Botón «i» (ADR 0020)

Se retira la tarjeta de ayuda «⌨️ Atajos de teclado» de Ajustes y la mención «también con la
tecla V» de «Vista amplia y Modo vídeo»; se actualizan el FAQ de la Ayuda (solo quedan Ctrl/⌘+K y
Esc), el texto del tour y `docs/arquitectura.md`. No se tocan ADR ni CHANGELOG antiguos (quedan
como histórico); la 1.16.1 lo recoge en su entrada del CHANGELOG y en la card de novedades.

## Retrocompatibilidad

Todo aditivo o de presentación; las carteras no cambian de datos. La preferencia
`patrimonio.atajos` que pudiera quedar en el navegador es dato muerto inofensivo (ya no se lee).
El centinela `"__sincat__"` se sanea desde el valor antiguo corrupto, así que un filtro guardado
no rompe.

## Tests

`node --check` de `app.js` y `editor.js` (OK), `npm test` 14/14 (OK), `pytest` 259 (OK) y
verificación en vivo por CDP: filtro «Sin categoría» → apuntes correctos, «Todas» recarga bien, el
año se teclea entero sin saltar, `window.ATAJOS`/`muestraAtajos` ya no existen, pulsar `2`/`1`/`V`
con el foco fuera de un campo no hace nada y **Ctrl+K** sigue abriendo la paleta.
