# ADR 0013 — Pulidos de UX y Configuración por pestañas (General / Activos / Ingresos y gastos)

- **Estado:** aceptado
- **Fecha:** 2026-10-14
- **Fase:** mejoras post-F4 (pulido de experiencia)

## Contexto

Batería de siete pulidos pedidos por el usuario. El más sustancial es el **#7**: la
pantalla de Configuración había crecido hasta mezclar en un único formulario largo tres
tipos de ajustes muy distintos —lo general del hogar, lo de la «app de activos» y lo de la
«app de ingresos y gastos»—, lo que costaba de leer y recorrer. Los otros seis son arreglos
y retoques concretos.

## Decisión

**#7 · Configuración en tres bloques.** Tanto el formulario de edición (modal) como la vista
de lectura se agrupan en tres secciones con el mismo criterio:

- **🏠 General del hogar:** nombre del patrimonio, objetivo, titulares, colchón, inflación,
  avisos automáticos, privacidad (buscar actualizaciones).
- **📈 Activos e inversiones:** tipos de activo (base + propios), control de asignación
  (concentración, desviación, objetivos por tipo), días de aviso de vencimientos, monedas,
  dimensiones de clasificación de activos.
- **💶 Ingresos y gastos:** categorías, reglas del banco, marcas, entidades/bancos,
  dimensiones de flujos y el recordatorio «sin anotar».

En el **modal** son **pestañas** (`.cfgTabs`/`.cfgTab` + paneles `.cfgPanel`): todas las
secciones siguen en el DOM (solo se ocultan con `hidden`), así que un único «Guardar» guarda
el formulario entero, sin tocar el handler ni los nombres de campo. En la **vista de lectura**
son tres tablas `leyenda` con cabecera de grupo. Esto reparte el antiguo bloque «Control de
asignación», que mezclaba objetivos de activos con el recordatorio de flujos (`diasSinAnotar`
pasa a Ingresos y gastos; `diasAviso` queda en Activos).

**Pulidos (#1–#6):**

1. **Aviso de versión arriba.** Junto al selector de patrimonio, una píldora naranja
   `#avisoVersion` que aparece solo si `/api/version` indica `hayNueva`; al pulsarla,
   `actualizaDesdePie` (la misma descarga que el pie). Respeta el toggle de privacidad.
2. **«Limpiar filtros» con solo fechas.** Los filtros de fecha de Ingresos y gastos hacen un
   refresco ligero (sin reconstruir la barra, para no perder el foco); por eso el botón
   «Limpiar filtros» —que vive en la barra— no aparecía al poner únicamente un rango. Ahora
   `refrescaFlujos` muestra/oculta el botón y marca el campo de fechas como activo a mano.
3. **Facturas en formato registro.** La pestaña «Facturas» pasa de tarjetas (`.factGrid`/
   `.factCard`) a filas compactas (`.factRows`/`.factRow`): se ven muchas más de un vistazo.
4. **«Ver apunte» selecciona el apunte.** Desde Facturas, «Ver apunte» no solo cambia a
   Ingresos y gastos: resalta la fila (`#fila-flujo-<id>` + clase `.resaltado`, destello que
   se desvanece) y hace scroll a ella. Si algún filtro la dejaba fuera, se limpian los filtros
   (`irAFlujo`).
5. **Selector de año del informe fiscal estilizado.** Ese `<select>` vive fuera de `#editor`,
   así que no heredaba estilos; se le da la clase `.selApp` (misma flecha y aspecto que los
   selects del editor).
6. **«+ Añadir aportación» en la ficha del producto.** En «Aportaciones a este producto»
   (Panel → ficha) un botón lleva a «Saldos y movimientos» y abre el formulario de movimiento
   con el **producto precargado** (importe/precio en blanco). Nuevo `window.Editor.nuevoMovimiento(id)`.
   Solo en modo propio.

## Garantías / retrocompatibilidad

- No cambia el modelo de datos ni la API: las pestañas de Configuración solo reorganizan el
  mismo formulario (mismos `name`), verificado por un guardado de ida y vuelta que persiste
  campos de paneles distintos (uno visible, otro oculto).
- Todo verificado por CDP en una cartera de ejemplo (propio): pestañas y guardado, limpiar
  filtros con solo fechas, facturas en filas, «Ver apunte» con resaltado, selector fiscal
  estilizado, «+» de aportaciones con producto precargado y píldora de versión.

## Alternativas descartadas (para #7)

- **Acordeón** y **cabeceras + índice**: válidas, pero las pestañas separan mejor los tres
  conceptos y reducen el scroll (elección del usuario).
