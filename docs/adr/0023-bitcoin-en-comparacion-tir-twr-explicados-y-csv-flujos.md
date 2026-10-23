# ADR 0023 — Bitcoin en la comparación, TIR/TWR explicados y CSV de Ingresos y gastos

- **Estado:** aceptado
- **Fecha:** 2026-10-23
- **Fase:** madurez de UX (versión 1.14.1)

## Contexto

Tanda de correcciones pedidas por Alonso tras probar la 1.14.0: ampliar la comparación de
Rentabilidad para incluir Bitcoin (y cambiar el título), explicar con detalle TIR y TWR en la
tabla central, aclarar por qué el TIR de Rentabilidad y el de Patrimonio difieren un poco, y
mejorar el CSV de Ingresos y gastos.

## Decisiones

**1. Comparación «¿Y si lo hubiera metido en otro sitio?» (`motor.py`, `index.html`).** El título
pasa de «…en un indexado» a «…en otro sitio» y se añade **Bitcoin** a `REFERENCIAS`
(`piezas:[("BTC-EUR",1.0)]`, precio de Yahoo). La referencia compra BTC con tus mismas aportaciones
en las mismas fechas, como el resto.

**2. TIR y TWR explicados (`app.js`).** En la tabla central (vista Total) las cabeceras **TIR** y
**TWR** llevan el icono «i» (`info()`) con una explicación larga y detallada de qué es cada una,
cómo se calcula y en qué se diferencian (money-weighted vs time-weighted).

**3. Por qué difieren el TIR de Rentabilidad y el de Patrimonio (investigación, NO se cambia).**
El KPI «TIR anualizada» de Patrimonio y el de la tabla central son el **mismo** valor
(`total.tir`). El que difiere un poco es el de la caja «Tú tienes hoy… TIR» de la comparación
(`comparacion.tuTir`). Ambos usan **los mismos flujos** (compras/ventas/dividendos, mismas
fechas); la diferencia es el **valor con que se cierra el cálculo**: `total.tir` usa el valor
actual `p["valor"]` (para un activo con precio en vivo, como Bitcoin, el último tick), mientras
`tuTir` usa el valor de la **serie diaria al último cierre** (`serie[-1]`), para comparar en
igualdad con las carteras de referencia (que también se miden al cierre). Es correcto e
intencionado; sin activos con precio en vivo, ambos coinciden salvo redondeo. No se modifica.

**4. CSV de Ingresos y gastos a medida (`editor.js`).** El clic en «CSV» de la tabla de flujos usa
`descargaFlujosCSV` (en vez del genérico): el **importe** se exporta como número limpio (negativo
con guion ASCII), la **divisa** va en una **columna propia** (`€`), y **Observaciones** y
**Facturas** muestran su contenido real (el texto / el nombre del adjunto), vacío si no hay nada —
nunca los iconos. Respeta filtro, búsqueda y orden (lee las filas visibles y las mapea a los datos
por id). Helper `descargaCSV` compartido.

## Retrocompatibilidad

Aditivo. La referencia Bitcoin aparece solo si Yahoo devuelve BTC-EUR (si no, se omite, como las
demás). El CSV genérico sigue para el resto de tablas.

## Tests

`ruff`, `node --check`, 14 jsdom y verificación por CDP: Bitcoin en las opciones de comparación,
iconos «i» con el texto detallado en TIR/TWR, y el CSV de flujos con la columna Divisa y el importe
numérico. `pytest` en verde.
