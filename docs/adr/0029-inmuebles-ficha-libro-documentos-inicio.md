# ADR 0029 — Inmuebles: ficha ampliada, libro por categorías, documentos e Inicio

- **Estado:** aceptado (en la rama `inmuebles`; se integrará en `main` con la release que la cierre)
- **Fecha:** 2026-11-01
- **Fase:** F6 · Inmuebles — iteraciones 3 y 4 y la parte de documentos de la 5 (ver [diseño](../diseno-inmuebles.md))

## Contexto

Tras el núcleo (ADR 0028), Alonso pidió cuatro cosas:

- que **Inicio** reflejara la zona nueva;
- que los inmuebles tuvieran su sitio en **Configuración** y en **Documentos**;
- poder **asociar categorías** de ingresos y gastos a cada inmueble;
- una **ficha ampliada** del inmueble que reúna todo lo que tiene la de edición, más sus
  ingresos y gastos, sus categorías y sus documentos, asociables desde Documentos o desde
  la propia ficha.

Los contratos e inquilinos (iteración 2) quedan para después.

## Decisiones

**A. Libro por categorías (`almacen._categorias_inmueble`, `motor.libro_inmueble`).**

- El inmueble guarda `categorias: [...]`. Sus apuntes de Ingresos y gastos son su libro.
- No se duplica nada y no se tocan saldos. La comparación no distingue mayúsculas.
- **Una categoría, como mucho en un inmueble**, porque si no un apunte contaría dos veces. Se
  valida al guardar la ficha y al repartir desde Configuración.
- Se asocian desde dos sitios:
  - Casillas en la ficha. Las categorías de otro inmueble salen deshabilitadas y nombran a
    su dueño.
  - Configuración → **🏢 Inmuebles**, con un selector de inmueble por categoría. Así es
    imposible ponerla en dos.
- Configuración lo manda dentro de `/api/config` (`inmueblesCategorias`) para que se guarde
  todo junto, con una sola copia.
- Si la ficha no manda `categorias`, se conservan.
- El motor da, por inmueble:
  - ingresos, gastos y neto de los 12 meses que acaban en la fecha de valoración;
  - totales históricos;
  - series mensuales y reparto por categoría;
  - todos sus apuntes (con un tope de seguridad de 5.000) **sin su concepto**: la ficha lo
    lee de la cartera en vivo, así que no viaja en `DATOS` ni en la web exportada;
  - la **rentabilidad neta**: neto de 12 meses ÷ coste. Solo en los de inversión con ingresos.

**B. La vivienda habitual no es una inversión.** El cash-flow total («lo que te dejan») suma
solo los inmuebles de inversión. Los gastos de la habitual salen aparte («Tu vivienda, 12
meses»). En la verificación en vivo, mezclarlos daba un cash-flow de −2.215 € que no tenía
sentido.

**C. Ficha ampliada en el Panel (solo lectura).**

- Se abre al pulsar una tarjeta. Al ir a un inmueble desde Mis datos (nombre), una nota, la
  paleta o la lista de Inicio, `irAEntidad("inmueble")` lleva a la ficha mediante
  `window.verInmueble`. Si hay cambios sin recalcular, recarga y vuelve a ella.
- Contenido:
  - KPIs: valor, revalorización, neto, cash-flow y rentabilidad neta, o el coste de la
    habitual;
  - «El inmueble», «Compra y valor» e «Hipoteca»;
  - el libro: KPIs, barras, «Por categoría» (cada una salta a sus apuntes) y «Apuntes del
    periodo»;
  - los documentos.
- **Selector de periodo del libro** (añadido después, a petición de Alonso): 12 meses (por
  defecto), este año, el año pasado, todo o «Rango…» de una fecha a otra.
  - Se calcula en el navegador con los apuntes que manda el motor, sin volver al servidor.
  - Solo se repinta el cuerpo del libro, no los campos de fecha, y con retardo (350 ms). Es la
    lección de la 1.16.1: rehacer los `<input type=date>` en cada tecla robaba el foco.
  - Si el periodo pasa de dos años, las barras van por años.
  - El modo se recuerda (`patrimonio.inmPeriodo`). Al pasar a «Rango…» arranca con las fechas
    que estabas viendo.
  - La rentabilidad neta de la cabecera sigue siendo la de 12 meses.
- «✎ Editar ficha» abre el mismo formulario de Mis datos y recarga el Panel al guardar.
- La ficha abierta se recuerda (`patrimonio.inmSel`). Para volver a la lista, «← Todos los
  inmuebles» o volver a pulsar la pestaña.
- Sin «Mis datos» detrás (la web exportada) no hay ni edición ni documentos.

**D. Documentos = notas enlazadas.**

- No se crea un tipo de documento nuevo: se añade `inmueble` a `VINCULO_TIPOS`. Una nota (con
  sus archivos de la Biblioteca) se enlaza a un inmueble.
- Desde la nota: «Relacionada con → Un inmueble», también en los recordatorios.
- Desde la ficha:
  - «+ Nueva nota del inmueble», que ya viene enlazada;
  - «🔗 Enlazar una nota que ya tengo»;
  - «×» para quitar el enlace sin borrar la nota.
- La sección se repinta al guardar notas.
- **Al borrar un inmueble, sus enlaces se sueltan.** Así un inmueble nuevo que reutilice el id
  no hereda papeles ajenos.

**E. Inicio: «Tus inmuebles» y el patrimonio total del hogar.**

- `motor.inmuebles_hogar` calcula: neto de la cartera + valor de los inmuebles − hipotecas
  **sin enlace** (`hipotecasSinEnlace`).
- Las enlazadas a una deuda ya restan en el neto de la cartera: restarlas otra vez sería
  doble conteo.
- El bloque muestra:
  - las tarjetas de patrimonio del hogar, valor, hipotecas y cash-flow (o neto);
  - una lista corta de inmuebles que abre sus fichas.
- Sin inmuebles, una invitación a la zona.

## Arreglo de privacidad (también en `main` / 1.16.1)

Al verificar la **web exportada** («Publicar como web → Ocultar importes») salieron dos fallos
previos:

1. `exportar.sin_importes` escalaba solo una lista de campos «de dinero». Se colaban **62
   rutas con cifras reales** en la demo: patrimonio neto y bruto, deudas, colchón, dinero libre,
   variaciones, informe fiscal, saldos de vencimientos…
   - Se invierte la regla: **se escala todo número** salvo los de `NO_DINERO` (porcentajes,
     tipos, días, recuentos, superficies) y los bloques de proporciones o índices
     (`BLOQUES_RATIO`).
   - Los importes escritos dentro de textos se tapan («••• €»).
   - Un campo nuevo ya no se puede escapar por olvido.
2. `app.js` reescribía `window.OCULTAR_IMPORTES` con la preferencia local de quien abría la
   web: con «Ocultar importes» apagado, la web exportada **enseñaba las cantidades**. Ahora la
   marca de la exportación manda (`OCULTOS_AL_EXPORTAR`).

Conviene sacar este arreglo en un parche de `main` sin esperar a la rama.

## Botón «i» (ADR 0020)

- Se actualizan:
  - `panel.inicio`: tus inmuebles y patrimonio del hogar;
  - `panel.inmuebles`: ficha completa, libro, cash-flow y rentabilidad neta, documentos;
  - `datos.inmuebles`: categorías y ver ficha;
  - `datos.config`: pestaña Inmuebles;
  - `doc.lista`: vincular a inmuebles.
- Textos de ayuda en la ficha de edición y en la pestaña de Configuración.

## Retrocompatibilidad

Aditivo. Sin `categorias` no hay libro (`libro: null`) y todo funciona igual. Las notas
antiguas no cambian. La demo añade la categoría «Gastos piso Valencia», 5 apuntes (2 rentas,
comunidad e IBI) y las categorías de sus dos inmuebles.

## Pendiente

- Contratos e inquilinos, con la rentabilidad bruta (iteración 2).
- Filtro «ocultar apuntes de inmuebles» en Ingresos y gastos.
- Que la asociación siga a una categoría renombrada (hoy las categorías se editan como texto).
- Avisos de agenda del inmueble.
- La limitación de `construir` → `None` sin activos.

## Tests

- **`pytest` 295.** Son nuevos:
  - 11 en `test_inmuebles.py`: categorías desde la ficha y desde Configuración con su
    unicidad; libro y su ventana de 12 meses; el concepto no viaja; habitual aparte;
    patrimonio del hogar sin doble conteo; libro y hogar en la demo; vínculo de notas y su
    limpieza; API de config.
  - 2 en `test_exportar.py`: ninguna cifra de la demo intacta; euros en textos.
- **`npm test` 20/20.** Son nuevos: la ficha ampliada, el periodo del libro (12 meses, todo
  y un rango sin rehacer los campos de fecha), Inicio con y sin inmuebles, y que la web oculta
  no se pueda destapar.
- **`ruff`** OK.
- **CDP en claro y oscuro, sin errores de JS:**
  - Inicio y ficha.
  - Configuración → Inmuebles: guardar un reparto.
  - Casillas ocupadas en la ficha.
  - Nota nueva desde la ficha, quitar y volver a enlazar.
  - Chip de nota → ficha.
  - Ficha de la habitual.
  - Web exportada con y sin importes.
  - Periodo del libro: los cinco modos, y una fecha tecleada dígito a dígito en «Rango…» sin
    perder el foco.
