# ADR 0033 — «Patrimonio» pasa a ser «Cartera»; el patrimonio total va en Inicio

- **Estado:** aceptado (publicado en la v1.18.0)
- **Fecha:** 2026-11-02
- **Fase:** F6 · Inmuebles — siguiente paso tras la 1.17.0

## Contexto

Con la zona de Inmuebles (ADR 0028–0031), lo que la app llamaba «Patrimonio» ya no es todo lo
que tiene el hogar: es lo financiero (inversiones, cuentas y sus deudas). Los inmuebles van
aparte para no descuadrar los gráficos. El total del hogar solo aparecía como una casilla
dentro de la card «Tus inmuebles» de Inicio.

Alonso propuso: la pestaña «Patrimonio» es en realidad la **cartera**; **patrimonio** es la
suma de cartera e inmuebles y debe verse en Inicio, en una card central.

## Decisiones

**1. Solo cambian textos.** En la pestaña y sus cifras, «Patrimonio» → «Cartera»:

- pestaña «Cartera»; «Cartera neta», «Cartera bruta», «Cartera este mes»;
- bloque «Tu cartera hoy» (antes «Patrimonio del hogar», que era solo de la cartera);
- «Cartera neta y deudas», «Evolución de la cartera», «Cartera neta por titular»;
- «deuda de tu cartera» (en la hipoteca y la ficha del inmueble);
- ayudas «i», visita guiada, preguntas frecuentes, informe impreso.

No cambian: identificadores (`data-pv="patrimonio"`, `pintaPatrimonio`), claves de DATOS
(`patrimonioNeto`…), preferencias guardadas (`patrimonio.*`) ni los mensajes donde
«patrimonio» es el **archivo entero** del hogar («Eliminar este patrimonio», «Nuevo
patrimonio…»), que sigue siendo correcto.

**2. Objetivo e hitos: siguen midiéndose con la cartera** (decisión de Alonso, recomendada).
Si se midieran con el total, una tasación de la casa haría «cumplir» un hito sin ahorrar. Solo
cambia el texto: «Objetivo de tu cartera».

**3. Card «Tu patrimonio» arriba del todo en Inicio.**

- Cifra: `patrimonioHogar` del motor (cartera neta + valor de los inmuebles − hipotecas no
  enlazadas). Sin inmuebles, la cartera neta.
- Reparto en dos filas, que llevan a Cartera y a Inmuebles:
  - **Inmuebles netos** = valor − **todas** sus hipotecas (`total.neto`);
  - **Cartera neta** = total − inmuebles netos. Con una hipoteca enlazada a una deuda de la
    cartera, esa deuda se «devuelve» a la cartera y la hipoteca se ve con su inmueble; el
    total es el mismo y no se resta dos veces.
- Barra del reparto (%) cuando los dos lados son positivos.
- Sin inmuebles: fila «➕ Añade tus inmuebles» (no en la web exportada).
- Los apartados y el colchón no restan: el dinero sigue siendo tuyo (se ven en «Tu cartera
  hoy»).

**4. La card «Tus inmuebles» no repite el total**: valor, hipotecas, neto inmobiliario y
cash-flow 12 meses (o revalorización si no hay libro).

**5. Diferido:** la gráfica del patrimonio total en el tiempo (necesita una serie del motor
que combine la cartera con el historial de valoraciones de los inmuebles).

## Botón «i» (ADR 0020)

- `panel.inicio`: nuevo «💎 Tu patrimonio (arriba del todo)»; «🏠 Tus inmuebles» ajustado.
- `panel.patrimonio`: título «Cartera» y textos.
- `datos.config`, `datos.activos`, `panel.deudas`, `panel.inmuebles`, `datos.inmuebles`: textos.

## Retrocompatibilidad

Sin cambios de datos ni de API.

## Tests

- **`npm test` 25/25** (+1): la card con inmuebles (cifras, barra, navegación), con hipoteca
  enlazada y sin inmuebles; la pestaña se llama «Cartera»; el informe dice «Cartera neta».
- **`pytest` 326**, **`ruff`** OK.
