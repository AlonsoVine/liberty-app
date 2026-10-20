# ADR 0018 — Notas documentales, agenda navegable y pulido de tablas

- **Estado:** aceptado
- **Fecha:** 2026-10-20
- **Fase:** madurez de UX (versión 1.12.0)

## Contexto

Tanda de mejoras pedidas por el usuario para dar más potencia y navegabilidad al
«espacio libre» (notas, agenda) y a las tablas de datos, sin tocar las cifras del panel.
Todo aditivo y retrocompatible.

## Decisiones

**1. Notas más documentales (`almacen.guarda_notas`, `editor.js`).** Una nota pasa de tener
un único `vinculo` a una lista `vinculos: [{tipo, ref}]` (varios activos/deudas/reservados) y
estrena `archivos: [{tipo, id}]` (documentos de la biblioteca: `archivo` sueltos o una
`carpeta` entera, que representa «todo lo que contenga» y se resuelve al mostrarla, no se
congela). También `color` (misma paleta corta que el tablero: `s2/s6/s8/s11/s14`).
Retrocompatibilidad: el `vinculo` único antiguo se migra a `vinculos` al leer, y se sigue
escribiendo `vinculo = vinculos[0]` para que los indicadores «📝» y el filtro «notas de esta
entidad» (que ya existían) no se enteren del cambio. Sin duplicados y con topes (≤20 vínculos,
≤40 adjuntos). En el front: formulario con chips para añadir/quitar vínculos y documentos,
selector de color, y el **pin de fijar arriba a la derecha** (como fuera); en la tarjeta de la
lista, iconos estándar **editar / duplicar / borrar**, borde de color, y los chips de
**activos / documentos / etiquetas en líneas separadas** (son conceptos distintos). Los chips de
activo navegan a su ficha; los de archivo abren/descargan; los de carpeta abren la Biblioteca
ya posicionada en ella.

**2. Agenda navegable (`motor.py`, `editor.js`).** Cada vencimiento que calcula el motor lleva
ahora su origen: `ref` (id del producto/apartado) y `origen` (`activo`/`deuda`/`reservado`). En
la agenda (lista y calendario) los vencimientos y las tarjetas del tablero dejan de ser
informativos y **llevan a su ficha** en «Mis datos» con el registro **resaltado**
(`Editor.irAEntidad`, que resalta la fila `fila-prod-<id>` / `fila-ap-<id>`). Los recordatorios
propios se siguen editando desde ambos modos.

**3. Filtro «Sin categoría» (`editor.js`).** El filtro de categoría de «Ingresos y gastos»
ofrece «— Sin categoría —» (valor centinela interno) cuando hay apuntes sin categoría, para
aislarlos y clasificarlos.

**4. Pulido de tablas (`editor.js`).** La tabla de «Ingresos y gastos» pasa a tener altura
acotada con scroll y **cabeceras fijas** (como ya tenía Movimientos: clase `.tablaEnv.alto`).
Todas las tablas que usan `envTabla` muestran un **pie discreto con el nº de registros**
(`N registros`, o `N de M` cuando la búsqueda deja fuera algunos), que vive fuera del área con
scroll y se recalcula al buscar/ordenar.

## Retrocompatibilidad

Todo aditivo. Carteras sin `vinculos`/`archivos`/`color` en sus notas funcionan igual (el
`vinculo` único se migra solo). Las cifras del panel no cambian; `vencimientos` solo gana campos.

## Tests

pytest con casos nuevos de `guarda_notas` (color validado contra la paleta, varios vínculos sin
duplicados con migración del `vinculo` único, adjuntos archivo/carpeta). `ruff`, 14 jsdom,
`node --check` y verificación visual por CDP (notas, formulario de nota, agenda con navegación a
ficha resaltada, «Ingresos y gastos» con cabeceras fijas y pie de registros, filtro «Sin
categoría»).
