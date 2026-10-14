# ADR 0014 — Recordatorios separados (activos/deudas vs ingresos/gastos) y mejoras del tablero

- **Estado:** aceptado
- **Fecha:** 2026-10-15
- **Fase:** mejoras post-F4 (avisos y tablero)

## Contexto

En Configuración, el «Recordatorio sin anotar» (umbral `diasSinAnotar`) estaba bajo
«Ingresos y gastos», pero su aviso `sin-anotar` miraba en realidad la fecha más reciente
entre **movimientos, valoraciones Y flujos** a la vez: era un recordatorio global, mal
ubicado. El usuario pidió separarlo y poder fijar **plazos distintos** para el día a día de
ingresos/gastos y para la actualización de activos/deudas. Además, en el tablero tipo Trello
se podían reordenar las tarjetas pero **no las columnas**.

## Decisión

**1. Dos recordatorios independientes.** El aviso único se divide en dos, cada uno con su
umbral:

- **`sin-anotar`** (umbral `diasSinAnotar`, por defecto 30): mira solo los **flujos**
  (ingresos y gastos). Texto: «Hace N días que no anotas ningún ingreso ni gasto.». Vive en
  la pestaña «Ingresos y gastos» de Configuración. `pv="ingresos"` (la alerta salta a esa vista).
- **`sin-actualizar`** (umbral `diasSinActualizar`, por defecto 90): mira **movimientos +
  valoraciones** (saldos y movimientos de activos y deudas). Texto: «Hace N días que no
  actualizas tus activos ni deudas (saldos y movimientos).». Vive en «Activos e inversiones».
  `pv="patrimonio"`.

Ambos se calculan con el mismo helper (`_recuerda`) y se silencian en la vista «a fin de un
mes pasado» (`hasta`). `diasSinActualizar` se añade a `CARTERA_VACIA`, se valida en
`guarda_config` (entero ≥ 0, respeta el 0 = avisar siempre) y aparece en el catálogo de
avisos (centro de avisos) y en la vista de lectura de Configuración.

**2. Tablero: reordenar columnas + pulidos.**

- **Reordenar columnas** arrastrando el asa `⠿` del encabezado (`.kGrip`, `draggable`). El
  arrastre de tarjetas y el de columnas conviven con guardas: la tarjeta fija `dragId` (y
  anula `dragColId`) y el asa al revés; las zonas de tarjetas (`.kCards`) solo aceptan si hay
  `dragId`, y el tablero (`.kBoard`) solo reordena columnas si hay `dragColId`. El orden es
  el del array `columnas`, que el backend ya respeta.
- **Alta y renombrado de columnas inline** (sin `prompt()`): un input que confirma con
  Enter/blur y cancela con Escape (`inlineEdita`).
- **Columna vacía** muestra un marcador «Suelta tarjetas aquí» y sigue siendo zona de drop.

## Retrocompatibilidad

- Carteras sin `diasSinActualizar` usan el defecto 90. El cambio de comportamiento es el
  pretendido: los activos/deudas antiguos dejan de avisar a los 30 días (ahora a los 90,
  configurable) y los ingresos/gastos mantienen su propio plazo.
- El tablero no cambia su modelo de datos (columnas con `id`/`nombre`, orden = array).

## Tests

- Motor: `test_recordatorio_sin_actualizar_activos` y `test_recordatorio_sin_anotar_flujos`
  (cada aviso con su umbral, de forma independiente); config `test_config_dias_sin_actualizar`.
- CDP: campo en el panel correcto, guardado de ida y vuelta, switches de ambos avisos;
  tablero: reordenar columnas (persistido), alta/renombrado inline, marcador de columna vacía
  y arrastre de tarjetas intacto.
