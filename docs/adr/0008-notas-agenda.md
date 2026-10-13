# ADR 0008 — Notas, tablero y agenda

- **Estado:** aceptado
- **Fecha:** 2026-10-13
- **Fase:** mejoras post-F4 (sección «Notas»)

## Contexto

La sección «Notas» ofrecía dos vistas genéricas: una lista de notas y un tablero
tipo Trello. Son un espacio libre del usuario y **no afectan a las cifras** del
panel. Faltaba, sin embargo, una vista con **eje temporal**: la lista es material
de referencia y el tablero es estado (por hacer / en curso / hecho), pero no había
dónde ver «qué tengo que hacer y para cuándo». La app ya calcula **vencimientos**
(depósitos, fin de promoción, revisiones de deuda, reservados con fecha prevista)
y los muestra en el Panel, pero no se podían combinar con recordatorios propios.

## Decisión

Mantener las notas y el tablero como **espacio libre** (se guardan tal cual, el
cliente manda el todo, sin recálculo del panel) y:

1. **Enriquecer las notas** sin romper el modelo. Cada nota pasa a admitir campos
   **opcionales**: `etiquetas: [str]`, `fijada: bool`, `editada: fecha`, y
   `vinculo: {tipo: "activo"|"deuda"|"categoria", ref}`. Las **listas de tareas**
   viven dentro del propio texto: las líneas `- [ ] …` / `- [x] …` se renderizan
   como casillas marcables (marcarlas reescribe esa línea). No hay estructura nueva
   para las tareas: es texto, portable y simple.

2. **Enriquecer el tablero**: cada tarjeta admite `color` y `vence` (fecha)
   opcionales; se puede **reordenar dentro de una columna** además de moverla entre
   columnas, y se edita **en línea** (doble clic) en vez de con `prompt()`.

3. **Nueva vista «Agenda»** (`cfg.recordatorios`, endpoint `/api/recordatorios`,
   sin recálculo). Cada recordatorio es `{id, texto, fecha, hecho, repetir:
   "no"|"mensual"|"anual"}`. La Agenda **fusiona en el cliente** esos recordatorios
   con los `vencimientos` que el motor ya expone en `DATOS`, los ordena por fecha y
   muestra los días que faltan. Los vencimientos son **solo lectura** (se gestionan
   desde «Mis datos»); los recordatorios son editables y se pueden marcar hechos.

El saneado vive en `almacen.py` (`guarda_notas`, `guarda_tablero`,
`guarda_recordatorios`): límites de tamaño, deduplicado de etiquetas, validación de
`repetir` y de `vinculo.tipo`, y los campos opcionales **no se inventan** si no
vienen (para no ensuciar carteras existentes).

## Alternativas descartadas

- **Bitácora / diario** como tercera vista (registro cronológico de decisiones):
  útil, pero aporta menos que la Agenda y no aprovecha los vencimientos que la app
  ya calcula. Se deja como posible futura.
- **Tareas como estructura propia** (lista de objetos por nota) en vez de dentro
  del texto: más rígido y menos portable; el formato `- [ ]` es suficiente.
- **Recálculo del panel** al guardar recordatorios: innecesario; la Agenda solo
  combina datos que ya existen, así que se usa `cambia(recalc=False)` como en notas
  y tablero.

## Consecuencias

- Aditivo y retrocompatible: una cartera sin `recordatorios` ni los campos nuevos
  de nota/tarjeta funciona igual; los campos opcionales aparecen solo al usarlos.
- La Agenda depende de que el panel ya haya cargado `DATOS` (de donde lee los
  vencimientos); si no, muestra solo los recordatorios. No hay cálculo nuevo en el
  motor.
- Las listas de tareas son texto: se exportan y migran sin esfuerzo, pero no se
  pueden consultar/agregar como datos estructurados (no es el objetivo).
