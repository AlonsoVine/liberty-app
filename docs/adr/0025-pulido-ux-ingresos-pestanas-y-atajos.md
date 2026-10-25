# ADR 0025 — Pulido de UX: filtros de Ingresos y gastos, agrupación de pestañas y atajos opcionales

- **Estado:** aceptado
- **Fecha:** 2026-10-25
- **Fase:** madurez de UX (versión 1.15.0, segunda tanda)

## Contexto

Tras cerrar la primera tanda de la 1.15.0 (ADR 0024), Alonso pidió una segunda ronda de pulido
de interfaz, centrada en que cada pantalla «respire» y en reconocer que dentro de la app conviven
en realidad **dos aplicaciones**: la de patrimonio e inversiones y la de ingresos y gastos del
hogar. Cuatro ajustes concretos (A–D), todos de interfaz, sin tocar el motor.

## Decisiones

**A. Filtro de Ingresos y gastos en una sola línea (`index.html`, `app.js`).** El selector
«Filtrar apuntes» estaba en una fila aparte del control de periodo/rango. Se envuelven ambos en
un contenedor `.igControles` (flex, `align-items:center`, `gap`) para que periodo y filtro
compartan línea y la vista ocupe menos alto.

**B. Sin dimensiones de activo en el filtro de Ingresos y gastos (`app.js`,
`pintaFiltroTitular`).** La fila de filtros superior mostraba, además del titular, los filtros de
**clase de activo** y **geografía**, que no tienen sentido para apuntes de caja (nunca afectaban a
la lista de flujos, que se filtra por `estado.igDim`, no por `estado.filtroDim`). En la vista de
Ingresos y gastos (`estado.pv === "ingresos"`) se ocultan esas dimensiones y queda solo el filtro
por **titular**. En el resto del panel se mantienen.

**C. Pestañas del panel agrupadas por tema (`index.html`, `app.js`, `editor.js`).** Las subpestañas
del panel se reorganizan en tres grupos visuales segmentados (estilo «Mis datos»), sin etiquetas
de texto: **Inicio** · **(Patrimonio · Distribución · Rentabilidad · Evolución · Deudas · Fiscal)**
· **Ingresos y gastos**. CSS `.subtabs`/`.pvGrupo`/`.segm` con el botón activo resaltado. Se
reagrupa también «Mis datos» en coherencia: **(Activos · Deudas · Reservados · Saldos y
movimientos)** · **(Ingresos y gastos · Facturas)** · **(Configuración · Importar · Copias y
seguridad)**. El atajo numérico de teclado se reordena al orden visual nuevo (1–8).

**D. Interruptor de atajos de teclado (`app.js`, `pintaAjustes`, `aplicaPrefs`).** Nueva
preferencia `patrimonio.atajos` (por defecto activada) → `window.ATAJOS`. Con ella desactivada, las
teclas de una sola pulsación (1–8 para las vistas, `V` vídeo, `L` largo plazo, `?` la lista) dejan
de actuar, para quien las pulsa sin querer. **Escape** (limpiar filtro) y la **paleta Ctrl/⌘+K**
siguen funcionando siempre. La fila se añade a Ajustes y el modal de atajos / el tour reflejan el
nuevo orden y la opción de desactivarlos.

## Botón «i» (ADR 0020)

Se actualizan las tarjetas de ayuda contextual afectadas: `panel.ingresos` (periodo + filtro solo
por titular), `ajustes` (nuevo punto «⌨️ Atajos de teclado»), y los textos del tour/modal de
atajos con el orden nuevo.

## Retrocompatibilidad

Todo aditivo y de presentación. Las carteras existentes no cambian de datos. Quien no toque Ajustes
conserva los atajos activados. La reagrupación de pestañas no altera rutas ni estado (`estado.pv`
y `estado.tab` siguen igual); solo cambia su disposición visual.

## Tests

`ruff` (OK), `node --check` de los tres JS (OK), `npm test` 14/14 (OK), `pytest` 244 (OK), y
verificación en vivo por CDP: filtro y periodo en una línea, dimensiones de activo ausentes en
Ingresos y gastos, pestañas agrupadas y activas, y el interruptor de atajos (ON: la tecla cambia de
vista; OFF: no; Ctrl+K sigue abriendo la paleta).
