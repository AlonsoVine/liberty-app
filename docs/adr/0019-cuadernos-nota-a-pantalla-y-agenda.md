# ADR 0019 — Cuadernos de notas, nota a pantalla completa y pulido de la agenda

- **Estado:** aceptado
- **Fecha:** 2026-10-20
- **Fase:** madurez de UX (versión 1.13.0)

## Contexto

Segunda tanda sobre el «espacio libre» (notas, agenda), continuación de la 0018. Objetivo:
poder **archivar** notas documentales (p. ej. una nota de la renta con sus facturas) en
agrupadores, leer una nota larga cómodamente, y dejar la agenda más clara. Todo aditivo y sin
tocar las cifras del panel.

## Decisiones

**1. Cuadernos (`almacen.py`, `servidor.py`, `editor.js`).** Nuevo `cfg.cuadernos` =
`[{id, nombre, color?}]` (planos, sin anidar) y, en cada nota, un campo opcional `cuaderno`
(una nota pertenece a lo sumo a **un** cuaderno). Endpoints `POST /api/cuadernos` (guarda la
lista) y `POST /api/cuaderno-borra` (borra uno y **deja sus notas sueltas**, no las borra).
Front: pestaña **«📓 Cuadernos»** junto a «Lista de notas» con rejilla de cuadernos
(crear/renombrar/borrar, color), al entrar en uno se reusa la lista de notas filtrada a ese
cuaderno con «← Cuadernos». «Enviar a un cuaderno» desde el icono de la tarjeta, el formulario de
la nota y el modal de lectura.

**2. Visibilidad configurable + pestaña «Documentos» en Configuración.** `config.docNotasMuestra`
(`sueltas` por defecto | `todas`): la pestaña «Lista de notas» enseña solo las notas sin cuaderno
(modelo de archivado) o todas con un chip del cuaderno. Se expone en una **nueva pestaña
«Documentos»** del modal de Configuración, pensada para alojar los ajustes de la sección
(se trasladó ahí también el de la papelera de archivos).

**3. Nota a pantalla completa (`editor.js`, `index.html`).** La tarjeta de la lista recorta el
texto (~6 líneas, con desvanecido, clase `.notaTxt.recortada`); pulsar el título o el cuerpo abre
un **modal grande** (`.notaModalG`, reutiliza el `<dialog id="modal">` como la papelera) con el
texto completo, el **checklist operativo**, los chips pulsables de activos/documentos y acciones
(editar, a cuaderno, duplicar, borrar). Clic en el fondo o «Cerrar» vuelve. El ancho se fija en el
diálogo con `#modal:has(.notaModalG)` (el `.mForm` no puede ser más ancho que el diálogo).

**4. Pulido de la agenda.** La lista de recordatorios estrena los iconos estándar
**editar/borrar** (clase `.accIco`, ahora con estilo genérico fuera de tablas) a la derecha. En el
calendario, el chip de un recordatorio tiene **hover propio** (borde de acento + brillo), distinto
del hover del día, para que se vea que es editable (los vencimientos ya llevaban «→» a su ficha
desde la 0018).

## Retrocompatibilidad

Aditivo. Notas sin `cuaderno` y carteras sin `cuadernos` funcionan igual. `docNotasMuestra` por
defecto `sueltas`. Borrar un cuaderno nunca borra notas.

## Tests

pytest con casos nuevos: `guarda_cuadernos` (id estable, sin nombre fuera, color validado),
asignación de `cuaderno` a una nota y `borra_cuaderno` dejando las notas sueltas. `ruff`, 14 jsdom,
`node --check` y verificación visual por CDP (cuadernos, cuaderno abierto, modal de nota, pestaña
Documentos de Configuración, iconos de la agenda).
