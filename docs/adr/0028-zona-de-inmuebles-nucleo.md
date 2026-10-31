# ADR 0028 — Zona de Inmuebles: núcleo (fichas, valor, hipoteca y vista del Panel)

- **Estado:** aceptado (en la rama `inmuebles`; se integrará en `main` con la release que la cierre)
- **Fecha:** 2026-10-31
- **Fase:** F6 · Inmuebles — iteración 1 de 5 (ver [diseño](../diseno-inmuebles.md))

## Contexto

Hasta ahora un inmueble solo podía ser un activo más de la cartera (`tipo: "inmueble"`). Eso
tiene dos problemas que Alonso señaló: **descuadra los gráficos** (un piso pesa tanto frente a
fondos y cuentas que aplasta los donuts; el propio `test_demo_esta_equilibrado` existe porque un
pico de 185.000 € de vivienda desequilibró la demo) y **no le cabe la gestión** (inquilinos,
contratos, rentas, gastos, hipoteca, papeleo). Se decide crear una **tercera «app» dentro de
Liberty**, al nivel de la cartera y de Ingresos y gastos, y construirla por iteraciones en una
rama propia, sin publicar nada hasta que esté lista.

## Decisiones

**A. Colección propia, aparte de la cartera (`almacen.py`, `motor.py`).** Nueva colección raíz
`inmuebles` (ids `i1`, `i2`…; `siguiente_id` solo admite prefijos de una letra). El motor la
resume en `DATOS.inmuebles` con `inmuebles_de(cfg, deudas, hasta)` y **no la suma** en
`total.patrimonio` ni en ninguna agrupación de la cartera. Un test lo garantiza (mismo patrimonio
y mismos `porClase` con y sin inmuebles).

**B. La ficha (`guarda_inmueble`).** Nombre (obligatorio), tipo (piso, casa, local, garaje,
trastero, terreno, otro), titular, dirección, referencia catastral, m², habitaciones, valor
catastral; **compra** (fecha no futura, precio, gastos de compra); **valor** estimado a mano con
su fecha (sin fecha = hoy); **hipoteca** (capital pendiente, cuota, tipo de interés escrito en %
y guardado como fracción, como la TAE de una deuda, y fecha de fin). El formulario manda campos
planos (`compraPrecio`, `hipCuota`…) y el almacén los agrupa. Al editar se conserva lo que la
ficha aún no edita (`contratos`, `categorias`, de las iteraciones 2 y 3).

**C. Uso: inversión o vivienda habitual.** Por defecto, inversión, con estado (alquilado,
vacío, en reforma, en venta). Uno puede marcarse **vivienda habitual**: no lleva estado y
**solo puede haber una** (error claro si se intenta una segunda).

**D. Hipoteca dentro del inmueble, con enlace opcional a una deuda.** La hipoteca vive en la
ficha (fuente única). `deudaRef` solo **señala** una deuda (`tipo: "deuda"`) de Patrimonio para
navegar de una a otra; no mueve ninguna cifra. Una deuda solo puede enlazarse a un inmueble; si
se borra la deuda, el enlace se suelta y la hipoteca sigue. Si la ficha no tiene capital propio,
el motor usa el de la deuda enlazada.

**E. Revalorización honesta.** Sin valor estimado, el inmueble «vale lo que costó» (precio de
compra) y su revalorización es **desconocida**, no negativa: restar los gastos de compra daría
una «pérdida» que no es tal. Los totales solo comparan inmuebles con estimación propia.

**F. Interfaz.** Grupo nuevo **«Inmuebles»** en el Panel (KPIs: valor estimado, revalorización,
hipotecas pendientes y neto inmobiliario, más una tarjeta por inmueble que abre su ficha; la vista
es una foto fija y oculta el periodo y los filtros de la cartera) y en **Mis datos** (tabla con
alta, edición y borrado). Navegación en los dos sentidos inmueble ⇄ deuda (`irAEntidad` acepta el
origen `"inmueble"`) y entradas en la paleta Ctrl/⌘+K. Los catálogos (tipos, usos, estados) viven
en `motor.py` y se sirven en `/api/cartera`.

**G. Números del formulario con coma decimal.** Al rellenar la ficha para editar, los números van
con coma (`2,125`): `num_es` lee «2.125» como dos mil ciento veinticinco (en castellano el punto
separa miles). Verificado en vivo: re-guardar sin cambios deja la ficha idéntica.

## Botón «i» (ADR 0020)

Tarjetas nuevas `panel.inmuebles` y `datos.inmuebles`. Se actualiza `datos.activos` (los pisos y
locales, mejor en Inmuebles; los que ya estén como activo siguen funcionando) y el paso del tour
que enumera los grupos de vistas.

## Retrocompatibilidad

Aditivo. Una cartera sin `inmuebles` funciona igual (`[]` por defecto en `CARTERA_VACIA`; el
motor lo trata como vacío). Los productos `tipo: "inmueble"` existentes **conviven sin migrar**;
la migración se decidirá cuando la zona esté completa. Las copias de seguridad validan que
`inmuebles` sea una lista. Renombrar un titular llega también a los inmuebles.

## Limitación conocida

Si la cartera no tiene **ningún activo con datos**, `motor.construir` devuelve `None` y el Panel no
calcula nada (comportamiento previo; le pasa igual a quien solo tiene ingresos y gastos). Mis datos
sí funciona. Se revisará al llevar el resumen de inmuebles a Inicio (iteración 4).

## Arreglo colateral

El paso del tour sobre las vistas del Panel aún decía «Con las teclas 1–8 saltas al instante»,
resto de la retirada de atajos de la 1.16.1 (ADR 0027). Se corrige aquí; en `main` sigue hasta que
se integre esta rama o se haga un parche.

## Tests

`pytest` 284 (24 nuevos en `tests/test_inmuebles.py`: validación, conservación al editar, enlace y
unicidad de la deuda, propagación de titular, motor —coste, revalorización, neto, foto de un mes
pasado— y que la zona no toca el patrimonio de la cartera ni el de la demo), `npm test` 16/16 (2
nuevos: estado vacío y vista con datos, incluido el escapado del nombre), `ruff` OK, y verificación
en vivo por CDP en claro y oscuro: vista del Panel, alta, re-edición idéntica, regla de una sola
vivienda habitual, navegación inmueble ⇄ deuda, ayuda «i» y salto de tarjeta a ficha, sin errores
de JS.
