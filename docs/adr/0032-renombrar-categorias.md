# ADR 0032 — Renombrar o fusionar una categoría de ingresos y gastos

- **Estado:** aceptado (publicado en la v1.18.0)
- **Fecha:** 2026-11-01
- **Fase:** F6 · Inmuebles — pendiente nº 5 de la revisión de la 1.17.0

## Contexto

Las categorías son texto libre y se repiten en muchos sitios:

- `flujos[].categoria`;
- `config.categorias` (nombre, tipo, presupuesto);
- `config.reglasCategoria`;
- `config.recurrentes[].categoria`;
- `inmuebles[].categorias` y `contratos[].categoria`;
- vínculos de notas `{tipo:"categoria", ref}`.

Cambiar el nombre en la lista de Configuración solo cambiaba la lista. Los apuntes, reglas e
inmuebles seguían con el nombre viejo: la categoría «reaparecía» y el libro del inmueble
perdía sus apuntes.

## Decisión

**Operación propia en el servidor, inmediata** (`almacen.renombra_categoria`,
`POST /api/categorias/renombrar`). Va por `cambia()`: cerrojo, guarda de cartera activa y copia
automática previa.

No se aplica al pulsar «Guardar» de Configuración porque ese formulario reenvía las
categorías desde los textareas y los selectores de inmuebles: volvería a escribir los nombres
viejos. Por eso, si hay cambios sin guardar en Configuración, el botón pide guardarlos antes.
Tras renombrar, el formulario se vuelve a abrir con los datos nuevos.

**Reglas:**

- Origen y destino no pueden estar vacíos ni ser «Sin categoría»; tampoco iguales.
- El origen debe existir, en la lista o en algún apunte (las categorías escritas a mano
  también se pueden renombrar).
- Cambiar solo mayúsculas es un renombrado normal.
- **Fusión:** si el nombre nuevo ya existe (sin distinguir mayúsculas):
  - manda la grafía de la que ya existe;
  - deben ser del mismo tipo (ingreso/gasto);
  - no pueden ser de dos inmuebles distintos;
  - la de origen desaparece de la lista; la de destino hereda el presupuesto si no tenía;
  - las reglas y las categorías de inmueble repetidas quedan una sola vez.
- Devuelve cuántos apuntes, plantillas, reglas, inmuebles, contratos y notas cambió.

**Interfaz.** Bloque «Renombrar o fusionar una categoría» en Configuración →
💶 Ingresos y gastos: desplegable (agrupado por tipo, con nº de apuntes) → nombre nuevo
→ «Renombrar…». Debajo, la vista previa del impacto y el aviso de fusión o de tipos
incompatibles. Pide confirmación.

## Botón «i» (ADR 0020)

- `datos.config`: «✏️ Renombrar o fusionar una categoría».

## Retrocompatibilidad

Aditivo: no cambia el formato de datos.

## Tests

- **`pytest` 326** (+5): renombrado en todas partes, solo mayúsculas, fusión (grafía,
  presupuesto, reglas repetidas), casos prohibidos y conflicto de inmuebles, categoría que solo
  está en apuntes, y la API.
- Verificado en vivo (CDP): vista previa, renombrado de apuntes, inmueble y contrato, y aviso
  de cambios sin guardar.
