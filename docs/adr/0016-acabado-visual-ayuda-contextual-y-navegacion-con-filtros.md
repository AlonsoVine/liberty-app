# ADR 0016 — Acabado visual, ayuda contextual y navegación con filtros

- **Estado:** aceptado
- **Fecha:** 2026-10-19
- **Fase:** madurez de UX (versiones 1.11.0 → 1.11.2)

## Contexto

Con la app ya completa en funcionalidad, una tanda de mejoras para que se vea profesional y se
entienda sin fricción, sin añadir conceptos de datos nuevos. Todo aditivo, respetando
`prefers-reduced-motion` y el export estático (web compartida).

## Decisiones

**1. Correcciones del análisis (1.11.0).** Auditoría de errores/incongruencias. Lo relevante en
arquitectura: el motor guarda su estado en variables de módulo (`CACHE`/`SIN_RED`/`SOLO_FALTAN`/
`AVISOS`) y **no es reentrante**; se serializa **todo** el acceso al motor bajo `cerrojo` en el
servidor (también la previsualización de importación y `valida_copia`, que antes quedaban fuera y
podían pisar el estado con `threaded=True`). Además: valoraciones con fecha futura se ignoran en
el motor; el export «ocultar importes» no escala la tasa de ahorro (es un ratio); arreglo de
huérfanos al subir una carpeta si una ruta falla a medias; doble escapado en Inicio; `aro()` con
`textContent` en vez de `innerHTML`.

**2. Acabado visual (1.11.0).** Tokens de movimiento (`--dur-1/2/3`, `--ease`, `--sombra`) y un
`@media (prefers-reduced-motion:reduce)` global, con `window.SIN_MOV` para el JS. Los gráficos se
animan **solo en su 1.ª aparición** por carga (línea con `stroke-dashoffset`, donut por sectores,
barras desde la base), controlado por id de contenedor y saltando el export estático. Contador
ascendente en las cifras grandes. **«Faro»** en la barra de objetivo: se rellena desde 0 y un
resplandor aterriza en la punta al llegar (clases `.conFaro`/`.aterriza`, carril `overflow:visible`).
Microinteracciones (hover/press), foco de teclado visible (`:focus-visible` global), crossfade de
tema, barras de desplazamiento y selección acordes al tema, y barra de carga superior.

**3. Ayuda contextual (1.11.2).** Una **«i»** al final de la barra de navegación de cada zona abre
una tarjeta (modal, reutiliza el de novedades) que explica **esa** pantalla. Registro `AYUDA` en
`app.js` (~23 entradas, concretas y con ejemplos: dimensiones, reglas del banco, titular por
defecto, rebalanceo, FIFO…); la clave se deduce del estado (`estado.tab`/`pv` y `localStorage`),
sin acoplarse al editor. Se ocultan desde Ajustes (pref `patrimonio.ayudaBotones` → `body.ayudaOff`)
y en el export estático. Los iconitos de info antiguos (helper `info()` en `app.js` y `editor.js`)
se unificaron con ese estilo (`.info` = círculo serif cursiva) y estrenan un **popover propio**
(`#infoPop`) que se muestra en hover **y al pulsar** (fijado hasta pulsar fuera o Esc), delegado en
`window` (captura para el clic, para no disparar la fila/botón donde esté el icono).

**4. Navegación con filtros (1.11.1).** Los diagramas llevan a los datos **ya filtrados**: el donut
de categorías de «Ingresos y gastos» → «Mis datos → Ingresos y gastos» por categoría + tipo
(`Editor.verFlujosCategoria`); el donut de «Distribución» → «Saldos y movimientos» por producto, o
por **grupo** (se pasan los **ids** de los productos del sector, para no depender del reetiquetado
de `tipo`/`clase` que hace el motor para el panel; `Editor.verMovimientos`). Barra de filtros
potenciada en Movimientos (`E.movFiltros`: producto, operación, entidad, dimensiones, importe,
fechas, limpiar). «N movs./valores» de Activos/Deudas enlaza a sus registros (`irARegistros`);
botón «Anotar saldo» en las fichas de productos a mano (`Editor.nuevoValor`).

**5. Arreglo del tooltip de gráficos.** El tooltip (`.gtt`) es `position:absolute` y se coloca por
coordenadas **del contenedor**; si el contenedor no era un ancestro posicionado se anclaba a uno
lejano (aparecía sobre los avisos). `creaTooltip` fuerza `position:relative` en el contenedor.

## Retrocompatibilidad

Todo aditivo. Los filtros nuevos se guardan en `localStorage` y conviven con los saltos desde el
panel. El donut de Distribución pasa a llevar a movimientos (antes abría la ficha); las fichas
siguen accesibles por las tarjetas de «Componentes de la cartera» y el treemap.

## Tests

pytest (nuevos: export que no escala la tasa de ahorro, y valoración con fecha futura), 14 jsdom,
`ruff`, `node --check` y verificación visual por CDP (dark/light) en cada tanda.
