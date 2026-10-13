# ADR 0009 — Vínculo de notas y recordatorios a entidades (no a categorías)

- **Estado:** aceptado
- **Fecha:** 2026-10-13
- **Fase:** mejoras post-F4 (sección «Notas», continúa [ADR 0008](0008-notas-agenda.md))

## Contexto

Las notas podían enlazarse a un **activo**, una **deuda** o una **categoría**
(ADR 0008). Se quería, además: (a) que los **recordatorios** también pudieran
enlazarse; (b) poder enlazar a un **reservado**; y (c) que una entidad con nota
asociada **lo señalara desde el resto de la app** (un icono que llama la atención
y lleva a la nota). Al diseñarlo surgió la duda de si **categoría** encaja en ese
modelo.

## Decisión

Enlazar notas y recordatorios **solo a entidades concretas con id estable**:
**activo, deuda o reservado**. Se **retira «categoría»** del selector al crear o
editar, pero se **sigue aceptando y mostrando** si una nota ya la tenía (el campo
`vinculo:{tipo,ref}` admite `categoria` como valor legado; no se borra al guardar).

Motivo: un activo/deuda/reservado es **una cosa única**, así que tiene un sitio
natural donde enseñar el indicador (su fila en Mis datos, su ficha en el Panel) y
un **enlace de vuelta inequívoco** (una entidad ↔ sus notas). Una **categoría** no
es una entidad sino una etiqueta que llevan muchos apuntes: no tiene un único lugar
donde colgar el indicador y el enlace de vuelta queda difuso.

**Indicador e ida-vuelta:**
- El motor expone en `DATOS` la lista `notasRefs` (refs de entidades con alguna
  nota), para que el **Panel** pinte el icono en la ficha sin consultar las notas.
- El editor pinta el mismo icono en las tablas de **Activos/Deudas/Reservados**.
- Al pulsarlo, `window.Editor.verEntidad(ref)` abre la pestaña **Notas → Lista**
  filtrada por esa entidad (un banner permite «ver todas»).

Los **recordatorios** reutilizan el mismo selector de vínculo y se guardan igual
(`guarda_recordatorios` acepta `vinculo` opcional).

## Alternativas descartadas

- **Mantener «categoría»** como destino de enlace de primera clase: sin un hogar
  claro para el indicador, aporta poco; se deja solo como valor legado.
- **Indicador también para categorías** (p. ej. en cada flujo de esa categoría):
  ruidoso y de dudosa utilidad.
- **Exponer todas las notas en `DATOS`** para el Panel: basta con los `notasRefs`
  (la sección Notas vive en el editor, que ya tiene las notas completas).

## Consecuencias

- Aditivo y retrocompatible: los vínculos a categoría previos se siguen viendo; los
  nuevos usan activo/deuda/reservado.
- El indicador del Panel depende de `DATOS.notasRefs` (recalculado como el resto del
  panel); el de Mis datos se calcula en el cliente desde las notas cargadas.
