# ADR 0020 — Regla del botón de información, tabla central de Rentabilidad y avisos de la agenda

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Fase:** madurez de UX (versión 1.14.0)

## Contexto

Dos cosas motivan esta tanda. Primera, un fallo de proceso: en la 1.13.0 se creó la
entidad de **cuadernos** y se rehízo el sistema de notas, pero la **ayuda contextual** (el
botón «i» de la pantalla) no se actualizó y quedó describiendo una versión anterior. Hay que
convertir «mantener la ayuda al día» en una regla, no en un acto de buena voluntad. Segunda,
Alonso pidió más potencia de análisis en **Rentabilidad** (una vista de conjunto de todas las
rentabilidades, no solo por año/producto) y avisos **por fecha** configurables para la agenda.

## Decisiones

**1. Regla: toda funcionalidad nueva o modificada actualiza su botón «i» (proceso).**
Siempre que se cree o cambie el comportamiento de cualquier pantalla, área o elemento de la
app, en el **mismo lote** hay que actualizar la entrada correspondiente del registro `AYUDA`
de `app/web/app.js` (lo que abre el botón «i» de esa zona). La ayuda forma parte del elemento:
si cambia el elemento y no la ayuda, el lote no está terminado. Como primer cumplimiento, esta
versión pone al día la ayuda de **Documentos · Lista de notas** (cuadernos, color, pin, ficha a
pantalla completa, chips y navegación), **Documentos · Agenda** (iconos, recordatorios que se
repiten, avisos con antelación) y **Rentabilidad** (tabla central, TIR vs TWR).

**2. Tabla central de Rentabilidad (`motor.py`, `app/web`).** Nuevo bloque arriba de la
pestaña Rentabilidad (`#rentCentral`, `pintaRentCentral()`): un **resumen de cartera** (aportado,
valor, plusvalía €/%, TIR y TWR) y una **tabla por activo** con fila de total, y un **selector de
periodo** `Total | Año | Mes`:
- **Total** (de vida): aportado, valor, plusvalía, **TIR** (rentabilidad de tu dinero,
  money-weighted) y **TWR** (rentabilidad de la inversión, time-weighted, comparable entre
  productos). Se explica la diferencia en la propia nota y en la ayuda.
- **Año / Mes**: descomposición en inicio → +aportado +mercado → cierre, con la rentabilidad del
  periodo (TWR encadenado para la cartera; por activo, el TWR del año o, en el mes, sobre el valor
  inicial). Reutiliza `resumenMensual` y `rentabilidadAnual` ya calculados; el único añadido al
  motor es el **TWR total por producto** (`p["twr"]`, derivado de `idx_prod`).

**3. Avisos de la agenda configurables (`almacen.py`, `motor.py`, `app/web`).** Nuevo
`config.avisoAgendaDias` (entero 0–365; vacío = sin aviso) en la **pestaña «Documentos»** de
Configuración. El motor emite, por cada recordatorio cuya próxima ocurrencia (respeta
`repetir` mensual/anual y `hecho`) cae dentro de la ventana, una alerta `info` con clave
`agenda-proxima` y un **`destino`** `{tab:"notas", vista:"agenda", fecha}`. Las alertas se muestran
en la franja superior del **Panel** (`pintaAlertas`) y de **Mis datos** (`avisa`), y al pulsarlas
`window.Editor.irAgenda(fecha)` abre el **calendario** situado en el mes y **resalta** el día
(clase `.calDia.flash`). El aviso se puede desactivar del todo desde el centro de avisos
(General), por su clave en `AVISOS_CATALOGO`.

**4. Las cuatro pestañas de Configuración en una sola línea.** El modal de Configuración se
ensancha (`#modal:has(.cfgTabs){width:min(820px,…)}`) y `.cfgTabs` pasa a `nowrap`, para que
General · Activos · Ingresos y gastos · Documentos quepan en una fila.

## Retrocompatibilidad

Todo aditivo. Carteras sin `avisoAgendaDias` ni recordatorios no generan avisos; `_al` admite
`destino` opcional sin afectar a las alertas existentes; productos sin `twr` muestran «—». La
tabla central no recalcula el panel: solo agrega datos ya expuestos.

## Tests

`pytest`: validación de `avisoAgendaDias` (límite 365, vacío lo elimina) y el aviso de agenda
(salta dentro de la ventana con `destino` a la agenda, no salta fuera ni sin configurar).
`ruff`, `node --check`, 14 jsdom y verificación visual por CDP (tabla Total/Año/Mes, pestañas de
Configuración en una línea, aviso de agenda clicable y salto al calendario).
