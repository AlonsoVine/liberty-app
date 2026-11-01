# ADR 0031 — Pasar los inmuebles de la cartera a la zona de Inmuebles

- **Estado:** aceptado (en la rama `inmuebles`; se integrará en `main` con la release que la cierre)
- **Fecha:** 2026-11-01
- **Fase:** F6 · Inmuebles — el pendiente «migración de los productos `tipo:"inmueble"`»
  (ADR 0028, 0030)

## Contexto

Antes de la zona de Inmuebles, un piso solo se podía apuntar en la cartera como un activo
de tipo «Inmueble», con sus valores anotados. Esos productos convivían sin migrar (ADR 0028).
Problemas:

- Si además se crea el mismo inmueble en la zona nueva, **cuenta dos veces** en el patrimonio
  del hogar de Inicio (cartera + inmuebles).
- No tienen ficha: ni libro, ni inquilinos, ni avisos.
- Mezclan ladrillo con inversiones en las gráficas y la rentabilidad de la cartera.

## Opciones

- **A. Traspaso completo:** el producto sale de la cartera **también hacia atrás**; sus datos
  se llevan al inmueble.
- **B. Como una venta en la fecha del traspaso:** la cartera conserva su pasado con el
  inmueble dentro y ese día sale como una retirada.

Alonso eligió **A**. Encaja con la idea de que la cartera es lo financiero y los inmuebles van
aparte (y ambos forman el patrimonio del hogar). Pidió además llevar a la ficha del inmueble
algo de lo que enseñaba la ficha del activo: su **gráfica de valor**.

## Decisiones

**Traspaso (`almacen.traspasa_a_inmueble`, `POST /api/traspasos`).** Todo o nada, bajo el
cerrojo y con copia automática previa, como cualquier guardado:

1. Se crea la ficha con los datos del formulario (valida como `guarda_inmueble`). Sin valor
   estimado, toma el último valor anotado del producto.
2. Sus valores anotados pasan al **historial** del inmueble (`historico`), salvo el que queda
   como actual.
3. Las notas (`vinculo` y `vinculos`) y los recordatorios que señalaban al producto pasan a
   señalar el inmueble.
4. Se borra el producto con sus movimientos y valores (`borra_producto`).

- Si la ficha no valida, no se toca nada.
- Solo para productos de tipo `inmueble`.
- **No pasan** los movimientos que no son compras (rentas como «dividendo», ventas,
  comisiones). El formulario lo avisa y sugiere apuntar las rentas en Ingresos y gastos.

**Formulario.** Es el del inmueble, ya relleno, con un recuadro que explica qué pasará:

- nombre, titular y nota (su «papel»);
- el **tipo**, deducido del nombre: garaje, trastero, terreno, casa, piso o local; si no, otro;
- el **estado** «alquilado» si el nombre o la nota hablan de alquiler;
- el **último valor** con su fecha;
- la **compra**: la suma de las compras y la fecha de la primera. Sin compras, lo aportado de
  sus valores (productos «a mano»).

**Dónde se ofrece.** Un aviso «🏠 Tienes N inmuebles dentro de tu cartera» con un botón
«Pasar a Inmuebles →» por cada uno:

- en **Mis datos → Inmuebles**;
- en **Panel → Inmuebles**: guarda y recarga.

**Historial de valoraciones (`historico: [{fecha, importe}]`).**

- Al guardar la ficha con un valor estimado de **otra fecha**, el anterior pasa al historial.
  Corregir el del mismo día lo sustituye.
- Una fecha por entrada, hasta 300.
- Se conserva al editar (`INMUEBLE_CONSERVA`).
- `inmuebles_de` toma el valor de la **última estimación a la fecha de la foto**. Antes, en un
  mes pasado una estimación posterior se descartaba y el inmueble quedaba sin valor. Devuelve
  `valoraciones` (historial + actual, hasta esa fecha).

**Evolución del valor en la ficha.**

- Una gráfica de línea mes a mes, desde la compra (o la primera estimación) hasta la última.
- Entre estimaciones manda la anterior (escalón): es lo que se sabía entonces.
- Marcas en la compra (verde, con aro) y en cada estimación.
- Sale con dos fechas o más.
- `lineaConEventos` acepta `etiquetaX` y `fechaTT` para rotular por meses. Sin ellos, igual que
  antes.

## Botón «i» (ADR 0020)

- `panel.inmuebles`: «📈 Evolución del valor» y «🔀 ¿Tenías el piso en la cartera?».
- `datos.inmuebles`: «🔀 Pasar a Inmuebles».

## Retrocompatibilidad

Aditivo:

- Sin `historico`, todo igual.
- Los productos de tipo inmueble siguen funcionando si no se traspasan; solo hay un aviso.
- El traspaso borra datos de la cartera, por diseño, pero los lleva al inmueble, y hay copia
  automática previa.

## Tests

- **`pytest` 321** (+4):
  - historial al cambiar la estimación y foto de un mes pasado;
  - traspaso completo: valor, historial, compra, notas, recordatorios, fuera de la cartera;
  - traspaso que no valida y producto que no es inmueble;
  - API.
- **`npm test` 24/24**: la evolución del valor con dos o más fechas, y sin ella con una.
- **`ruff`** OK.
