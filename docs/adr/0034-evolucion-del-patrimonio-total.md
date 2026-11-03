# ADR 0034 — Evolución del patrimonio total del hogar

- **Estado:** aceptado (publicado en la 1.19.0)
- **Fecha:** 2026-11-03
- **Fase:** F6 · Inmuebles — lo diferido en el ADR 0033

## Contexto

La 1.18.0 puso en Inicio la card «Tu patrimonio» (cartera neta + inmuebles netos) con la foto
de hoy. Faltaba su evolución: la serie de la cartera es diaria y empieza en su primer
movimiento, y de los inmuebles solo hay precio de compra, estimaciones sueltas (`historico` +
la actual) y el capital pendiente **de hoy** de cada hipoteca.

## Decisiones

**Serie en el motor (`motor.serie_hogar`, en `inmuebles.total.serieHogar`).** Solo si hay
inmuebles. `{fechas, total, cartera, inmuebles, hipotecaEstimada}`.

- **Eje mensual propio:** el último día de cada mes desde lo más antiguo de la cartera **o de
  los inmuebles** (una casa comprada años antes de abrir la cartera cuenta desde su compra),
  y la fecha de la foto al final. Mensual porque los inmuebles cambian poco y así la serie es
  ligera (también en la web exportada).
- **Cartera:** su serie diaria en esa fecha; antes de su primer día, 0.
- **Valor de cada inmueble:** la última estimación a esa fecha; antes de la primera, el precio
  desde la compra. Antes de la compra no está. Sin fecha de compra, desde su primera
  estimación. Es un escalón, igual que la gráfica de la ficha (ADR 0031): entre estimaciones
  manda la anterior. No se interpola: sería inventar valores.
- **Hipotecas:**
  - enlazada a una deuda de la cartera → la serie real de esa deuda;
  - sin enlace → solo se sabe el capital de hoy: se reconstruye hacia atrás deshaciendo la
    amortización francesa, `C(k+1) = (C(k) + cuota) / (1 + i/12)`; sin cuota, el de hoy.
    Desde la compra y nunca por encima de lo que costó. Se marca `hipotecaEstimada` y la
    gráfica lo dice.
- **Reparto, como la card (ADR 0033):** total = cartera + valor − hipotecas sin enlace;
  inmuebles = valor − todas las hipotecas; cartera = total − inmuebles.
- **El último punto es la foto de hoy** (las mismas cifras que la card, con el valor en vivo).

**Interfaz.** En la card «Tu patrimonio», a la derecha de las cifras (debajo en pantallas
estrechas): «Cómo ha crecido» con el cambio en 12 meses (o desde el inicio) y una gráfica de
tres líneas (total destacado, cartera neta, inmuebles netos) con su tooltip. Necesita dos
puntos o más.

**Arreglo de paso:** `fmtEurSigno(v, dec)` ignoraba los decimales; siete llamadas ya pasaban
`0` y enseñaban céntimos.

## Privacidad

La web exportada con «Ocultar importes» escala todos los números que no son porcentajes ni
recuentos (`exportar.py`), así que la serie sale escalada sin tocar nada.

## Botón «i» (ADR 0020)

- `panel.inicio`: «📈 Cómo ha crecido tu patrimonio».

## Retrocompatibilidad

Aditivo: un campo nuevo en DATOS; sin cambios de datos.

## Tests

- **`pytest` 331** (+5): eje desde la compra aunque la cartera empiece después, antes de la
  compra, hipoteca sin enlace reconstruida (y con tope), hipoteca enlazada sin restar dos
  veces, y `construir` publica la serie que acaba en la cifra de la card.
- **`npm test` 25/25**: la gráfica con sus tres líneas, el cambio en 12 meses y la nota de
  hipoteca estimada; sin serie, sin gráfica.
