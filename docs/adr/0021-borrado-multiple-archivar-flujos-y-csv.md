# ADR 0021 — Borrado múltiple, archivar/borrar por fecha en Ingresos y gastos y CSV compatible

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Fase:** madurez de UX (versión 1.14.0, segunda tanda)

## Contexto

Pulido de la entrada de datos pedido por Alonso para la misma 1.14.0: al borrar apuntes o
movimientos la lista saltaba al principio (molesto para borrar varios seguidos); hacía falta
borrar en lote; a principio de año se quiere «dejar la lista solo con lo reciente»; y el CSV no
se importaba en Excel/Android por el signo negativo.

## Decisiones

**1. El borrado no pierde el sitio (`editor.js`).** `borrarFlujo` y `borrarMov` usan
`pintaScroll()` (re-render conservando `window.scrollY`) en vez de `pinta()`, para poder seguir
borrando sin volver al principio.

**2. Selección múltiple opt-in (`editor.js`, `almacen.py`, `servidor.py`).** Junto al botón de
CSV aparece **«☑ Seleccionar»**; al activarlo, una casilla por fila y **«🗑 Borrar (N)»**. No
ocupa sitio cuando está apagado. Estado en `E.selModo` (`flujos`|`movimientos`) y `E.selIds`.
Endpoints `POST /api/flujos-borrar` y `POST /api/movimientos-borrar` (`almacen.borra_flujos` /
`borra_movimientos`). Las facturas de los apuntes borrados **se conservan** (igual que en el
borrado individual).

**3. Archivar / borrar por fecha, solo Ingresos y gastos (`editor.js`, `almacen.py`,
`servidor.py`).** Botón **«🗄 Archivar / borrar…»** → modal con una fecha y tres acciones sobre
los apuntes con fecha ≤ esa: **archivar** (`flujo.archivado=true`: los oculta de la lista, es
**reversible**; `guarda_flujo` conserva el flag al editar), **desarchivar** o **borrar** para
siempre. Un interruptor **«Ver archivados (N)»** los muestra cuando interese. Endpoint
`POST /api/flujos-masa` (`accion` = archivar|desarchivar|borrar). **Decisión:** archivar solo
declutra la **lista de datos** por defecto; los apuntes archivados **siguen contando en el
panel**, pero es **configurable**: `config.archivadosEnPanel` (por defecto `true`). Si se
desactiva (Configuración → Ingresos y gastos), el motor excluye los archivados de la sección
Ingresos y gastos del panel (y de la tasa de ahorro), filtrando `flujos_cfg` una sola vez, y el
panel muestra un aviso de transparencia («Este panel no incluye N apuntes archivados», vía
`D.flujos.archivadosFuera`). En Movimientos **no** hay borrado por fecha: ahí se mantiene la
historia.

**4. CSV compatible con Excel/Android (`editor.js`).** `descargaTablaCSV` sustituye el signo
«menos real» (U+2212) por el guion ASCII «-», que es el que entienden Excel y las hojas de
cálculo de Android.

## Retrocompatibilidad

Aditivo. Apuntes sin `archivado` y carteras existentes funcionan igual. `_al` ya admitía campos
opcionales; los endpoints nuevos no alteran los existentes. El borrado en lote reutiliza la
conservación de facturas del borrado individual.

## Tests

`pytest`: `borra_flujos` / `borra_movimientos`, `archiva_flujos` (archivar/desarchivar por
fecha), conservación de `archivado` al editar, y `borra_flujos_hasta`. `ruff`, `node --check`,
14 jsdom y verificación visual por CDP (selección múltiple, modal de archivar, «Ver archivados»,
scroll que no salta, CSV con «-»).
