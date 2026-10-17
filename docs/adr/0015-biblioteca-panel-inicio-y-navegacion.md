# ADR 0015 — Biblioteca de documentos, panel de inicio y mejoras de navegación

- **Estado:** aceptado
- **Fecha:** 2026-10-18
- **Fase:** mejoras post-F4 (batería de UX de octubre)

## Contexto

Batería de ocho mejoras pedidas por el usuario (notas de voz), orientadas a hacer la app
más completa y fácil de recorrer ahora que convive la gestión de activos con la de ingresos
y gastos. Van juntas en la versión **1.10.0**.

## Decisiones

**1. Biblioteca de documentos (Notas → Biblioteca).** Un gestor de archivos sencillo e
integrado, 100 % local, para guardar documentos importantes (Hacienda, escrituras,
contratos…) en carpetas anidadas que crea el usuario.
- **Modelo:** `cfg["biblioteca"] = {carpetas:[{id,nombre,padre}], archivos:[{id,nombre,
  carpeta,archivo,tipo,tam,fecha}]}`. Los ficheros viven en `biblioteca/` dentro de la
  cartera (como las facturas en `adjuntos/`); la cartera solo guarda la referencia.
- **API:** `/api/biblioteca/{carpeta,renombra,mover,carpeta-borra,borrar,subir}` y
  `GET /api/biblioteca/archivo/<id>` (inline, o `?descargar=1`). Se admite **cualquier tipo**
  de archivo, hasta 50 MB. Validaciones en `almacen` (nombres, anidamiento ≤ 10, no mover
  una carpeta dentro de sí misma, borrado recursivo). No recalcula el panel (como notas);
  el front marca `EDITOR_SUCIO` para refrescar los contadores.
- **Backup:** el `.zip` de copia incluye `biblioteca/` y la restauración la repone (export e
  import, cartera nueva o sustituir).

**2. Ayuda y Ajustes a la esquina superior derecha.** Dejan de ser pestañas y pasan a ser
dos botones-icono (`❓`/`⚙️`, nombre por `title` al pasar el ratón) junto a «Actualizar
precios». La selección de pestaña se generaliza a cualquier `[data-tab]` (no solo
`#tabs button`).

**3. Volver atrás desde la ficha de un componente.** La vista de producto estrena un botón
«← Volver a Distribución».

**4. Gráfico de deudas en su ficha (regresión).** La serie de una deuda es negativa; con el
eje anclado en 0 (`desdeCero`) la escala colapsaba (`escalaBonita(maxNeg, 0)` → `{0,1}`) y la
curva se salía. Ahora, si la serie tiene valores negativos, el eje se adapta
(`desdeCero:false`).

**5. Buscador (⌘K): Ayuda y Ajustes primero.** Se anclan como las dos primeras entradas de
la paleta de acciones.

**6. Panel de inicio.** Nueva primera sub-pestaña «Inicio»: un resumen de un vistazo
(patrimonio neto, activos/deudas, dinero libre, ingresos/gastos del mes, nº de facturas,
documentos, apuntes, avisos y vencimientos) con tarjetas que enlazan a cada sección. El
motor expone un bloque `conteos` para alimentarlo. Pasa a ser la vista por defecto del Panel
(las carteras con vista guardada conservan la suya). Atajos de teclado 1–8.

**7. Tarjeta de novedades.** Un modal que se muestra **una vez por versión** cuando ya hay
datos (modo propio con productos) y la versión instalada coincide con la de las novedades y
no se ha visto aún (`patrimonio.novedadesVistas` en `localStorage`).

**8. Listas de aportaciones enlazadas.** En la ficha de un componente, cada fila de
«Aportaciones» lleva al movimiento concreto en «Saldos y movimientos» (resaltado + scroll),
igual que «Ver apunte» en Facturas. El motor añade `movId` (id del movimiento de origen) a
cada aportación; `Editor.irAMovimiento(movId, prodId)` navega y resalta.

## Retrocompatibilidad

Todo aditivo. Carteras sin `biblioteca` funcionan igual (se crea al primer uso). El cambio de
vista por defecto a «Inicio» solo afecta a quien no tenga una vista guardada.

## Tests

- `test_biblioteca.py`: unidad de `almacen` (crear/anidar/mover/borrado recursivo) y e2e del
  servidor (crear carpeta, subir, servir, renombrar, mover, borrar) y ciclo zip export/import.
- `test_construir_offline.py`: `conteos` del panel y `movId` en las aportaciones.
- jsdom: la sub-pestaña «Inicio» se dibuja sin errores; selector de Ajustes actualizado.
- CDP: Inicio por defecto, botones Ayuda/Ajustes arriba, volver desde la ficha, filas de
  aportación clicables, eje de deuda adaptado, Biblioteca renderizada, paleta con Ayuda/Ajustes
  primero. Consola sin errores.
