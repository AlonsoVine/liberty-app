# ADR 0012 — Copia de seguridad en .zip (con facturas) y limpieza de `mis_datos`

- **Estado:** aceptado
- **Fecha:** 2026-10-14
- **Fase:** mejoras post-F4 (copias y estructura de datos)

## Contexto

Con las facturas adjuntas (ADR 0011), la copia de seguridad de un solo `.json` ya no
lleva **todo**: los archivos quedaban fuera. Además, en `mis_datos` seguían colgando en
la **raíz** los archivos de trabajo de la **demo** (`calculado_demo.json`, `estado.json`,
`historico.json`, `cache/`), junto a `carteras/` y `app/`. Objetivo: que una copia pueda
llevarse **también las facturas** (sin perder ninguna, nunca) y que la raíz de `mis_datos`
tenga **solo `app/` y `carteras/`**.

## Decisión

**1. Copia en `.zip`.** En «Copias y seguridad», además del `.json` de siempre, un `.zip`
que contiene `cartera.json` + `adjuntos/`. Dentro del zip las facturas se renombran a un
nombre **descriptivo** `AAAA-MM-DD - IMPORTE€ - CONCEPTO/CATEGORÍA - nombre_original.ext`
(saneado, acortado, dedup) para poder identificarlas aunque se abra el zip fuera de la
app; y **se reescriben las referencias** en el `cartera.json` del zip para que se **restaure
sin perder ningún enlace**. Recuperar admite `.json` **y** `.zip` (el zip vuelca las
facturas en la carpeta de la cartera). El mismo nombre descriptivo se usa cuando una
factura queda «suelta» al borrar un apunte.

**2. `mis_datos` ordenado.** En modo demo, `carpeta()` pasa a ser `app/demo/` (en vez de
la raíz), así que los archivos de trabajo de la demo viven dentro de `app/`. La raíz queda
con **solo `app/` y `carteras/`** (cada cartera con su `cartera.json`, cálculo, estado,
histórico, caché, copias y `adjuntos/`). `migra_layout()` mueve los archivos de demo
sueltos de la raíz a `app/demo/` al arrancar: **idempotente y no destructivo** (solo mueve
si existe el origen y no el destino).

## No perder NUNCA una factura (garantías)

- **Exportar** = solo lee y copia; jamás borra ni mueve los originales.
- **Restaurar un zip que sustituye**: antes se **mueven** las facturas actuales a
  `copias/adjuntos_antes_de_recuperar_<sello>/` (no se pisan aunque el zip traiga otras con
  el mismo nombre); luego se escriben las del zip.
- **Restaurar un `.json`**: no toca las facturas en disco (sus referencias siguen válidas).
- **Migración**: mover-si-no-existe-destino; si algo falla (`OSError`), se reintenta en el
  próximo arranque sin tocar nada.
- Tests: ida y vuelta exportar→importar conservando la factura y su enlace; migración de la
  demo; renombrado descriptivo; borrar apunte conserva su factura.

## Alternativas descartadas

- **Meter las facturas en el `.json`** (base64): peso/rendimiento (ya en ADR 0011).
- **Renombrar las facturas en disco al subirlas**: se mantienen con nombre interno estable
  (aleatorio); el nombre descriptivo se genera al exportar/soltar, no en el día a día.
- **Borrar las facturas actuales al restaurar un zip**: se respaldan, nunca se pierden.
