# ADR 0010 — Observaciones del apunte y tarjetas del tablero en la agenda

- **Estado:** aceptado
- **Fecha:** 2026-10-14
- **Fase:** mejoras post-F4 (ingresos y gastos + sección Notas)

## Contexto

La columna «Nota» de Ingresos y gastos guardaba, de hecho, el **concepto** del banco
(lo rellena la importación). Se quería además poder escribir una **nota libre** por
apunte, sin ocupar una columna ancha, y que **no se mezclara** con la sección Notas.
Surgió un choque de nombres: en la app «**apunte**» ya es el registro de ingreso/gasto
y «**Notas**» es la pestaña del otro lado.

## Decisión

Tres términos sin solapamiento:

- **Apunte** = el registro (como estaba).
- **Concepto** = de qué es (lo que ya había en el campo `nota`; se **renombra solo la
  etiqueta** de la columna y del formulario, la clave de datos sigue siendo `nota` para
  no migrar nada).
- **Observaciones** = nota libre del apunte. Campo nuevo `observaciones` en el flujo,
  **opcional** (solo se guarda si tiene contenido; `guarda_flujo` lo reconstruye en cada
  guardado, así que vaciarlo lo borra). No se muestra como columna: una **columna
  estrecha con 📝** marca los apuntes que la tienen (clic → popover para leer/editar) y
  hay un filtro **«Observaciones: con/sin nota»** en el super-buscador. **Aislado**: no
  aparece en Notas, Agenda ni tablero.

Además, las **tarjetas del tablero que tengan fecha de vencimiento** (`vence`, ADR 0008)
pasan a aparecer en la **Agenda** (calendario y lista) como una **tercera fuente**, junto
a recordatorios y vencimientos. Son **solo lectura** en la agenda (badge «📋 Tablero»,
sin checkbox ni editar/borrar); al pulsarlas se abre el Tablero, que sigue siendo su
único punto de gestión.

## Alternativas descartadas

- **Renombrar la clave `nota`→`concepto`** y usar `nota` para la nueva: obligaría a migrar
  todos los flujos; se evita renombrando solo la etiqueta visible.
- **Llamar «apuntes» o «notas» a la nota libre**: choca con el registro («apunte») y con
  la pestaña («Notas»). Por eso «Observaciones».
- **Observaciones como columna visible**: ocupa demasiado; mejor indicador + popover.
- **Editar/cerrar las tarjetas desde la agenda**: se mantiene el tablero como única
  fuente de gestión; en la agenda son solo lectura.

## Consecuencias

- Aditivo y retrocompatible: apuntes sin `observaciones` y tableros sin fechas funcionan
  igual; los campos nuevos solo aparecen al usarlos.
- El CSV de la tabla no incluye las observaciones (no son columna); se ven/editan desde
  el apunte. Se puede añadir más adelante si hace falta.
